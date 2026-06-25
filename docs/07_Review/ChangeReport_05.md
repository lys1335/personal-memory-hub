# ChangeReport_05 — Review 变更报告

> **日期**: 2026-06-18  
> **触发文档**: `05_MemoryLifecycle_ReflectionEngine.md`  
> **被 Review 文档**: `01`、`02`、`03`、`04`  
> **Review 范围**: 结构冲突、名称冲突、设计冲突、过时描述

---

## 修改文档

| 文档 | 修改状态 | 修改行数 |
|------|----------|----------|
| `02_MemoryEngine_ContextBuilder.md` | ✅ 已修改 | 4 处 |
| `03_Entity_MemoryGraph.md` | ✅ 已修改 | 2 处 |
| `04_Schema_Archive_Reflect.md` | ✅ 已修改 | 4 处 |
| `01_MemoryHub_Foundation.md` | ❌ 无需修改 | — |

---

## 修改原因

05 引入了五个核心新概念，与已有文档产生设计冲突：

1. **Evidence Based Memory Principle** — 废弃所有 Time Based Memory 设计
2. **Three-Score Separation** — confidence/importance/signal_strength 三套评分独立
3. **State Is Runtime** — State 不是持久化实体，是 Belief + Current Context 的激活结果
4. **Light Reflect 触发条件变更** — 从"每次 Conversation 后"改为"Queue 满时触发"
5. **Memory Ingestion Pipeline** — 完整的 8 阶段 Pipeline 定义

---

## 修改内容

### 02_MemoryEngine_ContextBuilder.md

#### 修改 1：Belief JSON 示例增加 Evidence 字段

**原因**：05 第 3 章规定 Pattern 与 Belief 必须拥有 `support_count`/`support_entities`/`support_areas` 字段。

**变更**：

```diff
 {
   "belief": "用户倾向先POC后投入开发",
   "confidence": 0.8,
+  "support_count": 3,
+  "support_entities": ["ent_001", "ent_002"],
+  "support_areas": ["area_ai", "area_work"],
   "support_evidence": ["observation_001", "observation_002", "observation_003"],
   "contradict_evidence": []
 }
```

#### 修改 2：Current State 推导公式更新

**原因**：05 第 12 章明确 `State = Belief + Current Context`，且 State 不是持久化实体。

**变更**：

```diff
-Current State = f(Observations, Beliefs)
+State = Belief + Current Context
```

增加注释："State 不是独立的持久化实体，而是 Belief 在当前上下文中的运行时激活结果（参见 05 第 12 章）"。

#### 修改 3：数据流总结更新

**原因**：05 引入了 Evidence Links 作为横向关联的新维度。

**变更**：

```diff
-Entity = Observations + Beliefs + Current State
+Entity = Observations + Beliefs + State（State = Belief + Current Context，参见 05 第 12 章）

-横向关联：Tag（跨 Area/Project）+ Relationship（图边）
+横向关联：Tag（跨 Area）+ Relationship（图边）+ Evidence Links（跨 Level）
```

#### 修改 4：架构图 Layer 2 名称统一

**原因**：05 中不再有"Project Memory"的概念，Layer 2 统一为 Entity Memory。

**变更**：`Layer2: ProjectMemory 30%` → `Layer2: EntityMemory 30%`

#### 修改 5：02 版本号 1.2 → 1.3

---

### 03_Entity_MemoryGraph.md

#### 修改 1：ADR-004 L4 State 描述

**原因**：05 第 12 章明确 State 是运行时激活，非持久化实体。

**变更**：

```diff
-| L4 | State | 实体的当前状态结论 |
+| L4 | State | 实体的当前状态结论（运行时激活，非持久化实体，参见 05 第 12 章） |
```

#### 修改 2：附录 B 术语表同步

**变更**：

```diff
-| State (L4) | 实体的当前状态结论 |
+| State (L4) | 实体的当前状态结论（运行时激活，非持久化实体，参见 05 第 12 章） |
```

#### 修改 3：03 版本号 1.1 → 1.2

---

### 04_Schema_Archive_Reflect.md

#### 修改 1：Reflect 分级触发条件

**原因**：05 第 10 章明确 Light Reflect 是 Queue 满时触发，不是每次 Conversation 后。

**变更**：

```diff
-| 轻 | Light Reflect | 每次 Conversation 结束后 | 快速分类、初步 Pattern 提取 |
+| 轻 | Light Reflect | Queue 满（≥N 条 Observation）或兜底定时 | 快速聚类、生成候选 Pattern |
```

#### 修改 2：核心任务名称

**原因**：05 第 12 章明确 State 不是"Refresh"而是"Activation"。

**变更**：

```diff
-| State Refresh | 刷新实体当前状态 | L4 State |
+| State Activation | 评估 Belief 是否应激活为 State | 运行时 |
```

#### 修改 3：Memory Cleanup → Memory Verification

**原因**：05 第 1.3 章明确废弃了基于时间的淘汰机制。

**变更**：

```diff
-| Memory Cleanup | 清理无效或过时的认知 | 标记废弃 |
+| Memory Verification | 验证无效或过时的认知（基于证据而非时间） | 标记废弃 |
```

#### 修改 4：memory_relationships 关系类型

**原因**：05 第 12 章明确 State 是运行时激活，不持久化存储，`supersedes` 不适用。

**变更**：

```diff
-| `supersedes` | 替代 | New State supersedes Old State |
+| `attenuates` | 减弱 | 新证据削弱原有 Belief 的置信度 |
```

#### 修改 5：04 版本号 1.0 → 1.1

---

## 影响分析

### 对整体架构的影响

| 影响维度 | 说明 | 严重度 |
|----------|------|--------|
| 数据模型 | 无影响。05 不改变表结构，只改变语义解释 | 低 |
| API 契约 | 无影响。reflect() 行为细节在 05 中深化，但接口签名不变 | 低 |
| 检索排序 | 无影响。04 的 Final Score 公式已包含 Importance，05 的三套评分体系补充了其计算方式 | 低 |
| Reflect 触发 | **已修正**。04 原"每次 Conversation 后"改为"Queue 满时触发" | 中 |
| State 语义 | **已修正**。02/03 中 State 从"持久化结论"更正为"运行时激活" | 中 |
| 淘汰机制 | **已修正**。04 中"Memory Cleanup"改为"Memory Verification"，基于证据而非时间 | 低 |

### 无需修改的文档

**01_MemoryHub_Foundation.md**：

01 是宏观分类视角，定义的是记忆类型的性质（Objective/Knowledge/Cognitive），不涉及具体实现细节。05 的 Evidence Based Memory、Scoring Engine、Reflection Workflow 等内容在 01 的抽象层级上不构成冲突。

01 第 9 章"生命周期设计"中 Daily 30~90 天的时间机制保留——因为 Daily 是短期缓存，不是长期记忆，时间机制在此场景下仍然合理。

### 文档关系矩阵

| 文档 | 关注点 | 与 05 的关系 |
|------|--------|-------------|
| 01 | 宏观分类 | 互补（01 定义"是什么"，05 定义"怎么演化"） |
| 02 | API + Context | 已修正（State 公式、Belief 结构、Layer 2 命名） |
| 03 | 数据建模 | 已修正（L4 State 运行时性质） |
| 04 | Schema | 已修正（Reflect 触发条件、任务命名、关系类型） |
| 05 | Lifecycle + Reflect | 本轮新建 |
