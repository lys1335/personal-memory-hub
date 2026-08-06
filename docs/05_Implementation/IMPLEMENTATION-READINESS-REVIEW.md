# Personal Memory Hub — Implementation Readiness Review

> **Version**: 1.0
> **Date**: 2026-08-05
> **Type**: Read-Only Analysis
> **Status**: Complete

---

## Task: 三个问题回答（不修改任何文件）

---

## 问题一：当前代码与冻结后架构的差距（按优先级排序）

### 🔴 P0: 阻断性 Bug

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 1 | L2 节点 entity_id = NULL | `app.py:approve_proposal()` | L2 节点无法进入 candidates 表，L2→L3 演化完全失败 |
| 2 | source_level 未贯通 | `reflection_engine.py:_generate_proposals()` | 所有 Proposal 的 source_level 默认为 1，L2→L3 目标层级错误 |
| 3 | candidates 表需手动填充 | `scripts/create_candidates_batch.py` | 系统无法自动演化，必须手动运行脚本 |

### 🟠 P1: 严重问题

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 4 | EvidenceEvolution Engine 不存在 | 代码中无此 Engine 类 | 违反架构文档，Information Extraction 仍在 ReflectionEngine 中 |
| 5 | _extract_facts() 在 ReflectionEngine 中 | `reflection_engine.py:141-230` | 职责混淆，违反单一职责原则 |
| 6 | LLM Prompt 混合提取和推理 | `reflection_provider.py` | Prompt 目标不清晰，可能影响输出质量 |
| 7 | candidates.status 未更新 | `reflection_service.py:613` | 已处理的 Candidate 仍为 'candidate' 状态，导致重复处理 |

### 🟡 P2: 中等问题

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 8 | 11220 个 Evidence entity_id = NULL | 数据库 | 数据质量问题，部分 Evidence 无法关联到 Entity |
| 9 | `_acquire_scope()` 返回 dict key 不一致 | `reflection_service.py:636, 682` | 使用 "level" 而非 "source_level"，导致后续提取失败 |
| 10 | 无 EvidenceEvolution LLM Prompt 定义 | 代码中无此 Prompt | 新 Engine 实现时需提供 |

### 🟢 P3: 低优先级

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 11 | 无单元测试覆盖新架构 | 测试目录 | 重构后需补充测试 |
| 12 | 文档中仍有旧术语残留 | 部分文档 | 需清理 Light/Heavy Reflect 术语 |

---

## 问题二：实现 Bug vs 架构重构分类

### 纯实现 Bug（可独立修复）

| # | 问题 | 修复方式 | 工作量 |
|---|------|----------|--------|
| 1 | L2 entity_id = NULL | `approve_proposal()` 中设置 entity_id | 10 行代码 |
| 2 | source_level 未贯通 | `_generate_proposals()` 从 candidate 获取 source_level | 5 行代码 |
| 3 | candidates.status 未更新 | `_save_proposals()` 后更新 Candidate 状态 | 3 行代码 |
| 4 | dict key 不一致 | 统一使用 "source_level" | 2 处修改 |

**小计**：约 20 行代码，1-2 小时

### 架构重构（需系统性变更）

| # | 问题 | 修复方式 | 工作量 |
|---|------|----------|--------|
| 5 | EvidenceEvolution Engine 不存在 | 创建新类，移动提取逻辑 | 2-3 天 |
| 6 | _extract_facts() 位置错误 | 移至新 Engine，更新 Service 调用 | 1 天 |
| 7 | LLM Prompt 混合 | 拆分 Extraction Prompt 和 Reasoning Prompt | 1 天 |
| 8 | 手动脚本依赖 | 建立自动生成机制，集成到 cron | 1 天 |

**小计**：约 5-6 天

---

## 问题三：代码重构顺序

### Phase 0: 修复阻断性 Bug（必须先行）

**目标**：使 L2→L3 演化可以工作

```
Step 1: 修复 approve_proposal() 设置 entity_id
  - 文件：app.py
  - 位置：约第 229-250 行
  - 修改：INSERT 语句中添加 entity_id 字段

Step 2: 修复 source_level 传播
  - 文件：reflection_engine.py
  - 位置：_generate_proposals() 方法
  - 修改：从 candidate dict 获取 source_level，不再默认为 1

Step 3: 修复 dict key 一致性
  - 文件：reflection_service.py
  - 位置：_acquire_scope() 返回的 dict
  - 修改：统一使用 "source_level" 而非 "level"

Step 4: 修复 Candidate 状态更新
  - 文件：reflection_service.py
  - 位置：_save_proposals() 后
  - 修改：将已处理的 Candidate 状态更新为 'processed'
```

**验证**：
- [ ] 运行 `docker restart memory-hub-app`
- [ ] 执行一次 reflection API 调用
- [ ] 检查 proposals 的 source_level 和 target_level 是否正确
- [ ] 检查 L2 节点是否有 entity_id

---

### Phase 1: 创建 EvidenceEvolution Engine

**目标**：将 Information Extraction 职责从 ReflectionEngine 拆分

```
Step 1: 创建 EvidenceEvolutionEngine 类
  - 文件：backend/src/backend/engine/evidence_evolution_engine.py
  - 内容：
    - evolve() 方法：主入口
    - extract_entities()：LLM 调用
    - discover_patterns()：Rule 聚类
    - aggregate_evidence()：Rule 聚合
    - estimate_confidence()：Rule 计算

Step 2: 移动 _extract_facts() 逻辑
  - 从 reflection_engine.py 移动到 evidence_evolution_engine.py
  - 修改输入参数：从 facts 列表变为 evidence 列表
  - 修改输出：返回 EvolutionResult 对象

Step 3: 定义 Extraction LLM Prompt
  - 文件：backend/src/backend/shared/prompts/extraction_prompt.py
  - 内容：仅包含信息提取，不包含推理
```

**验证**：
- [ ] 单元测试：extract_entities() 返回正确格式
- [ ] 单元测试：discover_patterns() 正确聚类
- [ ] 集成测试：evolve() 端到端工作

---

### Phase 2: 更新 ReflectionEngine

**目标**：收窄 ReflectionEngine 职责为纯 Reasoning

```
Step 1: 移除 _extract_facts() 方法
  - 文件：reflection_engine.py
  - 操作：删除或注释掉

Step 2: 更新 reflect_pipeline() 签名
  - 输入：candidates（已提取的候选对象）
  - 不再接受 raw evidence

Step 3: 更新 _generate_proposals()
  - 从 candidate 获取 source_level
  - 确保 target_level = source_level + 1
```

**验证**：
- [ ] 单元测试：reflect_pipeline() 不调用 LLM 进行提取
- [ ] 单元测试：source_level 正确传播
- [ ] 集成测试：Candidate → Proposal 流程正确

---

### Phase 3: 更新 ReflectionService

**目标**：编排 EvidenceEvolution → Reflection → Approval 流程

```
Step 1: 添加 _run_evolution_pipeline() 方法
  - 调用 EvidenceEvolutionEngine
  - 保存 Candidate 到数据库

Step 2: 更新 reflect() 方法
  - 先调用 _run_evolution_pipeline()
  - 再调用原有的 reflection 逻辑

Step 3: 添加 _save_candidates() 方法
  - 批量保存 Candidate 到数据库
  - 处理冲突和重复
```

**验证**：
- [ ] 单元测试：reflect() 先创建 Candidate 再生成 Proposal
- [ ] 集成测试：完整 Pipeline 工作
- [ ] 端到端测试：L1→L2→L3 自动演化

---

### Phase 4: 废弃手动脚本

**目标**：移除 create_candidates_batch.py 依赖

```
Step 1: 标记脚本为废弃
  - 文件：scripts/create_candidates_batch.py
  - 添加注释：@DEPRECATED

Step 2: 更新 cron 任务
  - 文件：logs/cron_tasks.json
  - 确保使用自动演化

Step 3: 文档更新
  - 更新 README
  - 更新部署文档
```

**验证**：
- [ ] 确认无代码引用废弃脚本
- [ ] Cron 任务正常运行
- [ ] 文档更新完成

---

### Phase 5: 测试与文档

**目标**：确保重构质量

```
Step 1: 编写单元测试
  - EvidenceEvolutionEngine 测试
  - ReflectionEngine 更新测试
  - ReflectionService 编排测试

Step 2: 编写集成测试
  - 端到端 Pipeline 测试
  - L1→L2→L3 多级演化测试

Step 3: 文档更新
  - 更新架构文档（已完成）
  - 更新 API 文档
  - 更新部署指南
```

**验证**：
- [ ] 所有测试通过
- [ ] 文档与代码一致
- [ ] 无回归问题

---

## 总工作量估算

| Phase | 工作量 | 依赖 |
|-------|--------|------|
| Phase 0: 修复 Bug | 2-3 小时 | 无 |
| Phase 1: 创建 Engine | 2-3 天 | Phase 0 |
| Phase 2: 更新 ReflectionEngine | 1 天 | Phase 1 |
| Phase 3: 更新 Service | 1 天 | Phase 2 |
| Phase 4: 废弃脚本 | 0.5 天 | Phase 3 |
| Phase 5: 测试与文档 | 2 天 | Phase 4 |

**总计**：约 6-7 天

---

## 风险与建议

### 高风险项

1. **L2 entity_id 修复**：必须在 Phase 0 完成，否则 L2→L3 无法工作
2. **source_level 传播**：必须确保所有 Proposal 都有正确的 source_level

### 中风险项

1. **LLM Prompt 变更**：提取 Prompt 变更可能影响输出质量，需充分测试
2. **向后兼容**：确保现有 Candidate 数据可以继续处理

### 建议

1. **先修复 Bug，再做重构**：Phase 0 是必须的，否则重构后仍无法工作
2. **分阶段部署**：每个 Phase 完成后部署验证，不要一次性全部部署
3. **保留回滚方案**：重构前备份数据库和代码

---

*本分析报告仅用于决策参考，不包含任何代码修改。*
