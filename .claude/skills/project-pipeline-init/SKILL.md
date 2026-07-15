---
name: project-pipeline-init
description: Scan and initialize a MaaFramework game or app automation project for Maa skills and MaaMCP workflows. Use when asked for project-pipeline-init, project_pipeline_init, basic_info.md, researching a game repo, scanning pipeline nodes, finding common Back/Return/Exit/Confirm nodes, mapping pipeline node relationships, generating entry task flowcharts / Mermaid diagrams, summarizing TemplateMatch image assets, OCR expected text conventions, resource groups, task entries, or reducing token cost for future Maa skill / MaaMCP work.
---

# project-pipeline-init

Use this skill to turn a MaaFramework consumer project into a compact onboarding document for future AI sessions. It scans the project's pipeline and image resources, identifies reusable control nodes, and writes `basic_info.md` at the target project root.

The generated file is a producer/consumer handoff: `project-pipeline-init` produces project context, while Maa skills such as `pipeline-guide`, `pipeline-generate`, `pipeline-graph`, `pipeline-option`, and `pipeline-testing` consume the relevant sections before broad repository discovery.

Do not run this skill against MaaMCP itself unless the user explicitly asks to analyze MaaMCP as a consumer project. MaaMCP is the framework; the normal target is a project such as `F:\workspace\MaaGumballs`.

## Core Workflow

1. Locate the target project root.
   - Prefer a user-provided path.
   - Otherwise look for `assets/interface.json`, then `interface.json`.
   - Treat `assets/interface.json` as the source of resource groups, controller types, task entries, and agent settings.

2. Run the analyzer in summary mode first:

   ```bash
   python .claude/skills/project-pipeline-init/scripts/analyze_pipeline_project.py F:\workspace\MaaGumballs
   ```

3. Inspect the summary for:
   - resource groups and task entries from `interface.json`
   - pipeline file count and unique node count
   - high in-degree common nodes
   - Back / Return / Exit / Close / Confirm / Wait / Flag nodes
   - entry task flowcharts and primary path previews
   - unresolved references, isolated nodes, and cycle candidates
   - image directory inventory and TemplateMatch usage
   - Python `context.run_task()` / `run_recognition()` external entries
   - orphan candidates after excluding interface and Python entry points
   - agent script paths (declared `child_args` resolution + project_root 与 4 层 ancestor 约定入口候选 + 交叉对比)

4. Generate `basic_info.md` only after the summary looks reasonable:

   ```bash
   python .claude/skills/project-pipeline-init/scripts/analyze_pipeline_project.py F:\workspace\MaaGumballs --write-basic-info
   ```

   If `basic_info.md` already exists, the script refuses to overwrite it. Use `--overwrite` only after the user explicitly confirms.

5. Report where `basic_info.md` was written and name the most important sections that still need human review.

6. When handing off to another Maa skill:
   - tell it to read `basic_info.md` section 0 and the routed sections for its task
   - treat the document as a cache, not as source of truth
   - re-check every touched node in current JSON/Python and every live claim on the current device
   - if relevant source files are newer than `basic_info.md`, rerun summary mode and report staleness; do not overwrite silently

## What The Analyzer Reads

- `assets/interface.json` or `interface.json`
- all `assets/resource/**/pipeline/**/*.json`
- `default_pipeline.json` under resource roots
- all files under `assets/resource/**/image/**`
- static string targets passed to `context.run_task()` and `context.run_recognition()` under `agent/**/*.py`
- `interface.json` `agent.child_args` 里每条 `.py` 的磁盘解析状态（与运行时 `maa_mcp/agent_supervisor._build_subprocess_cmd` 同步上溯 4 层）
- project_root 与 4 层 ancestor 内 `agent/main.py`、`agent/server.py` 等约定入口的候选存在性（`AGENT_DIR_NAMES × AGENT_ENTRY_BASENAMES`，不递归子目录）

For MaaGumballs-style projects, the script should discover entries such as `Start_Up`, `DailyTask`, `Reward_Execute`, `Shop`, `AutoSky`, `JJC`, `Mars`, `DivineForgeLand_Start`, `TSD_Entry`, `AutoCdk`, and `StopGumballs`, then connect them to the pipeline nodes that define them.

## Relationship Rules

Parse these pipeline link fields:

- `next`
- `on_error`
- `interrupt`

Support these node reference forms:

- plain strings: `"ConfirmButton"`
- lists: `["A", "B"]`
- NodeAttr objects: `{ "name": "A", "jump_back": true }`
- prefixed strings: `"[JumpBack]BackText"`, `"[Anchor]SomeNode"`

Strip bracket prefixes when resolving the target node, but preserve the prefix in summaries where useful.

## Entry Flowcharts

Generate bounded Mermaid flowcharts from each `interface.json` task entry. These diagrams are meant to orient MaaMCP and future skills quickly, not to replace a full graph database.

- Start from the task `entry` node.
- Expand `next`, `on_error`, and `interrupt` edges with edge labels.
- Preserve branch hints such as `JumpBack`, `jump_back`, and `anchor` in edge labels.
- Limit depth and edge count so loops and shared utility nodes do not overwhelm `basic_info.md`.
- Include a short primary path text summary for agents that cannot render Mermaid.

## Public Node Detection

Treat a node as likely reusable when either condition is true:

- it has high in-degree across the merged graph
- its name or behavior indicates a common UI operation

Important common categories:

- Back / Return / Exit / Close / Logout / Stop
- Confirm / Cancel / Retry
- Wait / Loading / Communicating / PowerLack
- Flag / Check / State probe
- `ClickKey` with Android key `4`
- shared TemplateMatch assets such as back buttons, return buttons, confirm buttons, settings buttons

## `basic_info.md` Contents

The generated document must be concise and useful to an AI agent. Include:

1. Project overview
2. Resource groups and task entries
3. Main pipeline inventory
4. Common public nodes
5. Back / Return / Exit / popup handling
6. Node relationship summary
7. OCR expected text conventions
8. TemplateMatch image inventory
9. Resolution and ROI conventions
10. Risks and TODOs
11. Maa skill handoff routing and live verification status

For section 2, the "Agent script paths" subsection includes three parts:

- **Declared**: each `child_args` `.py` with `Status` (`resolved` / `unresolved` / `non-py` / `absolute`) and the absolute path of resolution (if any).
- **Discovered**: every `AGENT_DIR_NAMES × AGENT_ENTRY_BASENAMES` candidate under root + 4 ancestor levels with an `Exists` column.
- **Cross-check**: unresolved declarations, discovered-but-unreferenced candidates, and orphan declarations (resolved paths outside the convention list).

Warnings are emitted when `child_args` is empty, has no `.py` entries, has unresolved paths, references a non-convention name, or when a convention candidate exists but is not referenced by `child_args`. The scanner mirrors `maa_mcp/agent_supervisor._build_subprocess_cmd`'s parent-walk semantics (`AGENT_PARENT_WALK_LIMIT = 4`); keep the two limits in sync if you change one.

Keep automatically detected facts separate from TODOs. Do not invent game semantics that are not present in the project files.

## Optional Live MaaMCP Research

If a device or window is available and the user wants deeper game research, use MaaMCP after file scanning:

1. connect to the simulator/window
2. take a default `screencap`
3. infer portrait or landscape from image width/height
4. use OCR for visible text and key buttons
5. add stable UI facts to `basic_info.md`

Live observations must include time, controller/device, screenshot size/orientation, visible page evidence, tested node, score, and whether an action ran. If OCR and screenshot catch different frames during a transition, record them as separate observations and do not promote either one to a stable project fact.

For safe initialization validation, prefer a temporary `DoNothing` recognition probe derived from a known public node. Run it with `start_agent=false` when Custom code is unnecessary, inspect `recognition.all_results`, call `stop_pipeline`, and remove the temporary file.

This is an enhancement, not a blocker. File scanning must work without a live device.

## Do Not

- Do not overwrite an existing non-empty `basic_info.md` without explicit confirmation.
- Do not commit generated `basic_info.md` from another repository into MaaMCP.
- Do not modify unrelated target-project files while scanning.
- Do not treat OCR/image guesses as facts unless they came from files or live MaaMCP verification.
