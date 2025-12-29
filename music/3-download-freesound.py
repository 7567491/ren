#!/usr/bin/env python3
"""
Freesound 音乐下载脚本（合并版）

支持普通风格搜索与快节奏（BPM过滤）模式，输出到 resource/songs。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Sequence

import requests
from dotenv import load_dotenv

load_dotenv()

FREESOUND_API_URL = "https://freesound.org/apiv2"

# 风格关键词（来源于原 download-music.py）
STYLE_KEYWORDS: Dict[str, List[str]] = {
    "technology": ["electronic corporate", "tech background", "futuristic ambient", "digital soundscape"],
    "xianxia": ["chinese traditional", "oriental instrumental", "asian flute", "guzheng"],
    "cyberpunk": ["cyberpunk synthwave", "dark electronic", "dystopian", "neon synth"],
    "anime": ["anime background", "japanese instrumental", "upbeat game", "cheerful"],
    "realistic_3d": ["cinematic orchestral", "epic trailer", "dramatic film", "heroic orchestral"],
    "ink_painting": ["zen meditation", "peaceful traditional", "calm ambient", "nature sounds"],
    "steampunk": ["steampunk industrial", "victorian orchestral", "mechanical", "brass band"],
    "space_scifi": ["space ambient", "sci-fi soundtrack", "cosmic atmosphere", "deep space"],
    "fantasy_magic": ["fantasy orchestral", "magical mystical", "medieval adventure", "epic fantasy"],
    "cinematic": ["cinematic epic", "movie trailer", "orchestral dramatic", "emotional film"],
}

# 快节奏/史诗向关键词（来源于原 download-epic-music.py）
EPIC_TECH_KEYWORDS: List[str] = [
    "epic battle",
    "intense action",
    "cinematic trailer",
    "aggressive orchestral",
    "powerful dramatic",
    "electronic epic",
    "cyberpunk action",
    "futuristic tech",
    "digital energy",
    "synth powerful",
    "energetic sport",
    "workout motivation",
    "running fitness",
    "athletic powerful",
    "gym training music",
    "fast paced",
    "high energy",
    "upbeat dynamic",
    "adrenaline rush",
    "intense rhythm",
    "edm intense",
    "dubstep powerful",
    "drum and bass",
    "electro energetic",
    "techno driving",
    "rock intense",
    "metal aggressive",
    "hard rock energy",
    "hybrid epic",
    "modern cinematic",
    "aggressive beat",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freesound 免费音乐下载（合并版）")
    parser.add_argument("--style", choices=sorted(STYLE_KEYWORDS.keys()), default="realistic_3d",
                        help="风格关键词（普通模式）")
    parser.add_argument("--count", type=int, default=15, help="下载数量")
    parser.add_argument("--bpm-min", type=int, default=None,
                        help="最低BPM，设置后启用快节奏过滤（默认普通模式不限制）")
    parser.add_argument("--mode", choices=["normal", "epic"], default="normal",
                        help="normal 使用 style 关键词；epic 使用强化快节奏关键词")
    parser.add_argument("--api-key", help="Freesound API Key（默认读取环境变量 FREESOUND_API_KEY）")
    parser.add_argument("--output", default="./resource/songs", help="输出目录")
    return parser.parse_args()


def build_queries(args: argparse.Namespace) -> Sequence[str]:
    if args.mode == "epic":
        return EPIC_TECH_KEYWORDS
    return STYLE_KEYWORDS.get(args.style, ["background music", "instrumental"])


def ensure_api_key(args: argparse.Namespace) -> str:
    key = args.api_key or os.getenv("FREESOUND_API_KEY")
    if not key or key == "your_api_key_here":
        print("❌ 未找到有效的 FREESOUND_API_KEY，请在环境变量或参数中提供")
        sys.exit(1)
    return key


def download_with_queries(queries: Sequence[str], api_key: str, output_dir: Path, count: int, bpm_min: int | None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    attempted_ids = set()

    print(f"🔑 使用 API Key: {api_key[:6]}***")
    print(f"📁 输出目录: {output_dir.resolve()}")
    print(f"🎯 目标数量: {count}")
    if bpm_min:
        print(f"⚡ BPM过滤: ≥ {bpm_min}")

    for keyword in queries:
        if downloaded >= count:
            break

        print(f"\n🔍 搜索: {keyword}")
        params = {
            "query": keyword,
            "filter": "duration:[60 TO 300] type:(mp3 OR wav)",
            "sort": "rating_desc",
            "fields": "id,name,duration,previews,username,license,tags,ac_analysis",
            "page_size": 15,
            "token": api_key,
        }

        try:
            resp = requests.get(f"{FREESOUND_API_URL}/search/text/", params=params, timeout=30)
            if resp.status_code == 401:
                print("❌ API Key 无效或权限不足")
                break
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            print(f"❌ 搜索失败: {exc}")
            continue

        results = data.get("results") or []
        if not results:
            print("⚠️ 未找到结果")
            continue

        for sound in results:
            if downloaded >= count:
                break

            sound_id = sound.get("id")
            if sound_id in attempted_ids:
                continue
            attempted_ids.add(sound_id)

            name = sound.get("name", "audio")
            duration = sound.get("duration", 0)
            username = sound.get("username", "unknown")
            license_name = sound.get("license", "")
            preview_url = sound.get("previews", {}).get("preview-hq-mp3")

            ac_analysis = sound.get("ac_analysis") or {}
            bpm = ac_analysis.get("bpm") if isinstance(ac_analysis, dict) else None
            if bpm_min and bpm is not None and bpm < bpm_min:
                continue

            if not preview_url:
                continue

            safe_name = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in name).strip()
            safe_name = safe_name[:60] or "audio"
            bpm_suffix = f"_{int(bpm)}bpm" if bpm else ""
            filename = f"{keyword.replace(' ', '_')[:20]}_{downloaded+1:02d}{bpm_suffix}_{safe_name}.mp3"
            file_path = output_dir / filename

            if file_path.exists():
                print(f"⏭️  已存在: {filename}")
                downloaded += 1
                continue

            print(f"⬇️  [{downloaded+1}/{count}] {name[:40]} | 时长 {duration:.1f}s | 作者 {username} | 许可 {license_name}")
            try:
                audio_resp = requests.get(preview_url, timeout=30)
                audio_resp.raise_for_status()
                with open(file_path, "wb") as f:
                    f.write(audio_resp.content)
                downloaded += 1
                time.sleep(1)
            except Exception as exc:  # noqa: BLE001
                print(f"❌ 下载失败: {exc}")
                file_path.unlink(missing_ok=True)

    print(f"\n✅ 完成下载 {downloaded}/{count} 首")


def main() -> None:
    args = parse_args()
    api_key = ensure_api_key(args)
    queries = build_queries(args)
    output_dir = Path(args.output)
    download_with_queries(queries, api_key, output_dir, args.count, args.bpm_min)


if __name__ == "__main__":
    main()
