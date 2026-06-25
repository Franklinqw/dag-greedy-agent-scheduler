"""
Small report-generation demo task.
"""

from core.schema import TaskAction, TaskNode

REPORT_TOPIC = "写一段简短说明，介绍 DAG 调度为什么比纯串行执行更高效。"


def build_report_task() -> list[TaskNode]:
    return [
        TaskNode(
            node_id="collect",
            name="提炼要点",
            description="提炼主题中的核心概念和目标",
            deps=[],
            actions=[
                TaskAction("collect_a1", "简要提炼", f"请用3个要点概括主题：{REPORT_TOPIC}"),
                TaskAction("collect_a2", "对比提炼", f"请从串行与并行对比角度概括主题：{REPORT_TOPIC}"),
            ],
        ),
        TaskNode(
            node_id="draft",
            name="生成初稿",
            description="写出一段 120 字以内的说明文字",
            deps=["collect"],
            actions=[
                TaskAction("draft_a1", "学术风格", "写成课程论文摘要式说明"),
                TaskAction("draft_a2", "口语风格", "写成答辩时可直接朗读的说明"),
            ],
        ),
        TaskNode(
            node_id="polish",
            name="润色结果",
            description="统一措辞，让结果更自然",
            deps=["draft"],
            actions=[
                TaskAction("polish_a1", "轻量润色", "只修正语病并压缩长度"),
                TaskAction("polish_a2", "增强逻辑", "补上因果关系并统一术语"),
            ],
        ),
    ]
