"""
Hybrid scheduler: DAG parallelism + multi-branch selection + local rollback.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

from config import MAX_PARALLEL, SCORE_THRESHOLD
from core.cache import CacheManager
from core.dag import all_done, get_ready_nodes
from core.metrics import MetricsCollector
from core.schema import BranchResult, NodeState, TaskAction, TaskNode
from scheduler.greedy_tree import GreedyTreeSelector
from scheduler.rollback import RollbackManager


class HybridScheduler:
    def __init__(
        self,
        nodes: List[TaskNode],
        executor_agent,
        critic_agent,
        max_parallel=MAX_PARALLEL,
        score_threshold=SCORE_THRESHOLD,
        branch_parallelism: int | None = None,
    ):
        self.node_map: Dict[str, TaskNode] = {n.node_id: n for n in nodes}
        self.executor = executor_agent
        self.critic = critic_agent
        self.max_parallel = max_parallel
        self.score_threshold = score_threshold
        self.branch_parallelism = branch_parallelism
        self.cache = CacheManager()
        self.selector = GreedyTreeSelector()
        self.branch_history: Dict[str, list] = {}
        self.metrics = MetricsCollector()

    def _build_context(self, node: TaskNode) -> dict:
        context = {}
        for dep in node.deps:
            hit = self.cache.has(dep)
            self.metrics.record_cache(hit)
            context[dep] = self.cache.get(dep)
        return context

    def _execute_action(self, node: TaskNode, action: TaskAction, context: dict) -> BranchResult:
        start = time.perf_counter()
        output = self.executor.execute(node, action, context)
        latency = time.perf_counter() - start
        critic_result = self.critic.score(node, action, output)
        return BranchResult(
            node_id=node.node_id,
            action_id=action.action_id,
            output=output,
            success=critic_result.get("success", False),
            quality_score=critic_result.get("quality_score", 0.0),
            confidence_score=critic_result.get("confidence_score", 0.0),
            cost_tokens=max(1, len(output) // 4),
            latency=latency,
            error_reason=critic_result.get("reason", ""),
        )

    def _execute_node(self, node: TaskNode) -> BranchResult:
        node.state = NodeState.RUNNING
        context = self._build_context(node)
        actions = node.actions or [TaskAction("default", "default", "execute the task")]

        branch_results: List[BranchResult] = []
        branch_workers = self.branch_parallelism or len(actions)
        branch_workers = max(1, min(branch_workers, len(actions)))

        if branch_workers == 1:
            for action in actions:
                branch_results.append(self._execute_action(node, action, context))
        else:
            with ThreadPoolExecutor(max_workers=branch_workers) as pool:
                futures = [pool.submit(self._execute_action, node, action, context) for action in actions]
                for future in as_completed(futures):
                    branch_results.append(future.result())

        best_result, scored_results = self.selector.select_best(branch_results)
        self.branch_history[node.node_id] = scored_results

        for score, result in scored_results:
            self.metrics.record_branch(
                node_id=node.node_id,
                action_id=result.action_id,
                success=result.success,
                score=score,
                tokens=result.cost_tokens,
                latency=result.latency,
            )

        best_score = self.selector.calculate_score(best_result)
        if not best_result.success or best_score < self.score_threshold:
            node.state = NodeState.FAILED
            self.metrics.record_node(
                node.node_id,
                False,
                best_result.cost_tokens,
                best_result.latency,
                best_result.action_id,
            )
            return best_result

        node.state = NodeState.SUCCESS
        node.selected_action_id = best_result.action_id
        self.cache.set(node.node_id, best_result.output)
        self.metrics.record_node(
            node.node_id,
            True,
            best_result.cost_tokens,
            best_result.latency,
            best_result.action_id,
        )
        return best_result

    def _try_rollback(self, failed_node: TaskNode) -> bool:
        rollback_mgr = RollbackManager(self.node_map, self.cache, self.branch_history)
        if not rollback_mgr.can_rollback(failed_node.node_id):
            return False

        scored = self.branch_history[failed_node.node_id]
        second_best = self.selector.get_second_best(scored)
        if second_best is None:
            return False

        second_score = self.selector.calculate_score(second_best)
        if not second_best.success or second_score < self.score_threshold:
            return False

        affected = rollback_mgr.rollback_from(failed_node.node_id)
        self.metrics.record_rollback()

        failed_node.state = NodeState.SUCCESS
        failed_node.selected_action_id = second_best.action_id
        self.cache.set(failed_node.node_id, second_best.output)
        self.metrics.record_node(
            failed_node.node_id,
            True,
            second_best.cost_tokens,
            second_best.latency,
            second_best.action_id,
        )
        print(
            f"  [rollback] node={failed_node.node_id} -> {second_best.action_id}, "
            f"cleared={sorted(affected)}"
        )
        return True

    def run(self) -> MetricsCollector:
        print(f"\n{'=' * 60}")
        print(
            f"  Hybrid Scheduler Start (max_parallel={self.max_parallel}, "
            f"threshold={self.score_threshold})"
        )
        print(f"{'=' * 60}")

        round_num = 0
        while True:
            ready_nodes = get_ready_nodes(self.node_map, self.cache)
            if not ready_nodes:
                break

            round_num += 1
            batch = ready_nodes[: self.max_parallel]
            print(f"\n--- round {round_num}: {len(batch)} ready node(s) {[n.node_id for n in batch]} ---")

            with ThreadPoolExecutor(max_workers=len(batch)) as pool:
                futures = {pool.submit(self._execute_node, node): node for node in batch}
                for future in as_completed(futures):
                    node = futures[future]
                    result = future.result()
                    score = self.selector.calculate_score(result)
                    status = "OK" if node.state == NodeState.SUCCESS else "FAIL"
                    print(
                        f"  [{status}] {node.node_id} ({node.name}) "
                        f"action={result.action_id} score={score:.3f}"
                    )

            for node in batch:
                if node.state == NodeState.FAILED and not self._try_rollback(node):
                    print(f"  [stop] node {node.node_id} failed and cannot rollback")
                    self.metrics.success = False
                    self.metrics.print_summary("任务失败")
                    return self.metrics

            if all_done(self.node_map):
                break

        self.metrics.success = all_done(self.node_map)
        self.metrics.print_summary("任务完成")
        return self.metrics

    def get_final_output(self) -> str:
        has_successor = set()
        for node in self.node_map.values():
            for dep in node.deps:
                has_successor.add(dep)

        leaf_nodes = [
            node_id
            for node_id in self.node_map
            if node_id not in has_successor and self.cache.has(node_id)
        ]

        outputs = []
        for node_id in leaf_nodes:
            node = self.node_map[node_id]
            outputs.append(f"[{node.name}]\n{self.cache.get(node_id)}")
        return "\n\n".join(outputs) if outputs else "(no output)"
