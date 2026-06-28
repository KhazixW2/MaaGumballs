"""
pipeline-generate: 自动生成 OCR 文本节点并合并到指定 pipeline。

3 步工作流:
1. 连接 ADB 设备
2. 直接 ocr() 拿目标文字 box + score + 算 ROI
3. 合并到目标 pipeline

用法:
    python generate_node.py <target_text> <node_name> <pipeline_file>
    [--action ACTION] [--expand N] [--overwrite]
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Windows GBK 编码下 emoji/特殊字符报错 → 强制 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 默认基准分辨率
DEFAULT_SCREEN_W, DEFAULT_SCREEN_H = 720, 1280

# 项目根目录：脚本位于 .claude/skills/pipeline-generate/generate_node.py
PROJECT_ROOT = None

def find_project_root() -> Path:
    env_root = os.getenv("MAAHUB_ROOT") or os.getenv("PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()

    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / ".git").exists() or (parent / "package.json").exists() or (parent / "README.md").exists():
            return parent

    raise RuntimeError("无法定位项目根目录，请设置 MAAHUB_ROOT 或 PROJECT_ROOT 环境变量")


def get_screen_size(width: int | None, height: int | None) -> tuple[int, int]:
    if width is not None or height is not None:
        if width is None or height is None:
            raise ValueError("必须同时提供 --screen-width 和 --screen-height")
        return width, height

    env_size = os.getenv("SCREEN_SIZE")
    if env_size:
        parts = env_size.lower().split("x")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return int(parts[0]), int(parts[1])

    env_w = os.getenv("SCREEN_WIDTH")
    env_h = os.getenv("SCREEN_HEIGHT")
    if env_w and env_h and env_w.isdigit() and env_h.isdigit():
        return int(env_w), int(env_h)

    return DEFAULT_SCREEN_W, DEFAULT_SCREEN_H


def _val(r, key):
    """兼容 OCRResult 对象 (r.text) 和 dict (r['text'])。"""
    return getattr(r, key, None) if hasattr(r, key) else r[key]


def resolve_pipeline_path(pipeline_file: str) -> Path:
    """解析 pipeline 路径。绝对路径直接用；相对路径基于项目根目录的 assets/resource/base/pipeline/ 解析。"""
    path = Path(pipeline_file)
    if path.is_absolute():
        return path
    # 1. 先试 CWD（项目根）
    cwd_candidate = Path.cwd() / path
    if cwd_candidate.exists():
        return cwd_candidate
    # 2. 再试 PROJECT_ROOT（脚本所在位置的 4 级父目录）
    return PROJECT_ROOT / "assets" / "resource" / "base" / "pipeline" / pipeline_file


def connect_device():
    from maa_mcp.adb import find_adb_device_list, connect_adb_device
    devices = find_adb_device_list()
    if not devices:
        raise RuntimeError("未找到 ADB 设备，请启动模拟器或打开 USB 调试")
    if len(devices) > 1:
        print(f"发现 {len(devices)} 个设备，使用第一个: {devices[0]}")
    ctrl = connect_adb_device(devices[0])
    if not ctrl:
        raise RuntimeError(f"设备连接失败: {devices[0]}")
    return ctrl


def find_target_box(controller_id, target_text):
    """Step 2: 调 ocr() 拿 box，自动处理模型下载。"""
    from maa_mcp.vision import ocr
    from maa_mcp.download import check_and_download_ocr

    results = ocr(controller_id)
    # 首次可能 OCR 模型未下载
    if isinstance(results, str) and "OCR 模型文件不存在" in results:
        print("OCR 模型不存在，开始下载...")
        check_and_download_ocr()
        results = ocr(controller_id)
    if isinstance(results, str):
        raise RuntimeError(f"OCR 失败: {results}")

    matched = [r for r in results if target_text in (_val(r, "text") or "")]
    if not matched:
        raise RuntimeError(
            f"OCR 未在屏幕找到 '{target_text}'\n"
            f"请确认游戏窗口在前台，且该文字当前可见"
        )

    # 多匹配提示
    if len(matched) > 1:
        sorted_m = sorted(matched, key=lambda r: _val(r, "score"), reverse=True)
        diff = _val(sorted_m[0], "score") - _val(sorted_m[1], "score")
        if diff < 0.05:
            print(f"[WARN] 多个候选 score 接近 (差 {diff:.3f} < 0.05):")
            for i, r in enumerate(sorted_m):
                box = _val(r, "box")
                print(f"  [{i}] box={list(box)}, score={_val(r, 'score'):.3f}, text='{_val(r, 'text')}'")
            print("自动选 score 最高的")
        else:
            print(f"找到 {len(matched)} 个候选，自动选 score 最高的")

    best = max(matched, key=lambda r: _val(r, "score"))
    return list(_val(best, "box")), _val(best, "score")


def compute_roi(box, expand, screen_w: int, screen_h: int) -> list[int]:
    """扩大 ROI，并裁剪到当前屏幕尺寸内。宽高非法时回退到原始 box。"""
    x, y, w, h = box
    roi_x = max(0, x - expand)
    roi_y = max(0, y - expand)
    roi_w = min(screen_w - roi_x, w + 2 * expand)
    roi_h = min(screen_h - roi_y, h + 2 * expand)
    if roi_w <= 0 or roi_h <= 0:
        return [x, y, w, h]
    return [roi_x, roi_y, roi_w, roi_h]


def merge_into_pipeline(pipeline_file, node_name, node_config, overwrite):
    """Step 3: 合并节点到目标 pipeline 文件。"""
    from maa_mcp.pipeline_tools import load_pipeline, save_pipeline

    path = Path(pipeline_file)
    existing = load_pipeline(str(path.absolute())) if path.exists() else {}
    if isinstance(existing, str):
        raise RuntimeError(f"读取 pipeline 失败: {existing}")
    existing = existing or {}

    if node_name in existing and not overwrite:
        raise RuntimeError(
            f"节点 '{node_name}' 已存在，加 --overwrite 参数才能覆盖"
        )

    existing[node_name] = node_config
    result = save_pipeline(
        pipeline_json=json.dumps(existing, ensure_ascii=False, indent=4),
        output_path=str(path.absolute()),
        overwrite=True,
    )
    if isinstance(result, str) and "失败" in result:
        raise RuntimeError(result)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="自动生成 Pipeline OCR 文本节点 (3 步工作流)"
    )
    parser.add_argument("target_text", help="目标文字")
    parser.add_argument("node_name", help="节点名 (PascalCase)")
    parser.add_argument("pipeline_file", help="目标 pipeline 路径")
    parser.add_argument(
        "--action", default="Click",
        choices=["Click", "DoNothing", "LongPress", "Swipe", "ClickKey", "InputText"],
    )
    parser.add_argument("--expand", type=int, default=20, help="ROI 扩边像素（推荐 20-30，可先用 generate_sweep.py 测试）")
    parser.add_argument("--post-delay", type=int, default=500)
    parser.add_argument("--timeout", type=int, default=2000)
    parser.add_argument("--screen-width", type=int, default=None, help="屏幕宽度（默认 720，可通过环境变量 SCREEN_WIDTH 或 SCREEN_SIZE 读取）")
    parser.add_argument("--screen-height", type=int, default=None, help="屏幕高度（默认 1280，可通过环境变量 SCREEN_HEIGHT 或 SCREEN_SIZE 读取）")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    screen_w, screen_h = get_screen_size(args.screen_width, args.screen_height)
    global PROJECT_ROOT
    PROJECT_ROOT = find_project_root()

    # 解析 pipeline 路径：相对路径基于项目根目录的 assets/resource/base/pipeline/
    path = resolve_pipeline_path(args.pipeline_file)
    print(f"目标 pipeline: {path}")

    # === Step 1: 连接设备 ===
    print("\n=== Step 1: 连接设备 ===")
    ctrl = connect_device()
    print(f"已连接: {ctrl}")

    # === Step 2: OCR + 算 ROI ===
    print(f"\n=== Step 2: OCR 找 '{args.target_text}' ===")
    box, score = find_target_box(ctrl, args.target_text)
    roi = compute_roi(box, args.expand, screen_w, screen_h)
    print(f"匹配: box={box}, score={score:.3f}")
    print(f"扩大 ROI (expand={args.expand}): {roi}")

    # === Step 3: 合并 ===
    print(f"\n=== Step 3: 合并到 {path.name} ===")
    node_config = {
        "recognition": "OCR",
        "expected": [args.target_text],
        "roi": roi,
        "action": args.action,
        "post_delay": args.post_delay,
        "timeout": args.timeout,
    }
    result_path = merge_into_pipeline(str(path), args.node_name, node_config, args.overwrite)
    print(f"[OK] 已写入: {result_path}")

    # 回显
    print("\n" + "=" * 50)
    print(f"基准分辨率: {SCREEN_W}x{SCREEN_H}")
    print(f"OCR score: {score:.3f}")
    print(f"原始 box: {box}")
    print(f"扩大 ROI: {roi}")
    print(f"节点 {args.node_name} 已合并到 {path.name}")
    print("=" * 50)
    print("\n建议运行 /pipeline-testing 验证节点稳定性")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"\n[ERR] {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n用户取消", file=sys.stderr)
        sys.exit(130)
