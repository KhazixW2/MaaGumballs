# -*- coding: utf-8 -*-
"""跨进程 / 跨重启的运行时状态存储。

只用来记"程序自己要记住的东西"（例如本局已经用了几次大地之门），
用户配置不要放这里（那属于 GUI 设置 / config/config.json）。

存储位置：<项目根>/config/runtime_state.json
  - config 目录已在 .gitignore 中，不会被提交
  - 路径用 __file__ 锚定，避免 dev 模式 cwd 被切到 assets/ 后路径漂移

结构：{"<namespace>": { ...任意 JSON 字段... }}
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from .logger import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # agent/utils/xxx.py -> 项目根
STATE_FILE = PROJECT_ROOT / "config" / "runtime_state.json"

_lock = threading.RLock()
_cache: dict[str, Any] | None = None


def _read() -> dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    data: dict[str, Any] = {}
    try:
        if STATE_FILE.exists():
            with STATE_FILE.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                data = raw
            else:
                logger.warning(f"[state] {STATE_FILE} 顶层不是 dict，已忽略")
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(f"[state] 读取 {STATE_FILE} 失败，按空状态继续: {exc}")
    _cache = data
    return data


def _write(data: dict[str, Any]) -> None:
    """原子写：先写临时文件再 os.replace，避免进程被杀时留下半截 JSON。"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".runtime_state.", suffix=".tmp", dir=str(STATE_FILE.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, STATE_FILE)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except OSError:
                pass


def get(namespace: str, default: Any = None) -> Any:
    with _lock:
        return _read().get(namespace, default)


def put(namespace: str, value: Any) -> None:
    with _lock:
        data = _read()
        if data.get(namespace) == value:
            return
        data[namespace] = value
        try:
            _write(data)
        except OSError as exc:
            logger.warning(f"[state] 写入 {STATE_FILE} 失败: {exc}")


def update(namespace: str, **fields: Any) -> dict[str, Any]:
    """把若干字段合并进某个 namespace 并落盘，返回合并后的记录。"""
    with _lock:
        data = _read()
        record = data.get(namespace)
        record = dict(record) if isinstance(record, dict) else {}
        record.update(fields)
        data[namespace] = record
        try:
            _write(data)
        except OSError as exc:
            logger.warning(f"[state] 写入 {STATE_FILE} 失败: {exc}")
        return record


def clear(namespace: str) -> None:
    with _lock:
        data = _read()
        if namespace in data:
            data.pop(namespace, None)
            try:
                _write(data)
            except OSError as exc:
                logger.warning(f"[state] 写入 {STATE_FILE} 失败: {exc}")
