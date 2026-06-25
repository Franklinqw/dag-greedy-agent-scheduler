"""
Small data-analysis demo task.
"""

from core.schema import TaskAction, TaskNode

DATA_SCENARIO = """
某门店一周销量如下：
周一 120，周二 132，周三 128，周四 150，周五 176，周六 210，周日 205。
任务目标：总结趋势，并给出两条经营建议。
""".strip()


def build_data_analysis_task() -> list[TaskNode]:
    return [
        TaskNode(
            node_id="inspect",
            name="观察数据",
            description="识别数据整体变化趋势",
            deps=[],
            actions=[
                TaskAction("inspect_a1", "基础观察", f"阅读数据并总结趋势：\n{DATA_SCENARIO}"),
                TaskAction("inspect_a2", "峰值观察", f"重点分析峰值和低谷：\n{DATA_SCENARIO}"),
            ],
        ),
        TaskNode(
            node_id="analyze",
            name="形成结论",
            description="提炼主要现象与原因假设",
            deps=["inspect"],
            actions=[
                TaskAction("analyze_a1", "简洁结论", "用两句话总结销量变化规律"),
                TaskAction("analyze_a2", "业务结论", "从营业日与周末差异解释趋势"),
            ],
        ),
        TaskNode(
            node_id="advice",
            name="给出建议",
            description="输出两条具体经营建议",
            deps=["analyze"],
            actions=[
                TaskAction("advice_a1", "促销建议", "给出面向平日低谷的促销建议"),
                TaskAction("advice_a2", "排班建议", "给出面向周末高峰的库存和排班建议"),
            ],
        ),
    ]
