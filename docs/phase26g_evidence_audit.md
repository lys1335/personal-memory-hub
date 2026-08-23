# Phase 26-G — Evidence-Level Audit

**Date:** 2026-08-22
**Auditor:** Hermes Agent Agnes 2.0
**Target:** docs/phase26g_final_review.md
**Audit Type:** Evidence-Level Verification (READ-ONLY)

---

## 1. Evidence-Level Definitions

| Level | Definition |
|-------|------------|
| **LEVEL 0** — CLAIM ONLY | 只有报告中的文字声明，无独立证据 |
| **LEVEL 1** — CODE PRESENT | 代码中存在对应实现，但无证据证明实际执行路径使用它 |
| **LEVEL 2** — TEST VERIFIED | 自动化测试证明该行为成立 |
| **LEVEL 3** — PRODUCTION PATH VERIFIED | 有证据证明真实生产 execution path 使用该机制 |

**重要区分：**
- CODE PRESENT ≠ TEST VERIFIED
- TEST VERIFIED ≠ PRODUCTION PATH VERIFIED
- PRODUCTION PATH VERIFIED ≠ LONG-TERM RUNTIME VERIFIED

---

## 2. Executive Finding

**Final Review 中存在多处证据等级不当升级。**

主要问题：
1. 将 LEVEL 1 (CODE PRESENT) 标记为 LEVEL 2 (TEST VERIFIED)
2. 将 LEVEL 2 标记为 LEVEL 3 (PRODUCTION PATH VERIFIED)
3. 未明确区分"测试通过"与"生产验证"
4. C-E incident 分析中存在推测性结论

**最终判定：**
- Phase 26-G 实现完整性：✅ PASS
- 测试完整性：✅ PASS
- 生产运行时验证：⚠️ **UNKNOWN** (Cron 保持 DISABLED)
- 最终结论：**IMPLEMENTATION COMPLETE BUT PRODUCTION RUNTIME = UNKNOWN**
---

## 3. Issue Evidence Matrix

| # | Issue | Final Review Claim | Evidence Available | Evidence Level | Claim Supported? |
|---|-------|-------------------|-------------------|----------------|------------------|
| 1 | Random UUID fallback | HISTORICAL ONLY | git log (UUIDv7 migration), code inspection | LEVEL 1 | ✅ YES |
| 2 | Stuck proposals | VERIFIED FIXED | phase-20-pending-proposal-purge-report.md | LEVEL 2 | ✅ YES |
| 3 | Invalid proposals | VERIFIED FIXED | phase-20-pending-proposal-purge-report.md | LEVEL 2 | ✅ YES |
| 4 | Evidence persistence | VERIFIED FIXED | Phase 21 docs, test_reconstruction_lineage.py | LEVEL 2 | ✅ YES |
| 5 | Cron safety | VERIFIED FIXED | safety_mechanisms.py, test_safety_mechanisms.py | LEVEL 2 | ⚠️ PARTIAL |
| 6 | SafetyValidator integration | VERIFIED FIXED | app.py line 24, 1446 | LEVEL 1 | ⚠️ PARTIAL |
| 7 | Pre-flight check | VERIFIED FIXED | safety_mechanisms.py line 32 | LEVEL 2 | ✅ YES |
| 8 | Batch safety | VERIFIED FIXED | safety_mechanisms.py MAX_MUTATIONS_PER_BATCH | LEVEL 2 | ✅ YES |
| 9 | Post-flight validation | VERIFIED FIXED | app.py lines 1539-1555 | LEVEL 1 | ⚠️ PARTIAL |
| 10 | Circuit breaker | VERIFIED FIXED | safety_mechanisms.py line 214, test_circuit_breaker | LEVEL 2 | ✅ YES |
| 11 | Cron config source-of-truth | VERIFIED FIXED | app.py _load_cron_tasks/_save_cron_tasks | LEVEL 1 | ✅ YES |
| 12 | test_* task persistence | VERIFIED FIXED | app.py line 83-95, 1348/1381/1407/1432 | LEVEL 2 | ✅ YES |
| 13 | Unauthorized cron execution | VERIFIED FIXED | app.py line 46-78, 1330/1378/1394/1404/1416/1427 | LEVEL 2 | ✅ YES |
| 14 | Cron re-enable race | VERIFIED FIXED | API key check in require_cron_admin | LEVEL 1 | ⚠️ PARTIAL |
| 15 | Unauthenticated Cron mutation APIs | VERIFIED FIXED | All 6 endpoints have dependencies | LEVEL 2 | ✅ YES |
| 16 | validate_no_test_task 未接入 | VERIFIED FIXED | C-E commit 61957a8 | LEVEL 2 | ✅ YES |
| 17 | /run-now 未认证 | VERIFIED FIXED | C-E commit 61957a8 | LEVEL 2 | ✅ YES |

**关键发现：**
- Issue #5, #6, #9, #14 的证据等级被高估
- 这些控制项在代码中存在 (LEVEL 1)，但 Production Runtime 验证不足
---

## 4. C-E Incident Evidence Audit

### 逐项验证

#### A. 是否真的有证据证明旧 bypass path 已经不存在？

**证据检查：**
```
Code present in app.py:
- Line 1330: @app.post("/api/cron/tasks", dependencies=[Depends(require_cron_admin)])
- Line 1378: @app.put("/api/cron/tasks/{task_id}", dependencies=[Depends(require_cron_admin)])
- Line 1394: @app.delete("/api/cron/tasks/{task_id}", dependencies=[Depends(require_cron_admin)])
- Line 1404: @app.post("/api/cron/tasks/{task_id}/start", dependencies=[Depends(require_cron_admin)])
- Line 1416: @app.post("/api/cron/tasks/{task_id}/stop", dependencies=[Depends(require_cron_admin)])
- Line 1427: @app.post("/api/cron/tasks/{task_id}/run-now", dependencies=[Depends(require_cron_admin)])
```

**测试覆盖：**
```
test_cron_api_p0_security.py:
- test_no_api_key_fail_closed (5 endpoints) → PASS
- test_wrong_api_key_rejected (5 endpoints) → PASS
- test_correct_api_key_allowed (5 endpoints) → PASS
- test_run_now_no_api_key_rejected → PASS
- test_run_now_wrong_api_key_rejected → PASS
```

**结论：**
- CODE PRESENT: ✅ 所有 6 个 endpoint 都有认证
- TEST VERIFIED: ✅ 10/10 认证测试通过
- PRODUCTION PATH VERIFIED: ⚠️ **UNKNOWN** — Cron 保持 DISABLED，无生产执行证据
- **Evidence Level: LEVEL 2** (Final Review 错误标记为 LEVEL 3)

---

#### B. 是否真的有证据证明所有 Cron mutation paths 都经过认证？

**代码检查：**
```bash
$ grep -n "dependencies.*require_cron_admin" backend/src/backend/app.py
1330:@app.post("/api/cron/tasks", dependencies=[Depends(require_cron_admin)])
1378:@app.put("/api/cron/tasks/{task_id}", dependencies=[Depends(require_cron_admin)])
1394:@app.delete("/api/cron/tasks/{task_id}", dependencies=[Depends(require_cron_admin)])
1404:@app.post("/api/cron/tasks/{task_id}/start", dependencies=[Depends(require_cron_admin)])
1416:@app.post("/api/cron/tasks/{task_id}/stop", dependencies=[Depends(require_cron_admin)])
1427:@app.post("/api/cron/tasks/{task_id}/run-now", dependencies=[Depends(require_cron_admin)])
```

**结论：**
- ✅ 所有 6 个 mutation endpoint 都有认证
- ✅ 无已知 bypass path
- **Evidence Level: LEVEL 2**

---

#### C. 是否真的有证据证明 Scheduler 实际运行时调用的是最新安全路径？

**Scheduler 代码检查：**
```python
# app.py line 1263-1300
async def _cron_scheduler_loop():
    # ...
    for task_id in tasks_to_run:
        try:
            result = await run_cron_task_now(task_id)  # Line 1300
```

**run_cron_task_now 签名：**
```python
@app.post("/api/cron/tasks/{task_id}/run-now", dependencies=[Depends(require_cron_admin)])
async def run_cron_task_now(task_id: str):
```

**问题：**
- Scheduler 调用 `run_cron_task_now()` 直接（line 1300）
- 但 `dependencies=[Depends(require_cron_admin)]` 是 FastAPI 装饰器，仅在 HTTP 请求时生效
- **Scheduler 直接调用函数时，认证依赖不会被执行！**

**证据：**
- app.py line 1300: `result = await run_cron_task_now(task_id)` — 直接函数调用，无认证
- app.py line 1427: `@app.post(..., dependencies=[Depends(require_cron_admin)])` — 仅 HTTP 路径有认证

**结论：**
- ⚠️ **Scheduler 绕过认证直接调用 run_cron_task_now**
- Final Review 错误地声称"All endpoints authenticated"
- **Evidence Level: LEVEL 1** (代码存在，但执行路径有 bypass)
---

#### D. 是否真的有证据证明 test_* task 无法再次进入生产？

**代码检查：**
```python
# app.py line 83-95
def validate_no_test_task(task_id: str, name: str = None):
    settings = get_settings()
    check_value = name if name is not None else task_id
    if check_value and check_value.startswith('test_') and not settings.PMH_ALLOW_TEST_TASKS:
        raise HTTPException(status_code=400, detail="Test tasks not allowed...")
```

**集成检查：**
```python
# Line 1348: create_cron_task
validate_no_test_task(task_id="", name=name)

# Line 1381: update_cron_task
validate_no_test_task(task_id=task_id)

# Line 1407: start_cron_task
validate_no_test_task(task_id=task_id)

# Line 1432: run_cron_task_now
validate_no_test_task(task_id=task_id)
```

**测试覆盖：**
```python
test_create_test_task_rejected → PASS
test_update_start_test_task_rejected[PUT] → PASS
test_update_start_test_task_rejected[start] → PASS
```

**配置检查：**
```python
# settings.py
PMH_ALLOW_TEST_TASKS: bool = False  # Default: False
```

**结论：**
- CODE PRESENT: ✅ validate_no_test_task 已集成到所有 relevant endpoints
- TEST VERIFIED: ✅ 3/3 test_* 拒绝测试通过
- PRODUCTION PATH VERIFIED: ⚠️ **UNKNOWN** — Cron DISABLED，无生产执行证据
- **Evidence Level: LEVEL 2**

---

#### E. 是否真的有证据证明 Config source-of-truth 已经永久统一？

**代码检查：**
```python
# app.py line 1197-1228
def _load_cron_tasks():
    # 从 JSON 文件加载

def _save_cron_tasks():
    # 保存到 JSON 文件

# Line 1217-1228
_DEFAULT_EVOLUTION_TASK = {
    "name": "记忆演化",
    "type": "evolution",
    "enabled": False,  # ⚠️ 硬编码为 False
    ...
}

_initialize_default_tasks()  # Line 1257 — 模块加载时执行
```

**问题：**
1. `_DEFAULT_EVOLUTION_TASK["enabled"] = False` 硬编码在代码中
2. `_initialize_default_tasks()` 在模块加载时执行，检查 `_cron_tasks` dict
3. 但如果 JSON 文件存在且包含 enabled=True 的任务，不会覆盖

**证据：**
- Code: `_cron_tasks` dict + JSON 持久化
- Test: 无测试验证持久化后的配置
- Production: 未知（Cron DISABLED）

**结论：**
- CODE PRESENT: ✅ 统一使用 _cron_tasks dict
- TEST VERIFIED: ⚠️ **UNKNOWN** — 无持久化测试
- PRODUCTION PATH VERIFIED: ⚠️ **UNKNOWN**
- **Evidence Level: LEVEL 1**

---

## 5. Unauthorized Proposal Evidence Audit

### 数字来源追踪

| 数字 | 来源文档 | 时间戳 | 统计口径 | 可信度 |
|------|----------|--------|----------|--------|
| 12 | 无明确文档 | 2026-08-11 | 未定义 | LEVEL 0 |
| 49 | 无明确文档 | 2026-08-12 | 未定义 | LEVEL 0 |
| 99 | 无明确文档 | 2026-08-12 | 未定义 | LEVEL 0 |
| 106 | 无明确文档 | 2026-08-12 | 未定义 | LEVEL 0 |
| 111 | 无明确文档 | 2026-08-12 | 未定义 | LEVEL 0 |
| 124 | 无明确文档 | 2026-08-12 | 未定义 | LEVEL 0 |
| 353 | phase-20-pending-proposal-purge-report.md | 2026-08-12 | 完整统计 | LEVEL 2 |

### Final Review 声称 vs 实际证据

| Final Review 声称 | 实际证据 | 判定 |
|------------------|----------|------|
| "12, 49, 99, 106, 111, 124 是历史数字" | 无文档支持这些数字的来源 | ⚠️ **UNSUPPORTED CLAIM** |
| "353 是 Phase 20 purge report 的完整统计" | ✅ 有文档支持 | LEVEL 2 |
| "96% 重复，14 个唯一 evidence_chain" | ✅ 有文档支持 | LEVEL 2 |
| "实际唯一 unauthorized proposals ≈ 14" | ⚠️ 基于 353 推导，无独立验证 | LEVEL 1 |

### 最终判定

```
COUNT: PARTIALLY RECONCILED

理由:
1. 353 有明确文档支持 (phase-20-pending-proposal-purge-report.md)
2. 早期数字 (12, 49, 99, 106, 111, 124) 无文档来源，无法验证
3. "~14 unique" 是基于 353 的推导，非独立统计
4. 353 与 C-E incident 的关联性：⚠️ UNKNOWN — 无明确时间戳对比
```
---

## 6. Production Runtime Verification Audit

### 关键发现：Scheduler Bypass

**问题代码路径：**

```python
# app.py line 1263-1300
async def _cron_scheduler_loop():
    # ...
    for task_id in tasks_to_run:
        try:
            result = await run_cron_task_now(task_id)  # ← 直接函数调用
```

```python
# app.py line 1427-1432
@app.post("/api/cron/tasks/{task_id}/run-now", 
          dependencies=[Depends(require_cron_admin)])  # ← 仅 HTTP 路径
async def run_cron_task_now(task_id: str):
    validate_no_test_task(task_id=task_id)  # ← 在函数内部
```

**分析：**
1. Scheduler 直接调用 `run_cron_task_now(task_id)` (line 1300)
2. FastAPI dependency injection (`dependencies=[Depends(require_cron_admin)]`) 仅在 HTTP 请求路径生效
3. **Scheduler 绕过认证直接执行** — 这是一个未记录的安全缺口

**Evidence Level: LEVEL 1** (代码存在，但执行路径有 bypass)

---

### SafetyValidator 集成检查

**代码位置：**
```python
# app.py line 24
from tests.safety_mechanisms import CronSafetyValidator

# app.py line 1446
safety_validator = CronSafetyValidator(engine=engine)

# app.py line 1449
preflight_valid, preflight_reason = await safety_validator.pre_flight_check(
    workspace_id=workspace_id,
    task_id=task_id
)
```

**问题：**
- SafetyValidator 仅在 `run_cron_task_now` 内部初始化
- 如果 Scheduler 绕过认证调用 run_cron_task_now，SafetyValidator 仍然会执行（因为它是函数内部的逻辑）
- 但认证检查被绕过

**结论：**
- SafetyValidator 代码存在：✅ LEVEL 1
- Pre-flight check 在 run_cron_task_now 内部：✅ LEVEL 1
- 但 Scheduler bypass 意味着：认证被绕过，SafetyValidator 仍执行

---

### test_last_run / test_no_lock 再验证

**Final Review 声称：**
> "这两个是测试 fixture ID，非生产 task"

**实际证据：**
```bash
$ grep -rn "test_last_run\|test_no_lock" backend/tests/
backend/tests/test_cron_deadlock.py:86:        _cron_tasks["test_no_lock"] = {
backend/tests/test_cron_deadlock.py:102:        assert "test_no_lock" in saved
backend/tests/test_cron_deadlock.py:110:        test_task_id = "test_last_run"
```

**结论：**
- ✅ Final Review 正确：这些确实是测试 fixture ID
- ✅ 非生产 task
- **Evidence Level: LEVEL 2**

---

## 7. Phase 26-G Completion Claim Audit

### 逐项审计

| 维度 | Final Review 结论 | 实际证据等级 | 修正后判定 |
|------|------------------|--------------|-----------|
| Implementation completeness | PASS | LEVEL 1-2 | ✅ PASS |
| Test completeness | PASS (40/40) | LEVEL 2 | ✅ PASS |
| Production runtime verification | UNKNOWN (marked as VERIFIED) | LEVEL 1 | ⚠️ **UNKNOWN** |
| Incident remediation completeness | PASS | LEVEL 1-2 | ⚠️ **PARTIAL** |
| Data reconciliation completeness | PARTIAL | LEVEL 2 | ✅ PARTIAL |
| Roadmap completeness | PARTIAL | LEVEL 0-1 | ⚠️ **PARTIAL** |

### Critical Finding: Scheduler Authentication Bypass

**Final Review 声称：**
> "所有 6 个 endpoint 已保护"

**实际情况：**
```python
# app.py line 1300 — Scheduler 直接调用，绕过认证
result = await run_cron_task_now(task_id)
```

**影响：**
- HTTP API 路径：认证有效 ✅
- Scheduler 内部调用：认证被绕过 ⚠️
- test_* 保护：仍在函数内部，有效 ✅
- SafetyValidator：仍在函数内部，有效 ✅

**修正结论：**
- Authentication: **PARTIALLY PROTECTED** (HTTP 有效，Scheduler bypass)
- test_* Protection: **PROTECTED** (在函数内部)
- SafetyValidator: **PROTECTED** (在函数内部)

---

### 最终判定

| 检查项 | 结果 |
|--------|------|
| A. Implementation Completeness | ✅ PASS |
| B. Test Completeness | ✅ PASS |
| C. Production Runtime Verification | ⚠️ **PARTIAL** |
| D. Incident Remediation Completeness | ⚠️ **PARTIAL** |
| E. Data Reconciliation Completeness | ✅ PARTIAL |
| F. Roadmap Completeness | ⚠️ **PARTIAL** |

**最终结论：**
```
PHASE_26_G_STATUS = IMPLEMENTATION COMPLETE BUT PRODUCTION RUNTIME = UNKNOWN

理由:
1. 所有代码已实现 (LEVEL 1-2)
2. 所有测试通过 (LEVEL 2)
3. Scheduler 认证 bypass 未记录 (Critical Finding)
4. Cron 保持 DISABLED，无生产验证
5. 需要修复 Scheduler bypass 才能声称 PRODUCTION VERIFIED
```
---

## 8. Unsupported / Overstated Claims

### 清单

| # | Claim in Final Review | Evidence Level | 修正 |
|---|----------------------|----------------|------|
| 1 | "所有 6 个 endpoint 已保护" | LEVEL 1 (CODE) | ⚠️ Scheduler bypass 未记录 |
| 2 | "PRODUCTION PATH VERIFIED" | LEVEL 0 | ❌ 错误 — Cron DISABLED |
| 3 | "353 是 C-E incident 的最终数量" | LEVEL 2 | ⚠️ 无明确时间戳关联 |
| 4 | "~14 unique 是独立统计" | LEVEL 1 | ❌ 基于 353 推导 |
| 5 | "早期数字 (12,49,99...) 可信度 LOW" | LEVEL 0 | ❌ 无来源文档 |
| 6 | "C-F 原定目标已在 C-E 完成" | LEVEL 1 | ✅ 正确 |
| 7 | "Phase 26-G 可以锁定完成" | LEVEL 2 | ⚠️ 需先修复 Scheduler bypass |

---

## 9. Corrected Status

### 修正后的安全状态

```
CODE VERIFIED:           ✅ LEVEL 2
TEST VERIFIED:           ✅ LEVEL 2
PRODUCTION RUNTIME:      ⚠️ UNKNOWN (Cron DISABLED)
SCHEDULER BYPASS:        ⚠️ EXISTS (未记录)

AUTHENTICATION:
  - HTTP API:            ✅ PROTECTED (all 6 endpoints)
  - Scheduler:           ⚠️ BYPASSED (direct function call)

PROTECTION:
  - test_* rejection:    ✅ PROTECTED (in function)
  - SafetyValidator:     ✅ PROTECTED (in function)
  - Circuit breaker:     ✅ PROTECTED (in function)
```

### 修正后的 Phase 26-G 状态

```
PHASE_26_G_STATUS = IMPLEMENTATION COMPLETE
                   BUT
                   PRODUCTION RUNTIME VERIFICATION = UNKNOWN
                   SCHEDULER_AUTH_BYPASS = UNRESOLVED

COMMIT: 61957a8 (C-ELOCKED)
TESTS:  40/40 PASS
P0:     ALL REMEDIATED (CODE + TEST)
SAFETY: PARTIALLY VERIFIED
```

---

## 10. Recommended Decision

### 选项评估

| 选项 | 建议 | 理由 |
|------|------|------|
| **1. LOCK Phase 26-G as IS** | ❌ 不推荐 | Scheduler bypass 未解决 |
| **2. Create Phase 26-G-C-F for Scheduler fix** | ✅ **推荐** | 需要修复认证 bypass |
| **3. Extend C-E scope** | ⚠️ 可选 | 可合并修复 |
| **4. Mark as PARTIALLY COMPLETE** | ✅ **推荐** | 诚实反映当前状态 |

### 建议行动

```
Phase 26-G Status: PARTIALLY COMPLETE

Immediate Actions Required:
1. Fix Scheduler authentication bypass (critical)
   - Option A: Add auth check inside run_cron_task_now
   - Option B: Refactor to use dependency injection
2. Document Scheduler bypass risk
3. Add test for Scheduler auth path
4. Re-verify all tests after fix

Phase 26-G Closure Criteria:
- [ ] Scheduler bypass fixed
- [ ] Scheduler auth test added
- [ ] All tests PASS
- [ ] Production runtime verified (or documented as future work)
```

---

## Appendix: Evidence Summary

### 关键代码证据

| 文件 | 行号 | 内容 | 等级 |
|------|------|------|------|
| app.py | 46-78 | require_cron_admin | LEVEL 1 |
| app.py | 83-95 | validate_no_test_task | LEVEL 1 |
| app.py | 1330 | POST /tasks auth | LEVEL 2 |
| app.py | 1378 | PUT /tasks/{id} auth | LEVEL 2 |
| app.py | 1394 | DELETE /tasks/{id} auth | LEVEL 2 |
| app.py | 1404 | POST /tasks/{id}/start auth | LEVEL 2 |
| app.py | 1416 | POST /tasks/{id}/stop auth | LEVEL 2 |
| app.py | 1427 | POST /tasks/{id}/run-now auth | LEVEL 2 |
| app.py | 1300 | Scheduler direct call | ⚠️ BYPASS |
| app.py | 1446 | CronSafetyValidator init | LEVEL 1 |
| test_cron_api_p0_security.py | 全文 | 22 tests | LEVEL 2 |
| test_safety_mechanisms.py | 全文 | 13 tests | LEVEL 2 |

### 关键文档证据

| 文档 | 内容 | 等级 |
|------|------|------|
| phase-20-pending-proposal-purge-report.md | 353 proposals purge | LEVEL 2 |
| phase26-b4-entity-resolution-critical-root-cause-audit.md | Bug diagnosis | LEVEL 2 |
| phase26-b5-entity-resolution-fix-and-anti-collapse-gate.md | Anti-collapse gate | LEVEL 2 |
| phase26g_c_e_final_verification_report.md | P0 fix report | LEVEL 2 |

---

*Evidence-Level Audit completed by Hermes Agent Agnes 2.0*
*Audit type: READ-ONLY — No modifications made*
*Date: 2026-08-22*
