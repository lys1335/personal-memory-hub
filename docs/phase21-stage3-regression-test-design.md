# Phase 21 Stage 3 — Regression Test Design

**项目**: Personal Memory Hub  
**阶段**: Phase 21 Stage 3  
**调查日期**: 2026-08-13  
**范围**: 只读调查，设计 Regression Test Suite，不修改任何代码、测试、数据库、Schema 或设计文档  

---

## 1. Test Strategy

### 1.1 核心原则

> **Design → Expected Behavior → Regression Test**

而不是：

> **Current Code → 写测试证明 Current Code 正确**

如果当前实现与设计冲突：

标记为 **DESIGN / IMPLEMENTATION GAP**

不要通过修改设计迁就代码。

### 1.2 测试分层架构

```
┌─────────────────────────────────────────────────────────┐
│                    Layer 5: E2E                         │
│              End-to-End Scenario Tests                  │
│              (完整 Pipeline 验证)                        │
├─────────────────────────────────────────────────────────┤
│                    Layer 4: Integration                  │
│              Cross-Layer Interaction Tests               │
│              (Service + Engine + Repository)             │
├─────────────────────────────────────────────────────────┤
│                    Layer 3: Repository                  │
│              DB Schema + Data Integrity Tests            │
│              (Evidence, Candidate, Proposal, Topic)      │
├─────────────────────────────────────────────────────────┤
│                    Layer 2: Service/Engine               │
│              Business Logic Tests                        │
│              (Reconstruction, Context Window,            │
│               User Fact Boundary)                        │
├─────────────────────────────────────────────────────────┤
│                    Layer 1: Unit                        │
│              Component-Level Tests                       │
│              (EvidenceEvolutionEngine, ReflectionEngine) │
└─────────────────────────────────────────────────────────┘
```

### 1.3 测试优先级

| 优先级 | 含义 | 数量估算 |
|--------|------|----------|
| **P0** | 必须通过，阻塞发布 | ~30 |
| **P1** | 重要功能，应当通过 | ~25 |
| **P2** | 增强覆盖，可选 | ~15 |

---

## 2. Existing Test Baseline

### 2.1 当前测试结构

**测试目录**: `backend/tests/`

**测试文件清单**:

| 文件 | 行数 | 主要测试内容 |
|------|------|-------------|
| `test_evidence_evolution_engine.py` | 306 | EvidenceEvolutionEngine 单元测试 |
| `test_reflection_engine.py` | 391 | ReflectionEngine 单元测试 |
| `test_engine_layer.py` | 898 | Engine Layer 集成测试 |
| `test_service_layer.py` | 826 | Service Layer 测试 |
| `test_integration.py` | 336 | E2E 完整生命周期测试 |
| `test_memory_domain_repositories.py` | 843 | Memory Repository 测试 |
| `test_entity_domain_repositories.py` | 1277 | Entity Repository 测试 |
| `test_repository_infrastructure.py` | 651 | Repository 基础设施测试 |
| `test_entry_layer.py` | 509 | Entry Layer 测试 |
| `test_chatgpt_adapter.py` | 455 | ChatGPT Adapter 测试 |
| `test_import_framework.py` | 294 | Import Framework 测试 |
| `test_import_integration.py` | 229 | Import Integration 测试 |
| `test_cron_deadlock.py` | 132 | Cron Deadlock 测试 |
| `test_fixtures.py` | 128 | Fixtures 测试 |
| `test_smoke.py` | 9 | Smoke Test |

**总计**: 16 个测试文件，7,306 行代码

### 2.2 现有测试覆盖分析

**已覆盖**:
- ✅ EvidenceEvolutionEngine 基本功能
- ✅ ReflectionEngine 基本功能
- ✅ Memory Lifecycle（capture → retrieve → query）
- ✅ Entity Domain Repository
- ✅ Memory Domain Repository
- ✅ Import Adapter（ChatGPT, OpenWebUI）

**未覆盖（Phase 21 新增）**:
- ❌ Reconstruction Architecture
- ❌ Context Window
- ❌ User Fact Boundary
- ❌ Topic Definition
- ❌ Candidate → Proposal Lineage（Phase 20 但未专门测试）
- ❌ Evidence Role（user vs assistant）
- ❌ Short Confirmation Handling
- ❌ AI Pollution Protection

### 2.3 Phase 20 Regression 状态

**来源**: Phase 20 文档

**已确认 14/14 Core Regression Tests Passed**:

| # | 测试项 | 状态 |
|---|--------|------|
| 1 | Candidate → Proposal lineage | ✅ PASS |
| 2 | proposals.candidate_id FK | ✅ PASS |
| 3 | approve → Candidate confirmed | ✅ PASS |
| 4 | reject → Candidate orphaned | ✅ PASS |
| 5 | Evolution scope（candidate status + no pending proposal） | ✅ PASS |
| 6 | Evidence → Candidate lineage | ✅ PASS |
| 7 | Entity grouping（entity, candidate_id） | ✅ PASS |
| 8 | 多 Candidate → 同一 Entity 不错误合并 | ✅ PASS |
| 9 | 单 Candidate → 多 Entity 保持 lineage | ✅ PASS |
| 10 | Partial unique index（workspace_id, candidate_id WHERE status='pending'） | ✅ PASS |
| 11 | Candidate lifecycle（candidate → confirmed → archived → orphaned） | ✅ PASS |
| 12 | Pending Proposal dedup | ✅ PASS |
| 13 | Evidence immutable | ✅ PASS |
| 14 | No Orphan Memory | ✅ PASS |

**发现 Gap**:
- ⚠️ 2,616 条历史 Proposal 的 candidate_id = NULL（现有实现问题）
- ⚠️ 没有专门的 Phase 20 Regression Test 文件

---

## 3. Phase 20 Regression Preservation

### 3.1 必须保留的测试

**策略**: 将 Phase 20 核心测试移入专门文件，确保 Phase 21 不会破坏。

**新增文件**: `backend/tests/test_phase20_regression.py`

**测试内容**:

```python
"""Phase 20 Core Regression Tests.

These tests must remain PASS after Phase 21 implementation.
"""

class TestCandidateProposalLineage:
    """Test 1: Candidate → Proposal lineage."""
    
    async def test_candidate_has_proposal_lineage(self):
        """Verify Proposal.candidate_id references valid Candidate."""
        ...

class TestCandidateLifecycle:
    """Test 2-4: Candidate lifecycle transitions."""
    
    async def test_approve_candidate_confirmed(self):
        """approve → Candidate.status = 'confirmed'."""
        ...
    
    async def test_reject_candidate_orphaned(self):
        """reject → Candidate.status = 'orphaned'."""
        ...

class TestEvidenceLineage:
    """Test 5-6: Evidence → Candidate lineage."""
    
    async def test_candidate_has_evidence_chain(self):
        """Every Candidate must have non-empty evidence_chain."""
        ...

class TestEntityGrouping:
    """Test 7-9: Entity grouping behavior."""
    
    async def test_multi_candidate_same_entity(self):
        """Multiple Candidates can belong to same Entity."""
        ...
```

### 3.2 验证方法

**执行方式**:
```bash
pytest backend/tests/test_phase20_regression.py -v
```

**通过标准**: 14/14 tests PASS

---

## 4. Phase 21 P0 Tests

### 4.1 Evidence Role Tests（P0）

**背景**: Stage 2.3 发现当前 Evidence 缺少 role 字段。

**测试文件**: `backend/tests/test_evidence_role_regression.py`

#### Test E-001: User Evidence Identification

```python
async def test_user_evidence_has_role_user():
    """User Evidence must have metadata.role = 'user'."""
    evidence = await create_user_evidence("我决定使用 PostgreSQL")
    assert evidence.metadata.get("role") == "user"
```

#### Test E-002: Assistant Evidence Identification

```python
async def test_assistant_evidence_has_role_assistant():
    """Assistant Evidence must have metadata.role = 'assistant'."""
    evidence = await create_assistant_evidence("建议采用 PostgreSQL")
    assert evidence.metadata.get("role") == "assistant"
```

#### Test E-003: Role Distinction

```python
async def test_system_can_distinguish_user_vs_assistant():
    """System must be able to distinguish user vs assistant Evidence."""
    user_ev = await create_user_evidence("我确认")
    assistant_ev = await create_assistant_evidence("建议 A")
    
    user_evidences = await get_evidences_by_role("user")
    assistant_evidences = await get_evidences_by_role("assistant")
    
    assert len(user_evidences) == 1
    assert len(assistant_evidences) == 1
```

#### Test E-004: Assistant Evidence in Context

```python
async def test_assistant_evidence_can_enter_context():
    """Assistant Evidence can enter Context Window."""
    assistant_ev = await create_assistant_evidence("建议使用 PostgreSQL")
    
    context = await build_context_window(trigger_evidence=assistant_ev)
    
    assert assistant_ev.id in context.evidence_ids
```

#### Test E-005: Assistant Evidence Cannot Form Candidate Alone

```python
async def test_assistant_evidence_cannot_form_candidate_alone():
    """Assistant Evidence alone cannot form User Candidate."""
    assistant_ev = await create_assistant_evidence("建议使用 PostgreSQL")
    
    candidates = await try_form_candidates([assistant_ev])
    
    assert len(candidates) == 0
```

### 4.2 Short Confirmation Tests（P0）

**测试文件**: `backend/tests/test_short_confirmation_regression.py`

#### Test SC-001: Simple Confirmation

```python
async def test_simple_confirmation_ai_to_user():
    """AI: '建议使用 PostgreSQL' → User: '对，就这样' → Candidate: '用户确认采用 PostgreSQL'."""
    
    # Create context
    ai_ev = await create_assistant_evidence("建议使用 PostgreSQL")
    user_ev = await create_user_evidence("对，就这样")
    
    # Build context window
    context = await build_context_window(trigger_evidence=user_ev, include_recent=True)
    
    # Form reconstruction
    reconstruction = await form_reconstruction(context)
    
    # Verify semantic
    assert "用户确认" in reconstruction.semantic_summary
    assert "PostgreSQL" in reconstruction.semantic_summary
    assert "建议" not in reconstruction.semantic_summary  # Should not be AI's suggestion
    
    # Form candidate
    candidates = await form_candidates(reconstruction)
    assert len(candidates) == 1
    assert "用户决定" in candidates[0].content or "用户确认" in candidates[0].content
```

#### Test SC-002: Selection Confirmation

```python
async def test_selection_confirmation():
    """AI: '方案 A / B / C' → User: '第二个' → Candidate: '用户选择方案 B'."""
    
    ai_ev = await create_assistant_evidence("方案 A 成本低，方案 B 更稳定，方案 C 性能最好")
    user_ev = await create_user_evidence("第二个")
    
    context = await build_context_window(trigger_evidence=user_ev, include_recent=True)
    reconstruction = await form_reconstruction(context)
    candidates = await form_candidates(reconstruction)
    
    assert len(candidates) == 1
    assert "方案 B" in candidates[0].content
```

#### Test SC-003: Ambiguous Acknowledgment

```python
async def test_ambiguous_acknowledgment_no_candidate():
    """AI: '建议 A' → User: '知道了' → No Candidate (just acknowledgment)."""
    
    ai_ev = await create_assistant_evidence("建议使用 PostgreSQL")
    user_ev = await create_user_evidence("知道了")
    
    context = await build_context_window(trigger_evidence=user_ev, include_recent=True)
    reconstruction = await form_reconstruction(context)
    candidates = await form_candidates(reconstruction)
    
    assert len(candidates) == 0  # "知道了" is not confirmation
```

#### Test SC-004: Mild Confirmation as Preference

```python
async def test_mild_confirmation_as_preference():
    """AI: '建议 A' → User: '可以' → Candidate with preference semantics."""
    
    ai_ev = await create_assistant_evidence("建议使用 PostgreSQL")
    user_ev = await create_user_evidence("可以")
    
    context = await build_context_window(trigger_evidence=user_ev, include_recent=True)
    reconstruction = await form_reconstruction(context)
    candidates = await form_candidates(reconstruction)
    
    assert len(candidates) == 1
    # Should be preference, not decision
    assert "倾向于" in candidates[0].content or "偏好" in candidates[0].content
```

### 4.3 Rejection / Correction Tests（P0）

**测试文件**: `backend/tests/test_rejection_correction_regression.py`

#### Test RC-001: Rejection of AI Suggestion

```python
async def test_rejection_of_ai_suggestion():
    """AI: '你决定使用 PostgreSQL' → User: '不，我只是考虑' → Candidate: '用户仅在考虑 PostgreSQL'."""
    
    ai_ev = await create_assistant_evidence("你决定使用 PostgreSQL")
    user_ev = await create_user_evidence("不，我只是考虑")
    
    context = await build_context_window(trigger_evidence=user_ev, include_recent=True)
    reconstruction = await form_reconstruction(context)
    candidates = await form_candidates(reconstruction)
    
    assert len(candidates) == 1
    assert "仅" in candidates[0].content or "考虑" in candidates[0].content
    assert "决定" not in candidates[0].content  # Should NOT say "decided"
```

#### Test RC-002: Correction of AI Understanding

```python
async def test_correction_of_ai_understanding():
    """AI: '你决定 PostgreSQL' → User: '不对，我是说 MySQL' → Candidate: '用户决定使用 MySQL'."""
    
    ai_ev = await create_assistant_evidence("你决定使用 PostgreSQL")
    user_ev = await create_user_evidence("不对，我是说 MySQL")
    
    context = await build_context_window(trigger_evidence=user_ev, include_recent=True)
    reconstruction = await form_reconstruction(context)
    candidates = await form_candidates(reconstruction)
    
    assert len(candidates) == 1
    assert "MySQL" in candidates[0].content
    assert "PostgreSQL" not in candidates[0].content
```

#### Test RC-003: Partial Acceptance

```python
async def test_partial_acceptance_multiple_candidates():
    """AI: 'A + B + C' → User: 'A 可以，B 不行，C 再看看' → 3 Candidates."""
    
    ai_ev = await create_assistant_evidence("我建议方案 A + B + C")
    user_ev = await create_user_evidence("A 可以，但 B 不行，C 再看看")
    
    context = await build_context_window(trigger_evidence=user_ev, include_recent=True)
    reconstruction = await form_reconstruction(context)
    candidates = await form_candidates(reconstruction)
    
    assert len(candidates) >= 2  # At least A accepted, B rejected
    # Verify semantic separation
    accepted = [c for c in candidates if "A" in c.content and "接受" in c.content]
    rejected = [c for c in candidates if "B" in c.content and "否定" in c.content]
    
    assert len(accepted) >= 1
    assert len(rejected) >= 1
```

### 4.4 AI Pollution Protection Tests（P0）

**测试文件**: `backend/tests/test_ai_pollution_protection.py`

#### Test AP-001: Pure Assistant Evidence

```python
async def test_pure_assistant_evidence_no_candidate():
    """Only Assistant Evidence → 0 User Candidates."""
    
    assistant_evidences = [
        await create_assistant_evidence("建议采用 PostgreSQL"),
        await create_assistant_evidence("PostgreSQL 的优势是..."),
    ]
    
    candidates = await try_form_candidates(assistant_evidences)
    
    assert len(candidates) == 0
```

#### Test AP-002: AI Recommendation Without Confirmation

```python
async def test_ai_recommendation_without_confirmation():
    """AI recommendation without user adoption → 0 Candidates."""
    
    ai_ev = await create_assistant_evidence("建议采用 PostgreSQL")
    # No user response
    
    candidates = await try_form_candidates([ai_ev])
    
    assert len(candidates) == 0
```

#### Test AP-003: Multiple AI Messages

```python
async def test_multiple_ai_messages_no_candidate():
    """Multiple consecutive AI messages without user adoption → 0 Candidates."""
    
    ai_evidences = [
        await create_assistant_evidence("方案 A 成本低"),
        await create_assistant_evidence("方案 B 更稳定"),
        await create_assistant_evidence("方案 C 性能最好"),
    ]
    
    candidates = await try_form_candidates(ai_evidences)
    
    assert len(candidates) == 0
```

#### Test AP-004: AI Statement With Unrelated User Response

```python
async def test_ai_statement_with_unrelated_user_response():
    """AI statement with unrelated user response → No false association."""
    
    ai_ev = await create_assistant_evidence("建议使用 PostgreSQL")
    user_ev = await create_user_evidence("今天天气不错")
    
    context = await build_context_window(trigger_evidence=user_ev, include_recent=True)
    reconstruction = await form_reconstruction(context)
    candidates = await form_candidates(reconstruction)
    
    # Should not falsely associate "天气" with "PostgreSQL"
    assert len(candidates) == 0 or "PostgreSQL" not in candidates[0].content
```

### 4.5 Reconstruction Lineage Tests（P0）

**测试文件**: `backend/tests/test_reconstruction_lineage.py`

#### Test RL-001: Version Chain

```python
async def test_reconstruction_version_chain():
    """R1 → R2 → R3 version chain preserves each Candidate snapshot."""
    
    # R1
    r1 = await create_reconstruction(
        evidence_refs=["ev1"],
        semantic_summary="用户决定使用 PostgreSQL"
    )
    c1 = await create_candidate(
        reconstruction_id=r1.id,
        content="用户决定使用 PostgreSQL",
        evidence_chain=["ev1"]
    )
    
    # R2 (parent = R1)
    r2 = await create_reconstruction(
        parent_reconstruction_id=r1.id,
        evidence_refs=["ev1", "ev2"],
        semantic_summary="用户决定使用 PostgreSQL，并通过 Docker 部署"
    )
    c2 = await create_candidate(
        reconstruction_id=r2.id,
        content="用户决定使用 PostgreSQL，并通过 Docker 部署",
        evidence_chain=["ev1", "ev2"]
    )
    
    # R3 (parent = R2)
    r3 = await create_reconstruction(
        parent_reconstruction_id=r2.id,
        evidence_refs=["ev1", "ev2", "ev3"],
        semantic_summary="用户改为使用 SQLite"
    )
    c3 = await create_candidate(
        reconstruction_id=r3.id,
        content="用户改为使用 SQLite",
        evidence_chain=["ev1", "ev2", "ev3"]
    )
    
    # Verify C1 is NOT modified
    c1_refreshed = await get_candidate(c1.id)
    assert c1_refreshed.content == "用户决定使用 PostgreSQL"
    assert c1_refreshed.status == "confirmed"  # Or whatever it was
    
    # Verify lineage
    assert r2.parent_reconstruction_id == r1.id
    assert r3.parent_reconstruction_id == r2.id
```

#### Test RL-002: Candidate Independence

```python
async def test_candidate_is_immutable_snapshot():
    """Once created, Candidate content cannot be modified by later Reconstructions."""
    
    r1 = await create_reconstruction(evidence_refs=["ev1"])
    c1 = await create_candidate(reconstruction_id=r1.id, content="原始内容")
    
    # Later Reconstruction
    r2 = await create_reconstruction(
        parent_reconstruction_id=r1.id,
        evidence_refs=["ev1", "ev2"]
    )
    
    # C1 should not change
    c1_after = await get_candidate(c1.id)
    assert c1_after.content == "原始内容"
```

### 4.6 Proposal Lineage Tests（P0）

**测试文件**: `backend/tests/test_proposal_lineage.py`

#### Test PL-001: Candidate → Proposal Lineage

```python
async def test_proposal_has_candidate_id():
    """New Proposal must have candidate_id = expected Candidate ID."""
    
    c1 = await create_candidate(content="用户决定使用 PostgreSQL")
    p1 = await create_proposal(candidate_id=c1.id, status="pending")
    
    assert p1.candidate_id == c1.id
    assert p1.candidate_id is not None
```

#### Test PL-002: Pending Proposal Dedup

```python
async def test_pending_proposal_dedup():
    """Candidate with pending Proposal cannot generate another Proposal."""
    
    c1 = await create_candidate(content="测试")
    p1 = await create_proposal(candidate_id=c1.id, status="pending")
    
    # Try to create another Proposal
    p2 = await try_create_proposal(candidate_id=c1.id)
    
    assert p2 is None  # Should not create duplicate
```

#### Test PL-003: Approve → Confirmed

```python
async def test_approve_candidate_confirmed():
    """Approve Proposal → Candidate.status = 'confirmed'."""
    
    c1 = await create_candidate(content="测试")
    p1 = await create_proposal(candidate_id=c1.id, status="pending")
    
    await approve_proposal(p1.id)
    
    c1_refreshed = await get_candidate(c1.id)
    assert c1_refreshed.status == "confirmed"
```

#### Test PL-004: Reject → Orphaned

```python
async def test_reject_candidate_orphaned():
    """Reject Proposal → Candidate.status = 'orphaned'."""
    
    c1 = await create_candidate(content="测试")
    p1 = await create_proposal(candidate_id=c1.id, status="pending")
    
    await reject_proposal(p1.id)
    
    c1_refreshed = await get_candidate(c1.id)
    assert c1_refreshed.status == "orphaned"
```

---

## 5. Phase 21 P1 Tests

### 5.1 Context Window Tests（P1）

**测试文件**: `backend/tests/test_context_window_regression.py`

#### Test CW-001: Short Confirmation Context Expansion

```python
async def test_short_confirmation_context_expansion():
    """Trigger Evidence '对' must expand context to include previous AI content."""
    
    # Create sequence
    ev1 = await create_user_evidence("我准备改架构")
    ev2 = await create_assistant_evidence("建议采用 Reconstruction → Candidate 模式")
    ev3 = await create_user_evidence("对")
    
    # Build context for ev3
    context = await build_context_window(trigger_evidence=ev3)
    
    # Must include ev2 (AI content)
    assert ev2.id in context.evidence_ids
    assert len(context.evidence_ids) >= 2
```

#### Test CW-002: Long AI Response Handling

```python
async def test_long_ai_response_selective_use():
    """Long AI response should be selectively used, not fully copied."""
    
    long_ai_content = "A" * 5000  # 5000 tokens
    ev1 = await create_assistant_evidence(long_ai_content)
    ev2 = await create_user_evidence("同意")
    
    context = await build_context_window(trigger_evidence=ev2)
    
    # Should use summary or relevant span, not full 5000 tokens
    assert context.token_count < 5000 or context.has_summary
```

#### Test CW-003: Topic Drift Detection

```python
async def test_topic_drift_boundary():
    """Topic drift should create Context boundary."""
    
    # Topic A
    ev1 = await create_user_evidence("讨论 Memory Hub 架构")
    ev2 = await create_assistant_evidence("Memory Hub 应该...")
    
    # Topic B
    ev3 = await create_user_evidence("PostgreSQL 选型")
    ev4 = await create_assistant_evidence("PostgreSQL 优势...")
    
    # Back to Topic A
    ev5 = await create_user_evidence("回到架构讨论")
    
    context = await build_context_window(trigger_evidence=ev5)
    
    # Should recognize topic return, not include Topic B noise
    assert ev3.id not in context.evidence_ids or context.has_topic_filter
```

#### Test CW-004: Explicit Topic Switch

```python
async def test_explicit_topic_switch_boundary():
    """User explicit topic switch creates hard boundary."""
    
    ev1 = await create_user_evidence("讨论架构")
    ev2 = await create_user_evidence("换个问题")
    ev3 = await create_user_evidence("PostgreSQL 怎么选")
    
    context = await build_context_window(trigger_evidence=ev3)
    
    # Should not include ev1 (topic switched)
    assert ev1.id not in context.evidence_ids
```

#### Test CW-005: Cross-Conversation Recall

```python
async def test_cross_conversation_recall():
    """New Evidence in new conversation should recall related existing Reconstruction."""
    
    # Conversation 1
    r1 = await create_reconstruction(
        workspace_id=w1,
        evidence_refs=["ev1", "ev2"],
        semantic_summary="用户决定使用 PostgreSQL"
    )
    
    # Conversation 2 (new)
    ev3 = await create_user_evidence("继续讨论 PostgreSQL 部署")
    
    context = await build_context_window(
        trigger_evidence=ev3,
        enable_cross_conversation=True
    )
    
    # Should recall R1
    assert context.has_recall or context.related_reconstruction_id == r1.id
```

### 5.2 Topic Tests（P1）

**测试文件**: `backend/tests/test_topic_regression.py`

#### Test T-001: Reconstruction ↔ Topic N:M

```python
async def test_reconstruction_multiple_topics():
    """One Reconstruction can have multiple Topics."""
    
    r1 = await create_reconstruction(
        evidence_refs=["ev1"],
        semantic_summary="用户决定使用 PostgreSQL 并通过 Docker 部署"
    )
    
    topic_a = await create_topic(name="数据库选型")
    topic_b = await create_topic(name="部署方案")
    
    await link_reconstruction_to_topics(r1.id, [topic_a.id, topic_b.id])
    
    r1_topics = await get_topics_for_reconstruction(r1.id)
    assert len(r1_topics) == 2
```

#### Test T-002: Topic ↔ Reconstruction N:M

```python
async def test_topic_multiple_reconstructions():
    """One Topic can have multiple Reconstructions."""
    
    topic = await create_topic(name="Memory Hub 架构")
    
    r1 = await create_reconstruction(
        evidence_refs=["ev1"],
        semantic_summary="初始架构设计"
    )
    r2 = await create_reconstruction(
        evidence_refs=["ev2"],
        semantic_summary="架构优化"
    )
    
    await link_reconstruction_to_topics(r1.id, [topic.id])
    await link_reconstruction_to_topics(r2.id, [topic.id])
    
    topic_reconstructions = await get_reconstructions_for_topic(topic.id)
    assert len(topic_reconstructions) == 2
```

#### Test T-003: Topic Hierarchy

```python
async def test_topic_hierarchy():
    """Topic can have parent-child relationship."""
    
    parent = await create_topic(name="数据库")
    child = await create_topic(name="PostgreSQL", parent_topic_id=parent.id)
    
    assert child.parent_topic_id == parent.id
    
    children = await get_children_topics(parent.id)
    assert len(children) == 1
```

#### Test T-004: Topic ≠ Entity

```python
async def test_topic_not_equivalent_to_entity():
    """Topic and Entity are distinct concepts."""
    
    entity = await create_entity(canonical_name="PostgreSQL", entity_type="Technology")
    topic = await create_topic(name="数据库选型")
    
    # Topic can be about Entity, but not the same
    await link_topic_to_entity(topic.id, entity.id)
    
    topic_link = await get_topic_links(topic.id)
    assert any(link.target_type == "entity" for link in topic_link)
    
    # But they are not the same object
    assert topic.id != entity.id
```

### 5.3 User Fact Boundary Tests（P1）

**测试文件**: `backend/tests/test_user_fact_boundary.py`

#### Test UF-001: Explicit Fact

```python
async def test_explicit_fact_candidate():
    """Explicit user fact forms Candidate."""
    
    ev = await create_user_evidence("我使用 Windows")
    
    candidates = await try_form_candidates([ev])
    
    assert len(candidates) == 1
    assert "Windows" in candidates[0].content
```

#### Test UF-002: Hypothetical No Candidate

```python
async def test_hypothetical_no_candidate():
    """Hypothetical statement does not form Candidate."""
    
    ev = await create_user_evidence("如果以后需要，我可能会用 PostgreSQL")
    
    candidates = await try_form_candidates([ev])
    
    assert len(candidates) == 0  # Not a definite fact
```

#### Test UF-003: Third-Party Fact No Candidate

```python
async def test_third_party_fact_no_candidate():
    """Third-party fact does not form User Candidate."""
    
    ev = await create_user_evidence("我朋友使用 PostgreSQL")
    
    candidates = await try_form_candidates([ev])
    
    assert len(candidates) == 0  # Not user's own fact
```

#### Test UF-004: Conditional Fact

```python
async def test_conditional_fact_candidate():
    """Conditional fact forms Candidate with condition metadata."""
    
    ev = await create_user_evidence("如果预算够，我会升级")
    
    candidates = await try_form_candidates([ev])
    
    assert len(candidates) == 1
    assert "预算" in candidates[0].content
    assert candidates[0].metadata.get("condition") == "预算够"
```

### 5.4 Temporal / Historical Tests（P1）

**测试文件**: `backend/tests/test_temporal_semantics.py`

#### Test TS-001: Historical Candidate Preservation

```python
async def test_historical_candidate_preserved():
    """Old Candidate is not modified when new fact replaces it."""
    
    # T1: User uses PostgreSQL
    c1 = await create_candidate(content="用户决定使用 PostgreSQL")
    
    # T2: User switches to SQLite
    c2 = await create_candidate(content="用户改为使用 SQLite")
    
    # C1 should not change
    c1_refreshed = await get_candidate(c1.id)
    assert c1_refreshed.content == "用户决定使用 PostgreSQL"
    assert c1_refreshed.status != "superseded"  # Not automatically superseded
```

#### Test TS-002: Negative State Candidate

```python
async def test_negative_state_candidate():
    """Negative user statement forms negative Candidate."""
    
    ev = await create_user_evidence("我不再使用 PostgreSQL")
    
    candidates = await try_form_candidates([ev])
    
    assert len(candidates) == 1
    assert "不再" in candidates[0].content or "否定" in candidates[0].content
```

#### Test TS-003: Uncertain State Candidate

```python
async def test_uncertain_state_candidate():
    """Uncertain user statement forms uncertain Candidate."""
    
    ev = await create_user_evidence("我只是在考虑 PostgreSQL")
    
    candidates = await try_form_candidates([ev])
    
    assert len(candidates) == 1
    assert "考虑" in candidates[0].content
```

---

## 6. P2 Tests

### 6.1 Context Budget Tests（P2）

**测试文件**: `backend/tests/test_context_budget.py`

#### Test CB-001: Normal Budget

```python
async def test_context_within_budget():
    """Context under 4000 tokens processes normally."""
    
    evidences = [await create_user_evidence(f"Message {i}") for i in range(5)]
    context = await build_context_window(evidences[-1])
    
    assert context.token_count < 4000
```

#### Test CB-002: Budget Exceeded

```python
async def test_context_exceeds_budget():
    """Context over 4000 tokens triggers budget control."""
    
    # Create many evidences
    evidences = [await create_user_evidence(f"Long message {i}" * 100) for i in range(20)]
    context = await build_context_window(evidences[-1])
    
    assert context.token_count <= 4000  # Should be capped
```

### 6.2 Long Evidence Tests（P2）

**测试文件**: `backend/tests/test_long_evidence.py`

#### Test LE-001: Long AI Response

```python
async def test_long_ai_response_handled():
    """Long AI Evidence (5000 tokens) handled correctly."""
    
    long_content = "A" * 5000
    ev = await create_assistant_evidence(long_content)
    
    # Should not cause errors
    context = await build_context_window(trigger_evidence=ev)
    assert context is not None
```

#### Test LE-002: Very Long AI Response

```python
async def test_very_long_ai_response_summary():
    """Very long AI Evidence (20000 tokens) uses summary."""
    
    very_long_content = "A" * 20000
    ev = await create_assistant_evidence(very_long_content)
    
    context = await build_context_window(trigger_evidence=ev)
    
    # Should use summary, not full content
    assert context.has_summary or context.compressed
```

---

## 7. End-to-End Scenarios

### 7.1 E2E-01: Simple Confirmation

```python
async def test_e2e_simple_confirmation():
    """Full pipeline: Evidence → Context → Reconstruction → Candidate → Proposal."""
    
    # Step 1: User expresses intention
    ev1 = await create_user_evidence("我准备把 Candidate Formation 改成 Reconstruction → Candidate")
    
    # Step 2: AI provides analysis
    ev2 = await create_assistant_evidence("建议采用 Reconstruction → Candidate 模式，原因如下...")
    
    # Step 3: User confirms
    ev3 = await create_user_evidence("对，就这样")
    
    # Step 4: Build context
    context = await build_context_window(trigger_evidence=ev3)
    assert ev2.id in context.evidence_ids  # AI context included
    
    # Step 5: Form reconstruction
    reconstruction = await form_reconstruction(context)
    assert "用户确认" in reconstruction.semantic_summary
    assert "Reconstruction → Candidate" in reconstruction.semantic_summary
    
    # Step 6: Form candidate
    candidates = await form_candidates(reconstruction)
    assert len(candidates) == 1
    assert "用户确认" in candidates[0].content
    
    # Step 7: Create proposal
    proposal = await create_proposal(candidate_id=candidates[0].id, status="pending")
    assert proposal.candidate_id == candidates[0].id
    
    # Verify full lineage
    assert proposal.candidate_id is not None
```

### 7.2 E2E-02: Multi-turn Discussion with Topic Drift

```python
async def test_e2e_multi_turn_topic_drift():
    """Multi-turn discussion with topic drift and return."""
    
    # Topic A: Memory Hub
    ev1 = await create_user_evidence("讨论 Memory Hub 架构")
    ev2 = await create_assistant_evidence("Memory Hub 应该...")
    
    # Topic B: PostgreSQL
    ev3 = await create_user_evidence("PostgreSQL 选型")
    ev4 = await create_assistant_evidence("PostgreSQL 优势...")
    
    # Back to Topic A
    ev5 = await create_user_evidence("回到架构讨论")
    ev6 = await create_user_evidence("对，就用这个架构")
    
    context = await build_context_window(trigger_evidence=ev6)
    
    # Should recognize topic return
    assert context.topic_continuity == "returned"
    assert context.primary_topic.id == get_topic_for_memory_hub()
```

### 7.3 E2E-03: Cross-Conversation Continuity

```python
async def test_e2e_cross_conversation():
    """Cross-conversation continuity with Reconstruction recall."""
    
    # Conversation 1 (Month 1)
    ev1 = await create_user_evidence("我计划使用 PostgreSQL", conversation_id="conv1")
    ev2 = await create_assistant_evidence("好的，PostgreSQL 是不错的选择", conversation_id="conv1")
    
    r1 = await form_reconstruction([ev1, ev2])
    c1 = await form_candidate(r1)
    
    # Conversation 2 (Month 3)
    ev3 = await create_user_evidence("继续讨论 PostgreSQL 部署", conversation_id="conv2")
    
    context = await build_context_window(
        trigger_evidence=ev3,
        enable_cross_conversation=True
    )
    
    # Should recall R1
    assert context.related_reconstruction_id == r1.id
    assert context.has_historical_context
```

### 7.4 E2E-04: Partial Acceptance

```python
async def test_e2e_partial_acceptance():
    """Partial acceptance forms multiple Candidates."""
    
    ev1 = await create_assistant_evidence("我建议方案 A + B + C")
    ev2 = await create_user_evidence("A 可以，B 不行，C 再看看")
    
    context = await build_context_window([ev1, ev2])
    reconstruction = await form_reconstruction(context)
    candidates = await form_candidates(reconstruction)
    
    # Should form at least 2 candidates
    assert len(candidates) >= 2
    
    # Verify semantic separation
    contents = [c.content for c in candidates]
    has_accepted = any("A" in c and "接受" in c for c in contents)
    has_rejected = any("B" in c and "否定" in c for c in contents)
    
    assert has_accepted
    assert has_rejected
```

### 7.5 E2E-05: Historical Fact Update

```python
async def test_e2e_historical_update():
    """Historical fact update preserves old Candidate."""
    
    # T1: User uses PostgreSQL
    ev1 = await create_user_evidence("我使用 PostgreSQL")
    c1 = await form_candidate(await form_reconstruction([ev1]))
    
    # T2: User switches to SQLite
    ev2 = await create_user_evidence("我改成 SQLite 了")
    c2 = await form_candidate(await form_reconstruction([ev1, ev2]))
    
    # Verify C1 unchanged
    c1_refreshed = await get_candidate(c1.id)
    assert c1_refreshed.content == "用户决定使用 PostgreSQL"
    
    # Verify C2 created
    c2_refreshed = await get_candidate(c2.id)
    assert c2_refreshed.content == "用户改为使用 SQLite"
    
    # Future: Evolution will establish superseded relationship
    # But for now, both exist independently
```

---

## 8. Test Layer Allocation

| Test ID | Layer | 说明 |
|---------|-------|------|
| E-001 ~ E-005 | Layer 1 | Unit: Evidence role detection |
| SC-001 ~ SC-004 | Layer 2 | Service: Short confirmation handling |
| RC-001 ~ RC-003 | Layer 2 | Service: Rejection/Correction |
| AP-001 ~ AP-004 | Layer 2 | Service: AI pollution protection |
| RL-001 ~ RL-002 | Layer 3 | Repository: Reconstruction lineage |
| PL-001 ~ PL-004 | Layer 3 | Repository: Proposal lineage |
| CW-001 ~ CW-005 | Layer 2 | Service: Context Window |
| T-001 ~ T-004 | Layer 3 | Repository: Topic relationships |
| UF-001 ~ UF-004 | Layer 2 | Service: User Fact Boundary |
| TS-001 ~ TS-003 | Layer 2 | Service: Temporal semantics |
| CB-001 ~ CB-002 | Layer 1 | Unit: Budget control |
| LE-001 ~ LE-002 | Layer 1 | Unit: Long evidence handling |
| E2E-001 ~ E2E-005 | Layer 5 | E2E: Full pipeline scenarios |

---

## 9. Traceability Matrix

| Design Decision | Test ID | Layer | Priority | Status |
|----------------|---------|-------|----------|--------|
| **Stage 2.1: Reconstruction Architecture** |
| Reconstruction 独立持久化 | RL-001 | Layer 3 | P0 | NOT IMPLEMENTED |
| Reconstruction ↔ Candidate = 1:1 | RL-002 | Layer 3 | P0 | NOT IMPLEMENTED |
| Version chain (parent_reconstruction_id) | RL-001 | Layer 3 | P0 | NOT IMPLEMENTED |
| **Stage 2.1A: Relationship Validation** |
| Candidate 是固定 Snapshot | RL-002 | Layer 3 | P0 | NOT IMPLEMENTED |
| **Stage 2.2: Topic Definition** |
| Topic 独立持久化 | T-001 | Layer 3 | P1 | NOT IMPLEMENTED |
| Reconstruction ↔ Topic = N:M | T-001, T-002 | Layer 3 | P1 | NOT IMPLEMENTED |
| Topic 层级关系 | T-003 | Layer 3 | P1 | NOT IMPLEMENTED |
| Topic ≠ Entity | T-004 | Layer 3 | P1 | NOT IMPLEMENTED |
| **Stage 2.3: Context Window** |
| Context Window Hybrid Model | CW-001 | Layer 2 | P0 | NOT IMPLEMENTED |
| Short confirmation context expansion | CW-001 | Layer 2 | P0 | NOT IMPLEMENTED |
| Topic drift detection | CW-003 | Layer 2 | P1 | NOT IMPLEMENTED |
| Cross-conversation recall | CW-005 | Layer 2 | P1 | NOT IMPLEMENTED |
| Context budget control | CB-001 | Layer 1 | P2 | NOT IMPLEMENTED |
| **Stage 2.4: User Fact Boundary** |
| User-owned Semantic definition | UF-001 | Layer 2 | P0 | NOT IMPLEMENTED |
| AI Evidence in Context | E-004 | Layer 1 | P0 | NOT IMPLEMENTED |
| AI Evidence cannot form Candidate alone | E-005 | Layer 1 | P0 | NOT IMPLEMENTED |
| Short confirmation semantics | SC-001 | Layer 2 | P0 | NOT IMPLEMENTED |
| Ambiguous acknowledgment handling | SC-003 | Layer 2 | P0 | NOT IMPLEMENTED |
| Rejection semantics | RC-001 | Layer 2 | P0 | NOT IMPLEMENTED |
| Correction semantics | RC-002 | Layer 2 | P0 | NOT IMPLEMENTED |
| Partial acceptance | RC-003 | Layer 2 | P0 | NOT IMPLEMENTED |
| AI pollution protection | AP-001 | Layer 2 | P0 | NOT IMPLEMENTED |
| Hypothetical no candidate | UF-002 | Layer 2 | P1 | NOT IMPLEMENTED |
| Third-party fact no candidate | UF-003 | Layer 2 | P1 | NOT IMPLEMENTED |
| Conditional fact | UF-004 | Layer 2 | P1 | NOT IMPLEMENTED |
| **Phase 20: Proposal Lineage** |
| candidate_id FK | PL-001 | Layer 3 | P0 | GAP (历史数据) |
| Pending proposal dedup | PL-002 | Layer 3 | P0 | NOT IMPLEMENTED |
| Approve → confirmed | PL-003 | Layer 3 | P0 | NOT IMPLEMENTED |
| Reject → orphaned | PL-004 | Layer 3 | P0 | NOT IMPLEMENTED |
| **Historical Memory** |
| Candidate snapshot immutability | TS-001 | Layer 2 | P1 | NOT IMPLEMENTED |
| Negative state candidate | TS-002 | Layer 2 | P1 | NOT IMPLEMENTED |
| Uncertain state candidate | TS-003 | Layer 2 | P1 | NOT IMPLEMENTED |

---

## 10. Implementation Gates

### 10.1 前置条件（必须满足才能开始 Implementation）

| Gate | 要求 | 状态 |
|------|------|------|
| **Gate 1** | Evidence.metadata 可存储 role 字段 | ✅ 现有 Schema 支持 |
| **Gate 2** | 导入逻辑可保留 AI Evidence | ❌ 需修改（当前过滤掉） |
| **Gate 3** | Context Window 可提供相关 AI Context | ❌ 未实现 |
| **Gate 4** | User-centric semantic boundary 可测试 | ❌ 未实现 |
| **Gate 5** | Reconstruction → Candidate lineage 可测试 | ❌ 未实现 |
| **Gate 6** | Candidate → Proposal lineage 可测试 | ⚠️ Phase 20 部分实现 |
| **Gate 7** | Topic relationship 可测试 | ❌ 未实现 |
| **Gate 8** | Phase 20 Regression 全部 PASS | ⚠️ 需验证 |

### 10.2 Gate 依赖关系

```
Gate 1 (Evidence role) → Gate 2 (Import logic) → Gate 3 (Context Window)
                                              ↓
Gate 4 (User Fact Boundary) ← ← ← ← ← ← ← ← ←
              ↓
Gate 5 (Reconstruction) → Gate 6 (Proposal Lineage)
              ↓
Gate 7 (Topic)
              ↓
Gate 8 (Phase 20 Verification)
```

---

## 11. Blocked / Failing / Not Implemented Tests

### 11.1 Blocked Tests（依赖未实现功能）

| Test ID | 阻塞原因 | 依赖 Gate |
|---------|----------|-----------|
| E-001 ~ E-005 | Evidence.role 未实现 | Gate 1, 2 |
| SC-001 ~ SC-004 | Context Window 未实现 | Gate 3 |
| RC-001 ~ RC-003 | User-centric Interpretation 未实现 | Gate 4 |
| AP-001 ~ AP-004 | Role distinction 未实现 | Gate 1, 2 |
| RL-001 ~ RL-002 | Reconstruction 表未创建 | Gate 5 |
| PL-001 ~ PL-004 | candidate_id 填充逻辑未完全实现 | Gate 6 |
| CW-001 ~ CW-005 | Context Window 未实现 | Gate 3 |
| T-001 ~ T-004 | Topic 表未创建 | Gate 7 |
| UF-001 ~ UF-004 | User Fact Boundary 未实现 | Gate 4 |
| TS-001 ~ TS-003 | Temporal semantics 未实现 | Gate 5 |

### 11.2 Failing Tests（现有代码行为错误）

| 测试项 | 问题 | 建议 |
|--------|------|------|
| PL-001 | 2,616 条历史 Proposal 的 candidate_id = NULL | 需数据修复或明确标记为历史 Gap |
| 所有 E-* 测试 | 当前导入逻辑过滤掉 assistant messages | 需修改导入逻辑 |

### 11.3 Not Implemented Tests（新功能）

所有 Phase 21 相关测试均为 NOT IMPLEMENTED 状态。

---

## 12. Test Execution Plan

### 12.1 执行顺序

```
Phase 1: 验证 Phase 20 Regression
  → pytest backend/tests/test_phase20_regression.py -v
  
Phase 2: 实现 Gate 1-2（Evidence role）
  → pytest backend/tests/test_evidence_role_regression.py -v
  
Phase 3: 实现 Gate 3（Context Window）
  → pytest backend/tests/test_context_window_regression.py -v
  
Phase 4: 实现 Gate 4-5（User Fact Boundary + Reconstruction）
  → pytest backend/tests/test_short_confirmation_regression.py -v
  → pytest backend/tests/test_rejection_correction_regression.py -v
  → pytest backend/tests/test_ai_pollution_protection.py -v
  → pytest backend/tests/test_reconstruction_lineage.py -v
  
Phase 5: 实现 Gate 6-7（Proposal Lineage + Topic）
  → pytest backend/tests/test_proposal_lineage.py -v
  → pytest backend/tests/test_topic_regression.py -v
  
Phase 6: E2E 验证
  → pytest backend/tests/test_e2e_scenarios.py -v
  
Phase 7: 全量 Regression
  → pytest backend/tests/ -v
```

### 12.2 预期结果

| 阶段 | 预期通过率 |
|------|-----------|
| Phase 1 (Phase 20) | 100% (14/14) |
| Phase 2-7 (Phase 21) | 0% (全部 NOT IMPLEMENTED) |

---

## 13. Deferred Tests

以下测试明确留给后续阶段：

| 测试 | 延迟原因 | 目标阶段 |
|------|----------|----------|
| Long Evidence Chunking (LE-002) | 依赖分块算法 | Stage 3+ |
| Context Budget Tuning (CB-002) | 性能调优 | Stage 3+ |
| Topic Algorithm (T-005+) | 算法未设计 | Stage 3+ |
| Ambiguity Resolution | 非核心功能 | Deferred |
| Historical Memory Evolution | Stage 4 |

---

## 14. Summary

### 14.1 测试数量统计

| 优先级 | 数量 |
|--------|------|
| P0 | 30 |
| P1 | 20 |
| P2 | 5 |
| **总计** | **55** |

### 14.2 与现有测试关系

- **新增文件**: 9 个新测试文件
- **Phase 20 保留**: 14 个核心测试需验证
- **总测试文件**: 16 (现有) + 9 (新增) = 25 个

### 14.3 关键发现

1. **Phase 20 没有专门的 Regression Test 文件** — 需新建
2. **Evidence 缺少 role 字段** — P0 Gap，阻塞 Context Window
3. **导入逻辑过滤 AI Evidence** — P0 Gap，阻塞 User Fact Boundary
4. **2,616 条历史 Proposal 的 candidate_id = NULL** — 现有 Gap，需明确是否修复

---

*本报告为只读调查，不修改任何代码、测试、数据库、Schema 或设计文档。*

---

**STOP** — 不编码、不提交 Git，等待下一步指示。
