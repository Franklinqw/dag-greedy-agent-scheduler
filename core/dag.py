"""
DAG 工具：依赖检查、拓扑排序、下游节点查找。
"""

from collections import defaultdict, deque
from typing import Dict, List, Set

from core.schema import TaskNode, NodeState


def topological_sort(nodes: List[TaskNode]) -> List[str]:
    """对节点列表进行拓扑排序，返回排序后的 node_id 列表。"""
    node_map = {n.node_id: n for n in nodes}
    in_degree = {n.node_id: len(n.deps) for n in nodes}

    # 构建反向邻接表：dep -> [children]
    children = defaultdict(list)
    for n in nodes:
        for dep in n.deps:
            children[dep].append(n.node_id)

    queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
    result = []

    while queue:
        nid = queue.popleft()
        result.append(nid)
        for child in children.get(nid, []):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if len(result) != len(nodes):
        raise ValueError("DAG 中存在循环依赖，拓扑排序失败")
    return result


def get_descendants(node_id: str, node_map: Dict[str, TaskNode]) -> Set[str]:
    """获取某个节点的所有下游节点（递归）。"""
    descendants: Set[str] = set()

    def dfs(current: str):
        for child_id, child in node_map.items():
            if current in child.deps and child_id not in descendants:
                descendants.add(child_id)
                dfs(child_id)

    dfs(node_id)
    return descendants


def get_ready_nodes(node_map: Dict[str, TaskNode], cache: Dict[str, str]) -> List[TaskNode]:
    """返回所有依赖已满足且尚未执行成功的就绪节点。"""
    ready = []
    for node in node_map.values():
        if node.state in (NodeState.SUCCESS, NodeState.RUNNING, NodeState.FAILED):
            continue
        deps_ok = all(dep in cache for dep in node.deps)
        if deps_ok:
            node.state = NodeState.READY
            ready.append(node)
    return ready


def all_done(node_map: Dict[str, TaskNode]) -> bool:
    """检查所有节点是否都已成功完成。"""
    return all(n.state == NodeState.SUCCESS for n in node_map.values())


def any_failed(node_map: Dict[str, TaskNode]) -> bool:
    """检查是否存在失败节点。"""
    return any(n.state == NodeState.FAILED for n in node_map.values())
