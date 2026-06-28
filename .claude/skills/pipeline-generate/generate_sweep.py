"""
pipeline-generate ROI Sweep 测试工具。

用法:
    python generate_sweep.py <target_text> <box> [expands]
    python generate_sweep.py "角色" "46,1248,50,30"
    python generate_sweep.py "角色" "46,1248,50,30" 0,5,10,15,20,25,30,50,100

输出:
    在 generate_sweep/<text>_<expands>.json 生成测试 pipeline
    打印每条 expand 的 ROI 范围
    然后用 run_pipeline 逐个测试（手动）
"""

import os
import re
import sys
import json
from pathlib import Path

# 默认基准分辨率
DEFAULT_SCREEN_W, DEFAULT_SCREEN_H = 720, 1280

# 项目根目录：脚本位于 .claude/skills/pipeline-generate/
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


def sanitize_filename(name: str) -> str:
    safe = re.sub(r"[\\/]+", "_", name)
    safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff _\-]+", "_", safe)
    return safe.strip("_ ") or "target_text"


def parse_expands(arg: str) -> list[int]:
    """解析 '0,5,10,20' 字符串为 [0, 5, 10, 20]"""
    return [int(x.strip()) for x in arg.split(",")]


def parse_box(arg: str) -> tuple[int, int, int, int]:
    """解析 'x,y,w,h' 字符串为 (x, y, w, h) 元组"""
    parts = [int(x.strip()) for x in arg.split(",")]
    if len(parts) != 4:
        raise ValueError(f"box 格式错误: {arg}，应为 'x,y,w,h'")
    return tuple(parts)


def compute_roi(box: tuple[int, int, int, int], expand: int, screen_w: int, screen_h: int) -> list[int]:
    """计算扩大后的 ROI，限制不超出屏幕边界；宽高非法时回退到原始 box。"""
    x, y, w, h = box
    roi_x = max(0, x - expand)
    roi_y = max(0, y - expand)
    roi_w = min(screen_w - roi_x, w + 2 * expand)
    roi_h = min(screen_h - roi_y, h + 2 * expand)
    if roi_w <= 0 or roi_h <= 0:
        return [x, y, w, h]
    return [roi_x, roi_y, roi_w, roi_h]


def make_sweep_pipeline(
    target_text: str,
    box: tuple[int, int, int, int],
    expands: list[int],
    output_path: str,
    screen_w: int,
    screen_h: int,
) -> dict:
    """生成 ROI sweep 测试 pipeline"""
    nodes = {}
    for e in expands:
        roi = compute_roi(box, e, screen_w, screen_h)
        node_name = f"Sweep_{target_text}_e{e}"
        nodes[node_name] = {
            "recognition": "OCR",
            "expected": [target_text],
            "roi": roi,
            "action": "DoNothing",  # 只测识别，不点
            "post_delay": 100,
            "timeout": 2000,
        }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    return nodes


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    target_text = sys.argv[1]
    box = parse_box(sys.argv[2])
    expands = parse_expands(sys.argv[3]) if len(sys.argv) > 3 else [0, 5, 10, 15, 20, 25, 30, 50, 100]
    screen_w, screen_h = get_screen_size(None, None)
    global PROJECT_ROOT
    PROJECT_ROOT = find_project_root()

    safe_target_text = sanitize_filename(target_text)
    expand_suffix = "_".join(str(v) for v in expands)
    output_dir = PROJECT_ROOT / "generate_sweep"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{safe_target_text}_{expand_suffix}.json"

    nodes = make_sweep_pipeline(target_text, box, expands, str(output_path), screen_w, screen_h)

    print(f"生成 sweep pipeline: {output_path}")
    print(f"目标文字: {target_text}")
    print(f"原始 box: {box}")
    print(f"测试 expand: {expands}")
    print()
    print("ROI 范围预览:")
    for name, node in nodes.items():
        print(f"  {name}: roi={node['roi']}")

    print()
    print("=" * 60)
    print("下一步: 用 run_pipeline 逐个测试 (action: DoNothing)")
    print(f"  run_pipeline(pipeline_path='{output_path}', entry='Sweep_{target_text}_e20', ...)")
    print()
    print("测试后选最佳 expand, 然后从项目根目录运行:")
    print(f"  python .claude/skills/pipeline-generate/generate_node.py \"{target_text}\" <NodeName> <target_pipeline> --expand <best> --overwrite")


if __name__ == "__main__":
    main()
