# Phase 21 Stage 2.3 — Context Window Definition

**项目**: Personal Memory Hub  
**阶段**: Phase 21 Stage 2.3  
**调查日期**: 2026-08-13  
**范围**: 只读调查，定义 Context Window 概念、边界和规则，不修改任何代码、数据库、Schema、测试或设计文档  

---

## 1. Decision Context

### 1.1 为什么需要 Context Window

Stage 2.1/2.2 已确定：
- Reconstruction ↔ Candidate = 1:1
- Reconstruction ↔ Topic = N:M
- Reconstruction 持久化，保存 semantic_summary + evidence_refs

但发现关键问题：

**场景**:
```
User: "我准备把 Candidate Formation 改成 Reconstruction → Candidate。"
AI: [长篇分析]
User: "对，就这样。"
```

**问题**: 
- Evidence_1: "我准备把 Candidate Formation 改成 Reconstruction → Candidate。"
- Evidence_2: "对，就这样。"

如果直接形成 Reconstruction:
- R1 只有 Evidence_2 → "对，就这样。"（无意义）
- 丢失了 User 的完整语义

**需要**: Context Window 将 Evidence_1（AI 的分析）作为上下文，理解 Evidence_2 的真实含义。

### 1.2 核心问题

1. Context Window 是什么？
2. Context Window 的边界如何确定？
3. AI Evidence 是否进入 Context？
4. 短回复如何获得足够上下文？
5. 主题偏离后如何回归？
6. Context Window 是否持久化？

---

## 2. Existing Evidence / Conversation Model

### 2.1 现有 Evidence Schema

**来源**: `memory_models.py` §Evidence

```python
class Evidence(Base):
    id: UUID
    workspace_id: UUID
    entity_id: UUID
    area_id: UUID
    user_id: UUID
    
    evidence_type: str
    content: str
    raw_content: str | None
    
    confidence: float
    importance: float
    signal_strength: float
    
    source: str  # conversation, manual, explicit_command, document, import
    
    _meta: dict[str, Any]  # JSONB
    
    created_at: datetime
    updated_at: datetime
```

**关键观察**:
1. Evidence 有 `_meta` JSONB 字段，可存储 conversation_id、message_id
2. Evidence **没有** `role` 字段区分 user/assistant
3. Evidence **没有** `parent_evidence_id` 表达消息关系
4. Evidence **没有** `sequence` 字段表达顺序

### 2.2 现有导入逻辑

**来源**: `chatgpt.py`, `open_webui.py`

```python
# chatgpt.py:116-118
role = author.get("role", "").lower()
# Only import user messages (skip assistant/system)
if role != "user":
    continue

# metadata
metadata = {
    "source": "chatgpt",
    "conversation_title": conv_title,
    "message_id": msg_id,
    "recipient": recipient,
}
```

**关键发现**:
1. **只导入 user messages，不导入 assistant messages**
2. conversation_id 在 metadata 中（OpenWebUI），message_id 在 metadata 中（ChatGPT）
3. 没有存储消息间的父子关系

### 2.3 现有 Metadata 结构

**ChatGPT**:
```json
{
  "source": "chatgpt",
  "conversation_title": "...",
  "message_id": "...",
  "recipient": "...",
  "original_timestamp": "..."
}
```

**OpenWebUI**:
```json
{
  "source": "open_webui",
  "conversation_title": "...",
  "conversation_id": "...",
  "message_index": 0,
  "model": "...",
  "original_timestamp": "..."
}
```

**关键观察**:
- conversation_id 可用于跨消息关联
- message_index 可用于同一 conversation 内的排序
- **但没有 role 信息**（user/assistant 被过滤掉了）

---

## 3. Context Window Semantic Definition

### 3.1 正式定义

**Context Window** = Reconstruction Formation 阶段，为解释触发 Evidence 而动态选择的一组相关 Evidence。

**关键特征**:
1. **动态性**: 每次 Reconstruction 形成时动态计算
2. **语义性**: 基于语义相关性，不是简单的时间窗口
3. **临时性**: Context Window 本身不持久化，只有结果（Reconstruction）持久化
4. **可追溯性**: Context Window 的选择过程应可审计

### 3.2 Context Window ≠ 其他概念

| 概念 | 定义 | Context Window 的关系 |
|------|------|---------------------|
| Conversation | 用户与 AI 的完整对话历史 | Context Window 可能是 Conversation 的子集 |
| Turn | 一次 User + AI 交互 | Context Window 可能包含多个 Turn |
| Evidence | 单条证据记录 | Context Window 是 Evidence 的集合 |
| Reconstruction | 语义重构结果 | Context Window 是 Reconstruction 的输入 |
| Topic | 语义组织维度 | Context Window 受 Topic 影响，但不等于 Topic |

### 3.3 Context Window 的组成部分

```
Context Window = {
    trigger_evidence: Evidence,      # 触发 Reconstruction 的新 Evidence
    context_evidences: [Evidence],   # 上下文 Evidence
    boundary_signals: [...],         # 边界信号（主题切换、时间间隔等）
    selection_reason: str            # 为什么选择这些 Evidence
}
```

---

## 4. Context Window Options

### Option A — Fixed Sliding Window

**设计**: 固定最近 N 条 Evidence

```
Evidence_N-5, Evidence_N-4, Evidence_N-3, Evidence_N-2, Evidence_N-1, Evidence_N(trigger)
```

**优点**:
- ✅ 简单实现
- ✅ Token 成本可控

**缺点**:
- ❌ 短回复场景：如果 N=5，但相关证据在第 10 条，丢失上下文
- ❌ 主题漂移：会把不相关的中间话题也包含进来
- ❌ 跨 Conversation：无法自动关联旧 Conversation 的相关证据

**结论**: **不推荐**作为唯一方案。

---

### Option B — Turn-Based Window

**设计**: 以 User + AI 为最小单位

```
Turn_1: User_A + AI_A
Turn_2: User_B + AI_B
Turn_3: User_C(trigger)
```

**问题**:
- 现有系统不存储 Assistant Evidence（导入时过滤掉了）
- 无法获得完整的 Turn 结构

**结论**: **需要修改导入逻辑**，超出 Stage 2.3 范围。

---

### Option C — Semantic Expansion Window

**设计**: 从触发 Evidence 开始，向前/向后扩展，直到语义边界

```
触发 Evidence → 向前扩展 → 找到语义边界
```

**如何判断边界**:
1. 语义不连续（主题切换）
2. 时间间隔超过阈值
3. 用户显式切换话题
4. Token budget 达到上限

**优点**:
- ✅ 语义完整
- ✅ 自适应长度

**缺点**:
- ❌ 需要 LLM 判断边界（成本高）
- ❌ 边界判断可能不一致

**结论**: **推荐作为核心机制**。

---

### Option D — Topic-Aware Window

**设计**: 根据 Topic 动态选择相关 Evidence

```
触发 Evidence → 提取 Topic → 查找同一 Topic 的其他 Evidence → 形成 Context
```

**循环依赖问题**:
- Topic Formation 依赖 Context Window（需要理解 Evidence 的语义）
- Context Window 依赖 Topic（需要 Topic 来筛选 Evidence）

**解决方案**: 两阶段
1. 第一阶段：使用轻量规则（时间、Entity）初步筛选
2. 第二阶段：Topic 形成后，重新评估 Context

**结论**: **推荐作为辅助机制**，不与 Option C 互斥。

---

### Option E — Reconstruction-Driven Window

**设计**: 先找到已有的 Reconstruction，然后扩展 Context

```
New Evidence → 查找相关的 Existing Reconstruction → 合并 Context → 形成新 Reconstruction
```

**优点**:
- ✅ 支持跨 Conversation Continuity（Stage 2.1 的核心需求）
- ✅ 避免从零开始重建

**缺点**:
- ⚠️ 需要高效的 Reconstruction Recall 机制

**结论**: **推荐作为核心机制之一**。

---

### Option F — Hybrid（推荐）

**设计**: 组合多种机制

```
Context Window = Recent Turn Window + Semantic Expansion + Reconstruction Recall + Topic Filtering
```

**优先级**:
1. **Reconstruction Recall**: 先查找相关的 Existing Reconstruction
2. **Semantic Expansion**: 从触发 Evidence 向前扩展
3. **Topic Filtering**: 排除与当前 Topic 无关的 Evidence
4. **Boundary Check**: 检查时间、语义、显式切换等边界信号

**结论**: **最终推荐方案**。

---

## 5. Recommended Context Model

### 5.1 Context Window 组成

```python
class ContextWindow:
    trigger_evidence: Evidence           # 触发 Reconstruction 的新 Evidence
    context_evidences: list[Evidence]    # 上下文 Evidence
    source_reconstruction: Reconstruction | None  # 相关的已有 Reconstruction
    topic_context: list[Topic]           # 相关的 Topic
    boundary_reason: str                 # 为什么在这里停止扩展
    token_count: int                     # 总 token 数（用于预算控制）
```

### 5.2 Context Window 形成算法

```
Step 1: 提取 Trigger Evidence 的 Topic
Step 2: 查找同一 Topic 的 Existing Reconstructions
Step 3: 从 Trigger Evidence 向前扩展 Evidence
        - 直到遇到边界信号（主题切换、时间间隔、budget 限制）
        - 只包含同一 Topic 的 Evidence
Step 4: 合并 Existing Reconstruction 的 evidence_refs
Step 5: 检查 Context Budget（token 上限）
Step 6: 返回 ContextWindow
```

### 5.3 边界信号

| 信号 | 类型 | 说明 |
|------|------|------|
| 语义不连续 | Soft | LLM 判断语义跳跃 |
| 用户显式切换 | Hard | 用户说"换个话题" |
| 时间间隔 > 24h | Soft | 长时间不活跃 |
| Token budget 达到 80% | Hard | 成本控制 |
| 不同的 Primary Entity | Soft | 主要讨论对象变化 |
| 不同的 Topic | Soft | Topic 转换 |

---

## 6. Context Boundary Rules

### 6.1 Hard Boundaries（必须停止）

1. **Token Budget 达到上限**: 例如 4000 tokens
2. **用户显式切换话题**: "换个话题"、"另外"
3. **超过 7 天无活动**: 长时间不活跃
4. **不同的 Primary Entity**: 讨论对象完全改变

### 6.2 Soft Boundaries（建议停止）

1. **语义不连续**: LLM 判断语义跳跃
2. **时间间隔 > 24h**: 中等长度不活跃
3. **不同的 Topic**: Topic 转换
4. **Evidence 数量 > 20**: 防止过多噪声

### 6.3 边界判断优先级

```
Hard Boundaries > Soft Boundaries

如果触发 Hard Boundary，立即停止扩展。
如果只触发 Soft Boundary，可以继续但标记为"可能的边界"。
```

---

## 7. Short User Reply Handling

### 7.1 问题定义

**场景**:
```
User: "我准备把 Candidate Formation 改成 Reconstruction → Candidate。"
AI: [长篇分析，2000 tokens]
User: "对，就这样。"
```

**问题**: Evidence_2 = "对，就这样。" 本身没有独立语义。

### 7.2 解决方案

**Context Window 必须包含 Trigger Evidence 前面的 AI 内容**。

**规则**:
1. 检测 Trigger Evidence 是否为短回复（长度 < 10 字符）
2. 如果是短回复，强制向前扩展 Context，直到找到足够的语义上下文
3. Context 中必须包含最近的 AI Evidence（如果存在）

**关键约束**:
> AI Evidence 可以作为 Context，但不能直接成为 User Candidate。

**Reconstruction 生成规则**:
```
Context = [User_Evidence_1, AI_Evidence_1, User_Evidence_2(trigger)]

Reconstruction 必须:
1. 理解 User_Evidence_2 是对 AI_Evidence_1 的确认
2. 以 User 视角表达语义："我确认采用 X 方案"
3. 不能直接将 AI_Evidence_1 的内容作为 User 事实
```

### 7.3 短回复类型

| 类型 | 示例 | Context 需求 |
|------|------|-------------|
| 确认 | "对"、"好的"、"就这样" | 需要前面的 AI 建议 |
| 否定 | "不要"、"不行"、"换一个" | 需要前面的 AI 建议 |
| 选择 | "第一个"、"方案 B" | 需要前面的选项列表 |
| 继续 | "继续"、"然后呢" | 需要前面的讨论 |
| 补充 | "另外"、"还有" | 需要前面的讨论 |

---

## 8. AI Evidence Handling

### 8.1 当前 Gap

**发现**: 现有导入逻辑**只导入 user messages**，不导入 assistant messages。

**来源**: `chatgpt.py:116-118`, `open_webui.py:110`

```python
# Only import user messages (skip assistant/system)
if role != "user":
    continue
```

**问题**:
1. Context Window 需要 AI 内容作为上下文
2. 但 AI Evidence 没有被导入/存储
3. 无法追溯"用户确认的是哪个 AI 建议"

### 8.2 设计决策

**Decision**: AI Evidence **允许**进入 Context Window，但**不允许**直接形成 Candidate。

**规则**:
```
Context Window 可以包含:
- User Evidence ✅
- AI Evidence ✅（作为上下文）

Reconstruction 必须:
- 以 User 视角表达语义
- 区分"用户事实"和"AI 建议"

Candidate 只能包含:
- User 确认的事实
- User 明确的决策
```

### 8.3 实现路径

**Stage 2.3 范围**: 定义规则，不实现。

**后续需要**:
1. 修改导入逻辑，保留 AI Evidence（标记 role='assistant'）
2. 在 Reconstruction 生成时，识别 AI Evidence 并正确解释
3. 在 Candidate 形成时，过滤掉纯 AI 内容

**Design Gap 记录**:
> 当前 Evidence Schema 缺少 `role` 字段，无法区分 user/assistant Evidence。
> 当前导入逻辑过滤掉 assistant messages，导致 Context Window 无法获得 AI 内容。

---

## 9. Topic Drift / Topic Return

### 9.1 场景

```
A: 讨论 Memory Hub 架构
B: 讨论 PostgreSQL 选型
C: 讨论 Ollama 部署
A: 回到 Memory Hub 架构
```

### 9.2 处理规则

**规则 1: 主题漂移检测**
- 如果连续 N 条 Evidence 属于不同 Topic，标记为"漂移"
- 漂移期间，Context Window 限制在当前 Topic 内

**规则 2: 主题回归检测**
- 如果新 Evidence 与之前的 Topic 相似，恢复之前的 Context
- 使用 Semantic Similarity 判断是否"回归"

**规则 3: 多 Topic Context**
- 允许 Context Window 包含多个 Topic 的 Evidence
- 但标记每个 Evidence 的 Topic 归属
- Reconstruction 生成时，选择最相关的 Topic 作为 primary

### 9.3 实现方式

```
Step 1: 为每条 Evidence 分配 Topic（或候选 Topic）
Step 2: 扩展 Context 时，优先选择同一 Topic 的 Evidence
Step 3: 如果遇到不同 Topic，检查是否"回归"
Step 4: 如果回归，恢复之前的 Context；否则，创建新的 Context Window
```

---

## 10. Cross-Conversation Context

### 10.1 场景

```
Conversation A (Month 1):
  Evidence_1, Evidence_2 → Reconstruction_R1 → Candidate_C1

Conversation B (Month 3):
  Evidence_3, Evidence_4
  如何找到 R1？
```

### 10.2 解决方案

**Recall 机制**:
```
New Evidence → Extract Topic → Query Existing Reconstructions by Topic
    ↓
找到 R1 → 加载 R1 的 evidence_refs → 扩展 Context
    ↓
形成 R2（基于 R1 的延续）
```

**关键设计**:
1. Context Window 可以引用 Existing Reconstruction 的 evidence_refs
2. 不需要重新导入所有历史 Evidence
3. 通过 Topic 和 Entity 进行 Recall

### 10.3 与 Stage 2.1 的关系

Stage 2.1 已定义：
- Reconstruction 持久化
- Reconstruction 支持 version chain
- Reconstruction 关联 Topic

**Stage 2.3 补充**:
- Context Window 可以引用 Existing Reconstruction
- Cross-Conversation Continuity 通过 Reconstruction Recall 实现

---

## 11. Long Evidence Handling

### 11.1 问题

AI 回复可能很长（2000-20000 tokens），是否全部进入 Context？

### 11.2 处理原则

**原则 1: 完整保存，选择性使用**
- Evidence 完整保存在数据库中（immutable）
- Context Window 可以选择性引用

**原则 2: 摘要优先**
- 对于超长 Evidence，优先使用摘要
- 需要时再查阅原始内容

**原则 3: Chunking 可选**
- 如果 Evidence 超过 4000 tokens，可以考虑分块
- 但这是 Future Phase，Stage 2.3 不实现

### 11.3 预算计算

```
Context Window Token Budget:
- 软上限: 4000 tokens
- 硬上限: 8000 tokens
- 默认: 2000 tokens

如果 Evidence 超过预算:
1. 优先保留 Trigger Evidence 和最近的 Context
2. 超长 Evidence 使用摘要
3. 标记为"需要人工查阅"
```

---

## 12. Context Budget

### 12.1 Budget 组成

| 组件 | Token 估算 | 说明 |
|------|-----------|------|
| Trigger Evidence | ~100 tokens | 触发 Reconstruction 的消息 |
| Context Evidence (5条) | ~1000 tokens | 平均 200 tokens/条 |
| Existing Reconstruction summary | ~500 tokens | R1 的 semantic_summary |
| System prompt | ~500 tokens | 固定的指令 |
| **总计** | ~2100 tokens | 默认预算 |

### 12.2 Budget 控制策略

```
策略 1: 严格模式（默认）
- 硬上限: 4000 tokens
- 超过则截断最早的 Context

策略 2: 宽松模式（高价值场景）
- 硬上限: 8000 tokens
- 用于重要决策场景

策略 3: 保守模式（成本敏感）
- 硬上限: 2000 tokens
- 只保留最近的 3 条 Evidence
```

### 12.3 Budget 分配

```
Trigger Evidence: 10%（必须保留）
Recent Context: 50%（最近 5 条 Evidence）
Historical Context: 30%（Existing Reconstruction 引用）
Overhead: 10%（系统提示等）
```

---

## 13. Reconstruction Reconciliation

### 13.1 R1 → R2 时的 Context 利用

**场景**:
```
R1: "用户决定使用 PostgreSQL"（已确认）
新 Evidence: "另外，我们还需要考虑 Docker 部署"
```

**处理方式**:
```
Step 1: 检测新 Evidence 是否与 R1 相关
        - 相同 Topic? ✅
        - 相同 Entity? ✅
        
Step 2: 加载 R1 的 Context
        - R1.evidence_refs
        - R1.semantic_summary
        
Step 3: 扩展 Context
        - R1 的 Evidence + 新 Evidence
        
Step 4: 形成 R2
        - R2.parent = R1
        - R2.evidence_refs = R1.evidence_refs + [新 Evidence]
        - R2.semantic_summary = 更新的语义状态
```

**关键原则**:
> 新 Reconstruction 应该继承旧 Reconstruction 的 Context，而不是从零开始。

### 13.2 Context 继承规则

| 情况 | Context 处理 |
|------|-------------|
| 新 Evidence 与已有 Reconstruction 同 Topic | 继承 Existing Reconstruction 的 evidence_refs |
| 新 Evidence 与已有 Reconstruction 不同 Topic | 创建新的 Context Window |
| 新 Evidence 是短回复 | 强制继承前面的 Context |
| 新 Evidence 是独立话题 | 创建新的 Context Window |

---

## 14. Persistence Boundary

### 14.1 Context Window 是否持久化？

**Decision**: **不独立持久化 Context Window 本身**。

**理由**:
1. Context Window 是 Reconstruction Formation 的中间过程
2. Reconstruction 已经保存了 `evidence_refs`，足以追溯 Context
3. 独立持久化会产生重复数据

**需要持久化的**:
1. Reconstruction.evidence_refs — 已存在
2. Reconstruction.parent_reconstruction_id — 已设计
3. Context Window 的选择理由 — 可选存储在 Reconstruction.metadata 中

### 14.2 Reconstruction.evidence_refs 是否足够？

**答案**: **是**，但有条件。

**足够的原因**:
- evidence_refs 包含所有参与 Reconstruction 的 Evidence ID
- 可以通过 ID 查询完整的 Evidence 内容
- 支持审计和 Debug

**不足的情况**:
- 如果需要了解"为什么选择这些 Evidence"，需要额外的 selection_reason
- 建议存储在 Reconstruction.metadata 中

### 14.3 推荐 Schema 扩展

```sql
-- reconstruction 表新增字段
ALTER TABLE memory_hub.reconstructions ADD COLUMN context_reason TEXT;
ALTER TABLE memory_hub.reconstructions ADD COLUMN context_token_count INTEGER;
```

**用途**:
- context_reason: 为什么选择这些 Evidence 作为 Context
- context_token_count: Context 的总 token 数（用于监控）

---

## 15. Evidence ↔ Context ↔ Reconstruction Lineage

### 15.1 完整关系图

```
┌─────────────┐     1:N      ┌─────────────┐     N:1      ┌─────────────┐
│   Evidence   │────────────▶│ ContextWindow │────────────▶│Reconstruction│
│              │             │ (临时对象)    │             │             │
│ - id         │             │ - trigger     │             │ - id        │
│ - content    │             │ - evidences   │             │ - evidence_ │
│ - metadata   │             │ - budget      │             │   refs      │
└─────────────┘             └─────────────┘             └──────┬──────┘
       │                                                        │
       │ 1:N                                                    │ 1:1
       ▼                                                        ▼
┌─────────────┐                                         ┌─────────────┐
│  Topic      │◄─────────────────────────────────────────│Reconstruction│
│             │                    N:M                   │             │
└─────────────┘                                         └─────────────┘
```

### 15.2 Lineage 追溯

**查询"某 Reconstruction 的 Context"**:
```sql
SELECT e.* FROM evidences e
WHERE e.id = ANY(r.evidence_refs)
AND r.id = :reconstruction_id;
```

**查询"某 Evidence 参与了哪些 Reconstruction"**:
```sql
SELECT r.* FROM reconstructions r
WHERE :evidence_id = ANY(r.evidence_refs);
```

**查询"某 Reconstruction 的 Context 选择理由"**:
```sql
SELECT r.context_reason, r.context_token_count
FROM reconstructions r
WHERE r.id = :reconstruction_id;
```

---

## 16. Code / Design Compatibility

### 16.1 与现有设计的兼容性

| 现有设计 | Context Window 影响 | 兼容性 |
|---------|---------------------|--------|
| Evidence 表 | 需要 metadata 存储 context 信息 | ✅ 兼容 |
| Reconstruction 表 | 新增 context_reason 字段 | ⚠️ 小修改 |
| Topic 表 | 通过 topic_links 关联 | ✅ 兼容 |
| Candidate 表 | 不受影响 | ✅ 兼容 |
| Proposal 表 | 不受影响 | ✅ 兼容 |

### 16.2 发现的 Design Gap

**Gap 1: Evidence 缺少 role 字段**

**证据**:
- 导入逻辑只导入 user messages
- Evidence Schema 没有 role 字段
- 无法区分 user/assistant Evidence

**影响**:
- Context Window 无法获得 AI 内容作为上下文
- 短回复场景无法正确处理

**解决方案**:
- 修改导入逻辑，保留 AI Evidence（标记 role='assistant'）
- 在 Evidence Schema 中新增 role 字段

**优先级**: P0（影响 Context Window 核心功能）

---

**Gap 2: Evidence 缺少 parent_evidence_id**

**证据**:
- Evidence Schema 没有 parent 字段
- 无法表达消息间的父子关系
- 无法追溯"这条消息是对哪条消息的回复"

**影响**:
- Context Window 难以精确选择相关的上下文

**解决方案**:
- 在 Evidence Schema 中新增 parent_evidence_id 字段
- 或在 metadata 中存储 reply_to 信息

**优先级**: P1（可选增强）

---

### 16.3 Stage 2.1/2.2 决策影响

**Stage 2.1**: Reconstruction ↔ Candidate = 1:1
- **不受影响** ✅

**Stage 2.1**: Reconstruction.entity_id NOT NULL
- **不受影响** ✅

**Stage 2.2**: Topic ↔ Reconstruction = N:M
- **部分影响**: Context Window 需要考虑 Topic 关联
- **解决方案**: Context Window 形成时，查询同一 Topic 的已有 Reconstruction

---

## 17. ADR Decision Statement

### 17.1 Decision

**ADR-Phase21-02: Context Window Architecture**

**Status**: Proposed

**Context**:
Phase 21 需要定义 Context Window，以支持：
1. 短回复的语义理解（"对，就这样"）
2. 跨 Conversation 的连续性
3. 主题漂移后的回归

**Decision**:
采用 Hybrid Context Model：
```
Context Window = Reconstruction Recall + Semantic Expansion + Topic Filtering + Budget Control
```

**Schema Changes**:
```sql
-- 新增字段（可选增强）
ALTER TABLE memory_hub.reconstructions ADD COLUMN context_reason TEXT;
ALTER TABLE memory_hub.reconstructions ADD COLUMN context_token_count INTEGER;

-- 发现的 Gap（需后续处理）
-- Evidence 表需要 role 字段
-- Evidence 表需要 parent_evidence_id 字段
```

**Context Budget**:
- 默认: 4000 tokens
- 硬上限: 8000 tokens
- 分配: Trigger 10%, Recent 50%, Historical 30%, Overhead 10%

**Short Reply Handling**:
- 检测短回复（< 10 字符）
- 强制向前扩展 Context
- AI Evidence 可作为 Context，但不能直接成为 Candidate

**Cross-Conversation**:
- 通过 Existing Reconstruction Recall 实现
- 不重复导入历史 Evidence

**Consequences**:
- ✅ 支持短回复语义理解
- ✅ 支持跨 Conversation 连续性
- ✅ Token 成本可控
- ⚠️ 需要修改导入逻辑（保留 AI Evidence）
- ⚠️ 需要新增 Evidence.role 字段

**References**:
- `phase21-stage2.1-reconstruction-architecture.md`
- `phase21-stage2.1a-reconstruction-relationship-validation.md`
- `phase21-stage2.2-topic-definition.md`

---

## 18. Deferred Questions

| 问题 | 优先级 | 所属阶段 | 理由 |
|------|--------|----------|------|
| Evidence.role 字段实现 | P0 | Stage 2.4 | 影响 Context Window 核心功能 |
| Evidence.parent_evidence_id | P1 | Deferred | 可选增强 |
| Context Window 算法实现 | P1 | Stage 3 | 实现细节 |
| Token budget 精确数值 | P2 | Stage 3 | 性能调优 |
| Long Evidence Chunking | P2 | Deferred | 未来优化 |

---

## 最终回答

### Question 1: Context Window 正式定义是什么？

**Answer**:
> Context Window 是 Reconstruction Formation 阶段，为解释触发 Evidence 而动态选择的一组相关 Evidence。

### Question 2: Context Window 是固定/滑动/语义/Topic-aware/Reconstruction-driven/Hybrid？

**Answer**: **Hybrid** ✅

组合：Reconstruction Recall + Semantic Expansion + Topic Filtering + Budget Control

### Question 3: Context Window 是否持久化？

**Answer**: **否** ✅

Context Window 是临时对象，只有结果（Reconstruction.evidence_refs）持久化。

### Question 4: Reconstruction.evidence_refs 是否足够？

**Answer**: **是**，但建议新增 context_reason 和 context_token_count 字段用于审计。

### Question 5: AI Evidence 是否允许进入 Context？

**Answer**: **是** ✅

AI Evidence 可以作为 Context，但不能直接成为 User Candidate。

### Question 6: AI Evidence 是否允许直接形成 Candidate？

**Answer**: **否** ✅

必须经过 User-centric semantic interpretation。

### Question 7: 短回复如何处理？

**Answer**: 强制向前扩展 Context，直到找到足够的语义上下文（包括 AI 内容）。

### Question 8: Topic Drift 如何处理？

**Answer**: 检测主题切换，漂移期间限制 Context 在当前 Topic 内；回归时恢复之前的 Context。

### Question 9: 跨 Conversation 如何处理？

**Answer**: 通过 Existing Reconstruction Recall 实现，不重复导入历史 Evidence。

### Question 10: 长 AI Response 如何处理？

**Answer**: 完整保存，选择性使用；超长时使用摘要。

### Question 11: Context Window 如何终止？

**Answer**: Hard Boundaries（budget 达到、显式切换）> Soft Boundaries（语义不连续、时间间隔）。

### Question 12: R1 → R2 时如何利用 R1？

**Answer**: 继承 R1 的 evidence_refs，扩展新 Evidence，形成 R2（parent=R1）。

---

*本报告为只读调查，不修改任何代码、数据库、Schema、测试或设计文档。*
*发现的 Gap（Evidence.role 缺失）需要后续 Stage 处理。*

---

**STOP** — 不编码、不提交 Git，等待下一步指示。
