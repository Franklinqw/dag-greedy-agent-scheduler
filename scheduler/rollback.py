"""
局部回溯管理器：下游失败时精准回滚，保留无关缓存。

核心逻辑：
  失败节点 → 反向追溯依赖链 → 回滚受影响子图 → 保留无关缓存 → 选择上游次优分支重试
"""

from typing import Dict, Set

from config import MAX_ROLLBACK_DEPTH
from core.schema import TaskNode, NodeState
from core.dag import get_descendants


class RollbackManager:
    def __init__(self, nodes: Dict[str, TaskNode], cache, branch_history: dict):
        self.nodes = nodes
        self.cache = cache
        self.branch_history = branch_history  # node_id -> [(score, BranchResult), ...]
        self.rollback_chain: list = []  # 回溯链记录

    def rollback_from(self, blame_node_id: str) -> Set[str]:
        """
        从 blame_node_id 出发，回滚所有下游受影响节点（含自身）。
        返回受影响的节点 ID 集合。
        """
        affected = get_descendants(blame_node_id, self.nodes)
        affected.add(blame_node_id)

        for node_id in affected:
            node = self.nodes[node_id]
            node.state = NodeState.WAITING
            node.selected_action_id = None
            node.retry_count += 1

            if node_id in self.cache:
                self.cache.remove(node_id)

        self.rollback_chain.append({
            "blame": blame_node_id,
            "affected": list(affected),
        })
        return affected

    def can_retry(self, node_id: str) -> bool:
        """检查节点是否还有重试次数。"""
        node = self.nodes.get(node_id)
        return node is not None and node.retry_count < node.max_retries

    def can_rollback(self, blame_node_id: str) -> bool:
        """检查是否满足回溯条件（有次优分支 + 未超回溯深度）。"""
        if len(self.rollback_chain) >= MAX_ROLLBACK_DEPTH:
            return False
        if blame_node_id not in self.branch_history:
            return False
        scored = self.branch_history[blame_node_id]
        return len(scored) >= 2  # 至少要有备选分支
