#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行解析与入口。"""

from __future__ import annotations

import argparse
import asyncio

from py.api.workflow import Workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Akamai AI 广告生成（异步重构版）")
    parser.add_argument("--resume", help="指定 session_id 继续任务")
    parser.add_argument("--no-auto-resume", action="store_true", help="禁用自动恢复")
    parser.add_argument("--resume-ignore-config", action="store_true", help="配置变更时强制继续恢复")
    parser.add_argument("--shots", type=int, help="镜头数量")
    parser.add_argument("--style", help="视觉风格")
    parser.add_argument("--resolution", help="分辨率")
    parser.add_argument("--dry-run", action="store_true", help="仅跑占位流程，不调用外部接口")
    return parser


async def main_async() -> None:
    parser = build_parser()
    args = parser.parse_args()

    workflow = await Workflow.create(args)
    ctx = workflow.ctx
    ctx.logger.info(f"Session: {ctx.session_id}")
    ctx.logger.info(f"输出目录: {ctx.work_dir}")

    ctx = await workflow.run_all()
    final = ctx.assets.get("final_video")
    if final:
        ctx.logger.info(f"最终输出: {final}")


def main() -> None:
    asyncio.run(main_async())


__all__ = ["main", "main_async", "build_parser"]
