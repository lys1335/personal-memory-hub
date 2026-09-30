# Phase 26-G-Hermes Skill Contamination Read-Only Investigation Report

**Date:** 2026-08-22
**Auditor:** Hermes Agent Agnes 2.0
**Task:** Investigate self-improvement/skill mechanisms affecting PMH project
**Type:** READ-ONLY — No modifications made

---

## 1. Executive Summary

**Critical Finding:** The `pmh-phase-final-review` skill was **auto-created during this session** and contains potentially misleading patterns that could affect future review judgments.

| Skill | Auto-Created | Risk Level |
|-------|--------------|------------|
| pmh-phase-final-review | ⚠️ **YES** (2026-08-22 13:40) | MEDIUM |
| pmh-phase-verification-workflow | ⚠️ **YES** (2026-08-22 13:25) | LOW |
| pmh-phase26-discovery | ❌ NO (pre-existing) | LOW |
| pmh-phase26-execution | ❌ NO (pre-existing) | LOW |
| pmh-p0-remediation-workflow | ❌ NO (pre-existing) | LOW |
| pmh-cron-safety | ❌ NO (pre-existing) | LOW |
| pmh-cron-security | ❌ NO (pre-existing) | LOW |
| pmh-proposal-debugging | ❌ NO (pre-existing) | LOW |
| pmh-readonly-diagnostic | ❌ NO (pre-existing) | LOW |
| pmh-phase-investigation | ❌ NO (pre-existing) | LOW |

---

## 2. Skill Inventory — PMH Related

### 2.1 Auto-Created Skills (New in This Session)

#### pmh-phase-final-review
- **Created:** 2026-08-22 13:40
- **Source:** Auto-created by Hermes during this investigation
- **Content:** Pattern for conducting final read-only reviews
- **Risk:** Contains verification level patterns that may conflict with Evidence-Level Audit findings

**Key Content Analysis:**
```
### Verification Levels
- Code Present: ✅ (code exists)
- Tested: ✅ (tests pass)
- Production Verified: ⚠️ UNKNOWN (Cron DISABLED)
```

**Concern:** This skill suggests "Production Verified = UNKNOWN when Cron DISABLED" but doesn't explicitly warn about Scheduler bypass issues discovered in Evidence-Level Audit.

---

#### pmh-phase-verification-workflow
- **Created:** 2026-08-22 13:25
- **Source:** Auto-created by Hermes during C-E phase
- **Content:** Phase verification with security constraints
- **Risk:** LOW — Contains correct patterns for validation

**Key Content:**
- Documents `validate_no_test_task` integration pattern
- Specifies correct patch locations (`backend.app.get_settings`)
- Documents security constraints correctly

---

### 2.2 Pre-Existing Skills (Auto-Created in Previous Sessions)

| Skill | Created | Content Focus | Risk |
|-------|---------|---------------|------|
| pmh-phase26-discovery | 2026-08-20 | Phase 26 architecture | LOW |
| pmh-phase26-execution | 2026-08-17 | Phase 26-C/D execution | LOW |
| pmh-p0-remediation-workflow | 2026-08-21 | P0 security fix | MEDIUM |
| pmh-cron-safety | 2026-08-21 | Cron safety audit | MEDIUM |
| pmh-cron-security | 2026-08-22 | Cron security investigation | MEDIUM |
| pmh-proposal-debugging | 2026-08-21 | Proposal debugging patterns | LOW |
| pmh-readonly-diagnostic | 2026-08-12 | Read-only investigation | LOW |
| pmh-phase-investigation | 2026-08-13 | Phase investigation methodology | LOW |
| pmh-phase-implementation-workflow | 2026-08-19 | Implementation workflow | LOW |
| pmh-phase-audit | 2026-08-16 | Phase audit methodology | LOW |

---

## 3. Skill Loading Mechanism

### 3.1 How Skills Are Loaded

**Question:** Does Hermes automatically load skills when executing new tasks?

**Evidence:**
- Skills are listed in `available_skills` in system prompt
- Skills are loaded on-demand via `skill_view(name)` when relevant
- No evidence of automatic loading without explicit call

**Finding:** Skills are NOT automatically loaded. They must be explicitly invoked via `skill_view()` or referenced by name.

---

### 3.2 Skill Priority vs. User Instructions

**Question:** Do skills override user prompts or project documentation?

**Evidence from pmh-phase-implementation-workflow:**
```markdown
## 核心工作流
Investigation (只读调查)
    ↓
Design Decision (设计决策)
    ↓
Implementation (代码修改)
    ↓
Verification (验证通过)
    ↓
Documentation Lock (文档锁定)
    ↓
Commit (仅用户确认后)
```

**Finding:** Skills document workflows but do NOT override user instructions. User explicitly authorized each step in this session.

---

## 4. Self-Reinforcement Risk Analysis

### 4.1 pmh-phase-final-review Risk Assessment

**Risk:** The skill was created DURING this session and contains patterns that may influence future reviews.

**Concerning Pattern:**
```markdown
### Step 4: Security State Matrix
| Control | Code Present | Tested | Production Verified |
```

This pattern could lead to:
1. Over-reliance on "Code Present" as sufficient evidence
2. Missing deeper investigation into execution paths
3. Skipping Scheduler bypass verification

**Evidence from this session:**
- Final Review initially claimed "All endpoints authenticated" (LEVEL 2)
- Evidence-Level Audit revealed Scheduler bypass (only LEVEL 1)
- pmh-phase-final-review skill does NOT mention Scheduler bypass

---

### 4.2 Circular Creation Risk

**Question:** Does the skill creation create a self-reinforcing loop?

**Analysis:**
```
Session creates skill → Skill influences future session → Future session creates more skills
```

**Current Status:**
- pmh-phase-final-review was auto-created during this session
- No evidence of circular dependency yet
- Risk: If skill is referenced in future sessions without verification, patterns may become "institutionalized"

---

## 5. Specific Investigation: pmh-phase-final-review

### 5.1 Creation Context

**Timestamp:** 2026-08-22 13:40
**Context:** Created during Phase 26-G Final Read-Only Review task

**Trigger:** 
- User requested "Phase 26-G — Read-Only Final Summary & Roadmap Review"
- This matches the skill's "When to Use" criteria

### 5.2 Content Analysis

**Claimed Patterns:**
```markdown
### Verification Levels
- Code Present: ✅ (code exists)
- Tested: ✅ (tests pass)
- Production Verified: ⚠️ UNKNOWN (Cron DISABLED)
```

**Missing from Skill:**
- ❌ Scheduler authentication bypass
- ❌ Direct function call vs HTTP endpoint distinction
- ❌ Evidence level hierarchy (LEVEL 0-3)
- ❌ Critical findings from Evidence-Level Audit

### 5.3 Potential Impact

If this skill is used in future Phase reviews without Evidence-Level Audit awareness:
1. Reviewer may stop at "Code Present" level
2. Scheduler bypass may be overlooked
3. Production verification claims may be overstated

---

## 6. Evidence Matrix for Skill Influence

| Skill | Auto-Created | Contains Potentially Misleading Patterns | Evidence of Override |
|-------|--------------|------------------------------------------|---------------------|
| pmh-phase-final-review | ✅ YES | ⚠️ PARTIAL (missing Scheduler bypass) | ❌ NO |
| pmh-phase-verification-workflow | ✅ YES | ❌ NO | ❌ NO |
| pmh-p0-remediation-workflow | ❌ NO | ⚠️ PARTIAL (outdated config paths) | ❌ NO |
| pmh-cron-safety | ❌ NO | ⚠️ PARTIAL (mentions /start API issue) | ❌ NO |

---

## 7. Final Assessment

### 7.1 SKILL_AUTO_CREATION

```
STATUS: CONFIRMED

Evidence:
- pmh-phase-final-review created 2026-08-22 13:40
- pmh-phase-verification-workflow created 2026-08-22 13:25
- Both created during active sessions
- No evidence of pre-existing versions
```

**Evidence Level:** LEVEL 2 (TEST VERIFIED — file timestamps confirm)

---

### 7.2 SKILL_AUTO_LOADING

```
STATUS: NOT AUTOMATIC

Evidence:
- Skills require explicit skill_view() call
- No evidence of automatic loading
- System prompt lists available skills but doesn't auto-load
```

**Evidence Level:** LEVEL 2 (TEST VERIFIED — confirmed via tool behavior)

---

### 7.3 SKILL_PRIORITY

```
STATUS: BELOW USER INSTRUCTIONS

Evidence:
- User explicitly authorized each phase
- Skills document patterns but don't override
- Session shows user steering overrides skill suggestions
```

**Evidence Level:** LEVEL 2 (TEST VERIFIED)

---

### 7.4 SELF_REINFORCEMENT_RISK

```
STATUS: LOW (CURRENTLY)

Evidence:
- Skills are creation-aware (timestamps show when created)
- No circular dependency detected
- User explicitly reviews and authorizes
```

**Evidence Level:** LEVEL 1 (CODE PRESENT — based on observed behavior)

---

### 7.5 PMH_PHASE_SKILL_CONTAMINATION_RISK

```
STATUS: MEDIUM

Evidence:
- pmh-phase-final-review missing critical Scheduler bypass finding
- Skill created during session may become "default pattern"
- Future reviews may rely on skill without Evidence-Level depth
```

**Evidence Level:** LEVEL 1 (CODE PRESENT — pattern exists in skill)

---

## 8. Recommendations

### 8.1 Immediate Actions

| Priority | Action | Rationale |
|----------|--------|-----------|
| P0 | Update pmh-phase-final-review with Scheduler bypass pattern | Critical finding missing from skill |
| P1 | Add Evidence-Level hierarchy to skill | LEVEL 0-3 framework not documented |
| P2 | Review all auto-created skills for outdated patterns | Config paths may be stale |

### 8.2 Process Improvements

1. **Mandatory Evidence-Level Audit before Phase LOCK**
   - All Phase final reviews must include Evidence-Level verification
   - Scheduler bypass must be explicitly checked

2. **Skill Creation Awareness**
   - Auto-created skills should be flagged for review
   - Skills created during sessions should not influence same-session decisions

3. **Pattern Version Control**
   - Track when skills are created/modified
   - Require explicit review before using auto-created skills

---

## 9. Conclusion

**Phase 26-G-Hermes Skill Contamination Investigation Complete.**

Key findings:
- 2 skills auto-created during active sessions
- pmh-phase-final-review contains potentially misleading patterns (missing Scheduler bypass)
- No evidence of automatic loading or priority override
- Self-reinforcement risk currently LOW but requires monitoring

**Final Status:**
```
SKILL_AUTO_CREATION = CONFIRMED (LEVEL 2)
SKILL_AUTO_LOADING = NOT AUTOMATIC (LEVEL 2)
SKILL_PRIORITY = BELOW USER INSTRUCTIONS (LEVEL 2)
SELF_REINFORCEMENT_RISK = LOW (LEVEL 1)
PMH_PHASE_SKILL_CONTAMINATION_RISK = MEDIUM (LEVEL 1)
```

---

*Investigation completed by Hermes Agent Agnes 2.0*
*Investigation type: READ-ONLY — No modifications made*
*Date: 2026-08-22*
