# E6 - 演化模型配置 (Evolution Model Configuration)

> **日期**: 2026-08-01  
> **状态**: MVP 初版

---

## 一、概述

本方案定义了 Personal Memory Hub 中用于记忆演化的专用 Ollama 模型配置。

**核心设计理念**：
- 基于现有基础模型（如 qwen2.5:7b）通过 Modelfile 定制专门角色
- 不冻结具体模型版本，便于后续优化
- 通过调整提示词即可改善演化效果

---

## 二、reflection-engine 模型配置

### 2.1 模型定义文件

**路径**: `backend/scripts/Modelfile.reflection-engine`

```dockerfile
FROM qwen2.5:7b

# 系统提示词 - 定义演化角色
SYSTEM """你是一个记忆演化专家 (Reflection Engine)，专门负责从用户的日常记忆中提取结构化信息并生成演化建议。

你的职责：
1. 从 Observation (L1) 级记忆中提取结构化事实
2. 分析实体相关的兴趣趋势
3. 生成 Memory Pyramid 更新建议

演化决策规则：
- Create (创建): 当某实体出现 >= 2 条高置信度事实时，创建新的 L1 Observation 或 L2 Pattern
- Strengthen (强化): 当某实体有 >= 3 条事实且平均置信度 >= 0.8 时，提升为 L2 Pattern
- Refine (精炼): 当某实体置信度 >= 0.9 时，精炼现有记录
- Split (拆分): 当某实体记录包含多个不相关主题时，建议拆分
- Ignore (忽略): 当证据不足或置信度低时，暂不处理

输入格式：
- 候选记忆列表，每条包含 content, level, source
- 工作空间 ID
- 演化范围 (daily/weekly/monthly)

输出格式 (JSON):
{
  "facts": [...],
  "entities": [...],
  "interest_trends": {...},
  "proposals": [...],
  "execution_log": [...]
}

约束：
- 只处理 L1 (Observation) 级记忆
- 不生成 L0 (State) 级记忆
- 证据链必须完整
- 置信度必须基于事实数量和质量计算
"""

PARAMETER temperature 0.3
PARAMETER num_ctx 32768
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
```

### 2.2 创建模型

```bash
ollama create reflection-engine -f backend/scripts/Modelfile.reflection-engine
```

### 2.3 环境变量配置

**docker-compose.yml**:
```yaml
environment:
  REFLECTION_MODEL: ${REFLECTION_MODEL:-reflection-engine}
  REFLECTION_TEMPERATURE: ${REFLECTION_TEMPERATURE:-0.3}
  OLLAMA_BASE_URL: ${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
```

---

## 三、后续优化方向

### 3.1 提示词优化

当前提示词为 MVP 初版，可通过以下方式优化：

1. **增加few-shot示例**：在 SYSTEM 提示中加入 2-3 个完整的输入输出示例
2. **细化决策规则**：根据实际测试结果调整 Create/Strengthen/Refine/Split 的阈值
3. **约束JSON格式**：使用更严格的 schema 定义，确保输出可解析

### 3.2 模型升级路径

未来可平滑升级到更强模型：

```bash
# 方案 1: 更换基础模型
FROM qwen3:8b  # 或任何其他支持的模型
# 保持相同 SYSTEM 提示词

# 方案 2: 微调专用模型
# 使用用户实际演化数据微调，生成专属模型
```

### 3.3 其他角色模型（未来）

可为不同任务创建专用模型：

| 模型名 | 用途 | 基础模型 |
|--------|------|----------|
| `extraction-engine` | 事实提取 | qwen2.5:7b |
| `analysis-engine` | 趋势分析 | qwen2.5:7b |
| `summarization-engine` | 记忆摘要 | qwen2.5:7b |

---

## 四、配置管理原则

1. **不冻结模型版本**：Modelfile 中只指定基础模型名，不锁定具体版本哈希
2. **提示词与代码分离**：演化逻辑在代码，角色定义在 Modelfile
3. **环境变量覆盖**：所有配置项都可通过环境变量覆盖，便于不同环境测试

---

## 五、验证方法

```bash
# 1. 检查模型列表
ollama list | grep reflection-engine

# 2. 测试模型
curl http://localhost:11434/api/generate -d '{
  "model": "reflection-engine",
  "prompt": "测试演化",
  "stream": false
}'

# 3. 运行完整演化
curl -X POST http://localhost:8000/api/cron/tasks/{task_id}/run-now
```

---

*本配置为 MVP 初版，后续可根据实际演化效果持续优化提示词。*
