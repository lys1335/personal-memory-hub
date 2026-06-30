# Personal AI Memory Hub — API Entry Implementation Design

> **Version**: 1.0
> **Date**: 2026-06-30
> **Phase**: Phase B-7 — API Contract + Integration
> **Status**: Draft
> **Author**: System Architecture Group

---

## 1. Design Goals

This document defines the **API Entry Layer** implementation design for the Personal AI Memory Hub.

It serves as the integration point that binds all Services (10_2~10_5) and TaskRuntime (10_6) into a coherent external interface.

### Core Objectives

| # | Objective | Description |
|---|-----------|-------------|
| 1 | **Protocol Adaptation** | Support REST / MCP / CLI / SDK / Agent entry adapters through a unified capability interface |
| 2 | **DTO Transformation** | Convert between external protocols and internal domain models |
| 3 | **Authentication & Authorization** | Validate caller identity and permission checks |
| 4 | **Capability Discovery** | Expose what the Memory Hub can do, without exposing internal architecture |
| 5 | **Request Validation** | Validate input at the Entry layer, reject invalid requests before they reach Services |
| 6 | **Response Shaping** | Shape responses according to protocol requirements (page/stream/cursor) |

### Non-Goals

- Business logic (belongs to Services)
- Engine algorithms (belongs to Engines)
- Persistence (belongs to Repositories)

---

## 2. API Entry Layer Definition

### 2.1 Terminology

> **Phase B Definition**: The term "API Layer" is renamed to **API Entry Layer**.
>
> **Entry Layer Responsibility**: Protocol adaptation, DTO transformation, authentication, capability checks. Entry contains **no business logic**.

### 2.2 Core Principle

> **One Capability, One Implementation; Multiple Entry Adapters.**

Each capability defined by the Services has exactly one implementation. Multiple Entry adapters (REST, MCP, CLI, SDK, Agent) can expose the same capability through different protocols.

```
                    ┌──────────────────────────────────┐
                    │         Entry Adapters            │
                    │  REST  │  MCP  │  CLI  │  SDK  │  │
                    └────┬────┴────┬────┴────┬────┴─────┘
                         │         │         │
                    ┌────▼─────────▼─────────▼────┐
                    │     Unified Capability       │
                    │     Interface (Services)     │
                    └────┬────────────────────────┬┘
                         │                        │
                    ┌────▼────┐            ┌─────▼────┐
                    │Service 1│            │Service 2 │
                    │Memory   │            │Query      │
                    └─────────┘            └──────────┘
```

### 2.3 Entry Layer Architecture

```
Entry Adapter
  ├─ Request Parsing (protocol-specific)
  ├─ Authentication / Authorization
  ├─ Input Validation
  ├─ DTO Conversion (Request)
  └─ Call Service
       └─ Response Shaping (protocol-specific)
```

### 2.4 Forbidden Behaviors

| Forbidden | Reason |
|-----------|--------|
| Entry → Engine (skipping Service) | Violates No Layer Skipping (G-014) |
| Entry → Repository | Violates No Layer Skipping (G-014) |
| Entry contains business logic | Business logic belongs to Services (G-007) |
| Entry knows about Engine internals | Entry only calls Service interfaces |
| Entry modifies domain state directly | Only Services can modify domain state |

---

## 3. Unified Capability Interface

The Entry Layer exposes capabilities, not services. Each capability corresponds to a Service method.

### 3.1 Capability Catalog

| Capability | Service | Methods | Section |
|------------|---------|---------|---------|
| **Evidence Ingestion** | IngestionService | `ingestEvidence()`, `validateEvidence()` | 10_2 |
| **Memory Management** | MemoryService | `captureMemory()`, `correctMemory()`, `archiveMemory()`, `restoreArchivedMemory()` | 10_2 |
| **Memory Retrieval** | QueryService | `retrieveContext()`, `searchMemories()`, `browseMemories()`, `projectView()`, `analyzeStats()` | 10_3 |
| **Reflection** | ReflectionService | `reflect()`, `consolidate()`, `summarize()`, `evaluate()` | 10_4 |
| **Identity Management** | EntityService | `createEntity()`, `resolveEntity()`, `mergeEntities()`, `addAlias()`, `addRelationship()`, `updateCanonicalName()` | 10_5 |
| **Task Operations** | TaskService | `submitTask()`, `getTask()`, `queryRuntimeStatus()`, `retryTask()` | 10_6 |

### 3.2 Capability vs Service Mapping

> **Design Intent**: External callers interact with **Capabilities**, not Services. Services are internal organizational units.

```
External Caller
  └─ Capability: "Ingest Evidence"
       └─ Service: IngestionService.ingestEvidence()
  └─ Capability: "Retrieve Context"
       └─ Service: QueryService.retrieveContext()
  └─ Capability: "Run Reflection"
       └─ Service: ReflectionService.reflect()
  └─ Capability: "Manage Entity"
       └─ Service: EntityService.createEntity() / mergeEntities() / ...
  └─ Capability: "Operate Task"
       └─ Service: TaskService.submitTask() / getTask() / ...
```

---

## 4. API Contract

### 4.1 Core API Methods

All methods are defined by the Services. The Entry Layer adapts them to protocols.

| Method | Service | Input | Output | Description |
|--------|---------|-------|--------|-------------|
| `ingestEvidence()` | IngestionService | Raw Conversation | `ObservationId` | Ingest evidence |
| `correctMemory()` | MemoryService | MemoryId + Correction | `Updated Memory` | Correct memory, preserve original |
| `archiveMemory()` | MemoryService | MemoryId batch | `ArchiveResult` | Archive memories |
| `restoreArchivedMemory()` | MemoryService | ArchiveId | `MemoryId` | Restore from archive |
| `retrieveContext()` | QueryService | Query + Entity | `ContextPackage` | Retrieve context |
| `searchMemories()` | QueryService | Search query + filters | `QueryResult<MemoryNode>` | Semantic search |
| `browseMemories()` | QueryService | Browse criteria + pagination | `QueryResult<MemoryNode>` | Browse with pagination |
| `projectView()` | QueryService | DomainResult + viewSpec | `MemoryView` | Build different views |
| `analyzeStats()` | QueryService | Analytics criteria | `AnalyticsResult` | Statistical analysis |
| `reflect()` | ReflectionService | Reflection scope + policy | `ReflectionExecutionResult` | Execute reflection |
| `consolidate()` | ReflectionService | Consolidation scope | `ReflectionExecutionResult` | Consolidate memories |
| `summarize()` | ReflectionService | Summary scope | `SummarizationResult` | Generate summaries |
| `evaluate()` | ReflectionService | Evaluation criteria | `EvaluationResult` | Evaluate memory quality |
| `createEntity()` | EntityService | Entity profile | `EntityId` | Create new entity |
| `resolveEntity()` | EntityService | Resolution criteria | `ResolvedEntity` | Resolve identity |
| `mergeEntities()` | EntityService | EntityIds to merge | `EntityId` (canonical) | Merge duplicate entities |
| `addAlias()` | EntityService | EntityId + alias | `Void` | Add entity alias |
| `addRelationship()` | EntityService | SourceId + TargetId + type | `RelationshipId` | Add entity relationship |
| `updateCanonicalName()` | EntityService | EntityId + newName | `Void` | Update entity canonical name |
| `submitTask()` | TaskService | Task payload | `TaskId` | Submit a task |
| `getTask()` | TaskService | TaskId | `TaskInfo` | Get task status |
| `queryRuntimeStatus()` | TaskService | — | `RuntimeStatus` | Query runtime health |
| `retryTask()` | TaskService | TaskId | `TaskId` | Retry a failed task |

### 4.2 Command / Query Separation at Entry Layer

> **Guideline G-008**: Command Returns Identity. Query Returns State.

| Operation Type | Entry Layer Behavior | Example |
|----------------|---------------------|---------|
| **Command** (write) | Returns `Id` or `JobId` or `Status` | `POST /memories` → `{ "memoryId": "uuid" }` |
| **Query** (read) | Returns full state / projected view | `GET /memories/search?q=...` → `{ "results": [...], "continuation": "..." }` |

### 4.3 Request/Response Contract

#### 4.3.1 Unified Request Envelope

```json
{
  "requestId": "uuid-v7",
  "capability": "memory.retrieval",
  "version": "1.0",
  "params": {
    "query": "...",
    "entityId": "uuid-v7",
    "filters": { ... }
  },
  "metadata": {
    "caller": "rest|grpc|mcp|cli|sdk|agent",
    "timestamp": "ISO-8601"
  }
}
```

#### 4.3.2 Unified Response Envelope

```json
{
  "requestId": "uuid-v7",
  "status": "success" | "partial_success" | "failed",
  "errorCode": "string (optional)",
  "message": "string (optional)",
  "data": { ... },
  "metadata": {
    "timestamp": "ISO-8601",
    "protocol": "rest|mcp|cli|sdk|agent",
    "pagination": {
      "hasMore": true,
      "continuation": "token"
    }
  }
}
```

#### 4.3.3 Error Response

```json
{
  "requestId": "uuid-v7",
  "status": "failed",
  "errorCode": "VALIDATION_ERROR",
  "message": "Invalid input: entityId is required for retrieveContext",
  "details": {
    "field": "entityId",
    "reason": "required_for_capability"
  }
}
```

### 4.4 Standard Error Codes

| Error Code | HTTP (REST) | Description |
|------------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `AUTHENTICATION_REQUIRED` | 401 | Authentication required |
| `AUTHORIZATION_DENIED` | 403 | Permission denied |
| `CAPABILITY_NOT_FOUND` | 404 | Requested capability does not exist |
| `SERVICE_UNAVAILABLE` | 503 | Backend service unavailable |
| `TASK_EXECUTION_FAILED` | 500 | Task execution failed |
| `DUPLICATE_ENTITY` | 409 | Entity already exists |
| `EVIDENCE_MISSING` | 422 | Required evidence not provided |
| `ARCHIVE_NOT_FOUND` | 404 | Archive not found |
| `JOB_NOT_FOUND` | 404 | Job not found |
| `JOB_CANCELLED` | 410 | Job has been cancelled |

---

## 5. Entry Adapters

### 5.1 Adapter Catalog

| Adapter | Protocol | MVP | V2+ |
|---------|----------|-----|-----|
| **REST Adapter** | HTTP/JSON | ✅ | — |
| **MCP Adapter** | Model Context Protocol | — | Planned |
| **CLI Adapter** | Stdin/Stdout | — | Planned |
| **SDK Adapter** | Language-specific SDK | — | Planned |
| **Agent Adapter** | Agent-native interface | — | Planned |

### 5.2 REST Adapter (MVP)

#### 5.2.1 Endpoint Convention

```
Base Path: /api/v1

Capability-based routing:
  POST   /capabilities/evidence/ingest          → IngestionService.ingestEvidence()
  POST   /capabilities/memory/capture           → MemoryService.captureMemory()
  POST   /capabilities/memory/correct           → MemoryService.correctMemory()
  POST   /capabilities/memory/archive           → MemoryService.archiveMemory()
  POST   /capabilities/memory/restore           → MemoryService.restoreArchivedMemory()
  GET    /capabilities/memory/retrieve          → QueryService.retrieveContext()
  GET    /capabilities/memory/search            → QueryService.searchMemories()
  GET    /capabilities/memory/browse            → QueryService.browseMemories()
  POST   /capabilities/memory/project           → QueryService.projectView()
  GET    /capabilities/memory/analyze           → QueryService.analyzeStats()
  POST   /capabilities/reflection/reflect       → ReflectionService.reflect()
  POST   /capabilities/reflection/consolidate   → ReflectionService.consolidate()
  POST   /capabilities/reflection/summarize     → ReflectionService.summarize()
  POST   /capabilities/reflection/evaluate      → ReflectionService.evaluate()
  POST   /capabilities/entity/create            → EntityService.createEntity()
  POST   /capabilities/entity/resolve           → EntityService.resolveEntity()
  POST   /capabilities/entity/merge             → EntityService.mergeEntities()
  POST   /capabilities/entity/alias             → EntityService.addAlias()
  POST   /capabilities/entity/relationship      → EntityService.addRelationship()
  PUT    /capabilities/entity/canonical-name    → EntityService.updateCanonicalName()
  POST   /capabilities/task/submit              → TaskService.submitTask()
  GET    /capabilities/task/{taskId}            → TaskService.getTask()
  GET    /capabilities/task/status              → TaskService.queryRuntimeStatus()
  POST   /capabilities/task/retry               → TaskService.retryTask()
```

#### 5.2.2 REST Response Format

```json
// Success — Command
{
  "status": "success",
  "data": {
    "memoryId": "uuid-v7"
  }
}

// Success — Query
{
  "status": "success",
  "data": {
    "results": [ ... ],
    "total": 42,
    "page": 1,
    "pageSize": 20
  },
  "metadata": {
    "pagination": {
      "hasMore": true,
      "continuation": "eyJwYWdlIjoyfQ=="
    }
  }
}

// Error
{
  "status": "failed",
  "errorCode": "VALIDATION_ERROR",
  "message": "entityId is required"
}
```

#### 5.2.3 Content Negotiation

| Header | Value | Behavior |
|--------|-------|----------|
| `Accept` | `application/json` | JSON response (default) |
| `Accept` | `text/event-stream` | SSE streaming (V2+) |
| `Accept` | `application/x-ndjson` | NDJSON streaming (V2+) |

#### 5.2.4 Pagination

REST Adapter implements pagination using the QueryService Continuation mechanism (G-003).

```
GET /capabilities/memory/browse?area=ai&entity=proj_001&page=2&pageSize=20&continuation=xyz
```

The Entry Layer translates protocol-level pagination parameters into QueryService's capability-level Continuation.

### 5.3 MCP Adapter (V2+)

MCP Adapter will expose capabilities as MCP tools:

```json
{
  "tools": [
    {
      "name": "memory_hub.ingestEvidence",
      "description": "Ingest raw conversation as evidence",
      "inputSchema": { ... }
    },
    {
      "name": "memory_hub.retrieveContext",
      "description": "Retrieve context for a query",
      "inputSchema": { ... }
    }
  ]
}
```

### 5.4 CLI Adapter (V2+)

CLI Adapter exposes capabilities as subcommands:

```bash
memory-hub evidence ingest --file conversation.json
memory-hub memory search --query "Supabase" --limit 10
memory-hub reflection run --scope daily --entity proj_001
memory-hub entity merge --ids ent_001 ent_002
memory-hub task status --id task_001
```

### 5.5 SDK Adapter (V2+)

SDK Adapter provides typed method calls:

```typescript
// TypeScript SDK example
const hub = new MemoryHubSDK({ apiKey: "..." });

// Command
const obsId = await hub.ingestEvidence(rawConversation);
const memId = await hub.captureMemory(obsId);

// Query
const ctx = await hub.retrieveContext({ query: "...", entityId: "..." });
const results = await hub.searchMemories({ query: "..." });

// Reflection
const result = await hub.reflect({ scope: "daily" });

// Entity
const entityId = await hub.createEntity({ name: "My Project" });
await hub.mergeEntities([ent1, ent2]);

// Task
const taskId = await hub.submitTask({ type: "REFLECTION", payload: {...} });
const status = await hub.getTask(taskId);
```

### 5.6 Agent Adapter (V2+)

Agent Adapter provides a native interface for AI Agents (Hermes, Claude, etc.):

```json
{
  "capabilities": {
    "ingestEvidence": {
      "description": "Submit raw conversation for evidence processing",
      "input": { "conversation": "string" },
      "output": { "observationId": "uuid" }
    },
    "retrieveContext": {
      "description": "Retrieve relevant context for a query",
      "input": { "query": "string", "entityId": "uuid?" },
      "output": { "contextPackage": "object" }
    }
  }
}
```

---

## 6. Authentication & Authorization

### 6.1 Authentication Strategies

| Adapter | Strategy | MVP |
|---------|----------|-----|
| REST | API Key / JWT Bearer | ✅ |
| MCP | Transport-level auth | — |
| CLI | Config file / CLI flag | — |
| SDK | API Key in constructor | — |
| Agent | Internal trust (same process) | — |

### 6.2 Authorization Model

> **Constraint**: Memory Hub is a personal AI platform. The MVP authorization model is simple.

| Role | Permissions |
|------|-------------|
| **Owner** (authenticated user) | Full read/write access to all capabilities |
| **Admin** (future) | Management access, user configuration |
| **Read-Only** (future) | Query capabilities only |

### 6.3 Capability-Level Permission Checks

| Capability Group | Owner | Admin | Read-Only |
|-----------------|-------|-------|-----------|
| Evidence Ingestion | ✅ | ✅ | ❌ |
| Memory Management | ✅ | ✅ | ❌ |
| Memory Retrieval | ✅ | ✅ | ✅ |
| Reflection | ✅ | ✅ | ❌ |
| Identity Management | ✅ | ✅ | ❌ |
| Task Operations | ✅ | ✅ | ✅ (query only) |

---

## 7. Request Validation

### 7.1 Validation Layers

```
Request
  └─ Layer 1: Protocol Validation (Entry)
       ├─ Is the request well-formed JSON?
       ├─ Are required fields present?
       └─ Are field types correct?
  └─ Layer 2: Capability Validation (Entry)
       ├─ Does the capability exist?
       ├─ Does the caller have permission?
       └─ Are business preconditions met?
  └─ Layer 3: Domain Validation (Service)
       ├─ Is the evidence chain complete?
       ├─ Does the Entity exist?
       └─ Are domain invariants satisfied?
```

### 7.2 Validation Rules

| Rule | Layer | Description |
|------|-------|-------------|
| **Required Fields** | Entry | All `NOT NULL` fields in the API contract must be present |
| **UUID Format** | Entry | All UUID fields must be valid UUIDv7 format |
| **Capability Existence** | Entry | Requested capability must exist in the catalog |
| **Permission Check** | Entry | Caller must have permission for the requested capability |
| **Evidence Completeness** | Service | Reflection output must have complete evidence chain (G-022) |
| **Entity Exists** | Service | Entity references must point to existing entities |
| **No Direct Memory Mutation** | Service | Memory correction must preserve original (08 §8.3) |

### 7.3 Validation Error Responses

```json
{
  "status": "failed",
  "errorCode": "VALIDATION_ERROR",
  "message": "Validation failed for capability: memory.retrieval",
  "details": [
    {
      "field": "entityId",
      "reason": "required_for_capability",
      "description": "entityId is required when querying entity-specific memories"
    },
    {
      "field": "query",
      "reason": "min_length_exceeded",
      "description": "Query must be at least 2 characters"
    }
  ]
}
```

---

## 8. DTO Transformation

### 8.1 Transformation Direction

```
External Request (protocol-specific)
  └─ DTO Converter (Entry)
       └─ Domain Command (capability-level)
            └─ Service Method
```

### 8.2 REST DTO Example

```json
// REST Request (external)
{
  "query": "Supabase",
  "entityId": "ent_001",
  "filters": {
    "levels": [1, 2, 3],
    "dateRange": { "from": "2026-01-01" }
  },
  "pagination": {
    "page": 1,
    "pageSize": 20
  }
}

// ↓ Entry Layer transforms to ↓

// Domain Command (internal)
{
  "capability": "searchMemories",
  "params": {
    "query": "Supabase",
    "entityId": "ent_001",
    "filterCriteria": {
      "memoryLevels": [1, 2, 3],
      "dateRange": { "from": "2026-01-01T00:00:00Z" }
    },
    "continuation": {
      "page": 1,
      "pageSize": 20
    }
  }
}
```

### 8.3 Response Transformation

```
Domain Result (Service)
  └─ DTO Converter (Entry)
       └─ External Response (protocol-specific)
```

### 8.4 Transformation Rules

| Rule | Description |
|------|-------------|
| **One Capability, One Internal Model** | Regardless of Entry adapter, the internal domain command is identical |
| **Protocol-Specific Shaping** | REST uses pagination, MCP uses tool schema, CLI uses flags |
| **No Domain Leakage** | Internal domain models must not appear in external responses |
| **Continuation Preservation** | QueryService Continuation is preserved across transformations (G-003) |

---

## 9. Capability Discovery

### 9.1 Discovery Endpoint

```
GET /capabilities
```

Returns the full catalog of available capabilities:

```json
{
  "version": "1.0",
  "capabilities": [
    {
      "name": "evidence.ingest",
      "service": "IngestionService",
      "method": "ingestEvidence",
      "type": "command",
      "description": "Ingest raw conversation as evidence",
      "inputSchema": { "type": "object", "properties": { ... } },
      "outputSchema": { "type": "object", "properties": { "observationId": "string" } }
    },
    {
      "name": "memory.retrieve",
      "service": "QueryService",
      "method": "retrieveContext",
      "type": "query",
      "description": "Retrieve context for a query",
      "inputSchema": { "type": "object", "properties": { ... } },
      "outputSchema": { "type": "object", "properties": { "contextPackage": "object" } }
    }
  ]
}
```

### 9.2 Discovery Purpose

- Allow external callers to discover what the Memory Hub can do
- Provide input/output schemas for integration
- Enable automated tool discovery (MCP, Agent adapters)
- Hide internal service architecture from external callers

### 9.3 Discovery Constraints

| Constraint | Description |
|------------|-------------|
| **Stable API** | Capability names and schemas are stable (G-004) |
| **No Internal Exposure** | Discovery does not expose Service/Engine/Repository internals |
| **Versioned** | Capabilities are versioned; breaking changes require version bump |

---

## 10. Integration Points

### 10.1 Entry → Service Dependency

The Entry Layer calls Services based on capability routing.

| Entry Capability | Service | Method |
|-----------------|---------|--------|
| `evidence.ingest` | IngestionService | `ingestEvidence()` |
| `memory.capture` | MemoryService | `captureMemory()` |
| `memory.correct` | MemoryService | `correctMemory()` |
| `memory.archive` | MemoryService | `archiveMemory()` |
| `memory.restore` | MemoryService | `restoreArchivedMemory()` |
| `memory.retrieve` | QueryService | `retrieveContext()` |
| `memory.search` | QueryService | `searchMemories()` |
| `memory.browse` | QueryService | `browseMemories()` |
| `memory.project` | QueryService | `projectView()` |
| `memory.analyze` | QueryService | `analyzeStats()` |
| `reflection.run` | ReflectionService | `reflect()` |
| `reflection.consolidate` | ReflectionService | `consolidate()` |
| `reflection.summarize` | ReflectionService | `summarize()` |
| `reflection.evaluate` | ReflectionService | `evaluate()` |
| `entity.create` | EntityService | `createEntity()` |
| `entity.resolve` | EntityService | `resolveEntity()` |
| `entity.merge` | EntityService | `mergeEntities()` |
| `entity.alias` | EntityService | `addAlias()` |
| `entity.relationship` | EntityService | `addRelationship()` |
| `entity.canonical-name` | EntityService | `updateCanonicalName()` |
| `task.submit` | TaskService | `submitTask()` |
| `task.get` | TaskService | `getTask()` |
| `task.status` | TaskService | `queryRuntimeStatus()` |
| `task.retry` | TaskService | `retryTask()` |

### 10.2 Service Independence Compliance

> **Guideline G-005**: Services do not call other Services.

The Entry Layer respects this constraint. It calls Services directly, and Services coordinate through Shared Domain Engines.

```
Entry Layer (calls Services directly)
  ├── IngestionService
  ├── MemoryService
  ├── QueryService
  ├── ReflectionService
  ├── EntityService
  └─ TaskService

Services (call Engines, not other Services)
  ├── IngestionService → ScoringEngine
  ├── MemoryService → MemoryEngine
  ├── QueryService → RetrievalEngine
  ├── ReflectionService → ReflectionEngine, MemoryEngine, EntityEngine
  ├── EntityService → EntityEngine, EvidenceEngine, RelationshipEngine
  └─ TaskService → TaskRuntime
```

### 10.3 Command/Query Separation Compliance

> **Guideline G-008**: Command Returns Identity. Query Returns State.

| Category | Capabilities | Returns |
|----------|-------------|---------|
| **Commands** (write) | ingestEvidence, captureMemory, correctMemory, archiveMemory, restoreArchivedMemory, reflect, consolidate, summarize, evaluate, createEntity, resolveEntity, mergeEntities, addAlias, addRelationship, updateCanonicalName, submitTask | `Id` / `JobId` / `Status` |
| **Queries** (read) | retrieveContext, searchMemories, browseMemories, projectView, analyzeStats, getTask, queryRuntimeStatus | `DomainResult` / `State` |

### 10.4 Memory Immutability Enforcement

> **Implementation Architecture §8.3**: Memory is immutable once created.

The Entry Layer enforces this constraint:

| Forbidden at Entry | Allowed at Entry |
|--------------------|------------------|
| `updateMemory(id, data)` | `correctMemory(id, correction)` |
| `deleteMemory(id)` | `archiveMemory(id)` |
| `patchMemory(id, fields)` | `restoreArchivedMemory(archiveId)` |

The Entry Layer rejects any request that attempts direct memory mutation, redirecting to the appropriate capability.

---

## 11. Streaming & Long-Running Operations

### 11.1 Streaming Support

For long-running queries or large context packages, the Entry Layer supports streaming.

| Adapter | Streaming Mechanism | Status |
|---------|---------------------|--------|
| REST | SSE (Server-Sent Events) | V2+ |
| REST | NDJSON | V2+ |
| MCP | Native streaming | V2+ |
| SDK | Async iterator | V2+ |

### 11.2 Long-Running Task Tracking

When a capability triggers a long-running operation (e.g., bulk reflection), the Entry Layer:

1. Submits a Task via TaskService
2. Returns the `taskId` immediately
3. Caller polls `GET /capabilities/task/{taskId}` for status

```
POST /capabilities/reflection/reflect
→ { "taskId": "task_001", "status": "accepted" }

GET /capabilities/task/task_001
→ { "status": "running", "progress": 0.5 }

GET /capabilities/task/task_001
→ { "status": "completed", "result": { ... } }
```

---

## 12. Observability at Entry Layer

### 12.1 Request Tracing

Every request entering the Entry Layer receives a `traceId` that propagates through the entire call chain.

```json
{
  "requestId": "req_001",
  "traceId": "trace_001",
  "capability": "memory.search",
  "duration_ms": 45,
  "status": "success"
}
```

### 12.2 Metrics

The Entry Layer exposes:

| Metric | Description |
|--------|-------------|
| `request_count` | Total requests per capability |
| `response_time_ms` | Latency per capability |
| `error_rate` | Error rate per capability |
| `validation_failures` | Count of validation failures |
| `authentication_failures` | Count of auth failures |

### 12.3 Structured Logging

```json
{
  "timestamp": "2026-06-30T12:00:00Z",
  "level": "info",
  "component": "entry.rest",
  "traceId": "trace_001",
  "capability": "memory.search",
  "method": "searchMemories",
  "duration_ms": 45,
  "status": "success",
  "caller": "rest"
}
```

---

## 13. Service Collaboration Matrix (Entry Perspective)

### 13.1 Entry → All Services

| Caller | Callee | Allowed | Pattern | Reason |
|--------|--------|---------|---------|--------|
| REST Entry | IngestionService | ✅ | Direct call | Evidence ingestion entry point |
| REST Entry | MemoryService | ✅ | Direct call | Memory management entry point |
| REST Entry | QueryService | ✅ | Direct call | Memory retrieval entry point |
| REST Entry | ReflectionService | ✅ | Direct call | Reflection orchestration entry point |
| REST Entry | EntityService | ✅ | Direct call | Identity management entry point |
| REST Entry | TaskService | ✅ | Direct call | Task operations entry point |
| MCP Entry | All Services | ✅ | Via capability router | MCP tool dispatch |
| CLI Entry | All Services | ✅ | Via capability router | CLI command dispatch |
| SDK Entry | All Services | ✅ | Typed method calls | SDK method dispatch |
| Agent Entry | All Services | ✅ | Via capability router | Agent tool dispatch |

### 13.2 Entry Layer Position in Architecture

```
┌─────────────────────────────────────────────┐
│              External Callers                │
│   (Mobile / Web / Telegram / Claude / ...)   │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│           API Entry Layer                    │
│  ┌──────┬──────┬──────┬──────┬──────┐      │
│  │ REST │ MCP  │ CLI  │ SDK  │Agent │      │
│  └──────┴──────┴──────┴──────┴──────┘      │
│                                             │
│  Auth │ Validation │ DTO │ Routing         │
└────────┬───────────┬──────────┬────────────┘
         │           │          │
┌────────▼───────────▼──────────▼────────────┐
│           Service Layer                     │
│  ┌──────┬──────┬──────┬──────┬──────┐     │
│  │Ingest│Memory │ Query │Reflect│Entity│     │
│  └──────┴──────┴──────┴──────┴──────┘     │
└────────────────┬──────────────────────────┘
                 │
┌────────────────▼──────────────────────────┐
│           Engine Layer                     │
│  ┌──────┬──────┬──────┬──────┬──────┐     │
│  │Score │MemEng│RetrEv│ReflEv│EntEv │     │
│  └──────┴──────┴──────┴──────┴──────┘     │
└────────────────┬──────────────────────────┘
                 │
┌────────────────▼──────────────────────────┐
│        TaskRuntime (Infrastructure)        │
└────────────────┬──────────────────────────┘
                 │
┌────────────────▼──────────────────────────┐
│        Repository Layer                    │
└────────────────┬──────────────────────────┘
                 │
┌────────────────▼──────────────────────────┐
│           Database (Supabase)              │
└────────────────────────────────────────────┘
```

---

## 14. Checklist

### 14.1 P0 — Must Complete

| # | Check Item | Status |
|---|------------|--------|
| P0-1 | **Entry → Service only, no layer skipping** | ✅ Defined |
| P0-2 | **One Capability, One Implementation** | ✅ Enforced |
| P0-3 | **Multiple Entry Adapters supported** | ✅ REST (MVP), MCP/CLI/SDK/Agent (V2+) |
| P0-4 | **Command / Query Separation** | ✅ G-008 enforced at Entry |
| P0-5 | **Memory Immutability** | ✅ No update/delete, only correct/archive |
| P0-6 | **Request Validation** | ✅ Three-layer validation defined |
| P0-7 | **Capability Discovery** | ✅ GET /capabilities endpoint |
| P0-8 | **Standard Error Codes** | ✅ 11 error codes defined |
| P0-9 | **Service Independence Preserved** | ✅ Entry calls Services, Services don't call each other |
| P0-10 | **Consumer-Agnostic Interface** | ✅ G-003: Entry adapts, Capability is stable |

### 14.2 P1 — Recommended

| # | Check Item | Status |
|---|------------|--------|
| P1-1 | **Structured Logging** | ✅ TraceId propagation |
| P1-2 | **Metrics Exposure** | ✅ Request count, latency, error rate |
| P1-3 | **Streaming Support** | ✅ SSE/NDJSON (V2+) |
| P1-4 | **Pagination via Continuation** | ✅ QueryService Continuation preserved |
| P1-5 | **DTO Transformation Tests** | ✅ Recommended |

### 14.3 P2 — Future Evolution

| # | Check Item | Status |
|---|------------|--------|
| P2-1 | **Rate Limiting** | Potential |
| P2-2 | **GraphQL Adapter** | Potential |
| P2-3 | **WebSocket Adapter** | Potential |
| P2-4 | **OpenAPI/Swagger Auto-Generation** | Potential |

---

## 15. Decision Summary

| # | Decision | Description | Source |
|---|----------|-------------|--------|
| 1 | **API Entry Layer Terminology** | Renamed from "API Layer" to "API Entry Layer" — Entry is protocol adaptation, not business logic | 08 §8.1 |
| 2 | **One Capability, One Implementation** | Each capability has exactly one Service implementation | G-001 |
| 3 | **Multiple Entry Adapters** | REST/MCP/CLI/SDK/Agent all adapt to the same capability interface | 08 §8.1 |
| 4 | **Capability Routing** | External callers interact with Capabilities, not Services | 10_7 §3 |
| 5 | **Command / Query Separation** | Command returns Id, Query returns State | G-008 |
| 6 | **Memory Immutability** | No update/delete; only correct/archive | 08 §8.3 |
| 7 | **Unified Request/Response Envelope** | Standard envelope with requestId, status, data, metadata | 10_7 §4.3 |
| 8 | **Validation at Entry Layer** | Three-layer validation: Protocol → Capability → Domain | 10_7 §7 |
| 9 | **DTO Transformation** | Protocol-specific → Domain Command (Entry responsibility) | 10_7 §8 |
| 10 | **Capability Discovery** | GET /capabilities exposes the full catalog | 10_7 §9 |
| 11 | **Service Independence at Entry** | Entry calls Services directly; Services never call each other | G-005 |
| 12 | **Authentication per Adapter** | REST=JWT/APIKey, CLI=config, Agent=internal trust | 10_7 §6.1 |
| 13 | **Streaming via Continuation** | QueryService Continuation preserved across protocol boundaries | G-003 |
| 14 | **Long-Running Task Tracking** | Submit → Poll → Complete pattern via TaskService | 10_7 §11 |
| 15 | **Observability** | TraceId, metrics, structured logging at Entry | 10_7 §12 |
| 16 | **REST MVP** | Only REST adapter implemented in MVP; others deferred to V2+ | 10_7 §5.1 |
| 17 | **Error Code Standardization** | 11 standard error codes across all adapters | 10_7 §4.4 |
| 18 | **No Internal Architecture Exposure** | Capability discovery hides Service/Engine/Repository internals | 10_7 §9.3 |

---

## 16. Backport Updates

Completing 10_7 requires updating the following documents:

| Document | Update Content |
|----------|---------------|
| **08_Implementation_Architecture** | §8 API Design — align terminology (API Entry Layer), add capability catalog reference |
| **10_1_Implementation_Service_Layer** | §10 MVP Implementation Order — confirm Phase B-7 position |
| **13_Architecture_Guidelines** | Add G-050~G-055 (Entry Layer Guidelines) |
| **12_Architecture_Decisions** | Add ADR for API Entry Layer principles |

---

## 17. Relationship with Other Documents

| Document | Reference Relationship |
|----------|----------------------|
| **01** | Memory types → Capability classification |
| **06** | Runtime Architecture → Entry Layer is the Runtime's external face |
| **07** | Boundary Review → Entry Layer enforces P1-P9 constraints (no direct memory mutation, no Agent inside Hub) |
| **08** | Implementation Architecture → API Entry Layer definition, API Contract, Memory Immutability |
| **09** | Database Physical Design → Entry Layer never touches tables directly |
| **10_1** | Service Layer Overview → Entry Layer calls Services defined in 10_1 |
| **10_2** | MemoryService → Entry Layer exposes MemoryService capabilities |
| **10_3** | QueryService → Entry Layer exposes QueryService capabilities, preserves Continuation |
| **10_4** | ReflectionService → Entry Layer exposes ReflectionService capabilities |
| **10_5** | EntityService → Entry Layer exposes EntityService capabilities |
| **10_6** | TaskRuntime → Entry Layer exposes TaskService capabilities, tracks long-running tasks |
| **13** | Architecture Guidelines → Entry Layer enforces G-001~G-049 |

---

## Appendix A: Terminology

| Term | Description | Source |
|------|-------------|--------|
| Capability | External-facing unit of functionality, mapped to a Service method | 10_7 |
| Entry Adapter | Protocol-specific implementation (REST/MCP/CLI/SDK/Agent) | 08 §8.1 |
| Domain Command | Internal representation after DTO transformation | 10_7 §8 |
| Continuation | QueryService-defined pagination/state transfer mechanism | G-003 |
| Unified Envelope | Standard request/response wrapper across all adapters | 10_7 §4.3 |

---

## Appendix B: Document Change Record

| Version | Date | Change Description | Status |
|---------|------|-------------------|--------|
| 1.0 | 2026-06-30 | 初始版本 — API Entry Layer design, capability catalog, adapter definitions, validation, DTO transformation, integration compliance | ✅ Confirmed |
| 1.1 | 2026-06-30 | Phase B-7 修订：(1) 回溯更新 08_Implementation_Architecture §8.1（添加 10_7 引用）(2) 回溯更新 10_1 Decision Summary 补充 39~41 (3) 回溯更新 13_Architecture_Guidelines 新增 G-050~G-055 (4) 回溯更新 INDEX.md 标记 10_7 完成 | ✅ Confirmed |

---

*This document records only design decisions reached by consensus. Items not covered are out of scope.*

*This document is the Phase B-7 API Contract + Integration design. All subsequent documents reference this document for API Entry Layer conventions.*
