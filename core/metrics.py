"""
Runtime metrics used by the scheduler and demos.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List


@dataclass
class MetricsCollector:
    start_time: float = field(default_factory=time.perf_counter)
    total_tokens: int = 0
    total_llm_calls: int = 0
    node_results: List[dict] = field(default_factory=list)
    branch_results: List[dict] = field(default_factory=list)
    rollback_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    success: bool = False

    def record_branch(self, node_id: str, action_id: str, success: bool, score: float, tokens: int, latency: float):
        self.total_tokens += tokens
        self.total_llm_calls += 1
        self.branch_results.append(
            {
                "node_id": node_id,
                "action_id": action_id,
                "success": success,
                "score": score,
                "tokens": tokens,
                "latency": latency,
            }
        )

    def record_node(self, node_id: str, success: bool, tokens: int, latency: float, selected_action: str = ""):
        self.node_results.append(
            {
                "node_id": node_id,
                "success": success,
                "tokens": tokens,
                "latency": latency,
                "selected_action": selected_action,
            }
        )

    def record_rollback(self):
        self.rollback_count += 1

    def record_cache(self, hit: bool):
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    @property
    def elapsed(self) -> float:
        return time.perf_counter() - self.start_time

    @property
    def node_count(self) -> int:
        return len(self.node_results)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.node_results if r["success"])

    @property
    def branch_count(self) -> int:
        return len(self.branch_results)

    @property
    def branch_success_count(self) -> int:
        return sum(1 for r in self.branch_results if r["success"])

    @property
    def avg_node_latency(self) -> float:
        if not self.node_results:
            return 0.0
        return sum(r["latency"] for r in self.node_results) / len(self.node_results)

    @property
    def avg_branch_score(self) -> float:
        if not self.branch_results:
            return 0.0
        return sum(r["score"] for r in self.branch_results) / len(self.branch_results)

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    def summary(self) -> dict:
        return {
            "total_time_s": round(self.elapsed, 2),
            "total_tokens": self.total_tokens,
            "total_llm_calls": self.total_llm_calls,
            "node_count": self.node_count,
            "success_count": self.success_count,
            "branch_count": self.branch_count,
            "branch_success_count": self.branch_success_count,
            "rollback_count": self.rollback_count,
            "cache_hit_rate": round(self.cache_hit_rate, 3),
            "avg_node_latency_s": round(self.avg_node_latency, 3),
            "avg_branch_score": round(self.avg_branch_score, 3),
            "task_success": self.success,
        }

    def print_summary(self, title: str = "指标汇总"):
        s = self.summary()
        print(f"\n{'=' * 52}")
        print(f"  {title}")
        print(f"{'=' * 52}")
        print(f"  总耗时:          {s['total_time_s']}s")
        print(f"  Token 消耗:      {s['total_tokens']}")
        print(f"  LLM 调用次数:    {s['total_llm_calls']}")
        print(f"  完成节点数:      {s['node_count']}")
        print(f"  成功节点数:      {s['success_count']}")
        print(f"  分支执行数:      {s['branch_count']}")
        print(f"  成功分支数:      {s['branch_success_count']}")
        print(f"  平均节点耗时:    {s['avg_node_latency_s']}s")
        print(f"  平均分支得分:    {s['avg_branch_score']}")
        print(f"  回溯次数:        {s['rollback_count']}")
        print(f"  缓存命中率:      {s['cache_hit_rate']}")
        print(f"  任务成功:        {s['task_success']}")
        print(f"{'=' * 52}\n")
