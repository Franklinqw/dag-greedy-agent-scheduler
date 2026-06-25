"""
Planner Agent：将用户复杂任务拆解为 DAG 任务图。
"""

from llm.client import LLMClient

PLANNER_SYSTEM = "你是一个擅长任务拆解和 DAG 规划的智能体。只输出 JSON，不要输出解释。"

PLANNER_PROMPT_TEMPLATE = """请将以下用户任务拆解为一个 DAG 任务图（有向无环图）。

要求：
1. 输出严格 JSON 格式。
2. 每个节点包含 node_id、name、description、deps（前置节点列表）、actions（候选执行动作）。
3. deps 为空列表表示该节点没有前置依赖。
4. 拆解粒度适中，节点数控制在 4-8 个。
5. 每个节点的 actions 应提供 2-3 种不同的执行策略作为候选分支。

用户任务：
{user_task}

输出格式示例：
{{
  "nodes": [
    {{
      "node_id": "task_1",
      "name": "理解需求",
      "description": "分析用户目标，确定任务范围",
      "deps": [],
      "actions": [
        {{"action_id": "task_1_a1", "description": "详细分析", "prompt": "仔细阅读并逐条列出需求要点"}},
        {{"action_id": "task_1_a2", "description": "概括分析", "prompt": "提炼核心目标，忽略细节"}}
      ]
    }},
    {{
      "node_id": "task_2",
      "name": "检索资料",
      "description": "根据理解结果查找相关资料",
      "deps": ["task_1"],
      "actions": [
        {{"action_id": "task_2_a1", "description": "广泛检索", "prompt": "全面搜索相关资料"}},
        {{"action_id": "task_2_a2", "description": "精准检索", "prompt": "只搜索最相关的资料"}}
      ]
    }}
  ]
}}"""


class PlannerAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def plan(self, user_task: str) -> dict:
        """输入用户任务描述，返回包含 nodes 列表的 DAG 定义字典。"""
        prompt = PLANNER_PROMPT_TEMPLATE.format(user_task=user_task)
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": prompt},
        ]
        return self.llm.chat_json(messages)
