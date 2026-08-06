# Phase 5: 废弃脚本标记

## 概述

本阶段标记并归档所有已废弃的辅助脚本。这些脚本在开发过程中用于调试、测试和数据修复，但现在已被系统自动化流程替代。

## 废弃脚本列表

### Candidates 创建脚本（已废弃）

以下脚本用于创建candidates，现已由系统自动化流程替代：

| 脚本 | 用途 | 废弃原因 |
|------|------|----------|
| `create_candidates.py` | 从Evidences创建Candidates | 已被 `create_candidates_batch.py` 替代 |
| `create_candidates_async.py` | 异步创建Candidates | 性能问题，已被替代 |
| `create_candidates_batch.py` | 批量创建Candidates | **当前使用**，保留 |
| `create_candidates_final.py` | 最终版本创建 | 与batch相同，可删除 |
| `create_candidates_fixed.py` | 修复版本 | 调试用，已合并到batch |
| `create_candidates_from_entities.py` | 从Entities创建 | 逻辑已被batch涵盖 |
| `create_candidates_from_evidences.py` | 从Evidences创建 | 逻辑已被batch涵盖 |
| `create_candidates_with_content.py` | 含内容的Candidates | 调试用，已合并 |
| `create_candidates_with_evidence.py` | 含evidence的Candidates | 调试用，已合并 |
| `create_l2_candidates.py` | L2→L3 Candidates | 已被系统自动处理 |

### 数据修复脚本（已废弃）

| 脚本 | 用途 | 废弃原因 |
|------|------|----------|
| `fix_evidence_entity_link.py` | 修复evidence关联 | 一次性修复，已执行 |
| `fix_evidence_entity_link_batch.py` | 批量修复 | 一次性修复，已执行 |
| `fix_evidence_entity_link_full.py` | 完整修复 | 一次性修复，已执行 |

### 保留脚本

| 脚本 | 用途 | 状态 |
|------|------|------|
| `init_db.py` | 数据库初始化 | 保留（首次部署用） |
| `create_candidates_batch.py` | 批量创建Candidates | 保留（当前使用） |
| `start.sh` | 启动脚本 | 保留 |

## 废弃操作

### 标记方式

所有废弃脚本添加废弃头部注释：

```python
"""
DEPRECATED: 此脚本已废弃，请勿使用。

废弃原因: [具体原因]
替代方案: [正确的使用方式]
废弃日期: 2026-08-06
"""
```

### 归档位置

废弃脚本保留在原位置，但添加明确的废弃标记。不删除是为了：
1. 保留开发历史记录
2. 便于追溯问题
3. 未来可能需要参考实现逻辑

## 当前推荐流程

### 创建 Candidates

```bash
# 使用批量脚本（推荐）
cd backend
python scripts/create_candidates_batch.py
```

### 运行 Reflection Pipeline

```bash
# 通过API调用（推荐）
curl -X POST "http://localhost:8000/reflection" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "fd0223ed-7aa2-491e-8db5-b0de71b75219",
    "scope": "workspace",
    "limit": 200
  }'
```

### 自动批准（可选）

设置环境变量 `AUTO_APPROVE=true` 以启用自动批准。

### 定时任务

```bash
# 查看定时任务
curl http://localhost:8000/api/cron/tasks

# 手动触发
curl -X POST http://localhost:8000/api/cron/tasks/{task_id}/run-now
```

## 数据清理

如需清理废弃脚本的历史数据：

```sql
-- 查看candidates状态
SELECT source, status, COUNT(*) 
FROM candidates 
GROUP BY source, status;

-- 清理旧candidates（谨慎操作）
DELETE FROM candidates 
WHERE source != 'system' AND created_at < NOW() - INTERVAL '7 days';
```

## Git 操作

所有废弃脚本已标记，但未删除。如需清理：

```bash
# 查看废弃脚本列表
git status | grep -E "create_candidates|fix_evidence"

# 删除废弃脚本（谨慎操作）
git rm backend/scripts/create_candidates.py
git rm backend/scripts/fix_evidence_entity_link.py
# ... 其他废弃脚本
```

## 相关文档

- [Phase 1-4 实施报告](./docs/phase-implementation-summary.md)
- [Reflection Pipeline 架构](./docs/D4-2g-evolution-architecture.md)
- [API 文档](./docs/api-reference.md)

---

标记日期: 2026-08-06
作者: Agnes (Hermes Agent)
