#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务产物存储与对外发布服务。

职责：
1. 统一管理 `output/<job_id>` 目录结构（头像/音频/视频/log/task.json）。
2. 提供元数据写入、artifact 拷贝等常用操作。
3. 按配置将最终视频复制到对象存储/挂载目录（如 /mnt/www/ren/ren_MMDDHHMM/）
   并返回可访问 URL，便于前端直接播放。
4. 可选：将最终视频额外拷贝到其他镜像目录（如 /mnt/www/ad），便于兄弟项目复用。
"""
from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TaskPaths:
    """某个任务的关键路径集合。"""

    task_dir: Path
    avatar_path: Path
    speech_path: Path
    video_path: Path
    meta_path: Path
    log_path: Path


logger = logging.getLogger(__name__)


class StorageService:
    """
    管理数字人任务的本地输出目录与公开发布目录。

    Args:
        output_root: 本地任务输出根目录（默认 `output/`）
        public_base_url: 对外访问 URL 前缀，如 `https://s.linapp.fun`
        public_export_dir: 对外访问挂载点，如 `/mnt/www`
        namespace: 发布目录下的命名空间（默认 `ren`）
        final_video_name: 最终视频文件名（默认 `digital_human.mp4`）
        task_dir_pattern: 发布目录命名模板，遵循 `datetime.strftime`
        video_mirror_targets: 额外镜像目录配置列表
    """

    def __init__(
        self,
        output_root: str | Path = "output",
        public_base_url: Optional[str] = None,
        public_export_dir: Optional[str | Path] = None,
        namespace: str = "ren",
        final_video_name: str = "digital_human.mp4",
        task_dir_pattern: str = "ren_%m%d%H%M",
        video_mirror_targets: Optional[List[Dict[str, str]]] = None,
    ):
        self.output_root = Path(output_root).expanduser()
        self.output_root.mkdir(parents=True, exist_ok=True)

        self.public_base_url = public_base_url.rstrip("/") if public_base_url else None
        self.namespace = (namespace or "").strip("/ ")
        self.final_video_name = final_video_name
        self.task_dir_pattern = task_dir_pattern
        self._base_includes_namespace = False
        if self.public_base_url and self.namespace:
            if self.public_base_url.endswith(f"/{self.namespace}"):
                self._base_includes_namespace = True

        self.public_export_base: Optional[Path] = None
        if public_export_dir:
            base_candidate = Path(public_export_dir).expanduser()
            try:
                base_candidate.mkdir(parents=True, exist_ok=True)
                self.public_export_base = base_candidate
            except PermissionError:
                self.public_export_base = None

        self.public_root: Optional[Path] = None
        if self.public_export_base:
            candidate = self.public_export_base
            if self.namespace:
                candidate = candidate / self.namespace
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                self.public_root = candidate
            except PermissionError:
                self.public_root = None

        self.video_mirror_targets: list[dict] = []
        if video_mirror_targets:
            self._init_video_mirrors(video_mirror_targets)

    # ------------------------------------------------------------------ #
    # 任务目录管理
    # ------------------------------------------------------------------ #
    def prepare_task_paths(self, task_id: str) -> TaskPaths:
        """
        创建并返回某任务相关的标准路径。

        Args:
            task_id: 任务 ID
        """
        task_dir = self.output_root / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        return TaskPaths(
            task_dir=task_dir,
            avatar_path=task_dir / "avatar.png",
            speech_path=task_dir / "speech.mp3",
            video_path=task_dir / self.final_video_name,
            meta_path=task_dir / "task.json",
            log_path=task_dir / "log.txt",
        )

    def save_metadata(self, task_id: str, payload: Dict) -> Path:
        """写入 task.json。"""
        paths = self.prepare_task_paths(task_id)
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        paths.meta_path.write_text(text, encoding="utf-8")
        return paths.meta_path

    def load_metadata(self, task_id: str) -> Dict:
        """读取 task.json，如不存在返回空 dict。"""
        paths = self.prepare_task_paths(task_id)
        if not paths.meta_path.exists():
            return {}
        return json.loads(paths.meta_path.read_text(encoding="utf-8"))

    def copy_into_task(self, source: Path, destination: Path) -> Path:
        """
        将外部文件复制进任务目录，若目标与源相同则跳过。

        Args:
            source: 现有文件路径
            destination: 任务目录内目标路径
        """
        source = source.expanduser()
        destination = destination.expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            if source.resolve() == destination.resolve():  # type: ignore[attr-defined]
                return destination
        except FileNotFoundError:
            # resolve 失败则直接复制（由 shutil 决定是否报错）
            pass

        shutil.copy2(source, destination)
        return destination

    def append_log(
        self,
        task_id: str,
        message: str,
        *,
        level: str = "INFO",
        trace_id: Optional[str] = None,
    ) -> Path:
        """
        追加日志到任务 log.txt，包含时间戳/级别/trace_id。
        """
        paths = self.prepare_task_paths(task_id)
        timestamp = datetime.now(timezone.utc).isoformat()
        safe_message = message.rstrip()
        line_parts = [f"[{timestamp}]", f"[{level.upper()}]"]
        if trace_id:
            line_parts.append(f"[trace={trace_id}]")
        line = " ".join(line_parts) + f" {safe_message}\n"
        paths.log_path.parent.mkdir(parents=True, exist_ok=True)
        with paths.log_path.open("a", encoding="utf-8") as fp:
            fp.write(line)
        return paths.log_path

    def _init_video_mirrors(self, targets: List[Dict[str, str]]) -> None:
        """解析镜像目录配置。"""
        for index, raw in enumerate(targets, start=1):
            dir_value = raw.get("dir") or raw.get("path") or raw.get("directory")
            if not dir_value:
                continue
            base_dir = Path(dir_value).expanduser()
            try:
                base_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError as exc:  # noqa: BLE001
                logger.warning("⚠️ 无法创建镜像目录 %s: %s", base_dir, exc)
                continue
            entry = {
                "name": raw.get("name") or raw.get("id") or f"mirror-{index}",
                "base_dir": base_dir,
                "base_url": raw.get("base_url"),
                "filename_template": raw.get("filename_template") or "{job_id}.mp4",
                "relative_dir": raw.get("relative_dir") or "",
            }
            self.video_mirror_targets.append(entry)

    @staticmethod
    def _format_template(template: str, context: Dict[str, str]) -> str:
        try:
            return template.format(**context)
        except Exception:  # noqa: BLE001
            return template

    def _mirror_video(
        self,
        task_id: str,
        local_video_path: Path,
        slug: str,
    ) -> list[Dict[str, str]]:
        """将视频复制到额外镜像目录。"""
        if not self.video_mirror_targets:
            return []

        context = {
            "job_id": task_id,
            "slug": slug,
            "filename": self.final_video_name,
            "video_name": self.final_video_name,
        }
        results: list[Dict[str, str]] = []
        for target in self.video_mirror_targets:
            dest_dir = target["base_dir"]
            relative_dir = target.get("relative_dir") or ""
            relative_dir_value = ""
            if relative_dir:
                relative_dir_value = self._format_template(relative_dir, context).strip()
                if relative_dir_value:
                    dest_dir = dest_dir / relative_dir_value
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError as exc:  # noqa: BLE001
                logger.warning("⚠️ 无法创建镜像子目录 %s: %s", dest_dir, exc)
                continue

            filename = self._format_template(target["filename_template"], context)
            dest_path = dest_dir / filename
            try:
                shutil.copy2(local_video_path, dest_path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("⚠️ 复制视频到镜像失败 (%s → %s): %s", local_video_path, dest_path, exc)
                continue

            entry: Dict[str, str] = {
                "name": target["name"],
                "path": str(dest_path),
            }
            base_url = target.get("base_url")
            if base_url:
                segments = [base_url.rstrip("/")]
                if relative_dir_value:
                    segments.append(relative_dir_value.strip("/"))
                segments.append(filename)
                entry["url"] = "/".join(filter(None, segments))
            results.append(entry)
        return results

    # ------------------------------------------------------------------ #
    # 对外发布
    # ------------------------------------------------------------------ #
    def publish_video(self, task_id: str, local_video_path: Path) -> Optional[Dict[str, str]]:
        """
        将最终视频复制到公共挂载目录并返回 URL；若配置了镜像目录，也会一并复制。
        若未配置 public_root / public_base_url 且没有镜像目录，返回 None。
        """
        if not local_video_path.exists():
            raise FileNotFoundError(local_video_path)

        slug = datetime.utcnow().strftime(self.task_dir_pattern or task_id)
        publish_result: Optional[Dict[str, str]] = None

        if self.public_root and self.public_base_url:
            dest_dir = self.public_root / slug

            index = 1
            while dest_dir.exists():
                index += 1
                dest_dir = self.public_root / f"{slug}-{index}"

            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / self.final_video_name
            shutil.copy2(local_video_path, dest_path)

            url_parts = [self.public_base_url.rstrip("/")]
            if self.namespace and not self._base_includes_namespace:
                url_parts.append(self.namespace.strip("/"))
            url_parts.extend([dest_dir.name, self.final_video_name])
            public_url = "/".join(url_parts)
            publish_result = {"path": str(dest_path), "url": public_url}

        mirrors = self._mirror_video(task_id, local_video_path, slug)
        if mirrors:
            publish_result = publish_result or {}
            publish_result["mirrors"] = mirrors

        return publish_result

    def publish_task_asset(
        self,
        task_id: str,
        local_path: Path,
        *,
        asset_dir: str = "output",
        filename: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        """
        将任务产物复制到挂载目录（如 /mnt/www/output/<task_id>/）。
        """
        if not self.public_export_base or not self.public_base_url:
            return None
        if not local_path.exists():
            raise FileNotFoundError(local_path)

        sanitized_asset_dir = asset_dir.strip("/ ")
        target_dir = self.public_export_base
        if self.namespace:
            target_dir = target_dir / self.namespace
        if sanitized_asset_dir:
            target_dir = target_dir / sanitized_asset_dir
        target_dir = target_dir / task_id
        target_dir.mkdir(parents=True, exist_ok=True)

        dest_path = target_dir / (filename or local_path.name)
        shutil.copy2(local_path, dest_path)

        url_parts = [self.public_base_url.rstrip("/")]
        if self.namespace and not self._base_includes_namespace:
            url_parts.append(self.namespace.strip("/"))
        if sanitized_asset_dir:
            url_parts.append(sanitized_asset_dir)
        url_parts.extend([task_id, dest_path.name])
        public_url = "/".join(url_parts)

        return {"path": str(dest_path), "url": public_url}


__all__ = ["StorageService", "TaskPaths"]
