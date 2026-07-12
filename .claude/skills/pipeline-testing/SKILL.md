---
name: pipeline-testing
description: "Test and validate MaaFramework Pipeline JSON, recognition nodes, action nodes, CustomAction/CustomRecognition wiring, resource loading, and end-to-end task behavior. Use when running `run_pipeline`, checking OCR/TemplateMatch/ColorMatch ROI, validating `context.run_task()` results, auditing `action: Custom` or `recognition: Custom` registrations, or choosing the right resource-check command."
---

# Pipeline Testing Skill

## 概述

测试 MaaFramework Pipeline JSON 中的 node，验证识别和操作是否正常工作。

## 历史审查后的测试边界

- **资源加载检查是 smoke test，不是端到端证明**：`python tools/ci/check_resource.py assets/resource/base` 能证明资源包可加载，但不能证明 CustomAction/CustomRecognition 名称存在、参数路径正确、`run_task()` 分支判断正确。
- **Custom 映射必须单独查**：所有 `action: Custom` / `action.type = Custom` 的 `custom_action` 都要能映射到 `@AgentServer.custom_action(...)`；所有 `recognition.type = Custom` 的 `custom_recognition` 都要能映射到 `@AgentServer.custom_recognition(...)`。
- **CustomRecognition 也要测**：M9A 证明复杂 OCR/list/image 逻辑经常放在 CustomRecognition，不要只测 CustomAction。
- **高风险链路要复测稳定态**：购买、消耗、战斗开始、继续挑战、结算确认等动作后，先识别稳定页面或完成态，再继续危险动作。
- **关闭节点不能继续调用**：当 option 把可执行节点的 `enable`/`enabled` 设为 false 时，Python 必须先短路，不能再调用该节点的 `run_recognition()`/`run_task()`；同时验证关闭可选分支后，同级战斗/调查分支仍会继续识别。

### Custom 映射快速检查

```powershell
rg -n '"Custom"|custom_action|custom_recognition' assets/resource -g '*.json'
rg -n '@AgentServer\.custom_action|@AgentServer\.custom_recognition' agent -g '*.py'
```

人工对照时按名字精确匹配。资源检查通过但这里缺注册，运行时仍会失败。

## 核心流程

```python
# 1. 连接设备
find_adb_device_list()
controller_id = connect_adb_device(device_name="xxx")
# 或
controller_id = connect_window(window_name="xxx")

# 2. 加载 pipeline
load_pipeline(pipeline_path="<pipeline_json>")
RESOURCE_PATH = "<resource_base_path>"

# 3. 逐个测试
for node_name in pipeline_nodes:
    result = run_pipeline(
        controller_id=controller_id,
        pipeline_path=pipeline_path,
        entry=node_name,
        resource_path=RESOURCE_PATH
    )
    # succeeded + all_results 有内容 = 识别成功
    # 详见下方"结果判断"小节
```

## 结果判断

| status | all_results | 含义 |
|--------|-------------|------|
| `succeeded` | 有内容 | ✅ 识别成功 |
| `succeeded` | 空 | ❌ 识别失败 |
| `failed` | — | ❌ 节点未触发 / 识别超时 |

返回结构：
```json
{
  "status": "succeeded",
  "nodes": [{
    "name": "node_name",
    "recognition": {
      "all_results": [{"box": [x, y, w, h], "score": 0.99, "text": "..."}]
    }
  }]
}
```

## `run_task()` 结果判断 ⚠️

MCP 的 `run_pipeline` 单节点结果和 Python CustomAction 里的 `context.run_task()` 结果不是同一个使用场景。`context.run_task()` 的 `result.nodes` 可能包含:

- 真正命中并执行完成的节点
- `next` 列表里被尝试过但失败的节点
- 调试面板显示红叉的节点

因此不要写:

```python
# ❌ 错：有 nodes 不代表目标节点命中
result = context.run_task("AutoSky_CloneDied")
if result and result.nodes:
    handle_clone_loss()
```

应该检查节点是否真的完成或识别命中:

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

实战信号：调试面板里目标节点是红叉，但日志却进入了成功分支，基本就是把"节点出现过"误当成"节点命中"。

对于会回到稳定页面的流程，建议先检测稳定状态:

```python
if task_result_has_hit(result, {"AutoSky_CheckExplorationInfo"}):
    return "done"
```

再跑危险兜底动作（取消结算、购买确认、继续挑战等），避免页面已经回稳后误触发。

## 跨测试导航 ⚠️

**Click 节点会让页面跳转，破坏后续测试初始状态**。必须用 `BackButton_500ms` 返回：

```python
# 测试节点
run_pipeline(..., entry="NodeA", ...)

# 必须返回！不要 click_key(4) 模拟 ESC（可能进错页面）
run_pipeline(..., entry="BackButton_500ms", ...)

# 测下一个
run_pipeline(..., entry="NodeB", ...)
```

**BackButton_500ms** 在 main_ui.json 里，DirectHit 识别返回箭头，定位精确可靠。

## ROI Sweep 测试方法

**OCR 失败时不要换 TemplateMatch**！先用 sweep 找 sweet spot。

操作流程：
1. **生成测试 pipeline** — 同一节点，多个 expand 变体
2. **关键**：`expected` 必须匹配当前资源实际显示文本；在 MaaGumballs 中文资源里是 `["角色"]`，不是英文 key `["Role"]`
3. `run_pipeline` 逐个跑，记录 score
4. 选 score ≥ 0.99 且 ROI 不重叠相邻元素的 expand
5. 用 `generate_node.py --expand X --overwrite` 正式写入

**实战矩阵**（5 节点实测）：

| 节点 | e0 | e20 | e50 | 最佳 |
|------|----|----|-----|------|
| 角色 | ✅ | ✅ 0.9997 | ✅ | e20 |
| 编队 | ✅ | ✅ 0.998 | ✅ | e20 |
| 城堡 | ✅ | ❌ | — | **e3**（仅 0-15） |
| 佣兵团 | ❌ | ✅ | ✅ | e20 |
| 前往群岛 | ✅ | ✅ | ✅ | e20 |

**观察**：
- OCR 引擎**非确定性**：同一 ROI 不同次测试结果可能不同
- `timeout: 2000` 期间 OCR 会重试多次，所以单次失败不一定是真失败
- 特殊节点（如"城堡"）需小 ROI，因为大 ROI 包含邻近 UI 元素会干扰 OCR

## 资源保护 ⚠️

测试时**绝对不要**点击这些按钮（消耗资源）：
- 升级建筑、神殿升级
- 供奉、祭拜先祖
- 购买物品、商城购买
- 确认战斗开始
- 任何有资源消耗的确认按钮

误入后处理：尝试 `BackButton_500ms` 或 ESC → 切换 tab 刷新。

## 常见问题

| 现象 | 排查 |
|------|------|
| 节点超时失败 | 截屏看实际界面 → 调整 `expected` 文本或 `roi` |
| OCR 拆分多字（如"角色"→"电"+"色"） | 缩小 ROI 避开干扰 |
| 误识别相邻文字 | 缩小 ROI 限制范围 |
| 点击位置不准 | 实际点击取 box 中心点：`x + w/2, y + h/2` |
| **可滚动 UI 单视图测不全** | 一个截图里只能看到 5-6 个元素，需要 **swipe 多次**分别测；详见下方 |
| **Click + BackButton 跳错页面** | Click 子页后按 BackButton 可能回到大地图/外层 UI，不是预期父页面；需主动 navigate 回来 |
| **部分可见元素识别** | 边界处只露 25px 也能 OCR 找到（score 偏低 0.8x），用大 ROI 覆盖即可 |

## 可滚动 UI 多视图测试

**单次截图只能测当前可见的 5-6 个元素**。要测全列表（如城堡 10 个建筑）必须多次 swipe：

```
1. 进入目标页（如城堡顶部）
2. run_pipeline 测当前可见的 N 个节点
3. 每个 click 后 BackButton 返回
4. swipe 滚动一屏
5. 再 run_pipeline 测新可见的节点
6. 重复直到列表测完
```

**典型案例：城堡建筑（10 节点）**
- 顶部：城堡管理/市场/铁匠铺/炼金工坊/训练所
- 中段：城堡主厅/神殿/家族
- 底部：藏馆/庄园

**关键**：所有节点共用**同一大 ROI** `[x, top_y, w, full_h]`，不要给每个节点算不同 ROI（滚动后位置变了，原 ROI 失效）。

## 卡住时截图查看

**症状**：节点超时、OCR 找不到、行为异常、识别 score 突然下降

**解决**：调 `screencap(controller_id)` 看实际屏幕状态：
- 当前在哪个页面？（是否已跳到其他页面）
- 目标文字是否被遮挡/弹窗挡住？
- 屏幕是否在加载/转圈？
- 滚动位置对吗？

配合 `ocr()` 看识别结果交叉验证。**不要盲调 ROI/expected，先看实际屏幕**。

## 跨测试导航 ⚠️（Click 节点路径风险）

**Click 节点会让页面跳转，破坏后续测试初始状态**。必须用 `BackButton_500ms` 返回：

```python
# 测试节点
run_pipeline(..., entry="NodeA", ...)

# 必须返回！不要 click_key(4) 模拟 ESC（可能进错页面）
run_pipeline(..., entry="BackButton_500ms", ...)
```

**注意**：BackButton 不一定回到你期望的父页面！
- 例：城堡管理 → BackButton → 实际回到 **大地图**（不是城堡）
- 例：训练所 → BackButton → 回到城堡（正常）

测试前先确认 BackButton 路径，或者用 `ocr()` 检查当前页面状态再继续。

## ⚠️ MCP `start_agent=true` 失败时的 Fallback 方案

**症状**:`run_pipeline(..., start_agent=true)` 报
```
Agent 启动失败: Agent 启动失败 (identifier=12345): connect() 返回 False
```

**根因**(常见):
1. MaaFramework 的 agent 子进程(socket 进程)未在预期时间窗口内完成 `MaaAgentServerStartUp`
2. Socket 路径冲突 / 权限问题
3. MaaFramework 内部 `MaaAgentServerNotImpl`(这个错误明确说"用 MaaFramework,不要用 MaaAgentServer")

**Fallback 1:单节点测试**(推荐):

用 `start_agent=false` + 指定 `entry` 测单个节点(只测 OCR/Template 识别,跳过 CustomAction 链):

```python
# 不开 agent,直接测某个节点
result = run_pipeline(
    controller_id=cid,
    pipeline_path="f:/workspace/MaaGumballs/assets/resource/base/pipeline/sky.json",
    entry="AutoSky_BagConfig",   # 任意节点名
    resource_path="f:/workspace/MaaGumballs/assets/resource/base",
    start_agent=False,          # ← 关键:false
)
```

**适用场景**:测 OCR / TemplateMatch / ColorMatch 等识别节点的 ROI 和 expected 文本是否正确。

**Fallback 2:手动启动 agent 后 MCP 通过 socket 连接**:

如果单节点测试不够(需测完整任务链),手动跑 agent 进程,然后用 `connect_adb_device` / `connect_window` 让 MCP 复用。

```python
# 步骤 1:手动启动 agent
import subprocess
agent_proc = subprocess.Popen(
    ["python", "agent/main.py", "test_socket"],
    cwd=".",
)

# 步骤 2:让 MCP 连接(需要 MCP 内部 socket ID 匹配)
# 实际中,MCP 启动 agent 会自动起 socket,如果手动起需要 MCP 端配对
# 通常这一步是 MCP 内部行为,我们无法直接控制
```

**Fallback 3:放弃 MCP,直接用 MaaFramework Python API**:

```python
import sys
sys.path.insert(0, "f:/workspace/MaaGumballs")
from maa.agent.agent_server import AgentServer
from maa.toolkit import Toolkit
from maa.resource import Resource
from maa.controller import AdbController
from maa.tasker import Tasker

Toolkit.init_option("./")
res = Resource(); res.post_bundle("./assets/resource/base").wait()
ctrl = AdbController(adb_path="adb", address="127.0.0.1:16384"); ctrl.post_connection().wait()
tasker = Tasker(); tasker.bind(res, ctrl)

import action.sky
autosky = action.sky.AutoSky()
result = autosky.run(tasker.context, type('X', (), {'custom_action_param': '{}'})())
```

**何时用哪种**:
- **Fallback 1**(单节点):调试 ROI / expected / TemplateMatch,快速迭代 → **首选**
- **Fallback 3**(直接 API):测完整 task 链,真实环境验证 → MCP 不可用时用
- **Fallback 2**(手动起 agent):通常不需要,MCP 会自动处理

## 测试模板

```markdown
## <文件名> 测试记录

日期: 2026-06-05
设备: xxx
controller_id: xxx

### Node 列表
- [ ] node_name_1
- [ ] node_name_2

### 测试进度
| Node | 结果 | 备注 |
|------|------|------|
| xxx  | ✅   | score=0.999 |
| xxx  | ❌   | 原因xxx |
```

## Reference（详见 [pipeline-guide](../pipeline-guide/SKILL.md)）

- ROI / box / target 概念
- 识别类型：DirectHit / OCR / TemplateMatch / FeatureMatch / ColorMatch / And / Or
- 动作类型：Click / LongPress / Swipe / Scroll / InputText / ClickKey
- 节点生命周期：pre_wait_freezes → pre_delay → action → post_wait_freezes → post_delay → 截图识别 next
