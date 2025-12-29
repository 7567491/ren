#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""视频生成步骤。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ..context import RunContext
from .common import resolve_resolution


async def run(ctx: RunContext, output_dir: Path) -> List[Path]:
    prompts = ctx.state.get("steps", {}).get("shots", {}).get("prompts") or []
    if not prompts:
        ctx.logger.warning("无分镜提示，跳过视频生成")
        return []

    resolution = ctx.state.get("steps", {}).get("shots", {}).get("resolution") or resolve_resolution(ctx)
    references = ctx.assets.get("images_urls") or ctx.state.get("steps", {}).get("images", {}).get("urls") or []
    client = ctx.clients.get("media")
    results: List[Dict] = await client.generate_videos(prompts, output_dir, references=references, resolution=resolution) if client else []
    videos = [item.get("path") for item in results if item.get("path")]
    urls = [item.get("url") for item in results if item.get("url")]

    ctx.state.setdefault("steps", {})["videos"] = {
        "files": [str(p) for p in videos],
        "urls": urls,
        "resolution": resolution,
    }
    ctx.assets["videos"] = videos
    if urls:
        ctx.assets["videos_urls"] = urls

    ctx.logger.info(f"视频生成完成（{len(videos)} 段）")
    return videos
