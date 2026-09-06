# ADR-D5-3: MemoryHubError Migration to shared/domain

## Status

Accepted

## Context

D5-2 (`bc65e96`) established the migration precedent by moving `EvolutionResult` /
`TopicEvolutionResult` from `backend/evolution/evolution_result.py` to
`backend/shared/domain/evolution_result.py`. The driver was the same problem
D5-3 must now address: a non-business type that is shared by multiple business
packages was physically located inside one of those packages.

`MemoryHubError` is the marker root of the entire MemoryHub exception
hierarchy. It is a pure marker (`class MemoryHubError(Exception)`) — no
`__init__`, no methods, no state. It is referenced by:

- `backend/src/backend/service/exceptions.py` — `DomainError(MemoryHubError)`
  and the 13 domain-error subclasses inherited transitively by service code.
- `backend/src/backend/ingest/exceptions.py` —
  `ImportFrameworkError(MemoryHubError)` and its subclasses.

It is therefore a **cross-package shared domain contract**: service/ and
ingest/ both consume it, neither owns the semantics, and the Entry Layer
relies on it as the discriminator that triggers error-response translation.

Currently the root sits inside `service/exceptions.py`. That placement makes
ingest/ depend on service/ purely for a marker, which inverts the natural
dependency direction (a sibling business package appears as if it were a
child of `service`). It also conflicts with the layering that D5-2 already
established for the parallel `evolution_result` case.

The goal of D5-3 is to relocate `MemoryHubError` alone (not `DomainError`,
not any of the 13 domain-error subclasses, not any of the ingest exceptions)
to the correct architectural home, leaving every business behaviour,
exception behaviour, call site, and import surface either identical or
strictly more correct.

## Decision

Four atomic decisions, each touching exactly the files required:

1. **D5-3-2a — Move `MemoryHubError` to `shared/domain/exceptions.py`.**
   A new file `backend/src/backend/shared/domain/exceptions.py` is created
   containing the marker class plus a module docstring that records the
   relocation rationale (cross-package role, no infrastructure
   dependencies, domain-level contract). The class body is byte-for-byte
   identical to the original at `service/exceptions.py:32-38`.

2. **D5-3-2b — Update `service/exceptions.py` import, do not re-export.**
   The 6-line class definition (with docstring) is removed. A single new
   import is added at the top of the import block:
   `from backend.shared.domain.exceptions import MemoryHubError`.
   `DomainError` continues to inherit from `MemoryHubError` and every one
   of the 13 domain-error subclasses continues to inherit from
   `DomainError` exactly as before. `service/exceptions.py` does **not**
   add a re-export alias for `MemoryHubError` — the relocation is honest,
   not a compatibility shim.

3. **D5-3-2c — Leave `DomainError` and the 13 domain-error subclasses in
   `service/exceptions.py`.** They are service-level implementation
   contracts and depend on service-layer details; relocating them would
   break the layering that D3.7 calls out ("Infrastructure Error never
   crosses Service boundary" — and conversely, service-specific domain
   errors do not leave `service/`). They are out of scope for D5-3.

4. **D5-3-2d — Update `ingest/exceptions.py` import only.**
   `from backend.service.exceptions import MemoryHubError` →
   `from backend.shared.domain.exceptions import MemoryHubError`.
   The `ImportFrameworkError(MemoryHubError)` inheritance is unchanged,
   all ingest subclasses are unchanged, no behaviour changes.

## Architecture Rationale

The decision to land in `shared/domain/exceptions.py` rather than any other
location is derived from the layering D5-2 already locked, and from the
absence of any conflicting signal in the existing module structure.

### Layered Architecture fit

`backend/src/backend/shared/` currently carries four sub-packages, each
with a clear, distinct purpose:

```
backend/src/backend/shared/
├── domain/           # cross-package shared domain types (values, marker bases)
├── infrastructure/   # technical concerns (config / db / di / logging / uuid)
├── protocols/        # protocol abstractions (empty — no precedent yet)
└── providers/        # provider implementations (empty — no precedent yet)
```

`shared/domain/` already carries:

- `evolution_result.py` — `EvolutionResult` / `TopicEvolutionResult` (D5-2)
- `memory_models.py` — domain models
- `proposal_model.py` — domain models

The `__init__.py` in `shared/domain/` declares the explicit charter
"D1 only: Base classes" — i.e. this sub-package exists to host **base
classes and shared domain types**, which is precisely what `MemoryHubError`
is.

`shared/infrastructure/` is for technical concerns only. Hosting an
exception root there would invert D3.7, which states "Infrastructure
Error never crosses Service boundary" — a shared domain marker is the
opposite of an infrastructure-scoped error.

`shared/` at the top level currently has no files and no precedent for
hosting a domain marker. Creating `shared/exceptions.py` would establish
a third layout with no supporting rationale and contradict the layering
that D5-2 already committed to.

### MemoryHubError's own role

`MemoryHubError` is a cross-package shared type. Its semantics:

- It is a **pure marker**. No state, no behaviour. Its only job is to
  exist as the parent class that lets `except MemoryHubError:` (or its
  subclass discriminants) work.
- It is **shared by service/ and ingest/ simultaneously** — neither is
  its owner.
- It has **no infrastructure dependencies** — no config, no db, no di,
  no logging, no uuid.
- It is a **domain-level contract**: the Entry Layer uses it as the
  discriminator that decides when to translate an exception into a
  protocol-specific error response.

That role is structurally identical to `EvolutionResult` (a cross-package
shared type with no business semantics, consumed by both engine code and
service code, placed in `shared/domain/` by D5-2). D5-3 is applying the
same rule to the parallel case.

### Post-migration hierarchy

After this ADR is implemented, the target hierarchy is:

**Service side:**
```
backend.shared.domain.MemoryHubError
        │
        ▼
backend.service.exceptions.DomainError(MemoryHubError)
        │
        ├── ValidationError
        ├── NotFoundError
        ├── DuplicateError
        ├── DomainIntegrityError
        ├── TransactionError
        ├── ServiceUnavailableError
        ├── ReflectionError
        └── ImportError
            │
            ├── TaskNotFoundError(NotFoundError)
            ├── TaskAlreadyRunningError(DomainIntegrityError)
            └── TaskCancellationError(DomainError)
```

**Ingest side:**
```
backend.shared.domain.MemoryHubError
        │
        ▼
backend.ingest.exceptions.ImportFrameworkError(MemoryHubError)
        │
        ├── AdapterNotFoundError
        ├── ParseError
        └── ValidationError
```

`MemoryHubError` is the single root shared by both trees. This is by
design, not coincidence.

### Alternative locations rejected

| Candidate | Why rejected |
|-----------|-------------|
| `shared/exceptions.py` | `shared/` top level currently has no files; no precedent; contradicts the `shared/domain/` charter that D5-2 already established for the parallel `evolution_result` case. |
| `shared/infrastructure/exceptions.py` | `infrastructure/` is for technical concerns. D3.7 explicitly states "Infrastructure Error never crosses Service boundary". `MemoryHubError` is the opposite — a domain contract consumed by service and ingest — so it does not belong here. |
| `service/exceptions.py` (no change) | Forces ingest/ to depend on service/ for a marker that neither package owns. Contradicts the D5-series intent to relocate cross-package types out of any single business package. |
| `ingest/exceptions.py` (no change) | Symmetric to the above — would force service/ to depend on ingest/. The shared root belongs at the shared layer, not in either sibling. |

## Frozen Status

**NO CONTROLLED DEFROST REQUIRED.**

`MemoryHubError` is a pure marker base. Its relocation does not touch any
frozen architectural fact. Four independent lines of evidence support
this:

1. **No Phase 21.* frozen document references `MemoryHubError`.**
   `grep -rn "MemoryHubError" docs/phase21-*` returns zero matches. The
   Phase 21 freeze scope covers `evolution/` package internals
   (`EvolutionEngine`, `EvolutionService`, `VALID_TRANSITIONS`,
   `EvidencePipelineService`, etc.) — not a marker exception class living
   in `service/exceptions.py:32`.

2. **No frozen architectural fact depends on `MemoryHubError`'s file
   location.** The frozen facts in Phase 21.* are: the evolution call
   chain (`EvidencePipelineService → EvolutionService → EvolutionResult`),
   topic status transitions (`VALID_TRANSITIONS`), historical memory
   immutability, and L2/L3 abstraction formation. `MemoryHubError` does
   not participate in any of these. It is only consulted when an
   exception is *raised* by code in those chains — and the exception
   discrimination logic uses the subclass (`DomainError` and its
   descendants), not `MemoryHubError` itself.

3. **This change relocates the exception base, not its semantics.** The
   class body is identical. `DomainError`'s inheritance is identical. The
   13 domain-error subclasses are byte-for-byte identical. The
   `ImportFrameworkError` inheritance is identical. No `raise` site
   changes. No `except` site changes. No Entry Layer translation logic
   changes (the translator dispatches on the `DomainError` subclass
   tree, not on `MemoryHubError` directly).

4. **D3.7 alignment.** D3.7_Error_Handling_DTO_Models.md states
   "Exception types are version-controlled architecture contracts." This
   change is a relocation of an architecture contract's physical
   location — not a modification of the contract itself. D3.7 explicitly
   anticipates such relocations and treats them as version-controlled
   housekeeping, not contract changes.

This is structurally identical to D5-2, which moved `EvolutionResult`
without a defrost declaration for the same reasons. D5-3 is the parallel
case for `MemoryHubError`.

## Consequences

- **`MemoryHubError` is now a shared domain contract**, physically
  located in the package whose charter is exactly "shared domain types".
  Its dependencies on infrastructure are zero by construction — the file
  imports nothing from `backend.shared.infrastructure.*`.
- **The cross-package shared-type pattern is now consistent.** Both
  `EvolutionResult` (D5-2) and `MemoryHubError` (D5-3) live in
  `shared/domain/` and follow the same relocation rationale. Future
  cross-package shared types have an unambiguous home.
- **No test was modified.** No assertion was added, removed, or changed.
  No test imports `MemoryHubError` directly (verified: zero references
  in `backend/tests/`). The pytest suite is expected to remain green
  because no behaviour changed.
- **`service.exceptions.MemoryHubError` is intentionally not re-exported.**
  Downstream code that did `from backend.service.exceptions import
  MemoryHubError` will break — but `grep` over the entire `backend/`
  tree confirms there are no such callers, so this is a deliberate,
  observable relocation, not a stealth one. If a future caller needs
  the old import path, the relocation gives them a clear, one-line fix.
- **DI container, alembic migrations, engine code, and repository code
  are untouched.** The relocation is scoped to the exception hierarchy
  itself.

## References

- `.hermes/plans/d5-3-investigation-report.md` — arch-laguna investigation
  report (the structural analysis that motivated D5-3).
- `.hermes/plans/d5-3-task-definition.md` v2 — the authorised task
  definition, including §2 (architecture rationale), §3 (frozen status), §4
  (goal and non-goals), §5 (execution steps), §6 (verification
  checklist).
- `docs/05_Implementation/ADR-D5-2-Evolution-Service-Migration.md` —
  the parallel D5-2 ADR. D5-3 is the same relocation pattern applied to
  the parallel cross-package marker exception.
- `docs/05_Implementation/D3.7_Error_Handling_DTO_Models.md` —
  authoritative error-handling architecture contract. D5-3's
  cross-package rule ("Infrastructure Error never crosses Service
  boundary") and exception-as-version-controlled-contract rule apply
  here.
- `.hermes/plans/d5-series-restructure-plan.md` — the D5-series
  restructure plan that frames both D5-2 and D5-3 as parallel
  relocations of cross-package shared types.
- `.hermes/plans/d5-3-execution-report.md` — execution record for this
  ADR (Step 1 / Step 2 / Step 4 outcomes, git diff evidence).

## Implementation

- **HEAD before**: `bc65e96` (D5-2 LOCKED + PUSHED).
- **Step 1 Precheck**: PASS. The investigation-report findings matched
  the live tree exactly:
  - HEAD = `bc65e96` ✓
  - `class MemoryHubError` at exactly one location
    (`service/exceptions.py:32`) ✓
  - `from backend.service.exceptions import MemoryHubError` at exactly
    one location (`ingest/exceptions.py:8`) ✓
  - `from backend.shared.domain.exceptions` at zero locations ✓
  - `backend/src/backend/shared/domain/exceptions.py` did not exist ✓
  - Test code references to `MemoryHubError`: zero ✓
- **Step 2 Implementation**: PASS / LOCKED. The three source-code
  changes match §Decision exactly:
  - `backend/src/backend/shared/domain/exceptions.py` created (21 lines,
    contains only the marker class and the relocation-rationale
    docstring).
  - `backend/src/backend/service/exceptions.py` modified: the 6-line
    class definition (with docstring) was deleted; one new import line
    was added (`from backend.shared.domain.exceptions import
    MemoryHubError`); all 14 remaining classes, all existing imports,
    all docstrings preserved.
  - `backend/src/backend/ingest/exceptions.py` modified: the import on
    line 8 was re-pointed to `backend.shared.domain.exceptions`; the
    `ImportFrameworkError(MemoryHubError)` inheritance is preserved;
    no other lines changed.
- **pytest**: 711 collected / 703 passed / 8 skipped / 0 failed / 0
  errors / 17 warnings. The 17 warnings include
  `PytestUnhandledThreadExceptionWarning` from pre-existing
  background-thread paths (unrelated to this change; pre-existing in
  the D5-2 baseline as well) — recorded for completeness, does not
  constitute a failure.
- **Runtime sanity check**:
  `from backend.shared.domain.exceptions import MemoryHubError;
   from backend.service.exceptions import DomainError;
   from backend.ingest.exceptions import ImportFrameworkError;
   assert issubclass(DomainError, MemoryHubError);
   assert issubclass(ImportFrameworkError, MemoryHubError)`
  passes (both subclasses resolve to the relocated root).
- **Step 3 (optional hardening)**: NOT EXECUTED. Default plan-A per the
  v2 task definition: no `service.exceptions.MemoryHubError` re-export,
  no new test file. This was a conscious non-action, not an oversight.
- **Step 5 (commit / push)**: NOT EXECUTED. Per the v2 task definition
  and per PM dispatch scope, commit and push require a separate
  authorisation. The working tree currently shows the Step 2 source
  changes plus the Step 4 documentation changes described in this ADR;
  Step 5 will produce a single commit covering both once authorised.

## Scope

The Step 2 implementation touched exactly three files, with exactly the
following line deltas:

- **Modified**: `backend/src/backend/service/exceptions.py`
  — net change: −6 / +1 (six lines of class body deleted, one import
  line added).
- **Modified**: `backend/src/backend/ingest/exceptions.py`
  — net change: one import-line target path changed (1-line
  substitution; no surrounding context changed).
- **Created**: `backend/src/backend/shared/domain/exceptions.py`
  — new file, 21 lines (marker class + relocation-rationale
  docstring).

The Step 4 documentation work (this ADR, the D5-2 ADR follow-up entry,
and the execution report) adds three more files, none of which modify
any source code.

**Not modified:**

- `backend/tests/` — no test changed (verified by `git diff
  backend/tests/` returning empty).
- `backend/alembic/` — no migration changed (verified by `git diff
  backend/alembic/` returning empty).
- `backend/src/backend/shared/infrastructure/di/container.py` — DI
  container untouched (verified by `git diff
  backend/src/backend/shared/infrastructure/di/container.py` returning
  empty).
- Any engine code, repository code, or other service file — untouched.
- Any `raise` statement, any `except` statement, any Entry Layer error
  translation logic — untouched.

The Step 4 scope is documentation-only: this ADR, one line appended to
  `ADR-D5-2-Evolution-Service-Migration.md`, and the execution report
  at `.hermes/plans/d5-3-execution-report.md`. No code is touched by
  Step 4.