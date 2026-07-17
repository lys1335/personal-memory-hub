"""Unit tests for Domain Engine Layer (D4).

Tests EngineBase, EntityEngine, MemoryEngine, RelationshipEngine,
ReflectionEngine, SearchEngine, and ProjectionEngine.

Per D4.3 Engine Testing Architecture:
- Invariant-First: tests verify domain invariants, not implementation details
- Black-Box: Engine tested via public contract only
- Stateless Verification: same input → same Domain Result (deterministic)
- Domain Error Classification: errors classified per D3.7 Error Taxonomy
- No Cross-Engine Tests: Engine tests verify Engine in isolation
- Tests mock Repository — no real database, no Service involvement

Test Categories:
- Domain Rule Tests: business rules applied correctly
- Invariant Tests: domain invariants preserved
- Algorithm Tests: domain algorithms produce correct results
- Error Classification Tests: errors classified per Taxonomy
- Statelessness Tests: deterministic behavior
- Boundary Tests: Engine-Repository boundary respected
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest

# Ensure src/ is on the Python path
_src = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_src))

from backend.engine.base import (
    DomainInvariantViolation,
    DomainResult,
    EngineBase,
)
from backend.engine.entity_engine import EntityEngine
from backend.engine.memory_engine import MemoryEngine
from backend.engine.projection_engine import ProjectionEngine
from backend.engine.reflection_engine import ReflectionEngine
from backend.engine.relationship_engine import RelationshipEngine
from backend.engine.search_engine import SearchEngine

# ---------------------------------------------------------------------------
# Helper: sample domain model dicts (inline to avoid fixture resolution issues)
# ---------------------------------------------------------------------------


def _make_entity(**overrides):
    """Create a sample entity dict with optional overrides."""
    base = {
        "id": str(uuid4()),
        "entity_type": "Project",
        "canonical_name": "Test Project",
        "aliases": ["TP", "test-project"],
        "description": "A test project",
        "metadata": {"key": "value"},
        "observation_count": 5,
        "pattern_count": 2,
        "belief_count": 1,
        "relationship_count": 3,
        "status": "active",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def _make_memory(**overrides):
    """Create a sample memory dict with optional overrides."""
    base = {
        "id": str(uuid4()),
        "level": 1,
        "node_type": "Observation",
        "content": "Test memory content",
        "summary": "A test summary",
        "confidence": 0.8,
        "importance": 0.5,
        "signal_strength": 0.7,
        "status": "active",
        "source": "user",
        "generated_by": "user",
        "evidence_links": ["ev-1", "ev-2"],
        "contradict_evidence": [],
        "metadata": {},
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def _make_relationship(**overrides):
    """Create a sample relationship dict with optional overrides."""
    base = {
        "id": str(uuid4()),
        "source_id": str(uuid4()),
        "target_id": str(uuid4()),
        "relationship_type": "depends_on",
        "strength": 0.8,
        "metadata": {},
    }
    base.update(overrides)
    return base


def _make_reflection(**overrides):
    """Create a sample reflection dict with optional overrides."""
    base = {
        "id": str(uuid4()),
        "scope": "workspace",
        "candidate_type": "pattern",
        "content": "Reflection content",
        "evidence_chain": ["ev-1", "ev-2"],
        "evidence_count": 2,
        "evidence_strength": 0.7,
        "status": "candidate",
    }
    base.update(overrides)
    return base


def _make_domain_object(**overrides):
    """Create a sample domain object dict with optional overrides."""
    base = {
        "id": str(uuid4()),
        "type": "Observation",
        "content": "Test content for projection",
        "level": 1,
        "confidence": 0.8,
        "importance": 0.5,
        "signal_strength": 0.7,
        "status": "active",
        "source": "user",
        "metadata": {"key": "value"},
        "evidence_links": ["ev-1"],
        "created_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests — EngineBase
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_engine_base_name():
    """Verify EngineBase stores its name."""
    engine = EngineBase("TestEngine")
    assert engine.name == "TestEngine"


@pytest.mark.unit
def test_engine_domain_result_ok():
    """Verify DomainResult.ok() creates success result."""
    result = DomainResult.ok({"data": "test"})
    assert result.success is True
    assert result.data == {"data": "test"}
    assert result.is_ok() is True
    assert result.is_fail() is False


@pytest.mark.unit
def test_engine_domain_result_fail():
    """Verify DomainResult.fail() creates failure result."""
    error = DomainInvariantViolation("Invariant violated", invariant="test")
    result = DomainResult.fail(error)
    assert result.success is False
    assert result.error is error
    assert result.is_fail() is True
    assert result.is_ok() is False


@pytest.mark.unit
def test_engine_domain_result_unwrap():
    """Verify DomainResult.unwrap() returns data or raises."""
    ok_result = DomainResult.ok("test_data")
    assert ok_result.unwrap() == "test_data"

    fail_result = DomainResult.fail(DomainInvariantViolation("fail", invariant="x"))
    with pytest.raises(DomainInvariantViolation):
        fail_result.unwrap()


@pytest.mark.unit
def test_engine_domain_result_unwrap_or():
    """Verify DomainResult.unwrap_or() returns default on failure."""
    fail_result = DomainResult.fail(DomainInvariantViolation("fail", invariant="x"))
    assert fail_result.unwrap_or("default") == "default"


@pytest.mark.unit
def test_engine_verify_invariant_pass():
    """Verify EngineBase._verify_invariant() returns ok when passed."""
    engine = EngineBase("TestEngine")
    result = engine._verify_invariant(True, "test_invariant")
    assert result.success is True


@pytest.mark.unit
def test_engine_verify_invariant_fail():
    """Verify EngineBase._verify_invariant() returns fail when violated."""
    engine = EngineBase("TestEngine")
    result = engine._verify_invariant(False, "test_invariant")
    assert result.success is False
    assert isinstance(result.error, DomainInvariantViolation)
    assert result.error.invariant == "test_invariant"


# ---------------------------------------------------------------------------
# Tests — EntityEngine
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_entity_engine_evaluate_state():
    """Verify EntityEngine.evaluate_entity_state returns correct state."""
    engine = EntityEngine()
    entity = _make_entity()
    result = engine.evaluate_entity_state(entity=entity)

    assert result.success is True
    assert result.data["state"] == "active"
    assert result.data["is_active"] is True
    assert result.data["alias_count"] == 2


@pytest.mark.unit
def test_entity_engine_validate_valid():
    """Verify EntityEngine.validate_entity passes for valid entity."""
    engine = EntityEngine()
    result = engine.validate_entity(entity=_make_entity())
    assert result.success is True
    assert result.data is True


@pytest.mark.unit
def test_entity_engine_validate_invalid_type():
    """Verify EntityEngine.validate_entity rejects invalid entity type."""
    engine = EntityEngine()
    bad_entity = _make_entity(entity_type="InvalidType")
    result = engine.validate_entity(entity=bad_entity)
    assert result.success is False
    assert isinstance(result.error, DomainInvariantViolation)


@pytest.mark.unit
def test_entity_engine_validate_empty_canonical_name():
    """Verify EntityEngine.validate_entity rejects empty canonical_name."""
    engine = EntityEngine()
    bad_entity = _make_entity(canonical_name="")
    result = engine.validate_entity(entity=bad_entity)
    assert result.success is False


@pytest.mark.unit
def test_entity_engine_validate_alias_equals_canonical():
    """Verify EntityEngine.validate_entity rejects alias equal to canonical name."""
    engine = EntityEngine()
    bad_entity = _make_entity(aliases=["Test Project"])
    result = engine.validate_entity(entity=bad_entity)
    assert result.success is False


@pytest.mark.unit
def test_entity_engine_validate_empty_entity():
    """Verify EntityEngine.validate_entity fails for empty entity."""
    engine = EntityEngine()
    result = engine.validate_entity(entity={})
    assert result.success is False


@pytest.mark.unit
def test_entity_engine_verify_invariants():
    """Verify EntityEngine.verify_domain_invariants passes for valid entity."""
    engine = EntityEngine()
    result = engine.verify_domain_invariants(entity=_make_entity())
    assert result.success is True
    assert "identity_immutable" in result.data
    assert "single_canonical_identity" in result.data
    assert "valid_domain_state" in result.data


@pytest.mark.unit
def test_entity_engine_derive_information():
    """Verify EntityEngine.derive_domain_information returns correct data."""
    engine = EntityEngine()
    result = engine.derive_domain_information(entity=_make_entity())
    assert result.success is True
    assert result.data["derived_canonical_name"] == "Test Project"
    assert result.data["alias_resolution"]["alias_count"] == 2


@pytest.mark.unit
def test_entity_engine_resolve_identity():
    """Verify EntityEngine.resolve_identity returns resolved identity."""
    engine = EntityEngine()
    result = engine.resolve_identity(
        canonical_name="Test Project",
        entity_type="Project",
        workspace_id=uuid4(),
    )
    assert result.success is True
    assert result.data["resolved"] is True


@pytest.mark.unit
def test_entity_engine_resolve_empty_name():
    """Verify EntityEngine.resolve_identity rejects empty name."""
    engine = EntityEngine()
    result = engine.resolve_identity(
        canonical_name="",
        entity_type="Project",
        workspace_id=uuid4(),
    )
    assert result.success is False


@pytest.mark.unit
def test_entity_engine_evaluate_evolution():
    """Verify EntityEngine.evaluate_evolution_decision returns action."""
    engine = EntityEngine()
    result = engine.evaluate_evolution_decision(entity=_make_entity())
    assert result.success is True
    assert "action" in result.data
    assert "reason" in result.data
    assert "confidence" in result.data


# ---------------------------------------------------------------------------
# Tests — MemoryEngine
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_memory_engine_evaluate_semantics():
    """Verify MemoryEngine.evaluate_memory_semantics returns correct scores."""
    engine = MemoryEngine()
    result = engine.evaluate_memory_semantics(memory=_make_memory())
    assert result.success is True
    assert "semantic_coherence" in result.data
    assert "evidence_strength" in result.data
    assert result.data["semantic_category"] == "observation"


@pytest.mark.unit
def test_memory_engine_validate_evidence_chain():
    """Verify MemoryEngine.validate_memory_evidence_chain passes with evidence."""
    engine = MemoryEngine()
    result = engine.validate_memory_evidence_chain(
        memory=_make_memory(),
        evidences=[{"content": "test evidence"}],
    )
    assert result.success is True
    assert result.data is True


@pytest.mark.unit
def test_memory_engine_validate_no_evidence():
    """Verify MemoryEngine rejects memory without evidence."""
    engine = MemoryEngine()
    no_evidence = _make_memory(evidence_links=[])
    result = engine.validate_memory_evidence_chain(memory=no_evidence)
    assert result.success is False
    assert isinstance(result.error, DomainInvariantViolation)


@pytest.mark.unit
def test_memory_engine_evaluate_evolution_promote():
    """Verify MemoryEngine promotes Observation with sufficient evidence."""
    engine = MemoryEngine()
    strong_obs = _make_memory(
        level=1,
        evidence_links=["ev-1", "ev-2", "ev-3"],
        confidence=0.8,
    )
    result = engine.evaluate_evolution_action(memory=strong_obs)
    assert result.success is True
    assert result.data["action"] == "promote"
    assert result.data["target_level"] == 2


@pytest.mark.unit
def test_memory_engine_evaluate_evolution_no_action():
    """Verify MemoryEngine returns no action for weak observation."""
    engine = MemoryEngine()
    weak_obs = _make_memory(
        level=1,
        evidence_links=["ev-1"],
        confidence=0.3,
    )
    result = engine.evaluate_evolution_action(memory=weak_obs)
    assert result.success is True
    assert result.data["action"] == "none"


@pytest.mark.unit
def test_memory_engine_verify_invariants():
    """Verify MemoryEngine.verify_invariants passes for valid memory."""
    engine = MemoryEngine()
    result = engine.verify_invariants(memory=_make_memory())
    assert result.success is True
    assert "every_memory_has_evidence" in result.data
    assert "semantic_consistency" in result.data
    assert "traceability_preserved" in result.data


@pytest.mark.unit
def test_memory_engine_assess_archive_eligible():
    """Verify MemoryEngine flags high-importance Belief as archive-eligible."""
    engine = MemoryEngine()
    high_belief = _make_memory(
        level=3,
        node_type="Belief",
        importance=0.85,
    )
    result = engine.assess_archive_eligibility(memory=high_belief)
    assert result.success is True
    assert result.data["eligible"] is True
    assert result.data["priority"] == "high"


@pytest.mark.unit
def test_memory_engine_derive_projection():
    """Verify MemoryEngine.derive_projection_data returns projection."""
    engine = MemoryEngine()
    result = engine.derive_projection_data(memory=_make_memory())
    assert result.success is True
    assert result.data["content"] == "Test memory content"
    assert result.data["evidence_count"] == 2


# ---------------------------------------------------------------------------
# Tests — RelationshipEngine
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_relationship_engine_validate_valid():
    """Verify RelationshipEngine validates a valid relationship."""
    engine = RelationshipEngine()
    result = engine.validate_relationship(relationship=_make_relationship())
    assert result.success is True
    assert result.data is True


@pytest.mark.unit
def test_relationship_engine_validate_self_relationship():
    """Verify RelationshipEngine rejects self-relationship."""
    engine = RelationshipEngine()
    self_rel = _make_relationship(
        source_id="same-id",
        target_id="same-id",
    )
    result = engine.validate_relationship(relationship=self_rel)
    assert result.success is False
    assert isinstance(result.error, DomainInvariantViolation)


@pytest.mark.unit
def test_relationship_engine_validate_invalid_type():
    """Verify RelationshipEngine rejects invalid relationship type."""
    engine = RelationshipEngine()
    bad_rel = _make_relationship(relationship_type="invalid_type")
    result = engine.validate_relationship(relationship=bad_rel)
    assert result.success is False


@pytest.mark.unit
def test_relationship_engine_validate_invalid_strength():
    """Verify RelationshipEngine rejects out-of-range strength."""
    engine = RelationshipEngine()
    bad_rel = _make_relationship(strength=1.5)
    result = engine.validate_relationship(relationship=bad_rel)
    assert result.success is False


@pytest.mark.unit
def test_relationship_engine_evaluate_semantics():
    """Verify RelationshipEngine evaluates relationship semantics."""
    engine = RelationshipEngine()
    result = engine.evaluate_relationship_semantics(
        relationship=_make_relationship()
    )
    assert result.success is True
    assert result.data["semantic_category"] == "dependency"


@pytest.mark.unit
def test_relationship_engine_normalize_inverse():
    """Verify RelationshipEngine normalizes inverse relationships."""
    engine = RelationshipEngine()
    belongs_to = _make_relationship(
        source_id="a",
        target_id="b",
        relationship_type="belongs_to",
    )
    result = engine.normalize_relationship(relationship=belongs_to)
    assert result.success is True
    assert result.data["normalized"] is True
    assert result.data["relationship_type"] == "part_of"


@pytest.mark.unit
def test_relationship_engine_assess_lifecycle_active():
    """Verify RelationshipEngine assesses active relationship."""
    engine = RelationshipEngine()
    result = engine.assess_lifecycle(relationship=_make_relationship())
    assert result.success is True
    assert result.data["active"] is True


@pytest.mark.unit
def test_relationship_engine_assess_lifecycle_deactivated():
    """Verify RelationshipEngine assesses deactivated relationship."""
    engine = RelationshipEngine()
    deactivated = _make_relationship(
        metadata={"deactivated_at": "2026-01-02T00:00:00Z"},
    )
    result = engine.assess_lifecycle(relationship=deactivated)
    assert result.success is True
    assert result.data["active"] is False


@pytest.mark.unit
def test_relationship_engine_check_compatible():
    """Verify RelationshipEngine checks endpoint compatibility."""
    engine = RelationshipEngine()
    result = engine.check_endpoint_compatibility(
        source_entity_type="Person",
        target_entity_type="Project",
        relationship_type="created_by",
    )
    assert result.success is True
    assert result.data is True


# ---------------------------------------------------------------------------
# Tests — ReflectionEngine
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_reflection_engine_validate_valid():
    """Verify ReflectionEngine validates a valid reflection."""
    engine = ReflectionEngine()
    result = engine.validate_reflection(reflection=_make_reflection())
    assert result.success is True
    assert result.data is True


@pytest.mark.unit
def test_reflection_engine_validate_no_evidence():
    """Verify ReflectionEngine rejects reflection without evidence."""
    engine = ReflectionEngine()
    no_evidence = _make_reflection(
        evidence_count=0,
        evidence_chain=[],
    )
    result = engine.validate_reflection(reflection=no_evidence)
    assert result.success is False


@pytest.mark.unit
def test_reflection_engine_evaluate_candidate_promotable():
    """Verify ReflectionEngine evaluates promotable candidate."""
    engine = ReflectionEngine()
    strong_candidate = _make_reflection(
        candidate_type="pattern",
        evidence_count=3,
        evidence_strength=0.8,
    )
    result = engine.evaluate_candidate(candidate=strong_candidate)
    assert result.success is True
    assert result.data["promotion_eligible"] is True


@pytest.mark.unit
def test_reflection_engine_evaluate_candidate_not_promotable():
    """Verify ReflectionEngine rejects non-promotable candidate."""
    engine = ReflectionEngine()
    weak_candidate = _make_reflection(
        candidate_type="pattern",
        evidence_count=1,
        evidence_strength=0.3,
    )
    result = engine.evaluate_candidate(candidate=weak_candidate)
    assert result.success is True
    assert result.data["promotion_eligible"] is False


@pytest.mark.unit
def test_reflection_engine_validate_evolution_monotonic():
    """Verify ReflectionEngine validates monotonic evolution."""
    engine = ReflectionEngine()
    valid_evolution = {
        "action": "promote",
        "source_level": 1,
        "target_level": 2,
        "evidence_chain": ["ev-1"],
        "justification": "Strong evidence",
    }
    result = engine.validate_evolution(evolution_action=valid_evolution)
    assert result.success is True


@pytest.mark.unit
def test_reflection_engine_validate_evolution_non_monotonic():
    """Verify ReflectionEngine rejects non-monotonic evolution."""
    engine = ReflectionEngine()
    bad_evolution = {
        "action": "demote",
        "source_level": 3,
        "target_level": 1,
        "evidence_chain": ["ev-1"],
        "justification": "Weak evidence",
    }
    result = engine.validate_evolution(evolution_action=bad_evolution)
    assert result.success is False


@pytest.mark.unit
def test_reflection_engine_assess_consolidation():
    """Verify ReflectionEngine assesses consolidation feasibility."""
    engine = ReflectionEngine()
    memories = [
        {"evidence_links": ["ev-1", "ev-2"], "content": "Memory 1"},
        {"evidence_links": ["ev-2", "ev-3"], "content": "Memory 2"},
    ]
    result = engine.assess_consolidation_feasibility(memories=memories)
    assert result.success is True
    assert "feasible" in result.data
    assert "overlap_score" in result.data


# ---------------------------------------------------------------------------
# Tests — SearchEngine
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_search_engine_interpret_intent():
    """Verify SearchEngine.interpret_intent parses query correctly."""
    engine = SearchEngine()
    result = engine.interpret_intent(query={
        "text": "test query",
        "scope": "workspace",
        "filters": {},
        "ranking_preference": "relevance",
    })
    assert result.success is True
    assert result.data["scope"] == "workspace"
    assert result.data["has_text_query"] is True


@pytest.mark.unit
def test_search_engine_interpret_empty():
    """Verify SearchEngine.interpret_intent rejects empty query."""
    engine = SearchEngine()
    result = engine.interpret_intent(query={})
    assert result.success is False


@pytest.mark.unit
def test_search_engine_plan_discovery():
    """Verify SearchEngine.plan_discovery creates valid plan."""
    engine = SearchEngine()
    result = engine.plan_discovery(
        query={"text": "test", "scope": "workspace"},
        scope={"workspace_id": str(uuid4())},
    )
    assert result.success is True
    assert "strategy" in result.data
    assert "validation_criteria" in result.data


@pytest.mark.unit
def test_search_engine_discover_candidates():
    """Verify SearchEngine.discover_candidates filters correctly."""
    engine = SearchEngine()
    plan = {"candidate_types": ["Observation"]}
    items = [
        {"node_type": "Observation", "evidence_links": ["ev-1"], "confidence": 0.5},
        {"node_type": "Pattern", "evidence_links": ["ev-1"], "confidence": 0.5},
    ]
    result = engine.discover_candidates(plan=plan, available_items=items)
    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0]["node_type"] == "Observation"


@pytest.mark.unit
def test_search_engine_validate_candidate():
    """Verify SearchEngine.validate_candidate validates correctly."""
    engine = SearchEngine()
    candidate = {
        "content": "test content",
        "level": 1,
        "evidence_links": ["ev-1"],
    }
    result = engine.validate_candidate(candidate=candidate)
    assert result.success is True


@pytest.mark.unit
def test_search_engine_rank_candidates():
    """Verify SearchEngine.rank_candidates sorts by score."""
    engine = SearchEngine()
    candidates = [
        {"confidence": 0.9, "importance": 0.8, "signal_strength": 0.7},
        {"confidence": 0.3, "importance": 0.2, "signal_strength": 0.1},
    ]
    result = engine.rank_candidates(
        candidates=candidates,
        ranking_approach="relevance",
    )
    assert result.success is True
    assert len(result.data) == 2
    assert result.data[0]["_ranking_score"] >= result.data[1]["_ranking_score"]


# ---------------------------------------------------------------------------
# Tests — ProjectionEngine
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_projection_engine_produce_summary():
    """Verify ProjectionEngine produces summary projection."""
    engine = ProjectionEngine()
    policy = {"type": "summary", "max_items": 10, "include_metadata": True}
    result = engine.produce_projection(
        domain_objects=[_make_domain_object()],
        policy=policy,
    )
    assert result.success is True
    assert len(result.data) == 1
    assert "content" in result.data[0]


@pytest.mark.unit
def test_projection_engine_produce_detail():
    """Verify ProjectionEngine produces detail projection."""
    engine = ProjectionEngine()
    policy = {"type": "detail", "max_items": 10, "include_metadata": True}
    result = engine.produce_projection(
        domain_objects=[_make_domain_object()],
        policy=policy,
    )
    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0]["content"] == "Test content for projection"


@pytest.mark.unit
def test_projection_engine_enforce_semantics_valid():
    """Verify ProjectionEngine.enforce_semantics passes valid projection."""
    engine = ProjectionEngine()
    projection = {
        "id": "test-id",
        "type": "Observation",
        "content": "Test content",
        "original_content": "Test content",
    }
    result = engine.enforce_semantics(projection=projection)
    assert result.success is True


@pytest.mark.unit
def test_projection_engine_enforce_semantics_inferred():
    """Verify ProjectionEngine.enforce_semantics rejects inferred fields."""
    engine = ProjectionEngine()
    projection = {
        "id": "test-id",
        "content": "Test",
        "_inferred_knowledge": "should not be here",
    }
    result = engine.enforce_semantics(projection=projection)
    assert result.success is False


@pytest.mark.unit
def test_projection_engine_normalize_structure():
    """Verify ProjectionEngine.normalize_structure returns canonical form."""
    engine = ProjectionEngine()
    projection = {
        "id": "test-id",
        "type": "Observation",
        "content": "Test",
        "extra_field": "should be removed",
    }
    result = engine.normalize_structure(projection=projection)
    assert result.success is True
    assert "extra_field" not in result.data
    assert "id" in result.data


@pytest.mark.unit
def test_projection_engine_verify_determinism():
    """Verify ProjectionEngine.verify_determinism returns True."""
    engine = ProjectionEngine()
    policy = {"type": "summary", "max_items": 10}
    result = engine.verify_determinism(
        input_objects=[_make_domain_object()],
        policy=policy,
    )
    assert result.success is True
    assert result.data is True


@pytest.mark.unit
def test_projection_engine_verify_invariants():
    """Verify ProjectionEngine.verify_invariants passes for valid projection."""
    engine = ProjectionEngine()
    result = engine.verify_invariants(
        projection={"id": "test", "content": "test", "level": 1}
    )
    assert result.success is True
    assert "projection_preservation" in result.data


@pytest.mark.unit
def test_projection_engine_empty_input():
    """Verify ProjectionEngine handles empty input gracefully."""
    engine = ProjectionEngine()
    policy = {"type": "summary"}
    result = engine.produce_projection(domain_objects=[], policy=policy)
    assert result.success is True
    assert result.data == []


# ---------------------------------------------------------------------------
# Tests — Engine Layer Boundary
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_engine_no_service_imports():
    """Verify Engine modules don't import from service layer."""
    import backend.engine.base
    import backend.engine.entity_engine
    import backend.engine.memory_engine
    import backend.engine.projection_engine
    import backend.engine.reflection_engine
    import backend.engine.relationship_engine
    import backend.engine.search_engine

    for mod in (
        backend.engine.base,
        backend.engine.entity_engine,
        backend.engine.memory_engine,
        backend.engine.relationship_engine,
        backend.engine.reflection_engine,
        backend.engine.search_engine,
        backend.engine.projection_engine,
    ):
        for name in dir(mod):
            obj = getattr(mod, name, None)
            if obj and hasattr(obj, "__module__"):
                assert not obj.__module__.startswith("backend.service"), \
                    f"{obj.__module__}.{name} imports from service layer"


@pytest.mark.unit
def test_engine_no_other_engine_imports():
    """Verify Engine modules don't import from other Engine modules."""
    import backend.engine.entity_engine
    import backend.engine.memory_engine
    import backend.engine.projection_engine
    import backend.engine.reflection_engine
    import backend.engine.relationship_engine
    import backend.engine.search_engine

    engine_modules = {
        "EntityEngine", "MemoryEngine", "RelationshipEngine",
        "ReflectionEngine", "SearchEngine", "ProjectionEngine",
    }

    for mod in (
        backend.engine.entity_engine,
        backend.engine.memory_engine,
        backend.engine.relationship_engine,
        backend.engine.reflection_engine,
        backend.engine.search_engine,
        backend.engine.projection_engine,
    ):
        for name in dir(mod):
            obj = getattr(mod, name, None)
            if obj and hasattr(obj, "__module__"):
                for other in engine_modules:
                    assert other not in obj.__module__, \
                        f"{obj.__module__} imports from {other}"
