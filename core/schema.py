"""
核心数据结构：TaskNode、BranchResult 等。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeState(str, Enum):
    WAITING = "waiting"      # 等待依赖就绪
    READY = "ready"          # 依赖已满足，可被调度
    RUNNING = "running"      # 正在执行
    SUCCESS = "success"      # 执行成功
    FAILED = "failed"        # 执行失败


@dataclass
class TaskAction:
    """节点的一个候选执行动作。"""
    action_id: str
    description: str
    prompt: str                  # 给 Executor 的具体指令


@dataclass
class TaskNode:
    """DAG 中的一个任务节点。"""
    node_id: str
    name: str
    description: str
    deps: List[str] = field(default_factory=list)                # 前置依赖节点 ID
    actions: List[TaskAction] = field(default_factory=list)      # 候选执行动作
    state: NodeState = NodeState.WAITING
    selected_action_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class BranchResult:
    """一个候选分支的执行结果。"""
    node_id: str
    action_id: str
    output: str
    success: bool
    quality_score: float
    confidence_score: float
    cost_tokens: int = 0
    latency: float = 0.0
    error_reason: str = ""
    blame_node: Optional[str] = None   # 失败时，追溯到的问题节点 ID
