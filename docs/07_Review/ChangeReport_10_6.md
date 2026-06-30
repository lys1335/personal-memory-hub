# Change Report 10_6 — Phase B Task Runtime Design

> **日期**: 2026-06-29
> **阶段**: Phase B — 实现设计（第六部分）
> **触发原因**: Phase B-6 开始，定义 Task Runtime 的工程实现设计
> **生成文档**: 10_6_Implementation_TaskRuntime.md

---

## 1. 变更概述

本次变更完成 Phase B-6 Task Runtime 的设计，定义了 Memory Hub 的通用任务执行基础设施。

核心设计决策：

1. Task Runtime 是基础设施，不是业务逻辑
2. 通用 Task 抽象，Runtime 不理解业务概念
3. Task Chaining 通过 Domain Event → Event Dispatcher → Task Registry → Task Factory → New Task
4. 最小状态机：Pending → Running → Completed / Failed → Retry → Dead
5. Retry（同一 Task）vs Re-trigger（新 Task）根本不同
6. At-Least-Once 执行保证，Task 实现应幂等
7. Scheduler 不是 Cron，是统一 Task 分发协调器
8. 四种触发源：Domain Event / Cron / Startup Recovery / User Async Request
9. 优先级队列（High / Normal / Low），预留执行容量
10. 三种失败分类：Transient / Permanent / Runtime Crash
11. Recovery 从不重新评估业务逻辑
12. Maintenance Manager 仅负责 Runtime 维护
13. 六个 Runtime 组件：Scheduler / Worker Manager / Event Dispatcher / Recovery Manager / Maintenance Manager / Task Registry
14. ExecutionContext 包含 taskId / traceId / retryCount / requestedBy
15. 仅暴露操作接口，不暴露业务接口
16. 可观测性分层：Runtime Metadata / Logging / Metrics / Dashboard
17. Infrastructure Isolation：Runtime 与业务逻辑完全隔离

---

## 2. 生成文档

### 2.1 10_6_Implementation_TaskRuntime.md

| 章节 | 内容 |
|------|------|
| §1 Purpose | Task Runtime 定位声明 |
| §2 Responsibility | 核心定位、明确禁止、正确定位 |
| §3 Task Model | Runtime Metadata、Payload 归属、Domain Agnostic |
| §4 Task Chaining | Event-Driven 链式模型、Task Registry 映射模式 |
| §5 Task Lifecycle | 最小状态机、Retry vs Re-trigger |
| §6 Idempotency | At-Least-Once、幂等策略 |
| §7 Scheduler | 统一 Task 分发协调器、四种触发源、优先级策略 |
| §8 Domain Event Consumption | Event Dispatcher + Task Registry 模式 |
| §9 Retry / Recovery | 三种失败分类、Exponential Backoff、Startup Recovery |
| §10 Background Maintenance | Maintenance Manager 职责与禁止项 |
| §11 Runtime Architecture | 六个组件、ExecutionContext |
| §12 Interfaces | 操作接口、Forbidden Interfaces |
| §13 Observability | 分层架构、数据类型 |
| §14 Service Collaboration | Service → Runtime 交互、Domain Event → Task 映射 |
| §15 Consistency Principles | Infrastructure Isolation、Error Handling、Concurrency |
| §16 Future Evolution | Planned + Potential |
| §17 Checklist | P0/P1/P2 检查项 |
| §18 Decision Summary | 29 项决策汇总 |
| §19 Appendix A | 5 个 Runtime Sequence Examples |
| §20 Design Validation | Example → Architecture Principles Mapping |

---

## 3. 回溯更新

| 文档 | 更新内容 |
|------|----------|
| **10_1_Implementation_Service_Layer** | 补充 TaskRuntime 到 Engine 清单（#13）；TaskService 编排改为 TaskRuntime；Service DAG 更新 TaskService → TaskRuntime；Engine DAG 补充 TaskRuntime |
| **06_Runtime_Architecture** | 补充 TaskRuntime 到 Engine 清单（#9）；Scheduler 职责更新（Service 而非 Engine）；新增 §6 Task Runtime Overview；队列能力补充 Priority + Task Registry |
| **10_2_Implementation_MemoryService** | 补充 TaskRuntime 交互模式（✅ Job Dispatch） |
| **10_4_Implementation_ReflectionService** | 补充 Forbidden Dependencies：ReflectionService → TaskRuntime（通过 Domain Event 路由） |
| **10_5_Implementation_EntityService** | 补充 Forbidden Dependencies：EntityService → TaskRuntime（通过 Domain Event 路由） |
| **13_Architecture_Guidelines** | 新增 G-039~G-049（共 11 条 Task Runtime Guideline），总数 38→49 |
| **README.md** | 补充 Task Runtime（10_6）到 Phase B 进度列表 |
| **INDEX.md** | 补充 10_6 条目，进度 15/15→16/16 |

---

## 4. 架构影响分析

### 4.1 新增组件

| 组件 | 类型 | 说明 |
|------|------|------|
| TaskRuntime | Infrastructure | 通用任务执行基础设施 |
| Scheduler | Component | 统一 Task 分发协调器 |
| Worker Manager | Component | Worker 生命周期管理 |
| Event Dispatcher | Component | Domain Event 路由 |
| Recovery Manager | Component | 启动恢复管理 |
| Maintenance Manager | Component | Runtime 维护 |
| Task Registry | Component | Event → Task 映射 |
| ExecutionContext | Component | 执行上下文 |

### 4.2 变更组件

| 组件 | 变更 | 说明 |
|------|------|------|
| Scheduler | 升级为 Task Runtime 一部分 | 不再是独立组件，是 Task Runtime 的子组件 |
| MemoryService | 补充 TaskRuntime 交互 | 通过 Task Registry 路由 Domain Event → Task |
| EntityService | 补充 TaskRuntime 交互 | 通过 Domain Event 触发异步维护 |
| ReflectionService | 补充 TaskRuntime 交互 | 通过 Domain Event 触发 Reflection Task |

### 4.3 不变组件

| 组件 | 说明 |
|------|------|
| Service Independence Principle（G-005） | 保持不变 |
| Shared Domain Engine Principle（G-006） | 保持不变 |
| Command/Query Separation（G-008） | 保持不变 |
| Database Schema | Task Runtime 不引入新表（复用 tasks 表） |

---

## 5. 附录：Runtime Sequence Examples

| 示例 | 说明 |
|------|------|
| Example 1 | User-triggered async task |
| Example 2 | Entity Merge → Reference Migration |
| Example 3 | L1 → L2 → L3 Reflection chain (Task Chaining) |
| Example 4 | LLM Timeout → Retry → Completed |
| Example 5 | Application Crash → Startup Recovery → Completed |

---

## 6. 设计验证

| 原则 | 验证方式 | 结果 |
|------|----------|------|
| Task Runtime 是基础设施 | Example 1: Service 决策，Runtime 执行 | ✅ |
| Domain Agnostic | Example 2: Runtime 不理解 Entity / Merge | ✅ |
| Task Chaining via Events | Example 2, 3: 通过 Domain Event 链式触发 | ✅ |
| Minimal Lifecycle | Example 4: Failed → Retry → Completed | ✅ |
| Retry vs Re-trigger | Example 3: Re-trigger；Example 4: Retry | ✅ |
| At-Least-Once Execution | Example 5: Crash 后 Recovery 重新执行 | ✅ |
| Recovery Never Re-evaluates | Example 5: 只恢复执行，不重新评估 | ✅ |
| Infrastructure Isolation | Example 1~5: Runtime 不涉及业务逻辑 | ✅ |

---

*本文档记录 Phase B-6 变更的全貌。*
