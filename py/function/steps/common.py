#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤通用工具。"""

from __future__ import annotations

from typing import Any, Dict

from ..context import RunContext


def resolve_style_key(ctx: RunContext) -> str:
    style_value: Any = ctx.options.get("style")
    if style_value is None:
        style_value = (ctx.config.user_config or {}).get("style") if isinstance(ctx.config.user_config, dict) else None
    if style_value is None and isinstance(ctx.config.merged, dict):
        style_value = ctx.config.merged.get("style")

    style_map = ctx.config.mappings.style_map
    if isinstance(style_value, str) and style_value.isdigit():
        style_value = int(style_value)

    if isinstance(style_value, int) and style_value in style_map:
        return style_map[style_value]

    visual_styles = ctx.config.base_config.get("visual_styles", {}) if isinstance(ctx.config.base_config, dict) else {}
    if isinstance(style_value, str) and style_value in visual_styles:
        return style_value

    return style_map.get(1) or next(iter(style_map.values()), "cartoon_adventure")


def resolve_resolution(ctx: RunContext) -> str:
    value: Any = ctx.options.get("resolution")
    if value is None:
        value = (ctx.config.user_config or {}).get("resolution") if isinstance(ctx.config.user_config, dict) else None
    if value is None and isinstance(ctx.config.merged, dict):
        value = ctx.config.merged.get("resolution")

    res_map = ctx.config.mappings.resolution_map
    if isinstance(value, str) and value.isdigit():
        value = int(value)
    if isinstance(value, int) and value in res_map:
        return res_map[value]
    if isinstance(value, str) and value:
        return value
    return res_map.get(1, "480p")


def resolve_shot_count(ctx: RunContext, override: Any = None) -> int:
    if override is not None:
        try:
            return int(override)
        except (TypeError, ValueError):
            pass

    value: Any = ctx.options.get("shots")
    if value is None and isinstance(ctx.config.user_config, dict):
        value = ctx.config.user_config.get("shot_count")
    if value is None and isinstance(ctx.config.merged, dict):
        value = ctx.config.merged.get("shot_count")

    try:
        return int(value)
    except (TypeError, ValueError):
        return 3


def resolve_topic(ctx: RunContext) -> str:
    topic: Any = (ctx.config.user_config or {}).get("topic") if isinstance(ctx.config.user_config, dict) else None
    if topic is None and isinstance(ctx.config.merged, dict):
        topic = ctx.config.merged.get("topic")
    if not topic:
        return "介绍Akamai推理云优势"  # 默认主题
    return str(topic).strip()


def visual_style_detail(ctx: RunContext, style_key: str) -> Dict[str, Any]:
    visual_styles = ctx.config.base_config.get("visual_styles", {}) if isinstance(ctx.config.base_config, dict) else {}
    return visual_styles.get(style_key, {})


__all__ = [
    "resolve_style_key",
    "resolve_resolution",
    "resolve_shot_count",
    "resolve_topic",
    "visual_style_detail",
]
