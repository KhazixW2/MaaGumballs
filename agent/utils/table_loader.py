"""配置表加载工具

参照 MAAGC 项目 (f:/workspace/MAAGC/) 的加载方式,用 cwd 相对路径:

    cwd_dir = os.getcwd()
    table_file = cwd_dir / "table" / "sky_events.json"

**前置条件**: `agent/main.py` 启动时已把 cwd 切到 `assets/`,所以 `cwd_dir/table/`
能正确解析到 `assets/table/`。这条规则与 MAAGC 完全一致(MAAGC 的 main.py 同样在 dev
模式下 `os.chdir(Path("./assets"))`)。

为什么不用 `__file__` 解析的绝对路径:
- 项目结构可能改(`assets/` 目录未来可能被替换为其他名字)
- 跟 MAAGC 保持一致降低维护成本
- main.py 已经处理了 cwd 切换,模块层用 cwd 相对路径更直观
"""
import os
from pathlib import Path
from typing import Any

from .logger import logger

# 配置表目录(相对 cwd)
# 假设 main.py 把 cwd 切到 assets/ → cwd_dir/table/ = assets/table/
_TABLE_DIR = Path("table")


def _resolve(name: str) -> Path:
    """解析配置表实际路径(只用 cwd 相对路径,跟 MAAGC 一致)。

    Args:
        name: 配置文件名(如 "sky_events.json"),不带路径。

    Returns:
        Path: 解析后的路径。如果文件不存在仍返回路径(让调用方看到 error)。
    """
    return _TABLE_DIR / name


def load_table(name: str) -> Any:
    """加载配置表 JSON,路径解析为 ``cwd_dir/table/{name}``。

    使用方法:
        from utils.table_loader import load_table
        events = load_table("sky_events.json")

    Args:
        name: 配置文件名,如 "sky_events.json"、"情报奖励-初级情报.json"。

    Returns:
        解析后的 Python 对象(list / dict / str 等)。

    Raises:
        FileNotFoundError: 文件不存在。
        json.JSONDecodeError: 文件不是合法 JSON。
    """
    import json
    path = _resolve(name)
    if not path.exists():
        raise FileNotFoundError(
            f"配置表 '{name}' 在 {path!s} 找不到。\n"
            f"当前 cwd = {Path.cwd()}\n"
            f"如果 dev 模式:检查 main.py 是否正确 os.chdir 到 assets/。\n"
            f"如果 release:检查 install_resource() 是否 copy 了 table/ 目录。"
        )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"加载配置表 {name!r} 来自 {path}")
    return data


def get_table_path(name: str) -> Path:
    """获取配置表实际路径(不读取内容)。

    Args:
        name: 配置文件名。

    Returns:
        Path: 解析后的路径(``cwd_dir/table/{name}``)。
    """
    return _resolve(name)
