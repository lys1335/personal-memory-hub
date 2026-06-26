# Personal AI Memory Hub — Boundary Review 架构边界定义

> **版本**: 1.0  
> **日期**: 2026-06-22  
> **阶段**: 第七阶段  
> **状态**: 已确认  
> **作者**: 系统架构组

---

## 1. 文档目的

本文档定义 Memory Hub 的**架构边界**（Architectural Constraints），明确 Memory Hub 的职责范围与禁止范围。

本文档是独立的架构约束文档，不修改 01~06 中的任何设计决策，也不修改 07 Candidate Schema 文档。

### 1.1 目标读者

* 架构师 — 理解 Memory Hub 的定位与边界
* 工程师 — 明确实现时的职责划分
* 评审者 — 验证设计决策的合理性

### 1.2 约束效力

本文档中的原则为**架构约束**（Architectural Constraints），具有最高优先级。当与任何其他设计决策冲突时，以本文档为准。

---

## 2. Memory Hub 定位

### 2.1 P1: Memory Hub Is Memory Infrastructure

**决策编号**: ADR-012  
**状态**: Final Decision  
**日期**: 2026-06-22

Memory Hub 定位为 **Memory Infrastructure**（记忆基础设施）。

#### 2.1.1 负责范围

| 职责 | 说明 |
|------|------|
| Observe | 观察并记录输入信息 |
| Store | 持久化存储记忆 |
| Retrieve | 根据查询检索记忆 |
| Reflect | 对记忆进行内部整理与推导 |
| Archive | 对记忆进行归档管理 |

#### 2.1.2 非负责范围

| 非职责 | 说明 |
|--------|------|
| Planning | 不进行任务规划 |
| Decision Making | 不进行决策 |
| Goal Management | 不管理目标 |
| Task Management | 不管理任务 |
| Tool Execution | 不执行工具调用 |

#### 2.1.3 Architecture Rationale

**为什么 Memory Hub 必须是基础设施？**

| 考量 | 说明 |
|------|------|
| 单一职责 | Memory Hub 专注于记忆，不分散注意力到其他能力 |
| 可替换性 | 基础设施可以被替换而不影响上层 Agent 的逻辑 |
| 安全性 | 记忆基础设施不应具备行动能力，降低风险 |
| 可维护性 | 职责清晰，便于独立测试和演进 |

**为什么禁止 Planning / Decision Making / Tool Execution？**

* 这些是 Agent 的核心能力，不是记忆系统的职责。
* 如果 Memory Hub 同时负责记忆和行动，将导致职责混乱、难以测试、难以替换。
* Agent 应当独立于 Memory Hub 存在，可以自由替换。

---

### 2.2 P2: Memory Hub Does Not Act

**决策编号**: ADR-013  
**状态**: Final Decision  
**日期**: 2026-06-22

Memory Hub **不主动改变外部世界**。

#### 2.2.1 允许的行为

| 行为 | 说明 |
|------|------|
| Observe | 观察输入信息 |
| Record | 记录信息到记忆系统 |
| Organize | 组织记忆的结构 |
| Reflect | 对记忆进行内部推导 |
| Retrieve | 检索并输出记忆 |

#### 2.2.2 禁止的行为

| 禁止行为 | 说明 |
|----------|------|
| Decide | 不做决策 |
| Recommend | 不做推荐 |
| Plan | 不做计划 |
| Execute | 不执行任何操作 |

#### 2.2.3 Boundary Examples

**允许的输出**:

```
✅ "用户在过去 30 天内讨论了 5 次关于 Supabase 的决策。"
✅ "用户倾向于先做 POC 再投入开发，置信度 0.85。"
✅ "以下是与当前查询相关的 3 条记忆。"
```

**禁止的输出**:

```
❌ "建议你采用 Supabase 作为后端。"
❌ "你应该先做 POC 再投入开发。"
❌ "我为你生成了以下行动计划。"
❌ "我已经帮你更新了项目状态。"
```

#### 2.2.4 Architecture Rationale

**为什么 Memory Hub 不能做出推荐或决策？**

| 考量 | 说明 |
|------|------|
| 信任边界 | Memory Hub 的输出是记忆，不是建议。混淆两者会误导用户。 |
| 责任归属 | 决策的责任应由 Agent 承担，而非记忆系统。 |
| 可替换性 | 如果 Memory Hub 做了推荐，替换 Memory Hub 时需要重写推荐逻辑。 |
| 安全性 | 记忆系统不应具备影响用户决策的能力。 |

---

### 2.3 P3: Agent Outside Memory Hub

**决策编号**: ADR-014  
**状态**: Final Decision  
**日期**: 2026-06-22

Agent **永远位于 Memory Hub 之外**。

#### 2.3.1 正确的架构关系

```
Agent
  ↓
Memory Hub
```

#### 2.3.2 错误的架构关系

```
Memory Hub
  ↓
Agent
```

#### 2.3.3 支持的 Agent 列表

| Agent | 访问方式 |
|-------|----------|
| Hermes | 统一接口 |
| Open WebUI | 统一接口 |
| Claude | 统一接口 |
| Gemini | 统一接口 |
| Future Agent | 统一接口 |

所有 Agent 通过**统一接口**访问 Memory Hub，Memory Hub 不感知具体是哪个 Agent 在调用。

#### 2.3.4 Architecture Rationale

**为什么 Agent 必须在 Memory Hub 之外？**

| 考量 | 说明 |
|------|------|
| 解耦 | Agent 可自由替换，不受 Memory Hub 实现影响 |
| 独立性 | Agent 拥有自主决策权，不被记忆系统控制 |
| 可扩展性 | 未来可以接入多个不同的 Agent |
| 安全性 | 即使某个 Agent 被攻破，Memory Hub 仍保持中立 |

#### 2.3.5 Unified Interface

Memory Hub 对外暴露统一的接口规范，不区分调用者的身份：

| 接口 | 输入 | 输出 |
|------|------|------|
| `observe()` | Raw Conversation / Observation | Observation ID |
| `store()` | Memory Data | Memory ID |
| `retrieve()` | Query | Related Memories |
| `reflect()` | Observation Pool | Updated Memories |
| `archive()` | Memory Batch | Archive Result |

---

### 2.4 P4: Agent Cannot Directly Modify Memory

**决策编号**: ADR-015  
**状态**: Final Decision  
**日期**: 2026-06-22

Agent 可以**提交**数据，但**不允许直接修改** Memory 的状态。

#### 2.4.1 Agent 允许的提交

| 提交类型 | 说明 |
|----------|------|
| Raw Conversation | 原始对话内容 |
| Observation | 观察记录 |
| Document | 文档内容 |
| Summary | 总结内容 |

#### 2.4.2 Agent 禁止的操作

| 禁止操作 | 说明 |
|----------|------|
| Update Memory | 直接更新已有记忆 |
| Delete Memory | 直接删除记忆 |
| Change Score | 直接修改评分（confidence / importance / signal_strength） |
| Archive Memory | 直接归档记忆 |

#### 2.4.3 Memory 状态变更的唯一途径

```
Agent 提交数据
  ↓
Memory Hub 内部流程
  ↓
Ingestion Pipeline（Chunking → Extraction → Entity Linking → Validation）
  ↓
Scoring Engine（计算三套评分）
  ↓
Reflection Engine（推导 Pattern / Belief）
  ↓
Memory 状态变更
```

**所有 Memory 状态变更只能通过 Memory Hub 内部流程完成，Agent 无法绕过此流程。**

#### 2.4.4 Architecture Rationale

**为什么 Agent 不能直接修改 Memory？**

| 考量 | 说明 |
|------|------|
| 数据完整性 | 防止 Agent 恶意篡改记忆 |
| 一致性 | 所有记忆变更经过统一的 Ingestion Pipeline 和 Scoring Engine |
| 可追溯性 | 所有变更都可追溯至内部流程，而非外部输入 |
| 安全性 | 即使 Agent 被攻破，也无法直接修改记忆 |

#### 2.4.5 Boundary Examples

**Agent 可以做的**:

```
Agent → Memory Hub: "用户今天讨论了 Supabase 的部署方案。"
```

**Agent 不可以做的**:

```
Agent → Memory Hub: "将 Supabase 的记忆置信度提高到 0.95。"
Agent → Memory Hub: "删除这条过时的记忆。"
Agent → Memory Hub: "将这条 Observation 升级为 Belief。"
```

---

### 2.5 P5: Summary Is Observation

**决策编号**: ADR-016  
**状态**: Final Decision  
**日期**: 2026-06-22

Agent 生成的 Summary **不是事实**，它属于 Observation 层级。

#### 2.5.1 Summary 的处理流程

```
Agent Summary
  ↓
Observation Layer（L1）
  ↓
Internal Processing（Ingestion Pipeline）
  ↓
Memory Candidate
```

**Summary 不能直接成为 Long-Term Memory。**

#### 2.5.2 为什么 Summary 不是长期记忆？

| 原因 | 说明 |
|------|------|
| Summary 是推理产物 | Summary 是 Agent 对原始数据的加工，可能丢失细节 |
| Summary 可能出错 | Agent 的总结可能不准确或不完整 |
| Summary 需要验证 | 只有通过内部流程验证的 Summary 才能成为长期记忆 |
| 可追溯性 | 长期记忆必须追溯到原始 Conversation，而非 Summary |

#### 2.5.3 Architecture Rationale

**为什么 Summary 必须经过内部流程？**

| 考量 | 说明 |
|------|------|
| 证据链完整性 | Summary 本身不是证据，原始 Conversation 才是 |
| 防止信息丢失 | 直接存入 Summary 可能导致关键细节丢失 |
| 统一处理 | 无论输入是原始对话还是 Summary，都经过相同的 Ingestion Pipeline |
| 可验证性 | 内部流程确保所有长期记忆都有完整的证据链 |

#### 2.5.4 Boundary Examples

**正确的 Summary 处理**:

```
Agent Summary: "用户在过去一个月讨论了 5 次关于 Supabase 的决策。"
  ↓
进入 Observation Layer（L1）
  ↓
Ingestion Pipeline 提取事实
  ↓
Scoring Engine 计算评分
  ↓
Memory Candidate
  ↓
Reflection Engine 验证
  ↓
Pattern / Belief（如适用）
```

**禁止的做法**:

```
Agent Summary: "用户喜欢 Supabase。"
  ↓
直接存入 Knowledge Memory  ❌
```

---

### 2.6 P6: Evidence-Based Memory

**决策编号**: ADR-017  
**状态**: Final Decision  
**日期**: 2026-06-22

**所有 Memory 必须拥有 Evidence。**

#### 2.6.1 核心原则

> **No Evidence = No Memory**

#### 2.6.2 证据来源

任何长期记忆必须可追溯至以下来源之一：

| 证据来源 | 说明 |
|----------|------|
| Conversation | 原始对话记录 |
| Document | 用户上传的文档 |
| Observation | 已有的观察记录 |
| Other Evidence Sources | 其他可验证的证据源 |

#### 2.6.3 Evidence Chain

```
Long-Term Memory
  ↓ derived_from
Intermediate Evidence（Pattern / Belief）
  ↓ derived_from
Raw Observation（L1）
  ↓ originates_from
Conversation / Document / External Input
```

#### 2.6.4 Architecture Rationale

**为什么必须基于证据？**

| 考量 | 说明 |
|------|------|
| 可信度 | 没有证据支撑的记忆不可信 |
| 可追溯性 | 用户可以追溯每条记忆的原始来源 |
| 可证伪性 | 新证据可以推翻旧的记忆 |
| 可维护性 | 证据链断裂的记忆可以被识别和处理 |

---

### 2.7 P7: No Orphan Memory

**决策编号**: ADR-018  
**状态**: Final Decision  
**日期**: 2026-06-22

**每个 Memory 至少关联一个 Evidence。**

#### 2.7.1 禁止的情况

```
❌ Memory 存在，但没有 Evidence
❌ Memory 存在，但 Evidence 已删除
❌ Memory 存在，但证据链断裂
```

#### 2.7.2 处理方式

| 情况 | 处理方式 |
|------|----------|
| 无 Evidence 的 Memory | 不得创建 |
| Evidence 被删除 | Memory 标记为 orphan，进入维护队列 |
| 证据链断裂 | Memory 标记为 broken_chain，进入维护队列 |

#### 2.7.3 Architecture Rationale

**为什么不能有孤儿记忆？**

| 考量 | 说明 |
|------|------|
| 数据完整性 | 孤儿记忆是不可信的，破坏整个记忆系统的可信度 |
| 可维护性 | 孤儿记忆需要额外维护成本 |
| 用户体验 | 用户可能基于错误的孤儿记忆做出决策 |

---

### 2.8 P8: Reflection Is Memory Maintenance

**决策编号**: ADR-019  
**状态**: Final Decision  
**日期**: 2026-06-22

Reflection 是 **Memory Maintenance**，不是 Agent 行为。

#### 2.8.1 Reflection 允许的行为

| 允许行为 | 说明 |
|----------|------|
| Memory Consolidation | 合并重复的记忆 |
| Memory Merge | 合并相关的记忆 |
| Entity Merge | 合并重复的 Entity |
| Relationship Update | 更新 Entity 之间的关系 |
| Archive Decision | 决定是否归档记忆 |

#### 2.8.2 Reflection 禁止的行为

| 禁止行为 | 说明 |
|----------|------|
| Recommendation | 不做推荐 |
| Goal Creation | 不创建目标 |
| Task Creation | 不创建任务 |
| Tool Invocation | 不调用工具 |
| Decision Making | 不做决策 |

#### 2.8.3 Architecture Rationale

**为什么 Reflection 只能是 Memory Maintenance？**

| 考量 | 说明 |
|------|------|
| 职责分离 | Reflection 是记忆系统的内部整理，不是对外行动 |
| 安全性 | 限制 Reflection 的行为范围，防止记忆系统越界 |
| 可预测性 | Reflection 的行为范围明确，便于测试和验证 |
| 可维护性 | 职责清晰，便于独立演进 |

#### 2.8.4 Boundary Examples

**Reflection 可以做的**:

```
✅ "观察到 3 条关于 Supabase 的记忆，建议合并为 1 条 Pattern。"
✅ "发现两个 Entity 指向同一个对象，建议合并。"
✅ "这些记忆已超过 30 天，建议归档到 Monthly Archive。"
```

**Reflection 不可以做的**:

```
❌ "建议用户采用 Supabase。"
❌ "为用户创建以下目标。"
❌ "帮用户安排以下任务。"
❌ "调用 API 更新外部系统。"
```

---

### 2.9 P9: Memory Hub Is A Witness

**决策编号**: ADR-020  
**状态**: Final Decision  
**日期**: 2026-06-22

Memory Hub 的核心定位是 **Witness, Not Actor**。

#### 2.9.1 核心定位

| 维度 | Memory Hub | Agent |
|------|-----------|-------|
| 角色 | Witness（见证者） | Actor（行动者） |
| 职责 | 记忆与上下文 | 思考与决策 |
| 输出 | Context | Conclusion |
| 行为 | Observe / Record / Organize / Reflect / Retrieve | Plan / Decide / Execute |

#### 2.9.2 Memory Hub 的职责

| 职责 | 说明 |
|------|------|
| Observe | 观察并记录输入信息 |
| Record | 记录信息到记忆系统 |
| Organize | 组织记忆的结构 |
| Reflect | 对记忆进行内部推导 |
| Retrieve | 检索并输出记忆 |

#### 2.9.3 Memory Hub 的输出

```
Memory Hub 输出: Context（上下文）

Memory Hub 不输出: Conclusion（结论）
```

#### 2.9.4 Agent 的职责

| 职责 | 说明 |
|------|------|
| Think | 基于 Context 进行思考 |
| Decide | 做出决策 |
| Plan | 制定计划 |
| Execute | 执行操作 |

#### 2.9.5 Architecture Rationale

**为什么 Memory Hub 必须是 Witness？**

| 考量 | 说明 |
|------|------|
| 信任边界 | 记忆系统提供事实，Agent 提供判断。混淆两者会误导用户。 |
| 责任归属 | 决策的责任应由 Agent 承担。 |
| 可替换性 | Agent 可自由替换，Memory Hub 保持中立。 |
| 安全性 | 记忆系统不应具备影响用户决策的能力。 |

#### 2.9.6 Boundary Examples

**Memory Hub 的输出（Context）**:

```
✅ "用户在过去的 30 天内讨论了 5 次关于 Supabase 的决策。"
✅ "用户倾向于先做 POC 再投入开发，置信度 0.85。"
✅ "以下是与当前查询相关的 3 条记忆。"
```

**Agent 的输出（Conclusion）**:

```
✅ "基于你的历史偏好，我建议先做 POC 再投入开发。"
✅ "根据你过去的项目经验，Supabase 是一个合适的选择。"
✅ "我已经为你制定了以下行动计划。"
```

---

## 3. Non-Goals

以下事项**不在** Memory Hub 的职责范围内：

### 3.1 不在 Memory Hub 范围内的功能

| 非目标 | 说明 |
|--------|------|
| Agent 行为 | Memory Hub 不包含任何 Agent 逻辑 |
| 用户界面 | Memory Hub 不直接面向用户，通过 Agent 间接服务 |
| 通知系统 | Memory Hub 不发送通知 |
| 日程管理 | Memory Hub 不管理日程 |
| 邮件/消息处理 | Memory Hub 不处理邮件或消息 |
| 外部系统集成 | Memory Hub 不直接集成外部系统 |
| 用户认证 | Memory Hub 不负责用户认证 |
| 计费/账单 | Memory Hub 不涉及计费 |

### 3.2 不在 Memory Hub 范围内的决策

| 非目标 | 说明 |
|--------|------|
| 技术选型 | Memory Hub 不决定使用什么技术 |
| 架构决策 | Memory Hub 不参与架构设计 |
| 产品决策 | Memory Hub 不提供产品建议 |
| 商业决策 | Memory Hub 不提供商业建议 |
| 个人建议 | Memory Hub 不提供个人建议 |

---

## 4. Impact On Candidate Schema

### 4.1 Candidate Schema 的设计约束

本文档的边界定义对 Candidate Schema 产生以下影响：

#### 4.1.1 Constraint: Candidate 必须携带 Evidence

由于 **P6（Evidence-Based Memory）** 和 **P7（No Orphan Memory）**，Candidate Schema 必须包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| `evidence_source` | String | 证据来源类型（conversation / document / observation） |
| `evidence_id` | UUID | 证据的来源 ID |
| `evidence_chain` | Array | 完整的证据链（支持多级追溯） |

**理由**：任何 Memory Candidate 都必须能够追溯到原始证据。

#### 4.1.2 Constraint: Candidate 不能直接成为 Long-Term Memory

由于 **P5（Summary Is Observation）**，Candidate Schema 必须包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | Enum | `candidate` / `confirmed` / `archived` / `orphaned` |
| `verified_at` | Timestamp | 验证通过的时间 |
| `verified_by` | Enum | `rule_engine` / `reflection_engine` |

**理由**：Candidate 必须经过内部流程验证后才能成为长期记忆。

#### 4.1.3 Constraint: Candidate 不允许来自 Agent 直接写入

由于 **P4（Agent Cannot Directly Modify Memory）**，tasks 表必须包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| `ingested_by` | Enum | `ingestion_pipeline`（唯一合法值） |
| `ingestion_timestamp` | Timestamp | 通过 Ingestion Pipeline 的时间 |

**理由**：所有 Candidate 必须通过 Ingestion Pipeline 进入，Agent 无法直接写入。

#### 4.1.4 Constraint: Candidate 不允许被 Agent 修改

由于 **P4（Agent Cannot Directly Modify Memory）**，Candidate Schema 必须包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| `modified_by` | Enum | 仅限 `reflection_engine` / `maintenance_queue` |
| `modification_reason` | String | 修改原因 |

**理由**：只有 Memory Hub 内部流程可以修改 Candidate 的状态。

#### 4.1.5 Constraint: Candidate 的 Evidence 必须可验证

由于 **P6（Evidence-Based Memory）**，Candidate Schema 必须包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| `evidence_count` | Integer | 关联的证据数量（≥ 1） |
| `evidence_strength` | Float | 证据强度评分 |

**理由**：每个 Candidate 必须有至少一个可验证的证据。

### 4.2 总结

| 原则 | 对 Candidate Schema 的影响 |
|------|--------------------------|
| P1: Memory Infrastructure | Candidate 是 Memory 的一部分，不是 Agent 的一部分 |
| P2: No Acting | Candidate 不携带 Action 相关字段 |
| P3: Agent Outside | Candidate 的 `source_type` 不区分 Agent 身份 |
| P4: Agent Cannot Modify | Candidate 的 `ingested_by` 和 `modified_by` 限制为内部流程 |
| P5: Summary Is Observation | Candidate 的 `status` 必须经历 candidate → confirmed 的过程 |
| P6: Evidence-Based | Candidate 必须携带 `evidence_source` / `evidence_id` / `evidence_chain` |
| P7: No Orphan | Candidate 的 `evidence_count` 必须 ≥ 1 |
| P8: Reflection Is Maintenance | Candidate 的 `modified_by` 仅限 `reflection_engine` |
| P9: Witness, Not Actor | Candidate 不携带任何 Conclusion 相关字段 |

---

## 5. Future Extension Discussion

### 5.1 边界演化的可能性

#### 5.1.1 可能扩展的方向

| 方向 | 说明 | 是否需要修改边界 |
|------|------|-----------------|
| Multi-Agent Support | 支持多个 Agent 同时访问 Memory Hub | 否（P3 已支持） |
| Cross-Workspace Sharing | 跨 Workspace 共享记忆 | 否（属于 Memory Hub 内部职责） |
| External Evidence Sources | 支持外部证据源（API / IoT） | 否（属于 Observe 职责） |
| Memory Export | 导出记忆给 Agent 使用 | 否（属于 Retrieve 职责） |

#### 5.1.2 禁止扩展的方向

| 禁止方向 | 说明 | 违反的原则 |
|----------|------|-----------|
| Memory Hub 获得行动能力 | Memory Hub 可以直接修改外部世界 | P1 / P2 / P9 |
| Memory Hub 做决策 | Memory Hub 可以替用户做决策 | P2 / P9 |
| Agent 直接修改 Memory | Agent 可以绕过 Ingestion Pipeline | P4 |
| Summary 直接成为长期记忆 | 跳过内部验证流程 | P5 |
| 无证据的记忆 | 允许 Memory 没有 Evidence | P6 / P7 |
| Reflection 做推荐 | Reflection 可以输出建议 | P8 / P9 |

### 5.2 边界审查机制

为确保边界不被侵蚀，建议建立以下机制：

| 机制 | 说明 | 频率 |
|------|------|------|
| 代码审查 | 审查代码中是否有越界行为 | 每次提交 |
| 架构评审 | 审查新功能是否符合边界定义 | 每个版本 |
| 自动化测试 | 测试 Memory Hub 的输出不包含行动指令 | 每次构建 |
| 边界审计 | 定期检查 Memory Hub 的行为日志 | 每季度 |

---

## 6. Boundary Summary

### 6.1 职责矩阵

| 功能 | Memory Hub | Agent |
|------|-----------|-------|
| Observe | ✅ | ❌ |
| Record | ✅ | ❌ |
| Organize | ✅ | ❌ |
| Reflect | ✅ | ❌ |
| Retrieve | ✅ | ❌ |
| Archive | ✅ | ❌ |
| Think | ❌ | ✅ |
| Decide | ❌ | ✅ |
| Plan | ❌ | ✅ |
| Execute | ❌ | ✅ |
| Recommend | ❌ | ✅ |
| Goal Management | ❌ | ✅ |
| Task Management | ❌ | ✅ |
| Tool Execution | ❌ | ✅ |

### 6.2 边界一句话总结

> **Memory Hub 是 Witness，不是 Actor。它负责记忆，不负责思考。**

---

## 7. 与前序文档的关系

| 文档 | 引用关系 |
|------|----------|
| 01 | 记忆类型体系、生命周期、分类体系（本文档约束其实现方式） |
| 02 | Memory Engine API（本文档约束 API 的输出格式） |
| 03 | Entity / MemoryNode / Relationship 模型（本文档约束其数据来源） |
| 04 | Schema / Reflect / Archive（本文档约束 Reflect 的行为范围） |
| 05 | Lifecycle / Reflection Engine（本文档约束 Reflection 的边界） |
| 06 | Runtime Architecture（本文档约束 Online/Offline 的职责划分） |
| 07 (Candidate Schema) | 本文档对 Candidate Schema 施加约束（参见第 4 章） |

---

## 附录 A：ADR 索引

| 编号 | 主题 | 状态 |
|------|------|------|
| ADR-012 | Memory Hub Is Memory Infrastructure | Final Decision |
| ADR-013 | Memory Hub Does Not Act | Final Decision |
| ADR-014 | Agent Outside Memory Hub | Final Decision |
| ADR-015 | Agent Cannot Directly Modify Memory | Final Decision |
| ADR-016 | Summary Is Observation | Final Decision |
| ADR-017 | Evidence-Based Memory | Final Decision |
| ADR-018 | No Orphan Memory | Final Decision |
| ADR-019 | Reflection Is Memory Maintenance | Final Decision |
| ADR-020 | Memory Hub Is A Witness | Final Decision |
| ADR-012 | Engine 重新定义（Phase B） | Final Decision（Engine = Domain Capability，参见 10_1 第 6 章） |

---

## 附录 B：术语表

| 术语 | 说明 |
|------|------|
| Witness | Memory Hub 的角色定位：观察和记录，不行动 |
| Actor | Agent 的角色定位：思考和决策，采取行动 |
| Evidence | 支持 Memory 真实性的原始数据源 |
| Evidence Chain | 从 Memory 到原始证据的完整追溯路径 |
| Candidate | 尚未经过验证的 Memory 提议 |
| Memory Maintenance | Memory Hub 内部的整理和推导活动 |
| Architectural Constraint | 具有最高优先级的设计约束 |

---

## 附录 C：文档变更记录

| 版本 | 日期 | 变更说明 | 状态 |
|------|------|----------|------|
| 1.1 | 2026-06-26 | Phase B 修订：附录 A 补充 ADR-012（Engine 重新定义） | ✅ 已确认 |

---

*本文档仅记录已达成共识的设计决策，未涉及的内容不在本文档范围内。*

*本文档为独立文档，不修改 01~06 中的任何设计决策，也不修改 07 Candidate Schema 文档。*
