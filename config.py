"""
全局配置：API Key、模型名称、并发参数等。
"""

import os

# ---- LLM 配置 ----
LLM_URL = "https://api.edgefn.net/v1/chat/completions"
LLM_API_KEY = "sk-G4uDrXf0K6ScC7D27370C2B080Db4f94Be5122D91817507c"
LLM_MODEL = "DeepSeek-V4-Pro"
LLM_TIMEOUT = 60

# ---- 调度引擎配置 ----
MAX_PARALLEL = 3          # 最大并行执行节点数
BRANCH_NUM = 3            # 每个节点的候选分支数
SCORE_THRESHOLD = 0.6     # 分支评分阈值，低于此值视为失败

# ---- 回溯配置 ----
MAX_ROLLBACK_DEPTH = 3    # 最大回溯深度，防止死循环

# ---- 贪心树搜索权重 ----
QUALITY_WEIGHT = 0.5
CONFIDENCE_WEIGHT = 0.4
COST_WEIGHT = 0.05
TIME_WEIGHT = 0.05
