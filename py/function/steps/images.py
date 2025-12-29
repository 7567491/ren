#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图像生成步骤。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ..context import RunContext


async def run(ctx: RunContext, output_dir: Path) -> List[Path]:
    prompts = ctx.state.get("steps", {}).get("shots", {}).get("prompts") or []
    if not prompts:
        ctx.logger.warning("无分镜提示，跳过图像生成")
        return []

    client = ctx.clients.get("media")
    results: List[Dict] = await client.generate_images(prompts, output_dir) if client else []
    images = [item.get("path") for item in results if item.get("path")]
    urls = [item.get("url") for item in results if item.get("url")]

    ctx.state.setdefault("steps", {})["images"] = {
        "files": [str(p) for p in images],
        "urls": urls,
    }
    ctx.assets["images"] = images
    if urls:
        ctx.assets["images_urls"] = urls

    ctx.logger.info(f"图像生成完成（{len(images)} 张）")
    return images
