# Phase 20 — Implementation Plan

## 一、Current Code Baseline

### 1.1 Schema / Model

| 实体 | 文件 | 行号 | 当前字段 | 缺失字段 |
|------|------|------|----------|----------|
| **Proposal** | `proposal_model.py` | 14-31 | id, workspace_id, type, source_level, target_level, entity, evidence_chain, confidence, summary, content, status, created_at, updated_at | **candidate_id** ❌ |
| **Candidate** | `memory_models.py` | 697-794 | id, workspace_id, entity_id, content, candidate_type, evidence_source, evidence_id, evidence_chain, evidence_count, evidence_strength, status, created_at, updated_at | - |

### 1.2 Repository

| 类 | 文件 | 关键方法 | 当前行为 |
|------|------|----------|----------|
| ProposalRepository | `proposal_repository.py:19` | create() | 创建Proposal，无candidate_id参数 |
| CandidateRepository | `candidate_repository.py:58` | find_by_workspace() | 查询Candidates，支持status过滤 |

### 1.3 Service

| 方法 | 文件 | 行号 | 当前行为 | 问题 |
|------|------|------|----------|------|
| approve_proposal() | `reflection_service.py:208` | 220-268 | 更新Proposal状态 + 创建MemoryNode | ❌ 未更新Candidate → confirmed |
| reject_proposal() | `reflection_service.py:446` | 459-467 | 更新Proposal状态 | ❌ 未更新Candidate → orphaned |
| _acquire_scope() | `reflection_service.py:1054` | 1080-1090 | WHERE status IN ('candidate', 'pending') | ❌ 无去重检查 |

### 1.4 测试

| 文件 | 内容 | 覆盖 |
|------|------|------|
| test_reflection_engine.py | Reflection引擎测试 | 基本功能 |
| test_service_layer.py | 服务层测试 | approve/reject基本流程 |
| **缺失** | Scope去重测试 | ❌ |
| **缺失** | 状态转换测试 | ❌ |
| **缺失** | 事务一致性测试 | ❌ |

---

## 二、Confirmed Design Decisions

### 2.1 Candidate 状态

```python
VALID_STATUSES = ('candidate', 'confirmed', 'archived', 'orphaned')
```

### 2.2 Proposal 状态

```python
VALID_STATUSES = ('pending', 'approved', 'rejected')
```

### 2.3 Candidate → Proposal 关系

```
Candidate 1 ─── N Proposal
proposals.candidate_id FK → candidates.id
```

### 2.4 Pending Proposal 唯一性

```sql
CREATE UNIQUE INDEX idx_proposals_candidate_pending
ON proposals (workspace_id, candidate_id)
WHERE status = 'pending';
```

### 2.5 Evolution Scope

```sql
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

### 2.6 State Transition

```
Candidate → Proposal pending → Candidate 保持 candidate
Proposal approved + MemoryNode created → Candidate confirmed
Proposal rejected → Candidate orphaned
```

### 2.7 Transaction Boundary

```
Approve:
BEGIN
  UPDATE proposals SET status='approved'
  INSERT INTO memory_nodes
  UPDATE candidates SET status='confirmed'  ← 新增
COMMIT

Reject:
BEGIN
  UPDATE proposals SET status='rejected'
  UPDATE candidates SET status='orphaned'   ← 新增
COMMIT
```

---

## 三、Required Changes

### 3.1 Schema Migration

| 步骤 | 操作 | 文件 | 风险 |
|------|------|------|------|
| 1 | 添加 candidate_id 列 | Migration script | 低（Pending=0） |
| 2 | 添加 FK 约束 | Migration script | 中（需处理1005 Approved） |
| 3 | 添加索引 | Migration script | 低 |
| 4 | 添加 Unique Index | Migration script | 中（可能冲突） |

**关键问题**：
- Pending Proposals = 0 → 可以添加 NOT NULL
- Approved Proposals = 1005 → 需要决定 candidate_id 是否为 NULL

**推荐方案**：
```
Option A: candidate_id nullable，逐步填充
Option B: candidate_id NOT NULL，1005条设为空值后报错（不推荐）
```

### 3.2 Model Update

**File**: `backend/src/backend/shared/domain/proposal_model.py`

```python
# 当前（第19-31行）
class Proposal(Base):
    __tablename__ = "proposals"
    id = Column(String, primary_key=True)
    workspace_id = Column(String, nullable=False)
    # ... 其他字段
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 修改为
class Proposal(Base):
    __tablename__ = "proposals"
    id = Column(String, primary_key=True)
    workspace_id = Column(String, nullable=False)
    candidate_id = Column(String, ForeignKey('candidates.id'), nullable=True)  # 新增
    # ... 其他字段
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 3.3 Repository Update

**File**: `backend/src/backend/repository/proposal_repository.py`

```python
# 当前 create() 方法（第29-58行）
async def create(self, proposal: dict[str, Any]) -> UUID:
    # ... INSERT 语句不含 candidate_id

# 修改为
async def create(self, proposal: dict[str, Any]) -> UUID:
    # 添加 candidate_id 参数
    stmt = text("""
        INSERT INTO proposals (
            id, workspace_id, candidate_id, type, ...
        ) VALUES (
            :id, :workspace_id, :candidate_id, :type, ...
        )
    """)
```

### 3.4 Service Update - approve_proposal()

**File**: `backend/src/backend/service/reflection_service.py`

```python
# 当前（第220-268行）
async with engine.begin() as conn:
    # 1. Get proposal
    # 2. Update proposal status
    await conn.execute(text("UPDATE proposals SET status = 'approved'..."))
    # 3. Create MemoryNode
    # ... 无 Candidate 更新

# 修改为
async with engine.begin() as conn:
    # 1. Get proposal
    # 2. Update proposal status
    await conn.execute(text("UPDATE proposals SET status = 'approved'..."))
    # 3. Create MemoryNode
    # 4. Update Candidate → confirmed（新增）
    if prop.get('candidate_id'):
        await conn.execute(text("""
            UPDATE candidates 
            SET status = 'confirmed', updated_at = NOW()
            WHERE id = :candidate_id AND workspace_id = :workspace_id
        """), {"candidate_id": prop['candidate_id'], "workspace_id": str(workspace_id)})
```

### 3.5 Service Update - reject_proposal()

**File**: `backend/src/backend/service/reflection_service.py`

```python
# 当前（第459-467行）
async with engine.begin() as conn:
    await conn.execute(text("UPDATE proposals SET status = 'rejected'..."))
    # 无 Candidate 更新

# 修改为
async with engine.begin() as conn:
    # 先获取 proposal 的 candidate_id
    result = await conn.execute(text("SELECT candidate_id FROM proposals WHERE id = :id"), {"id": str(proposal_id)})
    candidate_id = result.scalar()
    
    # Update proposal
    await conn.execute(text("UPDATE proposals SET status = 'rejected'..."))
    
    # Update Candidate → orphaned（新增）
    if candidate_id:
        await conn.execute(text("""
            UPDATE candidates 
            SET status = 'orphaned', updated_at = NOW()
            WHERE id = :candidate_id
        """), {"candidate_id": candidate_id})
```

### 3.6 Service Update - _acquire_scope()

**File**: `backend/src/backend/service/reflection_service.py`

```python
# 当前（第1080-1090行）
result = await conn.execute(text("""
    SELECT ... FROM candidates
    WHERE workspace_id = :workspace_id
    AND status IN ('candidate', 'pending')  ← 错误：pending 不是合法状态
    ORDER BY created_at ASC
    LIMIT :limit
"""), {...})

# 修改为
result = await conn.execute(text("""
    SELECT ... FROM candidates c
    WHERE c.workspace_id = :workspace_id
    AND c.status = 'candidate'  ← 修正
    AND NOT EXISTS (
        SELECT 1 FROM proposals p
        WHERE p.candidate_id = c.id
        AND p.status = 'pending'
    )  ← 新增去重
    ORDER BY c.created_at ASC
    LIMIT :limit
"""), {"workspace_id": str(workspace_id), "limit": limit})
```

### 3.7 Proposal Creation Update

**File**: `backend/src/backend/engine/evidence_evolution_engine.py`

需要确认 Proposal 创建时是否已传入 candidate_id：
- 检查 EvidenceEvolutionEngine.generate_proposal() 方法
- 确保从 Candidate 对象获取 ID 并传递给 Proposal

---

## 四、Migration Plan

### 4.1 Migration 文件位置

```
backend/src/backend/shared/infrastructure/database/migrations/
└── add_candidate_id_to_proposals.py  （新建）
```

### 4.2 Migration Steps

```python
"""
Migration: Add candidate_id to proposals
Date: 2026-08-12
Purpose: Link Proposals to Candidates for lifecycle management
"""

from sqlalchemy import text

def upgrade(engine):
    with engine.connect() as conn:
        # Step 1: Add column (nullable for existing data)
        conn.execute(text("""
            ALTER TABLE proposals 
            ADD COLUMN candidate_id VARCHAR REFERENCES candidates(id)
        """))
        
        # Step 2: Add index
        conn.execute(text("""
            CREATE INDEX idx_proposals_candidate_id 
            ON proposals (workspace_id, candidate_id)
        """))
        
        # Step 3: Add partial unique index for pending
        conn.execute(text("""
            CREATE UNIQUE INDEX idx_proposals_pending_unique
            ON proposals (workspace_id, candidate_id)
            WHERE status = 'pending'
        """))
        
        conn.commit()

def downgrade(engine):
    with engine.connect() as conn:
        conn.execute(text("DROP INDEX IF EXISTS idx_proposals_pending_unique"))
        conn.execute(text("DROP INDEX IF EXISTS idx_proposals_candidate_id"))
        conn.execute(text("ALTER TABLE proposals DROP COLUMN candidate_id"))
        conn.commit()
```

### 4.3 1005 Approved Proposals 处理

**问题**：
- 无法可靠映射到 Candidate（无 candidate_id FK 历史）
- Legacy Evidence UUID 可能无效

**方案**：
```
Option A: candidate_id = NULL（推荐）
  - 保留历史数据
  - 新数据必须填充
  - 风险最低

Option B: 尝试映射（高风险）
  - 可能产生错误关联
  - 需要复杂逻辑
  - 不推荐
```

---

## 五、Regression Test Plan

### 5.1 Scope Tests

```python
async def test_scope_excludes_pending():
    """Candidate with pending proposal should be excluded from scope"""
    candidate = await create_candidate()
    proposal = await create_proposal(candidate_id=candidate.id, status='pending')
    
    scope = await acquire_scope(workspace_id, limit=100)
    
    assert candidate.id not in [c['id'] for c in scope]

async def test_scope_includes_idle_candidate():
    """Candidate without pending proposal should be included"""
    candidate = await create_candidate()
    
    scope = await acquire_scope(workspace_id, limit=100)
    
    assert any(c['id'] == candidate.id for c in scope)

async def test_scope_excludes_confirmed():
    """Confirmed candidate should not be in scope"""
    candidate = await create_candidate()
    await update_candidate_status(candidate.id, 'confirmed')
    
    scope = await acquire_scope(workspace_id, limit=100)
    
    assert not any(c['id'] == candidate.id for c in scope)
```

### 5.2 Approve Tests

```python
async def test_approve_updates_candidate():
    """Approving proposal should mark candidate as confirmed"""
    candidate = await create_candidate()
    proposal = await create_proposal(candidate_id=candidate.id)
    
    await approve_proposal(proposal.id)
    
    updated = await get_candidate(candidate.id)
    assert updated.status == 'confirmed'

async def test_approve_rollback_on_memorynode_failure():
    """If MemoryNode creation fails, candidate should not be updated"""
    candidate = await create_candidate()
    proposal = await create_proposal(candidate_id=candidate.id)
    
    # Mock memory_node creation to fail
    with patch('memory_node_repo.create', side_effect=Exception()):
        with pytest.raises(Exception):
            await approve_proposal(proposal.id)
    
    updated = await get_candidate(candidate.id)
    assert updated.status == 'candidate'  # Should remain unchanged
```

### 5.3 Reject Tests

```python
async def test_reject_orphans_candidate():
    """Rejecting proposal should mark candidate as orphaned"""
    candidate = await create_candidate()
    proposal = await create_proposal(candidate_id=candidate.id)
    
    await reject_proposal(proposal.id)
    
    updated = await get_candidate(candidate.id)
    assert updated.status == 'orphaned'
```

### 5.4 Uniqueness Tests

```python
async def test_duplicate_pending_blocked():
    """Should not allow two pending proposals for same candidate"""
    candidate = await create_candidate()
    await create_proposal(candidate_id=candidate.id, status='pending')
    
    with pytest.raises(IntegrityError):
        await create_proposal(candidate_id=candidate.id, status='pending')
```

---

## 六、Rollback Plan

### 6.1 Migration Rollback

```python
def rollback_migration():
    """Reverse the candidate_id migration"""
    # 1. Drop indexes
    DROP INDEX idx_proposals_pending_unique;
    DROP INDEX idx_proposals_candidate_id;
    
    # 2. Drop column
    ALTER TABLE proposals DROP COLUMN candidate_id;
    
    # 3. Revert code changes
    # 4. Restart application
```

### 6.2 Data Recovery

```sql
-- 如果需要恢复被删除的 Pending Proposals
INSERT INTO proposals SELECT * FROM proposals_backup_20260812;
```

---

## 七、Out of Scope（明确排除）

以下问题**不在 Phase 20 实施范围**内：

1. **800 个无 Evidence 的 MemoryNodes**
   - 原因：需要单独的数据治理项目
   - 行动：标记 orphaned，等待人工审核

2. **Evidence API Bug**
   - 原因：独立问题，已有专项修复计划
   - 行动：Phase 21 处理

3. **Legacy Evidence 数据治理**
   - 原因：需要用户决策
   - 行动：等待设计确认

4. **Scheduler Startup Compensation**
   - 原因：已修复（Phase 15-17）
   - 行动：无需处理

5. **Cooldown 机制**
   - 原因：非 P0 问题
   - 行动：后续优化

---

## 八、New Design Gaps

### 8.1 P0: Approved Proposals 无法映射

**问题**：
- 1005 个 Approved Proposals 没有 candidate_id
- 无法可靠回溯到原始 Candidate
- 如果 candidate_id 设为 NOT NULL，迁移会失败

**影响**：
- 无法建立完整的 Candidate-Proposal 关系链
- 无法追溯 Approved Proposal 的来源

**候选方案**：
```
方案 A: candidate_id nullable（推荐）
  - 允许历史数据为空
  - 新数据必须填充
  - 风险最低

方案 B: 标记为 unknown
  - 添加特殊值如 'unknown'
  - 违反 FK 约束
  - 不推荐
```

**建议**：采用方案 A

---

### 8.2 P1: Proposal Content 重复检测

**问题**：
- 当前无内容重复检测
- 同一 Candidate 可能生成多个相似 Proposal
- 导致资源浪费

**建议**：
- Phase 21 添加内容指纹检测
- 使用 MD5/SHA 对 content 去重

---

## 九、Implementation Phases

### Phase 1: Schema（预计 2h）

- [ ] 编写 Migration 脚本
- [ ] 添加 candidate_id 列（nullable）
- [ ] 添加索引
- [ ] 运行测试

### Phase 2: Model（预计 1h）

- [ ] 更新 Proposal 模型
- [ ] 添加 candidate_id 字段
- [ ] 运行单元测试

### Phase 3: Repository（预计 2h）

- [ ] 更新 ProposalRepository.create()
- [ ] 更新 CandidateRepository 添加 find_in_scope()
- [ ] 运行集成测试

### Phase 4: Service（预计 4h）

- [ ] 更新 approve_proposal() 添加状态转换
- [ ] 更新 reject_proposal() 添加状态转换
- [ ] 更新 _acquire_scope() 添加去重逻辑
- [ ] 更新 Proposal 创建逻辑
- [ ] 运行回归测试

### Phase 5: Tests（预计 3h）

- [ ] 编写 Scope 去重测试
- [ ] 编写状态转换测试
- [ ] 编写事务一致性测试
- [ ] 运行完整测试套件

### Phase 6: 验证（预计 1h）

- [ ] 启动 Evolution
- [ ] 观察第一轮执行
- [ ] 验证 Candidate 状态更新
- [ ] 验证去重效果

**总计：约 13 小时**

---

## 十、Risk Assessment

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| Migration 失败 | 中 | 备份数据库，准备 rollback |
| 1005 Approved 映射失败 | 低 | candidate_id nullable |
| 测试覆盖不足 | 中 | 分阶段测试，逐步验证 |
| 性能下降 | 低 | 添加索引，监控查询 |
| 事务失败 | 中 | 完善的 rollback 逻辑 |

---

**状态**: 等待用户确认
**下一步**: 用户确认后开始 Phase 1 实施
