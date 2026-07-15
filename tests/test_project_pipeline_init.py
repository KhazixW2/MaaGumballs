import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / ".claude"
    / "skills"
    / "project-pipeline-init"
    / "scripts"
    / "analyze_pipeline_project.py"
)


def load_analyzer():
    spec = importlib.util.spec_from_file_location("analyze_pipeline_project", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def make_consumer_project(tmp_path: Path) -> Path:
    root = tmp_path / "MaaExampleGame"
    assets = root / "assets"
    write_json(
        assets / "interface.json",
        {
            "name": "MaaExampleGame",
            "url": "https://example.invalid/MaaExampleGame",
            "controller": [{"name": "ADB 默认方式", "type": "Adb"}],
            "resource": [
                {"name": "官服", "path": ["./resource/base"]},
                {"name": "渠道服", "path": ["./resource/base", "./resource/channel"]},
            ],
            "agent": {
                "child_exec": "python",
                "child_args": ["-u", "./agent/main.py"],
            },
            "task": [
                {"name": "启动游戏", "entry": "Start"},
                {"name": "每日任务", "entry": "DailyTask"},
            ],
        },
    )
    write_json(
        assets / "resource" / "base" / "default_pipeline.json",
        {
            "Default": {"post_delay": 100},
            "TemplateMatch": {"recognition": "TemplateMatch", "threshold": 0.7},
        },
    )
    write_json(
        assets / "resource" / "base" / "pipeline" / "utils.json",
        {
            "BackText": {
                "recognition": "OCR",
                "expected": "返回",
                "roi": [500, 1100, 180, 80],
                "action": "Click",
            },
            "ConfirmButton": {
                "recognition": "OCR",
                "expected": ["确定", "确认"],
                "roi": [30, 400, 660, 420],
                "action": "Click",
            },
            "PopupClose": {
                "recognition": "TemplateMatch",
                "template": "utils/Close.png",
                "action": "Click",
            },
            "AndroidBackKey": {
                "recognition": "DirectHit",
                "action": "ClickKey",
                "key": 4,
            },
            "ReturnHall": {
                "recognition": "DirectHit",
                "next": [
                    "CheckHall",
                    "[JumpBack]BackText",
                    {"name": "ConfirmButton", "jump_back": True},
                ],
            },
            "CheckHall": {
                "recognition": "OCR",
                "expected": "大厅",
            },
        },
    )
    write_json(
        assets / "resource" / "base" / "pipeline" / "main.json",
        {
            "Start": {
                "next": ["TaskNode", "[JumpBack]ReturnHall"],
                "on_error": "ConfirmButton",
                "interrupt": ["PopupClose"],
            },
            "TaskNode": {
                "recognition": "TemplateMatch",
                "template": "task/Task.png",
                "action": "Click",
                "next": ["AndroidBackKey", "MissingNode"],
            },
            "DailyTask": {
                "recognition": "DirectHit",
                "next": ["TaskNode", "[JumpBack]BackText"],
            },
            "SelfLoop": {
                "recognition": "DirectHit",
                "next": "SelfLoop",
            },
            "IsolatedProbe": {
                "recognition": "OCR",
                "expected": "孤立",
            },
            "V2BackKey": {
                "recognition": {
                    "type": "TemplateMatch",
                    "param": {
                        "template": "utils/BackButton.png",
                        "roi": [500, 1100, 180, 80],
                    },
                },
                "action": {"type": "ClickKey", "param": {"key": 4}},
            },
            "V2OcrProbe": {
                "recognition": {
                    "type": "OCR",
                    "param": {
                        "expected": ["外部入口"],
                        "roi": [30, 40, 200, 80],
                    },
                },
            },
        },
    )
    write_json(
        assets / "resource" / "channel" / "pipeline" / "start_up.json",
        {
            "ChannelStart": {
                "recognition": "DirectHit",
                "next": ["Start"],
            }
        },
    )
    for image in [
        assets / "resource" / "base" / "image" / "utils" / "Close.png",
        assets / "resource" / "base" / "image" / "utils" / "BackButton.png",
        assets / "resource" / "base" / "image" / "task" / "Task.png",
    ]:
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"png")
    agent = root / "agent" / "action" / "example.py"
    agent.parent.mkdir(parents=True, exist_ok=True)
    agent.write_text(
        "def run(context, dynamic_name):\n"
        "    context.run_task('V2OcrProbe')\n"
        "    context.run_recognition('CheckHall', None)\n"
        "    context.run_task(dynamic_name)\n",
        encoding="utf-8",
    )
    return root


def test_analyze_project_finds_entries_edges_common_nodes_and_images(tmp_path: Path):
    analyzer = load_analyzer()
    root = make_consumer_project(tmp_path)

    result = analyzer.analyze_project(root)
    pipeline = result["pipeline"]

    assert result["project_name"] == "MaaExampleGame"
    assert result["controllers"] == ["Adb"]
    assert {task["entry"] for task in result["tasks"]} == {"Start", "DailyTask"}
    assert result["pipeline_file_count"] == 3
    assert pipeline["edge_type_counts"]["next"] >= 8
    assert pipeline["edge_type_counts"]["on_error"] == 1
    assert pipeline["edge_type_counts"]["interrupt"] == 1
    assert "MissingNode" in pipeline["unresolved_refs"]
    assert ["SelfLoop"] in pipeline["cycle_candidates"]
    assert "Start" in pipeline["node_names"]

    common_names = {item["name"] for item in pipeline["common_nodes"]}
    return_names = {item["name"] for item in pipeline["return_exit_nodes"]}
    confirm_names = {item["name"] for item in pipeline["confirm_nodes"]}

    assert {"BackText", "ConfirmButton", "ReturnHall"} <= common_names
    assert {"BackText", "ReturnHall", "AndroidBackKey"} <= return_names
    assert "ConfirmButton" in confirm_names
    assert result["image_summary"]["image_count"] == 3
    assert any(item["dir"].endswith("utils") for item in result["image_summary"]["top_dirs"])

    flows = {flow["entry"]: flow for flow in pipeline["task_flow_graphs"]}
    start_flow = flows["Start"]
    assert start_flow["entry_found"] is True
    assert "TaskNode" in start_flow["nodes"]
    assert "MissingNode" in start_flow["unresolved_refs"]
    assert start_flow["primary_path"][:2] == ["Start", "TaskNode"]
    assert any(edge["field"] == "on_error" for edge in start_flow["edges"])
    assert any(edge["field"] == "interrupt" for edge in start_flow["edges"])
    assert any("JumpBack" in edge["attrs"] for edge in start_flow["edges"])
    assert any(item["node"] == "V2OcrProbe" for item in pipeline["ocr_expected"])
    assert any(item["node"] == "V2BackKey" for item in pipeline["templates"])
    assert "V2BackKey" in return_names
    assert pipeline["python_pipeline"]["targets"] == ["CheckHall", "V2OcrProbe"]
    assert {
        (item["kind"], item["target"]): item["count"]
        for item in pipeline["python_pipeline"]["call_summaries"]
    } == {("run_recognition", "CheckHall"): 1, ("run_task", "V2OcrProbe"): 1}
    assert len(pipeline["python_pipeline"]["dynamic_calls"]) == 1
    assert "V2OcrProbe" in pipeline["external_entry_nodes"]
    assert "V2OcrProbe" not in pipeline["orphan_candidates"]
    assert "IsolatedProbe" in pipeline["orphan_candidates"]


def test_render_and_write_basic_info_refuses_existing_file(tmp_path: Path):
    analyzer = load_analyzer()
    root = make_consumer_project(tmp_path)
    result = analyzer.analyze_project(root)

    content = analyzer.render_basic_info(result)
    assert "MaaExampleGame" in content
    assert "Start" in content
    assert "BackText" in content
    assert "ConfirmButton" in content
    assert "MissingNode" in content
    assert "TemplateMatch" in content
    assert "入口主链路流程图" in content
    assert "flowchart TD" in content
    assert "Maa Skills 接力协议" in content
    assert "Python / interface 外部入口" in content
    assert "V2OcrProbe" in content
    assert "static-scan-only" in content

    written = analyzer.write_basic_info(result)
    assert written == root / "basic_info.md"
    assert written.read_text(encoding="utf-8") == content

    with pytest.raises(FileExistsError):
        analyzer.write_basic_info(result)

    overwritten = analyzer.write_basic_info(result, overwrite=True)
    assert overwritten == written


# ---------------------------------------------------------------------------
# Agent script scanning tests
# ---------------------------------------------------------------------------


def make_consumer_project_with_agent_main(tmp_path: Path) -> Path:
    """与 make_consumer_project 相同，但额外创建 agent/main.py（命中 child_args）。"""
    root = make_consumer_project(tmp_path)
    main_script = root / "agent" / "main.py"
    main_script.parent.mkdir(parents=True, exist_ok=True)
    main_script.write_text("# agent entry\n", encoding="utf-8")
    return root


def _build_minimal_project(tmp_path: Path, agent_block: dict[str, Any]) -> Path:
    root = tmp_path / "Project"
    assets = root / "assets"
    write_json(
        assets / "interface.json",
        {
            "name": "Project",
            "controller": [{"name": "ADB", "type": "Adb"}],
            "resource": [{"name": "default", "path": ["./resource/base"]}],
            "agent": agent_block,
            "task": [],
        },
    )
    (assets / "resource" / "base").mkdir(parents=True, exist_ok=True)
    return root


class TestResolveAgentArg:
    def test_resolved_at_level_zero(self, tmp_path: Path):
        analyzer = load_analyzer()
        script = tmp_path / "agent" / "main.py"
        script.parent.mkdir(parents=True)
        script.touch()
        result = analyzer.resolve_agent_arg(tmp_path, "./agent/main.py")
        assert result["status"] == "resolved"
        assert result["resolved_at_level"] == 0
        assert Path(result["resolved"]).resolve() == script.resolve()
        assert result["is_py"] is True
        assert result["is_absolute"] is False

    def test_resolved_at_parent_level(self, tmp_path: Path):
        analyzer = load_analyzer()
        repo = tmp_path / "repo"
        assets = repo / "assets"
        assets.mkdir(parents=True)
        script = repo / "agent" / "main.py"
        script.parent.mkdir(parents=True)
        script.touch()
        result = analyzer.resolve_agent_arg(assets, "./agent/main.py")
        assert result["status"] == "resolved"
        # candidates[0] = assets/agent/main.py (level 0, missing)
        # candidates[1] = repo/agent/main.py (level 1, hits here)
        assert result["resolved_at_level"] == 1
        assert Path(result["resolved"]).resolve() == script.resolve()

    def test_unresolved_returns_none(self, tmp_path: Path):
        analyzer = load_analyzer()
        result = analyzer.resolve_agent_arg(tmp_path, "agent/missing.py")
        assert result["status"] == "unresolved"
        assert result["resolved"] is None
        assert result["resolved_at_level"] == -1
        assert len(result["candidates"]) >= 1

    def test_absolute_path_kept_as_is(self, tmp_path: Path):
        analyzer = load_analyzer()
        script = tmp_path / "main.py"
        script.touch()
        result = analyzer.resolve_agent_arg(tmp_path, str(script))
        assert result["is_absolute"] is True
        assert result["status"] == "absolute"
        assert result["resolved"] == str(script)

    def test_non_py_arg_short_circuits(self, tmp_path: Path):
        analyzer = load_analyzer()
        result = analyzer.resolve_agent_arg(tmp_path, "-u")
        assert result["is_py"] is False
        assert result["status"] == "non-py"
        assert result["resolved"] is None
        assert result["candidates"] == []

    def test_empty_arg_short_circuits(self, tmp_path: Path):
        analyzer = load_analyzer()
        result = analyzer.resolve_agent_arg(tmp_path, "")
        assert result["status"] == "non-py"
        assert result["resolved"] is None


class TestDiscoverAgentCandidates:
    def test_root_level_main_py_found(self, tmp_path: Path):
        analyzer = load_analyzer()
        script = tmp_path / "agent" / "main.py"
        script.parent.mkdir(parents=True)
        script.touch()
        result = analyzer.discover_agent_candidates(tmp_path)
        candidates = {item["candidate"] for item in result}
        assert str(script) in candidates
        match = next(item for item in result if item["candidate"] == str(script))
        assert match["exists"] is True
        assert match["level"] == 0

    def test_existing_and_missing_both_listed(self, tmp_path: Path):
        analyzer = load_analyzer()
        (tmp_path / "agent").mkdir()
        (tmp_path / "agent" / "main.py").touch()
        result = analyzer.discover_agent_candidates(tmp_path)
        main_exists = next(
            item for item in result if item["candidate"].endswith("agent\\main.py")
            or item["candidate"].endswith("agent/main.py")
        )
        server_missing = next(
            item for item in result if item["candidate"].endswith("agent\\server.py")
            or item["candidate"].endswith("agent/server.py")
        )
        assert main_exists["exists"] is True
        assert server_missing["exists"] is False

    def test_does_not_recurse_into_subdirectories(self, tmp_path: Path):
        analyzer = load_analyzer()
        nested = tmp_path / "agent" / "action" / "weird_main.py"
        nested.parent.mkdir(parents=True)
        nested.touch()
        result = analyzer.discover_agent_candidates(tmp_path)
        # nested file should NOT appear (we only look at convention basenames at agent/<basename>)
        assert not any(item["candidate"].endswith("weird_main.py") for item in result)

    def test_walks_ancestors_up_to_limit(self, tmp_path: Path):
        analyzer = load_analyzer()
        # tmp_path/grandparent/parent/child  → root=child, walk up to grandparent (level 2)
        grandparent = tmp_path / "grandparent"
        parent = grandparent / "parent"
        child = parent / "child"
        child.mkdir(parents=True)
        # Place main.py at grandparent level
        (grandparent / "agent").mkdir()
        (grandparent / "agent" / "main.py").touch()
        result = analyzer.discover_agent_candidates(child)
        levels = [item["level"] for item in result if item.get("exists")]
        # Should discover grandparent's agent/main.py (level 2)
        assert 2 in levels

    def test_skips_disallowed_ancestor(self, tmp_path: Path):
        analyzer = load_analyzer()
        venv = tmp_path / ".venv" / "project"
        venv.mkdir(parents=True)
        (venv / "agent").mkdir()
        (venv / "agent" / "main.py").touch()
        result = analyzer.discover_agent_candidates(venv)
        # .venv is in SKIP_DIR_NAMES → should be filtered out
        # All candidates should be from venv or its descendants (which is just venv itself)
        # Since venv should_skip(), its candidates get filtered
        assert all(item["level"] >= 0 for item in result)


class TestAnalyzeAgentScripts:
    def test_returns_empty_skeleton_without_interface(self, tmp_path: Path):
        analyzer = load_analyzer()
        result = analyzer.analyze_agent_scripts(tmp_path, None, {})
        assert result["agent_block_present"] is False
        assert result["declared"] == []
        assert result["discovered"] == []
        assert result["declared_resolved"] == []
        assert result["warnings"] == []

    def test_unresolved_when_file_missing(self, tmp_path: Path):
        analyzer = load_analyzer()
        # Use the existing make_consumer_project fixture which has child_args pointing to ./agent/main.py
        # but does NOT create that file.
        root = make_consumer_project(tmp_path)
        interface_path = root / "assets" / "interface.json"
        with interface_path.open("r", encoding="utf-8") as fh:
            interface = json.load(fh)
        result = analyzer.analyze_agent_scripts(root, interface_path, interface.get("agent") or {})
        assert result["agent_block_present"] is True
        assert result["declared_unresolved_count"] == 1  # ./agent/main.py
        assert "./agent/main.py" in [item["arg"] for item in result["declared"] if item["status"] == "unresolved"]
        assert any("./agent/main.py" in w for w in result["warnings"])

    def test_resolved_when_file_exists(self, tmp_path: Path):
        analyzer = load_analyzer()
        root = make_consumer_project_with_agent_main(tmp_path)
        interface_path = root / "assets" / "interface.json"
        with interface_path.open("r", encoding="utf-8") as fh:
            interface = json.load(fh)
        result = analyzer.analyze_agent_scripts(root, interface_path, interface.get("agent") or {})
        assert result["declared_resolved_count"] == 1
        assert result["declared_unresolved_count"] == 0
        assert any(item.endswith("agent\\main.py") or item.endswith("agent/main.py") for item in result["declared_resolved"])

    def test_orphan_declarations_when_outside_convention(self, tmp_path: Path):
        analyzer = load_analyzer()
        # child_args 指向 agent/custom_entry.py，不在 AGENT_ENTRY_BASENAMES 清单
        root = _build_minimal_project(
            tmp_path,
            {"child_exec": "python", "child_args": ["agent/custom_entry.py"]},
        )
        # 真实创建该文件
        script = root / "assets" / "agent" / "custom_entry.py"
        script.parent.mkdir(parents=True)
        script.touch()
        interface_path = root / "assets" / "interface.json"
        with interface_path.open("r", encoding="utf-8") as fh:
            interface = json.load(fh)
        result = analyzer.analyze_agent_scripts(root, interface_path, interface.get("agent") or {})
        assert result["declared_resolved_count"] == 1
        assert len(result["orphan_declarations"]) == 1
        assert result["orphan_declarations"][0].endswith("custom_entry.py")

    def test_unused_candidates_when_discovered_not_referenced(self, tmp_path: Path):
        analyzer = load_analyzer()
        # child_args 指向 ./agent/main.py；同时仓库里额外存在 ./agent/server.py 没用上
        root = _build_minimal_project(
            tmp_path,
            {"child_exec": "python", "child_args": ["./agent/main.py"]},
        )
        (root / "assets" / "agent").mkdir(parents=True)
        (root / "assets" / "agent" / "main.py").touch()
        (root / "assets" / "agent" / "server.py").touch()
        interface_path = root / "assets" / "interface.json"
        with interface_path.open("r", encoding="utf-8") as fh:
            interface = json.load(fh)
        result = analyzer.analyze_agent_scripts(root, interface_path, interface.get("agent") or {})
        # main.py referenced; server.py exists but not referenced
        unused_paths = [p for p in result["unused_candidates"] if p.endswith("server.py")]
        assert len(unused_paths) == 1

    def test_absolute_and_non_py_skipped_from_unresolved(self, tmp_path: Path):
        analyzer = load_analyzer()
        # Use a real absolute .py path that exists, plus a non-.py flag.
        real_script = tmp_path / "real_agent.py"
        real_script.touch()
        root = _build_minimal_project(
            tmp_path,
            {"child_exec": "python", "child_args": ["-u", str(real_script)]},
        )
        interface_path = root / "assets" / "interface.json"
        with interface_path.open("r", encoding="utf-8") as fh:
            interface = json.load(fh)
        result = analyzer.analyze_agent_scripts(root, interface_path, interface.get("agent") or {})
        # Neither -u nor existing absolute .py path should count toward unresolved
        assert result["declared_unresolved_count"] == 0
        assert result["declared_resolved_count"] == 1

    def test_warning_when_no_py_entries(self, tmp_path: Path):
        analyzer = load_analyzer()
        root = _build_minimal_project(
            tmp_path,
            {"child_exec": "python", "child_args": ["-u", "-X", "utf8"]},
        )
        interface_path = root / "assets" / "interface.json"
        with interface_path.open("r", encoding="utf-8") as fh:
            interface = json.load(fh)
        result = analyzer.analyze_agent_scripts(root, interface_path, interface.get("agent") or {})
        assert any("没有任何 .py" in w for w in result["warnings"])


class TestRenderAgentScriptPaths:
    def test_basic_info_includes_both_tables(self, tmp_path: Path):
        analyzer = load_analyzer()
        root = make_consumer_project(tmp_path)
        result = analyzer.analyze_project(root)
        content = analyzer.render_basic_info(result)
        assert "Agent script paths" in content
        assert "Declared (interface.json child_args)" in content
        assert "Discovered (root 与 4 层 ancestor" in content
        assert "Cross-check" in content
        assert "./agent/main.py" in content

    def test_basic_info_risk_bullet_counts_unresolved(self, tmp_path: Path):
        analyzer = load_analyzer()
        root = make_consumer_project(tmp_path)
        result = analyzer.analyze_project(root)
        content = analyzer.render_basic_info(result)
        assert "Agent script paths unresolved:" in content

    def test_basic_info_no_agent_block_shows_placeholder(self, tmp_path: Path):
        analyzer = load_analyzer()
        # Build a project WITHOUT agent block
        root = tmp_path / "NoAgent"
        (root / "assets" / "resource" / "base").mkdir(parents=True)
        write_json(
            root / "assets" / "interface.json",
            {
                "name": "NoAgent",
                "controller": [{"type": "Adb"}],
                "resource": [{"name": "default", "path": ["./resource/base"]}],
                "task": [],
            },
        )
        result = analyzer.analyze_project(root)
        content = analyzer.render_basic_info(result)
        assert "No agent block / child_args detected" in content

    def test_summary_includes_agent_script_paths_section(self, tmp_path: Path):
        analyzer = load_analyzer()
        root = make_consumer_project(tmp_path)
        result = analyzer.analyze_project(root)
        summary = analyzer.render_summary(result)
        assert "## Agent Script Paths" in summary
        assert "Declared (interface.json child_args)" in summary

    def test_summary_risks_includes_agent_counters(self, tmp_path: Path):
        analyzer = load_analyzer()
        root = make_consumer_project(tmp_path)
        result = analyzer.analyze_project(root)
        summary = analyzer.render_summary(result)
        assert "Unresolved agent script paths:" in summary
        assert "Orphan agent script path declarations:" in summary
        assert "Unreferenced agent entry candidates:" in summary


def test_analyze_project_includes_agent_scripts_field(tmp_path: Path):
    analyzer = load_analyzer()
    root = make_consumer_project(tmp_path)
    result = analyzer.analyze_project(root)
    assert "agent_scripts" in result
    assert result["agent_scripts"]["agent_block_present"] is True
    assert result["agent_scripts"]["declared_unresolved_count"] == 1
