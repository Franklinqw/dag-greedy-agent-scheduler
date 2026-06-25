"""
贪心树搜索模块：在多个候选分支中选择最优分支。

采用加权评分公式，综合考虑质量、置信度、成本和时延。
"""

from config import QUALITY_WEIGHT, CONFIDENCE_WEIGHT, COST_WEIGHT, TIME_WEIGHT


class GreedyTreeSelector:
    def __init__(
        self,
        quality_weight=QUALITY_WEIGHT,
        confidence_weight=CONFIDENCE_WEIGHT,
        cost_weight=COST_WEIGHT,
        time_weight=TIME_WEIGHT,
    ):
        self.quality_weight = quality_weight
        self.confidence_weight = confidence_weight
        self.cost_weight = cost_weight
        self.time_weight = time_weight

    def calculate_score(self, result) -> float:
        """计算分支的综合得分（0~1 区间，越高越好）。"""
        return (
            self.quality_weight * result.quality_score
            + self.confidence_weight * result.confidence_score
            - self.cost_weight * max(result.cost_tokens / 1000, 0)
            - self.time_weight * min(result.latency / 10, 1.0)
        )

    def select_best(self, branch_results):
        """从分支结果列表中选出得分最高的，返回 (best_result, all_scored)。"""
        scored = [(self.calculate_score(r), r) for r in branch_results]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1], scored

    def get_second_best(self, scored_results) -> "BranchResult | None":
        """获取得分第二高的分支（用于回溯备选）。"""
        return scored_results[1][1] if len(scored_results) > 1 else None
