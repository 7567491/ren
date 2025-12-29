#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成步骤。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..context import RunContext


async def run(ctx: RunContext, videos: List[Path], voice: Optional[Path], music: Optional[Path], subtitle: Optional[Path], output: Path) -> Path:
    client = ctx.clients.get("composer")
    result = await client.compose(videos, voice, music, subtitle, output) if client else output
    ctx.state.setdefault("steps", {})["compose"] = {"file": str(result)}
    ctx.assets["final_video"] = result
    ctx.logger.info(f"合成完成: {result}")
    return result
