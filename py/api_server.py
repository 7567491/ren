"""
AI 视频生成 REST API 服务
提供 Web API 接口，管理任务队列和子进程执行
"""
import os
import sys
import yaml
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from py.services.task_manager import TaskManager

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
task_manager = TaskManager(storage_dir=TEMP_DIR)

# 并发限制（从配置读取）
MAX_CONCURRENT_TASKS = 1
running_tasks = {}  # {job_id: subprocess}

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
    global task_manager, TEMP_DIR
    TEMP_DIR = temp_dir
    task_manager = TaskManager(storage_dir=temp_dir)


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
    job_id: str
) -> dict:
    """
    根据预设参数生成完整配置

    Args:
        topic: 视频主题
        preset_name: 预设名称（如"科技"、"仙侠"等）
        num_shots: 镜头数
        shot_duration: 每镜头时长
        resolution: 分辨率
        llm_provider: LLM提供商（1-DeepSeek 2-Kimi）
        image_model: 图像模型（1-6）
        video_model: 视频模型（1-5）
        voice: 音色选择（1-13）
        concurrent_workers: 并发线程数
        job_id: 任务 ID

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
    if shot_count < 2 or shot_count > 10:
        raise ValueError(f"镜头数 {shot_count} 无效，有效范围: 2-10")

    # 验证分辨率
    valid_resolutions = ['480p', '720p', '1080p']
    if config['resolution'] not in valid_resolutions:
        raise ValueError(f"分辨率 {config['resolution']} 无效，有效值: {valid_resolutions}")


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
                "voice": 1,
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
    voice: Optional[int] = 1

    # 工作流配置
    concurrent_workers: Optional[int] = 6

    # API密钥（前端传递）
    wavespeed_api_key: Optional[str] = None

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


class LogResponse(BaseModel):
    """日志响应"""
    lines: List[str]
    total_lines: int = 0
    eof: bool = True


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

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "running_tasks": len(running_tasks),
        "max_concurrent": MAX_CONCURRENT_TASKS
    }


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
    - **llm_provider**: LLM提供商（1-DeepSeek 2-Kimi）
    - **image_model**: 图像模型（1-6）
    - **video_model**: 视频模型（1-5）
    - **voice**: 配音音色（1-13）

    **工作流配置：**
    - **concurrent_workers**: 并发线程数（1-9）

    **高级模式：**
    - **user_yaml**: 用户自定义 YAML 配置（完整覆盖上述选项）
    """
    try:
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
                user_config = yaml.safe_load(request.user_yaml)
                validate_config(user_config)
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
                voice=request.voice or 1,
                concurrent_workers=request.concurrent_workers or 6,
                job_id=job_id
            )

            # 如果提供了Wavespeed API密钥，添加到配置中
            if request.wavespeed_api_key:
                if 'api' not in config:
                    config['api'] = {}
                config['api']['wavespeed_key'] = request.wavespeed_api_key

            # 验证配置
            validate_config(config)

            # 写入文件
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

        # 添加后台任务执行
        background_tasks.add_task(run_video_generation, job_id, config_file)

        # 返回任务信息
        task = task_manager.get_task(job_id)
        return JobResponse(**task)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@app.get("/api/jobs", response_model=dict)
async def list_jobs():
    """列出所有任务"""
    tasks = task_manager.list_tasks()
    return {
        "jobs": tasks,
        "total": len(tasks)
    }


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """获取任务状态"""
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
    if not checkpoint_file.exists():
        return None

    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def calculate_progress_from_checkpoint(checkpoint: dict, detailed: bool = False) -> float:
    """
    根据checkpoint计算进度

    Args:
        checkpoint: checkpoint字典
        detailed: 是否使用详细进度（考虑子任务）

    Returns:
        进度值 (0.0 - 1.0)
    """
    if not checkpoint or 'completed_steps' not in checkpoint:
        return 0.0

    # 定义步骤权重
    total_steps = ['story', 'images', 'videos', 'composition']
    completed_steps = checkpoint.get('completed_steps', [])

    # 只计数已知步骤
    valid_completed = [s for s in completed_steps if s in total_steps]

    # 基础进度
    base_progress = len(valid_completed) / len(total_steps)

    if not detailed:
        return base_progress

    # 详细进度：考虑子任务
    sub_progress = 0.0
    step_weight = 1.0 / len(total_steps)

    # 如果正在执行图像生成
    if 'images' in checkpoint and 'images' not in valid_completed:
        images_info = checkpoint['images']
        if 'completed' in images_info and 'total' in images_info:
            total = images_info['total']
            if total > 0:
                sub_progress = step_weight * (images_info['completed'] / total)

    # 如果正在执行视频生成
    elif 'videos' in checkpoint and 'videos' not in valid_completed:
        videos_info = checkpoint['videos']
        if 'completed' in videos_info and 'total' in videos_info:
            total = videos_info['total']
            if total > 0:
                sub_progress = step_weight * (videos_info['completed'] / total)

    return min(base_progress + sub_progress, 1.0)


def generate_progress_message(checkpoint: dict) -> str:
    """
    根据checkpoint生成进度消息

    Args:
        checkpoint: checkpoint字典

    Returns:
        进度消息字符串
    """
    if not checkpoint or 'completed_steps' not in checkpoint:
        return '准备中...'

    completed = checkpoint.get('completed_steps', [])

    # 判断当前阶段
    if 'composition' in completed:
        return '✅ 视频合成完成'
    elif 'videos' in completed:
        videos_info = checkpoint.get('videos', {})
        if 'completed' in videos_info and 'total' in videos_info:
            return f'🎬 正在合成视频...'
        return '✅ 视频生成完成，准备合成'
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
        return '✅ 故事生成完成，准备生成图像'
    else:
        return '📝 正在生成故事脚本...'


# ==================== 后台任务执行 ====================

async def run_video_generation(job_id: str, config_file: Path):
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
        # 更新状态为运行中
        task_manager.update_status(job_id, 'running', '正在生成视频...')

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
        with open(log_file, 'w', encoding='utf-8') as log_f:
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

            # 等待2秒后再次检查
            await asyncio.sleep(2)

        # 获取退出码
        returncode = process.returncode

        # 移除运行记录
        if job_id in running_tasks:
            del running_tasks[job_id]

        # 更新状态
        if returncode == 0:
            # 查找生成的视频文件
            output_dir = Path(OUTPUT_DIR) / job_id
            result_file = output_dir / 'final_video.mp4'

            if result_file.exists():
                task_manager.set_result_path(job_id, str(result_file))
                task_manager.update_status(job_id, 'succeeded', '视频生成成功')
                task_manager.update_progress(job_id, 1.0, '已完成')
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
