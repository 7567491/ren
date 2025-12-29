#!/usr/bin/env python3
"""
Incompetech 免费音乐一键下载（合并版）

整合原有 quick/补充/直链脚本，提供统一的曲库与并发下载。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import time
from pathlib import Path
from typing import Iterable, List, Tuple

import requests


DOWNLOAD_DIR = Path("./resource/songs")

# 经过验证的曲目列表（覆盖电影/电子/悬疑/爵士等多种风格）
TRACKS: List[Tuple[str, str]] = [
    ("Epic_Decisions", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Decisions.mp3"),
    ("Heroic_Intrepid", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Intrepid.mp3"),
    ("Majestic_Sovereign", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Sovereign.mp3"),
    ("Suspense_Killers", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Killers.mp3"),
    ("Action_Hitman", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Hitman.mp3"),
    ("Electronic_Cipher", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Cipher.mp3"),
    ("Tech_Reformat", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Reformat.mp3"),
    ("Mystery_Deliberate_Thought", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Deliberate_Thought.mp3"),
    ("Dark_Danse_Macabre", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Danse_Macabre.mp3"),
    ("Conflict_Chase", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Chase.mp3"),
    ("Drama_Crisis", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Crisis.mp3"),
    ("Sad_Heart_of_Nowhere", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Heart_of_Nowhere.mp3"),
    ("Revenge_Devastation_and_Revenge", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Devastation_and_Revenge.mp3"),
    ("Uneasy_Disquiet", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Disquiet.mp3"),
    ("Rhythmic_Movement_Proposition", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Movement_Proposition.mp3"),
    ("Ambient_Backed_Vibes", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Backed_Vibes.mp3"),
    ("Mystery_Black_Vortex", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Black_Vortex.mp3"),
    ("Action_Fearless_First", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Fearless_First.mp3"),
    ("Epic_Five_Armies", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Five_Armies.mp3"),
    ("Dramatic_Impact_Moderato", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Impact_Moderato.mp3"),
    ("Suspense_Long_Note_Four", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Long_Note_Four.mp3"),
    ("Cinematic_Lomi", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Ломи.mp3"),
    ("Electronic_Pixelland", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Pixelland.mp3"),
    ("Upbeat_Fluffing_a_Duck", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Fluffing_a_Duck.mp3"),
    ("Jazz_Bossa_Antigua", "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Bossa_Antigua.mp3"),
]


def unique_tracks(tracks: Iterable[Tuple[str, str]]) -> List[Tuple[str, str]]:
    seen = set()
    unique: List[Tuple[str, str]] = []
    for title, url in tracks:
        if url in seen:
            continue
        seen.add(url)
        unique.append((title, url))
    return unique


def sanitize_filename(title: str) -> str:
    safe = "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in title)
    safe = "_".join(part for part in safe.split() if part)
    return safe or "track"


def download_one(item: Tuple[str, str]) -> str:
    title, url = item
    filename = f"{sanitize_filename(title)}.mp3"
    output_file = DOWNLOAD_DIR / filename

    if output_file.exists():
        return f"⏭️  已存在: {filename}"

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()

        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = output_file.stat().st_size / 1024 / 1024
        if size_mb < 0.01:
            output_file.unlink(missing_ok=True)
            return f"❌ 失败: {filename} (文件过小)"
        return f"✅ {filename} ({size_mb:.1f}MB)"

    except Exception as exc:  # noqa: BLE001
        output_file.unlink(missing_ok=True)
        return f"❌ {filename}: {str(exc)[:40]}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Incompetech 免费音乐下载（合并版）")
    parser.add_argument("--count", "-c", type=int, default=15, help="下载数量（最多25）")
    parser.add_argument("--filter", "-f", help="按标题关键字过滤，如 cinematic/electronic")
    parser.add_argument("--workers", "-w", type=int, default=5, help="并发线程数")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    all_tracks = unique_tracks(TRACKS)

    selected = all_tracks
    if args.filter:
        keyword = args.filter.lower()
        selected = [(t, u) for t, u in all_tracks if keyword in t.lower()]

    if args.count > 0:
        selected = selected[: args.count]

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🎵 Incompetech 免费音乐下载（合并版）")
    print("=" * 60)
    print(f"📋 准备下载: {len(selected)} 首")
    print(f"📁 保存目录: {DOWNLOAD_DIR.absolute()}\n")

    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = list(executor.map(download_one, selected))

    elapsed = time.time() - start_time
    success = sum(1 for r in results if r.startswith("✅"))
    skipped = sum(1 for r in results if r.startswith("⏭️"))
    failed = sum(1 for r in results if r.startswith("❌"))

    for result in results:
        print(result)

    print("\n" + "=" * 60)
    print(f"✅ 成功: {success} | ⏭️ 跳过: {skipped} | ❌ 失败: {failed}")
    print(f"⏱️  用时: {elapsed:.1f}秒")
    print("\n⚠️  许可证: CC BY 3.0 - Kevin MacLeod (incompetech.com)")


if __name__ == "__main__":
    main()
