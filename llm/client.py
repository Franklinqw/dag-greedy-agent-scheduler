"""
LLM client with a deterministic mock fallback.

The project should remain runnable even when the remote model is unavailable.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import requests

from config import LLM_API_KEY, LLM_MODEL, LLM_TIMEOUT, LLM_URL


class LLMClient:
    def __init__(
        self,
        url=None,
        api_key=None,
        model=None,
        use_mock: bool | None = None,
        allow_fallback: bool = True,
    ):
        self.url = url or LLM_URL
        self.api_key = api_key or LLM_API_KEY
        self.model = model or LLM_MODEL
        self.use_mock = bool(use_mock) if use_mock is not None else False
        self.allow_fallback = allow_fallback

        self.headers = {
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "Content-Type": "application/json",
        }

    def chat(self, messages, temperature=0.3):
        if self.use_mock or not self.api_key:
            if not self.use_mock and not self.api_key and not self.allow_fallback:
                raise ValueError("Remote LLM is required, but no API key is configured.")
            return self._mock_chat(messages)

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        last_error = None
        for attempt in range(4):
            try:
                response = requests.post(
                    self.url,
                    headers=self.headers,
                    json=data,
                    timeout=LLM_TIMEOUT,
                )
                if response.status_code == 429 and attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except Exception as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                if not self.allow_fallback:
                    raise
                return self._mock_chat(messages)

        if not self.allow_fallback and last_error is not None:
            raise last_error
        return self._mock_chat(messages)

    def chat_json(self, messages, temperature=0.1):
        content = self.chat(messages, temperature=temperature).strip()
        if content.startswith("```"):
            lines = content.splitlines()
            content = "\n".join(lines[1:-1])
        return json.loads(content)

    def _mock_chat(self, messages) -> str:
        prompt = messages[-1]["content"] if messages else ""

        if "输出格式示例" in prompt and '"nodes"' in prompt:
            return json.dumps(self._mock_plan(), ensure_ascii=False)

        if "只输出 JSON" in prompt and "quality_score" in prompt:
            return json.dumps(self._mock_score(prompt), ensure_ascii=False)

        return self._mock_execute(prompt)

    def _mock_plan(self) -> dict[str, Any]:
        return {
            "nodes": [
                {
                    "node_id": "task_1",
                    "name": "理解任务",
                    "description": "提炼用户目标与约束",
                    "deps": [],
                    "actions": [
                        {
                            "action_id": "task_1_a1",
                            "description": "简要分析",
                            "prompt": "提炼目标、输入和输出",
                        },
                        {
                            "action_id": "task_1_a2",
                            "description": "结构分析",
                            "prompt": "按目标、约束、验收标准拆解",
                        },
                    ],
                },
                {
                    "node_id": "task_2",
                    "name": "生成结果",
                    "description": "根据任务理解生成结果",
                    "deps": ["task_1"],
                    "actions": [
                        {
                            "action_id": "task_2_a1",
                            "description": "保守生成",
                            "prompt": "输出简洁结果",
                        },
                        {
                            "action_id": "task_2_a2",
                            "description": "详细生成",
                            "prompt": "输出包含关键解释的结果",
                        },
                    ],
                },
            ]
        }

    def _mock_score(self, prompt: str) -> dict[str, Any]:
        output_match = re.search(r"执行结果：\s*(.*)", prompt, re.DOTALL)
        output = output_match.group(1).strip() if output_match else prompt

        lowered = output.lower()
        bad_markers = ["失败", "错误", "缺失", "bad", "error"]
        weak_markers = ["过短", "未完成", "待补充"]

        success = not any(marker in lowered for marker in bad_markers)
        quality = 0.88 if success else 0.35
        confidence = 0.83 if success else 0.40

        if any(marker in lowered for marker in weak_markers):
            quality -= 0.18
            confidence -= 0.12

        quality = max(0.0, min(1.0, quality))
        confidence = max(0.0, min(1.0, confidence))

        return {
            "quality_score": quality,
            "confidence_score": confidence,
            "success": success,
            "reason": "mock evaluator",
        }

    def _mock_execute(self, prompt: str) -> str:
        action = self._extract_field(prompt, "执行策略：")
        task_name = self._extract_field(prompt, "任务节点：")
        task_desc = self._extract_field(prompt, "任务描述：")

        if "快速" in action or "摘要" in action or "简" in action:
            return f"{task_name}：完成。策略={action}。结论：{task_desc[:40]}。"

        return (
            f"{task_name}：已完成。\n"
            f"- 任务描述：{task_desc}\n"
            f"- 执行策略：{action}\n"
            f"- 结果：给出一个可继续传递到下游节点的稳定中间结果。"
        )

    @staticmethod
    def _extract_field(text: str, label: str) -> str:
        if label not in text:
            return ""
        tail = text.split(label, 1)[1]
        return tail.splitlines()[0].strip()
