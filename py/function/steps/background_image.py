#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""背景图生成步骤。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..context import RunContext
from .common import resolve_style_key, visual_style_detail


def _build_background_prompt(ctx: RunContext, base_prompt: str) -> str:
    script_state = ctx.state.get("steps", {}).get("script", {})
    topic = script_state.get("topic") or script_state.get("story_theme") or "品牌故事"
    shots_state = ctx.state.get("steps", {}).get("shots", {})
    style_key = shots_state.get("style") or script_state.get("style") or resolve_style_key(ctx)
    style_cfg = visual_style_detail(ctx, style_key)

    style_name = style_cfg.get("name", style_key)
    visual_style = style_cfg.get("visual_style", "")
    palette = style_cfg.get("color_palette", "")

    parts = [
        f"Establish a hero background for \"{topic}\"",
        f"style: {style_name}",
    ]
    if visual_style:
        parts.append(visual_style)
    if palette:
        parts.append(f"color palette: {palette}")
    parts.extend(
        [
            "focus on environment, architecture, lighting and atmosphere consistency",
            "wide shot, no people, props or logos, only scenery layers",
            f"inspiration source: {base_prompt}",
        ]
    )
    return " | ".join(part for part in parts if part).strip()


async def run(ctx: RunContext, output_dir: Path) -> Optional[Path]:
    shots_state = ctx.state.get("steps", {}).get("shots", {})
    prompts = shots_state.get("prompts") or []
    if not prompts:
        ctx.logger.warning("无分镜提示，跳过背景图生成")
        return None

    client = ctx.clients.get("media")
    if not client:
        ctx.logger.warning("缺少媒体客户端，无法生成背景图")
        return None

    background_prompt = _build_background_prompt(ctx, prompts[0])
    results = await client.generate_images([background_prompt], output_dir)
    if not results:
        ctx.logger.warning("背景图生成失败，未返回图像")
        return None

    first = results[0]
    path = first.get("path")
    url = first.get("url")
    if not path:
        ctx.logger.warning("背景图生成结果缺少文件路径")
        return None

    ctx.state.setdefault("steps", {})["background_image"] = {
        "file": str(path),
        "url": url,
        "prompt": background_prompt,
    }
    ctx.assets["background_image"] = path
    if url:
        ctx.assets["background_image_url"] = url

    ctx.logger.info(f"背景图生成完成: {path.name}")
    return path


__all__ = ["run"]
