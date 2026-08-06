# Personal Memory Hub — Architecture Update Summary

> **Version**: 1.0
> **Date**: 2026-08-05
> **Type**: Architecture Documentation Update
> **Status**: ✅ Complete
> **Author**: System Architecture Group

---

## 1. Update Overview

本次架构更新正式引入 **EvidenceEvolution Engine**，将原 ReflectionEngine 中的 Information Extraction 职责拆分出来。

**核心变更**：
- 新增 EvidenceEvolution Engine（Information Extraction）
- Reflection Engine 职责收窄为 Reasoning
- 明确 Pipeline 三阶段：EvidenceEvolution → Reflection → Approval
- 支持多级演化 L1→L2→L3→L4

---

## 2. Documents Created

### 2.1 新增文档

| 文件名 | 类型 | 大小 | 说明 |
|--------|------|------|------|
| `D4.2g_EvidenceEvolutionEngine_Architecture.md` | 新架构定义 | 17,392 bytes | EvidenceEvolution Engine 完整架构规范 |
| `D4.2d_ReflectionEngine_Architecture_v1.1.md` | 更新架构定义 | 10,019 bytes | ReflectionEngine 职责收窄后的新定义 |
| `ADR-EvidenceEvolution-Split.md` | ADR | 11,447 bytes | 架构决策记录：拆分 EvidenceEvolution |

### 2.2 修改文档

| 文件名 | 修改内容 |
|--------|----------|
| `06_Runtime_Architecture.md` | 新增 EvidenceEvolution Engine 定义；更新 Engine 清单；更新持久化边界说明 |
| `05_MemoryLifecycle_ReflectionEngine.md` | 更新 14.4/14.5 章节；明确 Pipeline 三阶段持久化 |

---

## 3. Architecture Changes

### 3.1 New Pipeline

```
Evidence (L1)
    ↓
EvidenceEvolution Engine (Information Extraction)
    ↓
Candidate (source_level=1)
    ↓
Reflection Engine (Reasoning)
    ↓
Proposal (target_level=2)
    ↓
Approval (Service Method)
    ↓
MemoryNode (L2 Pattern)
    ↓
EvidenceEvolution Engine (L2 as input)
    ↓
Candidate (source_level=2)
    ↓
Reflection Engine
    ↓
Proposal (target_level=3)
    ↓
Approval
    ↓
MemoryNode (L3 Belief)
```

### 3.2 Engine Responsibilities

| Engine | Capability | Input | Output | LLM |
|--------|-----------|-------|--------|-----|
| EvidenceEvolution | Information Extraction | Evidence/MemoryNode | Candidate | Yes (extraction) |
| Reflection | Reasoning | Candidate | Proposal | No (rule-based) |
| Approval | Memory Commit | Proposal | MemoryNode | No |

### 3.3 Key Distinctions

| Aspect | EvidenceEvolution | Reflection |
|--------|-------------------|------------|
| **Question** | What is in this evidence? | What should we do? |
| **Output** | Structured Candidate | Decision (Create/Refine/Split/Reject) |
| **Persistence** | Candidate saved | Proposal saved |
| **LLM Role** | Extraction | None (rule-based) |

---

## 4. Data Model Changes

### 4.1 No Schema Changes

所有现有表保持不变：
- `candidates` — 已有 `source_level` 字段
- `proposals` — 已有 `source_level`, `target_level` 字段
- `memory_nodes` — 已有 `level` 字段

### 4.2 Candidate Definition Update

**Before**:
- Candidate = Reflection working object
- Created manually via scripts

**After**:
- Candidate = EvidenceEvolution output
- Created automatically by EvidenceEvolution Engine
- `source_level` indicates evolution origin

### 4.3 Proposal Definition Update

**Before**:
- Proposal = Reflection output
- source_level not consistently propagated

**After**:
- Proposal = Reasoning output
- `source_level` correctly propagated from Candidate
- `target_level = source_level + 1` (for Create/Strengthen)

---

## 5. Documentation Alignment

### 5.1 Alignment with Target Architecture

| Target | Current Docs | Status |
|--------|-------------|--------|
| EvidenceEvolution Engine exists | D4.2g created | ✅ |
| Reflection Engine narrowed | D4.2d v1.1 updated | ✅ |
| Approval as separate stage | 06_Runtime updated | ✅ |
| Multi-level evolution supported | source_level propagation defined | ✅ |
| Candidate = Reflection Working Object | Defined in all docs | ✅ |
| Fact as internal artifact | Explicitly stated | ✅ |

### 5.2 Implementation Notes

**Current State**:
- EvidenceEvolution logic exists in ReflectionEngine._extract_facts()
- Manual scripts (create_candidates_batch.py) required
- source_level propagation partially working

**Migration Path**:
1. Create EvidenceEvolutionEngine class
2. Move extraction logic
3. Update ReflectionService orchestration
4. Deprecate manual scripts

---

## 6. Files Changed Summary

### 6.1 New Files (3)

```
docs/05_Implementation/D4.2g_EvidenceEvolutionEngine_Architecture.md
docs/05_Implementation/D4.2d_ReflectionEngine_Architecture_v1.1.md
docs/05_Implementation/ADR-EvidenceEvolution-Split.md
```

### 6.2 Modified Files (2)

```
docs/01_Architecture/06_Runtime_Architecture.md
docs/03_Memory_System/05_MemoryLifecycle_ReflectionEngine.md
```

---

## 7. Verification Checklist

### 7.1 Documentation Completeness

- [x] EvidenceEvolution Engine architecture defined
- [x] Reflection Engine scope narrowed
- [x] Approval stage documented
- [x] Multi-level evolution explained
- [x] Data model impact assessed
- [x] Migration plan outlined
- [x] ADR created for decision record

### 7.2 Consistency Checks

- [x] No code changes made
- [x] No database changes made
- [x] No test changes made
- [x] No config changes made
- [x] All docs use consistent terminology
- [x] Pipeline flow consistent across docs

---

## 8. Next Steps

### 8.1 Implementation Phase (Future)

1. Create `EvidenceEvolutionEngine` class
2. Move `_extract_facts()` logic
3. Update `ReflectionService` orchestration
4. Add proper input/output types
5. Write unit tests
6. Deprecate manual scripts

### 8.2 Testing Phase (Future)

1. End-to-end pipeline testing
2. Multi-level evolution testing (L1→L2→L3)
3. Performance testing
4. Regression testing

---

## 9. Conclusion

本次架构更新完成以下目标：

1. **正式引入 EvidenceEvolution Engine** — 作为独立认知阶段
2. **收窄 Reflection Engine 职责** — 专注于 Reasoning
3. **明确 Pipeline 三阶段** — EvidenceEvolution → Reflection → Approval
4. **支持多级演化** — L1→L2→L3→L4 贯通
5. **保持文档一致性** — 所有架构文档对齐

**无代码修改、无数据库变更、无测试变更。**

---

## 10. Revision History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | 2026-08-05 | 初始架构更新 | ✅ Complete |
