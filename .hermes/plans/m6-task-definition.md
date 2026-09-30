# M6 共享抽取器合并 — 任务定义 v3

**状态**: TASK DEFINITION v3（基于 v2 + A1 helper API 决策；Step 1 已完成；Step 2 已 BLOCKED 一次；当前为 v3，Step 2 实施前需 @user 二次确认 A1 API 后再授权）
**生成时间**: 2026-09-07
**生成者**: @pm-hy3
**前置依赖**: D5-3 FINAL CLOSED @ commit `0e4cf20`
**调查来源**: `.hermes/plans/m1-m3-m6-investigation-report.md` §3 + §6 (M6)
**授权范围**: 当前无授权（Step 1 已通过 + Step 2 实施授权待 A1 API 二次确认）

---

## 0. v1 → v2 → v3 修订要点

| # | 项 | v1 | v2 | v3 | 裁决依据 |
|---|---|---|---|---|---|
| 1 | 文件数量 | "4 文件" | 5 个代码/测试文件 + 1 个 execution report = 6 个任务文件 | 不变 | @user 修正 1 |
| 2 | `_extract_content_text` 处理 | "删除函数体" | 保留函数，仅改为薄委托 | 不变 | @user 修正 2 |
| 3 | 行为等价性 baseline | 模糊 | Step 1 预检阶段取得 + 临时 harness + 不入 Git | 不变 | @user 修正 3 |
| 4 | `try_parse_python_dict` 顶层结果 | "dict" | 顶层 dict/list，失败 None | 不变 | @user 修正 4 |
| 5 | **helper API 增加 `min_length` 参数** | （无）| （无）| **`extract_multimodal_text(data, *, depth=0, max_depth=5, min_length=0) -> list[str]`** | @user A1 裁决：原 0e4cf20 中 app.py 与 chatgpt.py 既有行为**真不一致**（chatgpt 在 list-of-str 分支有 `len > 2`、app.py 无；两者在 dict `text` 分支均无 `len > 2`），单一无参数 helper 无法 byte-for-byte 复现两者；`min_length` 仅作用于 list-of-str 分支 |

### 0.1 A1 裁决详细动机（按 @user 要求明确记录）

#### 0.1.1 为什么必须增加 `min_length`

`extract_multimodal_text` 是**两个调用方**（`app.py` / `chatgpt.py`）共用的 helper，**这两个调用方在 0e4cf20 的既有行为真不一致**（PM 独立核查 0e4cf20 原文确认）：

| 维度 | app.py (0e4cf20:1863) | chatgpt.py (0e4cf20:375) |
|---|---|---|
| list-of-str 分支 | 仅 `item.strip()` | `item.strip() and len(item) > 2` |
| dict `text` 分支 | 仅 `val.strip()` | 仅 `val.strip()` |
| 返回类型 | `str`（`"\n".join(texts)`）| `list[str]` |

**单一无差别 `strip()` helper 无法精确复现 chatgpt 既有 list-of-str 过滤行为**。

#### 0.1.2 为什么不能采用无差别调用方过滤

最初尝试方案（在 chatgpt.py 调用方做 `texts = [t for t in texts if len(t) > 2]`）——**已 BLOCKED 一次**（deleg_fbd2e7bf）：

- F1 / F5 / F12 fixtures FAIL
- 根因：无差别过滤覆盖了原 chatgpt 在 `dict["text"]` 分支"仅 strip" 的既有行为
- 这违反 @user 硬性要求"不得借 M6 重构机会改变既有行为"

#### 0.1.3 `min_length` 的作用域严格限制

`min_length` **仅作用于 list-of-str 分支**，**不应用于 dict `text` 分支**：

```python
def extract_multimodal_text(data, *, depth=0, max_depth=5, min_length=0):
    if depth > max_depth or not isinstance(data, dict):
        return []
    texts = []
    for key, val in data.items():
        if key in _SKIP_KEYS:
            continue
        if key == "parts" and isinstance(val, list):
            for part in val:
                texts.extend(extract_multimodal_text(part, depth=depth+1, max_depth=max_depth, min_length=min_length))
        elif key == "text" and isinstance(val, str) and val.strip():  # dict text 分支：始终仅 strip()，不受 min_length 影响
            texts.append(val.strip())
        elif isinstance(val, dict):
            texts.extend(extract_multimodal_text(val, depth=depth+1, max_depth=max_depth, min_length=min_length))
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item.strip() and len(item) > min_length:  # list-of-str 分支：min_length 生效
                    texts.append(item.strip())
                elif isinstance(item, dict):
                    texts.extend(extract_multimodal_text(item, depth=depth+1, max_depth=max_depth, min_length=min_length))
    return texts
```

#### 0.1.4 A1 是为保持既有行为而增加的 API 参数，不是业务语义变更

- **不是新增过滤规则**：仅是把原 0e4cf20 两个调用方各自的 list-of-str 分支行为**精确参数化**
- **不改任何业务语义**：app.py 行为完全保留（min_length=0 = 仅 strip）；chatgpt.py 行为完全保留（min_length=3 = 复现原 list-of-str `len > 2`）
- **不需要 ADR**：纯内部重构 + 行为保持 0e4cf20 不变 + 公共契约零变更
- **不需要 Controlled Defrost**：未触及任何 Frozen 文档

---

## 1. 关键决策

| 项 | 决策 | 依据 |
|---|---|---|
| **目标** | 合并 `_extract_multimodal_text` 重复实现 | 调查报告 §3：两处独立实现（`app.py:1863` + `chatgpt.py:375`）|
| **公共 API 变更** | 零变更 | 报告 §5：M6 不触 Frozen；纯内部重构 |
| **Frozen 处理** | **NO CONTROLLED DEFROST REQUIRED** | 同 D5-3 模式：跨包共享 helper 归位，无业务语义变化 |
| **行为等价性** | 必须严格等价（逐 case 验证）| 报告 §6 M6 验证清单明确要求 + baseline 对比 |
| **测试策略** | 零修改现有测试 + 新增 2 个测试文件 | 公共 API 零变更 |
| **commit/push** | 不属于本次任务；需另行授权 | 沿用 D5-2/D5-3 闸门 |

---

## 2. 任务文件清单（v2 修正后）

### 2.1 实施阶段允许修改的 5 个代码/测试文件

| # | 文件 | 性质 | 变更类型 |
|---|---|---|---|
| 1 | `backend/src/backend/ingest/parser.py` | 代码 | 修改（新增 2 函数）|
| 2 | `backend/src/backend/app.py` | 代码 | 修改（删除 1 嵌套函数 + 改 1 委托函数 + 改 2 调用点）|
| 3 | `backend/src/backend/ingest/adapters/chatgpt.py` | 代码 | 修改（删除 1 实例方法 + 改 1 调用点）|
| 4 | `backend/tests/test_ingest_parser_multimodal.py` | 测试 | 新建 |
| 5 | `backend/tests/test_ingest_parser_helpers.py` | 测试 | 新建 |

### 2.2 文档产出（1 个，**非任务实施文件**）

| # | 文件 | 性质 |
|---|---|---|
| 6 | `.hermes/plans/m6-execution-report.md` | 实施报告（PM 工作记录，非 ADR）|

**总计 6 个任务文件**。

---

## 3. 范围与禁止

### 3.1 允许清单 ✅

| 类别 | 操作 |
|---|---|
| 新增函数 | 在 `backend/src/backend/ingest/parser.py` 新增 `extract_multimodal_text(data, *, depth=0, max_depth=5) -> list[str]`（**返回 list[str]**，统一约定）|
| 新增函数 | 在 `backend/src/backend/ingest/parser.py` 新增 `try_parse_python_dict(text: str) -> dict | list | None`（顶层为 dict 或 list，失败返回 None）|
| 删除 | `backend/src/backend/app.py:1863` 嵌套函数 `_extract_multimodal_text` |
| 删除 | `backend/src/backend/ingest/adapters/chatgpt.py:375` 实例方法 `_extract_multimodal_text` |
| **修改（保留函数）** | `backend/src/backend/app.py:1830 _extract_content_text` **保留**，仅改为薄委托：`try_parse_python_dict(content) → fallback 原 content → extract_multimodal_text(...) → "\n".join()` |
| 修改 | `backend/src/backend/ingest/adapters/chatgpt.py` 调用方改用 `parser.extract_multimodal_text` |
| 新增 | `backend/tests/test_ingest_parser_multimodal.py` 覆盖合并后行为 |
| 新增 | `backend/tests/test_ingest_parser_helpers.py` 覆盖 `try_parse_python_dict` |
| 文档 | 新增实施报告 `.hermes/plans/m6-execution-report.md`（**非 ADR**）|

### 3.2 禁止清单 ❌

- ❌ 不得修改任何 `Service` / `Engine` / `Repository` 公共方法签名
- ❌ 不得修改 `app.py` 现有 HTTP 端点的 URL / payload / 响应 schema
- ❌ 不得修改 `parser.py` 中既有的 `try_parse_json` / `sanitize_content` / `extract_text_segments` 行为
- ❌ 不得修改 `chatgpt.py` 中除 `_extract_multimodal_text` 之外的代码
- ❌ **不得删除 `_extract_content_text` 函数**（v2 修正 2：保留）
- ❌ 不得修改任何其它 service / engine / repository / alembic / DI 文件
- ❌ 不得删除或修改现有测试
- ❌ 不得引入新依赖（不修改 `pyproject.toml` / `requirements*.txt`）
- ❌ 不得"顺手修复"任何其它问题（lint、typo、风格、未关联 TODO）
- ❌ 不执行 `git commit` / `git push`（另行授权）
- ❌ 不修改 `docs/05_Implementation/` 下任何架构文档（无需 ADR — 纯内部重构）
- ❌ 不修改 `docs/CODEX_CONTEXT.md` / `phase*.md` / `ARCHITECTURE-FREEZE-CHECKLIST.md`
- ❌ 不修改 `MemoryService`（God Service 拆分另立任务，不纳入 M6）

### 3.3 baseline 边界（v2 修正 3）

- **Step 1 预检阶段**：用临时 harness / 临时运行方式读取当前 HEAD=`0e4cf20` 的两个原实现
- baseline 数据**不进入 Git**
- baseline 数据**不产生正式仓库修改**
- 实施后用相同 fixture 与新实现进行逐 case 输出比较
- **不为了 baseline 修改范围外代码**

---

## 4. 详细变更规格

### 4.1 新增 `parser.py` 函数

#### 4.1.1 `extract_multimodal_text`（v3 A1）

**位置**: `backend/src/backend/ingest/parser.py`（追加）

**签名**:
```python
def extract_multimodal_text(
    data: Any,
    *,
    depth: int = 0,
    max_depth: int = 5,
    min_length: int = 0,
) -> list[str]:
    """Recursively extract text segments from multimodal content structures.

    Used by app.py endpoint and chatgpt adapter to unify multimodal parsing.
    Returns list[str] (NOT joined string) — callers decide join strategy.

    min_length (v3 A1):
        Applies ONLY to the list-of-str branch (top-level list of strings).
        Does NOT apply to dict["text"] branch.
        Required to express the asymmetry between 0e4cf20 app.py (no len>2)
        and 0e4cf20 chatgpt.py (len>2 only in list-of-str branch).
    """
```

**实现要求**（基于调查 §3 事实 + A1 决策）：
- 跳过 key 集合（与原 `app.py:1863` / `chatgpt.py:375` 同款）：
  ```python
  _SKIP_KEYS = frozenset({
      "asset_pointer", "content_type", "metadata", "decoding_id",
      "direction", "tool_audio_direction", "frames_asset_pointers",
      "video_container_asset_pointer", "expiry_datetime",
  })
  ```
- 递归逻辑（与原实现同构 + A1）：
  - `data is None` → 返回 `[]`
  - `isinstance(data, str)` → 返回 `[data]`（非空时）
  - `isinstance(data, list)` → 递归每项
  - `isinstance(data, dict)` → 检查 `content_type`；非 multimodal 直接返回 `[]`；否则按 part/text 递归
  - `depth >= max_depth` → 返回 `[]`（防止无限递归）
- **`min_length` 作用域**（v3 A1 严格）：
  - **list-of-str 分支**（`elif isinstance(val, list)`）：`isinstance(item, str) and item.strip() and len(item) > min_length`
  - **dict `text` 分支**（`elif key == "text"`）：**仅 `val.strip()`**，**不应用 `min_length`**
  - **其它分支**（parts / 嵌套 dict / 嵌套 list / dict）：**不应用 `min_length`**

**调用方契约**（v3 A1）：
- `app.py` 调用：`extract_multimodal_text(content)`（`min_length=0` 默认）→ 行为与原 0e4cf20 app.py:1863 完全等价
- `chatgpt.py` 调用：`extract_multimodal_text(content, min_length=3)` → 行为与原 0e4cf20 chatgpt.py:375 list-of-str 分支完全等价
- 返回类型统一为 `list[str]`，各调用方按自身原有方式 `"\n".join` / 直接返回

#### 4.1.2 `try_parse_python_dict`（v2 修正 4）

**位置**: `backend/src/backend/ingest/parser.py`（追加）

**签名**:
```python
def try_parse_python_dict(text: str) -> dict | list | None:
    """Parse JSON or Python literal; return None on failure.

    Top-level result must be dict or list (anything else returns None).
    Falls back to ast.literal_eval if json.loads fails.
    Used by app.py _extract_content_text to handle both JSON and Python dict reprs.
    """
```

**实现要求**:
- 先尝试 `json.loads`
- 失败则 `ast.literal_eval`
- 两者均失败返回 `None`
- 顶层结果**必须为 dict 或 list**（其它类型如纯数字/字符串/布尔 → 返回 None）
- 不抛异常（与 `try_parse_json` 行为一致）
- 名称沿用 `try_parse_python_dict`（v2 修正 4）

### 4.2 `app.py` 修改

**位置**: `backend/src/backend/app.py`

#### 4.2.1 `_extract_content_text` 改为薄委托（v2 修正 2：保留函数）

**修改前**（line 1830）：
```python
def _extract_content_text(content: str) -> str:
    # _json.loads / ast.literal_eval fallback 逻辑
    parsed = try_parse(content)  # 或等价逻辑
    # ...
    return _extract_multimodal_text(parsed)  # line 1852
    # 或
    return _extract_multimodal_text(content)  # line 1859
```

**修改后**（v3 A1）：
```python
def _extract_content_text(content: str) -> str:
    """薄委托：try_parse_python_dict → fallback 原 content → extract_multimodal_text → join"""
    parsed = try_parse_python_dict(content)
    target = parsed if parsed is not None else content
    return "\n".join(extract_multimodal_text(target))  # min_length 默认 0，复现 0e4cf20 app.py:1863 行为
```

**关键边界**:
- **函数保留**（v2 修正 2）
- 仅改为薄委托：parser 解析 → fallback 原 content → helper 抽取 → join
- 保持原返回值类型 `str`
- **`min_length` 不显式传入**（使用默认 0），保持原 app.py 行为
- **行为等价**：原实现直接 `"\n".join(texts)`，新实现保持完全一致

#### 4.2.2 删除嵌套函数 `_extract_multimodal_text`

**删除范围**: `backend/src/backend/app.py:1863` 整段嵌套函数定义（约 30+ 行）

#### 4.2.3 添加 import

```python
from backend.ingest.parser import extract_multimodal_text, try_parse_python_dict
```

### 4.3 `chatgpt.py` 修改

**位置**: `backend/src/backend/ingest/adapters/chatgpt.py`

**修改前**:
```python
# line 375
def _extract_multimodal_text(self, data: dict[str, Any], depth: int = 0) -> list[str]:
    # ... 完整实现
    texts.extend(self._extract_multimodal_text(part, depth + 1))  # line 405
    # ...

# line 359
texts = self._extract_multimodal_text(content)
```

**修改后**（v3 A1）：
```python
from backend.ingest.parser import extract_multimodal_text

# line 364（调用点）— 仅此处必须传入 min_length=3
texts = extract_multimodal_text(content, min_length=3)  # 复现 0e4cf20 chatgpt.py:375 list-of-str 分支 len > 2 行为
if texts:
    return "\n".join(texts)

# 删除实例方法 _extract_multimodal_text（line 375-420+）
```

**关键边界**:
- 保持原返回值类型 `list[str]`（与 `parser` 函数一致）
- `self._extract_multimodal_text` 改为 `extract_multimodal_text`（无 `self`）
- **必须显式传入 `min_length=3`**：精确复现原 chatgpt 在 list-of-str 分支的 `len > 2` 行为
- **禁止**在 chatgpt.py 调用方对 helper 返回的全部 texts 做 `texts = [t for t in texts if len(t) > 2]` 这种**无差别全局过滤**——这会覆盖原 chatgpt 在 `dict["text"]` 分支"仅 strip" 的既有行为（v3 A1 明确禁止，参见 §0.1.2 BLOCKED 经验）
- **行为等价**（v3 A1 严格）：
  - 0e4cf20 chatgpt.py:375 list-of-str 分支：`item.strip() and len(item) > 2` ↔ 新实现 `min_length=3` 在 list-of-str 分支 `len(item) > min_length`
  - 0e4cf20 chatgpt.py:375 dict `text` 分支：`val.strip()` ↔ 新实现 dict `text` 分支仅 `val.strip()`（不受 min_length 影响）

### 4.4 新增测试

#### 4.4.1 `tests/test_ingest_parser_multimodal.py`

**位置**: `backend/tests/test_ingest_parser_multimodal.py`

**测试用例**（基于调查 §3 重复点分析）:

| 类别 | 测试 |
|---|---|
| 基础 | `extract_multimodal_text(None) == []` |
| 基础 | `extract_multimodal_text("hello") == ["hello"]` |
| 基础 | `extract_multimodal_text("") == []` |
| 列表 | `extract_multimodal_text(["a", "b"]) == ["a", "b"]` |
| 列表 | `extract_multimodal_text([{"text": "a"}, {"text": "b"}]) == ["a", "b"]` |
| dict 跳过 | `extract_multimodal_text({"asset_pointer": "x"}) == []` |
| dict 跳过 | `extract_multimodal_text({"metadata": "x"}) == []` |
| dict 跳过 | `extract_multimodal_text({"content_type": "image"}) == []`（非 multimodal） |
| dict multimodal | `extract_multimodal_text({"content_type": "multimodal_text", "parts": [{"text": "a"}, {"text": "b"}]}) == ["a", "b"]` |
| 嵌套 | `extract_multimodal_text({"parts": [{"parts": [{"text": "deep"}]}]}) == ["deep"]` |
| 深度限制 | `extract_multimodal_text({...max_depth levels...}) == []`（depth 5 截断） |
| 等价性 | `extract_multimodal_text(data) == chatgpt_原实现(data)`（用 Step 1 baseline 真实 fixture）|
| 等价性 | `"\n".join(extract_multimodal_text(data)) == app_原实现(data)`（用 Step 1 baseline 真实 fixture）|

#### 4.4.2 `tests/test_ingest_parser_helpers.py`

**位置**: `backend/tests/test_ingest_parser_helpers.py`

**测试用例**:

| 类别 | 测试 |
|---|---|
| 基础 JSON dict | `try_parse_python_dict('{"a": 1}') == {"a": 1}` |
| 基础 JSON list | `try_parse_python_dict('[1, 2]') == [1, 2]` |
| Python literal dict | `try_parse_python_dict("{'a': 1}") == {"a": 1}`（fallback to ast.literal_eval）|
| Python literal list | `try_parse_python_dict("[1, 2]") == [1, 2]` |
| 失败 | `try_parse_python_dict('not json or python') is None` |
| 失败 | `try_parse_python_dict('') is None` |
| 顶层非 dict/list | `try_parse_python_dict('"plain string"') is None` |
| 顶层非 dict/list | `try_parse_python_dict('42') is None` |
| 嵌套 | `try_parse_python_dict('{"a": [1, 2]}') == {"a": [1, 2]}` |

**约束**: 不修改任何现有测试。

---

## 5. 行为等价性验证

### 5.1 baseline 取得（v2 修正 3，**Step 1 预检阶段**）

**方法**：
1. 在临时 harness（独立 Python 脚本 / 临时文件中）加载当前 HEAD=`0e4cf20` 的两个原实现
2. 用一组真实 fixture（来自仓库现有测试数据 / 真实 chatgpt 样本）调用两个原实现
3. 记录两个原实现对每个 fixture 的输出
4. baseline 数据保存为**临时文件**（不入 Git、不修改任何正式仓库文件）

**关键边界**:
- baseline 仅用于实施后的对比
- **baseline 不进入 Git**
- **baseline 不产生正式仓库修改**
- **不为了 baseline 修改范围外代码**

### 5.2 验证方法（实施后）

| 步骤 | 操作 |
|---|---|
| 1 | 使用与 baseline 阶段相同的 fixture 集（12 个 fixtures）|
| 2 | 调用新实现 `parser.extract_multimodal_text(data, ...)`（按调用方不同传不同 `min_length`）|
| 3 | `app.py` 委托路径验证：`"\n".join(parser.extract_multimodal_text(parsed))` 应等价于原 `app.py:1863` 输出（`min_length` 默认 0）|
| 4 | `chatgpt.py` 调用路径验证：`parser.extract_multimodal_text(content, min_length=3)` 应等价于原 `chatgpt.py:375` 输出 |
| 5 | 逐 case byte-for-byte 比较 baseline 与新输出 |
| 6 | **特别覆盖**（v3 A1 严格行为验证）：<br>- F1 / F5 / F12：含 ≤2 字符串的 list-of-str 分支，验证 chatgpt min_length=3 过滤行为<br>- F2 / F4：dict `text` 分支产出的 ≤2 字符串，验证**两个调用方都保留**（不受 min_length 影响）|

### 5.3 关键等价点

- **返回类型一致**：
  - `app.py _extract_content_text` 委托：原返回 `str`（`"\n".join(texts)`）→ 新实现保持 `str`（`"\n".join(parser.extract_multimodal_text(...))`）
  - `chatgpt.py` 调用点：原返回 `list[str]`（`texts`）→ 新实现直接用 `parser.extract_multimodal_text(...)`（已返回 `list[str]`）
- **skip_keys 集合一致**：
  - 两处原实现含 9 个 skip key，新实现必须完全一致
- **递归深度限制一致**：
  - 两处原实现均默认 `depth=0, max_depth=5`，新实现保持一致
- **None / 空字符串处理一致**：
  - 调查未明确，需逐 case 验证

### 5.4 验证清单（LOCK 必需）

- [ ] `grep -rn "_extract_multimodal_text" backend/src/` → 0 命中（仅 `parser.py` 中函数名 `extract_multimodal_text` 不算）
- [ ] `grep -rn "def _extract_content_text" backend/src/backend/app.py` → **1 命中**（v2 修正 2：保留）
- [ ] `grep -rn "from backend.ingest.parser import" backend/src/` → 至少 2 命中（app.py + chatgpt.py）
- [ ] `pytest backend/tests/test_ingest_parser_multimodal.py -v` → 全部 PASS
- [ ] `pytest backend/tests/test_ingest_parser_helpers.py -v` → 全部 PASS
- [ ] `pytest backend/tests/ -x -q` → 全绿（703 passed / 0 failed / 0 errors，沿用 D5-3 基线）
- [ ] `git diff --stat` 范围仅含 5 个代码/测试文件
- [ ] 无 alembic / DI / service 其它文件 / engine / repository 变更
- [ ] 无现有测试变更
- [ ] 行为等价性：原 `app.py:1863` 与新 `parser.extract_multimodal_text` 对 baseline fixture 输出 byte-for-byte 一致
- [ ] 行为等价性：原 `chatgpt.py:375` 与新 `parser.extract_multimodal_text` 对 baseline fixture 输出 byte-for-byte 一致

---

## 6. Frozen 影响判定

### 6.1 检查清单

| Frozen 文档 | 是否触及 | 证据 |
|---|---|---|
| `ARCHITECTURE-FREEZE-CHECKLIST.md` | 否 | M6 不修改 Service/Engine/Repository 契约；不改 Pipeline 拓扑；不改术语 |
| `D2_Repository_Layer_Plan.md` | 否 | M6 不触及 Repository |
| `D3.7_Error_Handling_DTO_Models.md` | 否 | M6 不修改 Error Taxonomy |
| `D3.8_Service_Test_Suite.md` | 否 | M6 不修改 Service 测试 |
| `D4_*_Engine_Architecture.md` | 否 | M6 不修改 Engine |
| `phase21-7-historical-memory-evolution.md` | 否 | M6 不触及 evolution/ |
| `phase21-final-freeze-audit.md` | 否 | M6 不修改 evolution 业务 |
| `Terminology-Freeze` | 否 | M6 不修改术语 |

### 6.2 结论

**NO CONTROLLED DEFROST REQUIRED** — M6 纯内部重构（entry + ingest adapter 共用 helper），公共契约零变更。

---

## 7. 文档产出

### 7.1 实施报告

**位置**: `.hermes/plans/m6-execution-report.md`

**必含内容**:

1. **范围**: M6 实施范围与依据（指向 m1-m3-m6-investigation-report.md §3 + §6 M6）
2. **修改文件**: 5 个代码/测试文件（v2 修正后）
3. **行为等价性验证**: 逐 case 输出对比（baseline vs new）
4. **测试结果**: pytest 全绿（703 passed / 0 failed / 0 errors）
5. **未执行**: commit/push（另行授权）
6. **git diff --stat**: 完整输出
7. **LOCK 状态**: PASS / LOCKED

### 7.2 不需要的文档

- ❌ **不需要 ADR**：M6 是纯内部重构（与 D5-2 / D5-3 性质不同，不涉及跨包契约变化）
- ❌ **不需要更新 ARCHITECTURE-FREEZE-CHECKLIST**：架构原则未变
- ❌ **不需要更新 CODEX_CONTEXT**：Codex 工作记忆不属本任务范围

---

## 8. 执行顺序（单线程，v3 严格）

```
Step 1 — 预检（✅ 已完成，PASS）
  ├─ 1a-1g 全部通过；12 fixtures baseline 已取得（在 $LOCALAPPDATA/Temp/，不入 Git）
  └─ Step 2 实施授权前发现 v2 API 设计遗漏 min_length，已 BLOCKED 一次

Step 2 — 实施（⏸ 待 A1 API 二次确认 + 授权）
  ├─ 2a. 新增 parser.py 两个函数（extract_multimodal_text 含 min_length 参数 + try_parse_python_dict）
  ├─ 2b. 修改 app.py：删除嵌套函数 + 改 _extract_content_text 为薄委托（min_length 隐式默认 0）
  ├─ 2c. 修改 chatgpt.py：删除实例方法 + 改调用（必须显式 min_length=3，禁止无差别全局过滤）
  ├─ 2d. 12 fixtures 行为等价性逐 case 验证（v3 A1 §5.2 步骤 6 特别覆盖）
  └─ 2e. @pm-hy3 回报

Step 3 — 新增测试（待授权）
  ├─ 3a. 新增 test_ingest_parser_multimodal.py
  ├─ 3b. 新增 test_ingest_parser_helpers.py
  └─ 3c. @pm-hy3 回报

Step 4 — 验证（待授权）
  ├─ 4a. 运行所有新增测试
  ├─ 4b. 运行全量 pytest（703 passed / 0 failed / 0 errors 基线）
  ├─ 4c. 行为等价性逐 case 验证（baseline vs new）
  ├─ 4d. git diff --stat / grep 检查
  └─ 4e. @pm-hy3 回报 PASS / BLOCK

Step 5 — 文档产出（待授权）
  ├─ 5a. 写 .hermes/plans/m6-execution-report.md
  └─ 5b. @pm-hy3 报告最终 LOCK 状态

Step 6 — commit/push（不在本计划默认范围；待另行授权）
```

---

## 9. 风险与回滚

| 风险 | 触发条件 | 回滚策略 |
|---|---|---|
| 行为不等价 | baseline fixture 输出与新实现不一致 | `git checkout` 恢复 5 文件；上报 @user |
| 现有测试失败 | pytest 红 | 立即停止，不自行修复；`git checkout` 恢复 + 上报 |
| skip_keys 集合遗漏 | 新实现 skip 集合与原不一致 | 比对原 `app.py:1863` + `chatgpt.py:375` skip 集合；修复 |
| 递归深度不一致 | 边界 case 行为变化 | 显式测试覆盖 max_depth=5 场景 |
| `_extract_content_text` 被误删 | v2 修正 2 违反 | `git checkout` 恢复；该变更需 Step 2 重新派发 |
| `app.py` 端点响应变化 | HTTP 端点响应 schema 变化 | `git checkout` 恢复；该变更已超出 M6 范围 |
| 范围外文件被修改 | Worker 越权 | `git checkout` 恢复范围外；上报 @user |
| baseline 污染 Git | baseline 数据意外提交 | 立即 `git reset` 撤销；上报 @user |
| Worker 不可用 | API 限额 / 异常 | 上报 @user 等待整备 |
| 公共契约变化 | 函数签名 / 返回类型变化 | 立即停止；该变更需 ADR，超出 M6 范围 |

---

## 10. Step 1 预检详细任务（**当前已授权**）

### 10.1 预检内容

1. `cd F:\LI_YONGSHUN\AI\personal-memory-hub`
2. `git log -1 --oneline` — HEAD 应为 `0e4cf20`
3. `git status --short` — 应仅含 D5-3/D5-2 既有 untracked，无意外修改
4. `grep -n "extract_multimodal_text\|try_parse_python_dict" backend/src/backend/ingest/parser.py` — 应 0 命中
5. 读取 `backend/src/backend/app.py:1830-1910` 完整内容（`_extract_content_text` + `_extract_multimodal_text` 实现）
6. 读取 `backend/src/backend/ingest/adapters/chatgpt.py:350-430` 完整内容（`_extract_multimodal_text` 实现）
7. 记录 skip_keys 集合、递归边界（max_depth）、返回类型、None/空字符串处理
8. 用临时 harness 取得 baseline（**不入 Git**）：
   - 在 `/tmp/` 或 `LOCALAPPDATA/Temp/` 创建临时 Python 脚本
   - 加载原 `app.py:1863` 与 `chatgpt.py:375` 实现
   - 用一组真实 fixture 调用，记录输出
   - **临时文件不入仓库，不 commit**

### 10.2 异常检查

任一发生立即停止上报 @pm-hy3：
- HEAD 不是 `0e4cf20`
- 工作区出现意外变更
- `parser.py` 已含 `extract_multimodal_text` 或 `try_parse_python_dict`（已被他人添加）
- baseline 临时文件被意外 add 到 Git

### 10.3 输出要求

完成后 @pm-hy3，不 @user。必须包含：
- 步骤 2-8 完整命令输出
- skip_keys 集合、递归边界、返回类型记录
- baseline 临时文件路径（不入 Git）
- 预检结论：(A) 一致可继续 / (B) 发现问题等待裁决 / (C) 阻塞

### 10.4 硬性约束

- **不修改任何代码/测试/docs**
- **不 commit/push**
- **不进入 Step 2/3/4/5**
- **baseline 不入 Git**

---

## 11. 待 @user 裁决（v3 A1 修正后）

### 11.1 v2 阶段裁决（已确认）

1. ✅ M6 任务定义 v2 已确认（4 项修正已落实）
2. ✅ Step 1 预检授权（已通过）
3. ⏸ Step 2-5 实施框架（每步仍需单独授权）
4. ✅ 行为等价性 baseline 方法（Step 1 取得 + 临时 harness + 不入 Git）
5. ✅ 5 个代码/测试文件 + 1 个 execution report 任务范围
6. ✅ `_extract_content_text` 保留 + 薄委托
7. ✅ `try_parse_python_dict` 顶层 dict/list + 失败 None
8. ✅ Worker 选派：@arch-laguna（沿用 Step 1，熟悉 baseline）

### 11.2 v3 A1 阶段裁决（待 @user 二次确认）

| # | 裁决项 | 选项 |
|---|---|---|
| **A** | **A1 helper API 文字修正**（§4.1.1 + §0.1）| 接受 A1：`min_length` 参数 + list-of-str 分支作用域 + 显式调用方契约 |
| **B** | **是否授权进入 Step 2 实施**？| 待 A 确认后单独授权 |

**注**：当前 Step 2 实施**未授权**。已派 Step 2 + Step 2 修正两次均因 API 设计问题 BLOCKED，需 @user 二次确认 A1 后再授权第三次 Step 2 实施。

---

## 12. 修订历史

| 版本 | 时间 | 修订者 | 修订内容 |
|---|---|---|---|
| v1 | 2026-09-07 | @pm-hy3 | 初稿：4 文件 + 删除 `_extract_content_text` 函数 + 仅 app/chatgpt 单一 helper |
| v2 | 2026-09-07 | @pm-hy3 | @user 4 项修正：5+1 文件 / 保留 `_extract_content_text` 薄委托 / baseline 临时 harness / `try_parse_python_dict` 顶层 dict/list |
| v3 | 2026-09-07 | @pm-hy3 | A1 API 修正：helper 新增 `min_length` 参数（仅 list-of-str 分支生效），调用方按需显式传入；app 用 min_length=0，chatgpt 用 min_length=3 |
