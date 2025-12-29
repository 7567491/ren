#!/usr/bin/env python3
"""Download 60 background images (6 per visual style) to resource/background.

Styles come from config.yaml visual_styles (10 entries). Uses Pexels API via
pexels_api_key in .env. Downloads large/original resolution landscape images.

Usage:
    python3 pic/download_backgrounds.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

import requests


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
OUTPUT_ROOT = ROOT_DIR / "resource" / "background"


STYLES: Dict[str, str] = {
    "cartoon_adventure": "cartoon adventure colorful landscape background",
    "luxury_fashion": "luxury fashion abstract background glossy premium",
    "ink_xianxia": "chinese ink wash landscape wuxia background",
    "realistic_3d": "photorealistic 3d studio background",
    "cinematic": "cinematic film look dramatic landscape background",
    "technology": "futuristic technology hologram data background",
    "cyberpunk": "cyberpunk neon cityscape background",
    "space_exploration": "space nebula cosmic background",
    "outdoor_adventure": "outdoor adventure mountain landscape background",
    "magical_fantasy": "fantasy castle magical forest background",
}


def load_env(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        values[key.strip()] = val.strip()
    return values


def select_image_url(photo: Dict) -> str:
    src = photo.get("src") or {}
    return src.get("original") or src.get("large2x") or src.get("large")


def search_style(style_key: str, query: str, api_key: str, session: requests.Session, per_page: int = 6) -> List[str]:
    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": per_page, "orientation": "landscape"}
    api_url = "https://api.pexels.com/v1/search"
    response = session.get(api_url, headers=headers, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()
    photos: List[Dict] = data.get("photos") or []
    if not photos:
        raise RuntimeError(f"No photos returned for style {style_key}")
    urls: List[str] = []
    for photo in photos[:per_page]:
        url = select_image_url(photo)
        if url:
            urls.append(url)
    if len(urls) < per_page:
        raise RuntimeError(f"Insufficient images for {style_key}: {len(urls)}/{per_page}")
    return urls


def download(url: str, path: Path, session: requests.Session, timeout: int = 90) -> None:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)


def main() -> int:
    env = load_env(ENV_PATH)
    api_key = env.get("pexels_api_key")
    if not api_key:
        print("❌ Missing pexels_api_key in .env")
        return 1

    session = requests.Session()
    summary: List[Dict[str, str]] = []

    for style_key, query in STYLES.items():
        print(f"\n🎨 Style: {style_key} -> {query}")
        try:
            urls = search_style(style_key, query, api_key, session, per_page=6)
            for idx, url in enumerate(urls, 1):
                filename = f"{style_key}-{idx:02d}.jpg"
                dest = OUTPUT_ROOT / style_key / filename
                download(url, dest, session)
                summary.append({"style": style_key, "file": str(dest), "url": url})
                print(f"✅ Saved {dest}")
        except Exception as exc:  # pylint: disable=broad-except
            summary.append({"style": style_key, "status": "failed", "error": str(exc)})
            print(f"❌ {style_key}: {exc}")

    print("\n=== Summary ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    failures = [s for s in summary if s.get("status") == "failed"]
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

