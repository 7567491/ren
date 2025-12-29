#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字幕生成步骤。"""

from __future__ import annotations

from pathlib import Path

from ..context import RunContext


async def run(ctx: RunContext, voice_path: Path, output: Path) -> Path:
    text = ctx.state.get("steps", {}).get("script", {}).get("text", "字幕占位")
    client = ctx.clients.get("subtitle")
    voice_info = ctx.assets.get("voice_info", {}) if isinstance(ctx.assets, dict) else {}
    sub_maker = voice_info.get("sub_maker")
    duration = voice_info.get("duration") or ctx.state.get("steps", {}).get("voice", {}).get("duration")

    subtitle_path = await client.create_subtitle(voice_path, output, text, sub_maker=sub_maker, duration=duration) if client else output
    if subtitle_path:
        ctx.state.setdefault("steps", {})["subtitle"] = {"file": str(subtitle_path)}
        ctx.assets["subtitle"] = subtitle_path
        ctx.logger.info("字幕生成完成")
    else:
        ctx.logger.warning("字幕生成失败或已跳过")
    return subtitle_path
