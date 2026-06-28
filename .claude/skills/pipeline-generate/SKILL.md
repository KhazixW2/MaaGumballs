---
name: "pipeline-generate"
description: "自动生成 Pipeline OCR 文本节点。直接调 ocr() 拿目标文字 box，扩大 ROI 后合并到目标 pipeline 文件。提供单节点生成 (generate_node.py) + ROI 扫描找最佳 expand (generate_sweep.py) 两个脚本。"
---

# pipeline-generate

## 概念

Pipeline 由 Node 组成。本 skill 针对**OCR 文本识别节点**，按 Pipeline 协议生成节点 JSON 并合并到目标 pipeline 文件。

**核心流程**：连接设备 → `ocr()` 拿 box → 扩大 ROI → 合并节点

**自带脚本**（与本 SKILL.md 同目录）：

| 脚本 | 用途 |
|------|------|
| `generate_node.py` | 单节点生成（默认 `expand=20`） |
| `generate_sweep.py` | 多 expand 变体扫描，找最佳 ROI |

## MCP 工具绑定

依赖 `maa-mcp` MCP 服务。

| 工具 | 说明 |
|------|------|
| `find_adb_device_list` / `connect_adb_device` | 连接设备 |
| `ocr` | **截图 + OCR 一步完成**（内部已调 screencap，外部不要再调） |
| `load_pipeline` / `save_pipeline` | 读/写 pipeline JSON |
| `check_and_download_ocr` | 首次需下载 OCR 模型 |
| `run_pipeline` | 测试 pipeline 节点 |

## 输入参数

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `target_text` | ✅ | — | 要识别的目标中文文字 |
| `node_name` | ✅ | — | 节点名（PascalCase） |
| `pipeline_file` | ✅ | — | 目标 pipeline 路径（相对 `assets/resource/base/pipeline/xxx.json` 或绝对路径） |
| `action_type` | ❌ | `Click` | Click / DoNothing / LongPress / Swipe / ClickKey / InputText |
| `expand_offset` | ❌ | `20` | ROI 扩边像素（**推荐先用 sweep 找最佳**） |
| `post_delay` | ❌ | `500` | |
| `timeout` | ❌ | `2000` | |
| `overwrite` | ❌ | `False` | 节点名冲突时是否覆盖 |

## 3 步工作流（伪代码）

```python
# === Step 1: 连接设备 ===
from maa_mcp.adb import find_adb_device_list, connect_adb_device
controller_id = connect_adb_device(find_adb_device_list()[0])

# === Step 2: OCR 拿 box + 算 ROI ===
from maa_mcp.vision import ocr
from maa_mcp.download import check_and_download_ocr

ocr_results = ocr(controller_id)
if isinstance(ocr_results, str) and "OCR 模型文件不存在" in ocr_results:
    check_and_download_ocr()
    ocr_results = ocr(controller_id)

matched = [r for r in ocr_results if target_text in (r.text if hasattr(r, "text") else r["text"])]
best = max(matched, key=lambda r: r.score if hasattr(r, "score") else r["score"])
box = best.box if hasattr(best, "box") else best["box"]

# 扩大 ROI（720p 硬编码 + 4 边裁剪）
SCREEN_W, SCREEN_H = 720, 1280
x, y, w, h = box
E = expand_offset
roi = [
    max(0, x - E),
    max(0, y - E),
    min(SCREEN_W - max(0, x - E), w + 2 * E),
    min(SCREEN_H - max(0, y - E), h + 2 * E),
]

# === Step 3: 合并到目标 pipeline ===
from maa_mcp.pipeline_tools import load_pipeline, save_pipeline
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
pipeline_path = Path(pipeline_file)
if not pipeline_path.is_absolute():
    pipeline_path = PROJECT_ROOT / "assets" / "resource" / "base" / "pipeline" / pipeline_file

existing = load_pipeline(str(pipeline_path)) or {}
if node_name in existing and not overwrite:
    raise RuntimeError(f"节点 '{node_name}' 已存在")
existing[node_name] = {
    "recognition": "OCR",
    "expected": [target_text],
    "roi": roi,
    "action": action_type,
    "post_delay": post_delay,
    "timeout": timeout,
}
save_pipeline(
    pipeline_json=json.dumps(existing, ensure_ascii=False, indent=4),
    output_path=str(pipeline_path),
    overwrite=True,
)
```

## ROI 扩大示意

```
原始 box:     ┌────┐
              │ 文字│
              └────┘
扩大后 roi:   ┌──────────┐
              │  ┌────┐  │
              │  │文字│  │
              │  └────┘  │
              └──────────┘
```

## 使用流程

> 脚本位于 `.claude/skills/pipeline-generate/`，所有命令从**项目根目录** `f:\workspace\MAAGC` 运行。

### 步骤 1: Sweep 找最佳 expand

```bash
# 生成多个 expand 变体的测试 pipeline
python .claude/skills/pipeline-generate/generate_sweep.py "角色" "46,1248,50,30" 0,5,10,15,20,25,30
```

然后用 `run_pipeline` 逐个测试每个 `Sweep_<text>_eN` 节点，**用 `BackButton_500ms` 返回大地图**（详见 [pipeline-testing](../pipeline-testing/SKILL.md)）。记录成功的 expand 值（score ≥ 0.99 为佳）。

### 步骤 2: 正式生成节点

```bash
python .claude/skills/pipeline-generate/generate_node.py "角色" UI_RoleListPage main_ui.json --expand 20 --overwrite
```

## 关键经验

1. **`ocr()` 自动截图**：内部已调 `controller.post_screencap()`，**不要**再手动 screencap。证据：[vision.py:58](../MaaMCP/maa_mcp/vision.py#L58)。
2. **ROI 不是越大越好**：默认 `expand=75` 会失败（OCR 把"角色"拆成"电"+"色"）。多数节点 sweet spot 是 `expand=20-30`。
3. **特殊节点需要小 ROI**："城堡" expand≥20 全失败，**只接受 0-15**（上方有图标 M/3.9m/1077/👍 干扰）。
4. **`expected` 必须是中文**：`["角色"]` 正确，`["Role"]` 永远找不到。
5. **OCR 非确定性**：同一 ROI 不同次结果可能不同，`timeout: 2000` 期间会重试。
6. **OCR 失败不要换 TemplateMatch**：先用 sweep 找 sweet spot，多数情况能解决。
7. **可滚动 UI 用大 ROI + 父级 orchestrator**（**重要**）：
   - **不要**在 Click 节点的 `next` 里放 `[JumpBack]CastleSwipeDown/Up` —— 找不到文字时会**死循环滑动**！
   - 正确模式参考 marry.json 里的 `CastleHall` 节点：父级 orchestrator 节点的 `next` 列表里放 `[JumpBack]XXXEntry` + `[JumpBack]XXXSwipeDown` + `[JumpBack]XXXSwipeUp` 等
   - 滚动容错 ROI 范围参考 `CastleHallEntry`: `[60, 391, 609, 795]`
8. **`run_pipeline` 必须有手动超时意识**：超过 ~10 秒不返回要主动停止，可能 ROI/expected 配错或 OCR 引擎卡住。
9. **改完 pipeline 文件后调 `load_pipeline(path)` 即可**：**不需要重启 server**。`run_pipeline` 每次都按 `pipeline_path` 从磁盘读最新内容，reload 后立即生效。
10. **可滚动 UI 用统一大 ROI**：当多个目标在同一个可滚动列表（如城堡建筑列表）时，**所有节点共用同一 ROI** `[x, top_y, w, full_h]`，覆盖整个滚动区域。避免每个节点各自 ROI 滚动后失效。前提：每个节点的 `expected` 文字是唯一的（OCR 按 expected 匹配不会冲突）。
11. **ROI 上边界 ≤ 元素最小 y**：目标元素在 y=424 时，ROI y 起点必须 ≤ 424，否则切掉顶部导致 OCR 失败。例：原 ROI `[100, 450, ...]` 把"城堡管理"切掉 26px → 改为 `[100, 400, ...]` 通过。
12. **卡住时截图查看**：节点超时、OCR 找不到、行为异常时，调 `screencap` 看当前屏幕实际状态。可能界面已不在预期页、可能位置已被遮挡。

13. **跨页面流程用 `next` 状态机而非 Python orchestration**：当一个流程涉及多个页面跳转（如：大地图 → 活动入口 → 难度选择 → 队伍 → 战斗），用 MaaFramework 的 `next` + `[JumpBack]` 串节点。**不要**写 Python `for/while` 调 `context.run_task()` 模拟状态机。详见 [.claude/skills/pipeline-option/SKILL.md](../pipeline-option/SKILL.md) 的「不要做 #10」和 [.claude/skills/pipeline-guide/SKILL.md](../pipeline-guide/SKILL.md) 的「跨页面状态机」。

14. **跨文件节点引用在 `run_pipeline` 测试中会失败**：MaaFramework 全局加载时所有 `assets/resource/base/pipeline/*.json` 合并到同一命名空间，`[JumpBack]OtherFileNode` 能解析。但 `run_pipeline` **只加载单文件**，跨文件引用会报"加载 Pipeline 失败"。**应对**：
    - 单元测试每个节点用 `run_pipeline`（无跨文件依赖的子流程）是 OK 的
    - 含跨文件引用的状态机流程，集成测试必须用 MaaFramework GUI/CLI 触发
    - 调试时可考虑 `MaaCli` 命令行运行全 bundle

### 已验证最优 expand（5 节点实测）

| 节点 | expand | score | 备注 |
|------|--------|-------|------|
| `UI_RoleListPage` | **20** | 0.9997 | 中部偏左 |
| `UI_RoleFormationPage` | **20** | 0.998 | 角色右边 |
| `UI_CastlePage` | **3** | 0.997 | ⚠️ 仅 0-15 |
| `UI_TeamPage` | **20** | 0.997 | 城堡右边 |
| `ClickGoToArchipelago` | **20** | 0.991 | 中间大地图按钮 |

### 已验证：可滚动 UI 统一 ROI（10 城堡建筑）

| 节点 | 统一 ROI | score | 备注 |
|------|----------|-------|------|
| `CastleManage` | `[100, 400, 520, 880]` | 0.999 | 顶部 |
| `Market` | 同上 | 0.999 | 顶部 |
| `Blacksmith` | 同上 | 0.998 | 顶部 |
| `AlchemyWorkshop` | 同上 | 0.999 | 顶部 |
| `TrainingCenter` | 同上 | 1.000 | 顶部 |
| `CastleMainHall` | 同上 | 0.876 | 顶部只露 25px |
| `Shrine` | 同上 | 0.999 | 中段 |
| `Family` | 同上 | 0.999 | 中段 |
| `Museum` | 同上 | 0.999 | 底部 |
| `Manor` | 同上 | 0.999 | 底部 |

**关键设计**：
- 所有节点 ROI 完全相同（`[100, 400, 520, 880]`，覆盖 y=400-1280）
- 不靠 expand 微调，靠 `expected` 文字差异让 OCR 区分
- 不放 `next` 链（避免死循环）

---

## 跨页面状态机流程（用 `next` + `[JumpBack]`）

当生成的活动流程需要**跨多个页面跳转**（如：大地图 → 活动入口 → 难度选择 → 队伍 → 战斗），用 MaaFramework 的 `next` + `[JumpBack]` 机制串接各页面节点，**不要写 Python orchestration**。

### 模式：状态机入口节点

```jsonc
{
    "MyActivity_Start": {
        "next": [
            "MyActivity_TeamReady",                      // 已在队伍配置页 → 点击"进入战斗"
            "[JumpBack]MyActivity_Difficulty_Select",     // 在难度选择页 → 选难度
            "[JumpBack]MyActivity_Enter"                 // 在大地图 → 找入口
        ],
        "timeout": 10000
    },

    "MyActivity_Enter": {
        "next": [
            "MyActivity_Enter_Click",                    // 找到图标 → 点击
            "[JumpBack]BigMap_Activity_Resident",         // 切"常驻"tab
            "[JumpBack]BigMap_Activity"                  // 打开活动页
        ],
        "timeout": 10000
    },

    "MyActivity_EnterBattle": {
        "recognition": "OCR",
        "expected": ["进入战斗"],
        "action": "Click",
        "next": [
            "MyActivity_FightStart",                       // 战斗开始
            "[JumpBack]MyActivity_TravelSelect_Boat",      // 乘船
            "[JumpBack]MyActivity_TravelSelect_Walk"       // 步行 fallback
        ]
    },

    "MyActivity_TravelSelect_Boat": {
        "recognition": "OCR",
        "expected": ["确定"],
        "roi": [490, 740, 100, 80],                     // 窄 ROI 限定乘船行
        "action": "Click"
    },

    "MyActivity_TravelSelect_Walk": {
        "recognition": "OCR",
        "expected": ["确定"],
        "roi": [490, 590, 100, 80],                     // 窄 ROI 限定步行行
        "action": "Click"
    }
}
```

### 关键设计要点

1. **`[JumpBack]` 是状态回退的关键**：命中后执行完节点链，自动返回父节点的 `next` 继续。
2. **窄 ROI 区分同名字段**：用 y 范围 [490, 740, 100, 80] vs [490, 590, 100, 80] 区分两个"确定"按钮行（y 范围不重叠）。
3. **`target_offset` 偏移点击**：识别难度文字后用 `target_offset: [270, 0, 0, 0]` 把点击位置右移到"确定"按钮上。
4. **跨文件节点引用**：MaaFramework 全局加载会合并所有 `pipeline/*.json`，所以 `[JumpBack]BigMap_Activity`（在 main_ui.json）能从 growth_trial.json 引用。但 `run_pipeline` 测试只加载单文件，集成测试需用 GUI/CLI。

### 与 Python orchestration 的本质区别

| 状态机（推荐） | Python orchestration（次选） |
|--------------|--------------------------|
| 流程推进由 MaaFramework 调度 | 自己写 `for/if` 调度 |
| 每个节点 `next` 显式声明后继 | Python 函数串行 `run_task` |
| `[JumpBack]` 自动状态回退 | 手动实现回退逻辑 |
| 跨页面异常有自然路径 | 需手动 try/except |

详见 [.claude/skills/pipeline-option/SKILL.md](../pipeline-option/SKILL.md) 的「不要做 #10」和 [.claude/skills/pipeline-guide/SKILL.md](../pipeline-guide/SKILL.md) 的「跨页面状态机」典型模式。
