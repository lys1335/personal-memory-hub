# Phase 20 — Pre-Implementation Boundary Review（补充）

## 执行摘要

本轮 READ-ONLY 调查通过检索设计文档和 Hermes 记忆，确认了 `orphaned` 状态的权威定义。
核心发现：
1. **orphaned 是合法状态**，但**代码未实现状态转换**
2. **deprecated 不是 Candidate 的合法状态**
3. **Legacy Evidence Candidates 应标记为 orphaned（而非删除）**

---

## 1. orphaned 状态的权威定义

### 1.1 设计文档定义

**来源**：`docs/01_Architecture/07_Boundary_Review.md` 第 2.7 节 P7: No Orphan Memory

#### P7: No Orphan Memory

**决策编号**: ADR-018  
**状态**: Final Decision  
**日期**: 2026-06-22

**核心原则**：每个 Memory 至少关联一个 Evidence。

#### 禁止的情况

```
❌ Memory 存在，但没有 Evidence
❌ Memory 存在，但 Evidence 已删除
❌ Memory 存在，但证据链断裂
```

#### 处理方式（权威定义）

| 情况 | 处理方式 |
|------|----------|
| 无 Evidence 的 Memory | 不得创建 |
| **Evidence 被删除** | **Memory 标记为 orphan，进入维护队列** |
| **证据链断裂** | **Memory 标记为 broken_chain，进入维护队列** |

**关键结论**：
```
orphaned 不是删除，而是标记为"需要维护"的状态
标记后进入维护队列，等待人工审核处理
```

### 1.2 Candidate Schema 定义

**来源**：`docs/02_Data_Model/09_Database_Physical_Design.md` 第 09.11.1 节

```
candidates.status | candidate, confirmed, archived, orphaned | 候选状态
```

**验证**：
- Repository 层：`valid_statuses = ("candidate", "confirmed", "archived", "orphaned")`
- ORM 模型：`status: Mapped[str] = mapped_column(String(20), default="candidate")`
- 数据库表：无 CHECK 约束限制 status 值（只有 type 约束）

### 1.3 orphaned 的语义澄清

| 概念 | 正确理解 | 错误理解 |
|------|---------|---------|
| orphaned | 证据链断裂，等待维护 | ❌ 删除或废弃 |
| orphaned | 进入维护队列 | ❌ 永久无效 |
| orphaned | 可人工审核后恢复 | ❌ 不可恢复 |
| orphaned | 不再进入 Evolution Scope | ✅ 正确 |

**设计意图**：
```
orphaned = "证据链断裂，需要人工审核"
         ≠ "删除" 或 "永久无效"
```

---

## 2. deprecated 状态检查

### 2.1 Candidate 状态列表

**合法值**（design 文档定义）：
```
candidate, confirmed, archived, orphaned
```

**注意**：`deprecated` **不在** Candidate 的合法状态列表中。

### 2.2 Memory Node 状态列表

**合法值**（design 文档定义）：
```
active, candidate, deprecated, superseded, orphaned
```

**注意**：`deprecated` **在** Memory Node 的合法状态列表中。

### 2.3 关键区分

| 实体类型 | 合法 status | deprecated? |
|---------|-------------|-------------|
| Candidate | candidate, confirmed, archived, orphaned | ❌ 不存在 |
| Memory Node | active, candidate, deprecated, superseded, orphaned | ✅ 存在 |

**结论**：
```
deprecated 是 Memory Node 的状态，不是 Candidate 的状态。
Proposal 也没有 deprecated 状态。
```

---

## 3. Proposal 状态检查

### 3.1 当前 Proposal 状态

**代码实际使用**：
- `pending` — 创建时默认值
- `approved` — approve_proposal() 更新
- `rejected` — reject_proposal() 更新

**没有 CHECK 约束**，但代码未定义其他状态。

### 3.2 deprecated 在 Proposal 中的可用性

**结论**：
```
❌ Proposal 没有 deprecated 状态
❌ 不能使用 deprecated 标记断裂证据的 Proposal
```

---

## 4. Legacy Evidence Candidates 分类结果

### 4.1 重新分析

**之前假设**：不能自动 orphaned

**基于设计文档的新理解**：
- orphaned = 证据链断裂，进入维护队列
- **这正是 Legacy Evidence Candidates 的状态**

### 4.2 新的分类方案

| 分组 | 条件 | 状态 | 处理方式 |
|------|------|------|---------|
| **A** | evidence_chain 全部不存在 | candidate | 保持，等待迁移 |
| **B** | evidence_chain 部分存在 | candidate | 保持，正常处理 |
| **C** | 已有 pending Proposal | candidate | 迁移 candidate_id |
| **D** | 无 Proposal | candidate | 正常进入 Evolution |

### 4.3 关键判断

```
Evidence 不存在 ≠ Candidate 应 orphaned
原因：
1. Legacy UUID 可能来自早期导入（数据迁移问题）
2. 不能确定是否为"证据链断裂"还是"数据丢失"
3. 应保留数据，等待人工审核确认
```

**建议**：
- **不自动 orphaned**
- **标记为需要审核**（通过 metadata 或 Dashboard 警告）
- **等待人工确认数据来源**

---

## 5. 事务边界确认

### 5.1 approve_proposal() 事务流

**当前实现**：
```python
async with engine.begin() as conn:
    # Step 1: Update proposal status to 'approved'
    await conn.execute(text("UPDATE proposals SET status = 'approved'..."))
    
    # Step 2: Create MemoryNode
    await conn.execute(text("INSERT INTO memory_nodes..."))
    
    # ❌ 缺失：没有更新 candidates.status = 'confirmed'
```

**设计期望**（根据文档）：
```
Proposal approved
    ↓
MemoryNode 创建成功
    ↓
Candidate → confirmed
```

**问题**：代码未实现 Candidate 状态更新。

### 5.2 reject_proposal() 事务流

**当前实现**：
```python
async with engine.begin() as conn:
    # Step 1: Update proposal status to 'rejected'
    await conn.execute(text("UPDATE proposals SET status = 'rejected'..."))
    
    # ❌ 缺失：没有更新 candidates.status = 'orphaned'
```

**设计期望**（根据文档）：
```
Proposal rejected
    ↓
Candidate → orphaned（进入维护队列）
```

**问题**：代码未实现 Candidate 状态更新。

### 5.3 事务一致性评估

| 操作 | Proposal | MemoryNode | Candidate | 一致性 |
|------|----------|------------|-----------|--------|
| Approve | ✅ approved | ✅ created | ❌ 仍为 candidate | **不一致** |
| Reject | ✅ rejected | - | ❌ 仍为 candidate | **不一致** |

**设计缺口**：
1. approve 成功后，Candidate 应变为 confirmed
2. reject 成功后，Candidate 应变为 orphaned
3. 当前代码未实现这两步

---

## 6. Evolution Scope 规则验证

### 6.1 当前规则

```sql
SELECT * FROM candidates
WHERE workspace_id = :wid
AND status IN ('candidate', 'pending')
ORDER BY created_at ASC
LIMIT :limit;
```

### 6.2 三条路径验证

**路径 A: Proposal pending → Evolution #2**
```
Candidate A (candidate)
  → Proposal #1 (pending)
  → Evolution #2
  → _acquire_scope() 查询: status='candidate' ✓
  → Candidate A 仍在 scope（无去重）❌
  → 生成 Proposal #2（重复）❌
```

**路径 B: Proposal rejected → Evolution #3**
```
Candidate A (candidate)
  → Proposal #1 (rejected)
  → Candidate 状态未变（仍为 candidate）❌
  → Evolution #3
  → _acquire_scope() 查询: status='candidate' ✓
  → Candidate A 仍在 scope
  → 可能再次生成 Proposal ❌
```

**路径 C: Proposal approved → Evolution #4**
```
Candidate A (candidate)
  → Proposal #1 (approved)
  → MemoryNode created
  → Candidate 状态未变（仍为 candidate）❌
  → Evolution #4
  → _acquire_scope() 查询: status='candidate' ✓
  → Candidate A 仍在 scope（重复处理）❌
```

### 6.3 新规则设计（需要实施）

```sql
-- 新增 candidate_id FK 后
SELECT * FROM candidates c
WHERE c.workspace_id = :wid
AND c.status = 'candidate'
AND NOT EXISTS (
    SELECT 1 FROM proposals p
    WHERE p.candidate_id = c.id
    AND p.status = 'pending'
)
ORDER BY c.created_at ASC
LIMIT :limit;
```

---

## 7. 需要用户确认的决策（更新）

### 决策 1: Legacy Evidence Candidates 处理策略（更新）

**问题**：8,829 个引用不存在 Evidence 的 Candidates 如何处理？

| 选项 | 方案 | 风险 | 推荐度 |
|------|------|------|--------|
| **A** | 保持 candidate，标记 warning | 低 | ⭐⭐⭐⭐ |
| **B** | 自动标记 orphaned | 中（可能误判） | ⭐⭐ |
| **C** | 批量删除 | 极高 | ❌ |

**推荐**：**A**（保留等待人工审核）
- Legacy UUID 来源不确定（可能是历史导入数据）
- 不应在未确认来源前自动 orphaned
- Dashboard 显示"证据链断裂"警告

---

### 决策 2: 事务边界补全（确认）

**问题**：approve/reject 后是否需要立即更新 Candidate 状态？

| 选项 | 方案 | 事务影响 | 推荐度 |
|------|------|----------|--------|
| **A** | 同一事务内更新 | 强一致性 | ⭐⭐⭐⭐ |
| **B** | 异步更新 | 最终一致性 | ⭐⭐ |
| **C** | 暂不更新 | 状态延迟 | ⭐ |

**推荐**：**A**
- 符合设计文档的"Proposal approved → Candidate confirmed"流程
- 确保事务一致性

---

### 决策 3: 92 个 Pending Proposals 处理（确认）

| 选项 | 方案 | 推荐度 |
|------|------|--------|
| **A** | 保留所有，迁移 candidate_id，Dashboard 标记断裂证据 | ⭐⭐⭐⭐ |
| **B** | 删除断裂证据的 Proposal | ⭐⭐ |
| **C** | 批量重置为 candidate | ⭐ |

**推荐**：**A**
- 保留历史数据
- 等待人工审核

---

### 决策 4: Schema 变更顺序（确认）

| 顺序 | 方案 | 风险 | 推荐度 |
|------|------|------|--------|
| **A** | candidate_id → Scope 去重 → 状态转换 | 低 | ⭐⭐⭐⭐ |
| **B** | 状态转换 → candidate_id → Scope 去重 | 中 | ⭐⭐ |
| **C** | 同时进行 | 高 | ❌ |

**推荐**：**A**
- 分阶段实施，降低风险
- 每阶段可独立验证

---

## 8. 最终结论

### 8.1 orphaned 状态的权威定义

**设计文档明确定义**：
```
orphaned = 证据链断裂，进入维护队列
         ≠ 删除
         ≠ 永久无效
```

**Candidate 的 orphaned 状态**：
- 合法状态之一（design 文档定义）
- 用于标记证据链断裂的 Candidate
- 进入维护队列，等待人工审核

### 8.2 代码与设计的不一致

| 设计期望 | 代码实际 | 差距 |
|---------|---------|------|
| reject → candidate orphaned | reject 不更新 candidate | **P0** |
| approve → candidate confirmed | approve 不更新 candidate | **P0** |
| orphaned 进入维护队列 | orphaned 从未被设置 | **P1** |

### 8.3 建议实施路径

**Phase 1: Schema 基础**
1. 添加 `proposals.candidate_id` FK
2. 添加索引和唯一约束
3. 数据迁移脚本

**Phase 2: 状态转换补全**
1. approve_proposal() 添加 Candidate 更新
2. reject_proposal() 添加 Candidate 更新
3. 单元测试

**Phase 3: Scope 去重**
1. 修改 _acquire_scope() 查询
2. 添加 NOT EXISTS 子查询
3. 性能测试

**Phase 4: 数据清理（可选）**
1. 分析 92 个 pending proposals
2. 标记断裂证据的 Proposal
3. 人工审核后决定去留

---

## 9. 约束检查清单

### 已遵守的约束
- ✅ 未引入 processed 状态
- ✅ 未修改现有四状态定义
- ✅ 未改变既有生命周期语义
- ✅ 未执行任何数据库修改
- ✅ 未修改代码
- ✅ 未运行 Evolution
- ✅ 未删除任何 Proposal 或 Candidate

### 待用户确认的事项
- ⏳ 决策 1: Legacy Evidence Candidates 处理策略
- ⏳ 决策 2: 事务边界补全方案
- ⏳ 决策 3: 92 个 Pending Proposals 分类策略
- ⏳ 决策 4: Schema 变更实施顺序

---

**调查状态**: 完成
**修改状态**: 无（只读调查）
**下一步**: 等待用户确认四项决策后进入 Implementation
