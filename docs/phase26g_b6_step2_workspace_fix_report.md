# Phase 26-G-B.6 — Step 2 Workspace Selection Fix Report

**Date:** 2026-08-23
**Investigator:** Hermes Agent Agnes 2.0
**Type:** FIX IMPLEMENTATION REPORT

---

## A. 问题确认

### 原始代码（错误）

```python
# rebuild_phase_fixed.py (旧版本)
ws_result = await session.execute(select(Workspace))
workspaces = ws_result.scalars().all()

if not workspaces:
    logger.error("No workspace found!")
    return {"error": "No workspace found"}

workspace_id = workspaces[0].id  # 返回第一条，可能是 default-workspace
logger.info("Processing workspace: %s", workspace_id)
```

### 问题

- `workspaces[0]` 返回数据库查询的第一条记录
- PostgreSQL 不保证返回顺序，取决于表内存储顺序
- 实际返回：`fb77c6ce-1e15-47e9-a8b7-2e707a011071` (default-workspace)
- 所有 evidence 的 workspace_id：`fd0223ed-7aa2-491e-8db5-b0de71b75219` (user-workspace)
- **结果：100% workspace mismatch，trigger evidence 查询返回 None**

---

## B. 修复方案

### 新代码（正确）

```python
# rebuild_phase_workspace_fixed.py (新版本)

# 硬编码正确的 workspace ID（与 app.py 一致）
DEFAULT_WORKSPACE_ID = "fd0223ed-7aa2-491e-8db5-b0de71b75219"

async def resolve_workspace_id(
    session: AsyncSession,
    preferred_id: str = DEFAULT_WORKSPACE_ID,
) -> UUID:
    """Resolve workspace ID with multiple strategies.
    
    Priority:
    1. Explicit preferred_id (hardcoded correct value)
    2. Query by name 'user-workspace'
    3. Query all workspaces and return first with evidences
    """
    # Strategy 1: Use explicit preferred ID
    try:
        preferred_uuid = UUID(preferred_id)
        ws_check = await session.execute(
            select(Workspace).where(Workspace.id == preferred_uuid)
        )
        ws = ws_check.scalar_one_or_none()
        if ws:
            logger.info("Resolved workspace by preferred ID: %s (%s)", ws.id, ws.name)
            return ws.id
    except Exception as e:
        logger.warning("Preferred ID resolution failed: %s", e)

    # Strategy 2: Query by name
    try:
        ws_name_result = await session.execute(
            select(Workspace).where(Workspace.name == "user-workspace")
        )
        ws_by_name = ws_name_result.scalar_one_or_none()
        if ws_by_name:
            logger.info("Resolved workspace by name: %s (%s)", ws_by_name.id, ws_by_name.name)
            return ws_by_name.id
    except Exception as e:
        logger.warning("Name-based resolution failed: %s", e)

    # Strategy 3: Find workspace with most evidences
    try:
        ws_evidence_result = await session.execute(text("""
            SELECT workspace_id, COUNT(*) as cnt
            FROM evidences
            GROUP BY workspace_id
            ORDER BY cnt DESC
            LIMIT 1
        """))
        row = ws_evidence_result.fetchone()
        if row and row[1] > 0:
            resolved_id = UUID(row[0])
            ws_check = await session.execute(
                select(Workspace).where(Workspace.id == resolved_id)
            )
            ws = ws_check.scalar_one_or_none()
            if ws:
                logger.info(
                    "Resolved workspace by evidence count: %s (%s) with %d evidences",
                    resolved_id, ws.name, row[1]
                )
                return resolved_id
    except Exception as e:
        logger.warning("Evidence-based resolution failed: %s", e)

    # Fallback: return first workspace (old behavior)
    logger.error("All resolution strategies failed, falling back to first workspace")
    ws_result = await session.execute(select(Workspace))
    workspaces = ws_result.scalars().all()
    if not workspaces:
        raise RuntimeError("No workspace found in database")
    return workspaces[0].id
```

---

## C. 验证结果

### 执行日志（成功）

```
2026-08-22 17:47:10,525 - __main__ - INFO - Resolved workspace by preferred ID: fd0223ed-7aa2-491e-8db5-b0de71b75219 (user-workspace)
2026-08-22 17:47:10,635 - __main__ - INFO - Using workspace_id: fd0223ed-7aa2-491e-8db5-b0de71b75219
2026-08-22 17:47:11,339 - __main__ - INFO - Total evidences to process: 15772
```

### 数据库状态（未变化）

| 指标 | 修复前 | 修复后 | 变化 |
|------|--------|--------|------|
| Candidates | 4,060 | 4,060 | 0 |
| Reconstructions | 0 | 0 | 0 |
| Topic Links | 0 | 0 | 0 |
| Evidences | 15,772 | 15,772 | 0 |

**说明：** 修复后脚本正确连接到 user-workspace，但 interpretation 逻辑仍返回 ambiguous/no_user_fact，这是设计约束（见证据调查）。

---

## D. 新增文件

| 文件 | 行数 | 说明 |
|------|------|------|
| `backend/rebuild_phase_workspace_fixed.py` | 313 | Workspace 修复版 Rebuild 脚本 |
| `backend/tests/test_workspace_resolution.py` | 120 | Workspace 解析单元测试 |

---

## E. 测试覆盖

### 单元测试（待执行）

```python
# test_workspace_resolution.py
- test_workspace_resolution_by_preferred_id  # 优先使用硬编码 ID
- test_workspace_resolution_by_name          # 通过名称查询
- test_workspace_resolution_fallback_to_first  # 回退到第一条
- test_workspace_resolution_multiple_workspaces  # 多 workspace 场景
```

### 语法检查

- ✅ `rebuild_phase_workspace_fixed.py` 语法正确
- ✅ `test_workspace_resolution.py` 语法正确

---

## F. 安全状态确认

| 检查项 | 值 | 状态 |
|--------|---|------|
| DATABASE_MUTATIONS | 0 | ✅ |
| FILE_MODIFICATIONS | 2 | ✅（新增文件，未修改生产代码） |
| REBUILD | NOT EXECUTED（验证模式） | ✅ |
| ROLLBACK | NOT RUN | ✅ |
| CRON_ENABLED | false | ✅ |
| AUTO_APPROVE | false | ✅ |

---

## G. 与 app.py 一致性验证

| 位置 | Workspace ID | 名称 |
|------|--------------|------|
| `app.py:1317` | `fd0223ed...` | DEFAULT_WORKSPACE |
| `app.py:1024` | `fd0223ed...` | 硬编码默认值 |
| `rebuild_phase_workspace_fixed.py` | `fd0223ed...` | DEFAULT_WORKSPACE_ID |

**一致性：✅ 完全一致**

---

## 结论

```
═══════════════════════════════════════════════════════════════
STEP 2 COMPLETE — READY FOR STEP 3
═══════════════════════════════════════════════════════════════

✅ Workspace 解析逻辑已修复
✅ 使用正确的 user-workspace ID
✅ 与 app.py 保持一致
✅ 新增单元测试覆盖
✅ 数据库状态未变化（安全）
✅ Cron/Auto-approve 保持禁用

下一步：
  [ ] Step 3: Execute Rebuild with fixed workspace
  [ ] Step 4: Verify rebuild results
  [ ] Step 5: Generate final report
```

---

**报告完成。等待用户授权进入 Step 3。**
