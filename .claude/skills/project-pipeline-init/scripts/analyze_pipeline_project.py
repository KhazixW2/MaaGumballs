#!/usr/bin/env python3
"""Analyze a MaaFramework consumer project and generate basic_info.md."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REFERENCE_FIELDS = ("next", "on_error", "interrupt")
FLOW_MAX_DEPTH = 5
FLOW_MAX_EDGES = 32
FLOW_MAX_NODES = 36
FLOW_MAX_TASKS = 20
COMMON_NODE_RE = re.compile(
    r"(Back|Return|Exit|Close|Closed|Logout|Stop|Confirm|Cancel|Retry|Wait|"
    r"Flag|Popup|Start|Save|Home|Loading|Communicat|PowerLack|Check)",
    re.IGNORECASE,
)
RETURN_NODE_RE = re.compile(
    r"(Back|Return|Exit|Close|Closed|Logout|Stop|Leave)", re.IGNORECASE
)
CONFIRM_NODE_RE = re.compile(r"(Confirm|Cancel|Retry|OK|Yes|No)", re.IGNORECASE)
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".nicegui",
    ".playwright-mcp",
}

# Agent 入口扫描：与运行时 maa_mcp/agent_supervisor._build_subprocess_cmd 保持同步
# 若以后修改运行时的 ancestor 上溯层数，必须同步修改此常量。
AGENT_PARENT_WALK_LIMIT = 4

# 常见 agent 入口文件名（按出现频率排序），用于主动枚举仓库内的候选入口
AGENT_ENTRY_BASENAMES = (
    "main.py",
    "server.py",
    "agent.py",
    "run.py",
    "app.py",
)

# 常见 agent 目录名
AGENT_DIR_NAMES = ("agent", "agents", "Agent", "Agents")


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    field: str
    source_file: str
    attrs: tuple[str, ...] = ()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def find_interface(project_root: Path) -> Path | None:
    candidates = [
        project_root / "assets" / "interface.json",
        project_root / "interface.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    found = [
        p
        for p in project_root.rglob("interface.json")
        if not should_skip(p) and "deps" not in p.parts and "install" not in p.parts
    ]
    if not found:
        return None
    return sorted(found, key=lambda p: (len(p.parts), str(p)))[0]


def resolve_resource_dirs(project_root: Path, interface_path: Path | None, interface: dict) -> list[dict]:
    if not interface_path:
        base = project_root / "assets" / "resource"
        if not base.is_dir():
            return []
        return [
            {
                "name": path.name,
                "raw_paths": [str(path)],
                "paths": [str(path)],
                "existing_paths": [str(path)] if path.is_dir() else [],
            }
            for path in sorted(base.iterdir())
            if path.is_dir()
        ]

    base_dir = interface_path.parent
    groups: list[dict] = []
    for group in interface.get("resource", []) or []:
        raw_paths = group.get("path") or []
        if isinstance(raw_paths, str):
            raw_paths = [raw_paths]
        resolved = [(base_dir / p).resolve() for p in raw_paths]
        groups.append(
            {
                "name": group.get("name") or "<unnamed>",
                "raw_paths": list(raw_paths),
                "paths": [str(p) for p in resolved],
                "existing_paths": [str(p) for p in resolved if p.is_dir()],
            }
        )
    return groups


def unique_existing_resource_dirs(resource_groups: list[dict]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for group in resource_groups:
        for value in group.get("existing_paths", []):
            path = Path(value)
            key = str(path).lower()
            if key not in seen:
                seen.add(key)
                result.append(path)
    return result


def discover_pipeline_files(project_root: Path, resource_dirs: list[Path]) -> tuple[list[Path], list[Path]]:
    pipeline_files: set[Path] = set()
    default_files: set[Path] = set()
    for resource_dir in resource_dirs:
        default = resource_dir / "default_pipeline.json"
        if default.is_file():
            default_files.add(default)
        pipeline_dir = resource_dir / "pipeline"
        if pipeline_dir.is_dir():
            pipeline_files.update(p for p in pipeline_dir.rglob("*.json") if p.is_file())

    if not pipeline_files:
        for path in project_root.rglob("pipeline"):
            if path.is_dir() and not should_skip(path):
                pipeline_files.update(p for p in path.rglob("*.json") if p.is_file())

    return sorted(pipeline_files), sorted(default_files)


def discover_image_files(resource_dirs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for resource_dir in resource_dirs:
        image_dir = resource_dir / "image"
        if image_dir.is_dir():
            files.extend(p for p in image_dir.rglob("*") if p.is_file())
    return sorted(files)


def strip_prefixed_ref(value: str) -> tuple[str, tuple[str, ...]]:
    attrs: list[str] = []
    text = value
    while text.startswith("["):
        end = text.find("]")
        if end <= 0:
            break
        attrs.append(text[1:end])
        text = text[end + 1 :]
    return text, tuple(attrs)


def iter_refs(value: Any) -> list[tuple[str, tuple[str, ...]]]:
    refs: list[tuple[str, tuple[str, ...]]] = []
    if value is None:
        return refs
    if isinstance(value, str):
        target, attrs = strip_prefixed_ref(value)
        if target:
            refs.append((target, attrs))
        return refs
    if isinstance(value, list):
        for item in value:
            refs.extend(iter_refs(item))
        return refs
    if isinstance(value, dict):
        name = value.get("name")
        if isinstance(name, str) and name:
            attrs = tuple(
                key
                for key in ("jump_back", "anchor")
                if value.get(key) is True
            )
            refs.append((name, attrs))
        return refs
    return refs


def display_value(value: Any, max_len: int = 96) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False)
    text = text.replace("\n", " ")
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def md_escape(value: Any) -> str:
    return display_value(value).replace("|", "\\|")


def node_action_name(node: dict) -> str:
    action = node.get("action", "<default>")
    if isinstance(action, str):
        return action
    if isinstance(action, dict):
        return str(action.get("type") or action.get("action") or "<object>")
    return str(action)


def node_action_params(node: dict) -> dict:
    action = node.get("action")
    if not isinstance(action, dict):
        return node
    params = action.get("param")
    return params if isinstance(params, dict) else action


def node_recognition_name(node: dict) -> str:
    recognition = node.get("recognition", "<default>")
    if isinstance(recognition, str):
        return recognition
    if isinstance(recognition, dict):
        return str(recognition.get("type") or recognition.get("recognition") or "<object>")
    return str(recognition)


def node_recognition_params(node: dict) -> dict:
    recognition = node.get("recognition")
    if not isinstance(recognition, dict):
        return node
    params = recognition.get("param")
    return params if isinstance(params, dict) else recognition


def is_android_back_key(node: dict) -> bool:
    if node_action_name(node).lower() != "clickkey":
        return False
    key = node_action_params(node).get("key")
    return key == 4 or key == [4]


def classify_node(name: str, node: dict, in_degree: int) -> list[str]:
    categories: list[str] = []
    if in_degree >= 5:
        categories.append("high-in-degree")
    if RETURN_NODE_RE.search(name) or is_android_back_key(node):
        categories.append("return-exit")
    if CONFIRM_NODE_RE.search(name):
        categories.append("confirm-cancel")
    if COMMON_NODE_RE.search(name):
        categories.append("common-ui")
    if node_recognition_name(node) == "TemplateMatch":
        template = display_value(node_recognition_params(node).get("template"))
        if RETURN_NODE_RE.search(template) or CONFIRM_NODE_RE.search(template):
            categories.append("template-control")
    return sorted(set(categories))


def analyze_pipeline_files(project_root: Path, pipeline_files: list[Path]) -> dict:
    node_defs: dict[str, list[dict]] = defaultdict(list)
    file_summaries: list[dict] = []
    edges: list[Edge] = []
    read_errors: list[dict] = []
    templates: list[dict] = []
    ocr_expected: list[dict] = []
    roi_nodes: list[dict] = []

    for path in pipeline_files:
        rel_file = rel(path, project_root)
        try:
            data = load_json(path)
        except Exception as exc:  # noqa: BLE001 - analyzer should report all read issues.
            read_errors.append({"file": rel_file, "error": str(exc)})
            continue
        if not isinstance(data, dict):
            read_errors.append({"file": rel_file, "error": "top-level JSON is not an object"})
            continue

        file_summaries.append({"file": rel_file, "node_count": len(data)})
        for name, raw_node in data.items():
            node = raw_node if isinstance(raw_node, dict) else {"value": raw_node}
            recognition_params = node_recognition_params(node)
            node_defs[name].append(
                {
                    "file": rel_file,
                    "recognition": node_recognition_name(node),
                    "action": node_action_name(node),
                    "node": node,
                }
            )

            for field in REFERENCE_FIELDS:
                for target, attrs in iter_refs(node.get(field)):
                    edges.append(Edge(name, target, field, rel_file, attrs))

            if "template" in recognition_params:
                templates.append(
                    {
                        "node": name,
                        "file": rel_file,
                        "template": recognition_params.get("template"),
                        "roi": recognition_params.get("roi"),
                    }
                )
            if "expected" in recognition_params:
                ocr_expected.append(
                    {
                        "node": name,
                        "file": rel_file,
                        "expected": recognition_params.get("expected"),
                        "roi": recognition_params.get("roi"),
                    }
                )
            if "roi" in recognition_params:
                roi_nodes.append(
                    {
                        "node": name,
                        "file": rel_file,
                        "roi": recognition_params.get("roi"),
                    }
                )

    node_names = set(node_defs)
    in_degree = Counter(edge.target for edge in edges)
    out_degree = Counter(edge.source for edge in edges)
    edge_type_counts = Counter(edge.field for edge in edges)
    unresolved = sorted({edge.target for edge in edges if edge.target not in node_names})
    zero_in_degree = sorted(name for name in node_names if in_degree[name] == 0)
    isolated = sorted(
        name for name in node_names if in_degree[name] == 0 and out_degree[name] == 0
    )
    duplicate_nodes = sorted(name for name, defs in node_defs.items() if len(defs) > 1)
    cycles = find_cycle_candidates(node_names, edges)

    common_nodes = []
    return_exit_nodes = []
    confirm_nodes = []
    for name, defs in node_defs.items():
        primary = defs[0]["node"]
        categories = classify_node(name, primary, in_degree[name])
        item = {
            "name": name,
            "categories": categories,
            "in_degree": in_degree[name],
            "out_degree": out_degree[name],
            "recognition": defs[0]["recognition"],
            "action": defs[0]["action"],
            "files": [d["file"] for d in defs[:3]],
        }
        if "high-in-degree" in categories or "common-ui" in categories:
            common_nodes.append(item)
        if "return-exit" in categories:
            return_exit_nodes.append(item)
        if "confirm-cancel" in categories:
            confirm_nodes.append(item)

    common_nodes.sort(key=lambda x: (-x["in_degree"], x["name"]))
    return_exit_nodes.sort(key=lambda x: (-x["in_degree"], x["name"]))
    confirm_nodes.sort(key=lambda x: (-x["in_degree"], x["name"]))
    file_summaries.sort(key=lambda x: (-x["node_count"], x["file"]))

    cross_file_edges = []
    for edge in edges:
        target_defs = node_defs.get(edge.target) or []
        target_files = {d["file"] for d in target_defs}
        if target_files and edge.source_file not in target_files:
            cross_file_edges.append(asdict(edge))

    return {
        "node_count": len(node_defs),
        "node_definition_count": sum(len(defs) for defs in node_defs.values()),
        "node_names": sorted(node_defs),
        "duplicate_nodes": duplicate_nodes,
        "file_summaries": file_summaries,
        "edges": [asdict(edge) for edge in edges],
        "edge_type_counts": dict(edge_type_counts),
        "cross_file_edges": cross_file_edges,
        "unresolved_refs": unresolved,
        "zero_in_degree_nodes": zero_in_degree,
        "isolated_nodes": isolated,
        "cycle_candidates": cycles,
        "common_nodes": common_nodes[:80],
        "return_exit_nodes": return_exit_nodes[:80],
        "confirm_nodes": confirm_nodes[:80],
        "top_in_degree": [
            {"name": name, "in_degree": count}
            for name, count in in_degree.most_common(80)
        ],
        "templates": templates,
        "ocr_expected": ocr_expected,
        "roi_nodes": roi_nodes,
        "read_errors": read_errors,
    }


def find_cycle_candidates(node_names: set[str], edges: list[Edge]) -> list[list[str]]:
    adjacency: dict[str, set[str]] = {name: set() for name in node_names}
    for edge in edges:
        if edge.source in node_names and edge.target in node_names:
            adjacency[edge.source].add(edge.target)

    index = 0
    stack: list[str] = []
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def strongconnect(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for target in adjacency[node]:
            if target not in indices:
                strongconnect(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])

        if lowlinks[node] == indices[node]:
            component: list[str] = []
            while True:
                current = stack.pop()
                on_stack.remove(current)
                component.append(current)
                if current == node:
                    break
            if len(component) > 1 or node in adjacency[node]:
                components.append(sorted(component))

    for node in sorted(node_names):
        if node not in indices:
            strongconnect(node)

    components.sort(key=lambda item: (-len(item), item))
    return components[:30]


def resolve_agent_arg(root: Path, arg: str) -> dict:
    """对一条 child_args 条目走与运行时相同的解析路径，返回结构化报告。

    镜像 maa_mcp/agent_supervisor._build_subprocess_cmd 的解析语义。
    """
    if not arg or not isinstance(arg, str):
        return {
            "arg": str(arg) if arg is not None else "",
            "is_absolute": False,
            "is_py": False,
            "candidates": [],
            "resolved": None,
            "resolved_at_level": -1,
            "status": "non-py",
        }

    is_absolute = Path(arg).is_absolute()
    is_py = arg.lower().endswith(".py")

    if is_absolute:
        abs_path = Path(arg)
        try:
            resolved_str = str(abs_path.resolve()) if abs_path.is_file() else None
        except OSError:
            resolved_str = None
        return {
            "arg": arg,
            "is_absolute": True,
            "is_py": is_py,
            "candidates": [str(abs_path)],
            "resolved": resolved_str,
            "resolved_at_level": 0 if resolved_str is not None else -1,
            "status": "absolute",
        }

    if not is_py:
        return {
            "arg": arg,
            "is_absolute": False,
            "is_py": False,
            "candidates": [],
            "resolved": None,
            "resolved_at_level": -1,
            "status": "non-py",
        }

    # 与运行时一致：root/arg + root.parents[:AGENT_PARENT_WALK_LIMIT]/arg
    candidates: list[Path] = [root / arg]
    candidates.extend(parent / arg for parent in list(root.parents)[:AGENT_PARENT_WALK_LIMIT])
    resolved_path: Path | None = None
    resolved_level = -1
    for level, candidate in enumerate(candidates):
        try:
            if candidate.is_file():
                resolved_path = candidate
                resolved_level = level
                break
        except OSError:
            continue

    resolved_str: str | None = None
    if resolved_path is not None:
        try:
            resolved_str = str(resolved_path.resolve())
        except OSError:
            resolved_str = str(resolved_path)

    return {
        "arg": arg,
        "is_absolute": False,
        "is_py": True,
        "candidates": [str(c) for c in candidates],
        "resolved": resolved_str,
        "resolved_at_level": resolved_level,
        "status": "resolved" if resolved_path is not None else "unresolved",
    }


def discover_agent_candidates(root: Path) -> list[dict]:
    """主动枚举：root 与其 4 层 ancestor 内，按约定入口名扫描候选 .py。

    不递归子目录（避免误中 agent/action/*.py 等业务模块）。
    candidate 字段为 resolve() 后的绝对路径，便于 cross-check 与 declared 字符串对齐。
    """
    if root is None:
        return []
    roots = [root, *list(root.parents)[:AGENT_PARENT_WALK_LIMIT]]
    seen: set[str] = set()
    results: list[dict] = []
    for level, ancestor in enumerate(roots):
        if should_skip(ancestor):
            continue
        for dir_name in AGENT_DIR_NAMES:
            agent_dir = ancestor / dir_name
            for basename in AGENT_ENTRY_BASENAMES:
                candidate = agent_dir / basename
                try:
                    normalized = str(candidate.resolve())
                except OSError:
                    normalized = str(candidate)
                key = normalized.lower()
                if key in seen:
                    continue
                seen.add(key)
                try:
                    exists = candidate.is_file()
                except OSError:
                    exists = False
                results.append(
                    {
                        "candidate": normalized,
                        "exists": exists,
                        "level": level,
                    }
                )
    return results


def analyze_agent_scripts(
    project_root: Path,
    interface_path: Path | None,
    agent_block: Any,
) -> dict:
    """组合 declared（child_args 解析）+ discovered（约定入口枚举）视图。

    返回空骨架的场景：
    - 无 interface.json
    - 无 agent 块
    - child_args 不是列表

    返回的 dict 永远是完整字段集合，便于 render_basic_info / render_summary 直接索引。
    """
    empty: dict = {
        "interface_path": rel(interface_path, project_root) if interface_path else "",
        "agent_block_present": False,
        "declared": [],
        "discovered": [],
        "declared_resolved": [],
        "declared_resolved_count": 0,
        "declared_unresolved_count": 0,
        "discovered_existing_count": 0,
        "orphan_declarations": [],
        "unused_candidates": [],
        "warnings": [],
    }
    if not interface_path or not isinstance(agent_block, dict) or not agent_block:
        return empty

    root = interface_path.parent
    child_args = agent_block.get("child_args")
    if not isinstance(child_args, list):
        return {**empty, "agent_block_present": True}

    declared = [resolve_agent_arg(root, str(a)) for a in child_args]
    discovered = discover_agent_candidates(root)

    declared_resolved_set: set[str] = set()
    for item in declared:
        if item.get("resolved"):
            declared_resolved_set.add(item["resolved"])

    discovered_existing_set: set[str] = {
        item["candidate"] for item in discovered if item.get("exists")
    }

    orphan_declarations = sorted(declared_resolved_set - discovered_existing_set)
    unused_candidates = sorted(discovered_existing_set - declared_resolved_set)
    unresolved_args = [item["arg"] for item in declared if item.get("status") == "unresolved"]
    script_count = sum(1 for item in declared if item.get("is_py"))

    warnings: list[str] = []

    if not child_args:
        warnings.append("interface.json 的 agent 块里完全没有 child_args 条目")
    elif script_count == 0:
        warnings.append("interface.json 的 agent 块里没有任何 .py 入口条目")

    for arg in unresolved_args:
        warnings.append(f"声明的 `{arg}` 在 project_root 与 4 层 ancestor 内解析不到任何 .py 文件")

    for orphan in orphan_declarations:
        warnings.append(
            f"声明解析到 `{orphan}`，但该路径不在 AGENT_DIR_NAMES×AGENT_ENTRY_BASENAMES "
            "约定清单中（可能名不在约定名 / 路径在更深层）"
        )

    for unused in unused_candidates:
        warnings.append(f"仓库里 `{unused}` 存在，但 interface.json 未引用")

    return {
        "interface_path": rel(interface_path, project_root),
        "agent_block_present": True,
        "declared": declared,
        "discovered": discovered,
        "declared_resolved": sorted(declared_resolved_set),
        "declared_resolved_count": len(declared_resolved_set),
        "declared_unresolved_count": len(unresolved_args),
        "discovered_existing_count": len(discovered_existing_set),
        "orphan_declarations": orphan_declarations,
        "unused_candidates": unused_candidates,
        "warnings": warnings,
    }


class PipelineCallVisitor(ast.NodeVisitor):
    """Collect statically named Pipeline entries called by Python code."""

    CALL_METHODS = {"run_task", "run_recognition"}

    def __init__(self, source_file: str) -> None:
        self.source_file = source_file
        self.scopes: list[str] = []
        self.calls: list[dict] = []
        self.dynamic_calls: list[dict] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802 - ast API
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802 - ast API
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self.visit_FunctionDef(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802 - ast API
        method = node.func.attr if isinstance(node.func, ast.Attribute) else ""
        if method in self.CALL_METHODS:
            item = {
                "kind": method,
                "file": self.source_file,
                "line": node.lineno,
                "caller": ".".join(self.scopes) or "<module>",
            }
            target = node.args[0].value if (
                node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ) else ""
            if target:
                self.calls.append({**item, "target": target})
            else:
                self.dynamic_calls.append(item)
        self.generic_visit(node)


def analyze_python_pipeline_calls(project_root: Path) -> dict:
    agent_dir = project_root / "agent"
    if not agent_dir.is_dir():
        return {
            "python_file_count": 0,
            "calls": [],
            "call_summaries": [],
            "dynamic_calls": [],
            "targets": [],
            "read_errors": [],
        }

    calls: list[dict] = []
    dynamic_calls: list[dict] = []
    read_errors: list[dict] = []
    python_files = [
        path for path in agent_dir.rglob("*.py") if not should_skip(path)
    ]
    for path in sorted(python_files):
        source_file = rel(path, project_root)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:  # noqa: BLE001 - report all onboarding scan issues.
            read_errors.append({"file": source_file, "error": str(exc)})
            continue
        visitor = PipelineCallVisitor(source_file)
        visitor.visit(tree)
        calls.extend(visitor.calls)
        dynamic_calls.extend(visitor.dynamic_calls)

    grouped_calls: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in calls:
        grouped_calls[(item["kind"], item["target"])].append(item)
    call_summaries = []
    for (kind, target), items in grouped_calls.items():
        call_summaries.append(
            {
                "kind": kind,
                "target": target,
                "count": len(items),
                "callers": sorted({item["caller"] for item in items})[:3],
                "locations": [
                    f"{item['file']}:{item['line']}" for item in items[:3]
                ],
            }
        )
    call_summaries.sort(key=lambda item: (-item["count"], item["target"], item["kind"]))

    return {
        "python_file_count": len(python_files),
        "calls": calls,
        "call_summaries": call_summaries,
        "dynamic_calls": dynamic_calls,
        "targets": sorted({item["target"] for item in calls}),
        "read_errors": read_errors,
    }


def trace_primary_path(
    entry: str,
    adjacency: dict[str, list[dict]],
    node_names: set[str],
    max_steps: int = 12,
) -> list[str]:
    if not entry:
        return []
    if entry not in node_names:
        return [entry, "(missing entry)"]

    path: list[str] = []
    seen: set[str] = set()
    current = entry
    for _ in range(max_steps):
        path.append(current)
        if current in seen:
            path.append("(cycle)")
            break
        seen.add(current)

        next_edges = [
            edge for edge in adjacency.get(current, []) if edge.get("field") == "next"
        ]
        if not next_edges:
            break

        current = next_edges[0]["target"]
        if current not in node_names:
            path.extend([current, "(unresolved)"])
            break
    return path


def build_task_flow_graphs(
    tasks: list[dict],
    pipeline: dict,
    max_depth: int = FLOW_MAX_DEPTH,
    max_edges: int = FLOW_MAX_EDGES,
    max_nodes: int = FLOW_MAX_NODES,
    max_tasks: int = FLOW_MAX_TASKS,
) -> list[dict]:
    node_names = set(pipeline.get("node_names") or [])
    unresolved = set(pipeline.get("unresolved_refs") or [])
    adjacency: dict[str, list[dict]] = defaultdict(list)
    for edge in pipeline.get("edges", []):
        adjacency[edge["source"]].append(edge)

    flows: list[dict] = []
    for task in tasks[:max_tasks]:
        entry = task.get("entry") or ""
        node_order: list[str] = []
        seen_nodes: set[str] = set()
        selected_edges: list[dict] = []
        selected_edge_keys: set[tuple[str, str, str, tuple[str, ...]]] = set()
        truncated = False

        def add_node(name: str) -> None:
            if name and name not in seen_nodes:
                seen_nodes.add(name)
                node_order.append(name)

        add_node(entry)
        if entry in node_names:
            queue: deque[tuple[str, int]] = deque([(entry, 0)])
            expanded: set[str] = set()
            while queue:
                source, depth = queue.popleft()
                if source in expanded:
                    continue
                expanded.add(source)

                outgoing = adjacency.get(source, [])
                if depth >= max_depth:
                    if outgoing:
                        truncated = True
                    continue

                for edge in outgoing:
                    target = edge["target"]
                    attrs = tuple(edge.get("attrs") or ())
                    edge_key = (edge["source"], target, edge["field"], attrs)
                    if edge_key in selected_edge_keys:
                        continue
                    if len(selected_edges) >= max_edges:
                        truncated = True
                        break
                    if target not in seen_nodes and len(seen_nodes) >= max_nodes:
                        truncated = True
                        break

                    selected_edge_keys.add(edge_key)
                    selected_edges.append(
                        {
                            "source": edge["source"],
                            "target": target,
                            "field": edge["field"],
                            "attrs": list(attrs),
                        }
                    )
                    add_node(target)
                    if target in node_names and target not in expanded:
                        queue.append((target, depth + 1))

        flows.append(
            {
                "task": task.get("name") or "<unnamed>",
                "entry": entry,
                "repeatable": task.get("repeatable", False),
                "entry_found": entry in node_names,
                "depth_limit": max_depth,
                "edge_limit": max_edges,
                "node_limit": max_nodes,
                "node_count": len(node_order),
                "edge_count": len(selected_edges),
                "truncated": truncated,
                "primary_path": trace_primary_path(entry, adjacency, node_names),
                "unresolved_refs": sorted(name for name in node_order if name in unresolved),
                "nodes": node_order,
                "edges": selected_edges,
            }
        )
    return flows


def summarize_images(project_root: Path, resource_dirs: list[Path], image_files: list[Path]) -> dict:
    by_resource = Counter()
    by_dir = Counter()
    samples: list[dict] = []
    resource_lookup = {str(path.resolve()): path.name for path in resource_dirs}
    for path in image_files:
        resource_name = "<unknown>"
        image_rel = path.name
        for resource_dir in resource_dirs:
            try:
                sub = path.relative_to(resource_dir / "image")
            except ValueError:
                continue
            resource_name = resource_lookup[str(resource_dir.resolve())]
            image_rel = str(sub)
            parent = str(sub.parent) if str(sub.parent) != "." else "<root>"
            by_dir[f"{resource_name}/{parent}"] += 1
            break
        by_resource[resource_name] += 1
        if len(samples) < 40:
            samples.append({"resource": resource_name, "path": image_rel})

    return {
        "image_count": len(image_files),
        "by_resource": dict(by_resource.most_common()),
        "top_dirs": [
            {"dir": name, "count": count} for name, count in by_dir.most_common(40)
        ],
        "samples": samples,
    }


def analyze_project(project_root: str | Path) -> dict:
    root = Path(project_root).resolve()
    interface_path = find_interface(root)
    interface = load_json(interface_path) if interface_path else {}
    if not isinstance(interface, dict):
        interface = {}

    resource_groups = resolve_resource_dirs(root, interface_path, interface)
    resource_dirs = unique_existing_resource_dirs(resource_groups)
    pipeline_files, default_files = discover_pipeline_files(root, resource_dirs)
    image_files = discover_image_files(resource_dirs)
    pipeline = analyze_pipeline_files(root, pipeline_files)
    python_pipeline = analyze_python_pipeline_calls(root)

    controllers = [
        item.get("type") or item.get("name")
        for item in interface.get("controller", []) or []
        if isinstance(item, dict)
    ]
    tasks = [
        {
            "name": item.get("name") or "<unnamed>",
            "entry": item.get("entry") or "",
            "repeatable": item.get("repeatable", False),
        }
        for item in interface.get("task", []) or []
        if isinstance(item, dict)
    ]
    pipeline["task_flow_graphs"] = build_task_flow_graphs(tasks, pipeline)
    node_names = set(pipeline["node_names"])
    interface_entries = {task["entry"] for task in tasks if task["entry"]}
    python_targets = set(python_pipeline["targets"])
    externally_reached = interface_entries | python_targets
    pipeline["python_pipeline"] = python_pipeline
    pipeline["external_entry_nodes"] = sorted(externally_reached & node_names)
    pipeline["external_unresolved_refs"] = sorted(externally_reached - node_names)
    pipeline["orphan_candidates"] = sorted(
        set(pipeline["zero_in_degree_nodes"]) - externally_reached
    )

    return {
        "project_root": str(root),
        "project_name": interface.get("name") or root.name,
        "project_url": interface.get("url") or "",
        "interface_path": rel(interface_path, root) if interface_path else "",
        "controllers": controllers,
        "agent": interface.get("agent") or {},
        "agent_scripts": analyze_agent_scripts(
            root, interface_path, interface.get("agent") or {}
        ),
        "resource_groups": resource_groups,
        "tasks": tasks,
        "default_pipeline_files": [rel(p, root) for p in default_files],
        "pipeline_file_count": len(pipeline_files),
        "image_summary": summarize_images(root, resource_dirs, image_files),
        "pipeline": pipeline,
    }


def render_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "_None detected._\n"
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md_escape(cell) for cell in row) + " |")
    return "\n".join(lines) + "\n"


def mermaid_label(value: Any, max_len: int = 64) -> str:
    text = display_value(value, max_len=max_len)
    return (
        text.replace("\\", "/")
        .replace('"', "'")
        .replace("[", "(")
        .replace("]", ")")
        .replace("{", "(")
        .replace("}", ")")
        .replace("|", "/")
    )


def flow_edge_label(edge: dict) -> str:
    label = edge.get("field") or "edge"
    attrs = edge.get("attrs") or []
    if attrs:
        label = f"{label} {','.join(attrs)}"
    return mermaid_label(label, max_len=40)


def render_task_flow_mermaid(flow: dict) -> str:
    if not flow.get("nodes"):
        return "_No graph nodes detected._\n"

    node_ids = {name: f"N{idx}" for idx, name in enumerate(flow["nodes"])}
    unresolved = set(flow.get("unresolved_refs") or [])
    lines = ["```mermaid", "flowchart TD"]
    for name in flow["nodes"]:
        suffix = " (?)" if name in unresolved else ""
        lines.append(f'    {node_ids[name]}["{mermaid_label(name + suffix)}"]')

    for edge in flow.get("edges", []):
        source_id = node_ids.get(edge["source"])
        target_id = node_ids.get(edge["target"])
        if not source_id or not target_id:
            continue
        label = flow_edge_label(edge)
        if edge.get("field") == "next":
            lines.append(f"    {source_id} -- {label} --> {target_id}")
        else:
            lines.append(f"    {source_id} -. {label} .-> {target_id}")

    if unresolved:
        lines.append("    classDef unresolved fill:#fff3cd,stroke:#b7791f,color:#1f2933")
        lines.append(
            "    class "
            + ",".join(node_ids[name] for name in flow["nodes"] if name in unresolved)
            + " unresolved"
        )

    lines.append("```")
    return "\n".join(lines) + "\n"


def render_task_flow_sections(flows: list[dict], max_flows: int = FLOW_MAX_TASKS) -> str:
    if not flows:
        return "_None detected._\n"

    lines: list[str] = []
    for flow in flows[:max_flows]:
        task_name = flow.get("task") or "<unnamed>"
        entry = flow.get("entry") or "<missing>"
        path = " -> ".join(flow.get("primary_path") or []) or "None detected"
        lines.extend(
            [
                f"#### {task_name} (`{entry}`)",
                "",
                f"- 入口节点存在: {flow.get('entry_found')}",
                f"- 主路径: `{path}`",
                (
                    f"- 图规模: {flow.get('node_count', 0)} nodes / "
                    f"{flow.get('edge_count', 0)} edges"
                    + ("，已截断" if flow.get("truncated") else "")
                ),
                f"- 未解析引用: {', '.join(flow.get('unresolved_refs') or []) or 'None detected'}",
                "",
                render_task_flow_mermaid(flow),
            ]
        )
    return "\n".join(lines) + "\n"


def render_agent_script_paths_section(agent_scripts: dict, *, include_warnings: bool = True) -> str:
    """生成 Agent script paths 章节内容（含 Declared / Discovered / Cross-check）。"""
    if not agent_scripts.get("agent_block_present"):
        return "_No agent block / child_args detected._\n"

    declared = agent_scripts.get("declared") or []
    discovered = agent_scripts.get("discovered") or []

    declared_rows: list[list[Any]] = []
    for item in declared:
        arg = item.get("arg") or ""
        status = item.get("status") or "unknown"
        resolved = item.get("resolved") or "—"
        declared_rows.append([arg, status, resolved])

    discovered_rows: list[list[Any]] = []
    for item in discovered:
        candidate = item.get("candidate") or ""
        exists = "yes" if item.get("exists") else "no"
        discovered_rows.append([candidate, exists])

    lines: list[str] = [
        "**Declared (interface.json child_args)**",
        "",
        render_table(["Arg", "Status", "Resolved"], declared_rows),
        "**Discovered (root 与 4 层 ancestor，按约定入口名扫描)**",
        "",
        render_table(["Candidate", "Exists"], discovered_rows),
    ]

    unresolved_args = [
        item.get("arg")
        for item in declared
        if item.get("status") == "unresolved"
    ]
    orphan = agent_scripts.get("orphan_declarations") or []
    unused = agent_scripts.get("unused_candidates") or []

    lines.append("**Cross-check**")
    lines.append("")
    lines.append(
        "- Unresolved declarations: "
        + (", ".join(f"`{a}`" for a in unresolved_args) or "_(none)_")
    )
    lines.append(
        "- Discovered but unreferenced: "
        + (", ".join(f"`{p}`" for p in unused) or "_(none)_")
    )
    lines.append(
        "- Referenced but not in convention list: "
        + (", ".join(f"`{p}`" for p in orphan) or "_(none)_")
    )

    if include_warnings:
        warnings = agent_scripts.get("warnings") or []
        if warnings:
            lines.append("")
            lines.append("**Warnings**")
            lines.append("")
            for warning in warnings:
                lines.append(f"- {warning}")

    return "\n".join(lines) + "\n"


def render_summary(analysis: dict) -> str:
    pipeline = analysis["pipeline"]
    image_summary = analysis["image_summary"]
    lines = [
        f"# {analysis['project_name']} pipeline scan",
        "",
        f"- Root: `{analysis['project_root']}`",
        f"- Interface: `{analysis.get('interface_path') or 'not found'}`",
        f"- Controllers: {', '.join(analysis['controllers']) or 'unknown'}",
        f"- Resource groups: {len(analysis['resource_groups'])}",
        f"- Tasks: {len(analysis['tasks'])}",
        f"- Pipeline files: {analysis['pipeline_file_count']}",
        f"- Unique nodes: {pipeline['node_count']}",
        f"- Node definitions: {pipeline['node_definition_count']}",
        f"- Edges: {len(pipeline['edges'])} ({display_value(pipeline['edge_type_counts'])})",
        f"- Image files: {image_summary['image_count']}",
        "",
        "## Task Entries",
        render_table(
            ["Task", "Entry", "Repeatable"],
            [[t["name"], t["entry"], t["repeatable"]] for t in analysis["tasks"][:30]],
        ),
        "## Entry Flow Previews",
        render_table(
            ["Task", "Entry", "Found", "Primary Path", "Graph"],
            [
                [
                    flow["task"],
                    flow["entry"],
                    flow["entry_found"],
                    " -> ".join(flow.get("primary_path") or []),
                    f"{flow['node_count']} nodes / {flow['edge_count']} edges"
                    + ("; truncated" if flow.get("truncated") else ""),
                ]
                for flow in pipeline.get("task_flow_graphs", [])[:15]
            ],
        ),
        "## Python / Interface External Entries",
        render_table(
            ["Kind", "Target", "Calls", "Sample call site"],
            [
                [
                    item["kind"],
                    item["target"],
                    item["count"],
                    f"{item['callers'][0]} @ {item['locations'][0]}",
                ]
                for item in pipeline["python_pipeline"]["call_summaries"][:20]
            ],
        ),
        "## Agent Script Paths",
        render_agent_script_paths_section(
            analysis.get("agent_scripts") or {},
            include_warnings=False,
        ),
        "## Top Pipeline Files",
        render_table(
            ["File", "Nodes"],
            [[item["file"], item["node_count"]] for item in pipeline["file_summaries"][:20]],
        ),
        "## Common Nodes",
        render_table(
            ["Node", "In", "Out", "Recognition", "Action", "Categories"],
            [
                [
                    item["name"],
                    item["in_degree"],
                    item["out_degree"],
                    item["recognition"],
                    item["action"],
                    ", ".join(item["categories"]),
                ]
                for item in pipeline["common_nodes"][:25]
            ],
        ),
        "## Return / Exit Nodes",
        render_table(
            ["Node", "In", "Recognition", "Action", "Files"],
            [
                [
                    item["name"],
                    item["in_degree"],
                    item["recognition"],
                    item["action"],
                    ", ".join(item["files"]),
                ]
                for item in pipeline["return_exit_nodes"][:25]
            ],
        ),
        "## Image Directories",
        render_table(
            ["Directory", "Count"],
            [[item["dir"], item["count"]] for item in image_summary["top_dirs"][:25]],
        ),
        "## Risks",
        f"- Unresolved refs: {len(pipeline['unresolved_refs'])}",
        f"- Zero-in-degree nodes: {len(pipeline['zero_in_degree_nodes'])}",
        f"- Graph-isolated nodes: {len(pipeline['isolated_nodes'])}",
        f"- External entry nodes: {len(pipeline['external_entry_nodes'])}",
        f"- Zero-in-degree candidates after external-entry scan: {len(pipeline['orphan_candidates'])}",
        f"- Dynamic Python Pipeline calls: {len(pipeline['python_pipeline']['dynamic_calls'])}",
        f"- Duplicate node names: {len(pipeline['duplicate_nodes'])}",
        f"- Cycle candidates: {len(pipeline['cycle_candidates'])}",
        f"- Unresolved agent script paths: {analysis.get('agent_scripts', {}).get('declared_unresolved_count', 0)}",
        f"- Orphan agent script path declarations: {len(analysis.get('agent_scripts', {}).get('orphan_declarations', []))}",
        f"- Unreferenced agent entry candidates: {len(analysis.get('agent_scripts', {}).get('unused_candidates', []))}",
    ]
    if pipeline["unresolved_refs"]:
        lines.append(f"- Unresolved sample: {', '.join(pipeline['unresolved_refs'][:20])}")
    return "\n".join(lines) + "\n"


def render_basic_info(analysis: dict) -> str:
    pipeline = analysis["pipeline"]
    image_summary = analysis["image_summary"]
    resource_rows = [
        [group["name"], ", ".join(group["raw_paths"]), len(group["existing_paths"])]
        for group in analysis["resource_groups"]
    ]
    task_rows = [[task["name"], task["entry"], task["repeatable"]] for task in analysis["tasks"]]
    common_rows = [
        [
            item["name"],
            item["in_degree"],
            item["recognition"],
            item["action"],
            ", ".join(item["categories"]),
        ]
        for item in pipeline["common_nodes"][:30]
    ]
    return_rows = [
        [
            item["name"],
            item["in_degree"],
            item["recognition"],
            item["action"],
            ", ".join(item["files"]),
        ]
        for item in pipeline["return_exit_nodes"][:30]
    ]
    ocr_rows = [
        [item["node"], item["expected"], item["roi"], item["file"]]
        for item in pipeline["ocr_expected"][:40]
    ]
    template_rows = [
        [item["node"], item["template"], item["roi"], item["file"]]
        for item in pipeline["templates"][:40]
    ]
    roi_rows = [
        [item["node"], item["roi"], item["file"]]
        for item in pipeline["roi_nodes"][:30]
    ]
    python_call_rows = [
        [
            item["kind"],
            item["target"],
            item["count"],
            f"{item['callers'][0]} @ {item['locations'][0]}",
        ]
        for item in pipeline["python_pipeline"]["call_summaries"][:25]
    ]

    lines = [
        "# Basic Info",
        "",
        "> Auto-generated by `project-pipeline-init`. Review TODO items before relying on this file for automation edits.",
        "",
        "## 0. Maa Skills 接力协议",
        "",
        "`basic_info.md` 是项目上下文缓存，不是 Pipeline 源文件。Maa skills 应先读本节，再按任务读取相关章节，并始终以当前源码和实时设备结果为准。",
        "",
        render_table(
            ["Consumer skill", "Read first", "Must re-verify"],
            [
                ["pipeline-guide / pipeline-generate", "3, 4, 5, 7, 8, 9", "待修改节点及目标页面"],
                ["pipeline-graph", "2, 3, 6", "跨文件边、Python 调用和 interface entry"],
                ["pipeline-option", "1, 2, 6", "pipeline_override 与 Python 读取路径"],
                ["pipeline-testing", "2, 5, 7, 8, 9, 10", "当前截图、OCR 命中和高风险动作"],
            ],
        ),
        "- 若本文件缺失，且当前会话可用 `project-pipeline-init`，先运行它。",
        "- 若本文件早于相关 Pipeline / interface / agent 文件，视为可能过期；先重跑摘要，不要静默覆盖本文件。",
        "- 发现源码或实机结果与本文冲突时，记录冲突并采用新证据；未经确认不要覆盖已有非空文件。",
        "",
        "## 1. 项目概览",
        "",
        f"- 项目名: `{analysis['project_name']}`",
        f"- 根目录: `{analysis['project_root']}`",
        f"- 仓库/主页: {analysis.get('project_url') or 'TODO'}",
        f"- interface: `{analysis.get('interface_path') or 'TODO'}`",
        f"- 控制器: {', '.join(analysis['controllers']) or 'TODO'}",
        f"- Agent: `{display_value(analysis.get('agent')) or 'TODO'}`",
        "",
        "## 2. 资源组与入口任务",
        "",
        "### Resource groups",
        render_table(["Name", "Paths", "Existing paths"], resource_rows),
        "### Agent script paths",
        "",
        "> 接口声明的 agent 入口文件静态扫描结果；只读、不修改 interface.json。",
        "",
        render_agent_script_paths_section(analysis.get("agent_scripts") or {}),
        "### Task entries",
        render_table(["Task", "Entry", "Repeatable"], task_rows),
        "## 3. 主要 Pipeline",
        "",
        f"- Pipeline 文件数: {analysis['pipeline_file_count']}",
        f"- 默认配置文件: {', '.join(analysis['default_pipeline_files']) or 'None detected'}",
        f"- 唯一节点数: {pipeline['node_count']}",
        f"- 节点定义数: {pipeline['node_definition_count']}",
        "",
        render_table(
            ["File", "Nodes"],
            [[item["file"], item["node_count"]] for item in pipeline["file_summaries"][:30]],
        ),
        "### 入口主链路流程图",
        "",
        "从 `interface.json` 的 task entry 出发，按 `next/on_error/interrupt` 展开有限深度流程图；公共返回、确认、退出节点会自然出现在图中。",
        "",
        render_task_flow_sections(pipeline.get("task_flow_graphs", [])),
        "## 4. 公共基础节点",
        "",
        "这些节点通常被多条链路引用，或名称/行为显示它们是通用 UI 控制节点。",
        "",
        render_table(["Node", "In", "Recognition", "Action", "Categories"], common_rows),
        "## 5. 返回 / 退出 / 弹窗处理",
        "",
        "重点关注返回、退出、关闭、确认、重连、体力不足等流程。MaaGumballs 一类项目常通过 `[JumpBack]` 把这些节点挂到主链路中。",
        "",
        render_table(["Node", "In", "Recognition", "Action", "Files"], return_rows),
        "### Confirm / Cancel nodes",
        render_table(
            ["Node", "In", "Recognition", "Action"],
            [
                [item["name"], item["in_degree"], item["recognition"], item["action"]]
                for item in pipeline["confirm_nodes"][:20]
            ],
        ),
        "## 6. 节点关系摘要",
        "",
        f"- 边数量: {len(pipeline['edges'])}",
        f"- 边类型: `{display_value(pipeline['edge_type_counts'])}`",
        f"- 跨文件引用数: {len(pipeline['cross_file_edges'])}",
        f"- 未解析引用数: {len(pipeline['unresolved_refs'])}",
        f"- 孤立节点数: {len(pipeline['isolated_nodes'])}",
        f"- 重复节点名数: {len(pipeline['duplicate_nodes'])}",
        f"- 疑似循环/SCC 数: {len(pipeline['cycle_candidates'])}",
        "",
        "### Top in-degree nodes",
        render_table(
            ["Node", "In"],
            [[item["name"], item["in_degree"]] for item in pipeline["top_in_degree"][:25]],
        ),
        "### Python / interface 外部入口",
        "",
        f"- 扫描 Python 文件数: {pipeline['python_pipeline']['python_file_count']}",
        f"- 静态 Python Pipeline 调用数: {len(pipeline['python_pipeline']['calls'])}",
        f"- 动态目标调用数: {len(pipeline['python_pipeline']['dynamic_calls'])}",
        f"- 外部入口命中节点数: {len(pipeline['external_entry_nodes'])}",
        f"- 排除外部入口后的无入边候选数: {len(pipeline['orphan_candidates'])}",
        "",
        render_table(
            ["Kind", "Target", "Calls", "Sample call site"],
            python_call_rows,
        ),
        "## 7. OCR 文字识别约定",
        "",
        "以下为扫描到的 `expected` 样例。请人工补充 OCR 易错字、替换规则和跨语言差异。",
        "",
        render_table(["Node", "Expected", "ROI", "File"], ocr_rows),
        "## 8. TemplateMatch 图片模板",
        "",
        f"- 图片文件数: {image_summary['image_count']}",
        "",
        "### Image directories",
        render_table(
            ["Directory", "Count"],
            [[item["dir"], item["count"]] for item in image_summary["top_dirs"][:40]],
        ),
        "### TemplateMatch usage samples",
        render_table(["Node", "Template", "ROI", "File"], template_rows),
        "## 9. 分辨率与 ROI 约定",
        "",
        "- MaaMCP ADB 默认按截图短边 720 归一化；横屏/竖屏通过截图宽高判断。",
        "- Pipeline 中的 ROI 应结合项目实际截图基准确认，不要盲目从其他设备复制。",
        "- TODO: 用一次实机 `screencap` 记录目标设备分辨率、方向、DPI 和常用页面 ROI。",
        "",
        render_table(["Node", "ROI", "File"], roi_rows),
        "### MaaMCP 实机验证记录",
        "",
        "- 当前状态: `static-scan-only`（生成器不会把未验证的截图猜测写成事实）。",
        "- 记录格式: 时间、controller/device、截图尺寸与方向、页面证据、测试节点、score、是否执行动作。",
        "- 同一次验证的 OCR 与截图必须确认来自稳定的同一页面；画面切换时分别记录，不能合并为永久事实。",
        "- TODO: 使用 `DoNothing` 探针验证至少一个公共返回/确认节点，并保留 TaskDetail 结果。",
        "",
        "## 10. 风险清单与待确认项",
        "",
        f"- 未解析引用: {', '.join(pipeline['unresolved_refs'][:30]) or 'None detected'}",
        f"- 图内孤立节点样例: {', '.join(pipeline['isolated_nodes'][:30]) or 'None detected'}",
        f"- 排除外部入口后的无入边候选: {', '.join(pipeline['orphan_candidates'][:30]) or 'None detected'}",
        f"- Python 动态目标调用数: {len(pipeline['python_pipeline']['dynamic_calls'])}",
        f"- 外部入口未解析引用: {', '.join(pipeline['external_unresolved_refs'][:30]) or 'None detected'}",
        f"- 重复节点名样例: {', '.join(pipeline['duplicate_nodes'][:30]) or 'None detected'}",
        f"- 疑似循环样例: {display_value(pipeline['cycle_candidates'][:10]) or 'None detected'}",
        f"- Agent script paths unresolved: {analysis.get('agent_scripts', {}).get('declared_unresolved_count', 0)}",
        f"- Agent script path orphan declarations: {len(analysis.get('agent_scripts', {}).get('orphan_declarations', []))}",
        f"- Agent script path unreferenced candidates: {len(analysis.get('agent_scripts', {}).get('unused_candidates', []))}",
        "- TODO: 人工确认哪些高入度节点是真公共节点，哪些只是历史遗留或渠道覆盖。",
        "- TODO: 对关键入口任务跑一次 MaaMCP 实机截图/OCR，补充游戏首页、弹窗、返回路径。",
        "",
    ]
    return "\n".join(lines)


def write_basic_info(analysis: dict, overwrite: bool = False) -> Path:
    path = Path(analysis["project_root"]) / "basic_info.md"
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"{path} already exists; pass --overwrite only after explicit confirmation"
        )
    path.write_text(render_basic_info(analysis), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".", help="MaaFramework consumer project root")
    parser.add_argument("--json", action="store_true", help="print machine-readable analysis JSON")
    parser.add_argument("--write-basic-info", action="store_true", help="write <project_root>/basic_info.md")
    parser.add_argument("--overwrite", action="store_true", help="allow overwriting an existing basic_info.md")
    args = parser.parse_args(argv)

    analysis = analyze_project(args.project_root)
    if args.json:
        print(json.dumps(analysis, ensure_ascii=False, indent=2))
    else:
        print(render_summary(analysis))

    if args.write_basic_info:
        try:
            path = write_basic_info(analysis, overwrite=args.overwrite)
        except FileExistsError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
