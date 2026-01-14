#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WaveSpeed / MiniMax 连通性测试脚本。

用法：
    python3 py/test_network.py --digital-human

脚本会：
1. 加载 .env，读取 `WAVESPEED_API_KEY`、`MINIMAX_API_KEY`（可复用同一 Key）；
2. 串行执行“头像 → 语音 → 唇同步”三个阶段，生成 1 段 6-8 秒左右的数字人视频；
3. 将资产保存到 `output/test-network/<job_id>/`，并输出成本/状态摘要，便于排错。

由于会真实调用付费 API，请在调试/联调前确认账号余额，并保持 `speech_text` 足够短。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from py.exceptions import ExternalAPIError
from py.services.digital_human_service import DigitalHumanService
from py.services.storage_service import StorageService
from py.services.task_manager import TaskManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="WaveSpeed API 连通性检测脚本",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--digital-human",
        action="store_true",
        help="运行数字人三阶段真实冒烟（头像→语音→唇同步）",
    )
    parser.add_argument(
        "--avatar-mode",
        choices=("prompt", "upload"),
        default="prompt",
        help="头像阶段模式：prompt 会调用 Seedream，upload 可复用本地图片",
    )
    parser.add_argument(
        "--avatar-prompt",
        default="25岁职业女性，职业装，微笑，自信，正面半身照，白色背景",
        help="头像提示词（prompt 模式下必填）",
    )
    parser.add_argument(
        "--avatar-upload",
        type=str,
        help="可选：已有头像文件路径，将跳过 Seedream 直接上传",
    )
    parser.add_argument(
        "--speech-text",
        default="大家好，这是一条 WaveSpeed 数字人测试语音，用于连通性验证。",
        help="语音阶段要朗读的文本，建议 8-10 秒以内控制成本",
    )
    parser.add_argument("--voice-id", default="Wise_Woman", help="MiniMax 音色 ID")
    parser.add_argument("--resolution", default="720p", help="数字人视频分辨率")
    parser.add_argument("--seed", type=int, default=42, help="随机种子（影响唇形随机性）")
    parser.add_argument(
        "--output-dir",
        default="output/test-network",
        help="测试任务的输出目录（不会污染正式任务）",
    )
    parser.add_argument(
        "--temp-dir",
        default="temp/test-network",
        help="TaskManager 持久化 jobs.json 的目录",
    )
    parser.add_argument(
        "--public-url",
        help="可选：覆盖发布用的 Public Base URL（默认为 STORAGE_BUCKET_URL）",
    )
    parser.add_argument(
        "--public-export-dir",
        help="可选：覆盖挂载目录（默认读取 DIGITAL_HUMAN_PUBLIC_EXPORT_DIR）",
    )
    parser.add_argument(
        "--namespace",
        default=os.getenv("DIGITAL_HUMAN_PUBLIC_NAMESPACE", "ren"),
        help="发布时使用的命名空间",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出最终结果，便于脚本解析",
    )
    return parser.parse_args()


async def run_digital_human(args: argparse.Namespace) -> Dict[str, Any]:
    """执行数字人三阶段冒烟。"""
    load_dotenv()

    wavespeed_key = os.getenv("WAVESPEED_API_KEY")
    minimax_key = os.getenv("MINIMAX_API_KEY") or wavespeed_key
    if not wavespeed_key:
        raise RuntimeError("缺少 WAVESPEED_API_KEY，请在 .env 中配置")
    if not minimax_key:
        raise RuntimeError("缺少 MINIMAX_API_KEY 或 WAVESPEED_API_KEY")

    output_dir = Path(args.output_dir).expanduser()
    temp_dir = Path(args.temp_dir).expanduser()
    temp_dir.mkdir(parents=True, exist_ok=True)

    storage = StorageService(
        output_root=output_dir,
        public_base_url=args.public_url
        or os.getenv("DIGITAL_HUMAN_PUBLIC_BASE_URL")
        or os.getenv("STORAGE_BUCKET_URL"),
        public_export_dir=args.public_export_dir
        or os.getenv("DIGITAL_HUMAN_PUBLIC_EXPORT_DIR"),
        namespace=args.namespace,
    )
    task_manager = TaskManager(storage_dir=str(temp_dir))
    service = DigitalHumanService(
        wavespeed_key=wavespeed_key,
        minimax_key=minimax_key,
        storage_service=storage,
        task_manager=task_manager,
    )

    avatar_mode = args.avatar_mode
    avatar_upload = args.avatar_upload
    avatar_path: Optional[Path] = None
    if avatar_upload:
        avatar_path = Path(avatar_upload).expanduser()
        if not avatar_path.exists():
            raise FileNotFoundError(f"头像文件不存在: {avatar_path}")
        avatar_mode = "upload"
    elif avatar_mode == "upload":
        raise RuntimeError("avatar_mode=upload 时必须提供 --avatar-upload 文件路径")

    job_id = f"aka-test-{datetime.utcnow().strftime('%m%d%H%M%S')}"
    print(f"🚀 开始数字人冒烟任务: {job_id}")
    print(f"   - 头像模式: {avatar_mode}")
    print(f"   - 分辨率: {args.resolution}")
    print(f"   - 文案长度: {len(args.speech_text)} 字")

    record = await service.generate_digital_human(
        job_id=job_id,
        avatar_mode=avatar_mode,
        avatar_prompt=args.avatar_prompt if avatar_mode == "prompt" else None,
        avatar_upload_path=str(avatar_path) if avatar_path else None,
        speech_text=args.speech_text,
        voice_id=args.voice_id,
        resolution=args.resolution,
        speed=1.0,
        pitch=0,
        emotion="neutral",
        seed=args.seed,
        mask_image=None,
    )
    return record


def _print_summary(record: Dict[str, Any]) -> None:
    """控制台输出结果摘要。"""
    print("\n✅ 数字人冒烟完成")
    print(f"任务 ID: {record.get('job_id')}")
    print(f"最终状态: {record.get('status')}")
    duration = record.get("duration")
    if isinstance(duration, (int, float)):
        print(f"视频时长: {duration:.1f}s")
    print(f"成本 (估算): ${record.get('cost', 0):.4f}")

    assets = record.get("assets") or {}
    print("资产链接：")
    for key in ("avatar_url", "audio_url", "video_url"):
        value = assets.get(key) or record.get(key)
        if value:
            print(f"  - {key}: {value}")

    print("阶段状态：")
    for name, state in (record.get("stages") or {}).items():
        print(f"  - {name:<6s}: {state.get('state')} | {state.get('message')}")


def main() -> int:
    args = parse_args()
    if not args.digital_human:
        print("请指定 --digital-human 运行数字人连通性检查")
        return 1

    try:
        record = asyncio.run(run_digital_human(args))
    except ExternalAPIError as exc:
        print(f"❌ API 调用失败: {exc}")
        return 2
    except KeyboardInterrupt:
        print("\n⚠️ 已取消")
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 发生未知错误: {exc}")
        return 3

    if args.json:
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        _print_summary(record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
