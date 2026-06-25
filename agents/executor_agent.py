"""
Executor Agent：执行 DAG 中的具体子任务节点。
"""

from llm.client import LLMClient

EXECUTOR_SYSTEM = "你是一个可靠的 Agent 任务执行器，只输出执行结果，不输出多余解释。"

EXECUTOR_PROMPT_TEMPLATE = """请完成以下子任务。

任务节点：{node_name}
任务描述：{node_description}

执行策略：{action_description}
具体指令：{action_prompt}

前置节点上下文：
{context}

请输出该子任务的执行结果。"""


class ExecutorAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def execute(self, node, action, context: dict) -> str:
        """执行某个节点的某个候选动作，返回执行结果文本。"""
        context_str = "\n".join(
            f"[{nid}]: {output[:300]}" for nid, output in context.items()
        ) if context else "（无前置节点）"

        prompt = EXECUTOR_PROMPT_TEMPLATE.format(
            node_name=node.name,
            node_description=node.description,
            action_description=action.description,
            action_prompt=action.prompt,
            context=context_str,
        )

        messages = [
            {"role": "system", "content": EXECUTOR_SYSTEM},
            {"role": "user", "content": prompt},
        ]
        return self.llm.chat(messages)
