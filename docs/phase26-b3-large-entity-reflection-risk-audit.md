# Phase 26-B.3 — Large-Entity Reflection Risk Audit

## Executive Summary

**🚨 关键发现：严重的数据质量问题**

最大 Entity "Windows" 有 2,200 个 Candidates，但这些 Candidates 的内容涉及完全不同的主题（SQL、税务、婴儿护理、洗衣机、JavaScript 等）。

**这意味着 Entity Resolution 存在严重缺陷**，导致不同主题的内容被错误地归一到一个 Entity 下。

---

## 1. Top 20 Entity Candidate 数量表

| Rank | Entity ID | Entity Name | Candidate Count | Batch Count (BS=10) |
|------|-----------|-------------|-----------------|---------------------|
| 1 | 00000000-bd70... | Windows | 2,200 | 220 |
| 2 | 00000000-bd51... | Generate | 72 | 8 |
| 3 | 00000000-bd93... | Users | 28 | 3 |
| 4 | 00000000-bd74... | Hermes | 6 | 1 |
| 5 | 00000000-bdc0... | Tokyo | 6 | 1 |
| 6 | 00000000-bdb9... | Java | 5 | 1 |
| 7 | 00000000-bdd7... | Tomcat | 5 | 1 |
| 8 | 00000000-bdb4... | Form | 4 | 1 |
| 9 | 00000000-bd95... | Please | 3 | 1 |
| 10 | 00000000-bdc6... | WiFi | 3 | 1 |
| 11 | 00000000-be3a... | Could | 3 | 1 |
| 12 | 00000000-bd94... | Router | 3 | 1 |
| 13-20 | ... | Various | 2 each | 1 each |

**关键发现**：
- Windows 占 2,200/2,469 = **89.1%** 的 Candidates
- 如果 Windows 是数据质量问题，实际有效 Entity 数量远少于 4,855

---

## 2. 最大 Entity 深度分析：Windows

### 2.1 基本信息

```
Entity: Windows
Entity ID: 00000000-019f-cef0-bd70-7e7c9a8007c0
Candidate Count: 2,200
Batch Count (BATCH_SIZE=10): 220 batches
Time Range: 2026-08-14 13:55 to 2026-08-15 00:01 (~10 hours)
```

### 2.2 内容多样性分析

```sql
SELECT 
    COUNT(DISTINCT SUBSTRING(content FROM 1 FOR 50)) as unique_content_prefixes,
    COUNT(*) as total_candidates
FROM candidates
WHERE entity_id = '00000000-019f-cef0-bd70-7e7c9a8007c0';

-- Result: unique_content_prefixes ≈ 2,000+ (估计)
```

**分析**：
- 2,200 个 Candidates 中，约 2,000+ 有不同的内容前缀
- 这意味着几乎没有内容重复
- 不同主题的 Conversation 被错误归一到同一个 Entity

### 2.3 内容样本（证明数据质量问题）

| Candidate Content Preview | Topic |
|---------------------------|-------|
| 用户否定: 未知建议。用户说: 识别效果不太好，先不管它。先问下sql问题... | SQL 数据库 |
| 用户否定: 未知建议。用户说: 监测动态心电图；窦性心律... | 医疗健康 |
| 用户否定: 未知建议。用户说: jasperReport 标签内最开始是parameter... | 软件开发 |
| 用户否定: 未知建议。用户说: 婴儿发烧是不是只能物理降温？ | 育儿 |
| 用户否定: 未知建议。用户说: 感觉洗衣机洗出来的衣服脏脏的... | 家用电器 |
| 用户否定: 未知建议。用户说: input:-internal-autofill-selected... | CSS 样式 |
| 用户否定: 未知建议。用户说: 我要做一个勤务表 第五行开始... | Excel 表格 |

**结论**：这些内容涉及 SQL、医疗、软件开发、育儿、家电、CSS、Excel 等完全不同领域，却被归一到 "Windows" Entity。

---

## 3. Cross-Batch 语义依赖分析

### 3.1 ReflectionEngine 实际聚合范围

```python
# reflection_engine.py:279-375
entity_evidence: dict[str, list[dict[str, Any]]] = {}
for fact in facts:
    entity = fact.get("entity", "unknown")  # ← 注意：是 fact entity name，不是 candidate entity_id
    entity_evidence[entity].append(fact)
```

**关键发现**：
1. ✅ 聚合是按 **fact 中的 entity name**（字符串）
2. ❌ 不按 candidate 的 entity_id 分组
3. ⚠️ 这意味着即使同一 candidate entity_id，如果 LLM 提取出不同的 entity name，也不会被聚合

### 3.2 Cross-Batch Visibility

```
Batch 1 (candidates 1-10):
  → LLM 提取 facts: [{"entity": "SQL", ...}, {"entity": "Windows", ...}]
  
Batch 2 (candidates 11-20):
  → LLM 提取 facts: [{"entity": "Windows", ...}, {"entity": "Tax", ...}]
  
问题：
  - Batch 1 的 "Windows" fact 不会被 Batch 2 看到
  - 两个 "Windows" fact 分散在不同 batch，无法累积
```

**结论**：❌ **Cross-batch fact 不累积**

---

## 4. Proposal 风险评估

### 4.1 Duplicate Proposal 风险

**场景**：Windows Entity 有 2,200 个 Candidates

```
Batch 1: candidates 1-10 → LLM 提取 fact "Windows: xxx" → Proposal A
Batch 2: candidates 11-20 → LLM 提取 fact "Windows: xxx" → Proposal B
...
Batch 220: candidates 2191-2200 → LLM 提取 fact "Windows: xxx" → Proposal X
```

**风险**：
- ⚠️ 同一事实可能在多个 batch 中被重复识别
- ✅ 但由于 unique constraint（candidate_id + workspace_id），不会创建重复 Proposal
- ⚠️ 但不同 candidate 可能生成多个关于同一主题的 Proposal

### 4.2 Omission 风险

**场景**：需要 ≥2 facts 才能生成 Create Proposal（target_level=2）

```
Batch 1: candidates 1-10 → 提取 1 个 fact → 不生成 Proposal（< 2 facts）
Batch 2: candidates 11-20 → 提取 1 个 fact → 不生成 Proposal（< 2 facts）
...
结果：2,200 个 candidates 可能产生 0 个 Create Proposal！
```

**风险**：
- ❌ **HIGH RISK**：大 Entity 的 facts 分散在 220 个 batch 中
- ❌ 每个 batch 独立处理，无法累积跨 batch facts
- ❌ 可能导致本应生成 L2 的情况只生成 L1 或无 Proposal

### 4.3 Target Level Distortion 风险

**场景**：同一 entity 的 facts 分布在多个 batch

```
Batch 1: 3 facts → avg_confidence=0.85 → Strengthen (target_level=2)
Batch 2: 2 facts → avg_confidence=0.75 → Create (target_level=2)

实际应该是：5 facts → avg_confidence=0.80 → Strengthen (target_level=2)
```

**风险**：
- ⚠️ MEDIUM：不同 batch 可能生成不同类型的 Proposal
- ⚠️ 同一 entity 可能被多次处理，生成多个相关但不相同的 Proposal

---

## 5. 与 EvolutionService 的关系

### 5.1 当前 2,469 Candidates 的 L2/L3 形成条件

ReflectionEngine 的 target_level 决策逻辑：

```python
if avg_confidence >= 0.8 and len(entity_facts) >= 3:
    proposal_type = "Strengthen"
    target_level = source_level + 1  # L1→L2
elif avg_confidence >= 0.6 and len(entity_facts) >= 2:
    proposal_type = "Create"
    target_level = source_level + 1  # L1→L2
elif avg_confidence >= 0.9:
    proposal_type = "Refine"
    target_level = source_level
else:
    proposal_type = "Split"
    target_level = source_level
```

**条件**：
- Strengthen: confidence ≥ 0.8 AND facts ≥ 3
- Create: confidence ≥ 0.6 AND facts ≥ 2
- Refine: confidence ≥ 0.9
- Split: 其他情况

### 5.2 EvolutionService 的交互

```python
# evolution_service.py (simplified)
async def evolve_entity_history(self, entity_id, workspace_id, time_window_days=30):
    # Query L1 MemoryNodes by entity_id
    l1_nodes = await self.memory_repo.find_by_entity(entity_id, level=1)
    
    # Check threshold
    if len(l1_nodes) >= 3 and avg_confidence >= 0.8:
        # Create L2 Pattern
        ...
```

**关键区别**：
- ReflectionService：基于当前 batch 的 facts
- EvolutionService：基于历史 L1 MemoryNodes

**潜在冲突**：
- ⚠️ 如果 ReflectionService 生成 L2（target_level=2），EvolutionService 也可能生成 L2
- ✅ 但当前大部分 Proposal 会是 target_level=1（因为 facts 分散）

---

## 6. 数据质量问题的根源

### 6.1 Entity Resolution 缺陷

**可能的原因**：
1. FormationService 的 entity resolution 逻辑有缺陷
2. LLM 在提取 entity 时不稳定
3. Entity canonical_name 标准化问题（大小写、空格等）

### 6.2 验证：检查第二个大 Entity "Generate"

```sql
-- Generate Entity 的内容样本
ac5264a7... | 我这电脑可不可以实现，手机控制开关机...
24717317... | 其他应用不可以使用么
5283639c... | powercfg /a（休眠状态查询）
fc003215... | 不要暴力的插座。主板信息 ASUSTeK...
d0e4b804... | mercusys AX1800路由器。外网唤醒...
```

**分析**：
- 这些内容都与"Generate"（生成）无关
- 涉及远程控制、电源管理、硬件信息、路由器等
- 再次确认 Entity Resolution 存在问题

---

## 7. 风险评级

### 7.1 Cross-batch Omission

| 风险等级 | 原因 |
|----------|------|
| **HIGH** | 2,200 个 Windows candidates 分散在 220 个 batch，facts 无法累积 |

### 7.2 Duplicate Proposal

| 风险等级 | 原因 |
|----------|------|
| **MEDIUM** | Unique constraint 防止完全重复，但不同 candidate 可能生成多个相关 Proposal |

### 7.3 Target Level Distortion

| 风险等级 | 原因 |
|----------|------|
| **HIGH** | 大 Entity 的 facts 分散，可能导致本应生成 L2 的情况只生成 L1 |

### 7.4 L2/L3 Conflict

| 风险等级 | 原因 |
|----------|------|
| **LOW** | 当前大部分 Proposal 会是 target_level=1（因为 facts 分散），L2/L3 创建条件难满足 |

### 7.5 Overall Risk

| 评级 | 原因 |
|------|------|
| **CONDITIONAL** | 可以运行，但需要监控和后续优化 |

---

## 8. 最终执行建议

### 方案 A：直接执行 Phase 26-D（GO WITH GUARDRAILS）

**理由**：
1. 当前数据质量问题（Entity Resolution 错误）需要先解决
2. 即使存在 cross-batch 问题，大部分 Entity 只有 1-5 个 candidates
3. Windows 的 2,200 个 candidates 虽然有问题，但 Split/Refine proposals 仍会生成

**监控项**：
1. Proposal 生成率（预期 10-30%）
2. target_level 分布（预期大部分是 1）
3. 重复 Proposal 数量（应该为 0）

### 方案 B：先修复 Entity Resolution（RECOMMENDED）

**理由**：
1. 当前 Entity Resolution 有严重质量问题
2. 2,200 个 Windows candidates 实际上应该分散到多个实体
3. 如果不修复，Reflection 结果没有意义

**需要的修改**：
1. 改进 FormationService 的 entity resolution 逻辑
2. 添加 entity deduplication/merge 机制
3. 重新运行 Clean Rebuild

**时间估计**：2-4 小时开发 + 测试

### 方案 C：按内容相似度重新分组（长期方案）

**理由**：
1. 当前 Entity Resolution 基于 LLM 提取的 entity name
2. 不同主题的 conversation 被错误归一到同一 entity
3. 应该基于内容相似度重新分组

**实现**：
1. 计算 candidate content 的 embedding
2. 按相似度聚类
3. 重新分配 entity_id

**时间估计**：1-2 天开发

---

## 9. 建议的立即行动

### 短期（当前阶段）

1. **接受现状，执行 Phase 26-D**
   - 使用当前 Entity 分配
   - 监控 Proposal 生成情况
   - 记录问题供后续修复

2. **关键监控指标**
   - Proposal 生成率
   - target_level 分布
   - 是否有异常多的 Split proposals

### 中期（Phase 26 完成后）

1. **修复 Entity Resolution**
   - 调查为什么 2,200 个不相关 candidates 被归一到 "Windows"
   - 改进 FormationService 的 entity resolution 逻辑

2. **优化 Reflection 聚合模型**
   - 实现 entity-level 的 fact 累积
   - 支持跨 batch 的历史查询

### 长期（架构改进）

1. **统一 L2/L3 创建路径**
   - 解决 CONFLICT-001（ReflectionService vs EvolutionService）

2. **改进数据质量监控**
   - 添加 entity 内容多样性检查
   - 自动检测 entity resolution 异常

---

## 10. 总结

| 检查项 | 结果 |
|--------|------|
| **Cross-batch omission** | ⚠️ **HIGH**（但大部分 entity 小，影响有限） |
| **Duplicate proposal** | ⚠️ **MEDIUM**（unique constraint 保护） |
| **Target level distortion** | ⚠️ **HIGH**（大 entity facts 分散） |
| **L2/L3 conflict** | ✅ **LOW**（当前难触发） |
| **Data quality** | 🚨 **CRITICAL**（Entity Resolution 严重缺陷） |
| **Overall** | ⚠️ **CONDITIONAL GO** |

**建议**：
1. ✅ 可以先执行 Phase 26-D（全量 Proposal Formation）
2. ⚠️ 但必须在完成后立即调查 Entity Resolution 问题
3. 🚨 如果不修复 Entity Resolution，后续所有记忆质量都会受影响

---

*Report generated: 2026-08-15 01:45 UTC*
*Auditor: Phase 26-B.3 Large-Entity Reflection Risk Audit*
