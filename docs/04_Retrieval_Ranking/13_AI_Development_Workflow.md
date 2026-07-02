# Personal AI Memory Hub — 13 AI Development Workflow

> **Version**: 1.0
> **Date**: 2026-07-01
> **Phase**: Phase B — Engineering Planning
> **Status**: Draft
> **Author**: System Architecture Group

---

## 1. Purpose

This document defines the **engineering workflow** governing AI participation throughout the complete software development lifecycle for the Personal AI Memory Hub project.

It is **not** a conversation management guide. It is a **project-oriented engineering workflow specification** that applies to all AI-assisted development activities.

This document covers:

* Project lifecycle and state transitions
* Human / AI responsibility matrix
* Discussion → Decision → Design transition
* Design → Implementation transition
* Implementation Readiness criteria
* Engineering Escalation procedures
* Verification vs Human Review
* Verification Report format
* Evidence-Based Verification
* Project State Assessment
* GitHub as the authoritative representation of current Project State
* Project-oriented workflow (not conversation-oriented)
* Stateless AI collaboration through Project State
* Reflection before Knowledge Enrichment
* Knowledge Candidate, Knowledge Admission, Novelty Evaluation
* Knowledge Evolution
* Long-term maintainability

**引用**：11 §12, 11 §13, 12, 13

---

## 2. Project Lifecycle Overview

The project follows a **state-driven lifecycle** rather than a checklist-driven schedule.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Project Lifecycle States                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Design Complete                                                │
│    │                                                            │
│    ▼                                                            │
│  Gate Assessment ──NO──► Blocked (resolve blockers)             │
│    │ YES                                                       │
│    ▼                                                            │
│  Implementation Ready                                           │
│    │                                                            │
│    ▼                                                            │
│  State Assessment ──► Execute Next Milestone                    │
│    │                                                            │
│    ▼                                                            │
│  In Progress                                                    │
│    │                                                            │
│    ▼                                                            │
│  Execution Report ──► Human Decision                            │
│    │                                                            │
│    ▼                                                            │
│  Verification Needed                                            │
│    │                                                            │
│    ▼                                                            │
│  Automated Verification                                         │
│    │                                                            │
│    ▼                                                            │
│  Manual Verification                                            │
│    │                                                            │
│    ▼                                                            │
│  Verified ──► Human Approval ──► Committed                      │
│    │                                                            │
│    ▼                                                            │
│  Design Complete (next milestone)                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 State Definitions

| State | Description | Transition Trigger |
|-------|-------------|-------------------|
| **Design Complete** | Architecture and implementation design approved | Gate assessment initiated |
| **Blocked** | Prerequisites not met; blockers identified | Blocker resolved |
| **Implementation Ready** | Gates pass; resources allocated | State assessment initiated |
| **In Progress** | Active implementation underway | Execution report submitted |
| **Verification Needed** | Implementation complete; verification pending | Verification initiated |
| **Verified** | Automated and manual verification passed | Human approval requested |
| **Committed** | Approved; merged to authoritative state | Next milestone begins |

---

## 3. Human / AI Responsibility Matrix

### 3.1 Core Principle

**Human Decides, AI Executes.**

| Role | Responsibility | Boundary |
|------|---------------|----------|
| **Human** | Define goals, review outcomes, approve merges, assess risks, make architectural decisions, approve knowledge admission | Owns all engineering decisions |
| **AI** | Generate code, run tests, produce reports, update documents, verify compliance, analyze, recommend, enrich | Never silently redefine approved architecture |

### 3.2 Decision Ownership

| Activity | Human | AI |
|----------|-------|-----|
| Define project goals | ✅ | — |
| Approve merge | ✅ | — |
| Assess risk | ✅ | — |
| Make architectural decisions | ✅ | — |
| Generate code | — | ✅ |
| Run tests | — | ✅ |
| Produce reports | — | ✅ |
| Update documents (per human direction) | — | ✅ |
| Verify compliance | — | ✅ |
| Analyze project state | — | ✅ |
| Recommend alternatives | — | ✅ |
| Enrich knowledge (after admission) | — | ✅ |
| Redefine approved architecture | ❌ | ❌ |

### 3.3 Prohibited Actions

The following actions are **prohibited** for AI without explicit human approval:

1. Modifying approved architecture decisions
2. Creating or deleting Knowledge Candidates without novelty evaluation
3. Bypassing verification gates
4. Making decisions that conflict with documented engineering principles
5. Silently rewriting approved documentation

---

## 4. Discussion → Decision → Design Transition

### 4.1 Three-Stage Progression

```
Discussion (Working Memory)
    ↓沉淀为
Decision (Approved)
    ↓文档化为
Design (Implementation Guide)
```

| Stage | Nature | Authority | Persistence |
|-------|--------|-----------|-------------|
| **Discussion** | Exploratory, informal, conversation-bound | Advisory | Ephemeral |
| **Decision** | Formal, reviewed, approved | Binding | Permanent until revised |
| **Design** | Implementation-ready specification | Contract | Living document |

### 4.2 Discussion Phase

During discussion:

* Ideas are explored freely.
* Trade-offs are debated.
* No binding commitment is made.
* AI may propose alternatives and analyze implications.

### 4.3 Decision Phase

A discussion becomes a decision when:

1. The human explicitly approves the direction.
2. The decision is recorded in an approved document or Engineering Register.
3. The decision receives a stable identifier (e.g., ENG-XXX).

### 4.4 Design Phase

A decision becomes design when:

1. The decision is translated into implementation specifications.
2. The design is documented in a Phase B implementation document.
3. The design references the originating decision.

### 4.5 Evidence Requirement

Conversations alone do not constitute decisions. The evidence chain must include:

* **Source**: Where the discussion occurred (conversation, document, or meeting)
* **Decision**: What was decided
* **Approval**: Who approved and when
* **Recording**: Where the decision was documented

---

## 5. Design → Implementation Transition

### 5.1 Gate System

Before any implementation begins, the following gates must pass:

| Gate | Criteria | Responsible |
|------|----------|-------------|
| **Architecture Gate** | Design documents are complete and internally consistent | Architecture review |
| **Engineering Gate** | Dependencies resolved; coding order validated | Engineering assessment |
| **AI Gate** | AI understands the design; no hallucination of requirements | AI compliance check |
| **Human Gate** | Human approves the implementation plan | Human decision |

### 5.2 Implementation Readiness Criteria

An implementation is considered ready when:

1. All design documents referencing the implementation are committed and approved.
2. The relevant Engineering Register decisions have been reviewed.
3. Dependencies (coding order, module boundaries) are validated.
4. Verification criteria are defined.
5. Human approval has been obtained.

### 5.3 Document-First Principle

> **Documents are the operational contract between architecture and implementation.**

| Rule | Description |
|------|-------------|
| Code conforms to documents | Implementation must match design, not the reverse |
| Documents updated before code | Design changes precede implementation changes |
| AI reads documents first | AI never generates code without reading relevant design docs |
| Conversation history is ephemeral | Decisions in chat do not override documents |

---

## 6. Implementation Readiness

### 6.1 Pre-Implementation Checklist

Before starting any implementation task:

1. **Read relevant documents** — All Phase A architecture docs and Phase B implementation docs for the target area.
2. **Check Engineering Register** — Review related ENG decisions for constraints and trade-offs.
3. **Verify coding order** — Confirm dependencies are satisfied (foundation → repository → engine → service → entry → testing).
4. **Assess project state** — Determine current milestone and next expected deliverable.
5. **Define verification criteria** — Specify how success will be measured.

### 6.2 Implementation State Assessment

AI must assess project state before each implementation step:

1. What is the current milestone?
2. What has been completed?
3. What are the prerequisites for the next step?
4. Are there any known blockers?
5. What verification criteria apply?

### 6.3 Implementation Execution

During implementation:

1. Follow documented specifications exactly.
2. Do not infer or fabricate requirements not present in approved documents.
3. Report deviations from design immediately.
4. Produce execution reports documenting what was done.
5. Update documents only when design changes are approved.

---

## 7. Engineering Escalation

### 7.1 Escalation Triggers

Engineering issues must be escalated to human review when:

| Condition | Severity | Action |
|-----------|----------|--------|
| Design ambiguity | Medium | Report to human; wait for clarification |
| Contradictory documents | High | Halt implementation; escalate immediately |
| Architecture violation risk | Critical | Stop; escalate to human |
| AI hallucination detected | High | Correct; document the error |
| Unresolvable technical blocker | Medium | Report alternatives; await human decision |

### 7.2 Escalation Procedure

1. **Identify** the issue and classify severity.
2. **Document** the issue in an execution report.
3. **Propose** alternatives (if applicable).
4. **Wait** for human decision before proceeding.
5. **Record** the human decision in the relevant document.

### 7.3 No Silent Redefinition

AI must never silently redefine approved architecture. If an implementation reveals that the design is impractical:

1. Document the discrepancy.
2. Propose a revised design.
3. Wait for human approval.
4. Only then update the design document.

---

## 8. Verification

### 8.1 Verification vs Human Review

| Activity | Automation | Human Oversight |
|----------|-----------|-----------------|
| Automated verification | ✅ | — |
| Manual verification | — | ✅ |
| Human approval | — | ✅ |

### 8.2 Verification Levels

| Level | Scope | Method | Gate |
|-------|-------|--------|------|
| **Self-Verification** | Code conforms to design | Automated tests, lint, type-check | AI Gate |
| **Architecture Verification** | Design consistency | Cross-document scan, reference check | Architecture review |
| **Testing Verification** | Functional correctness | Test suite, golden dataset | Engineering Gate |
| **Human Review** | Overall quality | Manual inspection, risk assessment | Human Gate |

### 8.3 Evidence-Based Verification

Verification must be **evidence-based**:

1. Every verification claim must reference specific evidence (test output, document section, or approved decision).
2. Claims without evidence are not accepted.
3. Verification reports must include traceability to source documents.

### 8.4 Verification Report Format

When AI produces a verification report, it must include:

| Field | Description |
|-------|-------------|
| **Report ID** | Unique identifier (e.g., VER-001) |
| **Date** | When verification was performed |
| **Scope** | What was verified |
| **Method** | How verification was performed |
| **Evidence** | Supporting evidence (test output, document references) |
| **Findings** | What was found (pass/fail/issues) |
| **Conclusion** | Overall assessment |
| **Recommendation** | Next steps (approve, revise, escalate) |

---

## 9. Project State

### 9.1 GitHub as Authoritative Representation

**GitHub represents the current engineering state of the project.**

| Concept | Representation | Authority |
|---------|---------------|-----------|
| Project State | Git repository (HEAD) | Single Source of Truth |
| Engineering Decisions | 12_Engineering_Register.md | Binding |
| Architecture Design | Phase A documents (01~09) | Reference |
| Implementation Design | Phase B documents (10_1~10_N) | Contract |
| Guidelines | 13_Architecture_Guidelines.md | Normative |
| Roadmap | 11_Implementation_Roadmap.md | Execution Guide |

### 9.2 Project State vs Project Memory

| Aspect | Project State | Project Memory |
|--------|--------------|----------------|
| Scope | Engineering artifacts only | All knowledge (state + long-term memory) |
| Location | GitHub repository | Memory Hub (future) |
| Purpose | Current engineering reference | Long-term knowledge retention |
| Update Frequency | Continuous (per commit) | Periodic (via Reflection) |
| Human Review | Required for all changes | Required for knowledge admission |

A **Project belongs to a Human Memory Domain**; Project State is an **engineering abstraction** within that domain.

### 9.3 Project-Oriented Workflow

The workflow is **project-oriented**, not **conversation-oriented**.

| Characteristic | Project-Oriented | Conversation-Oriented |
|---------------|-----------------|----------------------|
| State representation | GitHub HEAD | Chat history |
| AI context source | Documents + repository | Conversation context |
| Decision persistence | Committed to repository | Lost after conversation ends |
| Knowledge evolution | Via Reflection + Admission | Implicit in conversation |
| Accountability | Documented evidence chain | Unverifiable |

### 9.4 Stateless AI Collaboration

AI collaboration is **stateless** — each session operates from the **current Project State** (GitHub HEAD), not from conversation history.

| Principle | Description |
|-----------|-------------|
| Read current state | AI starts each session by reading GitHub HEAD |
| No conversation dependency | AI does not rely on previous conversation context |
| Document-driven | AI reads relevant documents before acting |
| Evidence-based | AI produces verifiable output tied to source documents |
| State transition | AI reports state changes for human review |

---

## 10. Knowledge Lifecycle

### 10.1 Reflection Before Knowledge Enrichment

**Reflection is the bridge between engineering experience and long-term knowledge.**

Before any knowledge is enriched into the project:

1. **Reflection** — Analyze the engineering experience (what worked, what didn't, what was learned).
2. **Assessment** — Evaluate whether the learning constitutes new knowledge or merely implementation detail.
3. **Candidate Creation** — If new knowledge, create a Knowledge Candidate.
4. **Admission** — Apply Knowledge Admission criteria.
5. **Enrichment** — Only after admission, enrich relevant documents.

> **Not every implementation produces new knowledge.** Many implementations reinforce existing understanding without adding new insights.

### 10.2 Knowledge Candidate

A Knowledge Candidate is a provisional record of potential new knowledge.

| Field | Description |
|-------|-------------|
| **Candidate ID** | Unique identifier (e.g., KC-001) |
| **Source** | Where the insight originated (implementation, verification, review) |
| **Claimed Knowledge** | What the candidate proposes |
| **Evidence** | Supporting evidence |
| **Novelty Assessment** | Is this truly new, or already documented? |
| **Usefulness Assessment** | Will this improve future engineering? |
| **Redundancy Check** | Does overlapping knowledge already exist? |
| **Status** | Pending / Admitted / Rejected |

### 10.3 Knowledge Admission Criteria

A Knowledge Candidate is admitted only when it satisfies **all** criteria:

| Criterion | Requirement |
|-----------|-------------|
| **Novelty** | Not already documented in approved materials |
| **Usefulness** | Improves future engineering practice |
| **Evidence** | Supported by verifiable evidence |
| **Non-redundancy** | No significant overlap with existing knowledge |
| **Human Approval** | Explicitly approved by human |

### 10.4 Knowledge Evolution

> **Knowledge should evolve primarily by refining existing knowledge instead of continuously creating new knowledge.**

| Evolution Type | Description | Example |
|---------------|-------------|---------|
| **Refinement** | Deepening understanding of existing knowledge | Adding implementation examples to a principle |
| **Correction** | Fixing inaccurate or outdated knowledge | Updating a guideline based on new evidence |
| **Integration** | Connecting related knowledge across documents | Cross-referencing principles between documents |
| **Enrichment** | Adding supporting evidence or context | Adding trade-off analysis to a decision |
| **Proliferation** | Creating new knowledge entries | Only when refinement/correction/integration is insufficient |

Proliferation (creating new knowledge entries) is the **least preferred** evolution type. Refinement of existing knowledge is preferred.

### 10.5 Long-Term Maintainability

Knowledge maintainability requires:

1. **Centralized guidelines** — Core principles collected in 13_Architecture_Guidelines.md.
2. **Cross-document references** — Each document references related decisions and principles.
3. **Version tracking** — All documents maintain change records.
4. **Periodic review** — Knowledge is periodically reviewed for accuracy and relevance.
5. **Deprecation process** — Outdated knowledge is marked deprecated, not deleted.

---

## 11. Future Considerations

### 11.1 Multi-Workflow Architecture

Future versions of Memory Hub may introduce **multiple workflow types**, selected according to domain and task context:

| Workflow Type | Scope | Example |
|--------------|-------|---------|
| **Engineering Workflow** (this document) | Project-oriented development | Current scope |
| **Conversation Workflow** | Dialogue-oriented interaction | Chat-based assistance |
| **Research Workflow** | Knowledge discovery and synthesis | Literature review, analysis |
| **Personal Assistant Workflow** | Task automation and scheduling | Calendar, reminders, execution |

This selection mechanism is an **architectural extension point** and is not designed in this document. Future work will define:

* Workflow type identification criteria
* Selection logic (domain-based, task-based, or user-configured)
* Inter-workflow transitions
* Shared state management across workflows

### 11.2 Reflection Integration

As Memory Hub matures, Reflection may:

* Automatically identify Knowledge Candidates from engineering patterns.
* Suggest knowledge refinements based on implementation experience.
* Flag outdated or contradictory knowledge for human review.
* Track knowledge evolution metrics (admission rate, refinement frequency, redundancy reduction).

### 11.3 State Machine Evolution

The project lifecycle state machine may evolve to support:

* Parallel workstreams (multiple milestones in progress).
* Rollback and recovery (reverting committed state).
* Experiment branches (temporary state for exploration).
* Multi-domain projects (projects belonging to multiple human memory domains).

---

## 12. Relationship with Other Documents

| Document | Relationship |
|----------|-------------|
| **11_Implementation_Roadmap** | This document defines the workflow; 11 defines the execution plan within that workflow |
| **12_Engineering_Register** | Decisions in 12 constrain workflow; workflow produces evidence that enriches 12 |
| **13_Architecture_Guidelines** | G-066 (Knowledge Evolution) governs how knowledge in all documents evolves |
| **10_1_Implementation_Service_Layer** | Workflow applies to all Service Layer implementation activities |
| **10_8_Implementation_Testing** | Verification in this workflow uses testing principles from 10_8 |

---

## 13. Document Change Record

| Version | Date | Change Description | Status |
|---------|------|-------------------|--------|
| 1.0 | 2026-07-01 | Initial AI Development Workflow — Project lifecycle, responsibility matrix, state transitions, knowledge lifecycle, future considerations | ✅ Created |

---

## 14. Checklist

### 14.1 P0 — Must Have

| # | Check Item | Status |
|---|------------|--------|
| P0-1 | **Project lifecycle defined** | ✅ Seven states with transitions |
| P0-2 | **Human/AI responsibility matrix** | ✅ Core principle: Human Decides, AI Executes |
| P0-3 | **Discussion → Decision → Design transition** | ✅ Three-stage progression with evidence requirement |
| P0-4 | **Gate system** | ✅ Four gates: Architecture, Engineering, AI, Human |
| P0-5 | **Implementation readiness criteria** | ✅ Five pre-conditions defined |
| P0-6 | **Engineering escalation** | ✅ Five trigger conditions with escalation procedure |
| P0-7 | **Verification framework** | ✅ Evidence-based, four-level verification |
| P0-8 | **GitHub as Project State** | ✅ Distinguished from Project Memory |
| P0-9 | **Stateless AI collaboration** | ✅ Project-oriented, not conversation-oriented |
| P0-10 | **Knowledge lifecycle** | ✅ Reflection → Candidate → Admission → Evolution |
| P0-11 | **Knowledge evolution preference** | ✅ Refinement over proliferation |
| P0-12 | **Prohibited actions** | ✅ Five AI prohibitions listed |

### 14.2 P1 — Recommended

| # | Check Item | Status |
|---|------------|--------|
| P1-1 | **Multi-workflow architecture** | ✅ Extension point documented |
| P1-2 | **Reflection integration** | ✅ Future capability outlined |
| P1-3 | **State machine evolution** | ✅ Parallel workstreams, rollback, experiments |

---

*This document is a Living Workflow Specification. It evolves with the project. Engineering decisions always remain human-owned. AI may analyze, recommend, verify, and enrich, but never silently redefine approved architecture.*
