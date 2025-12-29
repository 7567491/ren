#!/usr/bin/env python3
"""Download Avengers character portraits into resource/pic.

Requirements:
- .env must contain pexels_api_key

Usage:
    python3 pic/download_avengers.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

import requests


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
OUTPUT_DIR = ROOT_DIR / "resource" / "pic"


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


def download_image(url: str, filename: str, session: requests.Session, timeout: int = 60) -> Path:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    path.write_bytes(response.content)
    return path


def search_pexels(query: str, api_key: str, session: requests.Session) -> str:
    headers = {"Authorization": api_key}
    api_url = "https://api.pexels.com/v1/search"
    params = {"query": query, "per_page": 3, "orientation": "portrait"}
    response = session.get(api_url, headers=headers, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()
    photos: List[Dict[str, str]] = data.get("photos") or []
    if not photos:
        raise RuntimeError(f"No photos returned for query: {query}")
    src = photos[0].get("src") or {}
    image_url = src.get("original") or src.get("large") or src.get("large2x")
    if not image_url:
        raise RuntimeError(f"No image url found for query: {query}")
    return image_url


def main() -> int:
    env = load_env(ENV_PATH)
    api_key = env.get("pexels_api_key")
    if not api_key:
        print("❌ Missing pexels_api_key in .env")
        return 1

    characters = [
        "Iron Man",
        "Captain America",
        "Thor",
        "Hulk",
        "Black Widow",
        "Hawkeye",
        "Scarlet Witch",
        "Vision",
        "Doctor Strange",
        "Captain Marvel",
    ]

    character_queries: Dict[str, str] = {
        "Iron Man": "Iron Man cosplay portrait red armor",
        "Captain America": "Captain America cosplay portrait shield",
        "Thor": "Thor cosplay portrait hammer",
        "Hulk": "Hulk cosplay green warrior portrait",
        "Black Widow": "Black Widow cosplay red hair portrait",
        "Hawkeye": "Hawkeye cosplay archer portrait",
        "Scarlet Witch": "Scarlet Witch cosplay magic portrait",
        "Vision": "Vision cosplay android portrait",
        "Doctor Strange": "Doctor Strange cosplay cloak portrait",
        "Captain Marvel": "Captain Marvel cosplay glowing portrait",
    }

    session = requests.Session()
    results: List[Dict[str, str]] = []

    for name in characters:
        query = character_queries.get(name, f"{name} portrait photo")
        print(f"\n🔎 Searching: {query}")
        try:
            image_url = search_pexels(query, api_key, session)
            filename = name.replace(" ", "_") + ".jpg"
            path = download_image(image_url, filename, session)
            info = {
                "name": name,
                "status": "success",
                "file": str(path),
                "url": image_url,
            }
            print(f"✅ Saved to {path}")
        except Exception as exc:  # pylint: disable=broad-except
            info = {"name": name, "status": "failed", "error": str(exc)}
            print(f"❌ {name}: {exc}")
        results.append(info)

    print("\n=== Summary ===")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    failures = [r for r in results if r.get("status") != "success"]
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
