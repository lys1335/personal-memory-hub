# 字节码缓存污染问题

## 问题描述

当使用 Docker volume 挂载源码时，旧的 `.pyc` 文件会导致 `NameError`。

## 症状

- `NameError: name 'datetime' is not defined`
- `NameError: name '_perf_cache' is not defined`
- 服务反复重启循环
- Dashboard 显示断开连接

## 根因

1. `__pycache__` 目录所有者是 `root:root`，权限 755
2. 应用运行用户是 `appuser` (uid=999)
3. Python 优先使用 `.pyc` 文件
4. 旧 `.pyc` 文件没有新导入

## 证据

```bash
docker exec memory-hub-app stat /app/src/backend/__pycache__/app.cpython-311.pyc
# Modify: 2026-08-02 11:37:48 (旧文件)

docker exec memory-hub-app stat /app/src/backend/app.py
# Modify: 2026-08-10 10:27:31 (新文件)
```

## 修复方案

### 方案 1: 防止写入缓存（推荐）

在 `docker-compose.yml` 中添加：
```yaml
environment:
  PYTHONDONTWRITEBYTECODE: "1"
```

### 方案 2: 启动脚本自动清理

在 `backend/scripts/start.sh` 中添加：
```bash
export PYTHONDONTWRITEBYTECODE=1
find /app/src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
```

### 方案 3: Dockerfile 构建时清理

在 `Dockerfile` 中添加：
```dockerfile
RUN find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
```

## 验证

```bash
# 检查环境变量是否生效
docker exec memory-hub-app python3 -c "import sys; print('PYTHONDONTWRITEBYTECODE:', sys.flags.dont_write_bytecode)"
# 应输出: PYTHONDONTWRITEBYTECODE: 1

# 检查缓存目录是否存在
docker exec memory-hub-app find /app/src -type d -name "__pycache__" | wc -l
# 应输出: 0
```

## 相关文件

- `backend/scripts/start.sh` — 启动脚本（包含缓存清理）
- `backend/Dockerfile` — Dockerfile（构建时清理）
- `docker-compose.yml` — 环境变量配置
