# Personal Memory Hub

A document-driven architecture project for building a long-term memory system for personal AI assistants.

The goal of Personal Memory Hub is to provide persistent, structured, explainable, and evolvable memory that can survive model changes, session resets, and application migrations.

---

# Vision

Most AI assistants today are stateless.

Even when memory exists, it is often:

* Opaque
* Difficult to inspect
* Difficult to migrate
* Tightly coupled to a specific model or platform

Personal Memory Hub aims to build a user-owned memory layer that remains independent from any particular LLM, agent framework, or application.

The long-term objective is:

> Build a personal memory infrastructure that can serve as the memory core of a Personal AI Platform.

---

# Core Principles

## Memory Before Agent

Agents can be replaced.

Memory should persist.

The memory layer is treated as a first-class system rather than a side feature of an AI agent.

---

## Evidence-Based Memory

Important memories should not be stored solely because an LLM generated them.

Every memory should have traceable evidence and promotion rules.

---

## Human Review First

Users must be able to inspect, review, correct, archive, and delete memories.

The system should remain understandable and controllable.

---

## Structured Before LLM

The platform prioritizes structured entities, relationships, observations, and evidence before relying on LLM reasoning.

---

## Local First

The architecture is designed primarily for personal deployment using local or self-hosted components, with optional cloud integration.

---

# Architecture Direction

Current architecture direction:

```text
User
  │
  ▼
Open WebUI / Hermes Desktop
  │
  ▼
Memory Engine
  │
  ├── Context Builder
  ├── Retrieval Layer
  ├── Reflection Engine
  ├── Candidate Promotion
  └── Memory Lifecycle
  │
  ▼
Memory Hub Database
  │
  ├── Entity Graph
  ├── Memory Store
  ├── Evidence Store
  ├── Reflection Records
  └── Archive Layer
```

Planned deployment technologies include:

* Open WebUI
* Hermes Desktop
* Ollama / Local Models
* Chroma
* Supabase
* MCP Ecosystem
* Google Cloud Storage (optional)

The architecture remains implementation-independent and may evolve over time.

---

# Documentation

Main documentation index:

```text
docs/INDEX.md
```

Current completed design documents:

* Memory Hub Foundation
* Memory Engine & Context Builder
* Entity & Memory Graph
* Schema / Archive / Reflect
* Memory Lifecycle & Reflection Engine
* Runtime Architecture
* Boundary Review
* Implementation Architecture
* Database Physical Design

---

# Development Status

## Phase A - Foundation Design

Completed

* Vision
* Architecture
* Data Model
* Lifecycle
* Runtime
* Boundary Definition
* Physical Database Design

## Phase B - Implementation Design

Planned

* Service Layer
* Ingestion Pipeline
* Runtime Flow
* Reflection Engine
* Task System
* Query System
* Consistency Engine
* API Contract
* Migration Strategy
* Orchestration Layer

## Phase C - Review

Planned

* Consistency Review
* Architecture Review
* Implementation Review

## Phase D - MVP Development

Planned

* Initial implementation
* Local deployment
* End-to-end validation

---

# Project Status

This repository currently focuses on architecture and design documentation.

Implementation has not started yet.

The project follows a document-first approach:

```text
Vision
  ↓
Architecture
  ↓
Data Model
  ↓
Implementation Design
  ↓
Review
  ↓
MVP Development
```

---

# License

License selection is deferred until the architecture and MVP implementation are sufficiently stable.
