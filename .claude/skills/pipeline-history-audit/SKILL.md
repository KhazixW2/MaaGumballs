---
name: pipeline-history-audit
description: "Audit a MaaFramework/Maa-series project's Git history to learn how Pipeline JSON, interface options, Python AgentServer CustomAction code, and related data tables evolved. Use when asked to review a Maa project from initial commit through a target commit, map `action: Custom` pipeline nodes to `@AgentServer.custom_action(...)` implementations, find pipeline/custom/option patterns or breakages, and produce a report plus skill-improvement recommendations."
---

# Pipeline History Audit

## Overview

Use this skill to let a Maa project "teach" its Pipeline and CustomAction conventions from real Git history. The output is an audit report, not a code change, unless the user explicitly asks to fix findings afterward.

Default to the current repository and current `HEAD` unless the user provides a path or commit. If the target checkout is not at the requested commit, read from `git show <target>:<path>` and `git log <target>` instead of moving the user's branch.

## Workflow

1. Ground the target.
   - Record repo root, current branch, `HEAD`, requested target commit, root commit, and `git status --short`.
   - Treat uncommitted changes as user work. Do not reset, checkout, clean, or format them.
   - If the user names a future/other commit that is not checked out, audit that commit object directly.

2. Classify every commit.
   - Traverse with `git log --reverse --date=short --format=%H%x00%h%x00%ad%x00%s <target>`.
   - For each commit, inspect `git diff-tree --root --no-commit-id --name-status -r <commit>`.
   - Mark a commit as relevant if it touches:
     - `assets/resource/**/pipeline*.json`
     - `assets/resource/**/pipeline/**/*.json`
     - `assets/resource/**/default_pipeline.json`
     - `assets/interface.json`
     - `agent/**/*.py`
     - `assets/table/**/*.json` or `intelligence_data/**`
     - `.claude/skills/pipeline-*`
   - Relevant type labels are `Pipeline`, `Option`, `Agent`, `Table`, and `Skill`; labels may overlap.
   - List all commits in an appendix, including irrelevant commits.

3. Scan historical change themes.
   - Use `git log -G` over the relevant pathspecs for:
     - `"action": "Custom"`
     - `custom_action` and `@AgentServer.custom_action`
     - `custom_action_param`
     - `"next":` and `[JumpBack]`
     - `pipeline_override`
     - `enable` / `enabled`
     - OCR, TemplateMatch, ColorMatch, `color_filter`
     - `run_task(`, `run_recognition(`, `get_node_data(`
   - Use these counts as navigation aids, not as the final conclusion.

4. Parse the target tree.
   - Load every target pipeline JSON and count files, nodes, action types, recognition types, `next` entries, and `[JumpBack]` entries.
   - Extract `action: Custom` nodes with `custom_action` and `custom_action_param`.
   - Parse `agent/**/*.py` with Python `ast`. Walk both `ast.ClassDef` and
     `ast.FunctionDef` decorator lists because Maa projects commonly register
     CustomAction implementations by decorating classes. Extract:
     - `@AgentServer.custom_action("Name")`
     - `context.run_task("Node")`
     - `context.run_recognition("Node")`
     - `context.get_node_data("Node")`
   - Build a `Pipeline node -> custom_action -> Python registration` table and explicitly list missing registrations.
   - Parse `assets/interface.json` for option/task counts and `pipeline_override` usage.

5. Review key commits.
   - Always sample major introduction/refactor/fix commits found by history, especially commits that introduce CustomAction, new pipeline files, options, ColorMatch/color_filter, or skill updates.
   - Use `git show --stat --oneline <commit>` plus targeted `git show <commit>:<path>` reads.
   - Explain what the commit teaches, not just which files changed.

6. Validate the target.
   - Run JSON parsing on all pipeline files.
   - If a resource checker exists, run it against the target commit. For this repo family, prefer:
     ```powershell
     python tools\ci\check_resource.py assets\resource\base
     ```
   - If checking an un-checked-out target commit, create a temporary detached worktree, run validation there, then remove the worktree. Verify the temp path before recursive deletion.
   - Note that resource loading may not detect missing Python CustomAction registrations; report both results separately.

7. Write the report.
   - Prefer `docs/zh_cn/develop/pipeline_history_audit.md` in the target repo if that path exists; otherwise use `docs/pipeline_history_audit.md`.
   - Include:
     - Method and target commit
     - Coverage stats
     - Historical keyword counts
     - Current pipeline/custom/option asset snapshot
     - Custom mapping table
     - Key timeline
     - Findings by subsystem
     - Skill improvement recommendations
     - Validation results
     - Full commit index appendix
     - Registered custom action appendix

## Report Judgement Rules

- Do not claim "all Custom nodes are valid" unless every `custom_action` has a matching decorator in the target tree.
- Do not treat `context.run_task()` result `.nodes` as proof of a hit. Prefer `completed` or `recognition.hit` when describing good patterns.
- Treat `pipeline_override` as a merge into existing nodes; flag cases where the target node is missing or Python reads a different field path.
- Call out `enable` vs `enabled` explicitly. Recommend compatibility helpers only when history already uses both.
- Prefer JSON state machines (`next` + `[JumpBack]`) for finite UI flows. Reserve Python orchestration for runtime loops, counters, event libraries, screenshot parsing, and business decisions.
- For OCR stability, look for ROI narrowing, expected text changes, ColorMatch, and `color_filter` before recommending TemplateMatch.
- Distinguish resource loading from end-to-end execution. A resource check can pass while CustomAction registration is missing.

## Useful Commands

```powershell
git -C <repo> status --short
git -C <repo> rev-list --count <target>
git -C <repo> log --reverse --date=short --format="%H%x00%h%x00%ad%x00%s" <target>
git -C <repo> diff-tree --root --no-commit-id --name-status -r <commit>
git -C <repo> log --format=%H -G'"action"\s*:\s*"Custom"' <target> -- assets/resource agent assets/interface.json
git -C <repo> show --stat --oneline <commit>
git -C <repo> show <target>:assets/interface.json
```

When generating analysis scripts, keep them temporary unless the user asks for a reusable script. Do not leave generated helper scripts in the repo.
