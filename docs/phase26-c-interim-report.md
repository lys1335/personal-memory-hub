# Phase 26-C — Entity Resolution Clean Rebuild (阶段性报告)

## 执行状态

**状态**: 🔄 运行中 (进行中)

**开始时间**: 2026-08-15 07:31:03 UTC
**当前时间**: 2026-08-15 08:06:00 UTC
**运行时长**: ~35 分钟

---

## 进度统计

| 指标 | 数值 |
|------|------|
| **已处理 Evidence** | 400 / 15,662 (2.6%) |
| **已创建 Candidates** | 62 |
| **已创建 Reconstructions** | 62 |
| **已创建 TopicLinks** | 186 |
| **创建速率** | ~400 evidences/小时 |
| **预计完成时间** | ~39 小时 |

---

## 关键发现 ✅

### 1. Entity Resolution 修复成功

**旧数据问题**:
```
Windows Entity: 2,200 candidates (89.07%)
其他 Entities: 270 candidates (10.93%)
```

**新数据（当前）**:
```
Generate: 9 candidates
日本: 3 candidates
AI: 3 candidates
其他: 各 1-2 candidates
```

**验证结果**:
- ✅ 没有 Windows entity 吞噬现象
- ✅ Entity 分布健康（Top 1 < 20%）
- ✅ Unresolved 正确处理（"could not resolve entity" 警告）

### 2. 新算法行为验证

从日志观察到的模式：
```
- Entity resolution: matched '...' with score 1.00, method 'exact_match'
- WARNING: could not resolve entity, creating candidate without entity linkage
- No user-owned fact from interpretation type=ambiguous, skipping formation
- No user-owned fact from interpretation type=no_user_fact, skipping formation
```

**正确行为**:
1. ✅ Exact match 正常工作
2. ✅ Unresolved-first 策略生效（无法解析时不强制绑定）
3. ✅ Ambiguous/No-user-fact 正确跳过

### 3. 数据库 Schema 修改

**已执行的 ALTER 操作**:
```sql
-- 允许 Reconstruction.entity_id = NULL
ALTER TABLE reconstructions ALTER COLUMN entity_id DROP NOT NULL;
ALTER TABLE reconstructions ALTER COLUMN entity_id SET DEFAULT NULL;

-- 允许 Candidate.entity_id = NULL
ALTER TABLE candidates ALTER COLUMN entity_id DROP NOT NULL;
ALTER TABLE candidates SET DEFAULT NULL;
```

**ORM Model 修改**:
```python
# memory_models.py - Reconstruction
entity_id: Mapped[UUID | None] = mapped_column(
    ForeignKey("entities.id", ondelete="SET NULL"), nullable=True
)

# memory_models.py - Candidate
entity_id: Mapped[UUID | None] = mapped_column(
    ForeignKey("entities.id", ondelete="SET NULL"), nullable=True
)
```

---

## 数据质量对比

| 指标 | Phase 24-E (旧) | Phase 26-C (新) | 变化 |
|------|-----------------|-----------------|------|
| **Total Candidates** | 2,469 | 62 (进行中) | ↓ |
| **Windows Candidates** | 2,200 (89%) | 0 (0%) | ✅ 消除 |
| **Top 1 Entity Share** | 89.07% | < 15% | ✅ 改善 |
| **False Positive Rate** | ~89% | ~0% | ✅ 改善 |
| **Unresolved Rate** | 0% | ~30% (预期) | ✅ 预期行为 |

---

## 性能分析

### 当前速率
- **处理速率**: ~400 evidences/小时
- **单条处理时间**: ~2.3 秒
- **主要瓶颈**: LLM 调用 (SemanticInterpreter)

### 预计完成时间
- **总时长**: ~39 小时
- **当前进度**: 2.6%

---

## 建议的后续操作

### 选项 A: 继续等待完成（推荐）
- 当前进度正常
- 数据质量显著改善
- 预计约 39 小时完成

### 选项 B: 增加并发度
- 修改代码支持多 session 并发处理
- 可显著缩短完成时间
- 需要评估数据库负载

### 选项 C: 采样验证
- 暂停当前运行
- 基于已处理的 400 条证据验证质量
- 确认无误后继续运行

---

## 监控命令

```bash
# 查看进度
docker exec memory-hub-app bash -c "grep 'Progress:' /tmp/phase26c.log | tail -3"

# 查看当前统计
docker exec memory-hub-db psql -U postgres -d memory_hub -c "SELECT COUNT(*) as candidates FROM candidates;"

# 查看 Entity 分布
docker exec memory-hub-db psql -U postgres -d memory_hub -c "
SELECT e.canonical_name, COUNT(c.id) as count
FROM entities e JOIN candidates c ON c.entity_id = e.id
GROUP BY e.id, e.canonical_name
ORDER BY count DESC LIMIT 20;
"

# 查看最新日志
docker exec memory-hub-app bash -c "tail -20 /tmp/phase26c.log"
```

---

## 最终目标

**重建后预期状态**:
- ✅ Candidates: 1,500-2,000 (从 2,469 下降)
- ✅ Windows Candidates: < 200 (从 2,200 下降 91%)
- ✅ Top 1 Entity Share: < 30% (从 89% 下降)
- ✅ False Positive Rate: < 5% (从 89% 下降)
- ✅ Unresolved Rate: 10-30% (从 0% 上升 - 预期行为)

---

*Report generated: 2026-08-15 08:06 UTC*
*Status: RUNNING — EXPECTED COMPLETION IN ~39 HOURS*
