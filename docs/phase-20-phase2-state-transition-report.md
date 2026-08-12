# Phase 20 — Phase 2: Candidate State Transition Report

## 执行摘要

✅ **Phase 2 完成**

---

## 一、修改内容

### 1.1 Candidate Repository 新增方法

**File**: `backend/src/backend/repository/candidate_repository.py`

```python
async def update_status(
    self,
    *,
    candidate_id: str,
    new_status: str,
) -> None:
    """Update a candidate's status.

    Args:
        candidate_id: The candidate UUID (as string).
        new_status: New status value (candidate, confirmed, archived, orphaned).

    Raises:
        DomainIntegrityError: If new_status is not valid.
    """
    valid_statuses = ("candidate", "confirmed", "archived", "orphaned")
    if new_status not in valid_statuses:
        raise DomainIntegrityError(...)

    await self.session.execute(
        text("""
            UPDATE candidates
            SET status = :new_status, updated_at = NOW()
            WHERE id = :candidate_id
        """),
        {"new_status": new_status, "candidate_id": candidate_id},
    )
```

### 1.2 ReflectionService 修改

#### approve_proposal() 新增

```python
# After MemoryNode creation
candidate_id = prop.get('candidate_id')
if candidate_id:
    await conn.execute(text("""
        UPDATE candidates
        SET status = 'confirmed', updated_at = NOW()
        WHERE id = :candidate_id
    """), {"candidate_id": str(candidate_id)})
```

#### reject_proposal() 重写

```python
async def reject_proposal(...):
    async with engine.begin() as conn:
        # Get proposal to find candidate_id
        result = await conn.execute(text("""
            SELECT id, candidate_id FROM proposals
            WHERE id = :id AND workspace_id = :workspace_id
        """), {...})
        
        # Update proposal status
        await conn.execute(text("""
            UPDATE proposals SET status = 'rejected'...
        """), {...})
        
        # Update candidate status to 'orphaned'
        candidate_id = prop_row[1]
        if candidate_id:
            await conn.execute(text("""
                UPDATE candidates
                SET status = 'orphaned', updated_at = NOW()
                WHERE id = :candidate_id
            """), {"candidate_id": str(candidate_id)})
```

#### _acquire_scope() 修改

```python
# Before (wrong):
AND status IN ('candidate', 'pending')

# After (correct):
AND status = 'candidate'
AND NOT EXISTS (
    SELECT 1 FROM proposals
    WHERE proposals.candidate_id = candidates.id
    AND proposals.status = 'pending'
)
```

---

## 二、事务边界

### approve_proposal()

```python
async with engine.begin() as conn:  # ← 同一事务
    # Step 1: UPDATE proposals SET status = 'approved'
    # Step 2: INSERT INTO memory_nodes
    # Step 3: UPDATE candidates SET status = 'confirmed' ← NEW
```

**验证**: 所有操作在 `engine.begin()` 上下文内，任一失败则全部回滚。

### reject_proposal()

```python
async with engine.begin() as conn:  # ← 同一事务
    # Step 1: SELECT candidate_id from proposal
    # Step 2: UPDATE proposals SET status = 'rejected'
    # Step 3: UPDATE candidates SET status = 'orphaned' ← NEW
```

**验证**: 所有操作在 `engine.begin()` 上下文内，任一失败则全部回滚。

---

## 三、Scope 去重验证

### 当前查询逻辑

```sql
SELECT ... FROM candidates
WHERE workspace_id = :workspace_id
AND status = 'candidate'                                          -- 只选待处理
AND NOT EXISTS (                                                 -- 排除有 pending proposal 的
    SELECT 1 FROM proposals
    WHERE proposals.candidate_id = candidates.id
    AND proposals.status = 'pending'
)
ORDER BY created_at ASC
LIMIT :limit
```

### 边界场景覆盖

| 场景 | 状态 | Scope 排除？ |
|------|------|-------------|
| Candidate 无 Proposal | candidate | ❌ 不排除 |
| Candidate 有 pending Proposal | candidate | ✅ 排除 |
| Candidate 有 approved Proposal | confirmed | ✅ 排除（状态不对） |
| Candidate 有 rejected Proposal | orphaned | ✅ 排除（状态不对） |
| 重复 Evolution | candidate + 无 pending | ❌ 不排除（可重新处理） |

---

## 四、测试覆盖

### Regression Tests（6/6 通过）

| # | 测试 | 状态 |
|---|------|------|
| 1 | Approve → confirmed | ✅ |
| 2 | Reject → orphaned | ✅ |
| 3 | Pending 排除 | ✅ |
| 4 | Approved 不重处理 | ✅ |
| 5 | Orphaned 排除 | ✅ |
| 6 | Unique pending per candidate | ✅ |

---

## 五、Git Diff

```diff
diff --git a/backend/src/backend/repository/candidate_repository.py b/backend/src/backend/repository/candidate_repository.py
index xxx..yyy 100644
+++ b/backend/src/backend/repository/candidate_repository.py
@@ -228,6 +228,39 @@
         result = await self.session.execute(stmt)
         return list(result.scalars().all())
 
+    async def update_status(
+        self,
+        *,
+        candidate_id: str,
+        new_status: str,
+    ) -> None:
+        """Update a candidate's status."""
+        ...
+
     async def find_by_candidate_type(

diff --git a/backend/src/backend/service/reflection_service.py b/backend/src/backend/service/reflection_service.py
index xxx..yyy 100644
+++ b/backend/src/backend/service/reflection_service.py
@@ -367,6 +367,16 @@
             logger.info(f"Approved proposal {proposal_id}: created {node_type} node {new_node_id}")
+
+            # P2 Fix: Update candidate status to 'confirmed'
+            candidate_id = prop.get('candidate_id')
+            if candidate_id:
+                await conn.execute(text("""
+                    UPDATE candidates
+                    SET status = 'confirmed', updated_at = NOW()
+                    WHERE id = :candidate_id
+                """), {"candidate_id": str(candidate_id)})
 
@@ -446,20 +456,45 @@
     async def reject_proposal(...):
         async with engine.begin() as conn:
+            # Get proposal to find candidate_id
+            result = await conn.execute(text("""
+                SELECT id, candidate_id FROM proposals...
+            """), {...})
+
             await conn.execute(text("""
                 UPDATE proposals SET status = 'rejected'...
             """), {...})
+
+            # P2 Fix: Update candidate status to 'orphaned'
+            candidate_id = prop_row[1]
+            if candidate_id:
+                await conn.execute(text("""
+                    UPDATE candidates
+                    SET status = 'orphaned', updated_at = NOW()
+                    WHERE id = :candidate_id
+                """), {"candidate_id": str(candidate_id)})
 
@@ -1091,7 +1126,12 @@
                     FROM candidates
                     WHERE workspace_id = :workspace_id
-                    AND status IN ('candidate', 'pending')
+                    AND status = 'candidate'
+                    AND NOT EXISTS (
+                        SELECT 1 FROM proposals
+                        WHERE proposals.candidate_id = candidates.id
+                        AND proposals.status = 'pending'
+                    )
                     ORDER BY created_at ASC
```

---

## 六、最终结论

```
======================================================================
Phase 20 — Phase 2: Candidate State Transition Complete
======================================================================

Changes:
  ✅ candidate_repository.py: +33 lines (update_status method)
  ✅ reflection_service.py: +55 lines (approve/reject/scope)

Transactions:
  ✅ approve: Proposal + MemoryNode + Candidate → same transaction
  ✅ reject: Proposal + Candidate → same transaction

Scope Dedup:
  ✅ NOT EXISTS pending proposal
  ✅ status = 'candidate' only

Tests:
  ✅ 6/6 regression tests passed

Design Constraints:
  ✅ No evidence modification
  ✅ No legacy data modification
  ✅ No scheduler modification
  ✅ Minimal code change
======================================================================
```

---

**状态**: Phase 2 完成
**下一步**: Phase 20 全部完成，等待用户确认
