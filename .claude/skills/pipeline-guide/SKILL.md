---
name: pipeline-guide
description: Universal Pipeline JSON 编写指南。基于 MaaFramework Pipeline 协议，提供节点命名、识别算法、动作类型、流程控制、可复用节点等编码规范与模式参考。在编写、修改或审查 Pipeline JSON、设计节点流程、使用 TemplateMatch/OCR/Custom 识别或 Click/Swipe 动作时使用。
---

# Universal Pipeline 编写指南

## 核心原则

1. **状态驱动**：遵循"识别 → 操作 → 识别"循环。每次操作必须基于识别结果，禁止假设操作后画面状态。
2. **高命中率**：扩充 `next` 列表，覆盖当前操作后所有可能画面，力争一次截图命中。
3. **显式等待策略**：优先通过中间识别节点确认状态，不用盲目的长 `delay` 掩盖问题；但启动、动画、结算、加载稳定等场景可以使用短的 `pre_delay` / `post_delay` / `timeout` / `*_wait_freezes`。当确实不需要等待时，要在节点上显式将 `rate_limit` / `pre_delay` / `post_delay` 设为 0（协议默认 `rate_limit=1000ms`、`pre_delay/post_delay=200ms`，省略字段会引入隐式等待）。不要假设仓库存在自动补默认值脚本，使用前先发现真实工具。
4. **720p 基准**：所有坐标、ROI、图片必须基于 **720X1280**。
5. **格式化**：JSON 遵循 `.prettierrc`（4 空格缩进，数组元素换行）。

## 历史审查后的设计准则

这些规则来自 MaaGumballs 与 M9A 的 Pipeline 历史审查，优先级高于早期经验里的绝对化表述：

1. **状态机优先，不等于禁止 Python**：稳定、可枚举的页面流转优先写成 `next` + `[JumpBack]`。当逻辑需要运行时数据、事件库、动态目标选择、跨节点计数、复杂 OCR/图像后处理、`pipeline_override` 计算或失败策略时，使用 CustomAction/CustomRecognition。
2. **Custom 不只是 action**：MaaGumballs 主要使用 `action: Custom`，M9A 同时大量使用 `custom_action`、`custom_recognition`、`tasker_sink`。设计新流程时先判断问题属于“控制流/动作决策”还是“识别/列表解析/图像后处理”。
3. **链路要显式**：父节点的 `next` 放“当前页面可能出现的下一批状态”；临时弹窗、加载、确认框用 `[JumpBack]`；高风险分支（战斗、购买、消耗、结算继续）要和普通调查/领取/返回分开。
4. **等待不是禁用项**：不要用盲目的长 `delay` 掩盖状态识别问题；但启动、切页动画、结算、加载后稳定画面等场景可以使用短的 `post_delay`、`rate_limit` 或 `*_wait_freezes`，并配套下一屏识别验证。
5. **校验分层**：资源加载通过只说明 JSON/资源可加载，不代表 Custom 名称、Python 参数路径、`run_task()` 结果判断都正确。Custom 映射和关键链路需要单独检查。

## Pipeline 链路设计

- 入口节点只负责分发当前可能状态，不要把所有业务语义塞进一个超宽 `next` 后再让 Python 猜。
- `next` 顺序表达优先级：先放最确定、最安全的稳定状态，再放可恢复分支，最后放异常/弹窗 `[JumpBack]`。
- `[JumpBack]X` 是“执行 X 后回到父节点继续识别”，不是普通跳转；适合关闭弹窗、处理加载、补一次确认、滑动列表后回到父识别。
- 对消耗资源或改变账号状态的分支，先识别稳定状态，再做动作；动作后必须有下一屏或完成态验证。
- 可滚动列表优先用父级 orchestrator 节点控制滑动，不要把 swipe 直接塞到每个目标节点的 `next` 里造成死循环。

## Custom 边界

- **CustomAction**：适合动态控制流、跨节点状态、事件库、计数器、运行时 `override_pipeline()`、多步任务编排、失败后是否继续的策略。
- **CustomRecognition**：适合 OCR 结果后处理、列表扫描、颜色/模板组合、图像裁剪分析、返回动态 box/ROI。
- **不要为了“配置统一”强行加 Python**：如果 UI 选项只是改一个已有节点的 `next`、`enabled`、`expected` 或 `roi`，优先 pure `pipeline_override`。
- **也不要为了“纯 JSON”硬绕开 Python**：一旦判断依赖运行时数据、历史状态、动态列表、复杂识别结果或安全策略，Custom 比堆叠巨大 JSON 分支更可靠。

## 项目兼容与实战约定

### 保持本文件既有语法风格

MaaFramework 协议推荐 v2 object 形态，但本仓库不少历史 pipeline 仍使用平铺字段:

```jsonc
{
    "AutoSky_CheckExplorationInfo": {
        "recognition": "OCR",
        "expected": "探索信息",
        "roi": [32, 964, 214, 103],
        "action": "DoNothing"
    }
}
```

编辑既有文件时优先沿用该文件已有风格，避免在同一个局部把 v1 平铺与 v2 object 混得过碎。若要新增 UI 选项或 Python 读取配置，先确认 `context.get_node_data()` 返回结构和当前代码读取路径。

### `enabled` 与 `enable`

协议字段是 `enabled`；部分项目/历史节点可能使用 `enable` 作为自定义开关字段。新增开关时:

- 若节点由 MaaFramework 原生启停，优先使用 `enabled`。
- 若 Python 代码显式读取 `enable` 或已有辅助函数兼容 `enable/enabled`，沿用该功能已有字段。
- `interface.json` 的 `pipeline_override` 必须覆盖代码实际读取的字段；不要 UI 写 `enabled`，Python 却读 `enable`。

### Python 中判断任务结果

`context.run_task()` 返回的 `result.nodes` 可能包含已经尝试过但识别失败的节点。调试面板里的红叉节点也可能出现在列表中，所以不要用 `if result.nodes` 或"节点名出现过"当作命中。

可靠判断顺序:

1. 优先用 `context.run_recognition("Node", img).hit` 判断当前截图。
2. 必须分析 `run_task()` 结果时，检查目标 node 的 `completed` 或 `node.recognition.hit`。
3. 对会回到稳定页面的流程，先检测稳定状态节点（如 `AutoSky_CheckExplorationInfo`），避免已经回到页面后又误跑危险兜底动作。

```python
def task_result_has_hit(result, names: set[str]) -> bool:
    if not result or not result.nodes:
        return False
    for node in result.nodes:
        if getattr(node, "name", None) not in names:
            continue
        if getattr(node, "completed", False):
            return True
        recognition = getattr(node, "recognition", None)
        if recognition and getattr(recognition, "hit", False):
            return True
    return False
```

### 宽入口与高风险分支拆开

不要把"战斗"、"调查"、"开启神殿"、"领奖"等语义不同的节点全塞进一个宽泛 `EventDetection.next` 后再由 Python 统一当战斗处理。高风险分支应在 Python 或上层状态机里先做分类:

- 非战斗事件：调查、拾取、神殿开启，命中后直接作为事件处理。
- 战斗事件：袭击、进入战斗，只有这一类才进入战斗失败/克隆体战损检测。
- 稳定状态：回到雷达/主界面后优先终止本次检测链。

这能避免"空雷达/调查事件被误判成战斗结算"一类问题。

## 节点命名

- 使用 **PascalCase**，同一任务内节点以任务名/模块名为前缀。
- 内部实现节点以 `__` 开头（如 `__ScenePrivateXXX`），不对外暴露。
- 示例：`ResellMain`、`DailyProtocolPassInMenu`、`RealTimeAutoFightEntry`。

## Pipeline v2 格式（推荐）

Universal pipeline 使用 v2 格式，recognition 和 action 放入二级字典：

```jsonc
{
    "MyNode": {
        "recognition": {
            "type": "TemplateMatch",
            "param": {
                "template": "MyTask/button.png",
                "roi": [100, 200, 300, 100],
                "threshold": 0.7,
            },
        },
        "action": {
            "type": "Click",
        },
        "next": ["NextNode"],
    },
}
```

## 常用识别算法

### TemplateMatch（找图）

```jsonc
"recognition": {
    "type": "TemplateMatch",
    "param": {
        "template": "path/to/image.png",  // 相对 image 文件夹
        "roi": [x, y, w, h],              // 720p 坐标，缩小搜索范围
        "threshold": 0.7                   // 默认 0.7，按需调整
    }
}
```

- 图片必须从无损原图裁剪并缩放到 720p。
- `green_mask: true` 可遮蔽不参与匹配的区域（用 RGB(0,255,0) 涂色）。

### OCR（文字识别）

```jsonc
"recognition": {
    "type": "OCR",
    "param": {
        "roi": [x, y, w, h],
        "expected": ["完整文本"]
    }
}
```

- 用户可见、固定文案优先写完整文本，便于多语言和维护。
- 片段、正则、数字状态（如 `0/\d+`）是合法设计，适合动态数值、状态栏、干扰多的 ROI；使用时要在测试记录里说明原因，并按项目 i18n 规则处理跳过/翻译。
- 不要假设所有项目都有同一套 `tools/i18n`；先发现目标仓库的 i18n 工具与约定。

### ColorMatch（找色）

```jsonc
"recognition": {
    "type": "ColorMatch",
    "param": {
        "roi": [x, y, w, h],
        "method": 40,                     // HSV 空间（推荐）
        "lower": [h_low, s_low, v_low],
        "upper": [h_high, s_high, v_high],
        "count": 100
    }
}
```

- 优先使用 HSV（method: 40）或灰度（method: 6），避免 RGB 直接匹配（不同显卡渲染差异）。

### And / Or（组合识别）

```jsonc
// And：全部子识别都成功才算命中
"recognition": {
    "type": "And",
    "param": {
        "all_of": ["NodeA", "NodeB"],  // 可引用节点名或内联 object
        "box_index": 0
    }
}

// Or：任一子识别成功即命中
"recognition": {
    "type": "Or",
    "param": {
        "any_of": ["NodeA", "NodeB"]
    }
}
```

### Custom（自定义识别）

调用 AgentServer 注册的自定义识别器。适合把“识别后的判断”放到 Python：OCR 后处理、列表扫描、动态 box、颜色/模板组合、复杂图像判断等。

```jsonc
"recognition": {
    "type": "Custom",
    "param": {
        "custom_recognition": "ExpressionRecognition",
        "custom_recognition_param": {
            "expression": "{CreditOCR}<300"
        }
    }
}
```

自定义动作使用 `action: Custom` 或 v5 object-form 的 `action.type = "Custom"`，适合把“执行策略”放到 Python：动态分支、事件库、计数器、运行时 `override_pipeline()`、多步子任务、失败是否继续等。

```jsonc
"action": {
    "type": "Custom",
    "param": {
        "custom_action": "NodeOverride",
        "custom_action_param": {
            "SomeNode": { "enabled": false }
        }
    }
}
```

## 常用动作类型

| 动作                   | 用途            | 关键字段                               |
| ---------------------- | --------------- | -------------------------------------- |
| `Click`                | 点击            | `target`, `target_offset`              |
| `LongPress`            | 长按            | `target`, `duration`                   |
| `Swipe`                | 滑动            | `begin`, `end`, `duration`             |
| `Scroll`               | 滚轮（仅Win32） | `target`, `dx`, `dy`                   |
| `ClickKey`             | 按键            | `key`（虚拟键码）                      |
| `InputText`            | 输入文本        | `input_text`                           |
| `StartApp` / `StopApp` | 启停应用        | `package`                              |
| `StopTask`             | 停止当前任务链  | 无                                     |
| `Custom`               | 自定义动作      | `custom_action`, `custom_action_param` |
| `DoNothing`            | 不执行（默认）  | 无                                     |

`target` 支持：`true`（当前识别结果）、节点名字符串、`[x, y]`、`[x, y, w, h]`。

## 流程控制

### next 列表

按序识别，首个命中的节点执行其 action 后成为当前节点。`next` 为空或全部超时则任务结束。

### on_error

识别超时或动作失败时执行的节点列表。

### Node Attributes（节点属性）

**`[JumpBack]`**：命中后执行完该节点链，自动返回父节点继续识别 next。适用于处理弹窗、加载等中断场景。

```jsonc
"next": [
    "BusinessNode",
    "[JumpBack]HandlePopup",
    "[JumpBack]WaitLoading"
]
```

**`[Anchor]`**：动态引用锚点，运行时解析为最后设置该锚点的节点。

### 等待画面稳定

只在必须时使用 `pre_wait_freezes` / `post_wait_freezes` 等待画面静止，不要为了执行稳定而使用延迟：

```jsonc
"post_wait_freezes": {
    "time": 200,
    "target": [0, 0, 0, 0]  // 全屏
}
```

避免对同一按钮重复点击——第二次点击可能作用于下一界面的其他元素。

### max_hit

限制节点最大命中次数，超过后自动跳过：

```jsonc
"max_hit": 3
```

## 可复用节点

编写前先检查是否已有可复用节点，避免重复造轮子。

### 通用按钮（`Common/Button/`）

| 节点                       | 说明                            |
| -------------------------- | ------------------------------- |
| `WhiteConfirmButtonType1`  | 白底圆环确认                    |
| `WhiteConfirmButtonType2`  | 白底对号确认                    |
| `YellowConfirmButtonType1` | 黄底圆环确认                    |
| `YellowConfirmButtonType2` | 黄底对号确认                    |
| `CancelButton`             | 白底 X 取消                     |
| `CloseButtonType1`         | 右上角 X（不兼容 ESC 菜单）     |
| `CloseButtonType2`         | 右上角 X（兼容 ESC 菜单，推荐） |
| `TeleportButton`           | 右下角传送按钮                  |
| `CloseRewardsButton`       | 奖励界面对号关闭                |


### Custom 节点

- `SubTask`：顺序执行子任务列表。
- `ResetCount` / `ClearHitCount`：清除节点命中计数；具体名称以目标项目注册函数为准。
- `NodeOverride` / `DisableNode`：运行时覆盖或禁用节点；适合动态状态，不适合替代简单 UI option。
- `ExpressionRecognition` / CustomRecognition：计算布尔表达式或做复杂识别后处理；具体名称以目标项目注册函数为准。
- 详见 `docs/zh_cn/develop/Custom编写.md`。

## 典型模式

### 带弹窗处理的任务入口

```jsonc
{
    "MyTaskEntry": {
        "next": [
            "MyTaskMainStep",
            "[JumpBack]SceneDialogConfirm",
            "[JumpBack]SceneWaitLoadingExit",
            "[JumpBack]SceneAnyEnterWorld",
        ],
    },
}
```

### 跨页面活动流程（纯 JSON 状态机）

当一个任务涉及**多个页面跳转**（如：大地图 → 活动入口 → 难度选择 → 队伍配置 → 战斗），用 MaaFramework 的 `next` + `[JumpBack]` 机制串接各页面节点。**不要写 Python orchestration**（自己 `for/while` 调 `run_task` 模拟状态机）。

```jsonc
{
    "MyActivity_Start": {
        "next": [
            "MyActivity_TeamReady",                       // 已在队伍配置页
            "[JumpBack]MyActivity_Difficulty_Select",     // 在难度选择页
            "[JumpBack]MyActivity_Enter"                  // 在大地图
        ],
        "timeout": 10000
    },

    "MyActivity_Enter": {
        "next": [
            "MyActivity_Enter_Click",                    // 找到图标
            "[JumpBack]BigMap_Activity_Resident",         // 切"常驻"tab
            "[JumpBack]BigMap_Activity"                  // 打开活动页
        ],
        "timeout": 10000
    },

    "MyActivity_EnterBattle": {
        "recognition": { "type": "OCR", "param": { "expected": ["进入战斗"], "roi": [...] } },
        "action": { "type": "Click" },
        "next": [
            "MyActivity_FightStart",                       // 战斗开始
            "[JumpBack]MyActivity_TravelSelect_Boat",      // 乘船
            "[JumpBack]MyActivity_TravelSelect_Walk"       // 步行
        ]
    }
}
```

**关键设计要点**：

- **`[JumpBack]` 是状态回退原语**：命中后执行完节点链，自动返回父节点的 `next` 继续识别。
- **窄 ROI 区分同名字段**：用 y 范围 [490, 740, 100, 80] vs [490, 590, 100, 80] 区分两个"确定"按钮行。
- **`target_offset` 偏移点击**：识别难度文字后用 `target_offset: [270, 0, 0, 0]` 右移到"确定"按钮位置。
- **跨文件节点引用**：MaaFramework 全局加载会合并所有 `pipeline/*.json`，跨文件引用 OK。但 `run_pipeline` 测试工具只加载单文件，集成测试需用 GUI/CLI。

**实战决策流程**：

```
要实现一个跨页面流程
│
├─ 流程可枚举为有限页面状态（A→B→C→D）？
│   └─ ✅ 优先用纯 JSON 状态机（next + [JumpBack]）
│       示例：成长试炼、相亲、英雄副本
│
└─ 流程涉及复杂的运行时分支或 Python 侧业务逻辑？
    └─ 用 Flag 节点 + Python CustomAction
        示例：跳过整个 handle_sailing_festival 函数
```

详细反模式参见 [.claude/skills/pipeline-option/SKILL.md](../pipeline-option/SKILL.md) 的「不要做 #10」。

### 确认后验证画面变化

```jsonc
{
    "ClickConfirm": {
        "recognition": { "type": "TemplateMatch", "param": { "template": "confirm.png", "roi": [...] } },
        "action": { "type": "Click" },
        "post_wait_freezes": { "time": 200, "target": [0, 0, 0, 0] },
        "next": ["VerifyNextScreen", "[JumpBack]ClickConfirm"]
    }
}
```

### And 组合识别（背景 + 图标）

```jsonc
{
    "MyButton": {
        "recognition": {
            "type": "And",
            "param": {
                "all_of": ["ButtonBackground", "ButtonIcon"],
                "box_index": 0,
            },
        },
        "action": {"type": "Click"},
    },
}
```

## 审查清单

- [ ] 字段名拼写正确、类型合法（核对 Pipeline 协议）
- [ ] 无不必要的 `pre_delay` / `post_delay` / `timeout`
- [ ] `next` 列表覆盖所有可能画面，含弹窗/加载/异常
- [ ] 每次点击后有识别验证，不假设操作后状态
- [ ] ROI / target 坐标基于 720×1280（宽×高）
- [ ] JSON 格式化符合 `.prettierrc`
- [ ] `locales/` 已添加新增任务的多语言文本
- [ ] OCR `expected` 写完整文本
- [ ] 优先通过中间节点避免重复点击，只在必须时用 `post_wait_freezes`
- [ ] 未引用 `__ScenePrivate*` 内部节点

## 参考

- Pipeline 协议完整规范：[PipelineProtocol](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/en_us/3.1-PipelineProtocol.md)
- Pipeline 编写：`docs/zh_cn/develop/Pipeline编写.md`
- Custom 节点：`docs/zh_cn/develop/Custom编写.md`
- Interface 选项：`docs/zh_cn/develop/interface.json编写.md`
- 项目结构：`docs/zh_cn/develop/项目结构.md`
