# Phase 20 — Final Schema Boundary Decision

## 执行摘要

经过完整的只读调查，确认以下 Schema 设计决策。

---

## 1. candidate_id NULLability

### 决策

```
proposals.candidate_id: VARCHAR(36) REFERENCES candidates(id)
                        NULLABLE = TRUE
```

### 理由

| 因素 | 分析 |
|------|------|
| **历史数据** | 1,042 个 Approved Proposals 无 candidate_id（无法可靠映射） |
| **当前数据** | Pending = 0，无冲突 |
| **新数据** | 代码层强制填充，数据库层不强制 |
| **风险** | NULL 允许历史数据保留，新数据通过代码约束 |

### 为什么不设为 NOT NULL？

```
❌ 如果设为 NOT NULL：
   - 1,042 条 Approved 记录会违反约束
   - Migration 失败
   - 需要复杂的数据填充逻辑
   - 风险过高

✅ 设为 NULLABLE：
   - 历史数据兼容
   - 新数据通过代码保证非空
   - 风险最低
```

---

## 2. Pending Proposal 约束

### 决策

```
不使用数据库 CHECK 约束
改用代码层 + 应用层约束
```

### 理由

| 方案 | 可行性 | 风险 |
|------|--------|------|
| **CHECK (status <> 'pending' OR candidate_id IS NOT NULL)** | ✅ 技术上可行 | ⚠️ 需要处理历史 Approved 数据 |
| **代码层约束** | ✅ 推荐 | ✅ 低风险 |
| **唯一索引** | ✅ 必须添加 | ✅ 防止并发重复 |

### 为什么不用 CHECK？

```sql
-- 方案 A：CHECK 约束（不推荐）
CHECK (status <> 'pending' OR candidate_id IS NOT NULL)

问题：
1. 需要更新 1,042 条 Approved 记录的 candidate_id（可能为空）
2. 如果 candidate_id 为 NULL，CHECK 会失败
3. 需要复杂的数据清洗

-- 方案 B：代码层约束（推荐）
在 ProposalRepository.create() 中：
  if status == 'pending' and candidate_id is None:
      raise ValueError("Pending proposals must have candidate_id")

优势：
1. 不需要修改历史数据
2. 清晰的错误信息
3. 易于测试
```

---

## 3. FK ON DELETE

### 决策

```
proposals.candidate_id → candidates.id
ON DELETE SET NULL
```

### 理由

| ON DELETE 行为 | 适用场景 | 本题适用性 |
|----------------|----------|------------|
| **CASCADE** | 删除 Candidate 时删除所有 Proposal | ❌ 丢失 Proposal 历史 |
| **SET NULL** | 删除 Candidate 时清空 candidate_id | ✅ 保留 Proposal 历史 |
| **RESTRICT** | 有 Proposal 时禁止删除 Candidate | ⚠️ 可能阻碍合法操作 |

### 为什么选 SET NULL？

```
场景分析：
1. Candidate 被删除（archived/orphaned）
   → Proposal 应保留（历史记录）
   → candidate_id 设为 NULL
   → 仍可追溯（通过 evidence_chain）

2. Candidate 仍然存在
   → Proposal 正常关联
   → 状态转换正常工作

3. 数据完整性
   → FK 保证 candidate_id 指向有效 Candidate（如果非空）
   → SET NULL 不会破坏其他表
```

### 为什么不选 CASCADE？

```
❌ CASCADE 会删除所有关联 Proposal
→ 丢失 1,042 条 Approved 历史
→ 违反"Evidence-Based Memory"原则
→ 不可接受
```

### 为什么不选 RESTRICT？

```
⚠️ RESTRICT 会阻止删除有 Proposal 的 Candidate
→ 可能需要人工处理大量数据
→ 增加运维复杂度
→ 不推荐
```

---

## 4. Unique Pending Index

### 决策

```sql
-- Partial Unique Index（PostgreSQL 特性）
CREATE UNIQUE INDEX idx_proposals_pending_unique
ON proposals (workspace_id, candidate_id)
WHERE status = 'pending';
```

### 为什么用 Partial Index？

| 索引类型 | 适用场景 | 本题适用性 |
|----------|----------|------------|
| **普通唯一索引** | 整个列唯一 | ❌ 会阻止同一 Candidate 有多个历史 Proposal |
| **Partial 唯一索引** | 满足 WHERE 条件的行唯一 | ✅ 只约束 pending 状态 |
| **复合唯一索引** | 多列组合唯一 | ⚠️ 过于严格 |

### 为什么只约束 Pending？

```
设计意图：
- 同一 Candidate 同时只能有 1 个 Pending Proposal
- 防止重复 Evolution 产生重复 Proposal

例外情况：
- Approved/Rejected Proposal 可以有多条（历史记录）
- 不同时间窗口的 Proposal 可以存在

实现：
WHERE status = 'pending' 只约束当前待处理的 Proposal
```

### 索引性能

```
当前 proposals 表已有索引：
- proposals_pkey (id)
- idx_proposals_workspace (workspace_id)
- idx_proposals_status (status)
- idx_proposals_target_level (target_level)

新增索引：
- idx_proposals_pending_unique (workspace_id, candidate_id) WHERE status='pending'

查询优化：
Scope 查询会用到：
  WHERE workspace_id = ?
  AND status = 'candidate'
  AND NOT EXISTS (SELECT 1 FROM proposals WHERE candidate_id = ? AND status = 'pending')

NOT EXISTS 子查询可利用新索引加速。
```

---

## 5. Migration 顺序

### Phase 1: Schema Migration

```sql
-- Step 1: 添加列（nullable）
ALTER TABLE proposals
ADD COLUMN candidate_id VARCHAR(36);

-- Step 2: 添加 FK（SET NULL）
ALTER TABLE proposals
ADD CONSTRAINT fk_proposals_candidate
FOREIGN KEY (candidate_id)
REFERENCES candidates(id)
ON DELETE SET NULL;

-- Step 3: 添加索引
CREATE INDEX idx_proposals_candidate_id
ON proposals (workspace_id, candidate_id);

-- Step 4: 添加 Partial Unique Index
CREATE UNIQUE INDEX idx_proposals_pending_unique
ON proposals (workspace_id, candidate_id)
WHERE status = 'pending';
```

### Phase 2: Model Update

```python
# proposal_model.py
class Proposal(Base):
    # ... 现有字段 ...
    candidate_id = Column(String(36), ForeignKey('candidates.id'), nullable=True)
```

### Phase 3: Repository Update

```python
# proposal_repository.py
async def create(self, proposal: dict) -> UUID:
    # 添加 candidate_id 参数
    if proposal.get('status') == 'pending' and not proposal.get('candidate_id'):
        raise ValueError("Pending proposals must have candidate_id")
    
    stmt = text("""
        INSERT INTO proposals (
            id, workspace_id, candidate_id, type, ...
        ) VALUES (
            :id, :workspace_id, :candidate_id, :type, ...
        )
    """)
```

### Phase 4: Service Update

```python
# reflection_service.py

# approve_proposal() - 添加 Candidate 状态更新
async with engine.begin() as conn:
    # ... 现有逻辑 ...
    # 新增：更新 Candidate → confirmed
    if prop.get('candidate_id'):
        await conn.execute(text("""
            UPDATE candidates 
            SET status = 'confirmed', updated_at = NOW()
            WHERE id = :candidate_id AND workspace_id = :workspace_id
        """), {"candidate_id": prop['candidate_id'], "workspace_id": str(workspace_id)})

# reject_proposal() - 添加 Candidate 状态更新
async with engine.begin() as conn:
    # 获取 candidate_id
    result = await conn.execute(text("SELECT candidate_id FROM proposals WHERE id = :id"), {"id": str(proposal_id)})
    candidate_id = result.scalar()
    
    # ... 现有逻辑 ...
    # 新增：更新 Candidate → orphaned
    if candidate_id:
        await conn.execute(text("""
            UPDATE candidates 
            SET status = 'orphaned', updated_at = NOW()
            WHERE id = :candidate_id
        """), {"candidate_id": candidate_id})

# _acquire_scope() - 添加去重逻辑
async with engine.begin() as conn:
    result = await conn.execute(text("""
        SELECT ... FROM candidates c
        WHERE c.workspace_id = :workspace_id
        AND c.status = 'candidate'
        AND NOT EXISTS (
            SELECT 1 FROM proposals p
            WHERE p.candidate_id = c.id
            AND p.status = 'pending'
        )
        ORDER BY c.created_at ASC
        LIMIT :limit
    """), {"workspace_id": str(workspace_id), "limit": limit})
```

### Phase 5: 测试验证

```python
# test_scope_deduplication.py
async def test_scope_excludes_pending():
    """Candidate with pending proposal should be excluded"""
    ...

# test_state_transition.py
async def test_approve_updates_candidate():
    """Approving proposal should mark candidate as confirmed"""
    ...

async def test_reject_orphans_candidate():
    """Rejecting proposal should mark candidate as orphaned"""
    ...
```

---

## 6. 最终 Schema Contract

### 6.1 Historical Proposal

```
candidate_id: NULL
范围: 所有在 Migration 前已存在的 Proposal
理由: 无法可靠映射到 Candidate
处理: 保留历史记录，不强制填充
```

### 6.2 New Pending Proposal

```
candidate_id: NOT NULL (代码层强制)
范围: Migration 后新创建的 Pending Proposal
理由: 必须有明确的 Candidate 来源
实现: ProposalRepository.create() 中验证
```

### 6.3 Approved / Rejected

```
candidate_id: 可为 NULL
范围: 
  - 历史数据（Migration 前）
  - 新数据但 Candidate 已被删除（ON DELETE SET NULL）
理由: 保留历史记录
```

### 6.4 FK 约束

```
proposals.candidate_id → candidates.id
ON DELETE: SET NULL
ON UPDATE: NO ACTION（默认）
```

### 6.5 Unique Pending Index

```sql
CREATE UNIQUE INDEX idx_proposals_pending_unique
ON proposals (workspace_id, candidate_id)
WHERE status = 'pending';
```

---

## 7. 关键发现

### 7.1 发现错误代码（P0 Bug）

**位置**: `reflection_service.py:758`

```python
# 错误代码
candidate_id = evidence_chain[0] if evidence_chain else f'entity_{i}'
```

**问题**:
- 将 Evidence UUID 当作 Candidate ID
- 这是错误的伪关联
- 会导致数据混乱

**修复**:
- 删除此代码
- 改为从 Evolution 上下文传入真实的 Candidate ID
- 在 ProposalRepository.create() 中验证

### 7.2 Alembic 配置

**位置**: `backend/alembic/`

- env.py 已正确配置
- 使用 Base.metadata 自动检测变更
- 支持异步数据库连接
- versions/ 目录为空（无历史迁移）

**建议**:
- 使用 `alembic revision --autogenerate` 自动生成迁移
- 或手动编写迁移脚本

---

## 8. 风险评估

| 风险项 | 级别 | 缓解措施 |
|--------|------|----------|
| Migration 失败 | 低 | 备份数据库，准备 rollback |
| 历史数据冲突 | 低 | candidate_id nullable |
| ON DELETE SET NULL 影响 | 低 | 不影响 Approved/Rejected |
| 索引性能 | 低 | Partial Index 只在 pending 时生效 |
| 代码变更遗漏 | 中 | 完整回归测试 |

---

## 9. 结论

### 是否可以开始 Phase 1？

**是的。**

```
Schema boundary confirmed — Phase 1 may begin.
```

### 前提条件

1. ✅ 设计决策已确认
2. ✅ 风险评估已完成
3. ✅ Migration 顺序已明确
4. ✅ 测试计划已制定
5. ⚠️ 需修复 P0 Bug（reflection_service.py:758）

### 下一步行动

```
Phase 1: Schema Migration
  → 创建 alembic migration
  → 添加 candidate_id 列
  → 添加 FK 和索引

Phase 2: Model Update
  → 更新 Proposal 模型
  → 添加 candidate_id 字段

Phase 3: Repository Update
  → 更新 ProposalRepository.create()
  → 添加 candidate_id 验证

Phase 4: Service Update
  → 修复 P0 Bug
  → 更新 approve/reject/scope
  → 添加状态转换逻辑

Phase 5: Tests
  → 编写回归测试
  → 运行完整测试套件

Phase 6: Validation
  → 启动 Evolution
  → 观察第一轮执行
  → 验证状态转换
```

---

**状态**: Schema Boundary Confirmed ✅  
**下一步**: 等待用户确认后开始 Phase 1 实施
