#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史视频查询服务。

遍历任务目录下的 task.json，提取发布到挂载网盘的视频信息，供“历史视频”面板使用。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from py.services.storage_service import StorageService


class HistoryService:
    """读取任务元数据，返回最近发布的视频列表。"""

    def __init__(self, storage: StorageService):
        self.storage = storage

    def list_recent_videos(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        返回最近的历史视频列表，按更新时间倒序。

        Args:
            limit: 限制返回条数（默认 20，最大 100）
        """
        safe_limit = max(1, min(int(limit or 1), 100))
        entries: List[Dict[str, Any]] = []
        for task_dir in self._iter_task_dirs():
            entry = self._build_entry(task_dir)
            if entry:
                entries.append(entry)

        entries.sort(key=lambda item: item.pop("_sort_timestamp", 0), reverse=True)
        return entries[:safe_limit]

    # ------------------------------------------------------------------ #
    # 内部辅助
    # ------------------------------------------------------------------ #
    def _iter_task_dirs(self) -> Iterable[Path]:
        output_root = self.storage.output_root
        if not output_root.exists():
            return []
        for child in output_root.iterdir():
            if not child.is_dir():
                continue
            meta_path = child / "task.json"
            if not meta_path.exists():
                continue
            yield child

    def _build_entry(self, task_dir: Path) -> Optional[Dict[str, Any]]:
        meta_path = task_dir / "task.json"
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None

        job_id = str(payload.get("job_id") or task_dir.name)
        assets = dict(payload.get("assets") or {})
        status = str(payload.get("status") or "unknown")
        message = payload.get("message")
        video_url = assets.get("video_url") or payload.get("video_url")
        local_video_url = assets.get("local_video_url") or f"/output/{job_id}/{self.storage.final_video_name}"
        public_video_path = assets.get("public_video_path")
        duration = payload.get("duration") or assets.get("duration")
        published_at = (
            assets.get("video_stage_completed_at")
            or (payload.get("stages") or {}).get("video", {}).get("completed_at")
            or payload.get("updated_at")
        )

        # allow未完成的任务过滤掉没有公共访问链接的
        if not video_url and not public_video_path:
            return None

        public_url, relative_url = self._resolve_public_url(video_url, public_video_path)
        size_value = self._resolve_file_size(public_video_path, task_dir / self.storage.final_video_name)
        sort_timestamp = self._parse_timestamp(published_at)
        if sort_timestamp is None:
            sort_timestamp = meta_path.stat().st_mtime

        return {
            "job_id": job_id,
            "status": status,
            "message": message,
            "video_url": public_url or video_url,
            "local_video_url": local_video_url,
            "public_video_path": public_video_path,
            "duration": duration,
            "published_at": published_at,
            "file_size": size_value,
            "web_url": public_url or video_url,
            "relative_url": relative_url,
            "_sort_timestamp": sort_timestamp,
        }

    @staticmethod
    def _parse_timestamp(value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        candidate = value.strip()
        if not candidate:
            return None
        candidate = candidate.replace("Z", "+00:00") if candidate.endswith("Z") else candidate
        try:
            return datetime.fromisoformat(candidate).timestamp()
        except ValueError:
            return None

    @staticmethod
    def _resolve_file_size(*candidates: Any) -> Optional[int]:
        for item in candidates:
            if not item:
                continue
            path = Path(item) if not isinstance(item, Path) else item
            try:
                if path.exists():
                    return path.stat().st_size
            except OSError:
                continue
        return None

    def _resolve_public_url(
        self,
        video_url: Optional[str],
        public_video_path: Optional[str],
    ) -> tuple[Optional[str], Optional[str]]:
        """返回公网 URL 及对应的相对路径。"""
        if video_url and video_url.startswith("http"):
            parsed = urlparse(video_url)
            relative = parsed.path if parsed.path else None
            return video_url, relative

        # 尝试根据 public_video_path 拼接
        if public_video_path and self.storage.public_base_url and self.storage.public_export_base:
            absolute_path = Path(public_video_path)
            base = self.storage.public_export_base
            try:
                relative = absolute_path.relative_to(base)
            except ValueError:
                relative = None
            if relative:
                segment = str(relative).strip("/")
                public_url = "/".join(
                    part.strip("/")
                    for part in [
                        self.storage.public_base_url.rstrip("/"),
                        segment,
                    ]
                    if part
                )
                parsed = urlparse(public_url)
                relative_path = parsed.path if parsed.path else None
                return public_url, relative_path

        if video_url and video_url.startswith("/"):
            return video_url, video_url

        return None, None


__all__ = ["HistoryService"]
