# E7 - 定时任务初始化 (Cron Task Initialization)

> **日期**: 2026-08-01  
> **状态**: MVP 初版

---

## 一、概述

本方案定义了 Personal Memory Hub 启动时的定时任务初始化逻辑，确保系统默认配置演化定时任务。

---

## 二、初始化逻辑

### 2.1 启动时检查

应用启动时，检查是否存在默认演化任务：

```python
# backend/src/backend/app.py

_DEFAULT_EVOLUTION_TASK = {
    "name": "记忆演化",
    "type": "evolution",
    "interval_seconds": 3600,  # 每小时执行一次
    "enabled": True,
    "payload": {
        "workspace_id": "fd0223ed-7aa2-491e-8db5-b0de71b75219",
        "limit": 50
    }
}


def _initialize_default_tasks():
    """初始化默认定时任务。"""
    global _cron_tasks
    
    # 检查是否已存在演化任务
    has_evolution = any(
        t.get('type') == 'evolution' for t in _cron_tasks.values()
    )
    
    if not has_evolution:
        # 创建默认演化任务
        import uuid as _uuid
        task_id = str(_uuid.uuid4())[:8]
        _cron_tasks[task_id] = {
            "id": task_id,
            "name": _DEFAULT_EVOLUTION_TASK["name"],
            "type": _DEFAULT_EVOLUTION_TASK["type"],
            "interval_seconds": _DEFAULT_EVOLUTION_TASK["interval_seconds"],
            "enabled": _DEFAULT_EVOLUTION_TASK["enabled"],
            "payload": _DEFAULT_EVOLUTION_TASK["payload"],
            "last_run": None,
            "status": "idle",
            "created_at": datetime.utcnow().isoformat()
        }
        _save_cron_tasks()
        logger.info(f"[CRON] Initialized default evolution task: {task_id}")
```

### 2.2 调用时机

在 `_load_cron_tasks()` 之后调用：

```python
# Load on startup
_load_cron_tasks()
_initialize_default_tasks()  # 新增
```

---

## 三、任务配置说明

### 3.1 默认配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `name` | "记忆演化" | 任务名称 |
| `type` | "evolution" | 任务类型 |
| `interval_seconds` | 3600 | 执行间隔（1小时） |
| `enabled` | True | 默认启用 |
| `limit` | 50 | 每次处理记忆数量 |

### 3.2 可配置项

通过环境变量覆盖默认值：

```yaml
# docker-compose.yml
environment:
  CRON_EOLUTION_INTERVAL: ${CRON_EOLUTION_INTERVAL:-3600}
  CRON_EVOLUTION_LIMIT: ${CRON_EVOLUTION_LIMIT:-50}
```

---

## 四、测试阶段 vs 生产阶段

### 4.1 测试阶段

- **自动批准**: 关闭（默认人工审批）
- **执行间隔**: 较短（如 300s = 5分钟）
- **日志级别**: DEBUG（详细记录演化过程）

### 4.2 生产阶段

- **自动批准**: 可开启（稳定后默认自动）
- **执行间隔**: 较长（如 3600s = 1小时）
- **日志级别**: INFO（仅记录关键事件）

### 4.3 切换方式

通过 Dashboard 的"自动批准"复选框临时切换，或通过环境变量配置默认行为。

---

## 五、持久化与恢复

### 5.1 任务存储

任务配置持久化到文件：

```
{LOG_DIR}/cron_tasks.json
```

### 5.2 启动恢复

每次启动时：
1. 加载已有任务配置
2. 检查是否需要初始化默认任务
3. 启动后台调度器

---

## 六、实现建议

### 6.1 当前状态

- ✅ Cron API 已实现
- ✅ 后台调度器已实现（每30秒检查）
- ✅ 手动触发功能已实现
- ⏳ 初始化默认任务逻辑待实现

### 6.2 下一步

1. 实现 `_initialize_default_tasks()` 函数
2. 添加环境变量支持
3. 在 Dashboard 显示默认任务创建提示

---

*本方案为 MVP 初版，后续可根据实际运行数据调整默认配置。*
