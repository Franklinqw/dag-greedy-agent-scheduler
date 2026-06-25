"""
Demo task: creative content generation.
"""

from core.schema import TaskAction, TaskNode


CREATIVE_BRIEF = """
创作一篇科幻短文，主题是“一个会记忆失败路径的城市调度系统”，
风格要求兼具技术感与文学感，长度控制在 300 字左右。
""".strip()


def build_creative_writing_task() -> list[TaskNode]:
    return [
        TaskNode(
            node_id="theme",
            name="提炼主题",
            description="提炼核心意象、叙事目标和情绪基调",
            deps=[],
            actions=[
                TaskAction(
                    "theme_a1",
                    "文学提炼",
                    f"请提炼以下创作需求中的主题、意象和情绪基调：\n{CREATIVE_BRIEF}",
                ),
                TaskAction(
                    "theme_a2",
                    "设定提炼",
                    f"请从世界观、主角和冲突三个维度拆解以下创作需求：\n{CREATIVE_BRIEF}",
                ),
            ],
        ),
        TaskNode(
            node_id="outline",
            name="生成提纲",
            description="设计开端、转折和结尾",
            deps=["theme"],
            actions=[
                TaskAction("outline_a1", "三段式提纲", "生成开端、发展、结尾三段式提纲"),
                TaskAction("outline_a2", "冲突驱动提纲", "突出系统失败记忆与城市恢复之间的冲突"),
            ],
        ),
        TaskNode(
            node_id="draft",
            name="生成初稿",
            description="创作 300 字左右的短文初稿",
            deps=["outline"],
            actions=[
                TaskAction("draft_a1", "偏文学", "写得更有画面感和比喻"),
                TaskAction("draft_a2", "偏科幻", "写得更强调系统设定和未来城市细节"),
            ],
        ),
        TaskNode(
            node_id="polish",
            name="润色成文",
            description="统一语言风格并增强结尾力度",
            deps=["draft"],
            actions=[
                TaskAction("polish_a1", "语言润色", "提升流畅度，保留意象"),
                TaskAction("polish_a2", "结尾强化", "增强结尾的余味和主题呼应"),
            ],
        ),
    ]
