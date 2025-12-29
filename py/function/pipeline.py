#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""流程编排。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .context import RunContext
from .llm_client import LLMClient
from .media_clients import ComposerClient, MediaGenClient, MusicClient, SubtitleClient, VoiceClient
from .storage import save_state
from .steps import compose, images, music, script, shots, subtitle, videos, voice


def _prepare_clients(ctx: RunContext) -> None:
    dry_run = getattr(ctx, "dry_run", False)
    ctx.clients["llm"] = LLMClient(ctx.config, ctx.logger, provider_choice=ctx.options.get("provider"), dry_run=dry_run)
    ctx.clients["media"] = MediaGenClient(ctx.config, ctx.logger, dry_run=dry_run)
    ctx.clients["voice"] = VoiceClient(ctx.config, ctx.logger, dry_run=dry_run)
    ctx.clients["subtitle"] = SubtitleClient(ctx.config, ctx.logger, dry_run=dry_run)
    ctx.clients["music"] = MusicClient(ctx.config, ctx.logger, dry_run=dry_run)
    ctx.clients["composer"] = ComposerClient(ctx.config, ctx.logger, dry_run=dry_run)


def _step_done(ctx: RunContext, name: str) -> bool:
    return name in ctx.state.get("steps", {})


def _paths(ctx: RunContext) -> dict:
    work_dir = ctx.work_dir
    return {
        "images_dir": work_dir / "images",
        "videos_dir": work_dir / "videos",
        "voice_path": work_dir / "voice.wav",
        "subtitle_path": work_dir / "subtitle.vtt",
        "music_path": work_dir / "music.mp3",
        "final_video": work_dir / "final_video.mp4",
        "music_dir": ctx.config.project_root / "resource" / "songs",
    }


async def run_step(ctx: RunContext, name: str) -> None:
    _prepare_clients(ctx)
    paths = _paths(ctx)

    if name == "script":
        await script.run(ctx)
    elif name == "shots":
        await shots.run(ctx, shots=ctx.options.get("shots"))
    elif name == "images":
        await images.run(ctx, paths["images_dir"])
    elif name == "videos":
        await videos.run(ctx, paths["videos_dir"])
    elif name == "voice":
        await voice.run(ctx, paths["voice_path"])
    elif name == "subtitle":
        await subtitle.run(ctx, paths["voice_path"], paths["subtitle_path"])
    elif name == "music":
        await music.run(ctx, paths["music_dir"], paths["music_path"])
    elif name == "compose":
        videos_list = ctx.assets.get("videos") or []
        await compose.run(
            ctx,
            videos_list,
            ctx.assets.get("voice"),
            ctx.assets.get("music"),
            ctx.assets.get("subtitle"),
            paths["final_video"],
        )
    else:
        raise ValueError(f"未知步骤: {name}")

    save_state(ctx.work_dir, ctx.state)


async def run_all(ctx: RunContext) -> RunContext:
    step_order = ["script", "shots", "images", "videos", "voice", "subtitle", "music", "compose"]

    for name in step_order:
        if _step_done(ctx, name):
            # 将已有路径回填 assets
            current = ctx.state.get("steps", {}).get(name, {})
            if "files" in current:
                ctx.assets[name] = [Path(p) for p in current.get("files", [])]
            if "file" in current:
                ctx.assets[name] = Path(current.get("file"))
            if "urls" in current:
                ctx.assets[f"{name}_urls"] = current.get("urls")
            if name == "voice" and "duration" in current:
                ctx.assets["voice_info"] = {"sub_maker": None, "duration": current.get("duration")}
            continue

        await run_step(ctx, name)

    return ctx


__all__ = ["run_all", "run_step"]
