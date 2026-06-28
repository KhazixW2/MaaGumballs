---
name: pipeline-option
description: Add runtime UI options (select/checkbox/switch/input) to interface.json. Two implementation styles: (1) wire to Python via context.get_node_data() for in-code decisions, or (2) pure pipeline_override on existing node fields (e.g. `next` array) for behavior-only changes that don't touch Python. Critical 3-place pattern: option definition + task option array + pre-defined pipeline node. Use when adding a new user-facing toggle, multi-choice selector, or custom input that must persist through MaaFramework's v2.3.0+ protocol.
---

# Pipeline Option 工作流

## TL;DR：3 处联动

新增一个 UI 选项需要**同时**改 3 个地方，缺一不可：

| # | 位置 | 内容 |
|---|------|------|
| 1 | `assets/interface.json` 的 `option` 字典 | 选项定义（type / cases / pipeline_override） |
| 2 | `assets/interface.json` 对应 task 的 `option: []` 数组 | 注册到具体任务（否则 UI 上看不到） |
| 3 | `assets/resource/base/pipeline/*.json` | **预定义**目标节点（pipeline_override 不会创建节点） |
| 4 | Python 代码（**仅模式 A 必需**） | `context.get_node_data()` 读取 + 业务分支；模式 E 用 pure override 可绕过 |

> ⚠️ **pipeline_override 只做属性合并，不会凭空创建节点。** 少了第 3 步，`context.get_node_data()` 会返回 `None`，运行时静默失败。

完整协议参考（嵌套 option、global_option、controller/resource 限制、占位符注入）：[references/protocol.md](references/protocol.md)

---

## 4 种 type 速查

| type | 选择 | override 字段 | 节点预定义形态 |
|------|------|---------------|---------------|
| `select` | 单选互斥 | `expected` | `recognition: "OCR"` + `expected: [...]` |
| `switch` | 二元 Yes/No | `enabled` | `{"enabled": bool}` |
| `input` | 自由文本 | `custom_action_param` | `action.param.custom_action_param` |
| `checkbox` | 多选 | `enabled` | `{"enabled": false}` |

## 选哪个模式？

| 你的需求 | 推荐模式 |
|---------|---------|
| 启用/禁用一个 Python 业务函数 | **A**（switch + Flag 节点 + Python 读 flag） |
| 从多个互斥选项里选一个值 | **B**（select + OCR 节点） |
| 同时启用多个独立的功能模块 | **C**（checkbox + 多个 Flag 节点） |
| 用户输入自定义文本 | **D**（input + 占位符注入） |
| 切换行为（点哪个按钮 / 走哪条 next 链）但不想改 Python | **E**（pure override 现有节点字段） |

> **黄金法则**：能 pure override 解决就不加 Flag + Python 改动 —— 改动面越小越好维护。

---

## 模式 A：开关（switch + Flag 节点）— 最常用

**适用**：开启/关闭某个功能。

### interface.json

```jsonc
"开启5月城堡相亲": {
    "type": "switch",
    "description": "是否开启5月自动相亲",
    "default_case": "Yes",
    "cases": [
        {
            "name": "Yes",
            "pipeline_override": { "Flag_EnableMarryTask": { "enabled": true } }
        },
        {
            "name": "No",
            "pipeline_override": { "Flag_EnableMarryTask": { "enabled": false } }
        }
    ]
}
```

### 配套 pipeline 节点（必须预定义！）

```jsonc
"Flag_EnableMarryTask": { "enabled": true }
```

### 注册到 task

```jsonc
"task": [{
    "name": "推年计划",
    "entry": "Auto_YearlyTask",
    "option": ["开启5月城堡相亲", /* 其他选项 */]
}]
```

### Python 读取（建议放在业务函数入口）

```python
def handle_marry_festival(context: Context) -> bool:
    """处理春林节相亲（5月）"""
    EnableMarryTask = context.get_node_data("Flag_EnableMarryTask").get("enabled")
    if not EnableMarryTask:
        logger.info("自动相亲已关闭，跳过")
        return True
    # ... 正常逻辑
```

---

## 模式 B：单选（select + OCR 节点）

**适用**：选择城市、关卡、模式等互斥选项。

### interface.json

```jsonc
"选择刷取任务国家": {
    "type": "select",
    "description": "选择要刷取任务的目标城市",
    "default_case": "雄月城",
    "cases": [
        { "name": "王座堡", "pipeline_override": { "EnterCity": { "expected": ["王座堡"] } } },
        { "name": "雄月城", "pipeline_override": { "EnterCity": { "expected": ["雄月城"] } } }
    ]
}
```

### 配套 OCR 节点

```jsonc
"EnterCity": {
    "recognition": "OCR",          // ⚠️ 必须是 OCR，否则 expected 不生效
    "expected": ["王座堡", "圣盾堡", "雄月城", "翠庭"],
    "roi": [58, 320, 600, 682],
    "action": "Click"
}
```

### Python 读取

```python
data = context.get_node_data("EnterCity")
city = data.get("recognition", {}).get("param", {}).get("expected", ["王座堡"])[0]
```

---

## 模式 C：多选（checkbox + 多个 Flag 节点）

**适用**：多条件检测（好苗子条件）、可叠加的功能模块。

### interface.json

```jsonc
"开启好娃提醒": {
    "type": "checkbox",
    "default_case": ["科内塔之怒"],
    "cases": [
        { "name": "科内塔之怒",   "pipeline_override": { "检测_科内塔之怒":     { "enabled": true } } },
        { "name": "太阳+科内塔之怒", "pipeline_override": { "检测_太阳+科内塔之怒": { "enabled": true } } }
    ]
}
```

### 配套节点（每个 case 一个，默认全 false）

```jsonc
"检测_科内塔之怒":      { "expected": ["koneita"],            "enabled": false },
"检测_太阳+科内塔之怒": { "expected": ["sun_and_koneita"],    "enabled": false }
```

### Python 读取（遍历收集）

```python
def _get_enabled_checks(context) -> list:
    enabled = []
    for key in ["检测_科内塔之怒", "检测_太阳+科内塔之怒"]:
        node = context.get_node_data(key)
        if node and node.get("enabled", False):
            expected = node.get("recognition", {}).get("param", {}).get("expected", [])
            if expected:
                enabled.append(expected[0])
    return enabled
```

---

## 模式 D：自由输入（input + 占位符注入）

**适用**：用户输入自定义关卡号、自定义黑名单任务等。

### interface.json

```jsonc
"自定义任务黑名单": {
    "type": "input",
    "inputs": [
        {
            "name": "任务名称",
            "pipeline_type": "string",
            "default": "",
            "verify": "^[^,，]*$",
            "pattern_msg": "不能包含逗号"
        }
    ],
    "pipeline_override": {
        "CustomTaskBlacklist": {
            "expected": ["{任务名称}"]   // {名称} 占位符被实际输入替换
        }
    }
}
```

### Python 读取

```python
data = context.get_node_data("CustomTaskBlacklist")
value = data.get("recognition", {}).get("param", {}).get("expected", [""])[0]
```

---

## 模式 E：行为覆盖（pure override 现有节点字段）— 最简

**适用**：行为切换映射到现有 pipeline 节点的**单个字段**（`next` 数组 / `action` 类型 / `recognition` 算法 / 任何可覆盖字段），且**不需要 Python 判断**。

**核心思路**：用户切换 UI 选项 → 改变 pipeline 节点的字段值 → 框架自身根据新值执行。**Python 代码完全不动。**

### 典型场景：开关决定点哪个按钮

```jsonc
"开启自动接受佣兵": {
    "type": "switch",
    "default_case": "No",
    "cases": [
        {
            "name": "Yes",
            "description": "直接点确认",
            "pipeline_override": {
                "Event_MercenaryJoin": {
                    "next": ["Event_MercenaryJoinConfirm"]
                }
            }
        },
        {
            "name": "No",
            "description": "直接点取消",
            "pipeline_override": {
                "Event_MercenaryJoin": {
                    "next": ["Event_MercenaryJoinCancel"]
                }
            }
        }
    ]
}
```

`Event_MercenaryJoin` 节点本身在 [event_utils.json](../../assets/resource/base/pipeline/event_utils.json) 里有完整定义（`recognition` / `expected` / `roi` / `timeout` 都在），`pipeline_override` 只覆盖 `next` 字段，其他字段保持原值。

### `next` 数组的单元素 vs 多元素语义

| 写法 | 语义 | 何时用 |
|------|------|-------|
| `["A"]` | **强约束**：只走 A | 行为已确定，单路径足够（**模式 E 的典型形态**） |
| `["A", "B"]` | **回退链**：优先 A，A 失败走 B | 兜底机制（"优先点确认，找不到才点取消"） |
| `["A", "B", "[JumpBack]C"]` | 失败后跳回 C 节点重试 | 复杂回退 |

### 可被 override 的字段

| 字段 | override 效果 | 典型用途 |
|------|--------------|---------|
| `next` | 改变后续节点列表 | 切换行为路径（模式 E 主力） |
| `action` | 改变点击/滑动/输入动作 | 切换操作类型 |
| `recognition` | 改变识别算法 | 切换识别方式（OCR ↔ Template） |
| `expected` | 改变识别期望值 | 配合 select 选值 |
| `roi` | 改变识别区域 | 适配不同界面尺寸 |
| `timeout` | 改变超时时间 | 适配不同网络/性能 |

> **关键认识**：上面这些字段都是普通 JSON 值，pipeline_override 一视同仁做深合并。**模式 A 用的 `enabled` 字段只是最常见的入口，不是唯一可 override 的字段。**

### 模式 A vs 模式 E 对比

| 场景 | 模式 A（Flag + Python） | 模式 E（pure override） |
|------|------------------------|----------------------|
| 行为由 Python `if` 控制 | ✅ 必须 | ❌ 绕远路 |
| 行为由 pipeline 字段决定 | ❌ 多此一举 | ✅ 最简 |
| 需要运行时根据 flag 走不同代码分支 | ✅ 唯一选择 | ❌ 不行 |
| 改动 Python 代码 | ✅ 需要 | ❌ 不需要 |
| 需要新加 Flag 节点 | ✅ 需要 | ❌ 不需要 |

### 实战决策流程

```
要加新选项
│
├─ 行为切换对应到一个 pipeline 节点的某个字段？
│   └─ ✅ 用模式 E（pure override）
│       示例：佣兵加入时点"确认"还是"取消"
│
└─ ❌ 行为在 Python 业务逻辑里
    └─ 用模式 A（Flag 节点 + Python 读 flag）
        示例：跳过整个 handle_sailing_festival 函数
```

---

## 补充：能用状态机就别写 Python orchestration

**MaaFramework 的 `next` + `[JumpBack]` 是为跨页面状态推进设计的原语**。如果一个流程的步骤可以**列举**为有限个页面状态（入口 → A → B → C → 战斗），优先用 JSON 状态机；不要写 Python 把 `context.run_task` 串起来。

详见 [.claude/skills/pipeline-guide/SKILL.md](../pipeline-guide/SKILL.md) 的「跨页面状态机」典型模式。

### 状态机 vs Python orchestration 对比

| 场景 | 状态机（推荐） | Python orchestration（次选） |
|------|--------------|--------------------------|
| 有限页面状态推进（如活动流程） | ✅ 链 `next` + `[JumpBack]` | ❌ 自己写 `for/while` 调度 |
| 按 flag 跳过整段函数 | ❌ 不适合 | ✅ 读 flag + 早返回 |
| 复杂的运行时分支逻辑 | ❌ 难表达 | ✅ Python 灵活 |

### 跨文件节点引用的测试陷阱

MaaFramework 全局加载时，所有 `assets/resource/base/pipeline/*.json` 会合并到同一命名空间，所以 `[JumpBack]OtherFileNode` 能解析。但 `run_pipeline` 测试工具**只加载单文件**，跨文件引用会报"加载 Pipeline 失败"。

**应对**：
- 集成测试必须用 MaaFramework GUI / CLI 触发，不能依赖 `run_pipeline`
- 单元测试每个节点用 `run_pipeline` 是 OK 的（无跨文件依赖）
- 若某个流程有跨文件引用，本地调试时考虑用 `MaaCli` 跑全 bundle

---

## 补充：状态机驱动的「流程型选项」

如果一个 UI 选项代表的是**进入某个跨页面流程**（如"开启成长试炼"→ 大地图 → 难度选择 → 队伍 → 战斗），把选项的 `pipeline_override` 用于：
1. 切换"是否启用流程"的 Flag 节点
2. 注入该流程入口节点所需参数（如难度 `expected`）

而**不要**用 Python orchestration 串联流程中的每个节点。完整流程示例：

```jsonc
// 选项定义
"开启3月成长试炼": {
    "type": "switch",
    "default_case": "No",
    "cases": [
        {
            "name": "Yes",
            "pipeline_override": {
                "Flag_GrowthTrialMode": { "enabled": true },
                "GrowthTrial_Difficulty_Select": { "expected": ["噩梦"] }
            }
        },
        {
            "name": "No",
            "pipeline_override": {
                "Flag_GrowthTrialMode": { "enabled": false }
            }
        }
    ]
}
```

```jsonc
// 入口节点（路由）
"GrowthTrial_Start": {
    "next": [
        "GrowthTrial_TeamReady",                  // 已在队伍配置页
        "[JumpBack]GrowthTrial_Difficulty_Select", // 在难度选择页
        "[JumpBack]GrowthTrial_Enter"             // 在大地图
    ]
}
```

战斗入口自动接力：

```jsonc
"GrowthTrial_EnterBattle": {
    "action": "Click",
    "next": [
        "GrowthTrial_FightStart",                   // 战斗开始
        "[JumpBack]GrowthTrial_TravelSelect_Boat",  // 弹出旅行框
        "[JumpBack]GrowthTrial_TravelSelect_Walk"   // fallback
    ]
}
```

---

## 命名与默认值

### 命名约定

| 角色 | 风格 | 示例 |
|------|------|------|
| option 名（用户可见） | 中文动词起头 | `开启5月城堡相亲`、`选择刷取任务国家` |
| 节点名（pipeline） | 英文 | `Flag_EnableMarryTask`、`EnterCity`、`检测_科内塔之怒` |
| switch case 名 | **严格 `Yes` / `No`** | 不要用 `true/false` 或 `是/否`（Client 解析跨平台不一致） |

### 默认值策略

> **保持现有行为是底线。** 老用户不该因新选项而行为改变。

| 场景 | 推荐 default |
|------|-------------|
| 新开关让功能默认关闭 | `No`（明确告知用户"关了"） |
| 新开关让功能默认开启 | `Yes`（保留旧行为） |
| 旧代码无条件开启 | `Yes`（兼容） |
| 旧代码无条件关闭 | `No`（兼容） |

---

## 读取位置

| 决策类型 | 放哪读 | 理由 |
|---------|-------|------|
| 是否执行某段流程 | 业务函数入口 `handle_xxx` | 与现有同名函数风格一致，子函数自治 |
| 用哪个值做主逻辑 | 任务入口 `run` 或 `YearlyTaskProcessor` | 一次读取、多次复用 |

> **反例**：不要把"是否开启 X"的判断堆在通用 `dispatch` 函数（如 `handle_festival_by_month`）里。每加一个开关 dispatch 就多一个 `if-elif`，越来越臃肿。

---

## ✅ 推荐做法

1. **先复用现有模式**：参考同项目里现成的同类选项（开关 → `开启5月城堡相亲`；选择 → `选择刷取任务国家`）
2. **3 处同步改完再跑**：不要中途停下来"先编译试试"
3. **JSON 改完跑 `python check_resource.py`**：pipeline 加载错误（如重复 key）会立刻报
4. **默认值遵循现状**：选项是"开"还是"关"取决于旧代码行为，不是你的偏好
5. **在 task 的 `doc` 数组里加一行说明**：用户能看懂每个选项的作用
6. **能用 pure override 解决就不要加 Flag + Python 改动**（模式 E）。Flag 节点仅在"Python 代码需要根据 flag 走不同分支"时才必要 —— 行为切换只动 pipeline 节点字段时一律用模式 E

---

## ❌ 不要做

### 1. 不要只通过 pipeline_override 定义节点

```jsonc
// ❌ 错：节点没在 pipeline JSON 中预定义 → 不会被加载 → get_node_data() 返回 None

// ✅ 对：在 pipeline JSON 里预定义
"Flag_EnableSailingFestivalPurchase": { "enabled": true }
```

**验证方法**：加完后跑 `python check_resource.py`，并在 Python 里加个 `None` 兜底日志。

### 2. 不要忘了注册到 task 的 option 数组

```jsonc
// ❌ 错：option 定义了但 task 不引用 → UI 上看不到
"option": []

// ✅ 对：同步注册
"option": ["开启3月启航节购买"]
```

### 3. 不要把判断塞到 dispatch 函数

```python
# ❌ 错：dispatch 越来越臃肿
def handle_festival_by_month(month):
    if month == 3 and not context.get_node_data("Flag_X").get("enabled"):
        return True
    if month == 3:
        return handle_sailing_festival(context)
    # ... 每加一个开关都得多一个 if

# ✅ 对：业务函数自治
def handle_sailing_festival(context):
    if not context.get_node_data("Flag_X").get("enabled"):
        return True
    # ... 正常逻辑
```

### 4. 不要混淆字段路径

| 用途 | 字段路径 | 备注 |
|------|---------|------|
| `select` | `data["recognition"]["param"]["expected"][0]` | 节点必须 `recognition: "OCR"` |
| `input` | `data["action"]["param"]["custom_action_param"][key]` | 完全独立的机制 |
| `switch` / `checkbox` | `data["enabled"]` | 最简单 |
| 模式 E 不读 | （不读，直接看 override 后节点的运行时行为） | pure override 模式，Python 拿不到也不需要 flag |

### 5. 不要用非 `Yes`/`No` 的 switch case 名

```jsonc
// ❌ 错：Client 解析可能不一致
{ "name": "true" } / { "name": "是" } / { "name": "ON" }

// ✅ 对：跨 Client 一致
{ "name": "Yes" } / { "name": "No" }
```

### 6. 不要在 input 里塞 OCR expected 路径

`input` 用 `custom_action_param` 注入自定义文本，**与 `select` 的 `expected` 是两套独立机制**。混用会导致节点配置混乱、后续维护者读不懂。

### 7. 不要用中文做 pipeline 节点名

```jsonc
// ❌ 错：中文节点名 + 英文字段访问
"开启5月": { "enabled": true }

// ✅ 对：英文 Flag_ 命名
"Flag_EnableMarryTask": { "enabled": true }
```

中文做 option 名（用户可见），英文做 pipeline 节点名（代码访问）。混了会让代码和配置都对不上。

### 8. 不要在多文件 pipeline 里重复定义同名节点

`parse_and_override_once` 合并所有 pipeline JSON 时**严格拒绝**重复顶层 key。检查方法：

```bash
grep -rn "^\s*\"YourNodeName\":" assets/resource/base/pipeline/
```

两个文件都定义同一个顶层节点会直接让整个 `check_resource.py` 失败，且 Python `json.load()` 检测不出来（Python 会静默覆盖），必须用 C++ 解析器或 C++ 模拟检测。

### 9. 不要为了"配置统一"硬塞 Flag 节点

```jsonc
// ❌ 错：行为切换只动 pipeline 字段，但你硬加了 Flag 节点 + Python 分支
"Flag_AcceptMercenary": { "enabled": true },   // ← 不必要
def handle_mercenary_join(context):
    if not context.get_node_data("Flag_AcceptMercenary").get("enabled"):
        return True
    context.run_task("Event_MercenaryJoin")      # 实际行为由 Event_MercenaryJoin.next 决定

// ✅ 对：直接 override `next`，零 Python 改动
"开启自动接受佣兵": {
    "type": "switch",
    "pipeline_override": {
        "Event_MercenaryJoin": { "next": ["Event_MercenaryJoinConfirm"] }
    }
}
```

**判断口诀**：如果你的 Python 分支里**只做了一件事**（调用 `run_task` 让 pipeline 接手），那这个分支完全可以由 `pipeline_override` 替代。Flag 节点 + Python 分支只在你需要在 Python 侧做**真正的条件逻辑**（不只是转发）时才必要。

### 10. 不要用 Python orchestration 替代状态机

如果一个跨页面流程可以**列举**为有限个页面状态（A → B → C → D），优先用 MaaFramework 的 `next` + `[JumpBack]` 串起来。**不要**写 Python `for` 循环 + `context.run_task()` 调度。

```jsonc
// ✅ 对：纯 JSON 状态机（推荐）
"GrowthTrial_Start": {
    "next": [
        "GrowthTrial_TeamReady",                  // 已在队伍配置页
        "[JumpBack]GrowthTrial_Difficulty_Select", // 在难度选择页
        "[JumpBack]GrowthTrial_Enter"             // 在大地图
    ]
}

"GrowthTrial_Enter": {
    "next": [
        "GrowthTrial_Enter_Click",                  // 找到图标
        "[JumpBack]BigMap_Activity_Resident",       // 切"常驻"tab
        "[JumpBack]BigMap_Activity"                 // 打开活动页
    ]
}

"GrowthTrial_EnterBattle": {
    "action": "Click",
    "next": [
        "GrowthTrial_FightStart",                    // 战斗开始
        "[JumpBack]GrowthTrial_TravelSelect_Boat",   // 弹出旅行框
        "[JumpBack]GrowthTrial_TravelSelect_Walk"    // fallback
    ]
}
```

```python
# ❌ 错：自己重新发明状态机
def enter_growth_trial(context):
    found = False
    for attempt in range(5):
        if context.run_recognition("BigMap_GrowthTrial_OCR", ...).hit:
            found = True
            break
        context.run_task("Map_SwipeUp_OnBigMap")
    if not found:
        return False
    context.run_task("GrowthTrial_Enter")
    # ... 又是 for/if 链
    return True
```

**自检问题**：
- 我的 Python 代码里是否在**调 `run_task` 把控制权交给 pipeline**？是 → 考虑改用 `next` 链
- 我的"流程推进"是否依赖**显式的状态变量**（如 `found`）？是 → 改用 `[JumpBack]` 让框架自动回退
- 我的"流程"是否**可以画成状态机图**？是 → 用 JSON `next` 链

**注意**：MaaFramework 全局加载时跨文件节点引用会解析（`main_ui.json` 里的 `BigMap_Activity*` 能在 `growth_trial.json` 引用），但**`run_pipeline` 测试工具只加载单文件**——集成测试必须用 MaaFramework GUI/CLI 触发。

---

## 验证流程

改完一次完整流程，**按顺序**做这 4 步：

1. **JSON 语法检查**

   ```bash
   python -c "import json; json.load(open('assets/interface.json', encoding='utf-8'))"
   python -c "import json; json.load(open('assets/resource/base/pipeline/auto_task.json', encoding='utf-8'))"
   ```

2. **资源加载检查**

   ```bash
   python check_resource.py ./assets/resource/base
   ```

   期望输出 `All directories checked.`

3. **Pipeline 节点测试**（可选）

   ```python
   data = context.get_node_data("Flag_EnableSailingFestivalPurchase")
   assert data is not None, "节点未预定义"
   assert "enabled" in data
   ```

4. **端到端验证**：用 Pipeline Testing Skill 跑一次实际流程

---

## 完整协议

更多 type 字段、嵌套 option、global_option、controller/resource 限制、`{占位符}` 注入机制等高级特性见 [references/protocol.md](references/protocol.md)。
