"""
Critic Agent：对候选分支的执行结果进行质量评分。
"""

from llm.client import LLMClient

CRITIC_SYSTEM = "你是一个严格的执行结果评价器，只输出 JSON，不要输出解释。"

CRITIC_PROMPT_TEMPLATE = """请评价以下子任务的执行结果。

任务节点：{node_name}
任务描述：{node_description}

执行策略：{action_description}

执行结果：
{output}

请从以下维度评分：
- quality_score：结果质量，0.0 到 1.0
- confidence_score：可信度，0.0 到 1.0
- success：是否成功，true 或 false
- reason：简要原因

只输出 JSON，格式如下：
{{"quality_score": 0.85, "confidence_score": 0.80, "success": true, "reason": "结果完整且符合要求"}}"""


class CriticAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def score(self, node, action, output: str) -> dict:
        """对某个节点的某个动作执行结果进行评分，返回评分字典。"""
        prompt = CRITIC_PROMPT_TEMPLATE.format(
            node_name=node.name,
            node_description=node.description,
            action_description=action.description,
            output=output[:1500],  # 截断过长输出
        )

        messages = [
            {"role": "system", "content": CRITIC_SYSTEM},
            {"role": "user", "content": prompt},
        ]
        return self.llm.chat_json(messages)
