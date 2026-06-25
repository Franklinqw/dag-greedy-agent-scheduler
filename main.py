"""
项目主入口：组装所有组件并运行混合调度引擎。

用法：
    python main.py              # 使用 Planner Agent 自动生成 DAG 并运行
    python main.py --task code  # 运行代码修复示例任务（手写 DAG）
    python main.py --task report  # 运行报告生成示例任务
    python main.py --task data  # 运行数据分析示例任务
    python main.py --task code --no-backtrack  # 无回溯模式（纯 DAG 基线）
    python main.py --task code --linear  # 线性顺序执行模式（ReAct 基线）

默认使用本地 mock LLM，保证离线也能演示。
如果要调用远端模型，可加 --remote，并配置环境变量：
    $env:EDGEFN_API_KEY="你的API_KEY"
"""

import argparse
from llm.client import LLMClient
from agents.planner_agent import PlannerAgent
from agents.executor_agent import ExecutorAgent
from agents.critic_agent import CriticAgent
from scheduler.engine import HybridScheduler
from core.schema import TaskNode, TaskAction
from tasks.code_fix_task import build_code_fix_task
from tasks.report_task import build_report_task
from tasks.data_analysis_task import build_data_analysis_task


TASK_BUILDERS = {
    "code": ("代码修复", build_code_fix_task),
    "report": ("报告生成", build_report_task),
    "data": ("数据分析", build_data_analysis_task),
}


def build_llm(use_remote: bool) -> LLMClient:
    return LLMClient(use_mock=not use_remote)


def run_with_planner(user_task: str, max_parallel: int, score_threshold: float,
                     no_backtrack: bool, use_remote: bool):
    """使用 Planner Agent 自动拆解任务 → 运行混合调度引擎。"""
    llm = build_llm(use_remote)
    planner = PlannerAgent(llm)
    executor = ExecutorAgent(llm)
    critic = CriticAgent(llm)

    print(f"\n用户任务: {user_task}")
    print("Planner Agent 正在拆解任务...")

    plan = planner.plan(user_task)
    nodes = []
    for n in plan.get("nodes", []):
        actions = [
            TaskAction(a["action_id"], a["description"], a["prompt"])
            for a in n.get("actions", [])
        ]
        nodes.append(TaskNode(
            node_id=n["node_id"],
            name=n["name"],
            description=n["description"],
            deps=n.get("deps", []),
            actions=actions,
        ))

    print(f"已生成 {len(nodes)} 个 DAG 节点:")
    for node in nodes:
        print(f"  {node.node_id} ({node.name}) <- {node.deps}")

    # 如果 no_backtrack，将 score_threshold 设为 0 禁用回溯路径
    actual_threshold = 0.0 if no_backtrack else score_threshold
    scheduler = HybridScheduler(
        nodes=nodes,
        executor_agent=executor,
        critic_agent=critic,
        max_parallel=max_parallel,
        score_threshold=actual_threshold,
    )

    metrics = scheduler.run()
    final = scheduler.get_final_output()
    print("\n" + "=" * 60)
    print("最终输出:")
    print("=" * 60)
    print(final[:2000] if len(final) > 2000 else final)

    return metrics


def run_with_task(task_key: str, max_parallel: int, score_threshold: float,
                  no_backtrack: bool, linear: bool, use_remote: bool):
    """使用手写 DAG 运行指定任务。"""
    task_name, builder = TASK_BUILDERS[task_key]

    llm = build_llm(use_remote)
    executor = ExecutorAgent(llm)
    critic = CriticAgent(llm)
    nodes = builder()

    print(f"\n任务类型: {task_name}")
    print(f"模式: {'线性顺序' if linear else ('纯DAG无回溯' if no_backtrack else '混合调度(DAG+贪心搜索+回溯)')}")
    print(f"节点数: {len(nodes)}")
    for node in nodes:
        print(f"  {node.node_id} ({node.name}) <- {node.deps}")

    actual_threshold = 0.0 if no_backtrack else score_threshold

    if linear:
        metrics = run_linear(nodes, executor, critic, max_parallel)
    else:
        scheduler = HybridScheduler(
            nodes=nodes,
            executor_agent=executor,
            critic_agent=critic,
            max_parallel=max_parallel,
            score_threshold=actual_threshold,
        )
        metrics = scheduler.run()
        final = scheduler.get_final_output()
        print("\n" + "=" * 60)
        print("最终输出:")
        print("=" * 60)
        print(final[:2000] if len(final) > 2000 else final)

    return metrics


def run_linear(nodes, executor, critic, max_parallel):
    """线性顺序执行模式（ReAct 基线）：逐个节点顺序执行，无分支。"""
    from core.schema import NodeState, BranchResult
    from core.cache import CacheManager
    from core.metrics import MetricsCollector
    import time

    cache = CacheManager()
    metrics = MetricsCollector()

    print("\n>>> 线性执行模式 <<<")
    for node in nodes:
        print(f"\n--- 执行节点: {node.node_id} ({node.name}) ---")

        context = {dep: cache.get(dep) for dep in node.deps}
        action = node.actions[0] if node.actions else TaskAction("default", "默认", "执行该任务")

        start = time.perf_counter()
        output = executor.execute(node, action, context)
        latency = time.perf_counter() - start
        critic_result = critic.score(node, action, output)

        success = critic_result.get("success", False)
        node.state = NodeState.SUCCESS if success else NodeState.FAILED

        result = BranchResult(
            node_id=node.node_id,
            action_id=action.action_id,
            output=output,
            success=success,
            quality_score=critic_result.get("quality_score", 0.0),
            confidence_score=critic_result.get("confidence_score", 0.0),
            cost_tokens=len(output) // 3,
            latency=latency,
        )

        score = result.quality_score * 0.6 + result.confidence_score * 0.4
        metrics.record_branch(
            node.node_id, action.action_id, success, score, result.cost_tokens, latency
        )
        metrics.record_node(node.node_id, success, result.cost_tokens, latency, action.action_id)
        cache.set(node.node_id, output)
        print(f"  [{'OK' if success else 'FAIL'}] {node.node_id} q={result.quality_score:.2f}")

        if not success:
            print("  [线性模式] 节点失败，无法回溯，任务终止")
            break

    metrics.success = all(n.state == NodeState.SUCCESS for n in nodes)
    metrics.print_summary("线性模式完成")
    return metrics


def main():
    parser = argparse.ArgumentParser(description="DAG + 贪心树搜索 Agent 调度引擎")
    parser.add_argument("--task", choices=["code", "report", "data"],
                        help="选择手写 DAG 任务类型")
    parser.add_argument("--prompt", type=str, default="",
                        help="自定义任务描述（使用 Planner Agent 自动生成 DAG）")
    parser.add_argument("--max-parallel", type=int, default=3,
                        help="最大并行执行节点数")
    parser.add_argument("--threshold", type=float, default=0.6,
                        help="分支评分最低阈值")
    parser.add_argument("--no-backtrack", action="store_true",
                        help="禁用回溯机制（纯 DAG 并行基线）")
    parser.add_argument("--linear", action="store_true",
                        help="使用线性顺序执行（ReAct 基线）")
    parser.add_argument("--remote", action="store_true",
                        help="调用远端 LLM 接口；默认使用本地 mock")

    args = parser.parse_args()

    if args.prompt:
        run_with_planner(
            args.prompt, args.max_parallel, args.threshold, args.no_backtrack, args.remote
        )
    elif args.task:
        run_with_task(args.task, args.max_parallel, args.threshold,
                      args.no_backtrack, args.linear, args.remote)
    else:
        # 默认：运行代码修复任务 + Planner 演示
        print("未指定任务，默认运行手写代码修复任务（混合模式）。\n")
        print("提示: 使用 --task report / --task data 运行其他任务")
        print("      使用 --prompt '...' 自定义任务（Planner 自动生成 DAG）")
        print("      使用 --no-backtrack 测试纯 DAG 基线")
        print("      使用 --linear 测试线性顺序基线")
        print("      使用 --remote 调用远端模型")
        run_with_task("code", args.max_parallel, args.threshold,
                      args.no_backtrack, args.linear, args.remote)


if __name__ == "__main__":
    main()
