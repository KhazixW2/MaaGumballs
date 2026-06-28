# Pipeline Option 协议参考

本文档描述 MaaFramework interface.json 中 `option` 字段的完整协议规范。  
协议版本：v2.3.0+

> 实战工作流与反模式见 [../SKILL.md](../SKILL.md)。

---

## option 字段位置

```jsonc
{
    "interface_version": 2,
    "option": { /* 所有选项定义 */ },
    "task": [
        { "name": "...", "entry": "...", "option": ["引用的选项名"] }
    ]
}
```

---

## type 合法值

| type | 说明 |
|------|------|
| `select` | 下拉选项框，用户从预定义选项中选择**一个** |
| `checkbox` | 多选框，用户从预定义选项中选择**多个** |
| `input` | 用户输入框，允许手动输入内容 |
| `switch` | 选择框，**Yes** or **No** |

---

## option 顶层字段

| 字段 | 类型 | 必选 | 说明 |
|-----|------|-----|-----|
| `type` | string | ✅ | `select` / `checkbox` / `input` / `switch` |
| `controller` | string[] | ❌ | 适用的控制器类型列表（v2.3.0） |
| `resource` | string[] | ❌ | 适用的资源包列表（v2.3.0） |
| `label` | string | ❌ | UI 显示标签，支持国际化（`$`开头） |
| `icon` | string | ❌ | 图标文件路径，相对于项目根目录 |
| `description` | string | ❌ | 详细描述，支持 Markdown |
| `default_case` | string \| string[] | ❌ | 默认选项（见下方说明） |
| `cases` | object[] | ❌ | 选项列表（`select`/`checkbox`/`switch` 使用） |
| `inputs` | object[] | ❌ | 输入字段（`input` 使用） |
| `pipeline_override` | pipeline | ❌ | `input` 类型的替换模板 |

### default_case 类型

| type | default_case 类型 | 说明 |
|------|------------------|------|
| `select` | `string` | 单个选项 name |
| `switch` | `string` | 单个选项 name（推荐 `Yes` 或 `No`） |
| `checkbox` | `string[]` | 字符串数组（v2.3.0+） |
| `input` | — | 不使用 `default_case`，在 `inputs[].default` 设置 |

---

## type 详解

### select — 单选互斥

```jsonc
{
    "关卡类型": {
        "type": "select",
        "default_case": "主线",
        "cases": [
            {
                "name": "主线",
                "label": "主线关卡",
                "pipeline_override": { "SomeNode": { "expected": ["主线"] } }
            },
            { "name": "资源", "pipeline_override": { "SomeNode": { "expected": ["资源"] } } }
        ]
    }
}
```

**配套节点**：`recognition: "OCR"`，`expected` 列出**所有可能的值**：

```jsonc
"SomeNode": {
    "recognition": "OCR",
    "expected": ["主线", "资源"],
    "roi": [...],
    "action": "Click"
}
```

> ⚠️ **`expected` 必须配合 `recognition: "OCR"`，否则不生效。** 这条反例在 SKILL.md 已说明，详见 [反模式 #4](../SKILL.md)。

### switch — 二元开关

**仅支持两个 cases**，且 name 必须严格匹配：

| 合法匹配 | 推荐 |
|---------|------|
| `Yes` / `No` | ✅ |
| `yes` / `no` | ❌（大小写不一致） |
| `Y` / `N` | ❌ |
| `true` / `false` | ❌ |

Client 会根据 case 的 name 来匹配用户的 Y/N 输入，其他输入会被要求重新输入。**建议使用 `"Yes"` 和 `"No"` 以保证跨 Client 的一致性。**

```jsonc
{
    "吃糖": {
        "type": "switch",
        "default_case": "Yes",
        "cases": [
            { "name": "Yes", "pipeline_override": { "EatCandy": { "enabled": true } } },
            { "name": "No",  "pipeline_override": { "EatCandy": { "enabled": false } } }
        ]
    }
}
```

### checkbox — 多选

**合并规则**：用户可同时选中多个 case，所有被选中的 case 的 `pipeline_override` 会按照 `cases` 数组中的**定义顺序**依次合并生效，与用户勾选的先后顺序**无关**。

```jsonc
{
    "功能选项": {
        "type": "checkbox",
        "default_case": ["选项A"],
        "cases": [
            { "name": "选项A", "pipeline_override": { "节点A": { "enabled": true } } },
            { "name": "选项B", "pipeline_override": { "节点B": { "enabled": true } } }
        ]
    }
}
```

### input — 自由文本

`inputs[].pipeline_type` 合法值：`string` | `int` | `bool`。

```jsonc
{
    "自定义关卡": {
        "type": "input",
        "inputs": [
            {
                "name": "章节号",
                "label": "章节号",
                "default": "2",
                "pipeline_type": "string",
                "verify": "^(\\d+)$",
                "pattern_msg": "请输入数字"
            }
        ],
        "pipeline_override": {
            "SelectStage": {
                "expected": ["{章节号}"]
            }
        }
    }
}
```

### inputs[] 字段说明

| 字段 | 类型 | 必选 | 说明 |
|-----|------|-----|-----|
| `name` | string | ✅ | 输入字段唯一标识符（用于 `{name}` 占位符） |
| `label` | string | ❌ | UI 显示名称，不设置则显示 name |
| `description` | string | ❌ | 输入字段描述 |
| `default` | string | ❌ | 默认值 |
| `pipeline_type` | string | ❌ | `string` / `int` / `bool` |
| `verify` | string | ❌ | 正则验证表达式 |
| `pattern_msg` | string | ❌ | 验证失败提示 |

### 占位符注入

使用 `{name}` 格式在 `pipeline_override` 中引用输入字段的值：

```jsonc
"pipeline_override": {
    "SelectStage": { "expected": ["{章节号}-{关卡号}"] }
}
```

**注意**：占位符**不区分**字段路径（`expected` 和 `custom_action_param` 都可用）。

---

## cases 字段说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| `name` | string | 选项唯一标识符（选项 ID） |
| `label` | string | UI 显示名称 |
| `description` | string | 选项描述，支持 Markdown |
| `icon` | string | 选项图标路径 |
| `option` | string[] | 子配置项列表（嵌套） |
| `pipeline_override` | pipeline | 选项激活时的覆盖配置 |

---

## option 嵌套

选项可以嵌套形成树状结构。**只有当用户选中当前选项时**，才会显示子配置项。支持无限嵌套。

```jsonc
{
    "自定义作战关卡": {
        "type": "switch",
        "cases": [
            { "name": "No",  "pipeline_override": {}, "option": ["关卡类型"] },
            { "name": "Yes", "pipeline_override": {}, "option": ["自定义关卡", "关卡难度"] }
        ]
    }
}
```

---

## pipeline_override 合并规则

当一个任务有多个选项时，所有选中选项的 `pipeline_override` 按**深度合并**。**后选择的选项覆盖先选择的同名字段。**

```jsonc
// 选项 A 的 override
{ "NodeA": { "expected": ["value1"], "enabled": true } }

// 选项 B 的 override
{ "NodeA": { "expected": ["value2"] } }

// 合并结果
{ "NodeA": { "expected": ["value2"], "enabled": true } }
```

> ⚠️ **同名顶层 key 跨文件也会冲突**。`PipelineResMgr::parse_and_override_once` 在合并同一目录下多个 pipeline JSON 时，**严格拒绝**重复顶层 key。Python `json.load()` 静默覆盖检测不出来，必须用 `check_resource.py` 验证。

---

## controller 和 resource 限制（v2.3.0）

### controller

```jsonc
{
    "仅模拟器选项": {
        "type": "select",
        "controller": ["ADB"],
        "cases": [...]
    }
}
```

- 不指定则所有控制器类型都可用
- Client 可将不适用于当前控制器的配置项隐藏或禁用

### resource

```jsonc
{
    "仅官服选项": {
        "type": "select",
        "resource": ["官服"],
        "cases": [...]
    }
}
```

- 不指定则所有资源包都可用

---

## global_option（v2.3.0）

全局选项，生成的参数会参与到**所有任务**的 pipeline override 中：

```jsonc
"global_option": ["战斗划火柴", "战斗自动闪避"]
```

与 `resource.option` 和 `controller.option` 不同，全局选项不依赖于任何资源包或控制器的选择。

---

## context.get_node_data() 返回格式

### switch / checkbox

```python
{"enabled": True}   # 或 {"enabled": False}
```

### select

```python
{
    "recognition": {"param": {"expected": ["王座堡"]}},
    "action": {...}
}
```

### input

```python
# 如果用 expected 占位符：
{
    "recognition": {"param": {"expected": ["2-1"]}}
}

# 如果用 custom_action_param：
{
    "action": {"param": {"custom_action_param": {"stage": "2-1"}}}
}
```

---

## 与 task 的关联

任务通过 `option` 字段引用选项：

```jsonc
{
    "task": [
        {
            "name": "常规作战",
            "entry": "Combat",
            "option": ["关卡选择", "作战次数"]
        }
    ]
}
```

> ⚠️ 漏了 `option: ["xxx"]` 注册，UI 上根本看不到这个选项。详见 [SKILL.md 反模式 #2](../SKILL.md)。
