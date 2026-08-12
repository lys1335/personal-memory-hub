# Phase 20 — Candidate–Proposal Lifecycle Design

## 执行摘要

本轮为纯设计分析，不涉及代码修改、数据库变更或数据迁移。
目标是完成 Candidate → Evolution → Proposal → Review → Confirmed/Orphaned 的完整生命周期设计。

---

## 1. Current Model — 当前架构缺陷诊断

### 1.1 实体关系现状

```
┌─────────────┐         ┌─────────────┐
│  Candidate  │         │  Proposal   │
├─────────────┤         ├─────────────┤
│ id          │         │ id          │
│ workspace_id│         │ workspace_id│
│ entity_id   │         │ type        │
│ content     │         │ evidence_chain│
│ evidence_chain│       │ confidence  │
│ status      │         │ status      │
└─────────────┘         └─────────────┘
     │                         │
     │    ❌ 无正式关联         │
     │    (no candidate_id)    │
     └─────────────────────────┘
              伪关联：evidence_chain[0]
              (这是 Evidence ID，不是 Candidate ID)
```

### 1.2 缺失关系清单

| 缺失项 | 影响 | 严重程度 |
|--------|------|----------|
| `proposals.candidate_id` FK | 无法追溯 Proposal 来源 | P0 |
| Scope 去重检查 | 重复生成 Proposal | P0 |
| Candidate 状态转换 | 状态永远不更新 | P1 |
| Proposal 唯一约束 | 同 Candidate 可有多 pending | P1 |
| 关联查询索引 | 性能问题 | P2 |

### 1.3 当前数据问题

```
Candidates: 13,146 (全部 status='candidate')
Pending Proposals: 92 (全部 evidence_chain 有效或断裂)
重复 Candidate: 每次 Evolution 重新处理全部 13,146 个
```

---

## 2. Option Comparison — 方案比较

### 2.1 Option A: 逻辑去重（不增加 candidate_id）

**设计**：
```python
# 通过 evidence_chain + entity + content 匹配
SELECT c.* FROM candidates c
WHERE c.workspace_id = :wid
AND c.status = 'candidate'
AND NOT EXISTS (
    SELECT 1 FROM proposals p
    WHERE p.workspace_id = c.workspace_id
    AND p.entity = c.entity_id
    AND p.evidence_chain LIKE '%' || c.id || '%'
    AND p.status = 'pending'
)
```

**分析**：

| 维度 | 评估 | 说明 |
|------|------|------|
| 可靠性 | ⚠️ 低 | evidence_chain 不可靠（Legacy UUID 污染） |
| 误判率 | 高 | 可能漏判或误判 |
| 长期架构 | ❌ 不推荐 | 依赖字段内容匹配，脆弱 |
| Evidence-Based | ❌ 偏离 | 应基于 ID 关联，而非内容匹配 |
| 扩展性 | ❌ 差 | 新增字段需修改匹配逻辑 |

**结论**：**不推荐**。逻辑去重在证据链断裂时完全失效。

---

### 2.2 Option B: 添加 candidate_id FK（推荐）

**设计**：
```sql
-- Schema 变更
ALTER TABLE proposals
ADD COLUMN candidate_id UUID REFERENCES candidates(id);

-- 索引
CREATE INDEX idx_proposals_candidate_id ON proposals(candidate_id);
CREATE UNIQUE INDEX idx_proposals_one_pending_per_candidate
ON proposals(workspace_id, candidate_id)
WHERE status = 'pending';
```

**Scope 查询**：
```sql
SELECT * FROM candidates c
WHERE c.workspace_id = :wid
AND c.status = 'candidate'
AND NOT EXISTS (
    SELECT 1 FROM proposals p
    WHERE p.candidate_id = c.id
    AND p.status = 'pending'
)
LIMIT :limit;
```

**分析**：

| 维度 | 评估 | 说明 |
|------|------|------|
| Schema | ✅ 清晰 | 外键明确，符合关系型设计 |
| Repository | ✅ 简单 | 标准 JOIN / NOT EXISTS |
| Service | ✅ 清晰 | 创建 Proposal 时传入 candidate_id |
| Evolution Scope | ✅ 精确 | 基于 ID 去重，不依赖内容 |
| 查询性能 | ✅ 优秀 | 索引支持，O(log n) |
| 历史数据 | ⚠️ 需迁移 | 现有 92 个 pending proposals 需补填 candidate_id |

**结论**：**推荐**。符合 Evidence-Based Memory 原则。

---

### 2.3 Option C: 混合方案

**设计**：
- 添加 candidate_id FK（核心）
- 保留 evidence_chain 作为辅助证据引用
- 添加 last_evolution_at 时间戳到 Candidate（可选）

**分析**：
- 优点：信息完整，便于审计
- 缺点：增加复杂度

**结论**：可作为 Option B 的增强，非必须。

---

## 3. Recommended Model — 推荐方案

### 3.1 Cardinality 设计

**推荐**：**Candidate 1 : N Proposal（历史）**，但 **Candidate 1 : 1 Pending Proposal（同时）**

```
Candidate A
    ├── Proposal #1 (pending)     ← 当前生效
    ├── Proposal #2 (approved)    ← 历史（已创建 MemoryNode）
    ├── Proposal #3 (rejected)    ← 历史
    └── Proposal #4 (rejected)    ← 历史
```

**理由**：
1. **历史记录价值**：Rejected Proposal 包含人类反馈，可用于训练和优化
2. **Pending 唯一性**：避免同时处理同一 Candidate 的多个待审批提案
3. **审计追踪**：完整记录 Candidate 的演化历史

### 3.2 状态影响矩阵

| Proposal 事件 | Candidate 状态变化 | 说明 |
|---------------|-------------------|------|
| Proposal created (pending) | 无变化（仍为 candidate） | 等待审批 |
| Proposal approved | candidate → confirmed | 创建 MemoryNode |
| Proposal rejected | candidate → orphaned | 证据不足或错误 |
| Proposal expired（超时） | candidate → candidate | 可重新生成 |

### 3.3 关键设计原则

```
1. Pending Proposal 是 Candidate 的"锁"
   - 防止重复 Evolution
   - 等待人类或自动审批

2. Approved 后 Candidate 完成使命
   - 转为 confirmed
   - 不再进入 Evolution Scope

3. Rejected 后 Candidate 终止
   - 转为 orphaned
   - 标记为"尝试失败"
```

---

## 4. Candidate State Machine — 完整状态机

### 4.1 状态转换图

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
              ┌──────────┐                               │
              │ candidate │◄──────────────────────────────┘
              └────┬─────┘
                   │
                   │ Evolution 成功
                   │ 生成 Proposal (pending)
                   ▼
              ┌──────────┐     ┌──────────┐
              │ candidate │────▶│ candidate│◄── Proposal rejected
              │ (有pending │     │ (重新进入│    (→ orphanded)
              │  Proposal)│     │  Evolution)│
              └────┬─────┘     └──────────┘
                   │
                   │ Proposal approved
                   │ 创建 MemoryNode
                   ▼
              ┌──────────┐
              │confirmed │
              └──────────┘
                   │
                   │ 创建 MemoryNode 成功
                   ▼
              ┌──────────┐
              │  (停止)  │
              └──────────┘

其他状态：
  archived  — 手动归档（非 Evolution 路径）
  orphaned  — 证据失效或人工拒绝
```

### 4.2 状态转换表

| 转换 | 触发条件 | 执行层 | 事务边界 |
|------|---------|--------|---------|
| candidate → candidate | Evolution 创建 Proposal | Service | 单步 |
| candidate → confirmed | Proposal approved + MemoryNode created | Service | 两步提交 |
| candidate → orphaned | Proposal rejected | Service | 单步 |
| candidate → archived | 用户手动操作 | Service | 单步 |

### 4.3 特别注意：Rejected → Orphaned 的冲突

**现有设计**：
```
Proposal rejected → Candidate orphaned
```

**问题**：如果 Candidate orphaned 后，是否允许重新进入 Evolution？

**分析**：
- `orphaned` 语义："证据失效"或"被放弃"
- 如果新证据出现，应该允许重新成为 `candidate`
- 但这需要显式的"复活"机制

**建议**：
```
orphaned 状态应禁止自动重新进入 Evolution
如需重新处理，必须通过手动操作重置为 candidate
```

---

## 5. Evolution Scope Rule — 新的范围规则

### 5.1 Scope 查询规则

```sql
-- 新规则：排除已有 pending Proposal 的 Candidate
SELECT * FROM candidates c
WHERE c.workspace_id = :wid
AND c.status = 'candidate'
AND NOT EXISTS (
    SELECT 1 FROM proposals p
    WHERE p.candidate_id = c.id
    AND p.status = 'pending'
)
ORDER BY c.created_at ASC
LIMIT :limit
```

### 5.2 规则验证

**Human Review First 原则**：
- Pending Proposal 代表"等待人工审查"
- 不应在审查期间重新生成
- ✅ 符合原则

**Evidence-Based Memory 原则**：
- 基于 ID 关联，不依赖内容
- ✅ 符合原则

**Memory First 原则**：
- 确保每个 Candidate 有唯一评审路径
- ✅ 符合原则

**Long-Term Evolvability**：
- 支持 Proposal 历史记录
- ✅ 符合原则

### 5.3 Rejected Proposal 的处理

**设计**：
```
Proposal rejected → Candidate orphaned → 永久排除出 Evolution
```

**例外**：如果新证据出现，可通过手动操作重置为 `candidate`。

---

## 6. Proposal Lifecycle — 提案生命周期

### 6.1 完整生命周期

```
┌─────────────────────────────────────────────────────────────────┐
│                        Proposal Lifecycle                        │
└─────────────────────────────────────────────────────────────────┘

                    ┌──────────────┐
                    │   created    │ ← Evolution 引擎生成
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
              ┌────│   pending    │────┐
              │    └──────┬───────┘    │
              │           │            │
              │           ▼            │
              │    ┌──────────────┐    │
              │    │   approved   │    │
              │    └──────┬───────┘    │
              │           │            │
              │           ▼            │
              │    ┌──────────────┐    │
              │    │  confirmed   │    │
              │    │ (Candidate)  │    │
              │    └──────────────┘    │
              │                        │
              │                        │
              │    ┌──────────────┐    │
              └───▶│   rejected   │◀───┘
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │  orphaned    │
                   │ (Candidate)  │
                   └──────────────┘
```

### 6.2 状态同步矩阵

| Proposal 状态 | Candidate 状态 | MemoryNode | 说明 |
|--------------|---------------|------------|------|
| pending | candidate | - | 等待审批 |
| approved | candidate | - | 准备创建 |
| approved | confirmed | 已创建 | 完成 |
| rejected | orphaned | - | 终止 |

---

## 7. Historical Data Migration — 历史数据迁移策略

### 7.1 Candidate 分类

**分类标准**：
```sql
-- Group A: 有效 Evidence，无 Proposal
SELECT * FROM candidates c
WHERE c.status = 'candidate'
AND NOT EXISTS (
    SELECT 1 FROM proposals p 
    WHERE p.candidate_id = c.id AND p.status = 'pending'
)
AND EXISTS (
    SELECT 1 FROM evidences e 
    WHERE e.id = ANY(c.evidence_chain)
);

-- Group B: Legacy Evidence（不存在于 evidences 表）
SELECT * FROM candidates c
WHERE c.status = 'candidate'
AND NOT EXISTS (
    SELECT 1 FROM evidences e 
    WHERE e.id = ANY(c.evidence_chain)
);

-- Group C: 已有 pending Proposal
SELECT c.*, p.id as proposal_id
FROM candidates c
JOIN proposals p ON p.candidate_id = c.id
WHERE c.status = 'candidate'
AND p.status = 'pending';

-- Group D: 无 Proposal，证据有效
SELECT * FROM candidates c
WHERE c.status = 'candidate'
AND NOT EXISTS (
    SELECT 1 FROM proposals p WHERE p.candidate_id = c.id
)
AND EXISTS (
    SELECT 1 FROM evidences e WHERE e.id = ANY(c.evidence_chain)
);
```

**预期分布**：
| 分组 | 描述 | 预估数量 | 处理策略 |
|------|------|---------|---------|
| **A** | 有效证据，无 Proposal | ~4,000 | 正常进入 Evolution |
| **B** | Legacy Evidence | ~8,829 | 需清理或标记 |
| **C** | 已有 pending Proposal | 92 | 补填 candidate_id |
| **D** | 与 A 重叠 | 见 A | - |

### 7.2 迁移步骤（设计，不执行）

**Step 1: 添加字段**
```sql
ALTER TABLE proposals
ADD COLUMN candidate_id UUID REFERENCES candidates(id);
```

**Step 2: 迁移现有 Proposal**
```sql
-- 基于 entity + evidence_chain 匹配（近似匹配）
UPDATE proposals p
SET candidate_id = c.id
FROM candidates c
WHERE p.workspace_id = c.workspace_id
AND p.entity = c.entity_id
AND p.evidence_chain::text LIKE '%' || c.evidence_chain[0] || '%'
AND p.status = 'pending'
AND p.candidate_id IS NULL;
```

**Step 3: 验证**
```sql
-- 检查未匹配的 Proposal
SELECT COUNT(*) FROM proposals 
WHERE candidate_id IS NULL AND status = 'pending';
```

**Step 4: 添加约束**
```sql
-- 确保每个 Candidate 最多一个 pending Proposal
ALTER TABLE proposals
ADD CONSTRAINT uq_pending_proposal_per_candidate
UNIQUE (workspace_id, candidate_id)
WHERE status = 'pending';
```

### 7.3 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 迁移失败导致数据丢失 | 低 | 备份 + 事务回滚 |
| 匹配不准确 | 中 | 人工审核未匹配项 |
| 性能影响 | 低 | 分批迁移 |

---

## 8. 92 个 Pending Proposals 处理策略

### 8.1 问题分析

**现状**：
- 92 个 pending proposals
- 部分 evidence_chain 断裂（引用不存在的 evidence）
- 无法追溯原始 Candidate

### 8.2 选项分析

**Option A: 全部删除后重新 Evolution**
- 优点：干净重启
- 缺点：丢失人类审查历史
- 风险：可能再次生成重复 Proposal

**Option B: 保留并迁移 Candidate 关联**
- 优点：保留历史
- 缺点：需要复杂匹配逻辑
- 风险：匹配可能不准确

**Option C: 去重后保留一个**
- 优点：减少噪音
- 缺点：需要定义去重规则
- 风险：可能误删有效 Proposal

**Option D: 分类处理**
- 有效证据：保留，迁移关联
- 断裂证据：标记为 deprecated，等待人工审核
- 重复 Proposal：保留最新的，标记旧的为 superseded

### 8.3 推荐方案

**分类处理（Option D 增强）**：

```sql
-- 1. 识别有效 Proposal（证据链完整）
SELECT p.* FROM proposals p
WHERE p.status = 'pending'
AND EXISTS (
    SELECT 1 FROM evidences e 
    WHERE e.id = ANY(p.evidence_chain::jsonb)
);

-- 2. 识别断裂 Proposal（证据链无效）
SELECT p.* FROM proposals p
WHERE p.status = 'pending'
AND NOT EXISTS (
    SELECT 1 FROM evidences e 
    WHERE e.id = ANY(p.evidence_chain::jsonb)
);
```

**处理策略**：
- 有效 Proposal：迁移 candidate_id，保留等待审批
- 断裂 Proposal：标记为 `deprecated`，不删除，等待人工审核

---

## 9. Design Gap 标识

### 9.1 已确认的设计缺口

| Gap ID | 描述 | 严重程度 | 影响 |
|--------|------|----------|------|
| **DG-001** | 无 Proposal-Candidate 关联 | P0 | 无法去重 |
| **DG-002** | 无 State Transition 代码 | P0 | 状态永远不更新 |
| **DG-003** | Scope 查询无去重逻辑 | P0 | 重复 Evolution |
| **DG-004** | 设计文档未定义排除规则 | P1 | 规范缺失 |
| **DG-005** | Legacy Evidence 污染数据 | P1 | 证据链断裂 |

### 9.2 需要补充的设计

1. **Proposal-Candidate 关联规范**
   - 外键定义
   - 唯一约束
   - 级联规则

2. **状态转换规范**
   - 触发条件
   - 执行层
   - 事务边界

3. **Scope 排除规则**
   - 查询条件
   - 性能要求
   - 边界情况

---

## 10. Decisions Required From User — 需要用户决定的事项

### 决策 1: Schema 变更方案

| 项目 | Option A | Option B | 推荐 |
|------|----------|----------|------|
| candidate_id 字段 | 不添加 | 添加 FK | **B** |
| 唯一约束 | 无 | pending 唯一 | **B** |
| 索引 | 无 | 标准索引 | **B** |

**Decision**: 是否同意添加 `proposals.candidate_id` 外键？
- **推荐**: ✅ 同意（Option B）
- **理由**: 符合关系型设计，支持可靠去重
- **影响**: 需要迁移现有 92 个 pending proposals

---

### 决策 2: Candidate 状态转换时机

| 项目 | Option A | Option B | 推荐 |
|------|----------|----------|------|
| approved 时机 | 审批时立即 confirmed | MemoryNode 创建后 confirmed | **B** |
| rejected 时机 | 拒绝时立即 orphaned | 拒绝时立即 orphaned | A/B 一致 |

**Decision**: Proposal approved 后，Candidate 何时变 confirmed？
- **推荐**: ✅ Option B（MemoryNode 创建成功后）
- **理由**: 事务一致性，避免中间状态
- **影响**: 短暂的状态窗口期

---

### 决策 3: 92 个 Pending Proposals 处理

| 项目 | Option A | Option B | Option C | 推荐 |
|------|----------|----------|----------|------|
| 有效 Proposal | 删除 | 保留迁移 | 去重保留 | **C** |
| 断裂 Proposal | 删除 | 保留 | 标记 deprecated | **C** |

**Decision**: 如何处理现有的 92 个 pending proposals？
- **推荐**: ✅ Option C（分类处理）
- **理由**: 保留历史，清理无效数据
- **影响**: 需要人工审核断裂 Proposal

---

### 决策 4: Legacy Evidence 处理

| 项目 | Option A | Option B | 推荐 |
|------|----------|----------|------|
| 有 Legacy UUID 的 Candidate | 删除 | 标记 orphaned | **B** |

**Decision**: 8,829 个引用 Legacy Evidence 的 Candidates 如何处理？
- **推荐**: ✅ Option B（标记 orphaned）
- **理由**: 保留数据，标记问题
- **影响**: 这些 Candidates 不再进入 Evolution

---

### 决策 5: Scope 查询性能要求

| 项目 | 当前 | 目标 |
|------|------|------|
| 查询耗时 | < 100ms | < 50ms |
| 并发支持 | 单实例 | 多实例安全 |

**Decision**: 是否需要进一步优化 Scope 查询？
- **推荐**: 当前设计已满足需求，暂不需额外优化
- **理由**: 索引已足够，后续可扩展

---

## 11. Implementation Roadmap — 实施路线图（设计阶段）

### Phase 1: Schema 变更（预计 1 天）
1. 添加 `proposals.candidate_id` 字段
2. 添加索引和唯一约束
3. 数据迁移脚本

### Phase 2: 代码修复（预计 2 天）
1. 修复 `_acquire_scope()` 查询
2. 修复 Proposal 创建逻辑
3. 添加状态转换代码
4. 修复 Evidence API

### Phase 3: 数据清理（预计 1 天）
1. 清理 92 个 pending proposals
2. 标记 Legacy Evidence Candidates
3. 验证数据一致性

### Phase 4: 测试验证（预计 2 天）
1. 单元测试
2. 集成测试
3. 性能测试
4. 回归测试

---

## 12. 约束检查清单

### 已遵守的约束
- ✅ 未引入 `processed` 状态
- ✅ 未修改现有四状态定义
- ✅ 未改变既有生命周期语义
- ✅ 未执行任何数据库修改
- ✅ 未修改代码
- ✅ 未运行 Evolution

### 待用户确认的事项
- ⏳ 决策 1: Schema 变更方案
- ⏳ 决策 2: 状态转换时机
- ⏳ 决策 3: Pending Proposals 处理
- ⏳ 决策 4: Legacy Evidence 处理
- ⏳ 决策 5: Scope 查询性能

---

**设计状态**: 完成，等待用户确认
**下一步**: 收到确认后进入 Implementation
