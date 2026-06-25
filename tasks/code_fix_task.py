"""
Small code-fix demo task.
"""

from core.schema import TaskAction, TaskNode

CODE_FIX_SCENARIO = """
函数 divide(a, b) 在 b=0 时会直接报错。
任务目标：说明问题原因，给出修复思路，并写出简短测试建议。
""".strip()


def build_code_fix_task() -> list[TaskNode]:
    return [
        TaskNode(
            node_id="understand",
            name="理解问题",
            description="识别 bug 原因和影响",
            deps=[],
            actions=[
                TaskAction("understand_a1", "直接分析", f"分析以下问题：\n{CODE_FIX_SCENARIO}"),
                TaskAction("understand_a2", "异常分析", f"从异常处理角度分析以下问题：\n{CODE_FIX_SCENARIO}"),
            ],
        ),
        TaskNode(
            node_id="patch",
            name="提出修复",
            description="给出简洁修复方案",
            deps=["understand"],
            actions=[
                TaskAction("patch_a1", "最小修复", "给出最小改动方案，重点处理除零情况"),
                TaskAction("patch_a2", "稳健修复", "给出包含参数检查和错误提示的修复方案"),
            ],
        ),
        TaskNode(
            node_id="test",
            name="验证方案",
            description="给出两条测试建议",
            deps=["patch"],
            actions=[
                TaskAction("test_a1", "正常路径", "说明正常输入下应如何验证"),
                TaskAction("test_a2", "异常路径", "说明 b=0 时应如何验证"),
            ],
        ),
    ]
