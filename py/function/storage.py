#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工作目录与状态持久化。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .config_loader import LoadedConfig


def ensure_workdir(output_base: Path, session_id: str) -> Path:
    work_dir = output_base / session_id
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


def state_path(work_dir: Path) -> Path:
    return work_dir / "state.json"


def load_state(work_dir: Path) -> Dict[str, Any]:
    path = state_path(work_dir)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(work_dir: Path, state: Dict[str, Any]) -> None:
    path = state_path(work_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def init_state(config: LoadedConfig, session_id: str) -> Dict[str, Any]:
    return {
        "session_id": session_id,
        "config_hash": config.config_hash,
        "steps": {},
        "assets": {},
    }


def check_config_hash(saved_state: Dict[str, Any], config: LoadedConfig) -> bool:
    return saved_state.get("config_hash") == config.config_hash


__all__ = [
    "ensure_workdir",
    "state_path",
    "load_state",
    "save_state",
    "init_state",
    "check_config_hash",
]
