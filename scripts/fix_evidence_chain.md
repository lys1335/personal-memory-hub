# Evidence-Based Memory 架构修复计划

## 设计目标

实现完整的 Evidence-Based Memory 架构：

```
L4: Reflection (跨Node总结)
     │
L3: Memory Graph (Entity, Area, Relationship)
     │
L2: Node (Fact/Preference/Event - AI解释)
     │
L1: Evidence (原始记录 - Immutable Source)
     │
聊天记录/邮件/文档...
```

## 当前问题

| 问题 | 状态 | 影响 |
|------|------|------|
| entities 表为空 | ❌ | 所有记忆无实体关联 |
| areas 表为空 | ❌ | 无领域分类 |
| evidences 表为空 | ❌ | 无原始证据记录 |
| memory_evidences 为空 | ❌ | 无证据链 |
| memory_nodes.entity_id 全为 NULL | ❌ | 10,521条记录无实体关联 |
| 导入流程只创建Node | ❌ | 缺少 Evidence 层 |

## 修复方案

### Phase 1: 批处理修复现有数据（立即执行）

**目标**：为现有的 10,521 条 memory_nodes 补充 entity/area/evidence 信息

**步骤**：
1. 为每条 memory_node 创建 Evidence 记录（存储原始 content）
2. 使用 LLM 从 content 中提取 entity 和 area
3. 创建 Entity 和 Area 记录
4. 更新 memory_nodes.entity_id 和 memory_nodes.area_id
5. 创建 memory_evidences 关联记录

**脚本**：`scripts/fix_evidence_chain.py`

### Phase 2: 修改导入流程（下一个迭代）

**目标**：新导入的数据自动创建完整的证据链

**步骤**：
1. 修改 `ChatGPTImportAdapter`，增加 entity/area 提取逻辑
2. 修改 `MemoryService.capture_conversation()`，创建 Evidence 记录
3. 添加 LLM 提取 entity/area 的提示词

### Phase 3: 优化 Reflection 流程

**目标**：Reflection 使用完整证据链进行演化

**步骤**：
1. 修改 `ReflectionService._acquire_scope()`，优先选择有完整证据链的 Node
2. 在 evidence_chain 中同时包含 evidence_id

## 技术实现

### Database Schema（已存在）

```sql
-- evidence 表：存储原始记录
CREATE TABLE evidences (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    entity_id UUID REFERENCES entities(id),
    area_id UUID REFERENCES areas(id),
    user_id UUID REFERENCES user_profiles(id),
    evidence_type VARCHAR(50) NOT NULL,  -- conversation, import, manual
    content TEXT NOT NULL,               -- 原始内容
    raw_content TEXT,                    -- 原始JSON（多模态）
    confidence FLOAT,
    importance FLOAT,
    signal_strength FLOAT,
    source VARCHAR(50) NOT NULL,         -- chatgpt, open_webui, manual
    _meta JSONB
);

-- memory_evidences 表：Node → Evidence 关联
CREATE TABLE memory_evidences (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    memory_node_id UUID NOT NULL REFERENCES memory_nodes(id),
    evidence_id UUID NOT NULL REFERENCES evidences(id),
    relationship_type VARCHAR(50) NOT NULL,  -- supports, derived_from
    contribution_weight FLOAT NOT NULL
);
```

### Python 实现

```python
# evidence_repository.py - 新增方法
class EvidenceRepository(BaseRepository):
    async def create_evidence(
        self,
        workspace_id: UUID,
        content: str,
        raw_content: str | None = None,
        evidence_type: str = "import",
        source: str = "import",
        entity_id: UUID | None = None,
        area_id: UUID | None = None,
    ) -> UUID:
        """创建 Evidence 记录"""
        ...

# memory_service.py - 修改 capture_memory
async def capture_memory(
    self,
    *,
    workspace_id: UUID,
    content: str,
    entity_id: UUID | None = None,
    area_id: UUID | None = None,
    evidence_id: UUID | None = None,  # 新增参数
    ...
) -> CaptureResult:
    # 创建 MemoryNode
    memory_node = MemoryNode(...)
    memory_id = await self._memory_node_repo.create(memory_node)
    
    # 如果提供了 evidence_id，建立关联
    if evidence_id:
        await self._memory_node_repo.link_evidence(
            memory_id=memory_id,
            evidence_id=evidence_id
        )
    
    return CaptureResult(...)
```

## 执行顺序

1. ✅ 修改 `reflection_service.py` - 证据链追溯（已完成）
2. ✅ 修改 `app.py` - 证据加载 API 文本提取（已完成）
3. ⏳ 创建批处理脚本修复现有数据
4. ⏳ 修改导入流程支持完整证据链

## 验证标准

- [ ] entities 表有记录
- [ ] areas 表有记录
- [ ] evidences 表有记录
- [ ] memory_evidences 表有记录
- [ ] memory_nodes.entity_id 不再为 NULL
- [ ] 证据加载 API 返回正确的证据内容
- [ ] 演化评审显示完整的证据链
