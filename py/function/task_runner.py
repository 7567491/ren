#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数字人任务运行器

将数字人生成流程拆分为 avatar/speech/video 三个阶段，
并负责写入 task.json、更新状态机、成本统计以及公共资源发布。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional
from uuid import uuid4

from py.services.storage_service import StorageService, TaskPaths
from py.services.task_manager import TaskManager


class TaskStatus(str, Enum):
    PENDING = "pending"
    AVATAR_GENERATING = "avatar_generating"
    AVATAR_READY = "avatar_ready"
    SPEECH_GENERATING = "speech_generating"
    SPEECH_READY = "speech_ready"
    VIDEO_RENDERING = "video_rendering"
    FINISHED = "finished"
    FAILED = "failed"


ALLOWED_TRANSITIONS: Dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.AVATAR_GENERATING, TaskStatus.FAILED},
    TaskStatus.AVATAR_GENERATING: {TaskStatus.AVATAR_READY, TaskStatus.FAILED},
    TaskStatus.AVATAR_READY: {TaskStatus.SPEECH_GENERATING, TaskStatus.FAILED},
    TaskStatus.SPEECH_GENERATING: {TaskStatus.SPEECH_READY, TaskStatus.FAILED},
    TaskStatus.SPEECH_READY: {TaskStatus.VIDEO_RENDERING, TaskStatus.FAILED},
    TaskStatus.VIDEO_RENDERING: {TaskStatus.FINISHED, TaskStatus.FAILED},
    TaskStatus.FINISHED: set(),
    TaskStatus.FAILED: set(),
}


@dataclass
class TaskRequest:
    avatar_mode: str
    avatar_prompt: Optional[str]
    avatar_upload_path: Optional[str]
    speech_text: str
    voice_id: str
    resolution: str
    speed: float
    pitch: int
    emotion: str
    seed: int
    mask_image: Optional[str] = None
    character: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        character = payload.get("character")
        if character:
            allowed_keys = ["id", "name", "appearance", "voice", "image_url", "image_path", "tags", "source"]
            payload["character"] = {k: character.get(k) for k in allowed_keys if character.get(k) is not None}
        return payload


@dataclass
class StageState:
    state: str = "pending"
    message: str = ""
    retries: int = 0
    provider_task_id: Optional[str] = None
    output_url: Optional[str] = None
    artifact_path: Optional[str] = None


@dataclass
class TaskRecord:
    job_id: str
    status: TaskStatus
    created_at: str
    updated_at: str
    params: Dict[str, Any]
    trace_id: str
    duration: Optional[float] = None
    stages: Dict[str, StageState] = field(
        default_factory=lambda: {
            "avatar": StageState(),
            "speech": StageState(),
            "video": StageState(),
        }
    )
    cost: float = 0.0
    cost_breakdown: Dict[str, float] = field(
        default_factory=lambda: {"avatar": 0.0, "speech": 0.0, "video": 0.0}
    )
    assets: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
    config_hash: Optional[str] = None
    logs: list[str] = field(default_factory=list)

    def as_serializable(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["stages"] = {
            name: asdict(stage)
            for name, stage in self.stages.items()
        }
        payload["avatar_url"] = self.assets.get("avatar_url")
        payload["audio_url"] = self.assets.get("audio_url")
        payload["video_url"] = self.assets.get("video_url")
        payload["video_path"] = self.assets.get("video_path")
        return payload


@dataclass
class TaskContext:
    job_id: str
    request: TaskRequest
    paths: TaskPaths
    record: TaskRecord


class TaskRunner:
    """数字人任务运行器。"""

    def __init__(
        self,
        avatar_client: Any,
        voice_client: Any,
        video_client: Any,
        storage_service: StorageService,
        task_manager: TaskManager,
        avatar_upload_handler: Optional[
            Callable[[str, Optional[str], Path], Awaitable[str]]
        ] = None,
        logger: Optional[logging.Logger] = None,
        config_hash: Optional[str] = None,
    ):
        self.avatar_client = avatar_client
        self.voice_client = voice_client
        self.video_client = video_client
        self.storage = storage_service
        self.task_manager = task_manager
        self.avatar_upload_handler = avatar_upload_handler
        self.logger = logger or logging.getLogger("TaskRunner")
        self.config_hash = config_hash

    async def run(self, job_id: str, request: TaskRequest) -> Dict[str, Any]:
        """执行完整数字人流水线，返回序列化的 task.json 数据。"""
        ctx = TaskContext(
            job_id=job_id,
            request=request,
            paths=self.storage.prepare_task_paths(job_id),
            record=self._init_record(job_id, request),
        )
        if ctx.request.character:
            sanitized = self._sanitize_character(ctx.request.character)
            ctx.record.assets["character"] = sanitized
            ctx.record.assets["character_id"] = sanitized.get("id")
            self._log(
                ctx,
                f"🎭 使用角色 {sanitized.get('name') or sanitized.get('id')}",
            )
        try:
            self._validate_config_hash(job_id)
            self._set_status(ctx, TaskStatus.PENDING, "任务已创建，等待执行")
            await self.run_step_avatar(ctx)
            await self.run_step_speech(ctx)
            await self.run_step_video(ctx)
            self._mark_finished(ctx)
        except Exception as exc:  # noqa: BLE001
            self._mark_failed(ctx, exc)
            raise

        return ctx.record.as_serializable()

    async def run_step_avatar(self, ctx: TaskContext) -> None:
        """生成或上传头像，并更新 avatar 阶段状态。"""
        self._set_status(ctx, TaskStatus.AVATAR_GENERATING, "正在生成头像...")
        req = ctx.request

        if req.avatar_mode == "upload":
            if not self.avatar_upload_handler:
                raise ValueError("avatar_upload_handler 未配置")
            avatar_url = await self.avatar_upload_handler(
                ctx.job_id, req.avatar_upload_path, ctx.paths.avatar_path
            )
            cost = 0.0
        else:
            avatar_result = await self.avatar_client.generate_images(
                prompts=[req.avatar_prompt],
                resolution="1024x1024",
                num_images=1,
            )
            avatar_url = avatar_result[0]["url"]
            cost = 0.03  # Rough estimate for Seedream

        self._update_stage(
            ctx,
            "avatar",
            state="completed",
            message="头像生成完成",
            output_url=avatar_url,
        )
        ctx.record.assets["avatar_url"] = avatar_url
        ctx.record.assets["wave_avatar_url"] = avatar_url
        self._increase_cost(ctx, "avatar", cost)
        self._set_status(ctx, TaskStatus.AVATAR_READY, f"✅ 头像生成完成: {avatar_url}")

    async def run_step_speech(self, ctx: TaskContext) -> None:
        """调用语音服务生成播报音频并写入任务目录。"""
        self._set_status(ctx, TaskStatus.SPEECH_GENERATING, "正在生成语音...")
        req = ctx.request

        voice_result = await self.voice_client.generate_voice(
            text=req.speech_text,
            voice_id=req.voice_id,
            speed=req.speed,
            pitch=req.pitch,
            emotion=req.emotion,
            output_path=ctx.paths.speech_path,
        )

        self._increase_cost(ctx, "speech", voice_result.get("cost", 0.0))
        duration = voice_result.get("duration")
        if duration is not None:
            ctx.record.duration = duration
            ctx.record.assets["duration"] = duration
        duration_value = duration if duration is not None else 0.0
        self._update_stage(
            ctx,
            "speech",
            state="completed",
            message=f"语音生成完成 ({duration_value:.1f}s)",
            output_url=voice_result.get("audio_url"),
            artifact_path=str(ctx.paths.speech_path),
        )
        ctx.record.assets["audio_url"] = voice_result.get("audio_url")
        ctx.record.assets["audio_path"] = voice_result.get("audio_path")
        ctx.record.assets["wave_audio_url"] = voice_result.get("audio_url")
        self._set_status(
            ctx,
            TaskStatus.SPEECH_READY,
            "✅ 语音生成完成",
        )

    async def run_step_video(self, ctx: TaskContext) -> None:
        """调用唇同步服务生成最终数字人视频并执行发布。"""
        self._set_status(ctx, TaskStatus.VIDEO_RENDERING, "正在生成数字人视频...")
        req = ctx.request
        avatar_url = ctx.record.assets.get("avatar_url") or ctx.record.stages["avatar"].output_url
        audio_url = ctx.record.assets.get("audio_url") or ctx.record.stages["speech"].output_url

        video_result = await self.video_client.generate_video(
            image_url=avatar_url,
            audio_url=audio_url,
            resolution=req.resolution,
            seed=req.seed,
            mask_image=req.mask_image,
        )

        provider_path = video_result.get("video_path")
        local_path = ctx.paths.video_path
        if provider_path:
            provider_path = Path(provider_path)
            if provider_path.exists():
                self.storage.copy_into_task(provider_path, local_path)

        publish_info = None
        try:
            publish_info = self.storage.publish_video(ctx.job_id, local_path)
        except FileNotFoundError:
            publish_info = None

        self._increase_cost(ctx, "video", video_result.get("cost", 0.0))
        provider_video_url = video_result.get("video_url")
        ctx.record.assets["video_url"] = (publish_info or {}).get("url") or provider_video_url
        ctx.record.assets["video_path"] = str(local_path)
        ctx.record.assets["public_video_path"] = (publish_info or {}).get("path")
        ctx.record.assets["avatar_url"] = avatar_url
        ctx.record.assets["wave_video_url"] = provider_video_url
        ctx.record.assets["local_video_url"] = f"/output/{ctx.job_id}/{self.storage.final_video_name}"

        if video_result.get("duration"):
            ctx.record.duration = video_result.get("duration")
            ctx.record.assets["duration"] = video_result.get("duration")

        video_stage_end = datetime.now(timezone.utc)
        self._update_stage(
            ctx,
            "video",
            state="completed",
            message="数字人视频生成完成",
            output_url=ctx.record.assets["video_url"],
            artifact_path=str(local_path),
        )
        ctx.record.assets["video_stage_completed_at"] = video_stage_end.isoformat()
        start_at = ctx.record.assets.get("video_stage_started_at")
        if start_at:
            try:
                start_dt = datetime.fromisoformat(start_at)
                elapsed = (video_stage_end - start_dt).total_seconds()
                ctx.record.assets["video_stage_seconds"] = max(elapsed, 0.0)
            except ValueError:
                pass
        self._persist(ctx)

    # ------------------------------------------------------------------ #
    # 内部辅助方法
    # ------------------------------------------------------------------ #
    def _init_record(self, job_id: str, request: TaskRequest) -> TaskRecord:
        now = datetime.now(timezone.utc).isoformat()
        record = TaskRecord(
            job_id=job_id,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            params=request.as_dict(),
            trace_id=f"trace-{uuid4().hex[:12]}",
            config_hash=self.config_hash,
        )
        speech_text = request.speech_text or ""
        record.assets["text_length"] = len(speech_text)
        return record

    def _increase_cost(self, ctx: TaskContext, stage: str, value: float) -> None:
        ctx.record.cost_breakdown[stage] = ctx.record.cost_breakdown.get(stage, 0.0) + value
        ctx.record.cost = sum(ctx.record.cost_breakdown.values())
        self._persist(ctx)

    def _set_status(
        self,
        ctx: TaskContext,
        status: TaskStatus,
        message: str = "",
        *,
        level: str = "INFO",
    ) -> None:
        if status == ctx.record.status:
            # 允许重复状态用于写入 message
            pass
        elif status not in ALLOWED_TRANSITIONS.get(ctx.record.status, {status}):
            self.logger.warning(
                "非法状态转换: %s -> %s", ctx.record.status.value, status.value
            )
        ctx.record.status = status
        ctx.record.updated_at = datetime.now(timezone.utc).isoformat()
        if status == TaskStatus.VIDEO_RENDERING and not ctx.record.assets.get("video_stage_started_at"):
            ctx.record.assets["video_stage_started_at"] = datetime.now(timezone.utc).isoformat()
        if message:
            self._log(ctx, message, level=level)
        self.task_manager.update_status(ctx.job_id, status.value, message)
        self._persist(ctx)

    def _update_stage(self, ctx: TaskContext, stage: str, **kwargs: Any) -> None:
        stage_state = ctx.record.stages.get(stage) or StageState()
        for key, value in kwargs.items():
            setattr(stage_state, key, value)
        ctx.record.stages[stage] = stage_state
        message = kwargs.get("message")
        if message:
            self._log(ctx, f"[{stage}] {message}")
        self._persist(ctx)

    def _mark_finished(self, ctx: TaskContext) -> None:
        self._set_status(ctx, TaskStatus.FINISHED, "✅ 数字人视频生成完成")

    def _mark_failed(self, ctx: TaskContext, error: Exception) -> None:
        ctx.record.error = {
            "message": str(error),
            "type": error.__class__.__name__,
            "trace_id": ctx.record.trace_id,
        }
        self._set_status(
            ctx,
            TaskStatus.FAILED,
            f"❌ 生成失败: {error}",
            level="ERROR",
        )

    def _persist(self, ctx: TaskContext) -> None:
        self.storage.save_metadata(ctx.job_id, ctx.record.as_serializable())

    def _log(self, ctx: TaskContext, message: str, level: str = "INFO") -> None:
        log_message = message.strip()
        if not log_message:
            return
        level_upper = level.upper()
        log_method = getattr(self.logger, level.lower(), None)
        if callable(log_method):
            log_method("[%s] %s", ctx.job_id, log_message)
        else:
            self.logger.info("[%s] %s", ctx.job_id, log_message)
        line = f"[{level_upper}] {log_message}"
        ctx.record.logs.append(line)
        self.storage.append_log(
            ctx.job_id,
            log_message,
            level=level_upper,
            trace_id=ctx.record.trace_id,
        )

    def _validate_config_hash(self, job_id: str) -> None:
        """确保任务使用的配置哈希与当前加载的配置一致。"""
        if not self.config_hash:
            return
        existing = self.storage.load_metadata(job_id)
        existing_hash = existing.get("config_hash") if isinstance(existing, dict) else None
        if existing_hash and existing_hash != self.config_hash:
            raise RuntimeError(
                "配置文件已更新，无法继续使用旧任务。请重新创建任务以加载最新配置。"
            )

    @staticmethod
    def _sanitize_character(character: Dict[str, Any]) -> Dict[str, Any]:
        """移除内部字段，仅保留对外可见信息。"""
        allowed_keys = ["id", "name", "appearance", "voice", "image_url", "image_path", "tags", "source"]
        sanitized: Dict[str, Any] = {}
        for key in allowed_keys:
            value = character.get(key)
            if value is not None:
                sanitized[key] = value
        return sanitized


__all__ = [
    "TaskRunner",
    "TaskRequest",
    "TaskStatus",
    "TaskRecord",
    "StageState",
]
