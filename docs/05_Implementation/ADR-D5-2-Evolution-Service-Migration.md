# ADR-D5-2: Evolution Service Migration

## Status
Accepted

## Context
Phase 21.7 (`evolution/` package) was frozen per `phase21-final-freeze-audit.md`. D5-1 investigation (2026-09-04) revealed structural issues requiring controlled refactoring.

## Decision
Perform **controlled structural refactoring only** (not business logic changes):

1. **Move `EvolutionService`** → `backend/src/backend/service/evolution_service.py`
   - Inherits `BaseService` ✓ (proper service contract)
   - Content unchanged: methods, signatures, docstrings preserved
   - Import adjusted: `evolution.evolution_result` → `shared.domain.evolution_result`

2. **Move `EvolutionResult` / `TopicEvolutionResult`** → `backend/src/backend/shared/domain/evolution_result.py`
   - Pure dataclasses, no import changes needed
   - Two `EvolutionResult` classes coexist:
     - `engine/evidence_evolution_engine.py:30` (EvidenceEvolutionEngine internal) — **untouched**
     - `shared/domain/evolution_result.py:41` (Historical Evolution) — **migrated**

3. **Delete `EvolutionEngine`** (dead code)
   - Does not inherit `EngineBase` — violates engine contract
   - D5-1 found no runtime references (tests import it but don't use it at runtime)
   - Duplicate of `EvolutionService` (11 methods nearly identical)

4. **`TopicEvolutionService`** follows `EvolutionEngine` deletion (defined inside `evolution_engine.py:449`)

5. **`VALID_TRANSITIONS`** naturally consolidated: only one copy remains in `service/evolution_service.py:49`

## Consequences
- `evolution/` package removed from repository
- Import paths updated in:
  - `app.py:198` → `backend.service.evolution_service`
  - `evidence_pipeline_service.py:27` → `backend.service.evolution_service`
  - `test_evolution_regression.py:18-23` → minimal import adaptation
  - `test_pipeline_integration.py:304,363,398,516` → minimal import adaptation
- Phase 21.7 frozen status: **structural refactoring allowed, business semantics unchanged**
- Tests import updated but test logic/assertions unchanged
- No alembic migration needed (no schema change)
- No DI container changes

## Blocked
- pytest execution blocked: venv lacks pytest module (per user裁决 (b), not auto-fixed)
- D5-3 (MemoryHubError migration) — **HOLD** pending separate authorization
- D5-4 (shared extractor) — **not included**

## References
- D5-1 Investigation Report: `.hermes/plans/d5-1-investigation-report.md`
- D5-2 Task Definition v2: `.hermes/plans/d5-2-task-definition.md`
- Phase 21 Freeze Audit: `docs/phase21-post-freeze-root-cause-verification.md`

## 最终 LOCK 确认

**LOCK 日期**: 2026-09-04
**LOCK 状态**: ✅ PASS / LOCKED
**测试结果**: 703 passed / 8 skipped / 0 failed / 0 errors（pytest 711 collected）
**Phase 21.7 状态**: 恢复 FROZEN ✅
**未 commit / 未 push**
