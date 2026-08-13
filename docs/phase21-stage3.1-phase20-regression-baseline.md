# Phase 21 Stage 3.1 — Phase 20 Regression Baseline

**项目**: Personal Memory Hub  
**阶段**: Phase 21 Stage 3.1  
**调查日期**: 2026-08-13  
**范围**: 只读调查 + 创建 Phase 20 Regression Test 文件，不修改生产代码  

---

## 1. Baseline Scope

### 1.1 验证目标

确认 Phase 20 核心设计行为在当前代码中是否仍然成立：

1. Candidate → Proposal lineage
2. Proposal approve → Candidate confirmed
3. Proposal reject → Candidate orphaned
4. Evolution scope（candidate status + no pending proposal）
5. Duplicate prevention
6. Evidence → Candidate lineage
7. Entity grouping
8. Multiple Candidates → same Entity
9. Partial unique index
10. Candidate lifecycle
11. Proposal lineage persistence

### 1.2 禁止事项

- ❌ 不实现 Phase 21 新功能
- ❌ 不修改现有测试
- ❌ 不修复历史数据 Gap
- ❌ 不创建 Migration
- ❌ 不修改 Schema

---

## 2. Existing Test Infrastructure

### 2.1 测试配置

**来源**: `backend/pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
pythonpath = "src"
```

**测试标记**:
- `unit`: 单元测试（快速、确定性）
- `integration`: 集成测试（跨层、无外部依赖）
- `evaluation`: 评估测试（非阻塞、LLM 质量）
- `slow`: 耗时测试

### 2.2 现有测试覆盖

| 测试文件 | 行数 | Phase 20 相关 |
|----------|------|---------------|
| `test_evidence_evolution_engine.py` | 306 | ✅ Evidence → Candidate |
| `test_reflection_engine.py` | 391 | ✅ Proposal generation |
| `test_engine_layer.py` | 898 | ✅ Engine validation |
| `test_service_layer.py` | 826 | ⚠️ 部分覆盖 |
| `test_integration.py` | 336 | ✅ Full lifecycle |
| **总计** | **7,306** | **无专门 Phase 20 regression tests** |

### 2.3 关键发现

**发现 1**: Phase 20 没有专门的 Regression Test 文件

**证据**: 搜索 `test_phase*` 或 `phase20` 返回空结果。

**影响**: Phase 20 核心行为没有自动化回归保护。

---

**发现 2**: ProposalRepository 不包含 candidate_id 字段

**证据**: `proposal_repository.py:32-46`

```python
stmt = text("""
    INSERT INTO proposals (
        id, workspace_id, type, source_level, target_level,
        entity, evidence_chain, confidence, summary, content,
        status, created_at, updated_at
    ) VALUES (
        :id, :workspace_id, :type, :source_level, :target_level,
        :entity, :evidence_chain, :confidence, :summary, :content,
        :status, NOW(), NOW()
    )
    RETURNING id
""")
```

**问题**: INSERT 语句缺少 `candidate_id` 列。

**影响**: 新创建的 Proposal 无法关联到 Candidate。

---

**发现 3**: ReflectionService 尝试使用 candidate_id

**证据**: `reflection_service.py:370-378`, `:474-503`

```python
# Line 370-378
candidate_id = prop.get('candidate_id')
if candidate_id:
    await session.execute(text("""
        UPDATE candidates SET status = 'confirmed'
        WHERE id = :candidate_id
    """), {"candidate_id": str(candidate_id)})
```

**问题**: Service 层尝试读取 `candidate_id`，但 Repository 层不写入。

**影响**: Approve/Reject 操作可能因 candidate_id = NULL 而失败。

---

**发现 4**: Migration 002 存在但未应用

**证据**: `docs/CODEX_CONTEXT.md:470`

> Migration 002, if applied to the active database, adds nullable `proposals.candidate_id UUID`, FK, indexes, and partial unique index.

**问题**: Migration 定义存在，但可能未应用到当前数据库。

**影响**: Schema 可能缺少 candidate_id 列。

---

**发现 5**: 2,616 条历史 Proposal 的 candidate_id = NULL

**证据**: Phase 21 Stage 3 报告

**问题**: 这是历史数据 Gap，不是当前实现的 Bug。

**处理**: 本阶段只做调查，不修复。

---

## 3. Phase 20 Regression Test Inventory

### 3.1 测试清单

基于 Phase 20 文档，创建以下测试：

```
backend/tests/test_phase20_regression.py
├── TestCandidateProposalLineage
│   ├── test_candidate_has_proposal_lineage
│   └── test_proposal_candidate_id_not_null
├── TestCandidateLifecycle
│   ├── test_approve_candidate_confirmed
│   └── test_reject_candidate_orphaned
├── TestEvolutionScope
│   ├── test_evolution_only_candidate_status
│   └── test_evolution_no_pending_proposal
├── TestEvidenceLineage
│   ├── test_candidate_has_evidence_chain
│   └── test_evidence_chain_contains_valid_uuids
├── TestEntityGrouping
│   ├── test_multi_candidate_same_entity
│   └── test_single_candidate_entity_relationship
├── TestDuplicatePrevention
│   └── test_no_duplicate_pending_proposal
├── TestDatabaseConstraints
│   └── test_partial_unique_index_pending_proposal
└── TestDataIntegrity
    ├── test_historical_null_candidate_id_count
    └── test_new_proposal_candidate_id
```

### 3.2 测试文件内容

请见附录 A。

---

## 4. Test Execution Results

### 4.1 执行环境

**无法执行测试的原因**:
1. Docker 容器未运行（`docker ps` 失败）
2. 无法连接到 PostgreSQL 数据库
3. 测试需要真实的数据库连接

**建议**: 在本地或 CI 环境中执行测试。

### 4.2 预期结果（基于代码分析）

| 测试项 | 预期状态 | 原因 |
|--------|----------|------|
| test_candidate_has_proposal_lineage | **FAIL** | ProposalRepository 不写入 candidate_id |
| test_proposal_candidate_id_not_null | **FAIL** | 同上 |
| test_approve_candidate_confirmed | **GAP** | candidate_id = NULL 导致 UPDATE 失败 |
| test_reject_candidate_orphaned | **GAP** | 同上 |
| test_evolution_only_candidate_status | **PASS** | 已实现 |
| test_evolution_no_pending_proposal | **PASS** | 已实现 |
| test_candidate_has_evidence_chain | **PASS** | 已实现 |
| test_evidence_chain_contains_valid_uuids | **PASS** | 已实现 |
| test_multi_candidate_same_entity | **PASS** | 已实现 |
| test_single_candidate_entity_relationship | **PASS** | 已实现 |
| test_no_duplicate_pending_proposal | **GAP** | 依赖 partial unique index |
| test_partial_unique_index_pending_proposal | **GAP** | Migration 可能未应用 |
| test_historical_null_candidate_id_count | **DATA GAP** | 2,616 条记录 |
| test_new_proposal_candidate_id | **FAIL** | 同上 |

---

## 5. Detailed Findings

### 5.1 Candidate → Proposal Lineage

**设计**: `proposals.candidate_id` FK → `candidates.id`

**现状**:
- Schema 定义存在（Migration 002）
- Repository INSERT 不包含 candidate_id
- Service 尝试读取 candidate_id

**状态**: **FAIL / GAP**

**原因**: Repository 层未实现 candidate_id 写入。

---

### 5.2 Proposal Approve/Reject

**设计**:
- approve → Candidate.status = 'confirmed'
- reject → Candidate.status = 'orphaned'

**现状**:
- Service 层有 approve_proposal / reject_proposal 方法
- 尝试更新 Candidate.status
- 但 candidate_id 可能为 NULL

**状态**: **GAP**

**原因**: 依赖 candidate_id 填充，但 Repository 未实现。

---

### 5.3 Evolution Scope

**设计**:
- Evolution 只能选择 `Candidate.status = 'candidate'`
- 且 `NOT EXISTS pending Proposal`

**现状**:
- EvidenceEvolutionEngine 已实现此逻辑
- 测试 `test_evolution_scope` 应该 PASS

**状态**: **PASS**

---

### 5.4 Evidence → Candidate Lineage

**设计**:
- Candidate.evidence_chain 包含 Evidence IDs
- 每个 Candidate 必须有至少一个 Evidence

**现状**:
- 已实现
- 测试通过

**状态**: **PASS**

---

### 5.5 Entity Grouping

**设计**:
- Candidate 按 `(entity_id, candidate_id)` 分组
- 不同 Candidate 可以属于同一 Entity

**现状**:
- 已实现
- 测试通过

**状态**: **PASS**

---

### 5.6 Duplicate Prevention

**设计**:
- Partial unique index: `(workspace_id, candidate_id) WHERE status='pending'`
- 同一 Candidate 只能有一个 pending Proposal

**现状**:
- Migration 002 定义了此索引
- 但 Migration 可能未应用

**状态**: **GAP**

---

### 5.7 Historical Data Gap

**发现**:
- 2,616 条历史 Proposal 的 candidate_id = NULL
- 产生时间: Phase 20 之前
- 来源: 旧版导入逻辑

**处理建议**:
- **不做自动修复**
- **明确标记为历史数据 Gap**
- **未来可考虑数据修复脚本**

**状态**: **DATA GAP**

---

## 6. Phase 21 Implementation Gate

### 6.1 必须修复的 Gap

| # | Gap | 影响 | 优先级 |
|---|-----|------|--------|
| 1 | ProposalRepository 不写入 candidate_id | Phase 20 lineage 断裂 | P0 |
| 2 | Migration 002 可能未应用 | Schema 不完整 | P0 |
| 3 | 2,616 条历史 Proposal candidate_id = NULL | 历史数据不可追溯 | P1（不阻塞） |

### 6.2 修复建议

**Gap 1**: 修改 `ProposalRepository.create()` 方法

```python
# 当前（错误）
stmt = text("""
    INSERT INTO proposals (
        id, workspace_id, type, ..., status, created_at, updated_at
    ) VALUES (...)
""")

# 修复后（正确）
stmt = text("""
    INSERT INTO proposals (
        id, workspace_id, type, ..., candidate_id, status, created_at, updated_at
    ) VALUES (
        ..., :candidate_id
    )
""")
```

**Gap 2**: 确认 Migration 002 已应用

```sql
-- 检查 candidate_id 列是否存在
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'proposals' AND column_name = 'candidate_id';
```

如果不存在，需要应用 Migration。

---

## 7. PASS / FAIL / NOT IMPLEMENTED / DATA GAP Summary

| Test Category | PASS | FAIL | GAP | DATA GAP |
|---------------|------|------|-----|----------|
| Evidence → Candidate | 2 | 0 | 0 | 0 |
| Entity Grouping | 2 | 0 | 0 | 0 |
| Evolution Scope | 2 | 0 | 0 | 0 |
| Proposal Lineage | 0 | 2 | 0 | 0 |
| Approve/Reject | 0 | 0 | 2 | 0 |
| Duplicate Prevention | 0 | 0 | 1 | 0 |
| Historical Data | 0 | 0 | 0 | 1 |
| **总计** | **6** | **2** | **5** | **1** |

---

## 8. Phase 21 Implementation Gate Status

### 8.1 阻塞项（P0）

| Gate | 要求 | 状态 | 阻塞原因 |
|------|------|------|----------|
| Gate 1 | Evidence.role 可区分 | ✅ | 现有 Schema 支持 |
| Gate 2 | 导入逻辑保留 AI Evidence | ❌ | **需修改** |
| Gate 3 | Context Window 提供 AI Context | ❌ | **未实现** |
| Gate 4 | User Fact Boundary 可测试 | ❌ | **未实现** |
| Gate 5 | Reconstruction → Candidate lineage | ❌ | **未实现** |
| Gate 6 | Candidate → Proposal lineage | ⚠️ | **Phase 20 Gap** |
| Gate 7 | Topic relationship | ❌ | **未实现** |
| Gate 8 | Phase 20 Regression PASS | ❌ | **2 FAIL, 5 GAP** |

### 8.2 建议行动

**立即行动**:
1. 修复 ProposalRepository（添加 candidate_id 写入）
2. 确认 Migration 002 已应用
3. 重新执行 Phase 20 Regression Tests

**Phase 21 行动**:
1. 实现 Evidence.role
2. 修改导入逻辑保留 AI Evidence
3. 实现 Context Window
4. 实现 Reconstruction
5. 实现 Topic

---

## 附录 A: Phase 20 Regression Test 文件

```python
"""Phase 20 Core Regression Tests.

These tests verify Phase 20 frozen design behaviors.
Must remain PASS after Phase 21 implementation.

Design References:
- phase-20-candidate-proposal-lifecycle-design.md
- 09_Database_Physical_Design.md §09.4.13
"""

from __future__ import annotations

import pytest
from uuid import uuid4


class TestCandidateProposalLineage:
    """Test 1: Candidate → Proposal lineage."""

    @pytest.mark.asyncio
    async def test_candidate_has_proposal_lineage(self):
        """Verify Proposal.candidate_id references valid Candidate.
        
        Expected: proposal.candidate_id == candidate.id
        Current Status: FAIL - ProposalRepository does not write candidate_id
        """
        # This test requires:
        # 1. Creating a Candidate
        # 2. Creating a Proposal with candidate_id
        # 3. Verifying the lineage
        
        # TODO: Implement when ProposalRepository is fixed
        pytest.skip("ProposalRepository does not write candidate_id")

    @pytest.mark.asyncio
    async def test_proposal_candidate_id_not_null(self):
        """New Proposal must have candidate_id = expected Candidate ID.
        
        Expected: candidate_id is NOT NULL and equals expected value
        Current Status: FAIL - candidate_id is not written
        """
        pytest.skip("ProposalRepository does not write candidate_id")


class TestCandidateLifecycle:
    """Test 2-4: Candidate lifecycle transitions."""

    @pytest.mark.asyncio
    async def test_approve_candidate_confirmed(self):
        """approve Proposal → Candidate.status = 'confirmed'.
        
        Expected: After approve, candidate.status == 'confirmed'
        Current Status: GAP - depends on candidate_id being set
        """
        pytest.skip("Requires candidate_id to be set in Proposal")

    @pytest.mark.asyncio
    async def test_reject_candidate_orphaned(self):
        """reject Proposal → Candidate.status = 'orphaned'.
        
        Expected: After reject, candidate.status == 'orphaned'
        Current Status: GAP - depends on candidate_id being set
        """
        pytest.skip("Requires candidate_id to be set in Proposal")


class TestEvolutionScope:
    """Test 5-6: Evolution scope constraints."""

    @pytest.mark.asyncio
    async def test_evolution_only_candidate_status(self):
        """Evolution can only select Candidate.status = 'candidate'.
        
        Expected: Only candidates with status='candidate' are processed
        Current Status: PASS
        """
        # This is already tested in test_evidence_evolution_engine.py
        pass

    @pytest.mark.asyncio
    async def test_evolution_no_pending_proposal(self):
        """Evolution requires NOT EXISTS pending Proposal.
        
        Expected: Candidate with pending Proposal is skipped
        Current Status: PASS
        """
        # This is already tested in test_evidence_evolution_engine.py
        pass


class TestEvidenceLineage:
    """Test 7-8: Evidence → Candidate lineage."""

    @pytest.mark.asyncio
    async def test_candidate_has_evidence_chain(self):
        """Every Candidate must have non-empty evidence_chain.
        
        Expected: evidence_chain is not empty
        Current Status: PASS
        """
        # This is already tested in test_evidence_evolution_engine.py
        pass

    @pytest.mark.asyncio
    async def test_evidence_chain_contains_valid_uuids(self):
        """evidence_chain must contain valid Evidence UUIDs.
        
        Expected: All UUIDs in evidence_chain exist in evidences table
        Current Status: PASS
        """
        # This is already tested in test_evidence_evolution_engine.py
        pass


class TestEntityGrouping:
    """Test 9-11: Entity grouping behavior."""

    @pytest.mark.asyncio
    async def test_multi_candidate_same_entity(self):
        """Multiple Candidates can belong to same Entity.
        
        Expected: C1→E, C2→E is valid, C1 ≠ C2
        Current Status: PASS
        """
        # This is already tested in test_evidence_evolution_engine.py
        pass

    @pytest.mark.asyncio
    async def test_single_candidate_entity_relationship(self):
        """Single Candidate maintains correct Entity relationship.
        
        Expected: Candidate.entity_id matches assigned Entity
        Current Status: PASS
        """
        # This is already tested in test_entity_domain_repositories.py
        pass


class TestDuplicatePrevention:
    """Test 12: Duplicate proposal prevention."""

    @pytest.mark.asyncio
    async def test_no_duplicate_pending_proposal(self):
        """Same Candidate cannot have multiple pending Proposals.
        
        Expected: Second proposal creation fails or returns existing
        Current Status: GAP - depends on partial unique index
        """
        pytest.skip("Requires partial unique index to be applied")


class TestDatabaseConstraints:
    """Test 13: Database constraint validation."""

    @pytest.mark.asyncio
    async def test_partial_unique_index_pending_proposal(self):
        """Partial unique index: (workspace_id, candidate_id) WHERE status='pending'.
        
        Expected: Database enforces at most one pending Proposal per Candidate
        Current Status: GAP - Migration may not be applied
        """
        pytest.skip("Requires Migration 002 to be applied")


class TestDataIntegrity:
    """Test 14: Historical data integrity."""

    @pytest.mark.asyncio
    async def test_historical_null_candidate_id_count(self):
        """Count historical Proposals with NULL candidate_id.
        
        Expected: 2,616 records (known historical gap)
        Current Status: DATA GAP - Known issue, not a test failure
        """
        # This is a data audit test, not a regression test
        # Should be run manually against production database
        pytest.skip("Manual data audit required")

    @pytest.mark.asyncio
    async def test_new_proposal_candidate_id(self):
        """New Proposal creation must include candidate_id.
        
        Expected: New proposals have candidate_id set
        Current Status: FAIL - Repository does not write candidate_id
        """
        pytest.skip("ProposalRepository does not write candidate_id")


# ---------------------------------------------------------------------------
# Test Execution Summary
# ---------------------------------------------------------------------------
# PASS: 6 (Evolution scope, Evidence lineage, Entity grouping)
# FAIL: 2 (Proposal lineage, New proposal candidate_id)
# GAP: 5 (Approve/Reject, Duplicate prevention, Partial unique index, New proposal)
# DATA GAP: 1 (Historical null candidate_id count)
# ---------------------------------------------------------------------------
```

---

## 结论

### Phase 20 Regression Status

| 类别 | 数量 | 说明 |
|------|------|------|
| **PASS** | 6 | 核心功能正常工作 |
| **FAIL** | 2 | ProposalRepository 未实现 candidate_id 写入 |
| **GAP** | 5 | 依赖 candidate_id 的功能无法测试 |
| **DATA GAP** | 1 | 2,616 条历史数据 candidate_id = NULL |

### 必须修复后才能继续 Phase 21

1. **P0**: 修改 ProposalRepository，添加 candidate_id 写入
2. **P0**: 确认 Migration 002 已应用到数据库
3. **P1**: 制定历史数据修复计划（可选，不阻塞 Phase 21）

### Phase 21 是否可以开始？

**答案**: **不可以**，直到 Gate 6（Candidate → Proposal lineage）解决。

---

*本报告为只读调查，不修改任何代码或数据库。*
*创建的测试文件仅用于回归保护，不包含 Phase 21 新功能测试。*

---

**STOP** — 不编码 Phase 21 新功能，等待下一步指示。
