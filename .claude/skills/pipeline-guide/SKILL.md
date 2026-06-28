---
name: pipeline-guide
description: Universal Pipeline JSON 编写指南。基于 MaaFramework Pipeline 协议，提供节点命名、识别算法、动作类型、流程控制、可复用节点等编码规范与模式参考。在编写、修改或审查 Pipeline JSON、设计节点流程、使用 TemplateMatch/OCR/Custom 识别或 Click/Swipe 动作时使用。
---

# Universal Pipeline 编写指南

## 核心原则

1. **状态驱动**：遵循"识别 → 操作 → 识别"循环。每次操作必须基于识别结果，禁止假设操作后画面状态。
2. **高命中率**：扩充 `next` 列表，覆盖当前操作后所有可能画面，力争一次截图命中。
3. **避免硬延迟**：尽量不用 `pre_delay` / `post_delay` / `timeout`，优先通过增加中间识别节点解决；只在必须等画面稳定时才用 `pre_wait_freezes` / `post_wait_freezes`。当确实不需要延迟时，要在节点上显式将 `rate_limit` / `pre_delay` / `post_delay` 设为 0（协议默认 `rate_limit=1000ms`、`pre_delay/post_delay=200ms`，省略字段会引入隐式等待；仓库的 `tools/add_node_defaults.py` 会为 Common 节点补齐这些 0 值字段）。
4. **720p 基准**：所有坐标、ROI、图片必须基于 **720X1280**。
5. **格式化**：JSON 遵循 `.prettierrc`（4 空格缩进，数组元素换行）。

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

- `expected` 写完整文本，不要写片段。
- 无需手动维护多语言——`tools/i18n` 会自动处理。
- 需要写片段或正则时，在 `expected` 数组中加 `// @i18n-skip` 注释。

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

调用 go-service 注册的自定义识别器：

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
- `ClearHitCount`：清除节点命中计数。
- `ExpressionRecognition`：计算布尔表达式。
- 详见 `docs/zh_cn/developers/custom.md`。

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
- [ ] ROI / target 坐标基于 1280×720
- [ ] JSON 格式化符合 `.prettierrc`
- [ ] `locales/` 已添加新增任务的多语言文本
- [ ] OCR `expected` 写完整文本
- [ ] 优先通过中间节点避免重复点击，只在必须时用 `post_wait_freezes`
- [ ] 未引用 `__ScenePrivate*` 内部节点

## 参考

- Pipeline 协议完整规范：[PipelineProtocol](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/en_us/3.1-PipelineProtocol.md)
- 通用按钮文档：`docs/zh_cn/developers/common-buttons.md`
- Custom 节点文档：`docs/zh_cn/developers/custom.md`
- 开发手册：`docs/zh_cn/developers/README.md`
- 节点测试：`docs/zh_cn/developers/node-testing.md`