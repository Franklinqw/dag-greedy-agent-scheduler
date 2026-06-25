可以。你现在的模型调用方式是标准的 `requests.post()` 调用大模型接口，所以你的项目可以设计成一个**“DAG调度器 + LLM Agent调用层 + 贪心树搜索层 + 缓存回溯层”**的工程结构。

下面我按你的论文思路，规划一个比较适合毕业论文实现的代码架构。

---

# 1. 项目整体目标

你的项目不需要一开始就做成很复杂的工业级系统，而是应该实现一个**可运行、可展示、可实验对比**的原型系统。

核心目标是实现：

```text
用户复杂任务
   ↓
Planner Agent 拆解任务
   ↓
生成 DAG 任务图
   ↓
调度器并行执行就绪节点
   ↓
每个节点生成多个候选执行分支
   ↓
Critic Agent 对分支评分
   ↓
贪心选择最优分支
   ↓
如果下游失败，则局部回溯
   ↓
复用无关节点缓存
   ↓
输出最终结果与实验指标
```

---

# 2. 推荐项目目录结构

```text
dag_greedy_agent/
│
├── main.py                         # 项目入口
├── config.py                       # API Key、模型名称、并发数等配置
│
├── llm/
│   └── client.py                   # 封装 DeepSeek-V4-Pro 调用
│
├── core/
│   ├── schema.py                   # TaskNode、Action、Result 等数据结构
│   ├── dag.py                      # DAG构建、依赖检查、拓扑排序
│   ├── cache.py                    # 缓存管理
│   └── metrics.py                  # Token、时间、成功率等统计
│
├── agents/
│   ├── planner_agent.py            # 将复杂任务拆成DAG
│   ├── executor_agent.py           # 执行具体子任务
│   ├── critic_agent.py             # 对候选分支打分
│   └── verifier_agent.py           # 检查结果是否正确，定位错误节点
│
├── scheduler/
│   ├── engine.py                   # 主调度引擎
│   ├── greedy_tree.py              # 贪心树搜索分支选择
│   └── rollback.py                 # 局部回溯机制
│
├── tasks/
│   ├── code_fix_task.py            # 示例任务1：代码修复
│   ├── report_task.py              # 示例任务2：论文/报告生成
│   └── data_analysis_task.py       # 示例任务3：数据分析
│
└── experiments/
    ├── run_baseline.py             # 线性执行 / 纯DAG / 本文方法对比
    └── run_demo.py                 # 演示实验
```

---

# 3. 模型调用层设计

你现在的调用方式应该封装成一个统一的 `LLMClient`，后续所有 Agent 都通过它调用模型。

## `llm/client.py`

```python
import os
import requests


class LLMClient:
    def __init__(self):
        self.url = "https://api.edgefn.net/v1/chat/completions"
        self.api_key = os.getenv("EDGEFN_API_KEY")
        self.model = "DeepSeek-V4-Pro"

        if not self.api_key:
            raise ValueError("请先设置环境变量 EDGEFN_API_KEY")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat(self, messages, temperature=0.3):
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }

        response = requests.post(
            self.url,
            headers=self.headers,
            json=data,
            timeout=60
        )

        response.raise_for_status()
        result = response.json()

        return result["choices"][0]["message"]["content"]
```

运行前设置 API Key：

```bash
export EDGEFN_API_KEY="你的API_KEY"
```

Windows PowerShell：

```bash
$env:EDGEFN_API_KEY="你的API_KEY"
```

---

# 4. 核心数据结构设计

## `core/schema.py`

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeState(str, Enum):
    WAITING = "waiting"
    READY = "ready"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class TaskAction:
    action_id: str
    description: str
    prompt: str


@dataclass
class TaskNode:
    node_id: str
    name: str
    description: str
    deps: List[str]
    actions: List[TaskAction] = field(default_factory=list)
    state: NodeState = NodeState.WAITING
    selected_action_id: Optional[str] = None
    retry_count: int = 0


@dataclass
class BranchResult:
    node_id: str
    action_id: str
    output: str
    success: bool
    quality_score: float
    confidence_score: float
    cost_tokens: int = 0
    latency: float = 0.0
    error_reason: str = ""
    blame_node: Optional[str] = None
```

---

# 5. Planner Agent：把复杂任务拆成DAG

Planner Agent 的作用是：输入用户复杂任务，输出结构化 DAG。

## `agents/planner_agent.py`

```python
import json
from llm.client import LLMClient


class PlannerAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def plan(self, user_task: str) -> dict:
        prompt = f"""
你是一个任务规划智能体。请将用户任务拆解为DAG任务图。

要求：
1. 输出JSON格式。
2. 每个节点包含 node_id、name、description、deps。
3. deps表示该节点依赖的前置节点。
4. 不要输出多余解释。

用户任务：
{user_task}

输出格式示例：
{{
  "nodes": [
    {{
      "node_id": "task_1",
      "name": "理解需求",
      "description": "分析用户目标",
      "deps": []
    }},
    {{
      "node_id": "task_2",
      "name": "检索资料",
      "description": "查找相关信息",
      "deps": ["task_1"]
    }}
  ]
}}
"""

        content = self.llm.chat([
            {"role": "system", "content": "你是一个擅长任务拆解和DAG规划的智能体。"},
            {"role": "user", "content": prompt}
        ])

        return json.loads(content)
```

---

# 6. Executor Agent：执行具体节点

每个节点不是只执行一次，而是生成多个候选分支。例如一个检索节点可以生成 3 种检索策略。

## `agents/executor_agent.py`

```python
from llm.client import LLMClient


class ExecutorAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def execute(self, node, action, context: dict) -> str:
        prompt = f"""
你是一个任务执行智能体。

当前任务节点：
节点名称：{node.name}
节点描述：{node.description}

当前执行动作：
{action.description}

前置节点上下文：
{context}

请完成该子任务，并输出该节点的执行结果。
"""

        return self.llm.chat([
            {"role": "system", "content": "你是一个可靠的Agent执行器。"},
            {"role": "user", "content": prompt}
        ])
```

---

# 7. Critic Agent：给候选分支打分

Critic Agent 对每个候选结果评分，输出质量分和置信度。

## `agents/critic_agent.py`

```python
import json
from llm.client import LLMClient


class CriticAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def score(self, node, action, output: str) -> dict:
        prompt = f"""
你是一个结果评价智能体。请评价下面任务执行结果。

任务节点：
{node.name}
{node.description}

执行动作：
{action.description}

执行结果：
{output}

请从以下维度评分：
1. quality_score：结果质量，0到1之间
2. confidence_score：可信度，0到1之间
3. success：是否成功，true或false
4. reason：简要原因

只输出JSON，不要输出解释。

示例：
{{
  "quality_score": 0.85,
  "confidence_score": 0.80,
  "success": true,
  "reason": "结果完整且符合任务要求"
}}
"""

        content = self.llm.chat([
            {"role": "system", "content": "你是一个严格的任务结果评价器。"},
            {"role": "user", "content": prompt}
        ])

        return json.loads(content)
```

---

# 8. 贪心树搜索模块

这个模块负责：多个候选分支中选择当前最优分支。

## `scheduler/greedy_tree.py`

```python
class GreedyTreeSelector:
    def __init__(
        self,
        quality_weight=0.5,
        confidence_weight=0.4,
        cost_weight=0.05,
        time_weight=0.05
    ):
        self.quality_weight = quality_weight
        self.confidence_weight = confidence_weight
        self.cost_weight = cost_weight
        self.time_weight = time_weight

    def calculate_score(self, result):
        return (
            self.quality_weight * result.quality_score
            + self.confidence_weight * result.confidence_score
            - self.cost_weight * result.cost_tokens / 1000
            - self.time_weight * result.latency
        )

    def select_best(self, branch_results):
        scored = []

        for result in branch_results:
            score = self.calculate_score(result)
            scored.append((score, result))

        scored.sort(key=lambda x: x[0], reverse=True)

        return scored[0][1], scored
```

---

# 9. DAG调度引擎设计

调度器负责：

1. 找到所有就绪节点
2. 并行执行就绪节点
3. 每个节点生成多个动作分支
4. 让 Critic 打分
5. 贪心选择最优分支
6. 缓存结果
7. 失败时触发回溯

## `scheduler/engine.py` 核心思路

```python
import time
import asyncio
from core.schema import NodeState, BranchResult
from scheduler.greedy_tree import GreedyTreeSelector


class HybridScheduler:
    def __init__(
        self,
        nodes,
        executor_agent,
        critic_agent,
        max_parallel=3,
        branch_num=3,
        score_threshold=0.6
    ):
        self.nodes = {node.node_id: node for node in nodes}
        self.executor = executor_agent
        self.critic = critic_agent
        self.selector = GreedyTreeSelector()

        self.max_parallel = max_parallel
        self.branch_num = branch_num
        self.score_threshold = score_threshold

        self.cache = {}
        self.branch_history = {}
        self.failed_nodes = set()

    def get_ready_nodes(self):
        ready = []

        for node in self.nodes.values():
            if node.state in [NodeState.SUCCESS, NodeState.RUNNING]:
                continue

            deps_success = all(dep in self.cache for dep in node.deps)

            if deps_success:
                node.state = NodeState.READY
                ready.append(node)

        return ready

    def build_context(self, node):
        return {
            dep_id: self.cache[dep_id]
            for dep_id in node.deps
            if dep_id in self.cache
        }

    async def execute_node(self, node):
        node.state = NodeState.RUNNING
        context = self.build_context(node)

        branch_results = []

        for action in node.actions:
            start = time.time()

            output = await asyncio.to_thread(
                self.executor.execute,
                node,
                action,
                context
            )

            latency = time.time() - start

            critic_result = await asyncio.to_thread(
                self.critic.score,
                node,
                action,
                output
            )

            result = BranchResult(
                node_id=node.node_id,
                action_id=action.action_id,
                output=output,
                success=critic_result["success"],
                quality_score=critic_result["quality_score"],
                confidence_score=critic_result["confidence_score"],
                latency=latency,
                error_reason=critic_result.get("reason", "")
            )

            branch_results.append(result)

        best_result, scored_results = self.selector.select_best(branch_results)

        self.branch_history[node.node_id] = scored_results

        best_score = self.selector.calculate_score(best_result)

        if not best_result.success or best_score < self.score_threshold:
            node.state = NodeState.FAILED
            return best_result

        node.state = NodeState.SUCCESS
        node.selected_action_id = best_result.action_id
        self.cache[node.node_id] = best_result.output

        return best_result

    async def run(self):
        while True:
            ready_nodes = self.get_ready_nodes()

            if not ready_nodes:
                break

            batch = ready_nodes[:self.max_parallel]

            results = await asyncio.gather(
                *[self.execute_node(node) for node in batch]
            )

            for result in results:
                if not result.success:
                    self.failed_nodes.add(result.node_id)
                    return False

            if all(node.state == NodeState.SUCCESS for node in self.nodes.values()):
                return True

        return all(node.state == NodeState.SUCCESS for node in self.nodes.values())
```

---

# 10. 局部回溯模块设计

回溯的核心不是重启整个任务，而是：

```text
失败节点
 ↓
找到其依赖来源
 ↓
回滚相关子图
 ↓
保留无关缓存
 ↓
选择上游节点的次优分支重新执行
```

## `scheduler/rollback.py`

```python
class RollbackManager:
    def __init__(self, nodes, cache, branch_history):
        self.nodes = nodes
        self.cache = cache
        self.branch_history = branch_history

    def get_descendants(self, node_id):
        descendants = set()

        def dfs(current):
            for child_id, child in self.nodes.items():
                if current in child.deps:
                    descendants.add(child_id)
                    dfs(child_id)

        dfs(node_id)
        return descendants

    def rollback_from(self, blame_node_id):
        affected = self.get_descendants(blame_node_id)
        affected.add(blame_node_id)

        for node_id in affected:
            node = self.nodes[node_id]
            node.state = "waiting"
            node.selected_action_id = None

            if node_id in self.cache:
                del self.cache[node_id]

        return affected
```

---

# 11. 需要设定的几个示例任务

你的论文项目建议至少设置 3 类任务，方便实验对比。

---

## 任务一：多文件代码修复任务

适合体现“下游测试失败 → 回溯到代码修改节点”。

```text
用户任务：
修复用户登录接口中 token 过期后无法自动刷新的问题。

DAG节点：
1. understand_issue：理解问题
2. locate_files：定位相关文件
3. analyze_logic：分析 token 刷新逻辑
4. patch_code：生成修复补丁
5. run_tests：运行测试
6. summarize_fix：总结修复结果

依赖关系：
understand_issue → locate_files
locate_files → analyze_logic
analyze_logic → patch_code
patch_code → run_tests
run_tests → summarize_fix
```

每个节点可以设计多个候选动作：

```text
locate_files:
- 快速定位 auth.py
- 全局搜索 token 相关文件
- 根据调用链定位 service 层文件

patch_code:
- 最小修改策略
- 稳健修改策略
- 重构式修改策略
```

---

## 任务二：长篇论文/报告生成任务

适合体现“并行写章节 + 缓存复用”。

```text
用户任务：
生成一篇关于 DAG 与贪心树搜索的 Agent 任务调度研究报告。

DAG节点：
1. collect_literature：收集相关文献
2. build_outline：生成大纲
3. write_background：写研究背景
4. write_method：写方法章节
5. write_experiment：写实验设计
6. merge_report：合并全文
7. polish_report：润色全文

依赖关系：
collect_literature → build_outline
build_outline → write_background
build_outline → write_method
build_outline → write_experiment
write_background → merge_report
write_method → merge_report
write_experiment → merge_report
merge_report → polish_report
```

并行点：

```text
write_background、write_method、write_experiment 可以并行执行
```

回溯点：

```text
如果 merge_report 发现 method 章节质量不足，只回溯 write_method，不重写 background 和 experiment。
```

---

## 任务三：复杂数据分析任务

适合体现“工具调用 + 多路径选择 + 结果验证”。

```text
用户任务：
分析某电商平台用户行为数据，找出影响复购率的主要因素。

DAG节点：
1. load_data：读取数据
2. clean_data：清洗数据
3. feature_engineering：构建特征
4. statistical_analysis：统计分析
5. model_training：训练预测模型
6. interpret_result：解释结果
7. generate_report：生成分析报告

依赖关系：
load_data → clean_data
clean_data → feature_engineering
feature_engineering → statistical_analysis
feature_engineering → model_training
statistical_analysis → interpret_result
model_training → interpret_result
interpret_result → generate_report
```

候选动作示例：

```text
clean_data:
- 删除缺失值
- 均值填充
- 基于规则修复异常值

model_training:
- 逻辑回归
- 随机森林
- XGBoost

interpret_result:
- 基于统计显著性解释
- 基于特征重要性解释
- 综合解释
```

---

# 12. 主程序入口设计

## `main.py`

```python
import asyncio

from llm.client import LLMClient
from agents.planner_agent import PlannerAgent
from agents.executor_agent import ExecutorAgent
from agents.critic_agent import CriticAgent
from scheduler.engine import HybridScheduler

from tasks.report_task import build_report_task


async def main():
    llm = LLMClient()

    executor = ExecutorAgent(llm)
    critic = CriticAgent(llm)

    # 先用手写DAG，方便论文实验稳定复现
    nodes = build_report_task()

    scheduler = HybridScheduler(
        nodes=nodes,
        executor_agent=executor,
        critic_agent=critic,
        max_parallel=3,
        branch_num=3,
        score_threshold=0.6
    )

    success = await scheduler.run()

    print("任务是否成功：", success)
    print("缓存节点：", scheduler.cache.keys())


if __name__ == "__main__":
    asyncio.run(main())
```

---

# 13. 推荐开发顺序

不要一上来就做全自动 Planner。建议按下面顺序开发，最稳：

## 第一阶段：手写DAG版本

先手动写好几个任务DAG，例如代码修复、论文生成、数据分析。

目标：

```text
验证 DAG 并行执行 + 多分支选择 + 缓存机制
```

---

## 第二阶段：加入真实模型调用

把 Executor Agent 和 Critic Agent 接入你的接口：

```python
https://api.edgefn.net/v1/chat/completions
```

目标：

```text
让每个节点真实调用 DeepSeek-V4-Pro 生成结果和评分
```

---

## 第三阶段：加入局部回溯

实现：

```text
下游失败 → 定位 blame_node → 回滚受影响子图 → 复用无关缓存
```

目标：

```text
证明本文方法比全局重启节省Token和时间
```

---

## 第四阶段：加入自动Planner

让模型根据用户任务自动生成DAG。

目标：

```text
实现从自然语言任务到DAG调度的完整闭环
```

---

## 第五阶段：做实验对比

至少实现三种模式：

```text
1. Linear Mode：线性顺序执行
2. DAG Mode：只做DAG并行，不做回溯
3. Hybrid Mode：DAG + 贪心树搜索 + 局部回溯
```

对比指标：

```text
任务成功率
平均执行时间
Token消耗
回溯次数
缓存命中率
失败恢复成功率
```

---

# 14. 你的论文代码核心卖点

你的代码实现一定要突出这几个地方：

| 论文创新点     | 代码体现                                   |
| -------------- | ------------------------------------------ |
| DAG空间并发性  | `get_ready_nodes()`+`asyncio.gather()` |
| 贪心树搜索     | `GreedyTreeSelector.select_best()`       |
| 多分支候选动作 | `TaskAction`列表                         |
| Critic评分     | `CriticAgent.score()`                    |
| 局部回溯       | `RollbackManager.rollback_from()`        |
| 缓存复用       | `self.cache`                             |
| 防止无限重试   | `retry_count`/`max_retry`              |
| 成本控制       | `cost_tokens`/`latency`统计            |

---

最终建议：你先不要让 Planner 自动生成DAG，而是先 **手写3个标准任务DAG** 。这样实验更稳定、论文更容易写。等核心调度器跑通之后，再把 Planner Agent 接进去，作为系统增强模块。
