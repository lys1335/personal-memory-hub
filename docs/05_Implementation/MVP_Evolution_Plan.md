# Memory Evolution MVP 实现方案

## 一、项目定位与边界

根据文档 `07_Boundary_Review` (P1-P9) 和 `ENG-002/003`：
- **Memory Hub 是 Witness，不是 Actor**：只观察、记录、组织、演化记忆，不做决策或推荐
- **Agent 始终在 Memory Hub 外部**：Ollama (qwen3:4b) 作为 LLM provider，不在 Memory Hub 内部嵌入 Agent 逻辑
- **Reflection 是演化，不是突变**：产生的是领域决策/建议，由 Engine 完成实际变更

## 二、当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| 数据摄入 (`MemoryService.capture`) | ✅ 已完成 | REST API + 批量导入 |
| 向量检索 (`QueryService.search`) | ✅ 已完成 | 语义搜索 + 重排 |
| 定时任务调度 (`TaskRuntime`) | ✅ 已完成 | Cron API + Dashboard UI |
| 日志查看器 | ✅ 已完成 | 后端日志写入 + Dashboard 展示 |
| MemoryEngine (Archive/Evidence) | ⚠️ 骨架 | 表结构存在，未实现核心逻辑 |
| EntityEngine | ❌ 未实现 | 实体解析/身份管理 |
| ReflectionEngine | ❌ 未实现 | 核心：事实提取、实体解析、兴趣分析、投影更新 |
| ReflectionService | ❌ 未实现 | Reflection 工作流编排 |
| QueryService (Projection) | ❌ 未实现 | 记忆金字塔抽象层级生成 |

## 三、MVP 目标

实现 **Memory Evolution 的最小可验证闭环**：

```
定时任务触发 → Ollama 调用 qwen3:4b (Modelfile) → 
事实提取 → 实体解析 → 兴趣分析 → 投影更新 → 
日志输出 + DB 验证
```

**关键约束**：
1. MVP 阶段 **不污染正式数据库**，先在 Sandbox 环境验证
2. 使用 **本地 Ollama Modelfile** 而非外部 AI（符合用户之前决策）
3. 输出以 **日志** 为主，DB 写入仅在人工确认后执行

## 四、实现准则

### 4.1 架构分层遵守五层模型

```
Entry Layer (REST/Cron Trigger)
  ↓
Service Layer (ReflectionService - MVP 仅编排)
  ↓
Engine Layer (ReflectionEngine - 核心算法)
  ↓
Repository Layer (SandboxRepo - MVP 专用)
  ↓
Database (Sandbox DB / 内存)
```

**严格遵守**：
- Engine 无数据库依赖（可独立单元测试）
- Service 编排 Engine + Repository
- 禁止跨层调用

### 4.2 服务独立性原则 (Service Independence)

- MVP 阶段只新增 `ReflectionService`，**不调用其他 Service**
- 通过 `Shared Domain Engine` 协作（ReflectionEngine → MemoryEngine → EntityEngine）
- EntityService MVP 范围：仅 `createEntity()` + `resolveEntity()`

### 4.3 幂等性与 Scope 锁

- 同一 Scope 同一时刻仅一个 Reflection 执行
- 失败跳过不 Resume（等待下一周期重新计算已积累 Evidence）
- 最大 Reflection Horizon：可配置，默认 Daily 10 天

### 4.4 L0 保护原则

- ReflectionService **绝不自主创建 L0**
- Recovery Baseline 只能源于用户交互或用户预授权
- 高层 Memory 存储演化解释，而非历史快照

### 4.5 错误隔离

- Reflection 是 Enhancement Capability
- 失败必须局部化，不能使已提交的 Memory 无效
- 重试必须是安全的（幂等）

### 4.6 增量传播

- 先更新本层（L1），再决定是否向上传播（L2→L3）
- 下层失败，上层立即停止传播
- 不重建整个金字塔

### 4.7 Sandbox First

- MVP 使用 **内存/Sandbox 存储** 而非直接写生产 DB
- 所有演化结果写入日志，供人工审查
- Dashboard 增加 "Evolution Review" 功能（确认/驳回演化建议）

## 五、MVP 实现步骤

### Phase E1: ReflectionEngine 骨架（核心）

**文件**：`backend/src/backend/engine/reflection_engine.py`

1. **FactExtractor** — 从 L0 Memories 中提取新事实
   - 输入：一批 L0 Memory 的 content
   - 输出：结构化事实列表（entity, relation, timestamp, confidence）
   - 实现：调用 Ollama `reflection-engine` Modelfile

2. **EntityResolver** — 识别事实中的实体并解析
   - 输入：事实列表
   - 输出：实体 ID 映射（new → created, existing → resolved）
   - 调用：EntityService.resolveEntity()

3. **InterestAnalyzer** — 分析用户兴趣变化
   - 输入：时间窗口内的 L0 Memories
   - 输出：兴趣趋势（上升/下降/稳定）、关键词权重

4. **ProjectionUpdater** — 生成高层 Memory 演化建议
   - 输入：事实 + 实体 + 兴趣分析
   - 输出：Memory Pyramid 更新建议（Create/Strengthen/Refine/Split）
   - 遵循：Semantic Evolution Decision（§7.2 of 10_4）

**Modelfile 设计**：
```
FROM qwen3:4b
PARAMETER temperature 0.3
SYSTEM """
You are a Memory Evolution Engine for Personal Memory Hub.
Your task is to analyze recent memories and produce structured evolution proposals.
Output ONLY valid JSON with fields: facts[], entities[], interest_trends[], proposals[]
"""
```

### Phase E2: ReflectionService 编排

**文件**：`backend/src/backend/service/reflection_service.py`

1. `reflect(scope="daily", limit=50)` — 编排完整 Reflection 流程
2. `getReflectionStatus(taskId)` — 查询执行状态
3. 返回：`ReflectionExecutionResult`（执行报告，非业务数据）

**编排流程**：
```
1. 获取待反思的 L0 Memories（按 scope 过滤）
2. FactExtractor.extract() → facts[]
3. EntityResolver.resolve(facts) → entity_map
4. InterestAnalyzer.analyze(facts, entity_map) → trends
5. ProjectionUpdater.propose(facts, entity_map, trends) → proposals[]
6. 写入 SandboxStorage（不写生产 DB）
7. 发布 DomainEvent: ReflectionCompleted
```

### Phase E3: Sandbox Storage + Review API

**文件**：`backend/src/backend/repository/sandbox_repository.py`

1. 内存级存储（或 SQLite 临时表）
2. 存储 Reflection 产出物：facts, entities, proposals
3. 提供 Review API：
   - `GET /api/review/proposals` — 列出待审建议
   - `POST /api/review/proposals/{id}/approve` — 批准并写入正式 DB
   - `POST /api/review/proposals/{id}/reject` — 驳回

### Phase E4: Cron Integration + Dashboard UI

1. Cron API 增加 `type: "evolution"` 时调用 `ReflectionService.reflect()`
2. Dashboard 新增 "Evolution Review" tab（在 Log tab 旁）
   - 显示待审建议列表
   - 一键批准/驳回
   - 批准后自动同步到正式 DB

### Phase E5: 日志集成

1. Reflection 每个步骤写入日志（INFO level）
2. 日志 Tab 增加 "evolution" 关键字过滤
3. Dashboard 自动刷新日志（每 5s）

## 六、验证标准

| 检查项 | 验收方式 |
|--------|----------|
| 定时任务触发 Reflection | Cron API 设置 interval=60s，观察日志输出 |
| FactExtractor 正确提取 | 注入已知测试数据，验证 JSON 输出 |
| EntityResolver 正确解析 | 验证实体 ID 映射正确 |
| InterestAnalyzer 趋势准确 | 对比手动标注结果 |
| ProjectionUpdater 建议合理 | 人工审查 proposals[] |
| Sandbox 隔离 | 确认不写入生产 memory_nodes 表 |
| Review API 批准生效 | 批准后 memory_nodes 出现新记录 |
| 日志完整性 | 日志 Tab 能看到全流程日志 |

## 七、与现有代码的关系

| 现有文件 | 改动 |
|----------|------|
| `app.py` | 新增 `/api/review/*` 端点 |
| `docker-compose.yml` | 无需改动（已有 cron API） |
| `dashboard_server.py` | 新增 `/api/review` 代理 |
| `dashboard-main.html` | 新增 Evolution Review tab |
| `.gitignore` | 无需改动 |

## 八、风险与缓解

| 风险 | 缓解 |
|------|------|
| Ollama 响应慢 | 异步执行 + timeout 控制 |
| LLM 输出不稳定 | temperature=0.3 + strict JSON schema |
| Sandbox 数据丢失 | 每次 Reflection 前导出到日志 |
| 实体冲突 | EntityService.resolveEntity() 处理 |
| 无限循环 | Scope 锁 + Maximum Reflection Horizon |
