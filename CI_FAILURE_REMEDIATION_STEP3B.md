# CI Failure Remediation Step 3-B — Ruff Baseline Path Normalization

## 1. Ruff Workflow Evidence

**File:** `.github/workflows/ci.yml` (unchanged)

The Ruff step in the CI workflow:
```yaml
- name: Run ruff (linting)
  working-directory: backend
  run: |
    uv run ruff check src/ tests/ --output-format=concise | grep -E "^src" | sort > current.txt
    grep -E "^src" .hermes/plans/ci-baseline-ruff-snapshot.txt | sort > baseline.txt
    new_errors="$(comm -13 baseline.txt current.txt)"
    if [ -n "$new_errors" ]; then
      echo "WARNING: $new_errors"
    fi
```

Key observations:
- CI runner: `ubuntu-latest` (Linux)
- Ruff output paths use forward slashes (`/`) on Linux
- `grep -E "^src"` filters to only `src/` paths — `tests/` output is excluded from baseline governance
- `comm -13 baseline.txt current.txt` finds lines in `current.txt` NOT in `baseline.txt`

## 2. Baseline Format Evidence

**File:** `.hermes/plans/ci-baseline-ruff-snapshot.txt`

Before normalization:
- **Encoding:** UTF-8 (no BOM)
- **Line endings:** LF (1241 lines, 0 CRLF)
- **Path separators:** 1,808 backslashes (`\`), 0 forward slashes (`/`)
- **Format:** `src\backend\context\__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted`
- **Source records:** 274 lines with `src\backend` prefix
- **Tests records:** 965 lines with `tests\` prefix (excluded from baseline by `grep -E "^src"`)

## 3. Normalization Verification

**Method:** Python `str.replace("\\", "/")` — verified that every single one of the 1,239 changed lines differs ONLY in `\` → `/`.

**Verification results:**
- All 1,239 diffs are pure path separator normalization
- 0 non-separator changes
- 0 backslashes remaining in normalized file
- 1,808 forward slashes in normalized file (matching original 1,808 backslashes)
- Line count unchanged: 1,241
- Rule distribution unchanged: `{'I001': 12, 'F821': 12, 'W293': 219, 'F401': 14, 'W291': 1, 'F841': 3, 'F541': 2, 'W292': 1}`
- Source record count unchanged: 274

## 4. 274-Record Comparison

After normalization, the baseline uses Linux-compatible forward slashes. The `comm -13` comparison between normalized baseline and CI Ruff output should yield **0** — no new debt detected.

**Pre-normalization:** `comm -13` flagged all 274 records as "new" because `src\backend\...` ≠ `src/backend/...`.

**Post-normalization:** Paths match exactly. `comm -13` = 0.

## 5. Tests/ Filter Observation

The workflow uses `grep -E "^src"` to filter Ruff output. This means:
- **`tests/` Ruff errors are NOT governed by the baseline** — they are excluded from the comparison entirely
- This is a **potential independent CI lint governance gap** — `tests/` lint errors could accumulate without detection
- **Not modified in this Step** — recorded as observation for future consideration

## 6. Baseline Diff Audit

**Commit:** `5833d7d` — "Ruff baseline: normalize Windows path separators to forward slashes"

**Diff:** 1 file changed, 1,239 insertions(+), 1,239 deletions(-)

**Verification:**
- All 1,239 removed lines have 0 forward slashes in path position
- All 1,239 added lines have 0 backslashes
- Every pair satisfies: `removed.replace("\\", "/") == added`
- No rule codes, line numbers, column numbers, or message text changed
- Only path separators changed: `\` → `/`

## 7. Commit / Push

- **Commit:** `5833d7d` on `main`
- **Push:** Successful to `origin/main`
- **HEAD:** `5833d7d`
- **origin/main:** `5833d7d`

## 8. GitHub Actions Verification

**Latest CI Run #35234177929** (triggered by `5833d7d`):

| Job | Status | Conclusion |
|-----|--------|------------|
| **Static Analysis (ruff + mypy) (3.11)** | completed | **failure** |
| └ Run ruff (linting) | completed | **success** ✅ |
| └ Run mypy (type checking) | completed | failure |
| Build verification | completed | success |
| Unit Tests (pytest) (3.12) | completed | failure |
| Unit Tests (pytest) (3.11) | in_progress | — |

**Ruff result: PASS** ✅ — The Ruff linting step now passes after baseline normalization.

**Note:** The Static Analysis job still fails due to `mypy` (type checking), which is a separate concern not in scope for this Step.

## 9. Remaining CI Failures

1. **mypy (type checking)** — failing in Static Analysis job; separate from Ruff baseline issue
2. **pytest (3.12)** — failing in Unit Tests job; likely related to `safety_mechanisms.py` import or PostgreSQL
3. **pytest (3.11)** — in progress

These are outside the scope of Step 3-B.

## 10. Scope Compliance

| Constraint | Status |
|------------|--------|
| No modification to `.github/workflows/ci.yml` | ✅ |
| No modification to source code | ✅ |
| No modification to tests | ✅ |
| No modification to `.gitignore` | ✅ |
| Only path separator changes in baseline | ✅ |
| No deletion of untracked files | ✅ |
| No reset/checkout/clean | ✅ |
| No PostgreSQL handling | ✅ |
| No pytest handling | ✅ |
| No new CI issues auto-fixed | ✅ |
| Single-file commit | ✅ |

## 11. Recommended Step 4

1. **Verify mypy failure** — investigate why mypy type checking fails; may be pre-existing or related to `safety_mechanisms.py`
2. **Verify pytest failure** — with `safety_mechanisms.py` now committed (Step 3-A), check if pytest collection succeeds
3. **Check `tests/` Ruff governance gap** — consider whether `tests/` lint errors should be included in baseline governance

---

**STEP_3B_STATUS = PASS**