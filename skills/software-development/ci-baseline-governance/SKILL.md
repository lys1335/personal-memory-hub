---
name: ci-baseline-governance
description: Decide if CI red is new debt or baseline. The forensic read-only workflow for resolving CI failures and establishing baseline governance.
---

# CI Baseline Governance

When CI goes red on a freshly-pushed commit, the first question is always
"is the new commit's fault, or is the CI baseline already red?" The naive
answer — count files the commit touched and divide — gives the wrong number
nearly every time. This skill is the read-only forensic + governance flow
for resolving that question and proposing a clean path forward.

## When this applies

- User pushed a commit, sees a red X on GitHub, and asks PM to investigate
  ("CI 失败", "红叉", "看看 CI 状态")
- User explicitly asks for "baseline governance" / "lint debt cleanup"
- A Worker reports a CI failure count and PM needs to decide if it is
  trustworthy (the M6 case — 22 errors, all misdiagnosed)
- Phase is FUNCTIONAL_LOCKED but CI is red; need to decide next step

## What this skill does NOT do

- It does not re-run CI. Re-running CI is a separate user authorization.
- It does not commit or push. Always out of scope until the user says so.
- It does not modify CI workflow files except as a Step-N governance
  deliverable with explicit user authorization.
- It does not "fix" baseline debt beyond documenting it.

## Procedure (read-only forensic first, governance second)

### Step 1 — Pull CI state for the suspect commit

Use public GitHub REST API; no `gh` CLI required, no token required for
`check-runs` / `commits` / `actions/runs` on public repos. See
`references/ci_forensic_recipe.md` for the exact curl + python parsing
sequence. Output: 4-row conclusion table (run id + per-job step list).

**Key signatures to look for:**
- **early-success / late-failure**: first N steps `success`, one late step `failure` (e.g. `Run ruff` failing after `Install dependencies` succeeded) — environment OK, command itself failed.
- **cancelled downstream**: 3.12 cancelled because 3.11 failed — only count 3.11 once, don't double-count.

### Step 2 — Reproduce the CI command locally with the project's venv

PM MUST re-run the failing command with the project's actual interpreter to isolate
environment vs code issues.

**Critical distinction:**
- **Local passes, CI fails** → Environment mismatch (system Python vs project venv). The CI environment (ubuntu-latest + uv) has different Python version, dependencies, or tooling than the local machine. This explains why `uv run mypy` fails locally but `uv run pytest` passes locally (when the latter succeeds).
- **Local fails, CI fails** → Actual code defect (import resolution, type errors, test infrastructure). The same command produces the same failure locally and in CI.

```bash
cd backend
.venv/Scripts/python.exe -m ruff check src/ tests/ --output-format=concise > /tmp/ruff.txt
.venv/Scripts/python.exe -m pytest tests/ -v --cov=backend --cov-report=term-missing
```

If local reproduction **PASSES** but CI **FAILS**, the root cause is environment-specific (missing dependencies, different Python version, different toolchain). If local **FAILS** and CI **FAILS**, the root cause is in the code (import resolution, type errors, test infrastructure).

### Step 3 — Compute the *real* new-debt count (not touched-file count)

Naive count = "ruff errors in files the commit touched". Correct count = "ruff errors on lines the commit actually changed, in files the commit changed, that didn't exist on the parent commit".

```bash
# Get the line ranges the commit changed
git diff <prev_sha>..<new_sha> -- <file> | grep -E '^[+-]'

# Get the ruff output with file:line:col triples
ruff check <file> --output-format=concise

# Cross-reference: which (file, line) triples fall inside the diff ranges
```

**Why this matters:** Most files have pre-existing lint debt. Modifying the touched-file count hides the real new-debt contribution of a commit.

### Step 4 — Compare against prior 1-2 commits on main

If the project has a committed baseline snapshot (e.g., `.hermes/plans/ci-baseline-ruff-snapshot.txt`), the CI workflow must compare current errors against that baseline using identical output format.

```bash
# In CI, with working-directory set (e.g., backend/):
uv run ruff check src/ tests/ --output-format=concise | grep -E "^src" | sort > current.txt
grep -E "^src" ../.hermes/plans/ci-baseline-ruff-snapshot.txt | sort > baseline.txt
new_errors="$(comm -13 baseline.txt current.txt)"
if [ -n "$new_errors" ]; then
  echo "New Ruff errors detected:"
  printf '%s\n' "$new_errors"
  exit 1
fi
echo "No new Ruff debt"
```

**Critical pitfall:** The baseline path must be relative to the CI working-directory. If the baseline snapshot was created on Windows (path separators `\`) but CI runs on Linux (path separators `/`), `comm -13` flags every line as "new debt" — not because anything changed, but because `src\\backend\\...` ≠ `src/backend/...`. Normalize path separators in the baseline to match the CI platform.

### Step 5 — Verdict and report shape

The forensic report to the user must contain:
- commit SHA + commit message
- run id (from `actions/runs`)
- per-job conclusion table (early-success / late-failure / cancelled)
- per-failing-job step list (CI command + local reproduction result)
- baseline comparison (same failure pattern on prior commits?)
- **new-debt count vs touched-file count** (the central distinction)
- `CI_VERIFICATION = PASS / FAIL / BASELINE_FAILURE / UNKNOWN`
- `NEXT_AUTHORIZATION_REQUIRED = YES` (if fixing new-debt)
- recommended next decision (fix / accept FUNCTIONAL_LOCKED / create separate CI baseline task / etc.)

## Pitfalls

- **"M6 caused ~99 ruff errors"** is the easy wrong attribution. The M6 case: touched-file count = 99, real M6-introduced count = 4. The diff-cross-reference method is mandatory, not optional.
- **CI workflow `exclude` lists hide some files from the touched-file count**. A file in `[tool.ruff] exclude` will not appear in CI's ruff output but will appear in `ruff check <file>`. Always cross-check the exclude list before computing the touched-file count.
- **System Python != project venv Python**. Reproducing CI commands with `python` (system) on a project with a `backend/.venv/` will report `ModuleNotFoundError: No module named 'sqlalchemy'` and the next downstream failure (DB connection) gets misattributed as 'PostgreSQL ConnectionRefused'. Use `backend/.venv/Scripts/python.exe` (or `backend/.venv/bin/python` on Linux) for any local reproduction.
- **A `cancelled` job is not a passing job**. Test jobs that show `cancelled` were killed because an earlier job in the matrix failed (e.g. pytest 3.12 cancelled because pytest 3.11 failed). Report as downstream symptom, not independent green status.
- **Baseline governance artifacts must be committed and shared, not .gitignored**. A local-only baseline snapshot (e.g., `.hermes/plans/ci-baseline-ruff-snapshot.txt` in `.gitignore`) defeats the entire "No New Debt" CI gate — CI runners, other machines, and new clones cannot fetch the same baseline to compare against. The baseline snapshot and its documentation MUST be committed to the repo so the CI workflow can read them.
- **New-debt detection must capture `comm -13` output, not rely on exit code**. `comm` returns 0 on success regardless of whether output exists. Correct pattern:
  ```bash
  new_errors="$(comm -13 baseline.txt current.txt)"
  if [ -n "$new_errors" ]; then
    echo "New Ruff errors detected:"
    printf '%s\n' "$new_errors"
    exit 1
  fi
  ```
  The `$?` / `[ -s current.txt ]` pattern is wrong — it checks the full current output, not the delta.
- **Ruff output format must be identical for baseline and current**. Use `--output-format=concise` + `grep -E "^src"` + `sort` for both baseline generation and CI comparison. Any format difference (headers, footers, warning lines) will produce false positives.
- **UV version in CI workflow should be pinned, not ranged**. `"0.11.x"` is a range; pin to a specific stable version (e.g., `"0.11.32"`) to avoid surprise upgrades on CI runners.
- **Pytest CI command should include failure-budget flags**. Add `--tb=short -x --durations=10` to the pytest invocation for concise failure output, fast-fail on first error, and slow-test visibility — these are CI-quality improvements that don't change pass/fail semantics.
- **Git add . / git add -A will pull in `nul` files, debug scripts, and untracked noise**. When the governance step is "fix 4 ruff errors in 2 test files", use `git add path/to/test_ingest_parser_multimodal.py path/to/test_ingest_parser_helpers.py` (each on its own), then `git status --short` to confirm.
- **Cross-platform path separator mismatch in baseline files causes false-positive `comm -13` on every record**. When a baseline snapshot is created on Windows (path separators `\`) but CI runs on Linux (path separators `/`), `comm -13 baseline.txt current.txt` flags every line as "new debt" — not because anything changed, but because `src\\backend\\...` ≠ `src/backend/...`. The fix is to normalize path separators in the baseline to match the CI platform. See `references/baseline-normalization.md` for the exact verification and audit procedure.

## References

- `references/ci_forensic_recipe.md` — exact curl + python parsing sequence for `check-runs` / `actions/runs` / `jobs` / `annotations`,
  plus the local-reproduction venv trick. Use this every time CI goes red on a fresh push.
- `references/baseline-normalization.md` — procedure for normalizing path separators in a committed baseline snapshot when the baseline platform (Windows `\`) differs from the CI platform (Linux `/`),
  including the byte-level diff audit that proves only `\` → `/` changed and nothing else.
