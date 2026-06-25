"""
缓存管理器：存储节点执行结果，支持局部回滚时保留无关缓存。
"""

from typing import Dict, Set


class CacheManager:
    def __init__(self):
        self._store: Dict[str, str] = {}  # node_id -> output

    def get(self, node_id: str) -> str:
        return self._store.get(node_id, "")

    def set(self, node_id: str, output: str):
        self._store[node_id] = output

    def has(self, node_id: str) -> bool:
        return node_id in self._store

    def remove(self, node_id: str):
        self._store.pop(node_id, None)

    def remove_batch(self, node_ids: Set[str]):
        for nid in node_ids:
            self.remove(nid)

    def keys(self):
        return self._store.keys()

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._store

    def __repr__(self):
        return f"CacheManager(keys={list(self._store.keys())})"
