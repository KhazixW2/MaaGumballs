# Pipeline Testing Skill

## 概述

测试 MaaFramework Pipeline JSON 中的 node，验证识别和操作是否正常工作。

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
2. **关键**：`expected` 必须是中文（`["角色"]`），不是英文 key（`["Role"]`）
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
