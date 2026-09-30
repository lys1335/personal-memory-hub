# Phase 24-E — Pipeline 暂停诊断报告

**Date**: 2026-08-14  
**Status**: PAUSED (Pending User Decision)  
**Mode**: READ-ONLY Diagnostic

---

## 1. 缺失的 Topic Method

### 错误信息

```
ERROR: 'TopicRepository' object has no attribute 'increment_count'
```

### 调用链

```
topic_service.py:219-228
  → _increment_reconstruction_count(topic_id)
  → _increment_candidate_count(topic_id)
  → _increment_entity_count(topic_id)
  → repo.increment_count(topic_id, count_field="...")
                    ↑ 方法不存在！
```

### TopicRepository 实际方法列表

| 方法名 | 存在 |
|--------|------|
| `create` | ✅ |
| `get_by_id` | ✅ |
| `update` | ✅ |
| `delete` | ✅ |
| `find_by_workspace` | ✅ |
| `find_by_name` | ✅ |
| `find_by_parent` | ✅ |
| `find_root_topics` | ✅ |
| `create_link` | ✅ |
| `remove_link` | ✅ |
| `list_links` | ✅ |
| `list_topics_for_source` | ✅ |
| `list_sources_for_topic` | ✅ |
| `is_valid_parent` | ✅ |
| **`increment_count`** | ❌ **缺失** |

---

## 2. 哪个代码路径调用它

### 路径 1: TopicService._increment_reconstruction_count

```python
# topic_service.py:219-221
async def _increment_reconstruction_count(self, topic_id: UUID) -> None:
    """Increment reconstruction_count on topic."""
    await self.repo.increment_count(topic_id, count_field="reconstruction_count")
```

### 路径 2: TopicService._increment_candidate_count

```python
# topic_service.py:223-225
async def _increment_candidate_count(self, topic_id: UUID) -> None:
    """Increment candidate_count on topic."""
    await self.repo.increment_count(topic_id, count_field="candidate_count")
```

### 路径 3: TopicService._increment_entity_count

```python
# topic_service.py:227-229
async def _increment_entity_count(self, topic_id: UUID) -> None:
    """Increment entity_count on topic."""
    await self.repo.increment_count(topic_id, count_field="entity_count")
```

### 触发点

```python
# topic_service.py:174-181
async def link_reconstruction_to_topics(self, ...):
    for topic_id in topic_ids:
        await self.repo.create_link(...)
        await self._increment_reconstruction_count(topic_id)  # ← 触发错误
```

---

## 3. 为什么被判定为"不阻塞"

### 原因 1: Exception Handler 吞掉了错误

```python
# evidence_pipeline_service.py:208-218
async def _extract_topics(...):
    try:
        topic_ids = await self.topics.extract_topics_from_summary(...)
        if formation.reconstruction_id:
            await self.topics.link_reconstruction_to_topics(...)
        return topic_ids
    except Exception as e:
        logger.error("Failed to extract topics: %s", e)
        return []  # ← 返回空列表，不抛出
```

### 原因 2: 错误在事务提交之后才发生

```python
# evidence_pipeline_service.py:155-171
if interpretation.user_owned:
    topic_ids = await self._extract_topics(...)  # ← 这里失败

# NOTE: 即使 topic_ids = []，pipeline 仍然继续
await self._commit(self.session)  # ← 事务已提交
```

### 原因 3: TopicLink 创建在 increment_count 之前

```python
# topic_repository.py:280-315
async def create_link(self, ...):
    # ... 检查 workspace ...
    link = TopicLink(topic_id=..., source_type=..., source_id=...)
    self.session.add(link)
    await self.session.flush()  # ← 这里成功提交
    
# 然后：
await self._increment_reconstruction_count(topic_id)  # ← 这里失败
```

---

## 4. 当前已处理数据统计

### 日志统计

```
Pipeline started: 216 次
Formation successful: 29 次
Failed to extract topics: 29 次（全部）
```

### 数据库统计

```sql
candidates:       29
reconstructions:  29
topic_links:      29    ← 全部成功创建
topics:           11    ← 去重后的 topic
proposals:        0
evidences:        15,662 (未变)
```

### Lineage 验证

```
Candidate → Reconstruction → TopicLink → Topic
    29        →      29       →     29     →   11
```

**结论**: 所有已处理的 29 个 Candidate 都有完整的 lineage。

---

## 5. 已提交但缺少 TopicLink 的记录？

### 检查结果

```sql
SELECT COUNT(*) as orphan_candidates
FROM candidates c
LEFT JOIN reconstructions r ON r.candidate_id = c.id
LEFT JOIN topic_links tl ON tl.source_type = 'reconstruction' AND tl.source_id = r.id
WHERE tl.source_id IS NULL;
-- 结果: 0
```

**结论**: 无孤儿记录。所有 Candidate/Reconstruction 都有对应的 TopicLink。

---

## 6. 修复影响分析

### 方案 A: 添加 increment_count 方法（最小修复）

```python
# topic_repository.py 新增方法
async def increment_count(self, topic_id: UUID, count_field: str) -> None:
    """Increment a count field on topic."""
    from sqlalchemy import update
    stmt = (
        update(Topic)
        .where(Topic.id == topic_id)
        .values(**{count_field: Topic.__table__.c[count_field] + 1})
    )
    await self.session.execute(stmt)
```

**影响**:
- ✅ 修复已有记录的 count 字段
- ⚠️ 需要回填已提交的 29 条记录的 count
- ⏸️ 暂停后修复，不影响已提交数据

### 方案 B: 跳过 count 更新（临时绕过）

```python
# topic_service.py
async def _increment_reconstruction_count(self, topic_id: UUID) -> None:
    pass  # 暂时跳过
```

**影响**:
- ✅ Pipeline 可以继续
- ❌ topic.reconstruction_count 等字段将为 NULL/0
- ❌ 违反授权条件（不绕过 topic extraction）

### 方案 C: 清除数据后重新执行（最干净）

1. TRUNCATE candidates/reconstructions/topic_links
2. 修复 increment_count 方法
3. 重新执行全量 Pipeline

**影响**:
- ✅ 数据完全一致
- ⏸️ 需要重新开始（已处理的 29 条会丢失）

---

## 7. 建议

### 推荐方案: A（添加 increment_count）

**理由**:
1. 符合授权条件（不绕过 topic extraction）
2. 不影响已提交数据
3. 修复成本低（1 个方法）
4. 回填工作量小（29 条记录）

**执行步骤**:
1. 在 TopicRepository 添加 `increment_count` 方法
2. 回填已提交的 29 条 topic 的 count 字段
3. 继续执行 Phase 24-E（从第 217 条证据开始）

---

## 8. 等待用户决策

| 选项 | 操作 | 影响 |
|------|------|------|
| **A** | 修复 increment_count + 回填 + 继续 | 推荐，数据完整 |
| **B** | 清空数据 + 修复 + 重跑 | 最干净，但需重新开始 |
| **C** | 跳过 count 更新 + 继续 | 违反授权条件 |

**Phase 24-E 已暂停，等待用户选择方案。**

---

## Appendix: 当前数据库快照

```sql
-- 完整状态
candidates:       29
reconstructions:  29
topic_links:      29
topics:           11
proposals:        0
memory_nodes:     0
evidences:        15,662 (只读)
entities:         4,855 (只读)
areas:            3,732 (只读)

-- 处理进度
processed:        216 / 15,662 (1.4%)
formation_rate:   29 / 216 (13.4%)
ambiguous_rate:   ~25% (estimated)
```
