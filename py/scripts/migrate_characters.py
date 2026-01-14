#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 resource/pic 中的预置人物素材整理为统一的 JSON 数据。

执行方式:
    python3 py/scripts/migrate_characters.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIC_DIR = PROJECT_ROOT / "resource" / "pic"
OUTPUT_DIR = PROJECT_ROOT / "resource" / "characters"
PREBUILT_FILE = OUTPUT_DIR / "prebuilt.json"

PRETTY_NAMES: Dict[str, str] = {
    "ada": "赤焰特工 Ada",
    "gy": "青龙武圣",
    "huang": "舞台领航者",
    "jack": "矩阵特工",
    "longma": "龙裔君主",
    "mai": "格斗女王",
    "mask": "星舰领袖",
    "scalet": "暗影玫瑰",
    "sun": "齐天行者",
    "terminator": "未来守护者",
    "tom": "睿智导师",
}

VOICE_PRESETS: Dict[str, str] = {
    "ada": "female-yujie",
    "gy": "male-qn-jingying",
    "huang": "male-qn-jingying",
    "jack": "male-qn-qingse",
    "longma": "female-yujie",
    "mai": "female-shaonv",
    "mask": "male-qn-qingse",
    "scalet": "female-yujie",
    "sun": "male-qn-qingse",
    "terminator": "male-qn-jingying",
    "tom": "male-qn-qingse",
}

TAG_MAP: Dict[str, list[str]] = {
    "ada": ["prebuilt", "heroine"],
    "gy": ["prebuilt", "historical"],
    "huang": ["prebuilt", "tech"],
    "jack": ["prebuilt", "action"],
    "longma": ["prebuilt", "fantasy"],
    "mai": ["prebuilt", "fighter"],
    "mask": ["prebuilt", "leader"],
    "scalet": ["prebuilt", "agent"],
    "sun": ["prebuilt", "classic"],
    "terminator": ["prebuilt", "cyber"],
    "tom": ["prebuilt", "mentor"],
}


def read_json(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_record(stem: str, meta: Dict) -> Dict:
    normalized = stem.lower()
    now = datetime.now(timezone.utc).isoformat()
    appearance = meta.get("appearance") or {}
    voice = meta.get("voice") or {}
    voice_id = VOICE_PRESETS.get(normalized)
    if voice_id:
        voice = dict(voice)
        voice["voice_id"] = voice_id

    return {
        "id": f"char-{normalized}",
        "name": PRETTY_NAMES.get(normalized, stem.title()),
        "image_path": f"{stem}.jpg",
        "appearance": appearance,
        "voice": voice,
        "tags": TAG_MAP.get(normalized, ["prebuilt"]),
        "status": "active",
        "source": "prebuilt",
        "created_at": now,
        "updated_at": now,
        "created_by": "system",
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for json_file in sorted(PIC_DIR.glob("*.json")):
        meta = read_json(json_file)
        stem = json_file.stem
        jpg_file = PIC_DIR / f"{stem}.jpg"
        if not jpg_file.exists():
            print(f"⚠️ 缺少图片：{jpg_file}")
            continue
        record = build_record(stem, meta)
        records.append(record)

    with open(PREBUILT_FILE, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)
    print(f"✅ 已写入 {PREBUILT_FILE} ({len(records)} 条)")


if __name__ == "__main__":
    main()
