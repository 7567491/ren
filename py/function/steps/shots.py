#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分镜拆分步骤。"""

from __future__ import annotations

import json

from ..context import RunContext
from .common import resolve_resolution, resolve_shot_count, resolve_style_key, visual_style_detail


async def run(ctx: RunContext, shots: int | None = None) -> None:
    script_state = ctx.state.get("steps", {}).get("script", {})
    base_text = script_state.get("text", "")
    style_key = script_state.get("style") or resolve_style_key(ctx)
    style_cfg = visual_style_detail(ctx, style_key)
    total = resolve_shot_count(ctx, shots)
    resolution = resolve_resolution(ctx)

    prompts = []
    segments = []
    cleaned = base_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").replace("json", "", 1).strip()
    try:
        parsed = json.loads(cleaned)
        breakdown = parsed.get("shot_breakdown") or []
        for item in breakdown:
            if isinstance(item, dict):
                segments.append(item.get("scene_summary") or item.get("key_action") or "")
    except Exception:  # noqa: BLE001
        segments = []

    for i in range(total):
        base_segment = segments[i] if i < len(segments) else cleaned
        segment_hint = base_segment.split("\n")[0]
        prompt = (
            f"Shot {i+1} | style: {style_cfg.get('name', style_key)} | "
            f"visual tone: {style_cfg.get('visual_style', '')} | {segment_hint.strip() or '请生成画面'}"
        )
        prompts.append(prompt)

    ctx.state.setdefault("steps", {})["shots"] = {
        "prompts": prompts,
        "style": style_key,
        "resolution": resolution,
    }
    ctx.assets["shots_meta"] = {"style": style_key, "resolution": resolution}
    ctx.logger.info(f"分镜生成完成（{len(prompts)} 个镜头）")
