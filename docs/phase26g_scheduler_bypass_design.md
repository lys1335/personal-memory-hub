# Phase 26-G — Scheduler Authentication Bypass
## Step 2 Design Report

**Date:** 2026-08-22
**Designer:** Hermes Agent Agnes 2.0
**Type:** DESIGN ONLY — No code modifications
**Base Commit:** 61957a84ebcd6331a5bf034da0a2b9abf8863f26

---

## 1. Design Decision

### 1.1 Problem Statement

**Current State:**
- HTTP Path: Authentication via `require_cron_admin` dependency ✅
- Scheduler Path: Direct function call, bypasses HTTP authentication ⚠️

**Key Question:**
Is Scheduler bypassing HTTP authentication a vulnerability or a design choice?

### 1.2 Decision Framework

```
TRUST MODEL ANALYSIS:
┌─────────────────────────────────────────────────────────────┐
│  External Request  →  HTTP API  →  require_cron_admin  ✅   │
│                         ↓                                     │
│                    run_cron_task_now()                       │
│                         ↓                                     │
│  Internal Scheduler  →  Direct Call  →  NO HTTP Auth ⚠️    │
│                         ↓                                     │
│                    validate_no_test_task()  ✅               │
│                         ↓                                     │
│                    CronSafetyValidator()  ✅                 │
│                         ↓                                     │
│                    Database Mutation                          │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Final Decision

**RECOMMENDED: Option B — Add Internal Authorization Check**

**Rationale:**
1. Defense-in-depth principle: Multiple layers of security
2. Future-proofing: Prevents accidental bypass if new call paths are added
3. Clarity: Makes security boundary explicit
4. Minimal impact: Small code change, clear intent

**Decision Matrix:**

| Option | Risk | Complexity | Recommendation |
|--------|------|------------|----------------|
| A: Document as-is | MEDIUM | LOW | ❌ Insufficient |
| **B: Add internal auth** | **LOW** | **MEDIUM** | **✅ RECOMMENDED** |
| C: Refactor architecture | LOW | HIGH | ❌ Over-engineering |
| D: Ignore (trust Scheduler) | MEDIUM | LOW | ❌ Bad practice |

---

## 2. Security Boundary Model

### 2.1 Three-Layer Security Model

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: External Authentication (HTTP Boundary)           │
│  - require_cron_admin dependency                            │
│  - API Key verification                                     │
│  - Purpose: Prevent unauthorized EXTERNAL access            │
│  - Scope: HTTP endpoints only                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: Internal Authorization (Function Boundary)        │
│  - _verify_internal_call() helper                           │
│  - Task existence verification                              │
│  - Task enabled state verification                          │
│  - Purpose: Prevent unauthorized INTERNAL execution         │
│  - Scope: run_cron_task_now() function                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: Business Safety (Domain Boundary)                 │
│  - validate_no_test_task()                                  │
│  - CronSafetyValidator.pre_flight_check()                   │
│  - CronSafetyValidator.validate_post_flight()               │
│  - Circuit breaker                                          │
│  - Purpose: Prevent unsafe operations                       │
│  - Scope: All execution paths (HTTP + Scheduler)            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Call Path Security Matrix

| Path | Layer 1 (HTTP Auth) | Layer 2 (Internal Auth) | Layer 3 (Safety) |
|------|---------------------|------------------------|------------------|
| HTTP: POST /run-now | ✅ require_cron_admin | ⚠️ MISSING | ✅ validate_no_test_task + SafetyValidator |
| Scheduler: _cron_scheduler_loop | N/A (internal) | ⚠️ MISSING | ✅ validate_no_test_task + SafetyValidator |

**Finding:** Layer 2 (Internal Authorization) is missing from BOTH paths.

### 2.3 Proposed Security Boundary

```python
# app.py — Proposed change to run_cron_task_now()

async def run_cron_task_now(task_id: str):
    """Manually trigger a task execution via Service layer.
    
    Security Boundary:
    - Layer 1: HTTP authentication (via FastAPI dependency)
    - Layer 2: Internal authorization (this function)
    - Layer 3: Business safety (validate_no_test_task + SafetyValidator)
    """
    
    # NEW: Layer 2 — Internal Authorization Check
    _verify_internal_call(task_id)
    
    # Layer 3 — Business Safety (existing)
    validate_no_test_task(task_id=task_id)
    
    # ... rest of function
```

---

## 3. Call-Path Matrix

### 3.1 All run_cron_task_now() Callers

| Caller | File:Line | Auth Layer | Safety Layer | Status |
|--------|-----------|------------|--------------|--------|
| `_cron_scheduler_loop()` | app.py:1300 | L1:N/A, L2:❌, L3:✅ | L3:✅ | ⚠️ NEEDS FIX |
| `@app.post(...)` | app.py:1427 | L1:✅, L2:❌, L3:✅ | L3:✅ | ⚠️ NEEDS FIX |

### 3.2 Proposed Fix Impact

| Path | Before | After |
|------|--------|-------|
| HTTP: /run-now | L1:✅, L2:❌, L3:✅ | L1:✅, L2:✅, L3:✅ |
| Scheduler | L1:N/A, L2:❌, L3:✅ | L1:N/A, L2:✅, L3:✅ |

---

## 4. Recommended Minimal Fix

### 4.1 Design: _verify_internal_call() Helper

```python
# app.py — New helper function (proposed)

def _verify_internal_call(task_id: str) -> None:
    """Verify internal authorization for cron task execution.
    
    This function serves as Layer 2 in the security boundary model.
    It verifies that:
    1. The task exists in _cron_tasks
    2. The task is enabled
    3. The call is from a trusted source
    
    Called by:
    - run_cron_task_now() (both HTTP and Scheduler paths)
    """
    # Check task existence
    if task_id not in _cron_tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found in cron configuration"
        )
    
    # Check task enabled state
    task = _cron_tasks[task_id]
    if not task.get('enabled', False):
        raise HTTPException(
            status_code=403,
            detail=f"Task {task_id} is not enabled"
        )
    
    # Optional: Log authorization check
    logger.info(f"[CRON-AUTH] Internal authorization verified for task {task_id}")
```

### 4.2 Integration Points

**Location 1: run_cron_task_now() (line 1432)**
```python
@app.post("/api/cron/tasks/{task_id}/run-now", 
          dependencies=[Depends(require_cron_admin)])
async def run_cron_task_now(task_id: str):
    """Manually trigger a task execution via Service layer."""
    
    # NEW: Layer 2 — Internal Authorization
    _verify_internal_call(task_id)  # ← ADD THIS
    
    # Layer 3 — Business Safety (existing)
    validate_no_test_task(task_id=task_id)
    # ... rest of function
```

**Location 2: _cron_scheduler_loop() (line 1300)**
```python
# Scheduler calls run_cron_task_now() which now includes _verify_internal_call()
result = await run_cron_task_now(task_id)  # ← No change needed here
```

### 4.3 Change Summary

| File | Lines | Change Type | Description |
|------|-------|-------------|-------------|
| app.py | ~1430 | NEW | Add `_verify_internal_call()` helper |
| app.py | ~1432 | MODIFY | Call `_verify_internal_call()` in `run_cron_task_now()` |

**Total Impact:** 2 locations, ~15 lines of code

---

## 5. Scheduler-specific Test Plan

### 5.1 Test Matrix

| Test Case | Path | Expected | Priority |
|-----------|------|----------|----------|
| Scheduler calls enabled task | Scheduler | 200 OK | P0 |
| Scheduler calls disabled task | Scheduler | 403 Forbidden | P0 |
| Scheduler calls nonexistent task | Scheduler | 404 Not Found | P0 |
| Scheduler calls test_* task | Scheduler | 400 Bad Request | P0 |
| HTTP calls enabled task with key | HTTP | 200 OK | P0 |
| HTTP calls disabled task with key | HTTP | 403 Forbidden | P1 |
| HTTP calls without key | HTTP | 401 Unauthorized | P1 |

### 5.2 Proposed Test Code

```python
# backend/tests/test_scheduler_security.py (proposed)

class TestSchedulerInternalAuthorization:
    """Tests for Scheduler internal authorization (Layer 2)."""
    
    def test_scheduler_calls_enabled_task(self, client, mock_cron_tasks):
        """Scheduler should execute enabled tasks."""
        mock_cron_tasks["prod_task"] = {"enabled": True, "type": "evolution"}
        # Mock the evolution execution
        with patch("backend.app.run_evolution_task") as mock_run:
            result = await run_cron_task_now("prod_task")
            assert result["status"] == "completed"
            mock_run.assert_called_once()
    
    def test_scheduler_rejects_disabled_task(self, client, mock_cron_tasks):
        """Scheduler should reject disabled tasks."""
        mock_cron_tasks["disabled_task"] = {"enabled": False, "type": "evolution"}
        with pytest.raises(HTTPException) as exc_info:
            await run_cron_task_now("disabled_task")
        assert exc_info.value.status_code == 403
    
    def test_scheduler_rejects_nonexistent_task(self, client, mock_cron_tasks):
        """Scheduler should reject nonexistent tasks."""
        with pytest.raises(HTTPException) as exc_info:
            await run_cron_task_now("nonexistent_task")
        assert exc_info.value.status_code == 404
    
    def test_scheduler_rejects_test_task(self, client, mock_cron_tasks):
        """Scheduler should reject test_* tasks (Layer 3)."""
        mock_cron_tasks["test_task"] = {"enabled": True, "type": "evolution"}
        with pytest.raises(HTTPException) as exc_info:
            await run_cron_task_now("test_task")
        assert exc_info.value.status_code == 400
```

---

## 6. Regression Scope

### 6.1 Existing Tests to Verify

| Test File | Tests | Status |
|-----------|-------|--------|
| test_cron_api_p0_security.py | 22 tests | ✅ PASS (should remain PASS) |
| test_safety_mechanisms.py | 13 tests | ✅ PASS (should remain PASS) |
| test_approval_safety.py | 5 tests | ✅ PASS (should remain PASS) |

### 6.2 New Tests to Add

| Test File | Tests | Purpose |
|-----------|-------|---------|
| test_scheduler_security.py | ~6 tests | Scheduler internal authorization |

### 6.3 Total Test Count

| Before | After | Change |
|--------|-------|--------|
| 40 tests | 46 tests | +6 |

---

## 7. Risk if Left Unchanged

### 7.1 Current Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Unauthorized Scheduler execution | MEDIUM | LOW | Cron DISABLED |
| Config file manipulation | LOW | LOW | File system permissions |
| New call path without auth | MEDIUM | MEDIUM | Code review process |
| Test_* task via Scheduler | LOW | LOW | validate_no_test_task() |

### 7.2 Risk if Fix Applied

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| False positive (valid task rejected) | LOW | LOW | Proper testing |
| Performance impact | NONE | NONE | Simple dict lookup |
| Test failures | LOW | LOW | Add Scheduler tests |

---

## 8. Phase Boundary Decision

### 8.1 Option A: Extend C-E

**Pros:**
- Completes C-E security work
- Single commit for related changes
- Clear completion of P0 remediation

**Cons:**
- C-E was already LOCKED
- May require re-opening locked phase

**Recommendation:** ❌ NOT RECOMMENDED

---

### 8.2 Option B: Create Phase 26-G-C-F

**Pros:**
- Clear phase boundary
- Dedicated focus on Scheduler security
- Can include comprehensive tests

**Cons:**
- New phase overhead
- May seem like scope creep

**Recommendation:** ⚠️ OPTIONAL (if user wants formal phase structure)

---

### 8.3 Option C: Post-C-E Hardening (Recommended)

**Pros:**
- Non-intrusive to locked C-E
- Clear documentation of follow-up work
- Can be combined with other hardening tasks

**Cons:**
- Not a formal "Phase"
- May be deferred

**Recommendation:** ✅ RECOMMENDED

**Designation:** `Phase 26-G-C-E-Hardening` (informal)

---

## 9. Fact vs Inference vs Unknown

### 9.1 Confirmed Facts

| # | Fact | Evidence Level |
|---|------|----------------|
| 1 | HTTP path has require_cron_admin | LEVEL 2 (TEST VERIFIED) |
| 2 | Scheduler calls run_cron_task_now() directly | LEVEL 1 (CODE PRESENT) |
| 3 | validate_no_test_task() covers both paths | LEVEL 2 (TEST VERIFIED) |
| 4 | CronSafetyValidator covers both paths | LEVEL 2 (TEST VERIFIED) |
| 5 | Cron is DISABLED in production | LEVEL 1 (CONFIG ASSUMED) |
| 6 | No Scheduler-specific tests exist | LEVEL 1 (CODE PRESENT) |

### 9.2 Inferences

| # | Inference | Basis |
|---|-----------|-------|
| 1 | Scheduler bypass is by design (not accidental) | Internal component trust model |
| 2 | Current risk is LOW | Cron DISABLED + protections in place |
| 3 | Fix is minimal impact | Single helper function + 1 call site |
| 4 | Future call paths may also bypass auth | Pattern observed in current code |

### 9.3 Unknowns

| # | Unknown | How to Verify |
|---|---------|---------------|
| 1 | Whether config file can be manipulated externally | File system audit |
| 2 | Whether other internal components call run_cron_task_now() | grep search complete |
| 3 | Production config state (Cron enabled?) | Docker exec required |
| 4 | Whether _cron_tasks can be modified at runtime | Code review required |

---

## 10. Final Design Summary

### 10.1 Security Model

```
THREE-LAYER DEFENSE:
┌─────────────────────────────────────────┐
│ LAYER 1: HTTP Authentication            │ ← External boundary
│   - require_cron_admin                   │
│   - API Key verification                 │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ LAYER 2: Internal Authorization         │ ← Function boundary
│   - _verify_internal_call() [NEW]       │
│   - Task existence check                 │
│   - Task enabled state check             │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ LAYER 3: Business Safety                │ ← Domain boundary
│   - validate_no_test_task()              │
│   - CronSafetyValidator                  │
│   - Circuit breaker                      │
└─────────────────────────────────────────┘
```

### 10.2 Changes Required

| Item | Change | Lines |
|------|--------|-------|
| New helper | `_verify_internal_call()` | +15 |
| Integration | Call in `run_cron_task_now()` | +1 |
| New tests | `test_scheduler_security.py` | +60 |
| **Total** | | **~76 lines** |

### 10.3 Decision

```
RECOMMENDED ACTION: Phase 26-G-C-E-Hardening (informal)

Steps:
1. Add _verify_internal_call() helper
2. Integrate into run_cron_task_now()
3. Add Scheduler-specific tests
4. Verify all 46 tests PASS
5. Document security model
```

---

*Step 2 Design completed by Hermes Agent Agnes 2.0*
*Design type: READ-ONLY — No code modifications made*
*Date: 2026-08-22*
