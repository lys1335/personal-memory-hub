# Phase 20 Proposal Idempotency Fix

**Date**: 2026-08-14
**Status**: COMPLETE
**Commit**: WIP (not committed per user request)

---

## 1. Root Cause

### 精确原因

**同一 batch 内，多个 proposal 共享相同的 `candidate_id`，触发唯一约束冲突。**

### 证据链

```
1. _acquire_scope 查询返回 200 个 candidates
2. Batch 20/20 处理，EvidenceEvolutionEngine.evolve() 生成 2 个 candidates
3. 两个 candidates 都来自同一原始 candidate:
   - candidate_id = '00000000-019f-d00e-642e-feecfd3348bb'
4. ReflectionEngine.reflect_pipeline() 提取 2 个 facts:
   - fact[0]: entity='经费', source_ids=['12eb3bf2-9096-11f1-9643-46894c7bcffe']
   - fact[1]: entity='Annotation', source_ids=['00000000-019f-d00e-642e-feecfd3348bb']
5. _generate_proposals 为每个 entity 生成一个 proposal
6. 两个 proposal 的 candidate_id 都指向同一原始 candidate
7. _save_proposals 尝试插入两条 proposal，触发 UniqueViolation
```

### 代码位置

| 文件 | 行号 | 说明 |
|------|------|------|
| `reflection_service.py` | 824 | `all_proposals.extend(result.get("proposals", []))` |
| `reflection_service.py` | 1063 | `async with engine.begin() as conn:` |
| `reflection_service.py` | 1064 | `for prop in proposals:` ← 遍历所有 proposals |
| `reflection_service.py` | 1075-1084 | INSERT INTO proposals ← 第二次 INSERT 失败 |

### 错误详情

```
UniqueViolationError: duplicate key value violates unique constraint 
"uk_proposals_pending_per_candidate"
DETAIL: Key (workspace_id, candidate_id)=(fd0223ed-..., 00000000-019f-d00e-642e-feecfd3348bb) 
already exists.
```

---

## 2. Fix

### 修改文件

`backend/src/backend/service/reflection_service.py` — `_save_proposals` 方法

### 修改内容

在 `_save_proposals` 方法中添加去重逻辑：

```python
# P0 Fix: Deduplicate by candidate_id
# If multiple proposals share the same candidate_id, keep only the first one
deduplicated: dict[str, dict[str, Any]] = {}
for prop in proposals:
    candidate_id = prop.get("candidate_id")
    if candidate_id and candidate_id not in deduplicated:
        deduplicated[candidate_id] = prop

skipped_count = len(proposals) - len(deduplicated)
if skipped_count > 0:
    logger.warning(
        f"[PROPOSAL] Deduplicated {skipped_count} proposals "
        f"(duplicate candidate_id detected)"
    )
```

### 行为变化

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 同一 batch 内多 proposal 同 candidate_id | UniqueViolation → 整个 transaction rollback | 只保留第一个 proposal，其余跳过并记录 warning |
| 正常情况（唯一 candidate_id）| 正常插入 | 正常插入（无变化） |
| 空 proposals | 正常返回 | 正常返回（无变化） |

---

## 3. Transaction Semantics

### 成功路径

```
1. _acquire_scope 查询 → 返回 200 candidates
2. 处理 batch → 生成 2 proposals
3. _save_proposals:
   - 检测到 candidate_id 重复
   - 去重后保留 1 个 proposal
   - 事务内 INSERT 成功
   - 提交事务
4. Auto-approve 检查 → 可能批准 proposal
5. Candidate status 不变（仍为 'candidate'）
```

### 重复路径（本次修复）

```
1. 同一 candidate 在 batch 内生成多个 proposal
2. _save_proposals 检测到重复 candidate_id
3. 跳过重复 proposal，记录 warning 日志
4. 只保留第一个 proposal 插入
5. 事务成功提交
```

### 失败路径（rollback）

```
1. 任何 INSERT 失败（非 UniqueViolation）
2. 整个 transaction rollback
3. 数据保持一致（无部分提交）
4. Candidate status 不变
5. 下次 cron 重试时，candidate 仍然可用
```

### Retry 路径

```
1. 上次运行失败 → rollback → proposals 表为空
2. 下次 cron 运行（10 分钟后）
3. _acquire_scope 重新查询 → candidate 仍为 'candidate' status
4. 重新处理同一 candidate
5. 如果问题消失 → 成功
6. 如果问题持续 → 再次失败
```

**关键改进**：修复后，即使同一 candidate 生成多个 proposal，也不会触发 UniqueViolation。

---

## 4. Tests

### 通过的测试

| 测试文件 | 结果 |
|----------|------|
| `test_phase20_regression.py` | 6 passed, 8 skipped |
| `test_service_layer.py` | 27 passed |
| **总计** | **33 passed, 8 skipped** |

### 已知测试问题（与本次修复无关）

| 问题 | 原因 | 影响 |
|------|------|------|
| `test_phase20_db_integration.py` 4 failed | pytest-asyncio fixture 配置错误 | 低（测试基础设施问题） |
| `test_repository_infrastructure.py` 60 errors | asyncio fixture 类型错误 | 低（测试基础设施问题） |

### 新测试建议（未实施）

建议在 Phase 21 冻结后添加以下测试：

```python
def test_deduplicate_proposals_same_candidate_id():
    """同一 candidate 生成多个 proposal 时，只保留第一个"""
    proposals = [
        {'entity': 'A', 'candidate_id': 'uuid-1', 'type': 'Create'},
        {'entity': 'B', 'candidate_id': 'uuid-1', 'type': 'Refine'},
    ]
    # 验证去重逻辑
```

---

## 5. Boundary Audit

### Phase 20 Frozen Boundary

| 文件 | 状态 |
|------|------|
| `backend/src/backend/repository/proposal_repository.py` | ✓ 未修改 |
| `backend/src/backend/repository/candidate_repository.py` | ✓ 未修改 |
| `backend/alembic/versions/` | ✓ 未修改 |
| Database schema | ✓ 未修改 |

### Phase 21 Frozen Boundary

| 文件 | 状态 |
|------|------|
| `backend/src/backend/service/evidence_pipeline_service.py` | ✓ 未修改 |
| `backend/src/backend/context/` | ✓ 未修改 |
| `backend/src/backend/service/formation_service.py` | ✓ 未修改 |
| `backend/src/backend/service/topic_service.py` | ✓ 未修改 |
| `backend/src/backend/evolution/evolution_service.py` | ✓ 未修改 |

### 修改的文件

| 文件 | 修改内容 |
|------|----------|
| `backend/src/backend/service/reflection_service.py` | `_save_proposals` 添加去重逻辑 |

### Cron 状态

| 项目 | 状态 |
|------|------|
| Cron schedule | ✓ 未修改 |
| Cron target | ✓ 仍调用 `ReflectionService.reflect()` |
| Task status update | ✓ 未修改 |

---

## 6. Remaining Known Issues

### 未处理的 P1 问题

| # | 问题 | 状态 |
|---|------|------|
| 1 | Cron 未接入 EvidencePipelineService | 未处理 |
| 2 | proposals 数据缺失（364 → 0） | 未处理 |

### 未处理的 P2 问题

| # | 问题 | 状态 |
|---|------|------|
| 1 | 50 个 Zero UUID candidates | 未处理 |
| 2 | 自定义 UUID 生成器 | 未处理 |
| 3 | proposals_backup 清理 | 未处理 |

### 潜在风险

| 风险 | 说明 |
|------|------|
| 去重策略 | 保留第一个 proposal，可能丢失更高质量的 proposal |
| 重复处理 | 如果 LLM 持续返回重复 candidate_id，每次都会跳过 |

---

## 7. Next Steps

### 建议验证

1. 观察未来 24 小时 Cron 运行日志
2. 确认不再出现 `UniqueViolationError`
3. 确认 proposals 表有新增记录

### 后续优化（不在本阶段范围）

1. 调查为什么同一 candidate 会生成多个 proposal
2. 考虑在 `_generate_proposals` 层面添加去重
3. 评估是否需要在 `_acquire_scope` 添加 processed_at 时间戳

---

**Fix complete. Ready for Docker test verification.**
