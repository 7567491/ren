#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workflow API：统一供 CLI/未来 HTTP 使用。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from py.function.config_loader import LoadedConfig, load_config
from py.function.context import RunContext, _gen_session_id
from py.function.pipeline import run_all
from py.function.storage import check_config_hash, ensure_workdir, init_state, load_state, save_state


@dataclass
class Workflow:
    config: LoadedConfig
    ctx: RunContext

    @classmethod
    async def create(cls, args: Any) -> "Workflow":
        config = load_config()
        session_id = args.resume or _gen_session_id()
        output_base = Path(config.merged.get("workflow", {}).get("output_base", "./output"))

        ctx = RunContext(config=config, session_id=session_id, work_dir=output_base, options=vars(args), dry_run=getattr(args, "dry_run", False))
        ctx.init_paths(output_base=output_base)

        work_dir = ensure_workdir(output_base, session_id)
        saved_state = load_state(work_dir)

        if saved_state and not getattr(args, "no_auto_resume", False):
            hash_ok = check_config_hash(saved_state, config)
            if not hash_ok and not getattr(args, "resume_ignore_config", False):
                ctx.logger.warning("配置已变更，与存档不一致，已创建新会话。使用 --resume-ignore-config 可强制恢复。")
                ctx.state = init_state(config, session_id)
                save_state(work_dir, ctx.state)
            else:
                if not hash_ok:
                    ctx.logger.warning("配置已变更，但已按指示强制恢复。")
                ctx.state = saved_state
                ctx.assets = saved_state.get("assets", {}) if isinstance(saved_state.get("assets"), dict) else {}
                ctx.logger.info("检测到历史状态，自动恢复")
        else:
            ctx.state = init_state(config, session_id)
            save_state(work_dir, ctx.state)

        return cls(config=config, ctx=ctx)

    async def run_all(self) -> RunContext:
        self.ctx = await run_all(self.ctx)
        save_state(self.ctx.work_dir, self.ctx.state)
        return self.ctx

    async def run_script(self) -> RunContext:
        from py.function.pipeline import run_step

        await run_step(self.ctx, "script")
        return self.ctx

    async def run_shots(self) -> RunContext:
        from py.function.pipeline import run_step

        await run_step(self.ctx, "shots")
        return self.ctx

    async def run_images(self) -> RunContext:
        from py.function.pipeline import run_step

        await run_step(self.ctx, "images")
        return self.ctx

    async def run_videos(self) -> RunContext:
        from py.function.pipeline import run_step

        await run_step(self.ctx, "videos")
        return self.ctx

    async def run_voice(self) -> RunContext:
        from py.function.pipeline import run_step

        await run_step(self.ctx, "voice")
        return self.ctx

    async def run_subtitle(self) -> RunContext:
        from py.function.pipeline import run_step

        await run_step(self.ctx, "subtitle")
        return self.ctx

    async def run_music(self) -> RunContext:
        from py.function.pipeline import run_step

        await run_step(self.ctx, "music")
        return self.ctx

    async def run_compose(self) -> RunContext:
        from py.function.pipeline import run_step

        await run_step(self.ctx, "compose")
        return self.ctx


__all__ = ["Workflow"]
