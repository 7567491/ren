#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一的角色库管理，支持预制+用户自定义角色。"""
from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from py.function.config_loader import load_config, LoadedConfig, PROJECT_ROOT


class CharacterRepository:
    """角色库读写与素材存储。"""

    def __init__(
        self,
        *,
        loaded_config: Optional[LoadedConfig] = None,
        storage_dir: Optional[str | Path] = None,
        prebuilt_file: Optional[str | Path] = None,
        user_library_file: Optional[str | Path] = None,
        public_base_url: Optional[str] = None,
        uploads_subdir: Optional[str] = None,
    ):
        self._lock = threading.Lock()
        self.project_root = PROJECT_ROOT
        cfg = loaded_config
        if cfg is None:
            try:
                cfg = load_config()
            except Exception:
                cfg = None
        char_cfg = (cfg.merged if cfg else {}).get("character_library", {})

        self.storage_dir = self._ensure_storage_path(
            [
                storage_dir,
                os.getenv("CHARACTER_STORAGE_DIR"),
                char_cfg.get("storage_dir"),
                self.project_root / "resource" / "pic",
            ]
        )

        self.uploads_subdir = uploads_subdir or os.getenv("CHARACTER_UPLOAD_SUBDIR") or char_cfg.get(
            "uploads_subdir", "user"
        )
        self.public_base_url = (
            public_base_url
            or os.getenv("CHARACTER_PUBLIC_BASE_URL")
            or char_cfg.get("public_base_url")
            or "/api/characters/assets"
        ).rstrip("/")

        self.prebuilt_file = Path(
            prebuilt_file
            or os.getenv("CHARACTER_PREBUILT_FILE")
            or char_cfg.get("prebuilt_file")
            or (self.project_root / "resource" / "characters" / "prebuilt.json")
        )
        self.user_library_file = Path(
            user_library_file
            or os.getenv("CHARACTER_LIBRARY_FILE")
            or char_cfg.get("user_library_file")
            or (self.project_root / "resource" / "characters" / "user_defined.json")
        )
        self.user_library_file.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 公开方法
    # ------------------------------------------------------------------ #
    def list_characters(
        self,
        *,
        status: Optional[str] = "active",
        source: Optional[str] = None,
        include_disabled: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """联合返回预置+用户角色。"""
        records = self._load_all_records()
        filtered: List[Dict[str, Any]] = []
        for record in records:
            if not include_disabled and status and record.get("status") != status:
                continue
            if source and record.get("source") != source:
                continue
            filtered.append(self._to_response(record))

        filtered.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)

        if offset:
            filtered = filtered[offset:]
        if limit is not None:
            filtered = filtered[:limit]
        return filtered

    def get_character(self, character_id: str, *, include_disabled: bool = False) -> Dict[str, Any]:
        """获取单个角色信息（公共视角）。"""
        record = self._find_record(character_id)
        if not record:
            raise KeyError(f"character {character_id} not found")
        if not include_disabled and record.get("status") == "disabled":
            raise KeyError(f"character {character_id} is disabled")
        return self._to_response(record)

    def get_internal(self, character_id: str) -> Dict[str, Any]:
        """提供包含绝对路径的内部数据。"""
        record = self._find_record(character_id)
        if not record:
            raise KeyError(f"character {character_id} not found")
        internal = deepcopy(record)
        internal["_abs_image_path"] = str(self._resolve_absolute_path(record.get("image_path")))
        internal["image_url"] = self._build_public_url(record.get("image_path"))
        return internal

    def create_character(
        self,
        *,
        name: str,
        appearance: Dict[str, Any],
        voice: Optional[Dict[str, Any]],
        image_bytes: bytes,
        image_filename: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
        created_by: str = "user_upload",
    ) -> Dict[str, Any]:
        """保存新角色并写入图库。"""
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("角色名称不能为空")
        if not image_bytes:
            raise ValueError("缺少角色图片内容")
        normalized_appearance = self._normalize_nested_fields(appearance, required_key="zh")
        normalized_voice = self._normalize_nested_fields(voice or {})

        image_rel_path = self._store_image(cleaned_name, image_bytes, image_filename)
        record_id = f"char-{uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": record_id,
            "name": cleaned_name,
            "image_path": image_rel_path,
            "appearance": normalized_appearance,
            "voice": normalized_voice,
            "tags": list(dict.fromkeys((tags or []) + ["user"])),
            "status": "active",
            "source": "user",
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
        }
        with self._lock:
            items = self._read_user_library()
            items.append(record)
            self._write_user_library(items)
        return self._to_response(record)

    def update_character(
        self,
        character_id: str,
        *,
        name: Optional[str] = None,
        appearance: Optional[Dict[str, Any]] = None,
        voice: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_filename: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """更新用户角色信息；预制角色只读。"""
        with self._lock:
            items = self._read_user_library()
            target = next((item for item in items if item.get("id") == character_id), None)
            if not target:
                raise KeyError(f"character {character_id} not found or not editable")

            if name:
                cleaned = name.strip()
                if cleaned:
                    target["name"] = cleaned
            if appearance:
                target["appearance"] = self._normalize_nested_fields(appearance, required_key="zh")
            if voice:
                target["voice"] = self._normalize_nested_fields(voice)
            if status:
                target["status"] = status
            if tags is not None:
                target["tags"] = list(dict.fromkeys(tags))
            if image_bytes:
                target["image_path"] = self._store_image(
                    target["name"], image_bytes, image_filename, existing_path=target.get("image_path")
                )
            target["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write_user_library(items)
            return self._to_response(target)

    def disable_character(self, character_id: str) -> Dict[str, Any]:
        """软删除/禁用角色。"""
        return self.update_character(character_id, status="disabled")

    def resolve_image_path(self, record: Dict[str, Any]) -> Path:
        """辅助：返回素材的绝对路径。"""
        return self._resolve_absolute_path(record.get("image_path"))

    def resolve_asset_path(self, relative_path: str | Path) -> Path:
        """根据存储目录解析素材相对路径。"""
        if relative_path is None or str(relative_path).strip() == "":
            raise ValueError("缺少素材路径")
        rel = Path(relative_path)
        if rel.is_absolute():
            return self._resolve_absolute_path(rel)
        if ".." in rel.parts:
            raise ValueError("非法素材路径")
        return self._resolve_absolute_path(rel)

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _load_all_records(self) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        records.extend(self._read_prebuilt())
        records.extend(self._read_user_library())
        return records

    def _find_record(self, character_id: str) -> Optional[Dict[str, Any]]:
        for record in self._load_all_records():
            if record.get("id") == character_id:
                return record
        return None

    def _read_prebuilt(self) -> List[Dict[str, Any]]:
        if not self.prebuilt_file.exists():
            return []
        try:
            with open(self.prebuilt_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def _read_user_library(self) -> List[Dict[str, Any]]:
        if not self.user_library_file.exists():
            return []
        try:
            with open(self.user_library_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def _write_user_library(self, records: List[Dict[str, Any]]) -> None:
        self.user_library_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.user_library_file, "w", encoding="utf-8") as fh:
            json.dump(records, fh, ensure_ascii=False, indent=2)

    def _store_image(
        self,
        name: str,
        image_bytes: bytes,
        original_filename: Optional[str],
        *,
        existing_path: Optional[str] = None,
    ) -> str:
        suffix = ".jpg"
        if original_filename:
            candidate = Path(original_filename).suffix.lower()
            if candidate in {".png", ".jpeg", ".jpg"}:
                suffix = candidate
        safe_name = f"{uuid4().hex}{suffix}"
        if existing_path:
            safe_name = Path(existing_path).name
        target_dir = self.storage_dir / self.uploads_subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / safe_name
        target.write_bytes(image_bytes)
        return str(Path(self.uploads_subdir) / safe_name)

    def _build_public_url(self, relative_path: Optional[str]) -> Optional[str]:
        if not relative_path:
            return None
        rel = str(relative_path).replace("\\", "/").lstrip("/")
        return f"{self.public_base_url}/{rel}"

    def _resolve_absolute_path(self, relative_path: Optional[str]) -> Path:
        if not relative_path:
            return self.storage_dir
        path = Path(relative_path)
        if path.is_absolute():
            return path
        candidate = self.storage_dir / path
        if candidate.exists():
            return candidate
        project_candidate = self.project_root / path
        if project_candidate.exists():
            return project_candidate
        resource_candidate = self.project_root / "resource" / "pic" / path
        if resource_candidate.exists():
            return resource_candidate
        return project_candidate

    def _to_response(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = deepcopy(record)
        payload["image_url"] = self._build_public_url(record.get("image_path"))
        payload["thumbnail_url"] = payload.get("thumbnail_url") or payload["image_url"]
        return payload

    @staticmethod
    def _normalize_nested_fields(data: Dict[str, Any], required_key: Optional[str] = None) -> Dict[str, Any]:
        normalized = {}
        for key, value in (data or {}).items():
            if value is None:
                continue
            normalized[key] = value.strip() if isinstance(value, str) else value
        if required_key and not normalized.get(required_key):
            raise ValueError(f"{required_key} 字段为必填")
        return normalized

    def _ensure_storage_path(self, candidates: List[Any]) -> Path:
        last_error: Optional[Exception] = None
        for candidate in candidates:
            if not candidate:
                continue
            try:
                path = Path(candidate)
                path.mkdir(parents=True, exist_ok=True)
                return path
            except PermissionError as exc:  # noqa: PERF203
                last_error = exc
                continue
            except OSError as exc:
                last_error = exc
                continue
        fallback = self.project_root / "resource" / "pic"
        try:
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback
        except Exception:
            if last_error:
                raise last_error
            raise


__all__ = ["CharacterRepository"]
