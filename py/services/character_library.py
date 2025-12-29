#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""人物参考图库存储与管理。"""
from __future__ import annotations

import json
import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

DEFAULT_LIBRARY_FILE = Path(__file__).parent.parent.parent / 'resource' / 'character_library.json'
CHARACTER_LIBRARY_FILE = DEFAULT_LIBRARY_FILE
_LIBRARY_LOCK = threading.Lock()
MAX_REFERENCES = 100
MAX_NAME_LENGTH = 60
MAX_DESCRIPTION_LENGTH = 600


def set_character_library_file(path: Path | str) -> None:
    """允许测试覆盖默认存储路径。"""
    global CHARACTER_LIBRARY_FILE
    CHARACTER_LIBRARY_FILE = Path(path)


def _read_library_unlocked() -> List[Dict]:
    if not CHARACTER_LIBRARY_FILE.exists():
        return []
    try:
        with open(CHARACTER_LIBRARY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return data
    return []


def _write_library_unlocked(items: List[Dict]) -> None:
    CHARACTER_LIBRARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHARACTER_LIBRARY_FILE, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def list_references() -> List[Dict]:
    """返回图库中的所有人物引用（按创建时间倒序）。"""
    with _LIBRARY_LOCK:
        items = _read_library_unlocked()
        sorted_items = sorted(
            items,
            key=lambda item: item.get('created_at', ''),
            reverse=True
        )
        return deepcopy(sorted_items)


def upsert_reference(name: str, image_url: str, description: str) -> Dict:
    """创建或覆盖一条参考图记录，依据 image_url 去重。"""
    cleaned_name = (name or '').strip()
    cleaned_url = (image_url or '').strip()
    cleaned_description = (description or '').strip()

    if not cleaned_name:
        raise ValueError('人物名称不能为空')
    if not cleaned_url:
        raise ValueError('参考图URL不能为空')
    if not cleaned_description:
        raise ValueError('人物描述不能为空')

    if len(cleaned_name) > MAX_NAME_LENGTH:
        cleaned_name = cleaned_name[:MAX_NAME_LENGTH].strip()
    if len(cleaned_description) > MAX_DESCRIPTION_LENGTH:
        cleaned_description = cleaned_description[:MAX_DESCRIPTION_LENGTH].strip()

    now = datetime.utcnow().isoformat()

    with _LIBRARY_LOCK:
        items = _read_library_unlocked()
        existing: Optional[Dict] = next(
            (item for item in items if item.get('image_url') == cleaned_url),
            None
        )

        if existing:
            existing['name'] = cleaned_name
            existing['description'] = cleaned_description
            existing['updated_at'] = now
            saved = deepcopy(existing)
        else:
            saved = {
                'id': f"gallery-{uuid4().hex[:8]}",
                'name': cleaned_name,
                'image_url': cleaned_url,
                'description': cleaned_description,
                'created_at': now,
                'updated_at': now
            }
            items.append(saved)
            if len(items) > MAX_REFERENCES:
                items.sort(key=lambda item: item.get('created_at', ''), reverse=True)
                items = items[:MAX_REFERENCES]

        _write_library_unlocked(items)
        return deepcopy(saved)
