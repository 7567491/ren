#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""旁白生成步骤。"""

from __future__ import annotations

from pathlib import Path

from ..context import RunContext


async def run(ctx: RunContext, output: Path) -> Path:
    script_text = ctx.state.get("steps", {}).get("script", {}).get("text", "旁白占位")
    client = ctx.clients.get("voice")
    voice_path: Path = output
    sub_maker = None
    duration = 0.0

    if client:
        voice_path, sub_maker, duration = await client.synthesize(script_text, output)

    ctx.state.setdefault("steps", {})["voice"] = {"file": str(voice_path), "duration": duration}
    ctx.assets["voice"] = voice_path
    ctx.assets["voice_info"] = {"sub_maker": sub_maker, "duration": duration}
    ctx.logger.info("旁白生成完成")
    return voice_path
