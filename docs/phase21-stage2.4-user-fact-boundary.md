# Phase 21 Stage 2.4 — User Fact Boundary

**项目**: Personal Memory Hub  
**阶段**: Phase 21 Stage 2.4  
**调查日期**: 2026-08-13  
**范围**: 只读调查，定义 User-owned Semantic 边界和语义归属规则，不修改任何代码、数据库、Schema、测试或设计文档  

---

## 1. Decision Context

### 1.1 为什么需要 User Fact Boundary

Stage 2.3 已确认：
- AI Evidence 可以进入 Context Window
- AI Evidence 不能直接成为 User Candidate

但发现关键 Gap：

**当前系统没有机制判断**：
- 哪些 Evidence 是 User 说的
- 哪些 Evidence 是 AI 说的
- 用户是否确认了 AI 的建议
- 用户是否否定了 AI 的方案

**问题场景**：
```
AI: "建议采用 PostgreSQL。"
User: "对。"

当前系统会形成什么 Candidate？
- 如果只看 Evidence_2: "对。" → 无意义
- 如果错误地保留 AI 内容: "建议采用 PostgreSQL。" → 污染 User Memory
- 正确应该: "用户确认采用 PostgreSQL。"
```

### 1.2 核心原则

> **AI 说过的话不是用户事实。**

但是：

> **用户可以通过确认、否定、修改、选择等行为，使 AI 提出的内容获得"用户语义归属"。**

---

## 2. Existing Architecture Evidence

### 2.1 当前 Evidence Schema

**来源**: `memory_models.py`, `09_Database_Physical_Design.md`

```python
class Evidence(Base):
    id: UUID
    workspace_id: UUID
    entity_id: UUID
    area_id: UUID
    user_id: UUID
    
    evidence_type: str      # 证据类型
    content: str            # 内容
    raw_content: str | None # 原始内容
    
    confidence: float       # 置信度
    importance: float       # 重要性
    signal_strength: float  # 信号强度
    
    source: str             # conversation, manual, explicit_command, document, import
    
    _meta: dict[str, Any]   # 元数据 JSONB
    
    created_at: datetime
    updated_at: datetime
```

**关键观察**:
1. **没有 `role` 字段** — 无法区分 user/assistant
2. **没有 `parent_evidence_id`** — 无法表达消息关系
3. **没有 `is_user_generated` 字段** — 无法标记语义来源
4. **metadata 可以存储 role** — 但不是结构化字段

### 2.2 导入逻辑现状

**来源**: `chatgpt.py:116-118`, `open_webui.py:110`

```python
# 只导入 user messages
if role != "user":
    continue
```

**关键发现**:
- Assistant messages **被过滤掉**
- Context Window 无法获得 AI 内容
- 无法追溯"用户确认的是哪个 AI 建议"

### 2.3 Candidate Schema

**来源**: `09_Database_Physical_Design.md` §09.4.13

```sql
CREATE TABLE memory_hub.candidates (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    entity_id UUID NOT NULL,
    area_id UUID,
    
    content TEXT NOT NULL,
    candidate_type VARCHAR(20) NOT NULL CHECK (candidate_type IN ('pattern', 'belief')),
    
    evidence_source VARCHAR(50) NOT NULL DEFAULT 'observation',
    evidence_id UUID,
    evidence_chain JSONB NOT NULL DEFAULT '[]',
    evidence_count INTEGER NOT NULL DEFAULT 0,
    evidence_strength FLOAT DEFAULT 0.0,
    
    status VARCHAR(20) NOT NULL DEFAULT 'candidate' CHECK (status IN (
        'candidate', 'confirmed', 'archived', 'orphaned'
    )),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**关键观察**:
1. `candidate_type` 只有 `pattern` 和 `belief` 两种
2. 没有表达"用户确认"、"用户否定"、"用户选择"的类型
3. `evidence_chain` 是 JSONB，可以存储 Evidence 引用
4. `status` 表达生命周期，但不表达语义归属

### 2.4 MemoryNode Schema

**来源**: `09_Database_Physical_Design.md` §09.4.5

```sql
CREATE TABLE memory_hub.memory_nodes (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    entity_id UUID NOT NULL,
    parent_node_id UUID,
    user_id UUID,
    
    level INTEGER NOT NULL CHECK (level IN (1, 2, 3)),
    node_type VARCHAR(50) NOT NULL,
    
    content TEXT NOT NULL,
    summary TEXT,
    
    observation_type VARCHAR(50) CHECK (
        level = 1 AND observation_type IN (
            'activity', 'decision', 'preference', 'fact', 'goal', 'problem', 'event'
        ) OR level != 1
    ),
    
    confidence FLOAT NOT NULL DEFAULT 0.0,
    importance FLOAT NOT NULL DEFAULT 0.0,
    
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**关键观察**:
1. L1 有 `observation_type`：activity, decision, preference, fact, goal, problem, event
2. 没有表达"用户确认"、"用户否定"的类型
3. `metadata` 可以存储额外信息

---

## 3. User-owned Semantic Definition

### 3.1 正式定义

**User-owned Semantic** = 用户通过语言行为明确表达的、可以归属为用户自身立场的语义内容。

**核心特征**:
1. **可归属**: 可以明确追溯到用户的语言行为
2. **可理解**: 在上下文中具有明确的语义
3. **可持久化**: 值得进入长期 Memory

### 3.2 User-owned vs AI-owned

| 维度 | User-owned | AI-owned |
|------|------------|----------|
| 来源 | 用户的语言行为 | AI 生成的内容 |
| 示例 | "我决定使用 PostgreSQL" | "建议采用 PostgreSQL" |
| 归属 | 用户事实 | AI 建议 |
| 持久化 | 可以成为 Candidate | 不能直接成为 Candidate |
| Context | 可以作为触发 Evidence | 可以作为上下文 Evidence |

### 3.3 User Language Behaviors

用户通过以下语言行为表达 User-owned Semantic：

| 行为 | 示例 | 说明 |
|------|------|------|
| **直接表达** | "我使用 PostgreSQL" | 明确陈述事实 |
| **确认** | "对，就这样" | 认可 AI 建议 |
| **否定** | "不要这个" | 拒绝 AI 建议 |
| **修正** | "我是说 B" | 纠正之前的表达 |
| **选择** | "第一个" | 从选项中挑选 |
| **偏好** | "我更喜欢 A" | 表达倾向 |
| **决策** | "就用方案 A" | 做出决定 |
| **意图** | "我准备迁移" | 表达未来计划 |
| **信念** | "我认为这个不可靠" | 表达主观判断 |
| **约束** | "我只有 16GB" | 表达限制条件 |

---

## 4. AI Statement vs User Fact

### 4.1 AI Statement 的特征

**不能成为 User Candidate 的 AI 内容**：

1. **建议/推荐**
   - "建议采用 PostgreSQL"
   - "推荐使用 Docker"
   
2. **分析/解释**
   - "PostgreSQL 的优势是..."
   - "根据你的需求，我建议..."
   
3. **问题/澄清**
   - "你确定要用 PostgreSQL 吗？"
   - "你的预算是多少？"
   
4. **假设/推演**
   - "如果采用 PostgreSQL，你可以..."
   - "假设你选择 A，那么..."

### 4.2 User Fact 的特征

**可以成为 User Candidate 的内容**：

1. **明确的事实陈述**
   - "我使用 PostgreSQL"
   - "我有 16GB 内存"
   
2. **明确的决策**
   - "我决定使用 PostgreSQL"
   - "就用方案 A"
   
3. **明确的偏好**
   - "我更喜欢 PostgreSQL"
   - "我倾向于方案 A"
   
4. **明确的意图**
   - "我准备迁移到 PostgreSQL"
   - "下个月我要部署"
   
5. **明确的信念/判断**
   - "我认为 PostgreSQL 更可靠"
   - "我觉得方案 A 更好"

### 4.3 边界判断规则

**规则 1**: 如果内容表达的是 AI 的建议/分析，不是 User Fact

**规则 2**: 如果内容表达的是用户自己的立场/决定/偏好，是 User Fact

**规则 3**: 如果用户确认了 AI 的建议，经过语义转换后是 User Fact

**规则 4**: 如果用户否定了 AI 的建议，经过语义转换后是 User Fact（否定状态）

---

## 5. User Confirmation Semantics

### 5.1 Confirmation 的定义

**Confirmation** = 用户通过语言行为认可、接受、采纳 AI 提出的内容。

### 5.2 Confirmation 的类型

#### Type 1: Explicit Confirmation（显式确认）

**特征**: 用户明确表达认可

**示例**:
- "对，就这样"
- "好，就用这个"
- "同意"
- "确认"
- "就这么定了"

**规则**: 直接形成 User Fact

#### Type 2: Implicit Confirmation（隐式确认）

**特征**: 用户通过选择、采纳行为表达认可

**示例**:
- "第一个"（选择第一个方案）
- "方案 A"（明确选择）
- "就用 PostgreSQL"（明确采纳）

**规则**: 需要结合上下文判断

#### Type 3: Ambiguous Acknowledgment（模糊确认）

**特征**: 用户表达模糊的认可

**示例**:
- "嗯"
- "知道了"
- "明白"
- "哦"
- "好吧"

**规则**: 需要额外确认，不能直接形成 User Fact

### 5.3 Confirmation 的判断流程

```
Step 1: 检测是否为短回复（长度 < 10 字符）
    ↓
Step 2: 检查是否为确认词汇
    ↓
Step 3: 查找 Context 中的最近 AI 建议
    ↓
Step 4: 判断确认的目标
    ↓
Step 5: 语义转换：AI 建议 → User Fact
```

### 5.4 Confirmation 场景测试

#### Case 1: 简单确认

**Context**:
```
AI: "建议使用 PostgreSQL。"
User: "对。"
```

**处理**:
1. 检测到"对"是确认词
2. 查找最近的 AI 建议："建议使用 PostgreSQL"
3. 语义转换："用户确认采用 PostgreSQL"
4. 形成 Candidate: "用户决定使用 PostgreSQL"

#### Case 2: 选择确认

**Context**:
```
AI: "方案 A 成本低，方案 B 更稳定。"
User: "第二个。"
```

**处理**:
1. 检测到"第二个"是选择词
2. 查找 Context 中的选项列表
3. 语义转换："用户选择方案 B"
4. 形成 Candidate: "用户选择方案 B"

#### Case 3: 部分确认

**Context**:
```
AI: "我建议 A + B + C。"
User: "A 可以，但 B 不行，C 再看看。"
```

**处理**:
1. 检测到部分确认
2. 形成多个 Candidate:
   - C1: "用户接受方案 A"
   - C2: "用户否定方案 B"
   - C3: "用户待定方案 C"

#### Case 4: 修正确认

**Context**:
```
AI: "你决定使用 PostgreSQL。"
User: "不，我只是考虑。"
```

**处理**:
1. 检测到否定/修正
2. 语义转换："用户仅在考虑 PostgreSQL"
3. 形成 Candidate: "用户正在考虑 PostgreSQL"（不确定性状态）

---

## 6. Rejection / Correction Semantics

### 6.1 Rejection 的定义

**Rejection** = 用户通过语言行为拒绝、否定 AI 提出的内容。

### 6.2 Rejection 的类型

#### Type 1: Explicit Rejection（显式拒绝）

**示例**:
- "不要这个"
- "不行"
- "我不需要"
- "否决"

**规则**: 形成否定状态的 User Fact

#### Type 2: Implicit Rejection（隐式拒绝）

**示例**:
- "换一个"
- "再想想"
- "不对"

**规则**: 需要结合上下文判断

### 6.3 Correction 的定义

**Correction** = 用户通过语言行为纠正自己之前的表达或 AI 的理解。

### 6.4 Correction 的场景

**场景 1: 用户纠正自己**
```
User: "我用 PostgreSQL。"
User: "不对，我是说 MySQL。"
```
**处理**: 形成更新的 User Fact："用户决定使用 MySQL"

**场景 2: 用户纠正 AI 的理解**
```
AI: "你决定使用 PostgreSQL。"
User: "不，我只是考虑。"
```
**处理**: 形成修正的 User Fact："用户仅在考虑 PostgreSQL"

---

## 7. Preference / Decision / Intention / Belief / Constraint

### 7.1 分类矩阵

| 类型 | 定义 | 示例 | Candidate 示例 |
|------|------|------|---------------|
| **Preference** | 用户的倾向性选择 | "我更喜欢 A" | "用户倾向于方案 A" |
| **Decision** | 用户的明确决定 | "就用方案 A" | "用户决定采用方案 A" |
| **Intention** | 用户的未来计划 | "我准备迁移" | "用户计划下月迁移" |
| **Belief** | 用户的判断/观点 | "我认为 A 更好" | "用户相信方案 A 更优" |
| **Constraint** | 用户的限制条件 | "我只有 16GB" | "用户内存限制 16GB" |
| **Fact** | 用户的客观事实 | "我用 Windows" | "用户操作系统为 Windows" |
| **Goal** | 用户的目標 | "我想提高性能" | "用户目标是提升性能" |
| **Problem** | 用户的问题 | "我的数据库很慢" | "用户遇到数据库性能问题" |

### 7.2 与现有 Schema 的关系

**候选 observation_type**:
- decision → 用户决策
- preference → 用户偏好
- fact → 用户事实
- goal → 用户目标
- problem → 用户问题
- activity → 用户活动
- event → 用户事件

**新增类型**（可选）:
- confirmation → 用户确认
- rejection → 用户否定
- correction → 用户修正

---

## 8. Hypothetical / Conditional / Third-party / Quoted Content

### 8.1 假设性内容

**特征**: 用户表达假设、推测、可能性

**示例**:
- "如果以后需要，我可能会用 PostgreSQL"
- "假设我用 A，那么..."
- "也许可以考虑 B"

**规则**: **不形成确定的 User Candidate**

**理由**:
- 不是明确的事实或决策
- 只是可能性探讨
- 可以作为 Context，但不作为 Memory

**例外**: 如果用户后续确认，则可以形成 Candidate

### 8.2 条件句

**特征**: 用户在特定条件下表达的态度

**示例**:
- "如果预算够，我会升级"
- "如果有时间，我会学习"
- "除非出问题，否则我用 A"

**规则**: **形成条件性 User Candidate**

**理由**:
- 表达了用户的态度，但有条件
- 可以作为 Memory，但需标注条件
- 当条件满足时，可以更新为确定性 Memory

**Schema 建议**:
```sql
-- 在 metadata 中存储条件
metadata = {
  "condition": "预算够",
  "conditional_fact": "用户计划升级"
}
```

### 8.3 第三方事实

**特征**: 用户陈述其他人的事实

**示例**:
- "我朋友用 PostgreSQL"
- "公司规定用 Docker"
- "大家都推荐这个"

**规则**: **不形成 User-owned Candidate**

**理由**:
- 不是用户自身的事实
- 是用户的观察/转述
- 可以作为 Context，但不作为 Memory

**例外**: 如果用户表达的是自己的判断（如"我认为公司规定..."），可以形成 Belief

### 8.4 引用内容

**特征**: 用户引用 AI 或其他来源的内容

**示例**:
- "你刚才说我使用 PostgreSQL"
- "记住你刚才关于 PostgreSQL 的分析"
- "把这段保存下来"

**规则**: **需要判断用户的真实意图**

**场景 1**: 引用 AI 内容但没有确认
```
User: "你刚才说我使用 PostgreSQL"
```
**处理**: 不是 User Fact，只是转述

**场景 2**: 用户要求保留 AI 分析
```
User: "记住你刚才关于 PostgreSQL 的分析"
```
**处理**: 这是"保留分析"的意图，不是"使用 PostgreSQL"的事实
- 形成 Candidate: "用户希望保留 PostgreSQL 分析"
- 不是: "用户决定使用 PostgreSQL"

---

## 9. User-centric Reconstruction

### 9.1 定义

**User-centric Reconstruction** = 从 Context 中重建用户可归属的语义状态，而不是简单地总结对话。

### 9.2 与普通 Summary 的区别

| 维度 | 普通 Summary | User-centric Reconstruction |
|------|-------------|---------------------------|
| 视角 | 客观总结 | 用户视角 |
| 内容 | "AI 建议 A，用户同意" | "用户确认采用 A" |
| 归属 | 不确定 | 明确归属用户 |
| 用途 | 记录对话 | 形成 Memory |

### 9.3 生成规则

**规则 1**: Reconstruction 必须以用户第一人称表达

**规则 2**: AI 内容只能作为上下文，不能直接成为 User Fact

**规则 3**: 用户确认的 AI 内容需要经过语义转换

**规则 4**: 用户否定的内容形成否定状态的 Fact

### 9.4 示例

**场景 1**: 简单确认
```
Context:
  AI: "建议使用 PostgreSQL。"
  User: "对，就这样。"

Reconstruction:
  "用户确认采用 PostgreSQL。"
```

**场景 2**: 部分确认
```
Context:
  AI: "我建议 A + B + C。"
  User: "A 可以，但 B 不行，C 再看看。"

Reconstruction:
  分解为多个语义单元:
  - "用户接受方案 A"
  - "用户否定方案 B"
  - "用户待定方案 C"
```

**场景 3**: 否定
```
Context:
  AI: "你决定使用 PostgreSQL。"
  User: "不，我只是考虑。"

Reconstruction:
  "用户仅在考虑 PostgreSQL（尚未决定）"
```

**场景 4**: 条件句
```
Context:
  User: "如果预算够，我会升级。"

Reconstruction:
  "用户计划：如果预算允许则升级（条件性决策）"
```

---

## 10. Candidate Formation Boundary

### 10.1 允许进入 Candidate 的内容

| 类别 | 示例 | 说明 |
|------|------|------|
| **Explicit Fact** | "我使用 Windows" | 直接事实陈述 |
| **Explicit Decision** | "我决定使用 PostgreSQL" | 明确决策 |
| **Explicit Preference** | "我更喜欢方案 A" | 明确偏好 |
| **Explicit Intention** | "我准备下月迁移" | 明确意图 |
| **Explicit Belief** | "我认为 A 更可靠" | 明确判断 |
| **Explicit Constraint** | "我只有 16GB" | 明确限制 |
| **Confirmed AI** | (AI: "用 A" → User: "好") | 用户确认的 AI 建议 |
| **Selected Option** | (AI: "A/B/C" → User: "第一个") | 用户选择的选项 |
| **Conditional Fact** | "如果预算够就升级" | 条件性事实 |

### 10.2 禁止进入 Candidate 的内容

| 类别 | 示例 | 原因 |
|------|------|------|
| **Pure AI Statement** | "建议使用 PostgreSQL" | 不是用户事实 |
| **AI Analysis** | "PostgreSQL 的优势是..." | 不是用户事实 |
| **Hypothetical** | "如果以后需要..." | 不是明确事实 |
| **Third-party** | "我朋友用 PostgreSQL" | 不是用户事实 |
| **Quoted AI** | "你刚才说..." | 只是转述 |
| **Roleplay** | "假设我是数据库..." | 不是真实陈述 |
| **Ambiguous** | "嗯" | 无法确定语义 |
| **Informational** | "有人用 PostgreSQL" | 不是用户事实 |

### 10.3 边界判断决策树

```
Trigger Evidence 到达
    ↓
是否包含 User Language Behavior？
    ├── 否 → 跳过，等待更多 Evidence
    └── 是 ↓
        是否明确表达 User-owned Semantic？
            ├── 否 → 判断是否为 Context
            │           ├── 是 → 存入 Context，不形成 Candidate
            │           └── 否 → 跳过
            └── 是 ↓
                是否经过 User-centric Interpretation？
                    ├── 否 → 转换语义（AI 建议 → User 确认）
                    └── 是 ↓
                        是否符合 Candidate Formation 标准？
                            ├── 否 → 存入 Context，等待更多 Evidence
                            └── 是 → 形成 Candidate
```

---

## 11. Confidence / Ambiguity

### 11.1 Confidence 的来源

**当前 Schema**: Evidence 已有 `confidence`、`importance`、`signal_strength` 字段

**建议**: 在 Reconstruction/Candidate 层不新增 Confidence 字段，而是：

1. **在 metadata 中存储 confidence 来源**
   ```json
   {
     "confidence_source": "user_explicit",
     "confidence_level": 0.9
   }
   ```

2. **在 Proposal 阶段评估**
   - Proposal 已有 `status` 字段
   - 可以通过 status 表达不确定性

### 11.2 Ambiguity Handling

**低置信度表达**:
- "嗯，可以吧"
- "也许吧"
- "可能可以"

**处理规则**:
1. 不直接形成 Candidate
2. 存入 Context，等待更高置信度的确认
3. 如果长时间无明确确认，标记为"待澄清"

**中等置信度表达**:
- "我觉得 A 更好"
- "我倾向于方案 A"

**处理规则**:
1. 形成 Candidate，标注为"偏好"而非"决策"
2. 在 observation_type 中使用 `preference` 而非 `decision`

---

## 12. Temporal Semantics

### 12.1 用户事实的变化

**场景**:
```
T1: "我使用 PostgreSQL。"
T2: "我改成 SQLite 了。"
```

**处理**:
1. T1 的 Candidate 保持历史状态
2. T2 的 Candidate 更新当前状态
3. 通过 Memory Evolution 建立 superseded 关系

### 12.2 与 Historical Memory Evolution 的兼容

**当前设计**:
- MemoryNode 有 `status`：active, candidate, deprecated, superseded, orphaned
- MemoryRelationship 有 `relationship_type`：supports, derived_from, contradicts, attenuates

**User Fact Boundary 的影响**:
- 不需要修改现有 Schema
- User Fact 的变化通过新的 Candidate 表达
- 旧的 Candidate 保持历史状态
- 通过 Evolution Engine 建立 superseded 关系

### 12.3 否定状态的表达

**场景**:
```
T1: "我使用 PostgreSQL。"
T2: "我不使用 PostgreSQL 了。"
```

**处理**:
1. 形成两个 Candidate:
   - C1: "用户曾经使用 PostgreSQL"
   - C2: "用户不再使用 PostgreSQL"
2. 通过 MemoryRelationship 表达矛盾关系
3. 不覆盖 C1，而是标记为 superseded

---

## 13. Semantic Classification Matrix

| User Expression | User-owned? | Requires Context? | Candidate-worthy? | Confidence | Observation Type |
|----------------|-------------|-------------------|-------------------|------------|-----------------|
| 我使用 PostgreSQL | ✅ | ❌ | ✅ | High | fact |
| 我喜欢 Python | ✅ | ❌ | ✅ | High | preference |
| 我决定使用 A | ✅ | ❌ | ✅ | High | decision |
| 对，就这样 | ✅ | ✅ | ✅ | High | decision |
| 好 | ⚠️ | ✅ | ⚠️ | Medium | decision (conditional) |
| 可以 | ⚠️ | ✅ | ⚠️ | Medium | preference |
| 知道了 | ❌ | ✅ | ❌ | Low | N/A |
| 不要这个 | ✅ | ✅ | ✅ | High | rejection |
| 我是说 B | ✅ | ✅ | ✅ | High | correction |
| 我只是考虑 | ✅ | ❌ | ✅ | Medium | intent |
| 如果以后需要，我会用 A | ⚠️ | ❌ | ⚠️ | Low | conditional fact |
| 假设我使用 A | ❌ | ❌ | ❌ | Low | hypothetical |
| 我朋友使用 A | ❌ | ❌ | ❌ | N/A | third-party |
| 你刚才说我使用 A | ❌ | ✅ | ❌ | N/A | quoted |
| 我觉得 A 更好 | ✅ | ❌ | ✅ | Medium | preference |

**关键原则**:
1. **User-owned = 否** → 不形成 Candidate
2. **User-owned = 是 + Context = 必需** → 需要 Context Window 辅助理解
3. **User-owned = 是 + Context = 不需要** → 可以直接形成 Candidate
4. **Confidence = 低** → 标记为待澄清，不直接进入 Memory

---

## 14. Implementation Prerequisites

### 14.1 Evidence Schema 扩展（P0）

**必要性**: 必须区分 user/assistant Evidence

**建议**:
```sql
-- 方案 A: 新增 role 字段
ALTER TABLE memory_hub.evidences ADD COLUMN role VARCHAR(20) CHECK (role IN ('user', 'assistant', 'system'));

-- 方案 B: 在 metadata 中存储
-- _meta 已经存在，可以存储 {"role": "assistant"}
```

**推荐**: 方案 B（metadata 中存储），避免 Schema 变更

### 14.2 导入逻辑修改（P0）

**必要性**: 必须保留 AI Evidence 作为 Context

**建议修改**:
```python
# 当前逻辑
if role != "user":
    continue

# 修改后
if role == "user":
    # 导入为 User Evidence
    item.metadata["role"] = "user"
elif role == "assistant":
    # 导入为 AI Evidence（用于 Context）
    item.metadata["role"] = "assistant"
    item.metadata["is_context_only"] = True  # 标记仅用于 Context
```

### 14.3 Context Window 扩展（P1）

**必要性**: Context Window 需要能够包含 AI Evidence

**建议**: 修改 Context Window 算法，允许包含 role='assistant' 的 Evidence

### 14.4 Reconstruction 语义转换（P1）

**必要性**: 需要 User-centric semantic interpretation

**建议**: 在 Reconstruction Engine 中新增语义转换逻辑

### 14.5 Candidate Formation 验证（P1）

**必要性**: 需要验证 User Fact Boundary

**建议**: 在 Candidate Formation 前添加验证步骤

---

## 15. Compatibility with Stage 2.1–2.3

### 15.1 与 Stage 2.1 的兼容性

**Stage 2.1 决策**:
- Reconstruction ↔ Candidate = 1:1
- Reconstruction.entity_id NOT NULL

**兼容性**: ✅ 完全兼容

User Fact Boundary 不影响这两个决策。

### 15.2 与 Stage 2.1A 的兼容性

**Stage 2.1A 决策**:
- Candidate 是固定 Snapshot
- 不因后续 Reconstruction 演化而改变

**兼容性**: ✅ 完全兼容

User Fact Boundary 只影响 Candidate 的内容，不影响其不可变性。

### 15.3 与 Stage 2.2 的兼容性

**Stage 2.2 决策**:
- Reconstruction ↔ Topic = N:M
- Topic 是独立持久化实体

**兼容性**: ✅ 兼容

User Fact 可以关联 Topic，但不影响 Topic 的独立存在。

### 15.4 与 Stage 2.3 的兼容性

**Stage 2.3 决策**:
- Context Window = Hybrid Model
- AI Evidence 可以进入 Context
- AI Evidence 不能直接成为 Candidate

**兼容性**: ✅ 完全兼容

User Fact Boundary 是 Stage 2.3 决策的具体化。

---

## 16. ADR Decision Statement

### 16.1 Decision

**ADR-Phase21-03: User Fact Boundary**

**Status**: Proposed

**Context**:
Phase 21 需要明确定义"什么内容可以成为 User Candidate"，以防止 AI 内容污染长期 Memory。

**Decision**:
采用 User-centric Semantic Interpretation 原则：

1. **AI Evidence 可以作为 Context，但不能直接成为 User Candidate**
2. **User-owned Semantic 必须经过 User-centric Interpretation**
3. **Confirmation/Rejection/Correction 必须明确语义归属**

**Schema Impact**:
- Evidence 表需要在 metadata 中存储 role 信息
- Candidate 表不需要修改
- Reconstruction 表不需要修改

**Implementation Prerequisites**:
1. [P0] 修改导入逻辑，保留 AI Evidence 并标记 role
2. [P0] 在 Evidence metadata 中存储 role 信息
3. [P1] 扩展 Context Window 支持 AI Evidence
4. [P1] 实现 User-centric Semantic Interpretation

**Consequences**:
- ✅ 防止 AI 内容污染 User Memory
- ✅ 明确 User-owned vs AI-owned 边界
- ✅ 支持复杂确认/否定/修正场景
- ⚠️ 需要修改导入逻辑
- ⚠️ 需要实现语义转换逻辑

**References**:
- `phase21-stage2.1-reconstruction-architecture.md`
- `phase21-stage2.1a-reconstruction-relationship-validation.md`
- `phase21-stage2.2-topic-definition.md`
- `phase21-stage2.3-context-window-definition.md`

---

## 17. Deferred Questions

| 问题 | 优先级 | 所属阶段 | 理由 |
|------|--------|----------|------|
| Evidence.role 字段实现 | P0 | Stage 3 | 影响 Context Window 核心功能 |
| 导入逻辑修改 | P0 | Stage 3 | 必须保留 AI Evidence |
| User-centric Semantic Interpretation 算法 | P1 | Stage 3 | 实现细节 |
| Conditional Fact 的 Evolution 规则 | P2 | Stage 4 | 依赖 Historical Memory Evolution |
| Ambiguity Resolution 策略 | P2 | Deferred | 非核心问题 |

---

## 最终回答

### Question 1: 什么是 User-owned Semantic？

**Answer**:
> User-owned Semantic = 用户通过语言行为明确表达的、可以归属为用户自身立场的语义内容。
>
> 包括：直接表达、确认、否定、修正、选择、偏好、决策、意图、信念、约束。

### Question 2: AI 内容什么时候可以影响 User Candidate？

**Answer**: 
当用户通过语言行为确认、采纳、选择 AI 内容时，经过 User-centric Semantic Interpretation 后，AI 内容可以影响 User Candidate。

**规则**:
- AI 建议 + 用户确认 → User Fact
- AI 建议 + 用户否定 → 否定状态的 User Fact
- AI 建议 + 用户未确认 → 不形成 User Candidate

### Question 3: "对，就这样"如何归属？

**Answer**: 
通过 Context Window 找到最近的 AI 建议，进行语义转换：
- AI: "建议使用 PostgreSQL"
- User: "对，就这样"
- Reconstruction: "用户确认采用 PostgreSQL"
- Candidate: "用户决定使用 PostgreSQL"

### Question 4: "可以 / 好 / 嗯 / 知道了"如何区分？

**Answer**:

| 表达 | 语义 | 处理方式 |
|------|------|----------|
| "好" | 确认 | 需要 Context，形成 User Fact |
| "可以" | 偏好/轻度确认 | 需要 Context，标记为 preference |
| "嗯" | 模糊确认 | 不直接形成 Candidate，标记为待澄清 |
| "知道了" | 中性认可 | 不形成 User Fact，只是信息接收 |

### Question 5: 用户否定 AI 时形成什么？

**Answer**: 
形成否定状态的 User Fact。

**示例**:
- AI: "你决定使用 PostgreSQL。"
- User: "不，我只是考虑。"
- Candidate: "用户仅在考虑 PostgreSQL（尚未决定）"

### Question 6: 用户修正 AI 时形成什么？

**Answer**: 
形成修正后的 User Fact。

**示例**:
- AI: "你决定使用 PostgreSQL。"
- User: "不对，我是说 MySQL。"
- Candidate: "用户决定使用 MySQL"

### Question 7: 用户只采纳 AI 建议的一部分时怎么办？

**Answer**: 
分解为多个 Candidate。

**示例**:
- AI: "我建议 A + B + C。"
- User: "A 可以，但 B 不行，C 再看看。"
- Candidate 1: "用户接受方案 A"
- Candidate 2: "用户否定方案 B"
- Candidate 3: "用户待定方案 C"

### Question 8: 第三方事实、假设、引用是否形成 User Candidate？

**Answer**: 
- **第三方事实**: 否（不是用户自身的事实）
- **假设**: 否（不是明确事实）
- **引用**: 否（只是转述，除非用户明确要求保留）

### Question 9: Negative / Uncertain User State 是否可以成为 Candidate？

**Answer**: 
**是**。

**示例**:
- "用户不再使用 PostgreSQL"（否定状态）
- "用户仅在考虑 PostgreSQL"（不确定状态）
- "用户尚未决定"（悬置状态）

### Question 10: User Fact 变化后如何与 Historical Memory Evolution 兼容？

**Answer**: 
- 旧的 Candidate 保持历史状态
- 新的 Candidate 表达更新后的状态
- 通过 Memory Relationship 建立 superseded/contradicts 关系
- 不需要修改现有 Schema

### Question 11: Evidence.role 是否是实现 User Fact Boundary 的必要前置条件？

**Answer**: 
**是**（P0）。

**理由**:
- 没有 role 信息，无法区分 user/assistant Evidence
- 无法判断 AI 内容是否被用户确认
- Context Window 无法获得 AI 上下文

**实现方式**:
- 方案 A: 新增 role 字段（需要 Schema Migration）
- 方案 B: 在 metadata 中存储（无需 Schema 变更，推荐）

### Question 12: 哪些内容必须明确禁止进入 User Candidate？

**Answer**:

1. **纯 AI statement** — "建议使用 PostgreSQL"
2. **AI recommendation without user adoption** — "我推荐 A"
3. **Hypothetical statement** — "如果以后需要..."
4. **Quoted third-party statement** — "我朋友用 PostgreSQL"
5. **Roleplay** — "假设我是数据库..."
6. **User merely repeating AI words without semantic commitment** — "你说得对（但没有具体确认内容）"
7. **Ambiguous acknowledgment** — "嗯"、"知道了"（单独出现时）
8. **Informational statement about someone else** — "公司规定..."

---

*本报告为只读调查，不修改任何代码、数据库、Schema、测试或设计文档。*
*发现的 Gap（Evidence.role 缺失）需要 Stage 3 实现。*

---

**STOP** — 不编码、不提交 Git，等待下一步指示。
