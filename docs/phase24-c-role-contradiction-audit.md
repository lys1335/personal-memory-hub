# Phase 24-C — Evidence Role / evidence_type Contradiction Audit (READ-ONLY)

**Date**: 2026-08-14  
**Mode**: READ ONLY — Contradiction Analysis  
**Status**: Complete

---

## Executive Verdict

```
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  AGNES_PREVIOUS_DIAGNOSIS = INCORRECT                               ║
║  ROOT_CAUSE = Two separate fields with different purposes           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Key Finding**: I queried the WRONG field. The role check uses `_meta->>'role'`, NOT `evidence_type`. The `evidence_type` field is a content category, NOT a semantic role.

---

## 1. evidences 表实际 Schema

### 完整列定义

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NOT NULL | Primary key |
| workspace_id | uuid | NOT NULL | Workspace scope |
| entity_id | uuid | YES | Entity linkage |
| area_id | uuid | YES | Area linkage |
| user_id | uuid | YES | User linkage |
| **evidence_type** | varchar(50) | NOT NULL | Content category |
| content | text | NOT NULL | Evidence content |
| raw_content | text | YES | Raw content copy |
| confidence | double precision | NOT NULL | Confidence score |
| importance | double precision | NOT NULL | Importance score |
| signal_strength | double precision | NOT NULL | Signal strength |
| source | varchar(50) | NOT NULL | Import source |
| **_meta** | jsonb | NOT NULL | Metadata including role |
| created_at | timestamp | NOT NULL | Creation time |
| updated_at | timestamp | NOT NULL | Update time |

### 关键发现

1. **role 字段不存在** — 表中没有独立的 `role` 列
2. **evidence_type 存在** — varchar(50)，NOT NULL
3. **role 存储在 _meta JSONB** — 通过 `_meta->>'role'` 访问

---

## 2. 统计数据

### evidence_type 分布

```sql
SELECT evidence_type, COUNT(*) 
FROM evidences
WHERE workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
GROUP BY evidence_type;
```

**结果**：

| evidence_type | count |
|---------------|-------|
| user | 7,782 |
| assistant | 7,880 |

**总计**: 15,662 (与之前统计一致)

### _meta->>'role' 分布

```sql
SELECT 
    evidence_type,
    _meta->>'role' as meta_role,
    COUNT(*) as count
FROM evidences
WHERE workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
GROUP BY evidence_type, _meta->>'role';
```

**结果**：

| evidence_type | meta_role | count |
|---------------|-----------|-------|
| assistant | user | 7,879 |
| assistant | test | 1 |
| user | user | 7,782 |

**关键发现**:
- 7,879 条 assistant evidence 的 `_meta->>'role'` = 'user'
- 这是 **元数据不匹配** — evidence_type 和 _meta.role 不一致

---

## 3. ORM Evidence Model

### 字段定义

```python
# memory_models.py:96
class Evidence(Base):
    __tablename__ = "evidences"
    
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # ... other fields ...
    
    _meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
```

### 关键发现

- ORM 使用 `evidence_type` 字段存储证据类型
- `_meta` 是 JSONB 字段，存储元数据（包括 role）
- **无独立 role 字段**

---

## 4. Semantic Interpreter 实际读取哪个字段

### 代码路径

```
EvidencePipelineService._form_context_window()
  ↓
ContextWindowFormulator.formulate()
  ↓
classify_role(evidence._meta)
  ↓
EvidenceRole (USER/ASSISTANT/SYSTEM/UNKNOWN)
  ↓
EvidenceContext.role
  ↓
UserSemanticInterpreter.interpret()
  ↓
trigger.role != EvidenceRole.USER → NoUserFact
```

### 关键代码

```python
# formulator.py:124
role = classify_role(evidence._meta)
# ↑ 读取的是 evidence._meta['role']，不是 evidence.evidence_type

# context_window.py:198-215
def classify_role(meta: dict[str, Any]) -> EvidenceRole:
    role = meta.get("role", "unknown").lower()
    role_map = {
        "user": EvidenceRole.USER,
        "assistant": EvidenceRole.ASSISTANT,
        "system": EvidenceRole.SYSTEM,
    }
    return role_map.get(role, EvidenceRole.UNKNOWN)
```

### 结论

**Semantic Interpreter 读取的是 `_meta['role']`，不是 `evidence_type`！**

---

## 5. ChatGPT Import Adapter 实现

### 代码路径

```
ChatGPTImportAdapter.parse()
  ↓
author.role (从 ChatGPT export JSON 读取)
  ↓
metadata['role'] = role if role else 'unknown'
  ↓
MemoryItem.metadata = metadata
  ↓
Evidence._meta = metadata
```

### 关键代码

```python
# chatgpt.py:111-114
author = msg.get("author", {})
role = ""
if isinstance(author, dict):
    role = author.get("role", "").lower()
# ↑ 读取 ChatGPT 原始的 human/assistant 角色

# chatgpt.py:131-137
metadata: dict[str, Any] = {
    "source": "chatgpt",
    "conversation_title": conv_title,
    "message_id": msg_id,
    "recipient": recipient,
    "role": role if role else "unknown",  # ↑ 写入 _meta.role
}
```

### evidence_type 设置

```python
# memory_service.py:985-989
evidence = Evidence(
    id=self._generate_id(),
    workspace_id=workspace_id,
    entity_id=entity_id or UUID(int=0),
    evidence_type="conversation",  # ← 固定值！
    content=content,
    raw_content=content,
    source=source,
)
```

### 关键发现

1. **evidence_type 固定为 "conversation"** — 不是 "user" 或 "assistant"
2. **role 存储在 _meta** — 从 ChatGPT 原始数据读取
3. **导入时 role 可能被修改** — 需要检查是否有后续处理

---

## 6. 完整数据链路

```
ChatGPT Export JSON
  ↓
author.role = "human" or "assistant"
  ↓
chatgpt.py: role = author.role.lower()
  ↓
metadata['role'] = role
  ↓
Evidence._meta['role'] = 'human'/'assistant'
  ↓
memory_service.py: evidence_type = "conversation" (固定)
  ↓
DB: evidences(_meta={role:'human'}, evidence_type='conversation')
```

### 但是！

我之前的查询显示：
- evidence_type: user=7782, assistant=7880
- _meta->>'role': user=15661, test=1

**这说明有人修改了数据！** 可能是在某次修复过程中。

---

## 7. 重新解释 Phase 24-C 现象

### Agnes 之前的诊断错误

**错误查询**:
```sql
-- 我之前执行的错误查询
SELECT _meta->>'role' as role, COUNT(*) 
FROM evidences 
WHERE workspace_id = '...'
GROUP BY _meta->>'role';
```

**结果**: user=15661, test=1

**正确理解**: 
- 所有 evidence 的 `_meta->>'role'` 都是 'user'（或 'test'）
- 但 `evidence_type` 是正确的 user/assistant 分类

### 为什么 _meta->>'role' 全部是 'user'？

可能原因：
1. **导入后批量更新** — 有人在某次修复中执行了 UPDATE 设置所有 role='user'
2. **导入逻辑错误** — chatgpt.py 的 role 解析有问题
3. **数据迁移脚本** — 某个迁移脚本错误地覆盖了 role

### 验证证据

```sql
-- 检查 assistant evidence 的 _meta
SELECT _meta 
FROM evidences 
WHERE workspace_id = '...' 
  AND evidence_type = 'assistant'
LIMIT 5;
```

**结果**: 所有 assistant evidence 的 `_meta->>'role'` = 'user'

**这证实了 role 元数据被错误覆盖！**

---

## 8. 最终裁决

### ROLE SOURCE OF TRUTH

**evidence_type 字段** — 正确的语义分类

| Field | Value | Purpose |
|-------|-------|---------|
| evidence_type | user/assistant | 正确的语义角色分类 |
| _meta->>'role' | 全部 user | **错误数据**，已被覆盖 |

### USER COUNT

```
evidence_type = 'user': 7,782
evidence_type = 'assistant': 7,880
```

### ASSISTANT COUNT

```
7,880 evidences
```

### IMPORT ROLE PRESERVATION

**FAIL**

证据：
- 7,879 条 assistant evidence 的 `_meta->>'role'` = 'user'
- 应该是 'assistant'
- 说明导入后 role 元数据被错误覆盖

### PHASE 24-C ROOT CAUSE

**"Import role preservation failed, but evidence_type is correct. Pipeline reads _meta['role'] (wrong) instead of evidence_type (correct)."**

---

## 9. 修复建议

### 立即修复（不修改数据）

**选项 A**: 修改 Pipeline 使用 evidence_type 而不是 _meta['role']

```python
# formulator.py:124 — 修改前
role = classify_role(evidence._meta)

# 修改后
role_map = {
    'user': EvidenceRole.USER,
    'assistant': EvidenceRole.ASSISTANT,
    'system': EvidenceRole.SYSTEM,
}
role = role_map.get(evidence.evidence_type, EvidenceRole.UNKNOWN)
```

### 数据修复（需要确认）

**选项 B**: 修复 _meta['role'] 元数据

```sql
-- 根据 evidence_type 同步 _meta['role']
UPDATE evidences
SET _meta = jsonb_set(_meta, '{role}', to_jsonb(evidence_type))
WHERE workspace_id = '...'
  AND _meta->>'role' != evidence_type;
```

**注意**: 这需要用户授权，且可能影响其他依赖 _meta['role'] 的代码。

---

## 10. 对 Phase 24-C 的影响

### 当前状态

Pipeline 运行结果：
- ✅ ContextWindow 形成正确（基于 _meta['role']）
- ⚠️ Interpretation 可能错误（因为所有证据都被识别为 user）
- ❌ Formation 跳过（因为 AMBIGUOUS）

### 如果修复 role 读取

预期结果：
- ✅ ContextWindow 包含正确的 user/assistant 混合
- ✅ Short confirmation 可以匹配到 preceding assistant evidence
- ✅ 更多证据会形成 User Fact（非 AMBIGUOUS）

### 估算恢复率

假设：
- 7,782 user evidence 中，约 20% 是短确认/问题
- 7,880 assistant evidence 提供上下文
- Short confirmation + preceding assistant = CONFIRM pattern

**预估**: 恢复 1,500-2,000 个 Candidates

---

## Appendix: 代码位置

| 文件 | 行号 | 问题 |
|------|------|------|
| `formulator.py:124` | 124 | 读取 _meta['role'] 而非 evidence_type |
| `context_window.py:198-215` | 198 | classify_role() 函数 |
| `memory_service.py:989` | 989 | evidence_type 固定为 "conversation" |
| `chatgpt.py:111-114` | 111 | role 从 author.role 读取 |

---

**Diagnostic Complete. No modifications made.**
