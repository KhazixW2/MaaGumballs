---
name: pipeline-graph
description: 生成 MaaFramework Pipeline 项目的可交互状态机图谱。当用户想"看 Pipeline 节点关系"、"画状态机图"、"画 Mermaid 图"、"看 node 间关系"、"找孤立节点 / orphan node"、"看 Python 怎么驱动 Pipeline"、"看 interface.json 入口"、"调试跨文件 next 引用"、"重构前理清架构" 时使用。**任何涉及 MaaFramework 节点关系可视化的需求都用这个 skill**,即便用户没明确说"画图"。
---

# Pipeline 状态机图谱生成

## TL;DR

把"声明式 JSON 节点 + 命令式 Python 调度"的项目(Pipeline 节点 + `context.run_task()` 调用 + `interface.json` 入口)一键画成可交互的 Mermaid 图,放到 `docs/zh_cn/graph/`,带导航栏和 index 主页,默认 `.gitignore`。

**30 秒上手**:

```bash
python tools/pipeline_to_mermaid.py
start docs\zh_cn\graph\index.html   # Windows
# 或 xdg-open docs/zh_cn/graph/index.html
```

## When to use

- **理解陌生项目**:新接手一个 MaaFramework 项目,想一眼看清节点、调用、入口
- **重构前盘点**:大改某个 Pipeline 文件前,先看图,免得改完不知道影响了哪些边
- **调试"孤儿"节点**:某节点在 Pipeline 里没 `next` 指向它,想知道是 bug 还是被 Python 调用
- **加新节点后**:新加了一个 Pipeline 节点或 `run_task` 调用,刷新图看新边
- **Code review**:看 PR 时,先看图理解结构再看代码,效率翻倍
- **写文档 / 培训新人**:把图当 on-boarding 资料

## What it produces

**4 类产物**(默认输出到 `docs/zh_cn/graph/`,已被 `.gitignore`):

| 文件 | 用途 | 语法 |
|------|------|------|
| `index.html` | 主目录(卡片导航 + 全局统计) | HTML 卡片 |
| `pipeline_overview.html` | 全局状态机,13 个文件作为复合状态 | `stateDiagram-v2` |
| `pipeline_external_entries.html` | Python → Pipeline 调用图 | `flowchart` |
| `pipeline_utility_usage.html` | 工具节点反向引用图 | `flowchart` |
| `pipeline_<file>.html` × 13 | 单文件状态机细节 | `stateDiagram-v2` |

**17 张图**带顶部导航栏,可互跳;`--open` 跑完自动开浏览器;`--watch` 改文件自动重生成(2 秒轮询)。

## How to use

### 跑一次

```bash
python tools/pipeline_to_mermaid.py
```

### 跑完自动开浏览器

```bash
python tools/pipeline_to_mermaid.py --open
```

### 改文件自动重生(watch 模式)

```bash
python tools/pipeline_to_mermaid.py --watch
```

### 给队友打包(一次性)

```bash
tools\update_graph.bat --open      # Windows
./tools/update_graph.sh --open     # bash
```

---

## Key design decisions

本节是**踩过的坑 + 解法**。下次再写类似工具时照搬。

### 1️⃣ 状态机 ≠ 子例程调用:用不同语义

**坑**:MaaFramework Pipeline 不是纯 FSM,有 2 种边:
- `next: "X"` — 真·状态转移,`A` → `X` 后,`X` 接管
- `[JumpBack]X` — 子例程调用,执行 `X`,**自动返回 `A`**,X 不接管

**为什么重要**:如果用同一种箭头画两种边,看图的人会误以为有环。状态机会被画成"循环依赖"。

**解法**:
- `flowchart` 用 `==>`(粗箭头)画 `[JumpBack]`,`-->`(细箭头)画 `next`
- `stateDiagram-v2` 用显式标签 `: calls` / `: returns`(画成两条边:调用方 → 被调方 → 调用方)
- 永远不要把 `[JumpBack]` 画成"返回当前节点"的回环——它本就是临时离开

### 2️⃣ 孤儿子图 = Python 调用的入口

**坑**:Pipeline 里很多节点没 `next` 指向它们(无入边),新手以为是 bug。

**真相**:这些节点是**外部入口**,被两个地方调用:
- Python 代码里的 `context.run_task("X")`
- `assets/interface.json` 的 `task[].entry`(MaaPiCli 暴露给用户的入口)

**解法**:扫描这两处,把调用边也画进图。

**怎么扫**:
- **Python**:用 `ast` 解析 `agent/**/*.py`,在 `ast.Call` 里找 `func.attr == "run_task"`,记录 `Class.method` 调用方
- **interface.json**:读 `task[]` 数组,每个 `entry` 字段就是用户级入口

### 3️⃣ 双遍解析:先建索引,再画边

**坑**:Pipeline 节点会跨文件 `next`,按文件名排序处理时,**后面的文件引用前面的节点,边会丢**。

**举例**:`auto_task.json` 按字母序排第一,里面有 `OpenCityTaskPanel.next = ["FindCityTask_OCR"]`,但 `FindCityTask_OCR` 定义在 `city.json`(字母序更后)。处理 `auto_task.json` 时,目标还没解析,直接 `continue` 跳过这条边。

**解法**:**两遍解析**:
```
Pass 1: 扫所有文件,建立 name → file 索引
Pass 2: 扫所有文件的 next,根据完整索引解析目标
```

### 4️⃣ Mermaid 语法选型:stateDiagram vs flowchart

| 场景 | 选 | 为什么 |
|------|-----|--------|
| 真·FSM(节点 + 转移 + 初始/终止) | **`stateDiagram-v2`** | 原生支持 `[*]` 初始/终止、复合状态、转移标签 |
| 调用图 / 反向引用图 | **`flowchart`** | stateDiagram 不支持"被谁调用"这种语义 |
| 节点形状区分(Stadium / Circle) | **`flowchart`** | stateDiagram 形状统一,只能用 classDef 染色 |
| 跨文件复杂关系 | **`stateDiagram-v2` + 复合状态** | `state X { ... }` 把每个文件折叠起来 |

**口诀**:**状态机用 stateDiagram,其他用 flowchart**。

### 5️⃣ ID 冲突:中文/emoji 节点必须加 hash 后缀

**坑**:Mermaid 节点 ID 由你写,内部是字符串。但**整个图里不能有两个同 ID 的节点**。

中文/emoji 节点名(如 `📲 启动游戏` 和 `📲 推年计划`)用 `re.sub(r'[^A-Za-z0-9_]', '_', name)` 过滤后,**都会变成 `iface________`**,Mermaid 解析失败,图直接黑屏。

**解法**:
```python
def mid(file: str, name: str) -> str:
    h = hash((file, name)) & 0xFFFF
    return f"{re.sub(r'[^A-Za-z0-9_]', '_', f'{file}__{name}')[:50]}_{h:04x}"
```

**永远不要**只靠字符串规范化生成 Mermaid ID,必须带 hash 后缀保证唯一性。

### 6️⃣ 产物必须 `.gitignore`

**坑**:自动生成的 HTML 会被 git 当成"新增文件"跟踪,每次重生都会改 commit,PR diff 爆掉。

**解法**:
- `docs/zh_cn/graph/` 加入 `.gitignore`
- 脚本每次**全量清空再重生**(无缓存、无 diff)
- 队友各跑各的,互不冲突

### 7️⃣ 16+ 张图必须有导航栏 + index 主页

**坑**:第一次版就只输出每张图,**没导航**。用户要从一个文件跳到另一个,得手动记路径或重新打开 IDE。

**解法**(用户视角):
- 每张 HTML 顶部固定深色 navbar(4 个常驻链接 + 当前页高亮橙色)
- 一个 `index.html` 主目录,卡片网格展示所有图
- 卡片显示节点数、入边/出边数(让人快速判断要不要点开看)

**对 skill 的启示**:**任何会生成多文件的工具,都要有导航机制**,否则用户每用一次就骂一次。

---

## Common pitfalls

### 跨文件 `next` 解析漏边

**症状**:总边数比手动数少,某些 `next` 字段在图里看不到。

**排查**:
1. 跑脚本时打印 `next count = 67, jumpback = 32`,如果比预期少,基本是双遍解析没做
2. 临时加个 `assert all(target in all_names for target in nexts)` 找未解析的悬挂引用
3. 目标节点在另一个文件且字母序靠前 → 字母序靠后的文件 `next` 引用它会丢

### ID 冲突导致图渲染失败

**症状**:浏览器控制台报 `SyntaxError: Duplicate id` 或图直接空白。

**排查**:
1. 节点名包含中文/emoji
2. 多个节点规范化后 ASCII 形式相同
3. **解决**:用 hash 后缀,见 5️⃣

### 状态名包含 ASCII 非法字符

**症状**:`stateDiagram-v2` 不允许节点名带 `.` 或 `-`,会解析失败。

**排查**:
- 节点名如 `CastleMarry_AgeCheck`(`_` 合法) OK
- 节点名如 `BigMap-MarketStart`(`-` 非法) 必须转成 `BigMap_MarketStart`
- **解决**:用 `re.sub(r'[^A-Za-z0-9_]', '_', name)` 转换

### 把生成物 commit 进 git

**症状**:`git status` 出现一堆 `pipeline_*.html` untracked。

**排查**:
1. `.gitignore` 加了 `docs/zh_cn/graph/` 吗
2. `git check-ignore -v docs/zh_cn/graph/pipeline_marry.html` 看是否被忽略
3. 如果没忽略,加完 gitignore 后 `git rm --cached docs/zh_cn/graph/*.html` 清理已跟踪文件

---

## Implementation reference

**本 skill 的"参考实现"在项目里**:[tools/pipeline_to_mermaid.py](../../tools/pipeline_to_mermaid.py)(约 1300 行)。

**结构速览**:
```
load_pipeline()         # Pass 1: 建 name→file 索引;Pass 2: 解析 next
scan_python_calls()     # ast 扫 agent/**/*.py 的 context.run_task()
scan_interface_tasks()  # 读 interface.json 的 task[].entry
build_state_overview()  # stateDiagram-v2 复合状态
build_state_per_file()  # 单文件 stateDiagram
build_external_entries()# Python 调用 flowchart
build_utility_usage()   # 反向引用 flowchart
build_index_html()      # 主目录
wrap_html()             # HTML 模板 + 导航栏
main()                  # --open / --watch 处理
```

**改本 skill 时**:
- **删改**:7️⃣ 经验任意一条 → 改对应章节
- **新增场景**:如果要给别的项目类型(非 MaaFramework)用,把"4️⃣ Mermaid 语法"和"3️⃣ 双遍解析"通用化即可,其他都是 MaaFramework 特化

---

## 移植到其他项目

如果你的项目是其他"声明式 + 命令式"系统(比如 Airflow DAG + Python、Terraform resources + tfvars、Ansible playbook + roles),**核心思路一致**:
1. 把声明式部分当 FSM(节点 + 边)
2. 把命令式部分当外部触发器(扫 `context.run_task()` 类似物)
3. 用双遍解析处理跨文件引用
4. ID 加 hash 后缀防冲突
5. 产物 gitignore

Mermaid 语法选择(stateDiagram vs flowchart)同样适用。
