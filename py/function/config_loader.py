#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置加载与校验模块。"""

from __future__ import annotations

import json
import os
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
USER_CONFIG_PATH = PROJECT_ROOT / "user.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _config_hash(data: Dict[str, Any]) -> str:
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class MappingConfig:
    style_map: Dict[int, str] = field(default_factory=dict)
    resolution_map: Dict[int, str] = field(default_factory=dict)
    bool_map: Dict[int, bool] = field(default_factory=dict)
    position_map: Dict[int, str] = field(default_factory=dict)
    voice_map: Dict[int, str] = field(default_factory=dict)


@dataclass
class LoadedConfig:
    project_root: Path
    config_path: Path
    user_config_path: Path
    base_config: Dict[str, Any]
    user_config: Dict[str, Any]
    merged: Dict[str, Any]
    mappings: MappingConfig
    config_hash: str
    workflow: Dict[str, Any] = field(default_factory=dict)
    runtime: Dict[str, Any] = field(default_factory=dict)
    rate_limits: Dict[str, Any] = field(default_factory=dict)
    models: Dict[str, Any] = field(default_factory=dict)
    frontend: Dict[str, Any] = field(default_factory=dict)
    storage: Dict[str, Any] = field(default_factory=dict)
    frontend: Dict[str, Any] = field(default_factory=dict)


def build_mappings(config: Dict[str, Any]) -> MappingConfig:
    voices = config.get("audio", {}).get("voices", {})
    return MappingConfig(
        style_map={
            1: "cartoon_adventure",
            2: "luxury_fashion",
            3: "ink_xianxia",
            4: "realistic_3d",
            5: "cinematic",
            6: "technology",
            7: "cyberpunk",
            8: "space_exploration",
            9: "outdoor_adventure",
            10: "magical_fantasy",
        },
        resolution_map={1: "480p", 2: "720p", 3: "1080p"},
        bool_map={0: False, 1: True},
        position_map={1: "bottom", 2: "center", 3: "top"},
        voice_map={int(k): v.get("name") for k, v in voices.items() if isinstance(v, dict) and v.get("name")},
    )


def load_config() -> LoadedConfig:
    load_dotenv()

    base_config = _load_yaml(CONFIG_PATH)
    user_config = _load_yaml(USER_CONFIG_PATH)
    merged = _deep_merge(base_config, user_config)

    _require(merged.get("visual_styles"), "配置缺少 visual_styles")
    _require(merged.get("camera_movements"), "配置缺少 camera_movements")
    _require(merged.get("prompt_templates"), "配置缺少 prompt_templates")

    mappings = build_mappings(merged)
    cfg_hash = _config_hash(merged)
    workflow_cfg = merged.get("workflow", {})
    runtime_cfg = merged.get("runtime", {})
    rate_limits = merged.get("rate_limits", {})
    models_cfg = merged.get("models", {})
    frontend_cfg = merged.get("frontend", {})
    storage_cfg = merged.get("storage", {})

    return LoadedConfig(
        project_root=PROJECT_ROOT,
        config_path=CONFIG_PATH,
        user_config_path=USER_CONFIG_PATH,
        base_config=base_config,
        user_config=user_config,
        merged=merged,
        mappings=mappings,
        config_hash=cfg_hash,
        workflow=workflow_cfg,
        runtime=runtime_cfg,
        rate_limits=rate_limits,
        models=models_cfg,
        frontend=frontend_cfg,
        storage=storage_cfg,
    )


__all__ = ["LoadedConfig", "MappingConfig", "load_config", "build_mappings", "PROJECT_ROOT"]
