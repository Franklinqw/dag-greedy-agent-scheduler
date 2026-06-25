"""
Demo task: complex code generation.
"""

from core.schema import TaskAction, TaskNode


CODE_GENERATION_BRIEF = """
设计一个 Python 命令行程序，用于读取学生成绩列表，
计算平均分、最高分、最低分，并按分数从高到低输出排行榜。
要求说明模块划分、核心函数设计和测试要点。
""".strip()


def build_code_generation_task() -> list[TaskNode]:
    return [
        TaskNode(
            node_id="requirements",
            name="分析需求",
            description="提炼程序输入、输出和功能要求",
            deps=[],
            actions=[
                TaskAction(
                    "requirements_a1",
                    "结构化分析",
                    f"请结构化分析以下代码生成需求，列出输入、输出、核心功能：\n{CODE_GENERATION_BRIEF}",
                ),
                TaskAction(
                    "requirements_a2",
                    "实现导向分析",
                    f"请从工程实现角度拆解以下代码需求，重点说明模块和函数职责：\n{CODE_GENERATION_BRIEF}",
                ),
            ],
        ),
        TaskNode(
            node_id="design",
            name="设计方案",
            description="给出程序架构、函数划分和数据流",
            deps=["requirements"],
            actions=[
                TaskAction("design_a1", "模块设计", "给出文件结构、函数列表和调用流程"),
                TaskAction("design_a2", "接口设计", "给出主要函数签名、输入输出和错误处理方案"),
            ],
        ),
        TaskNode(
            node_id="implement",
            name="生成代码",
            description="生成一份可直接运行的 Python 示例代码",
            deps=["design"],
            actions=[
                TaskAction("implement_a1", "完整实现", "输出完整 Python 代码，包含主函数"),
                TaskAction("implement_a2", "简洁实现", "输出精简但完整的 Python 代码，突出核心逻辑"),
            ],
        ),
        TaskNode(
            node_id="validate",
            name="验证结果",
            description="检查代码完整性并给出测试建议",
            deps=["implement"],
            actions=[
                TaskAction("validate_a1", "功能验证", "检查功能是否覆盖需求，并给出两条测试建议"),
                TaskAction("validate_a2", "边界验证", "重点检查空列表、重复分数等边界情况"),
            ],
        ),
    ]
