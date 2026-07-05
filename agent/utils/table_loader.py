"""配置表加载工具

参照 MAAGC 项目 (f:/workspace/MAAGC/) 的加载方式,但用更健壮的绝对路径:

- MAAGC 模式: `cwd_dir/table/xxx.json` (依赖 main.py 把 cwd 切到 assets/)
- MaaGumballs 模式: `__file__.resolve() → ../../.. → assets/table/xxx.json`
  (不依赖 cwd,在 release 包和 dev 环境都能用)

为什么用 `assets/table/` 而不是放在 `assets/resource/table/`:
- MaaGumballs 跟 MAAGC 一样用 `assets/table/`(同级放)
- `tools/install_V2.py` / `tools/install.py` 的 `install_resource()` 现在会 copy
  `assets/table/` 到 `install_path/table/`,CI 打包时自动包含
- `intelligence_data/` 是 dev 源数据(供开发时编辑),fallback 路径
"""
from pathlib import Path
from typing import Any

from .logger import logger

# 项目根目录 = utils 的上上上级
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# 优先路径(release / CI 打包, install_resource() 会 copy 到 install_path/table/)
_TABLE_DIR = _PROJECT_ROOT / "assets" / "table"
# Fallback 路径(dev 源数据,可能与 table 不一致)
_SOURCE_DIR = _PROJECT_ROOT / "intelligence_data"


def _resolve(name: str) -> Path:
    """根据 name 解析配置表实际路径(优先 table/,fallback intelligence_data/)。

    Args:
        name: 配置文件名(如 "sky_events.json"),不带路径。

    Returns:
        Path: 实际存在的文件路径(如果都不存在返回 table/ 路径,让调用方自己 fail)。
    """
    table_path = _TABLE_DIR / name
    if table_path.exists():
        return table_path
    source_path = _SOURCE_DIR / name
    if source_path.exists():
        return source_path
    # 两个都不存在,返回 table 路径(让调用方看到一致的 error 路径)
    return table_path


def load_table(name: str) -> Any:
    """加载配置表 JSON,优先 table/ 目录,fallback intelligence_data/。

    使用方法:
        from utils.table_loader import load_table
        events = load_table("sky_events.json")

    Args:
        name: 配置文件名,如 "sky_events.json"、"情报奖励-初级情报.json"。

    Returns:
        解析后的 Python 对象(list / dict / str 等)。

    Raises:
        FileNotFoundError: 两个路径都找不到。
        json.JSONDecodeError: 文件不是合法 JSON。
    """
    path = _resolve(name)
    if not path.exists():
        raise FileNotFoundError(
            f"配置表 '{name}' 在以下路径都找不到:\n"
            f"  - {_TABLE_DIR / name}\n"
            f"  - {_SOURCE_DIR / name}\n"
            f"如果是 dev,请检查 {(_SOURCE_DIR / name)!s} 是否存在。\n"
            f"如果是 release,请检查 install_resource() 是否 copy 了 table/ 目录。"
        )
    with open(path, "r", encoding="utf-8") as f:
        import json
        data = json.load(f)
    logger.info(f"加载配置表 {name!r} 来自 {path}")
    return data


def get_table_path(name: str) -> Path:
    """获取配置表实际路径(不读取内容)。

    Args:
        name: 配置文件名。

    Returns:
        Path: 实际文件路径(优先 table/,fallback intelligence_data/)。
    """
    return _resolve(name)
