"""
数字人 API 路由

提供任务创建 / 查询 / 素材上传端点，后端对接 DigitalHumanService + TaskRunner。
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

from py.function.config_loader import load_config
from py.services.digital_human_service import DigitalHumanService
from py.services.storage_service import StorageService
from py.services.task_manager import TaskManager
from py.exceptions import ExternalAPIError
from py.services.character_repository import CharacterRepository

router = APIRouter(prefix="/api", tags=["digital-human"])


# -----------------------------------------------------------------------------
# 依赖实例（共享 TaskManager + StorageService，确保 task.json/状态一致）
# -----------------------------------------------------------------------------
task_manager = TaskManager()
try:
    _LOADED_CONFIG = load_config()
except Exception as exc:  # noqa: BLE001
    print(f"[WARN] 加载 config.yaml 失败，改用环境变量: {exc}")
    _LOADED_CONFIG = None

storage_cfg = _LOADED_CONFIG.storage if _LOADED_CONFIG else {}

storage_service = StorageService(
    output_root=storage_cfg.get("output_root") or os.getenv("DIGITAL_HUMAN_OUTPUT_DIR", "output"),
    public_base_url=(
        storage_cfg.get("public_base_url")
        or os.getenv("DIGITAL_HUMAN_PUBLIC_BASE_URL")
        or os.getenv("STORAGE_BUCKET_URL")
    ),
    public_export_dir=storage_cfg.get("local_mount") or os.getenv("DIGITAL_HUMAN_PUBLIC_EXPORT_DIR"),
    namespace=storage_cfg.get("namespace") or os.getenv("DIGITAL_HUMAN_PUBLIC_NAMESPACE", "ren"),
    final_video_name=storage_cfg.get("final_video_name", os.getenv("DIGITAL_HUMAN_FINAL_VIDEO_NAME", "digital_human.mp4")),
    task_dir_pattern=storage_cfg.get("task_dir_pattern", os.getenv("DIGITAL_HUMAN_TASK_DIR_PATTERN", "ren_%m%d%H%M")),
    video_mirror_targets=storage_cfg.get("video_mirrors"),
)
UPLOAD_DIR = storage_service.output_root / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_PUBLIC_BASE = os.getenv(
    "DIGITAL_HUMAN_UPLOAD_BASE_URL", "https://s.linapp.fun/uploads"
).rstrip("/")
character_repository = CharacterRepository()
MAX_CHARACTER_IMAGE_SIZE = 10 * 1024 * 1024

_dh_service: Optional[DigitalHumanService] = None


def get_digital_human_service() -> DigitalHumanService:
    """延迟初始化，方便测试替换环境变量。"""
    global _dh_service
    if _dh_service is None:
        wavespeed_key = os.getenv("WAVESPEED_API_KEY", "")
        minimax_key = os.getenv("MINIMAX_API_KEY", "")
        _dh_service = DigitalHumanService(
            wavespeed_key=wavespeed_key,
            minimax_key=minimax_key,
            storage_service=storage_service,
            task_manager=task_manager,
            loaded_config=_LOADED_CONFIG,
        )
    return _dh_service


def _resolve_upload_file_path(upload_url: Optional[str]) -> Optional[str]:
    """根据上传 URL 推导本地路径，若无法映射则返回原始值。"""
    if not upload_url:
        return None

    candidate = Path(upload_url)
    if candidate.exists():
        return str(candidate)

    parsed = urlparse(upload_url)
    if parsed.scheme in {"http", "https"}:
        filename = Path(parsed.path).name
        if filename:
            local_path = UPLOAD_DIR / filename
            if local_path.exists():
                return str(local_path)

    return upload_url


# -----------------------------------------------------------------------------
# Pydantic 模型
# -----------------------------------------------------------------------------
class CreateTaskRequest(BaseModel):
    avatar_mode: str = Field(..., description="头像模式: upload / prompt")
    avatar_prompt: Optional[str] = Field(
        None, description="头像生成提示词（prompt模式必填）"
    )
    avatar_upload_url: Optional[str] = Field(
        None, description="上传的头像临时路径（upload模式必填）"
    )
    speech_text: str = Field(..., description="播报文本")
    voice_id: str = Field("male-qn-qingse", description="音色ID")
    resolution: str = Field("720p", description="分辨率: 720p / 1080p")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="语速 0.5-2.0")
    pitch: int = Field(0, ge=-12, le=12, description="音调 -12~12")
    emotion: str = Field("neutral", description="情绪: neutral/happy/sad/angry")
    seed: int = Field(42, description="随机种子")
    mask_image: Optional[str] = Field(None, description="蒙版图片URL")
    character_id: Optional[str] = Field(None, description="可选角色ID")


class TaskResponse(BaseModel):
    job_id: str
    status: str
    message: str
    billing: Optional[Dict[str, Any]] = None
    avatar_url: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    cost: Optional[float] = None
    duration: Optional[float] = None
    stages: Optional[Dict[str, Any]] = None
    assets: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None
    config_hash: Optional[str] = None
    logs: Optional[list[str]] = None
    links: Dict[str, str] = Field(default_factory=dict)
    character: Optional[Dict[str, Any]] = None


class CharacterResponse(BaseModel):
    id: str
    name: str
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_path: Optional[str] = None
    appearance: Dict[str, Any]
    voice: Optional[Dict[str, Any]] = None
    tags: list[str] = Field(default_factory=list)
    status: str
    source: str
    created_at: str
    updated_at: Optional[str] = None
    created_by: Optional[str] = None


# -----------------------------------------------------------------------------
# 路由实现
# -----------------------------------------------------------------------------
@router.post("/tasks", response_model=TaskResponse)
async def create_task(req: CreateTaskRequest):
    """创建数字人生成任务。"""
    character_internal: Optional[Dict[str, Any]] = None
    character_payload: Optional[Dict[str, Any]] = None
    if req.character_id:
        try:
            character_internal = character_repository.get_internal(req.character_id)
            character_payload = {
                key: character_internal.get(key)
                for key in ["id", "name", "appearance", "voice", "image_url", "image_path", "tags", "source"]
                if character_internal.get(key) is not None
            }
            if character_internal.get("_abs_image_path"):
                character_payload["image_local_path"] = character_internal["_abs_image_path"]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="角色不存在") from exc

    avatar_local_path = _resolve_upload_file_path(req.avatar_upload_url)
    avatar_prompt = req.avatar_prompt
    resolved_mode = req.avatar_mode

    if character_payload:
        char_prompt = (
            (character_payload.get("appearance") or {}).get("zh")
            or (character_payload.get("appearance") or {}).get("en")
        )
        if char_prompt:
            if avatar_prompt:
                avatar_prompt = f"{char_prompt}\n{avatar_prompt}"
            else:
                avatar_prompt = char_prompt
        char_image_path = character_payload.get("image_local_path") or character_internal.get("_abs_image_path") if character_internal else None
        if char_image_path:
            avatar_local_path = char_image_path
            resolved_mode = "upload"

    if resolved_mode == "prompt" and not avatar_prompt:
        raise HTTPException(
            status_code=400, detail="avatar_mode=prompt 时必须提供 avatar_prompt"
        )
    if resolved_mode == "upload" and not avatar_local_path:
        raise HTTPException(
            status_code=400, detail="avatar_mode=upload 时必须提供 avatar_upload_url 或角色图像"
        )

    job_id = task_manager.create_task(
        preset_name="digital_human",
        num_shots=1,
        resolution=req.resolution,
        user_yaml={},
    )

    if character_payload:
        char_voice_id = (character_payload.get("voice") or {}).get("voice_id")
        if char_voice_id:
            req.voice_id = char_voice_id

    async def _runner():
        try:
            service = get_digital_human_service()
            await service.generate_digital_human(
                job_id=job_id,
                avatar_mode=resolved_mode,
                avatar_prompt=avatar_prompt,
                avatar_upload_path=avatar_local_path,
                speech_text=req.speech_text,
                voice_id=req.voice_id,
                resolution=req.resolution,
                speed=req.speed,
                pitch=req.pitch,
                emotion=req.emotion,
                seed=req.seed,
                mask_image=req.mask_image,
                character=character_payload,
            )
        except Exception as exc:  # noqa: BLE001
            task_manager.update_status(job_id, "failed", f"生成失败: {exc}")

    asyncio.create_task(_runner())

    return TaskResponse(
        job_id=job_id,
        status="pending",
        message="任务已创建，开始生成数字人视频...",
        links={"self": f"/api/tasks/{job_id}"},
    )


@router.get("/tasks/{job_id}", response_model=TaskResponse)
async def get_task_status(job_id: str):
    """查询任务状态与阶段详情。"""
    summary = task_manager.get_task(job_id)
    if not summary:
        raise HTTPException(status_code=404, detail="任务不存在")

    meta = storage_service.load_metadata(job_id)
    status = meta.get("status") if meta else summary.get("status")
    assets = dict((meta or {}).get("assets") or {})
    if job_id:
        filename = storage_service.final_video_name
        video_path = assets.get("video_path")
        if isinstance(video_path, str) and video_path:
            filename = Path(video_path).name or filename
        assets.setdefault("local_video_url", f"/output/{job_id}/{filename}")
    assets.setdefault("character", (meta or {}).get("character") or assets.get("character"))
    character_payload = (meta or {}).get("character") or assets.get("character")
    return TaskResponse(
        job_id=job_id,
        status=status or "unknown",
        message=summary.get("message", ""),
        billing=(meta or {}).get("billing"),
        avatar_url=(meta or {}).get("avatar_url"),
        audio_url=(meta or {}).get("audio_url"),
        video_url=(meta or {}).get("video_url"),
        cost=(meta or {}).get("cost"),
        duration=(meta or {}).get("duration"),
        stages=(meta or {}).get("stages"),
        assets=assets,
        trace_id=(meta or {}).get("trace_id"),
        config_hash=(meta or {}).get("config_hash"),
        logs=(meta or {}).get("logs"),
        character=character_payload,
        links={"self": f"/api/tasks/{job_id}"},
    )


@router.post("/assets/upload")
async def upload_avatar(file: UploadFile):
    """上传头像文件，返回临时 URL 供任务使用。"""
    allowed_types = {"image/png", "image/jpeg"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="只支持图片文件 (png/jpeg)")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="文件扩展名必须为 png/jpg/jpeg")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小需小于 5MB")

    unique_name = f"{uuid4().hex}{suffix}"
    dest_path = UPLOAD_DIR / unique_name
    dest_path.write_bytes(contents)

    public_url = f"{UPLOAD_PUBLIC_BASE}/{unique_name}"
    return {"url": public_url, "path": str(dest_path)}


@router.get("/characters", response_model=list[CharacterResponse])
async def list_characters(
    status: str = "active",
    source: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """返回预制+用户角色列表。"""
    repo_status = None if status == "all" else status
    return character_repository.list_characters(
        status=repo_status,
        source=source,
        limit=limit,
        offset=offset,
        include_disabled=status == "all",
    )


@router.get("/characters/assets/{asset_path:path}")
async def get_character_asset(asset_path: str):
    """返回角色图库中的原始图片文件。"""
    try:
        resolved_path = Path(character_repository.resolve_asset_path(asset_path))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not resolved_path.exists():
        raise HTTPException(status_code=404, detail="角色图片不存在或已删除")

    return FileResponse(resolved_path)


def _parse_tags(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


@router.post("/characters", response_model=CharacterResponse)
async def create_character(
    name: str = Form(...),
    appearance_zh: str = Form(...),
    appearance_en: Optional[str] = Form(None),
    voice_zh: Optional[str] = Form(None),
    voice_prompt: Optional[str] = Form(None),
    voice_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """上传新的角色素材。"""
    contents = await file.read()
    if len(contents) > MAX_CHARACTER_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="角色图片需小于10MB")
    voice_payload = {"zh": voice_zh, "prompt": voice_prompt, "voice_id": voice_id}
    try:
        record = character_repository.create_character(
            name=name,
            appearance={"zh": appearance_zh, "en": appearance_en},
            voice=voice_payload,
            image_bytes=contents,
            image_filename=file.filename,
            tags=_parse_tags(tags),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return record


@router.put("/characters/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    name: Optional[str] = Form(None),
    appearance_zh: Optional[str] = Form(None),
    appearance_en: Optional[str] = Form(None),
    voice_zh: Optional[str] = Form(None),
    voice_prompt: Optional[str] = Form(None),
    voice_id: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """更新角色描述或重传头像。"""
    image_bytes = None
    image_name = None
    if file:
        contents = await file.read()
        if len(contents) > MAX_CHARACTER_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="角色图片需小于10MB")
        image_bytes = contents
        image_name = file.filename

    appearance_payload = None
    if appearance_zh or appearance_en:
        appearance_payload = {"zh": appearance_zh, "en": appearance_en}

    voice_payload = None
    if any([voice_zh, voice_prompt, voice_id]):
        voice_payload = {"zh": voice_zh, "prompt": voice_prompt, "voice_id": voice_id}

    try:
        record = character_repository.update_character(
            character_id,
            name=name,
            appearance=appearance_payload,
            voice=voice_payload,
            status=status,
            tags=_parse_tags(tags) if tags is not None else None,
            image_bytes=image_bytes,
            image_filename=image_name,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="角色不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return record


@router.delete("/characters/{character_id}")
async def delete_character(character_id: str):
    """禁用指定角色。"""
    try:
        record = character_repository.disable_character(character_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="角色不存在") from exc
    return {"status": "ok", "character": record}


async def handle_external_api_error(
    request: Request,
    exc: ExternalAPIError,
):
    """统一 ExternalAPIError -> JSON 响应。"""
    trace_id = exc.trace_id or f"trace-{uuid4().hex[:12]}"
    error_payload = {
        "error": {
            "code": f"{exc.provider}_error",
            "message": exc.message,
            "provider": exc.provider,
            "status_code": exc.status_code,
            "response_data": exc.response_data,
        },
        "trace_id": trace_id,
    }
    return JSONResponse(
        status_code=exc.status_code or 502,
        content=error_payload,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """在 FastAPI 应用中注册数字人路由使用的异常处理。"""
    app.add_exception_handler(ExternalAPIError, handle_external_api_error)


__all__ = ["router", "register_exception_handlers"]
