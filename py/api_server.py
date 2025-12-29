"""
AI 视频生成 REST API 服务
提供 Web API 接口，管理任务队列和子进程执行
"""
import json
import os
import sys
import shutil
import yaml
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from urllib.parse import urlparse

import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from py.services.task_manager import TaskManager
from py.services.eta_estimator import ETAEstimator
from py.services import character_library

# ==================== FastAPI 应用初始化 ====================
app = FastAPI(
    title="AI Video Generation API",
    description="AI 故事化视频生成系统 REST API",
    version="1.0.0"
)

# CORS 配置（允许前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 全局变量 ====================
TEMP_DIR = "temp"
OUTPUT_DIR = "output"
PUBLIC_EXPORT_DIR = Path("/mnt/www")
PUBLIC_EXPORT_URL = "https://s.linapp.fun"
task_manager = TaskManager(storage_dir=TEMP_DIR)
eta_estimator = ETAEstimator(stats_file=Path(TEMP_DIR) / "eta_stats.json")
eta_bootstrap_done = False

# 并发限制（从配置读取）
MAX_CONCURRENT_TASKS = 1
PROGRESS_POLL_INTERVAL = 1  # seconds between checkpoint inspections
running_tasks = {}  # {job_id: subprocess}
WAVESPEED_BALANCE_URL = "https://api.wavespeed.ai/api/v3/balance"
CHARACTER_IMAGE_TIMEOUT = 10

# ==================== 预设映射配置 ====================
# 预设名称到风格编号的映射（对应 ad-back.py 中的 STYLE_NUMBER_MAP）
PRESET_TO_STYLE_NUMBER = {
    '卡通': 1,        # cartoon_adventure
    '时尚': 2,        # luxury_fashion
    '仙侠': 3,        # ink_xianxia
    '3D': 4,          # realistic_3d
    '电影': 5,        # cinematic
    '科技': 6,        # technology
    '赛博朋克': 7,    # cyberpunk
    '太空': 8,        # space_exploration
    '户外': 9,        # outdoor_adventure
    '魔法': 10,       # magical_fantasy
    # 英文别名
    'cartoon': 1,
    'fashion': 2,
    'xianxia': 3,
    'realistic': 4,
    'cinematic': 5,
    'technology': 6,
    'cyberpunk': 7,
    'space': 8,
    'outdoor': 9,
    'magic': 10,
}


def set_temp_dir(temp_dir: str):
    """设置临时目录（用于测试）"""
    global task_manager, TEMP_DIR, eta_estimator, eta_bootstrap_done
    TEMP_DIR = temp_dir
    task_manager = TaskManager(storage_dir=temp_dir)
    eta_estimator = ETAEstimator(stats_file=Path(temp_dir) / "eta_stats.json")
    eta_bootstrap_done = False


def generate_config_from_preset(
    topic: Optional[str],
    preset_name: Optional[str],
    num_shots: int,
    shot_duration: int,
    resolution: str,
    llm_provider: int,
    image_model: int,
    video_model: int,
    voice: int,
    concurrent_workers: int,
    job_id: str,
    character_enabled: bool = False,
    character_image_url: Optional[str] = None,
    character_description: Optional[str] = None,
    character_name: Optional[str] = None,
    logo_outro_enabled: Optional[bool] = True
) -> dict:
    """
    根据预设参数生成完整配置

    Args:
        topic: 视频主题
        preset_name: 预设名称（如"科技"、"仙侠"等）
        num_shots: 镜头数
        shot_duration: 每镜头时长
        resolution: 分辨率
        llm_provider: LLM提供商（仅支持 1=DeepSeek）
        image_model: 图像模型（1-6）
        video_model: 视频模型（1-5）
        voice: 音色选择（1-13）
        concurrent_workers: 并发线程数
        job_id: 任务 ID
        logo_outro_enabled: 是否启用片尾logo动画

    Returns:
        配置字典

    Raises:
        ValueError: 如果预设名称无效
    """
    # 默认风格编号
    style_num = 6  # 默认：科技

    # 根据预设名称查找风格编号
    if preset_name:
        if preset_name in PRESET_TO_STYLE_NUMBER:
            style_num = PRESET_TO_STYLE_NUMBER[preset_name]
        else:
            # 尝试部分匹配
            for key, value in PRESET_TO_STYLE_NUMBER.items():
                if key in preset_name or preset_name in key:
                    style_num = value
                    break

    # 构建完整配置（对应user.yaml结构）
    include_logo_outro = True if logo_outro_enabled is None else bool(logo_outro_enabled)

    config = {
        'topic': topic or f'AI视频-{job_id}',
        'style': style_num,
        'shot_count': num_shots,
        'shot_duration': shot_duration,
        'resolution': resolution,
        'llm': {
            'provider': llm_provider
        },
        'models': {
            'image': image_model,
            'video': video_model
        },
        'audio': {
            'voice': voice
        },
        'workflow': {
            'concurrent_workers': concurrent_workers
        }
    }

    if character_enabled:
        character_config = {
            'enabled': True,
            'description': (character_description or '').strip() or '主角角色'
        }
        cleaned_name = (character_name or '').strip()
        if cleaned_name:
            character_config['name'] = cleaned_name
        if character_image_url:
            character_config['character_image'] = character_image_url.strip()
        config['character'] = character_config
    else:
        config['character'] = {'enabled': False}

    config['logo'] = {
        'enabled': include_logo_outro
    }

    # 验证配置有效性
    validate_config(config)

    return config


def validate_config(config: dict) -> None:
    """
    验证配置有效性

    Args:
        config: 配置字典

    Raises:
        ValueError: 如果配置无效
    """
    # 验证必需字段
    required_fields = ['topic', 'style', 'shot_count', 'shot_duration', 'resolution']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"配置缺少必需字段: {field}")

    # 验证风格编号
    style = config['style']
    if not isinstance(style, int):
        raise ValueError(f"风格编号必须是整数，当前: {type(style)}")

    if style < 1 or style > 10:
        raise ValueError(f"风格编号 {style} 无效，有效范围: 1-10")

    # 验证镜头数
    shot_count = config['shot_count']
    if shot_count < 1 or shot_count > 10:
        raise ValueError(f"镜头数 {shot_count} 无效，有效范围: 1-10")

    # 验证分辨率
    valid_resolutions = ['480p', '720p', '1080p']
    if config['resolution'] not in valid_resolutions:
        raise ValueError(f"分辨率 {config['resolution']} 无效，有效值: {valid_resolutions}")


# 兼容历史测试接口
validate_config_params = validate_config


def validate_character_image_url(image_url: str) -> None:
    """确保参考图URL可访问并返回图片。"""
    parsed = urlparse(image_url)
    if parsed.scheme not in ('http', 'https'):
        raise HTTPException(status_code=400, detail="参考图URL必须以 http 或 https 开头")

    response = None
    try:
        response = requests.get(image_url, timeout=CHARACTER_IMAGE_TIMEOUT, stream=True)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=400, detail=f"无法访问参考图: {exc}") from exc
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

    content_type = (response.headers.get('Content-Type') or '').lower()
    if 'image' not in content_type:
        raise HTTPException(status_code=400, detail="参考图URL返回的不是图片资源")


def fetch_wavespeed_balance(api_key: str, timeout: int = 10) -> Optional[float]:
    """查询 Wavespeed 余额（返回美元），失败返回 None"""
    if not api_key:
        return None

    try:
        response = requests.get(
            WAVESPEED_BALANCE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout
        )
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, dict) and 'data' in payload and isinstance(payload['data'], dict):
            data = payload['data']
            balance = data.get('balance') or data.get('credit') or data.get('amount')
        else:
            balance = payload.get('balance') or payload.get('credit') or payload.get('amount')

        if balance is None:
            return None
        return float(balance)
    except requests.exceptions.RequestException:
        raise



# ==================== 请求模型 ====================
class JobCreateRequest(BaseModel):
    """创建任务请求"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "topic": "一个投资银行客户经理使用Akamai推理云",
                "preset_name": "科技",
                "num_shots": 5,
                "shot_duration": 5,
                "resolution": "720p",
                "llm_provider": 1,
                "image_model": 4,
                "video_model": 1,
                "voice": 6,
                "concurrent_workers": 6
            }
        }
    )

    # 基础配置
    topic: Optional[str] = None
    preset_name: Optional[str] = None
    num_shots: Optional[int] = 5
    shot_duration: Optional[int] = 5
    resolution: Optional[str] = "720p"

    # 模型选择
    llm_provider: Optional[int] = 1
    image_model: Optional[int] = 4
    video_model: Optional[int] = 1
    voice: Optional[int] = 6

    # 工作流配置
    concurrent_workers: Optional[int] = 6
    logo_outro_enabled: Optional[bool] = True

    # API密钥（前端传递）
    wavespeed_api_key: Optional[str] = None

    # 参考人物图配置
    character_enabled: Optional[bool] = False
    character_image_url: Optional[str] = None
    character_description: Optional[str] = None
    character_name: Optional[str] = None

    # 高级模式
    user_yaml: Optional[str] = None
    resume_id: Optional[str] = None
    no_auto_resume: Optional[bool] = False


class JobResponse(BaseModel):
    """任务响应"""
    job_id: str
    status: str
    message: str = ""
    progress: float = 0.0
    result_path: Optional[str] = None
    created_at: str = ""
    eta_profile: Optional[dict] = None
    num_shots: Optional[int] = None


class LogResponse(BaseModel):
    """日志响应"""
    lines: List[str]
    total_lines: int = 0
    eof: bool = True


class BalanceRequest(BaseModel):
    """账户余额查询请求"""
    wavespeed_api_key: str


class BalanceResponse(BaseModel):
    """账户余额响应"""
    balance: float
    currency: str = "USD"


class CharacterReferenceRequest(BaseModel):
    """新增人物图库请求"""
    name: str
    image_url: str
    description: str


class CharacterReferenceResponse(BaseModel):
    """人物图库响应"""
    id: str
    name: str
    image_url: str
    description: str
    created_at: str
    updated_at: Optional[str] = None


# ==================== 静态文件服务 ====================

# 挂载前端目录
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.get("/")
async def root():
    """根路径 - 返回前端页面"""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "AI Video Generation API", "docs": "/docs"}


# ==================== API 端点 ====================

@app.on_event("startup")
async def on_startup_event():
    """服务启动时先尝试修复任务状态"""
    reconcile_task_states()
    bootstrap_eta_history()


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "running_tasks": len(running_tasks),
        "max_concurrent": MAX_CONCURRENT_TASKS
    }


@app.get("/api/character-references", response_model=List[CharacterReferenceResponse])
async def list_character_references_endpoint():
    """返回已保存的人物参考图库。"""
    return character_library.list_references()


@app.post("/api/character-references", response_model=CharacterReferenceResponse)
async def create_character_reference_endpoint(request: CharacterReferenceRequest):
    """验证并保存新的参考人物图。"""
    validate_character_image_url(request.image_url.strip())
    try:
        record = character_library.upsert_reference(
            name=request.name,
            image_url=request.image_url,
            description=request.description
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return record


@app.post("/api/jobs", response_model=JobResponse)
async def create_job(request: JobCreateRequest, background_tasks: BackgroundTasks):
    """
    创建新的视频生成任务

    **基础配置：**
    - **topic**: 视频主题（文字描述）
    - **preset_name**: 预设风格（科技/卡通/时尚/仙侠/3D/电影/赛博朋克/太空/户外/魔法）
    - **num_shots**: 镜头数（1-10）
    - **shot_duration**: 每镜头时长（3-10秒）
    - **resolution**: 分辨率（480p/720p/1080p）

    **模型选择：**
    - **llm_provider**: LLM提供商（仅支持 1=DeepSeek）
    - **image_model**: 图像模型（1-6）
    - **video_model**: 视频模型（1-5）
    - **voice**: 配音音色（1-13）

    **工作流配置：**
    - **concurrent_workers**: 并发线程数（1-9）

    **高级模式：**
    - **user_yaml**: 用户自定义 YAML 配置（完整覆盖上述选项）
    """
    try:
        resume_mode = bool(request.resume_id)
        job_id = None
        config_file = None
        config_data = None

        if resume_mode:
            job_id = request.resume_id.strip()
            if not job_id:
                raise HTTPException(status_code=400, detail="无效的 resume_id")

            task = task_manager.get_task(job_id)
            if not task:
                raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")

            if task['status'] == 'running':
                raise HTTPException(status_code=400, detail="任务正在运行中，无法继续操作")

            if task['status'] not in ['failed', 'succeeded', 'queued']:
                raise HTTPException(status_code=400, detail=f"当前状态 {task['status']} 暂不支持断点续传")

            config_file = Path(TEMP_DIR) / f"user-{job_id}.yaml"
            if not config_file.exists():
                raise HTTPException(status_code=400, detail="找不到任务配置文件，无法断点续传")

            if request.wavespeed_api_key:
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        resume_config = yaml.safe_load(f) or {}
                except Exception:
                    resume_config = {}

                if not isinstance(resume_config, dict):
                    resume_config = {}

                api_settings = resume_config.get('api') or {}
                api_settings['wavespeed_key'] = request.wavespeed_api_key.strip()
                resume_config['api'] = api_settings

                with open(config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(resume_config, f, allow_unicode=True, default_flow_style=False)
                config_data = resume_config
            else:
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                except Exception:
                    config_data = None

            task_manager.update_status(job_id, 'queued', '重新开始任务，准备断点续传')
            task_manager.update_progress(job_id, 0.0, '重新开始任务，准备断点续传')
        else:
            # 创建任务
            job_id = task_manager.create_task(
                preset_name=request.preset_name,
                num_shots=request.num_shots or 5,
                resolution=request.resolution or "720p",
                user_yaml=request.user_yaml,
                resume_id=request.resume_id,
                no_auto_resume=request.no_auto_resume or False
            )

            # 生成配置文件
            config_file = Path(TEMP_DIR) / f"user-{job_id}.yaml"
            if request.user_yaml:
                # 使用用户提供的 YAML
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(request.user_yaml)

                # 验证用户提供的配置
                try:
                    config_data = yaml.safe_load(request.user_yaml)
                    validate_config(config_data)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"配置验证失败: {str(e)}")
            else:
                # 使用新的配置生成函数
                config = generate_config_from_preset(
                    topic=request.topic,
                    preset_name=request.preset_name,
                    num_shots=request.num_shots or 5,
                    shot_duration=request.shot_duration or 5,
                    resolution=request.resolution or "720p",
                    llm_provider=request.llm_provider or 1,
                    image_model=request.image_model or 4,
                    video_model=request.video_model or 1,
                    voice=request.voice or 6,
                    concurrent_workers=request.concurrent_workers or 6,
                    job_id=job_id,
                    character_enabled=bool(request.character_enabled),
                    character_image_url=request.character_image_url,
                    character_description=request.character_description,
                    character_name=request.character_name,
                    logo_outro_enabled=request.logo_outro_enabled if request.logo_outro_enabled is not None else True
                )

                # 如果提供了Wavespeed API密钥，添加到配置中
                if request.wavespeed_api_key:
                    if 'api' not in config:
                        config['api'] = {}
                    config['api']['wavespeed_key'] = request.wavespeed_api_key.strip()

                # 验证配置
                validate_config(config)

                # 写入文件
                with open(config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                config_data = config

        # 添加后台任务执行
        background_tasks.add_task(run_video_generation, job_id, config_file, resume_mode)

        # 计算并保存 ETA 估计
        if config_data and not isinstance(config_data, str):
            eta_profile = eta_estimator.estimate(config_data)
            task_manager.set_eta_profile(job_id, eta_profile)
        elif resume_mode and config_data is None:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    resume_conf = yaml.safe_load(f)
            except Exception:
                resume_conf = None
            if resume_conf:
                eta_profile = eta_estimator.estimate(resume_conf)
                task_manager.set_eta_profile(job_id, eta_profile)

        # 返回任务信息
        task = task_manager.get_task(job_id)
        return JobResponse(**task)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@app.get("/api/jobs", response_model=dict)
async def list_jobs():
    """列出所有任务"""
    reconcile_task_states()
    tasks = task_manager.list_tasks()
    return {
        "jobs": tasks,
        "total": len(tasks)
    }


@app.post("/api/wavespeed/balance", response_model=BalanceResponse)
async def get_wavespeed_balance_api(request: BalanceRequest):
    """查询 Wavespeed API 账户余额"""
    api_key = (request.wavespeed_api_key or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="缺少 Wavespeed API 密钥")

    try:
        balance = fetch_wavespeed_balance(api_key)
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response else 502
        if status_code == 401:
            raise HTTPException(status_code=401, detail="Wavespeed API 密钥无效或已过期") from exc
        raise HTTPException(status_code=status_code, detail="Wavespeed 余额查询失败") from exc
    except requests.exceptions.Timeout as exc:
        raise HTTPException(status_code=504, detail="查询 Wavespeed 余额超时，请稍后重试") from exc
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=502, detail="无法连接 Wavespeed 服务，请稍后再试") from exc

    if balance is None:
        raise HTTPException(status_code=502, detail="未能从 Wavespeed API 获取余额信息")

    return BalanceResponse(balance=round(balance, 2))


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """获取任务状态"""
    reconcile_task_states()
    task = task_manager.get_task(job_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")

    return JobResponse(**task)


@app.get("/api/jobs/{job_id}/log", response_model=LogResponse)
async def get_job_log(job_id: str, lines: int = 100, offset: int = 0):
    """
    获取任务日志

    - **lines**: 返回的行数（默认 100）
    - **offset**: 起始行偏移（默认 0）
    """
    task = task_manager.get_task(job_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")

    log_file = Path(OUTPUT_DIR) / job_id / "log.txt"

    if not log_file.exists():
        return LogResponse(lines=[], total_lines=0, eof=True)

    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()

        total = len(all_lines)
        start = offset
        end = min(offset + lines, total)

        # 移除行尾换行符
        selected_lines = [line.rstrip('\n') for line in all_lines[start:end]]

        return LogResponse(
            lines=selected_lines,
            total_lines=total,
            eof=(end >= total)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {str(e)}")


@app.get("/api/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    """获取任务结果"""
    reconcile_task_states()
    task = task_manager.get_task(job_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")

    if task['status'] != 'succeeded':
        raise HTTPException(status_code=400, detail=f"任务未完成: {task['status']}")

    return {
        "job_id": job_id,
        "result_path": task.get('result_path'),
        "status": task['status']
    }


# ==================== 进度追踪辅助函数 ====================

def parse_checkpoint_file(checkpoint_file: Path) -> Optional[dict]:
    """
    解析checkpoint文件

    Args:
        checkpoint_file: checkpoint文件路径

    Returns:
        checkpoint字典，如果文件不存在或损坏则返回None
    """
    import json as json_module

    if not checkpoint_file.exists():
        return None

    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            return json_module.load(f)
    except (json_module.JSONDecodeError, IOError):
        return None


def calculate_progress_from_checkpoint(checkpoint: dict, detailed: bool = False) -> float:
    """
    根据checkpoint计算进度，按照“资产→剧本→图像→视频→音频/合成”权重映射

    Args:
        checkpoint: checkpoint字典
        detailed: 是否使用详细进度（考虑子任务）

    Returns:
        进度值 (0.0 - 1.0)
    """
    if not checkpoint or 'completed_steps' not in checkpoint:
        return 0.0

    # 阶段权重（累计后为100%）
    stage_weights = {
        'assets': 0.10,
        'story': 0.10,
        'images': 0.30,
        'videos': 0.40,
        'audio_subtitle': 0.05,
        'composition': 0.05,
    }

    completed_steps = checkpoint.get('completed_steps', [])
    stages_info = checkpoint.get('stages', {})

    # 只计数已知步骤，保持顺序
    valid_completed = []
    seen = set()
    for step in completed_steps:
        if step in stage_weights and step not in seen:
            valid_completed.append(step)
            seen.add(step)

    base_progress = sum(stage_weights[step] for step in valid_completed)

    # 兼容旧checkpoint：character_reference完成视为资产阶段完成
    if 'assets' not in seen and stages_info and stages_info.get('character_reference'):
        base_progress += stage_weights.get('assets', 0.0)

    base_progress = min(base_progress, 1.0)

    if not detailed:
        return base_progress

    sub_progress = 0.0

    # 图像生成细化
    if 'images' in checkpoint and 'images' not in seen:
        images_info = checkpoint['images']
        if 'completed' in images_info and 'total' in images_info:
            total = images_info['total']
            if total > 0:
                sub_progress = stage_weights['images'] * (images_info['completed'] / total)

    # 视频生成细化（仅在图像阶段完成但视频未完成时）
    elif 'videos' in checkpoint and 'videos' not in seen:
        videos_info = checkpoint['videos']
        if 'completed' in videos_info and 'total' in videos_info:
            total = videos_info['total']
            if total > 0:
                sub_progress = stage_weights['videos'] * (videos_info['completed'] / total)

    return min(base_progress + sub_progress, 1.0)


def generate_progress_message(checkpoint: dict) -> str:
    """
    根据checkpoint生成进度消息（5个阶段）

    Args:
        checkpoint: checkpoint字典

    Returns:
        进度消息字符串
    """
    if not checkpoint or 'completed_steps' not in checkpoint:
        return '准备中...'

    completed = checkpoint.get('completed_steps', [])
    stages = checkpoint.get('stages', {})

    # 判断当前阶段（按倒序检查）
    if 'composition' in completed:
        return '✅ 视频成片已完成'
    elif 'audio_subtitle' in completed:
        return '🎬 正在进行音频与合成'
    elif 'videos' in completed:
        return '🎧 正在制作旁白与字幕...'
    elif 'images' in completed:
        videos_info = checkpoint.get('videos', {})
        if 'completed' in videos_info and 'total' in videos_info:
            c = videos_info['completed']
            t = videos_info['total']
            return f'🎥 正在生成视频 ({c}/{t})'
        return '✅ 图像生成完成，准备生成视频'
    elif 'story' in completed:
        images_info = checkpoint.get('images', {})
        if 'completed' in images_info and 'total' in images_info:
            c = images_info['completed']
            t = images_info['total']
            return f'🖼️ 正在生成图像 ({c}/{t})'
        return '✅ 剧本生成完成，准备生成图像'
    elif 'assets' in completed or stages.get('character_reference'):
        return '🧬 正在准备角色与品牌资产...'
    else:
        return '🚀 正在初始化任务...'


# ==================== 结果整理与状态修复 ====================

def locate_final_video(output_dir: Path) -> Optional[Path]:
    """在输出目录中寻找最终视频文件"""
    preferred_paths = [
        output_dir / 'final_video.mp4',
        output_dir / 'final.mp4',
        output_dir / '90_final.mp4',
    ]
    for candidate in preferred_paths:
        if candidate.exists():
            return candidate

    final_candidates = sorted(output_dir.glob("*final*.mp4"))
    if final_candidates:
        return final_candidates[-1]
    return None


def prepare_final_result(job_id: str) -> Optional[str]:
    """
    查找并整理最终视频文件，返回可供前端访问的路径
    """
    output_dir = Path(OUTPUT_DIR) / job_id
    if not output_dir.exists():
        return None

    result_file = locate_final_video(output_dir)
    if not result_file:
        return None

    final_name = f"{job_id}.mp4"
    canonical_path = output_dir / final_name

    try:
        if not canonical_path.exists() or result_file.resolve() != canonical_path.resolve():
            shutil.copy2(result_file, canonical_path)
    except Exception as copy_err:
        print(f"[WARN] 无法生成命名文件 {canonical_path}: {copy_err}")
        canonical_path = result_file

    public_url = None
    if canonical_path.exists():
        try:
            PUBLIC_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            public_target = PUBLIC_EXPORT_DIR / final_name
            need_copy = True
            if public_target.exists():
                need_copy = canonical_path.stat().st_mtime > public_target.stat().st_mtime
            if need_copy:
                shutil.copy2(canonical_path, public_target)
            public_url = f"{PUBLIC_EXPORT_URL.rstrip('/')}/{final_name}"
        except Exception as export_err:
            print(f"[WARN] 无法复制视频到公共存储 {PUBLIC_EXPORT_DIR}: {export_err}")
            public_url = str(canonical_path)

    if public_url:
        return public_url
    if canonical_path.exists():
        return str(canonical_path)
    return str(result_file)


def reconcile_task_states():
    """
    扫描任务列表，修复已完成但状态未更新的任务
    """
    tasks_snapshot = task_manager.list_tasks()
    for task in tasks_snapshot:
        job_id = task.get('job_id')
        if not job_id:
            continue

        status = task.get('status')
        result_path = task.get('result_path')

        if status == 'succeeded' and result_path:
            continue

        final_result = prepare_final_result(job_id)
        if not final_result:
            continue

        task_manager.set_result_path(job_id, final_result)
        if status != 'succeeded':
            task_manager.update_status(job_id, 'succeeded', '视频生成成功（状态自动修复）')
            task_manager.update_progress(job_id, 1.0, '已完成')


def bootstrap_eta_history():
    """基于历史成功任务构建 ETA 样本"""
    global eta_bootstrap_done
    if eta_bootstrap_done:
        return

    try:
        tasks = task_manager.list_tasks()
        tasks_sorted = sorted(
            [task for task in tasks if task.get('status') == 'succeeded'],
            key=lambda item: item.get('created_at', '')
        )
        imported = 0
        for task in tasks_sorted:
            job_id = task.get('job_id')
            if not job_id or eta_estimator.has_record(job_id):
                continue
            config_path = Path(TEMP_DIR) / f"user-{job_id}.yaml"
            log_path = Path(OUTPUT_DIR) / job_id / "log.txt"
            if not config_path.exists() or not log_path.exists():
                continue
            if eta_estimator.record_success(job_id, config_path, log_path):
                imported += 1
        if imported:
            print(f"[INFO] 已导入 {imported} 个历史 ETA 样本")
    except Exception as exc:
        print(f"[WARN] 导入历史 ETA 样本失败: {exc}")
    finally:
        eta_bootstrap_done = True


# ==================== 后台任务执行 ====================

async def run_video_generation(job_id: str, config_file: Path, resume_mode: bool = False):
    """
    后台运行视频生成任务

    Args:
        job_id: 任务 ID
        config_file: 配置文件路径
    """
    global running_tasks

    # 检查并发限制
    while len(running_tasks) >= MAX_CONCURRENT_TASKS:
        await asyncio.sleep(1)

    try:
        # 更新状态为运行中（首阶段是故事脚本生成）
        task_manager.update_status(job_id, 'running', '正在生成故事脚本...')

        # 构建命令
        ad_back_path = Path(__file__).parent / 'ad-back.py'
        log_file = Path(OUTPUT_DIR) / job_id / 'log.txt'

        # 确保输出目录存在
        log_file.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,  # 使用当前 Python 解释器
            str(ad_back_path),
            '--resume', job_id,
            '--config-file', str(config_file),
            '--no-auto-resume'
        ]

        # 启动子进程
        append_existing_log = resume_mode and log_file.exists()
        mode = 'a' if append_existing_log else 'w'
        with open(log_file, mode, encoding='utf-8') as log_f:
            if append_existing_log:
                separator = "=" * 20
                log_f.write(f"\n{separator} 断点续传启动 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {separator}\n")
                log_f.flush()
            process = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                cwd=Path(__file__).parent.parent,  # 项目根目录
                env=os.environ.copy()
            )

        running_tasks[job_id] = process

        # 异步轮询：监控进度并等待完成
        checkpoint_file = Path(OUTPUT_DIR) / job_id / '00_checkpoint.json'
        last_progress = 0.0

        while process.poll() is None:
            # 解析checkpoint文件
            checkpoint = parse_checkpoint_file(checkpoint_file)

            if checkpoint:
                # 计算进度
                progress = calculate_progress_from_checkpoint(checkpoint, detailed=True)
                message = generate_progress_message(checkpoint)

                # 只在进度变化时更新（避免频繁写入）
                if abs(progress - last_progress) >= 0.01:  # 变化超过1%才更新
                    task_manager.update_progress(job_id, progress, message)
                    last_progress = progress

            # 等待下一次检查
            await asyncio.sleep(PROGRESS_POLL_INTERVAL)

        # 获取退出码
        returncode = process.returncode

        # 移除运行记录
        if job_id in running_tasks:
            del running_tasks[job_id]

        # 更新状态
        if returncode == 0:
            # 查找生成的视频文件
            final_result = prepare_final_result(job_id)
            if final_result:
                task_manager.set_result_path(job_id, final_result)
                task_manager.update_status(job_id, 'succeeded', '视频生成成功')
                task_manager.update_progress(job_id, 1.0, '已完成')
                try:
                    eta_estimator.record_success(job_id, config_file, log_file)
                except Exception as eta_err:
                    print(f"[WARN] 记录 ETA 数据失败: {eta_err}")
            else:
                task_manager.update_status(job_id, 'failed', '未找到输出文件')
        else:
            task_manager.update_status(job_id, 'failed', f'生成失败，退出码: {returncode}')

    except Exception as e:
        # 异常处理
        task_manager.update_status(job_id, 'failed', f'执行异常: {str(e)}')

        if job_id in running_tasks:
            del running_tasks[job_id]


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn

    print("🚀 启动 API 服务...")
    print(f"   - Swagger 文档: http://localhost:18000/docs")
    print(f"   - 健康检查: http://localhost:18000/health")
    print()

    uvicorn.run(app, host="0.0.0.0", port=18000)
