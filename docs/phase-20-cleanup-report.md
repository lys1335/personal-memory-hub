# Phase 20 — Pending Proposal Cleanup Report

## 执行摘要

✅ **清理成功完成**

---

## 1. 删除前状态

| 指标 | 数值 |
|------|------|
| Pending Proposals | 364 |
| Approved Proposals | 1,005 |
| Candidates | 14,340 |
| Evidences | 15,662 |
| MemoryNodes | 24,037 |

---

## 2. 删除操作

```sql
DELETE FROM proposals
WHERE workspace_id = 'fd0223ed-7aa2-491e-8db5-b0de71b75219'
AND status = 'pending';
```

**实际删除数量**: 364

---

## 3. 删除后状态

| 指标 | 删除前 | 删除后 | 变化 |
|------|--------|--------|------|
| Pending Proposals | 364 | **0** | -364 ✅ |
| Approved Proposals | 1,005 | 1,005 | 0 ✅ |
| Candidates | 14,340 | 14,340 | 0 ✅ |
| Evidences | 15,662 | 15,662 | 0 ✅ |
| MemoryNodes | 24,037 | 24,037 | 0 ✅ |

---

## 4. 备份信息

| 项目 | 值 |
|------|------|
| 备份表名 | `proposals_backup_20260812` |
| 备份记录数 | 364 |
| 备份时间 | 2026-08-12 |
| 恢复方式 | `INSERT INTO proposals SELECT * FROM proposals_backup_20260812` |

---

## 5. 验证结果

| 验证项 | 结果 |
|--------|------|
| Pending = 0 | ✅ |
| Approved 未变 | ✅ |
| Candidates 未变 | ✅ |
| Evidences 未变 | ✅ |
| MemoryNodes 未变 | ✅ |
| 备份完整 | ✅ |

---

## 6. 结论

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 20 Pending Proposal Cleanup                          │
├─────────────────────────────────────────────────────────────┤
│  删除前 Pending:  364                                       │
│  实际删除:        364                                       │
│  删除后 Pending:    0                                       │
│  备份记录数:      364                                       │
│  其他表影响:        0                                       │
├─────────────────────────────────────────────────────────────┤
│  STATUS: SUCCESS ✅                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. 下一步建议

### 短期（可选）
1. 保留备份表 7 天，确认无误后可删除
2. 重启 Evolution Scheduler，观察是否正常

### 中期（Phase 20 修复）
1. 添加 `proposals.candidate_id` FK
2. 实现状态转换逻辑
3. 添加 Scope 去重检查

### 长期
1. 清理 Legacy Evidence
2. 优化 Evolution 算法

---

**执行状态**: 完成 ✅  
**修改内容**: 仅删除 364 个 Pending Proposals  
**影响范围**: 无  
**恢复能力**: 可通过备份表恢复
