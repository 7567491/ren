#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""脚本生成步骤。"""

from __future__ import annotations

from typing import Any

from ..context import RunContext
from .common import resolve_shot_count, resolve_style_key, resolve_topic, visual_style_detail


def _build_prompt(ctx: RunContext, topic: str, shot_count: int, style_key: str) -> str:
    prompt_templates = ctx.config.merged.get("prompt_templates", {}) if isinstance(ctx.config.merged, dict) else {}
    style_cfg = visual_style_detail(ctx, style_key)
    style_name = style_cfg.get("name", style_key)
    palette = style_cfg.get("color_palette", "")
    colors = [c.strip() for c in palette.split(",") if c.strip()]
    primary_1 = colors[0] if colors else "blue"
    primary_2 = colors[1] if len(colors) > 1 else (colors[0] if colors else "purple")
    mood = style_cfg.get("mood", "")

    outline_tpl = prompt_templates.get("story_outline")
    if outline_tpl:
        return outline_tpl.format(
            topic=topic,
            shot_count=shot_count,
            style_name=style_name,
            visual_style=style_cfg.get("visual_style", ""),
            color_palette=palette,
            primary_color_1=primary_1,
            primary_color_2=primary_2,
            mood=mood,
        )

    return (
        f"请围绕主题“{topic}”生成一个包含{shot_count}个镜头的广告脚本，"
        f"风格参考：{style_name}，给出旁白文案和每个镜头概要。"
    )


async def run(ctx: RunContext) -> None:
    topic = resolve_topic(ctx)
    shot_count = resolve_shot_count(ctx)
    style_key = resolve_style_key(ctx)
    prompt = _build_prompt(ctx, topic, shot_count, style_key)

    llm = ctx.clients.get("llm")
    text = await llm.generate(prompt) if llm else "脚本文本占位"
    ctx.state.setdefault("steps", {})["script"] = {
        "text": text,
        "topic": topic,
        "shot_count": shot_count,
        "style": style_key,
    }
    ctx.logger.info("脚本生成完成")
