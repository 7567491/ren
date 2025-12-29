#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配乐选择与处理步骤。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..context import RunContext
from .common import resolve_style_key


async def run(ctx: RunContext, music_dir: Path, output: Path) -> Optional[Path]:
    client = ctx.clients.get("music")
    style = ctx.state.get("steps", {}).get("shots", {}).get("style") or resolve_style_key(ctx)
    music_path = await client.pick_music(music_dir, output, style=style) if client else None
    if music_path:
        ctx.state.setdefault("steps", {})["music"] = {"file": str(music_path)}
        ctx.assets["music"] = music_path
        ctx.logger.info("配乐准备完成")
    else:
        ctx.logger.info("未选择配乐，跳过")
    return music_path
