# D4 Engine Classification Review Report

> **Version**: 1.0
> **Date**: 2026-07-13
> **Phase**: Phase D — Document-Driven Implementation
> **Stage**: D4 — Domain Engine Layer
> **Review Type**: Engine Classification Review
> **Reviewer**: System Architecture Group

---

## Executive Summary

This review classifies every Engine-related term found in D3 Service documents and the D4 Plan.

**Overall Verdict: PASS**

The current D4 Engine Inventory is **architecturally sound**. The apparent "missing Engines" are either:
- Historical references (QueryEngine)
- Internal components (ArchiveEngine, EvidenceEngine)
- Policies/strategies (RankingEngine, TimelineEngine)
- Future considerations (DetailEngine, GraphEngine, SummaryEngine)

No architectural redesign is required.

---

## 1. Classification Table

| Engine | Category | Owner Engine | Reason |
|--------|----------|--------------|--------|
| **EntityEngine** | A - Stable Domain Engine | Independent | Core entity identity and merge analysis |
| **MemoryEngine** | A - Stable Domain Engine | Independent | Memory domain rules and consistency |
| **RelationshipEngine** | A - Stable Domain Engine | Independent | Relationship graph analysis and link validation |
| **ReflectionEngine** | A - Stable Domain Engine | Independent | Reflection algorithms and proposal generation |
| **SearchEngine** | A - Stable Domain Engine | Independent | Search domain algorithms |
| **ProjectionEngine** | A - Stable Domain Engine | Independent | Projection domain algorithms |
| **ArchiveEngine** | B - Engine Component | MemoryEngine | Supports Memory domain, not independent capability |
| **EvidenceEngine** | B - Engine Component | MemoryEngine | Supports Memory domain, not independent capability |
| **QueryEngine** | E - Historical/Legacy | N/A | Referenced in D3 but replaced by SearchEngine + ProjectionEngine |
| **RankingEngine** | C - Engine Policy | SearchEngine/ProjectionEngine | Configurable behavior within Search/Projection |
| **TimelineEngine** | C - Engine Policy | SearchEngine/ProjectionEngine | Configurable behavior within Search/Projection |
| **DetailEngine** | D - Engine Strategy | Future consideration | Warning about responsibility inflation, not yet implemented |
| **GraphEngine** | D - Engine Strategy | Future consideration | Warning about responsibility inflation, not yet implemented |
| **SummaryEngine** | D - Engine Strategy | Future consideration | Warning about responsibility inflation, not yet implemented |

---

## 2. Detailed Classification Analysis

### Category A: Stable Domain Engines

#### EntityEngine
- **Source Documents**: MemoryService, QueryService, ReflectionService, EntityService, D4 Plan
- **Architectural Meaning**: Core entity identity resolution and merge analysis
- **Classification Justification**: Represents independent Domain Capability (Entity identity)
- **D4 Plan Status**: ✅ Included

#### MemoryEngine
- **Source Documents**: MemoryService, QueryService, ReflectionService, EntityService, D4 Plan
- **Architectural Meaning**: Memory domain rules, consistency checks, L0-L4 hierarchy enforcement
- **Classification Justification**: Represents independent Domain Capability (Memory lifecycle)
- **D4 Plan Status**: ✅ Included

#### RelationshipEngine
- **Source Documents**: MemoryService, EntityService, D4 Plan
- **Architectural Meaning**: Relationship graph analysis, link validation, connection inference
- **Classification Justification**: Represents independent Domain Capability (Relationships)
- **D4 Plan Status**: ✅ Included

#### ReflectionEngine
- **Source Documents**: MemoryService, ReflectionService
- **Architectural Meaning**: Reflection algorithms, proposal generation, entity evolution analysis
- **Classification Justification**: Represents independent Domain Capability (Reflection)
- **D4 Plan Status**: ✅ Included (as ReflectionEngine)

#### SearchEngine
- **Source Documents**: QueryService, D4 Plan
- **Architectural Meaning**: Search domain algorithms, relevance ranking, query processing
- **Classification Justification**: Represents independent Domain Capability (Search)
- **D4 Plan Status**: ✅ Included

#### ProjectionEngine
- **Source Documents**: D4 Plan
- **Architectural Meaning**: Projection domain algorithms, read model generation, view assembly
- **Classification Justification**: Represents independent Domain Capability (Projection)
- **D4 Plan Status**: ✅ Included

### Category B: Engine Components

#### ArchiveEngine
- **Source Documents**: MemoryService
- **Architectural Meaning**: Archive capability execution, cognitive compression
- **Classification Justification**: Supports Memory domain but not independent capability
- **Owner**: MemoryEngine (internal component)

#### EvidenceEngine
- **Source Documents**: MemoryService
- **Architectural Meaning**: Evidence chain validation, version creation for Memory corrections
- **Classification Justification**: Supports Memory domain but not independent capability
- **Owner**: MemoryEngine (internal component)

### Category C: Engine Policies

#### RankingEngine
- **Source Documents**: QueryService
- **Architectural Meaning**: Ranking algorithm configuration for search results
- **Classification Justification**: Configurable behavior within Search/Projection
- **Owner**: SearchEngine or ProjectionEngine (policy)

#### TimelineEngine
- **Source Documents**: QueryService
- **Architectural Meaning**: Timeline generation policy for projections
- **Classification Justification**: Configurable behavior within Projection
- **Owner**: ProjectionEngine (policy)

### Category D: Engine Strategies (Future Considerations)

#### DetailEngine
- **Source Documents**: QueryService
- **Architectural Meaning**: Potential future Engine for detailed views
- **Classification Justification**: Warning about responsibility inflation
- **Status**: Not yet implemented, future consideration

#### GraphEngine
- **Source Documents**: QueryService
- **Architectural Meaning**: Potential future Engine for graph operations
- **Classification Justification**: Warning about responsibility inflation
- **Status**: Not yet implemented, future consideration

#### SummaryEngine
- **Source Documents**: QueryService
- **Architectural Meaning**: Potential future Engine for summarization
- **Classification Justification**: Warning about responsibility inflation
- **Status**: Not yet implemented, future consideration

### Category E: Historical/Legacy Names

#### QueryEngine
- **Source Documents**: QueryService, ReflectionService, EntityService
- **Architectural Meaning**: Historical reference to query processing
- **Classification Justification**: Replaced by SearchEngine + ProjectionEngine in D4 design
- **D4 Plan Status**: ❌ Not included (replaced)

---

## 3. Historical Mapping

### QueryEngine Evolution

```
QueryEngine (D3 Historical)
  ↓
SearchEngine + ProjectionEngine (D4 Current)
```

**Rationale**: 
- QueryEngine was a monolithic concept that combined search and projection
- D4 decomposition separates these into distinct Domain Capabilities
- SearchEngine handles retrieval algorithms
- ProjectionEngine handles view assembly

### ArchiveEngine/EvidenceEngine Status

```
ArchiveEngine → MemoryEngine.Component
EvidenceEngine → MemoryEngine.Component
```

**Rationale**:
- These support Memory domain but are not independent capabilities
- They represent internal implementation details of MemoryEngine

---

## 4. D4 Validation

### 4.1 One Domain Capability → One Engine

| Engine | Domain Capability | Status |
|--------|------------------|--------|
| EntityEngine | Entity Identity | ✅ |
| MemoryEngine | Memory Lifecycle | ✅ |
| RelationshipEngine | Relationship Analysis | ✅ |
| ReflectionEngine | Reflection/Evolution | ✅ |
| SearchEngine | Search | ✅ |
| ProjectionEngine | Projection | ✅ |

**Verdict**: ✅ **SATISFIED**

### 4.2 No God Engine

| Engine | Responsibility Scope | Status |
|--------|---------------------|--------|
| EntityEngine | Entity identity only | ✅ |
| MemoryEngine | Memory lifecycle only | ✅ |
| RelationshipEngine | Relationship analysis only | ✅ |
| ReflectionEngine | Reflection only | ✅ |
| SearchEngine | Search only | ✅ |
| ProjectionEngine | Projection only | ✅ |

**Verdict**: ✅ **SATISFIED**

### 4.3 Engine Owns Domain Capability

All Category A Engines own their respective domain capabilities. No Engine owns multiple unrelated capabilities.

**Verdict**: ✅ **SATISFIED**

### 4.4 Service Owns Orchestration

D3 Services coordinate Engines but do not contain domain logic. Service independence principle maintained.

**Verdict**: ✅ **SATISFIED**

### 4.5 Engine Does Not Call Engine

No cross-Engine dependencies detected. All Engine coordination happens at Service layer.

**Verdict**: ✅ **SATISFIED**

---

## 5. Findings

### 5.1 Terminology Issues

| Issue | Severity | Recommendation |
|-------|----------|----------------|
| QueryEngine still referenced in D3 documents | Low | Update D3 documents to reflect D4 terminology |
| Mixed use of "Engine" vs "Component" in D3 | Low | Clarify in D4 Plan |

### 5.2 Documentation Issues

| Issue | Severity | Recommendation |
|-------|----------|----------------|
| D3 documents reference Engines not in D4 Plan | Low | Add classification table to D4 Plan |
| Inconsistent Engine naming conventions | Low | Standardize naming |

### 5.3 Architecture Issues

**No genuine architectural issues found.**

The apparent "missing Engines" are properly classified as:
- Historical references (QueryEngine)
- Internal components (ArchiveEngine, EvidenceEngine)
- Policies/strategies (RankingEngine, TimelineEngine)
- Future considerations (DetailEngine, GraphEngine, SummaryEngine)

---

## 6. Final Verdict

**PASS**

The current D4 Engine Inventory is **architecturally sound** and **ready for implementation**.

### Justification

1. **All Category A Engines** (Stable Domain Engines) are properly represented in the D4 Plan
2. **All other Engine terms** are correctly classified as components, policies, strategies, or historical references
3. **No architectural inconsistencies** exist between D3 Services and D4 Engines
4. **D4 decomposition satisfies** all architectural principles:
   - One Domain Capability → One Engine
   - No God Engine
   - Engine owns Domain Capability
   - Service owns orchestration
   - Engine does not call Engine

### Recommendations

1. **Add classification table** to D4 Plan for clarity
2. **Update D3 documents** to reflect D4 terminology
3. **Proceed with D4 implementation** - no architectural changes required

---

**Review Date**: 2026-07-13  
**Review Status**: PASS  
**Next Step**: Begin individual Engine architecture documents
