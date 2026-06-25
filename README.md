# DAG + 贪心树搜索 Agent 调度引擎

基于 DAG 并行执行、贪心树搜索选择和局部回溯机制的混合 Agent 调度引擎。

## 核心特性

- **Planner Agent**：自动拆解用户任务并生成 DAG
- **Executor Agent**：执行任务节点的候选动作
- **Critic Agent**：评估执行质量，提供质量分和置信度分
- **Hybrid Scheduler**：DAG 并行 + 贪心树搜索 + 局部回溯
- **三种执行模式**：混合调度、纯 DAG、线性顺序

## 项目结构

```
├── agents/              # Agent 实现
│   ├── planner_agent.py   # 任务拆解与 DAG 生成
│   ├── executor_agent.py  # 任务执行
│   └── critic_agent.py    # 结果评估
├── core/                # 核心数据结构
│   ├── schema.py          # TaskNode、BranchResult 等
│   ├── dag.py             # DAG 拓扑排序与就绪检测
│   ├── cache.py           # 结果缓存
│   └── metrics.py         # 指标收集
├── scheduler/           # 调度引擎
│   ├── engine.py          # HybridScheduler 主类
│   ├── greedy_tree.py     # 贪心树搜索选择器
│   └── rollback.py        # 回溯管理器
├── tasks/               # 预定义任务 DAG
│   ├── code_fix_task.py       # 代码修复任务
│   ├── report_task.py         # 报告生成任务
│   └── data_analysis_task.py  # 数据分析任务
├── llm/                 # LLM 客户端
│   └── client.py          # Mock/Remote LLM 封装
├── main.py              # 主入口
└── config.py            # 全局配置
```

## 快速开始

### 环境要求

- Python 3.10+

### 运行方式

```bash
# 默认：运行代码修复任务（混合调度模式）
python main.py

# 运行指定任务
python main.py --task code      # 代码修复
python main.py --task report    # 报告生成
python main.py --task data      # 数据分析

# 使用 Planner Agent 自动生成 DAG
python main.py --prompt "帮我分析销售数据并生成报告"

# 纯 DAG 模式（无回溯）
python main.py --task code --no-backtrack

# 线性顺序模式（ReAct 基线）
python main.py --task code --linear

# 调用远端 LLM（需配置 API Key）
python main.py --task code --remote
```

### 配置远端模型

```bash
# Windows PowerShell
$env:EDGEFN_API_KEY="你的API_KEY"
python main.py --remote
```

## 执行模式对比

| 模式 | 并行执行 | 分支选择 | 回溯机制 | 适用场景 |
|------|---------|---------|---------|---------|
| 混合调度 | ✓ | ✓ | ✓ | 默认推荐，平衡质量与效率 |
| 纯 DAG | ✓ | ✗ | ✗ | 简单任务，最大化并行度 |
| 线性顺序 | ✗ | ✗ | ✗ | ReAct 基线对比 |

## 调度流程

1. **Planner Agent** 拆解任务 → 生成 DAG 节点
2. **调度引擎** 检测就绪节点，并行执行
3. **Executor Agent** 执行节点的多个候选动作
4. **Critic Agent** 评估每个分支的质量
5. **贪心选择器** 选择最优分支
6. **回溯管理器** 对失败节点进行局部回溯

## 关键参数

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `--max-parallel` | 3 | 最大并行执行节点数 |
| `--threshold` | 0.6 | 分支评分最低阈值 |
| `--no-backtrack` | False | 禁用回溯机制 |
| `--linear` | False | 使用线性顺序执行 |
| `--remote` | False | 调用远端 LLM |
