# CI Failure Investigation Step 1

## 1. Investigation Scope
- **Goal**: Investigate Run 35107609618 CI failures (Ruff + pytest)
- **Constraints**: No code modifications, no pushes, no commits
- **Focus**: Root cause analysis only

## 2. CI Run Facts (Run 35107609618)
| Component | Status | Details |
|-----------|--------|---------|
| Unit Tests (pytest 3.12) | Cancelled | PostgreSQL `ConnectionRefusedError` – environment issue, not code defect |
| Static Analysis (ruff + mypy 3.11) | Failure | 831 passed, 8 skipped, 22 errors, 0 failed |

## 3. Ruff Failure Root Cause
**Root Cause**: Cross-platform path separator mismatch between Windows (baseline) and Linux (CI).

- **Baseline snapshot** (`.hermes/plans/ci-baseline-ruff-snapshot.txt`) was generated on Windows and uses **backslash** path separators:
  ```
  src\backend\context\__init__.py:3:1: I001 [...]
  src\backend\context\context_window.py:139:44: UP037 [...]
  ```
- **CI environment** (Ubuntu) runs `ruff` which outputs **forward slashes**:
  ```
  src/backend/context/__init__.py:3:1: I001 [...]
  src/backend/context/context_window.py:139:44: UP037 [...]
  ```
- **Why `comm -13` flags all 274 lines**: `grep -E "^src"` on the Linux CI picks up forward-slash paths, while the Windows baseline has backslash paths. They are treated as different lines.
- **Conclusion**: The baseline snapshot was created with Windows path formatting. The CI always runs on Linux, producing forward-slash paths. The comparison fails because the path representations don't match.

## 4. Pytest Failure Root Cause
**Root Cause**: Test file `backend/tests/safety_mechanisms.py` is **untracked** (not in git index) despite being present in the working tree.

- **Import in `app.py`**: `from tests.safety_mechanisms import CronSafetyValidator`
- **Path resolution**: `app.py` (in `backend/src/backend/`) inserts `backend/src` into `sys.path`, allowing `tests.safety_mechanisms` to resolve to `backend/tests/safety_mechanisms.py`.
- **File existence**: Confirmed present (243 lines, 8MB) in the working tree.
- **Why it fails**: The file is untracked. While the import should theoretically work, the CI may be having issues with untracked test files (e.g., test collection ignoring untracked files, or the test runner not seeing the file properly).
- **Minimal remediation**: Track the file with `git add backend/tests/safety_mechanisms.py` and commit. However, this is a separate action from the current investigation scope.

## 5. Git / History Evidence
- **HEAD** = `8e02e9cacc096333ebcd03da6c605cdd6fc33bb8` (Step 3 commit)
- **origin/main** = `8e02e9cacc096333ebcd03da6c605cdd6fc33bb8` (same as HEAD)
- **Step 3 commit** `8e02e9c`: Contains the 4-line deletion in `backend/tests/test_ingest_parser_helpers.py` and `backend/tests/test_ingest_parser_multimodal.py` (authorized by Step 3)
- **`backend/tests/safety_mechanisms.py`** is **not in git history** (appears as `??` in `git status`)
- **No other uncommitted changes** in the working tree besides the Step 3 test file deletions

## 6. Local-vs-CI Difference
- **Local (Windows)**: `src\backend\...` (backslashes)
- **CI (Linux)**: `src/backend/...` (forward slashes)
- **Impact**: `comm -13` treats all 274 baseline lines as "new errors" because the path separators differ.

## 7. Root Cause Classification
| Issue | Category | Severity |
|-------|----------|----------|
| Ruff CI failure | Cross-platform path formatting | High (affects linting gate) |
| Pytest CI failure | Untracked test file | Medium (may affect test coverage reporting) |

## 8. Minimal Remediation Options
### Ruff
- **Option A**: Update the baseline snapshot to use forward slashes (match CI environment). This is safe and aligns with the CI's Linux environment.
- **Option B**: Modify the CI workflow to normalize path separators (not allowed per constraints).
- **Recommendation**: Option A — update `.hermes/plans/ci-baseline-ruff-snapshot.txt` to replace `src\` with `src/` throughout.

### Pytest
- **Option A**: Track `backend/tests/safety_mechanisms.py` with `git add` and commit (outside current scope).
- **Option B**: Ensure the test file is properly indexed for test collection (could involve workflow adjustments).
- **Recommendation**: Track the file (separate action).

## 9. Risks / Unknowns
- The Ruff baseline update requires careful path consistency across all files (not just the 274 lines).
- The pytest failure might also be related to the untracked file not being recognized by the test runner.
- No evidence of other CI-related issues (e.g., mypy failures, dependency issues).

## 10. Recommended Next Investigation Step
Update the Ruff baseline snapshot to use forward slashes (matching the CI Linux environment) to eliminate the `comm -13` false positive. Then re-run the Ruff check to confirm the baseline passes.

**STEP_1_STATUS = INVESTIGATION_COMPLETE**
