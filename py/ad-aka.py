#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Akamai AI推理云广告视频生成脚本
使用可配置LLM（DeepSeek/Kimi）生成脚本，WavespeedAI API生成视频和音频
"""

# 配置说明（请勿删除）：
# 1) 加载顺序：`.env` 密钥 → `config.yaml` 全局默认/阈值 → `user.yaml` 用户覆盖；缺省回落上一级。
# 2) `.env` 仅存 API 密钥，不入库；`config.yaml` 维护模型、路径、限流、输出目录等系统默认，不写用户私参。
# 3) `user.yaml` 只改必要的运行参数（主题、镜头数、分辨率、角色/Logo、并发等），保持键名与 `config.yaml` 一致。
# 4) 程序在启动时先 load_dotenv，再读 `config.yaml`，在 main 中读取 `user.yaml`；新增字段请同时补充两份配置示例。


import os
import json
import requests
import time
import sys
import io
import argparse
import subprocess
import queue
import threading
import yaml
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.rate_limiter import RateLimiter
from services.voice_service import VoiceService
from services.subtitle_service import SubtitleService
from services.video_composer import VideoComposer
from services.music_service import MusicService

# YAML配置文件支持（用于user.yaml）
# config.yaml已在前面通过yaml.safe_load()加载

# 设置标准输入输出的编码为UTF-8，宽容处理终端传入的异常字节以避免交互中断
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ============================================================
# 终端颜色定义 (ANSI颜色代码)
# ============================================================
class Colors:
    """终端颜色常量"""
    # 基础颜色
    GREEN = '\033[92m'      # 绿色 - 成功/完成
    YELLOW = '\033[93m'     # 黄色 - 警告/重试
    RED = '\033[91m'        # 红色 - 错误
    GRAY = '\033[90m'       # 灰色 - 等待/无进展
    BLUE = '\033[94m'       # 蓝色 - 信息
    CYAN = '\033[96m'       # 青色 - 进度
    MAGENTA = '\033[95m'    # 品红 - 特殊信息

    # 样式
    BOLD = '\033[1m'        # 粗体
    RESET = '\033[0m'       # 重置所有样式

    @staticmethod
    def strip(text):
        """移除文本中的颜色代码（用于写入日志文件）"""
        import re
        ansi_escape = re.compile(r'\033\[[0-9;]*m')
        return ansi_escape.sub('', text)

# 加载环境变量
load_dotenv()

# 加载YAML配置
CONFIG_FILE = Path(__file__).parent.parent / 'config.yaml'
try:
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        CONFIG = yaml.safe_load(f)
except FileNotFoundError:
    print(f"⚠️ 警告: 配置文件 {CONFIG_FILE} 不存在，使用默认配置")
    CONFIG = {}

WAVESPEED_API_KEY = os.getenv('Wavespeed_API_KEY') or CONFIG.get('api', {}).get('wavespeed_key', '')

# 初始化API限流器
rate_limits = CONFIG.get('rate_limits', {})

# LLM多提供商配置
LLM_CONFIG = CONFIG.get('llm', {})
LLM_PROVIDERS = LLM_CONFIG.get('providers', {})
LLM_NUMBER_MAP = {int(k): v for k, v in (LLM_CONFIG.get('number_map') or {}).items()}
LLM_DEFAULT_PROVIDER = LLM_CONFIG.get('default') or (list(LLM_PROVIDERS.keys())[0] if LLM_PROVIDERS else 'deepseek')
CURRENT_LLM_PROVIDER = LLM_DEFAULT_PROVIDER
LLM_SETTINGS = {}


def get_nested_config(cfg, path):
    value = cfg
    for part in path.split('.'):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value.get(part)
    return value


def resolve_llm_provider(user_choice=None):
    if isinstance(user_choice, int) and user_choice in LLM_NUMBER_MAP:
        return LLM_NUMBER_MAP[user_choice]
    if isinstance(user_choice, str) and user_choice.strip():
        if user_choice in LLM_PROVIDERS:
            return user_choice
        if user_choice.isdigit() and int(user_choice) in LLM_NUMBER_MAP:
            return LLM_NUMBER_MAP[int(user_choice)]
    return LLM_DEFAULT_PROVIDER


def get_llm_api_key(provider_key):
    provider = LLM_PROVIDERS.get(provider_key, {})
    env_name = provider.get('api_key_env')
    if env_name:
        env_value = os.getenv(env_name)
        if env_value:
            return env_value
    config_path = provider.get('api_key_config')
    if config_path:
        nested_value = get_nested_config(CONFIG, config_path)
        if isinstance(nested_value, str) and nested_value.strip():
            return nested_value
    direct = provider.get('api_key')
    if isinstance(direct, str) and direct.strip():
        return direct
    return ''


def init_llm_provider(provider_key):
    global CURRENT_LLM_PROVIDER, LLM_SETTINGS, llm_limiter

    provider = LLM_PROVIDERS.get(provider_key)
    if not provider:
        raise ConfigError(f"未找到LLM提供商配置: {provider_key}")

    api_key = get_llm_api_key(provider_key)
    if not api_key:
        raise ConfigError(f"缺少 {provider.get('name', provider_key)} 的API密钥")

    endpoint = provider.get('endpoint') or provider.get('base_url') or "https://api.deepseek.com/v1/chat/completions"
    model_name = provider.get('model', 'deepseek-chat')
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if provider.get('headers'):
        headers.update(provider.get('headers'))

    CURRENT_LLM_PROVIDER = provider_key
    LLM_SETTINGS = {
        'provider': provider_key,
        'name': provider.get('name', provider_key),
        'endpoint': endpoint,
        'model': model_name,
        'temperature': provider.get('temperature', 0.7),
        'max_tokens': provider.get('max_tokens'),
        'timeout': provider.get('timeout_seconds', 60),
        'headers': headers,
    }

    rl = provider.get('rate_limits') or rate_limits.get(provider_key) or rate_limits.get('deepseek', {})
    llm_limiter = RateLimiter(
        max_requests_per_minute=rl.get('max_requests_per_minute'),
        max_requests_per_day=rl.get('max_requests_per_day'),
        name=f"LLM-{provider_key}"
    )


# 初始化默认LLM提供商，后续会根据user.yaml覆盖
try:
    init_llm_provider(CURRENT_LLM_PROVIDER)
except Exception:
    llm_limiter = RateLimiter(name="LLM")


image_limiter = RateLimiter(
    max_requests_per_minute=rate_limits.get('image_generation', {}).get('max_requests_per_minute'),
    max_requests_per_day=rate_limits.get('image_generation', {}).get('max_requests_per_day'),
    name="图像生成"
)

video_limiter = RateLimiter(
    max_requests_per_minute=rate_limits.get('video_generation', {}).get('max_requests_per_minute'),
    max_requests_per_day=rate_limits.get('video_generation', {}).get('max_requests_per_day'),
    name="视频生成"
)

# 输出目录基础路径
OUTPUT_BASE = Path(CONFIG.get('workflow', {}).get('output_base', './output'))

# 工作目录和日志文件将在 main() 中根据命令行参数初始化
WORK_DIR = None
LOG_FILE = None
RUN_TIMESTAMP = None

# ============================================================
# 自定义异常类
# ============================================================
class VideoGenerationError(Exception):
    """视频生成基础异常"""
    pass

class APIError(VideoGenerationError):
    """API调用错误（可重试）"""
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after

class TaskFailedError(VideoGenerationError):
    """任务执行失败（不应重试）"""
    pass

class ConfigError(VideoGenerationError):
    """配置错误"""
    pass

# ============================================================
# 视觉风格与运镜模板（从配置文件加载）
# ============================================================
STYLE_TEMPLATES = CONFIG.get('visual_styles', {})
CAMERA_MOVEMENTS = CONFIG.get('camera_movements', {})

def get_camera_movement(shot_index, total_shots, scene_summary):
    """根据镜头位置和场景自动分配运镜模式

    Args:
        shot_index: int, 镜头索引（从0开始）
        total_shots: int, 总镜头数
        scene_summary: str, 场景概要（用于判断是否需要对比镜头）

    Returns:
        tuple: (运镜代号, 运镜配置字典)
    """
    # 关键词检测
    is_comparison = any(kw in scene_summary for kw in ['对比', 'vs', 'VS', 'before', 'after', '传统', '人工', '使用前', '使用后'])
    is_architecture = any(kw in scene_summary for kw in ['架构', '数据中心', '全球', '网络', '节点', '俯瞰'])
    is_product = any(kw in scene_summary for kw in ['产品', '界面', '平台', '模型', '展示'])
    # 修复：使用更精确的关键词组合，避免"场景"等常见词误判
    is_multi_scene = any(kw in scene_summary for kw in ['多个场景', '多种场景', '多个应用场景', '功能列表', '产品阵列', '系列产品'])

    # 开场镜头：必用M1（推进特写）
    if shot_index == 0:
        return 'M1', CAMERA_MOVEMENTS['M1']

    # 结尾镜头：必用M5（拉出揭示）
    if shot_index == total_shots - 1:
        return 'M5', CAMERA_MOVEMENTS['M5']

    # 对比场景：必用M6（分屏对比）
    if is_comparison:
        return 'M6', CAMERA_MOVEMENTS['M6']

    # 架构/全局场景：优先M2（俯视展开）
    if is_architecture:
        return 'M2', CAMERA_MOVEMENTS['M2']

    # 产品展示：优先M4（旋转环绕）
    if is_product:
        return 'M4', CAMERA_MOVEMENTS['M4']

    # 多场景并列：优先M3（平移扫过）
    if is_multi_scene:
        return 'M3', CAMERA_MOVEMENTS['M3']

    # 默认：根据位置循环使用M2/M3/M4
    middle_movements = ['M2', 'M3', 'M4']
    movement_code = middle_movements[shot_index % len(middle_movements)]
    return movement_code, CAMERA_MOVEMENTS[movement_code]

# ============================================================
# 用户友好的数字映射配置（用于user.yaml）
# ============================================================
# 风格数字映射（按yaml中的顺序，保持稳定）
STYLE_NUMBER_MAP = {
    1: 'cartoon_adventure',
    2: 'luxury_fashion',
    3: 'ink_xianxia',
    4: 'realistic_3d',
    5: 'cinematic',
    6: 'technology',
    7: 'cyberpunk',
    8: 'space_exploration',
    9: 'outdoor_adventure',
    10: 'magical_fantasy'
}

# 分辨率数字映射
RESOLUTION_NUMBER_MAP = {
    1: '480p',
    2: '720p',
    3: '1080p'
}

# 布尔值数字映射（通用）
BOOL_NUMBER_MAP = {
    0: False,
    1: True
}

# 字幕位置数字映射
POSITION_NUMBER_MAP = {
    1: 'bottom',
    2: 'center',
    3: 'top'
}

# 音色数字映射（从config.yaml加载）
VOICE_CONFIG = CONFIG.get('audio', {}).get('voices', {})
VOICE_NUMBER_MAP = {int(k): v['name'] for k, v in VOICE_CONFIG.items() if isinstance(v, dict) and 'name' in v}

# 运行时配置
RUNTIME_CONFIG = CONFIG.get('runtime', {})
IMAGE_DEFAULTS = RUNTIME_CONFIG.get('image_generation', {})
VIDEO_DEFAULTS = RUNTIME_CONFIG.get('video_generation', {})
POLLING_CONFIG = RUNTIME_CONFIG.get('polling', {})
IMAGE_UPLOAD_CONFIG = RUNTIME_CONFIG.get('image_upload', {})

# 提示词模板
PROMPT_TEMPLATES = CONFIG.get('prompt_templates', {})


def get_prompt(name, **kwargs):
    """从配置获取提示词模板并格式化"""
    template = PROMPT_TEMPLATES.get(name)
    if not template:
        raise ConfigError(f"配置缺少提示词模板: {name}")
    try:
        return template.format(**kwargs)
    except KeyError as e:
        raise ConfigError(f"提示词模板 {name} 缺少变量: {e}")


def require_config(condition, message):
    """配置校验辅助"""
    if not condition:
        raise ConfigError(message)

# ============================================================
# 模型选择配置（从YAML读取）
# ============================================================
# 工作流配置
USE_DIRECT_T2V = CONFIG.get('workflow', {}).get('use_direct_t2v', False)

# 图像生成模型配置（从YAML读取）
IMAGE_MODEL_CONFIG = CONFIG.get('models', {}).get('image', {}).get('available', {})
CURRENT_IMAGE_MODEL = CONFIG.get('models', {}).get('image', {}).get('current', 'seedream-v4')

# 视频生成模型配置（从YAML读取）
VIDEO_MODEL_CONFIG = CONFIG.get('models', {}).get('video', {}).get('available', {})
CURRENT_VIDEO_MODEL = CONFIG.get('models', {}).get('video', {}).get('current', 'wan-2.5-i2v')

# 如果使用直接T2V模式，调整模型选择
if USE_DIRECT_T2V:
    CURRENT_IMAGE_MODEL = None
    # 确保视频模型是t2v类型
    if CURRENT_VIDEO_MODEL not in VIDEO_MODEL_CONFIG or VIDEO_MODEL_CONFIG[CURRENT_VIDEO_MODEL].get('type') != 't2v':
        CURRENT_VIDEO_MODEL = 'wan-2.6-t2v'

# 并发配置（从YAML/TOML读取）
MAX_CONCURRENT_WORKERS = CONFIG.get('workflow', {}).get('concurrent_workers', 2)

# 配置校验
require_config(STYLE_TEMPLATES, "配置缺少视觉风格visual_styles")
require_config(CAMERA_MOVEMENTS, "配置缺少运镜配置camera_movements")
require_config(PROMPT_TEMPLATES, "配置缺少提示词模板prompt_templates")

IMAGE_DURATION = IMAGE_DEFAULTS.get('duration_seconds', 5)
IMAGE_SEED = IMAGE_DEFAULTS.get('seed', -1)
IMAGE_PROMPT_EXPANSION = IMAGE_DEFAULTS.get('enable_prompt_expansion', False)

VIDEO_DURATION_DEFAULT = VIDEO_DEFAULTS.get('duration_seconds', 5)
VIDEO_SEED_DEFAULT = VIDEO_DEFAULTS.get('seed', -1)
VIDEO_PROMPT_EXPANSION = VIDEO_DEFAULTS.get('enable_prompt_expansion', False)

POLLING_INTERVAL = POLLING_CONFIG.get('check_interval_seconds', 10)
MAX_WAIT_IMAGE = POLLING_CONFIG.get('max_wait_seconds', {}).get('image', 120)
MAX_WAIT_VIDEO = POLLING_CONFIG.get('max_wait_seconds', {}).get('video', 600)
MAX_NETWORK_RETRIES = POLLING_CONFIG.get('max_network_retries', 10)
BACKOFF_SECONDS = POLLING_CONFIG.get('backoff_seconds', 5)
MAX_BACKOFF_SECONDS = POLLING_CONFIG.get('max_backoff_seconds', 30)

def log(message, level="INFO"):
    """写入日志并打印（控制台带颜色，文件不带颜色）"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 根据level和消息内容选择颜色
    color = Colors.RESET
    if level == "ERROR" or "❌" in message or "错误" in message:
        color = Colors.RED
    elif level == "WARN" or "⚠️" in message or "警告" in message or "重试" in message:
        color = Colors.YELLOW
    elif level == "SUCCESS" or "✅" in message or "✓" in message or "完成" in message:
        color = Colors.GREEN
    elif "⏳" in message or "等待" in message or "⏱️" in message:
        color = Colors.GRAY
    elif "📊" in message or "进度" in message:
        color = Colors.CYAN
    elif level == "INFO":
        color = Colors.BLUE

    # 控制台输出（带颜色）
    colored_message = f"{color}[{timestamp}] [{level}] {message}{Colors.RESET}"
    print(colored_message)
    sys.stdout.flush()

    # 写入日志文件（不带颜色）
    plain_message = f"[{timestamp}] [{level}] {Colors.strip(message)}"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(plain_message + '\n')


def llm_chat(messages, temperature=None, max_tokens=None, context="LLM调用"):
    if not LLM_SETTINGS:
        raise ConfigError("LLM未初始化")

    payload = {
        "model": LLM_SETTINGS['model'],
        "messages": messages,
        "temperature": temperature if temperature is not None else LLM_SETTINGS.get('temperature', 0.7)
    }

    final_max_tokens = max_tokens or LLM_SETTINGS.get('max_tokens')
    if final_max_tokens:
        payload['max_tokens'] = final_max_tokens

    headers = LLM_SETTINGS['headers']
    llm_limiter.acquire()
    response = requests.post(LLM_SETTINGS['endpoint'], headers=headers, json=payload, timeout=LLM_SETTINGS.get('timeout', 60))
    response.raise_for_status()
    result = response.json()

    if os.getenv('DEBUG') == '1':
        log(f"[DEBUG] {context} 响应: {json.dumps(result, ensure_ascii=False)[:200]}...", "INFO")

    return result['choices'][0]['message']['content'].strip()


def llm_complete(prompt_text, temperature=None, max_tokens=None, context="LLM调用"):
    return llm_chat([{"role": "user", "content": prompt_text}], temperature=temperature, max_tokens=max_tokens, context=context)


def get_video_duration_seconds(video_path):
    """获取视频时长（秒），优先使用MoviePy，失败则回退到ffprobe"""
    try:
        from moviepy import VideoFileClip
        clip = VideoFileClip(str(video_path))
        duration = clip.duration
        clip.close()
        return float(duration or 0.0)
    except Exception:
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(video_path)
                ],
                capture_output=True,
                text=True,
                check=True
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0


def speedup_audio_file(input_path, output_path, speed_factor):
    """使用ffmpeg加速音频（atempo支持0.5-2.0，已限制为<=1.8）"""
    if speed_factor <= 0:
        return False

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(input_path),
                "-filter:a", f"atempo={speed_factor}",
                "-vn",
                str(output_path)
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return True
    except Exception as e:
        log(f"⚠️  音频倍速处理失败: {e}", "WARN")
        return False


def _format_srt_time(seconds: float) -> str:
    """格式化秒为SRT时间戳"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def rescale_srt_timestamps(input_srt, output_srt, scale: float):
    """按比例缩放SRT时间轴"""
    import re
    time_pattern = re.compile(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})")

    def to_seconds(ts: str) -> float:
        h, m, rest = ts.split(":")
        s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

    lines = []
    with open(input_srt, "r", encoding="utf-8") as f:
        for line in f:
            match = time_pattern.search(line)
            if match:
                start = to_seconds(match.group(1)) * scale
                end = to_seconds(match.group(2)) * scale
                lines.append(f"{_format_srt_time(start)} --> {_format_srt_time(end)}\n")
            else:
                lines.append(line)

    with open(output_srt, "w", encoding="utf-8") as f:
        f.writelines(lines)


def write_srt_from_submaker(sub_maker, output_file):
    """将SubMaker生成的字幕写入SRT"""
    if not sub_maker:
        return False
    try:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        srt_content = sub_maker.get_srt()
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(srt_content)
        return True
    except Exception as e:
        log(f"⚠️  写入SRT失败: {e}", "WARN")
        return False


def generate_global_narration(shots_data, video_durations):
    """读取完整旁白文本（阶段2.6已一次性生成）

    优先使用已生成的完整旁白，避免重复生成
    """
    # 从70_narrations.json读取完整旁白
    narrations_file = WORK_DIR / '70_narrations.json'
    if narrations_file.exists():
        try:
            with open(narrations_file, 'r', encoding='utf-8') as f:
                narrations_data = json.load(f)

            # 检查是否是新格式（完整旁白）
            if "global" in narrations_data:
                full_narration = narrations_data["global"]['narration']
                log(f"   ✓ 使用完整旁白（来自阶段2.6）")
                log(f"     旁白字数: {len(full_narration)}字")
                # 返回完整旁白作为单个句子
                return [full_narration]

            # 兼容旧格式（分镜头旁白）
            elif any(str(i) in narrations_data for i in range(1, 20)):
                sentences = []
                for shot in shots_data['shots']:
                    shot_id = str(shot['id'])
                    if shot_id in narrations_data:
                        narration = narrations_data[shot_id]['narration']
                        sentences.append(narration)
                    else:
                        text = shot.get('summary_cn', '') or shot.get('description', '')
                        sentences.append(text.strip()[:50])
                log(f"   ✓ 使用分镜头旁白（旧格式，来自阶段2.6）")
                return sentences

        except Exception as e:
            log(f"   ⚠️  读取旁白文件失败: {e}，使用回退方案", "WARN")

    # 回退方案：从shots_data读取
    sentences = []
    for shot in shots_data['shots']:
        narration = shot.get('narration', '').strip()
        if narration:
            sentences.append(narration)
        else:
            text = shot.get('summary_cn', '') or shot.get('description', '')
            sentences.append(text.strip()[:50])

    log(f"   ✓ 使用旁白（回退方案）")
    return sentences



# ============================================================
# 成本计算辅助函数
# ============================================================
def get_video_cost(model_name, resolution="720p"):
    """获取视频生成的成本（按分辨率）

    Args:
        model_name: 模型名称
        resolution: 分辨率（480p/720p/1080p）

    Returns:
        float: 成本（美元）
    """
    model_config = VIDEO_MODEL_CONFIG.get(model_name, {})

    # 优先使用分辨率定价
    cost_by_resolution = model_config.get('cost_by_resolution', {})
    if resolution in cost_by_resolution:
        return cost_by_resolution[resolution]

    # 回退到基础价格
    return model_config.get('cost', 0.30)

# ============================================================
# 余额查询功能
# ============================================================
def get_wavespeed_balance():
    """查询 WavespeedAI 账户余额

    Returns:
        float: 余额（美元），失败返回 None
    """
    try:
        url = "https://api.wavespeed.ai/api/v3/balance"
        headers = {
            "Authorization": f"Bearer {WAVESPEED_API_KEY}"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        result = response.json()
        # API返回格式: {"code": 200, "message": "success", "data": {"balance": 93.54}}
        # 或者直接: {"balance": 10.5} 或 {"credit": 10.5}
        if 'data' in result and isinstance(result['data'], dict):
            # 嵌套格式
            data = result['data']
            balance = data.get('balance') or data.get('credit') or data.get('amount', 0)
        else:
            # 直接格式
            balance = result.get('balance') or result.get('credit') or result.get('amount', 0)
        return float(balance)

    except requests.exceptions.Timeout:
        log("⚠️  查询余额超时，请检查网络连接", "WARN")
        return None
    except requests.exceptions.RequestException as e:
        log(f"⚠️  查询余额失败: {str(e)}", "WARN")
        return None
    except Exception as e:
        log(f"⚠️  解析余额数据失败: {str(e)}", "WARN")
        return None

def display_balance(before_balance=None, after_balance=None, cost=None, operation="API调用"):
    """显示余额信息

    Args:
        before_balance: 调用前余额
        after_balance: 调用后余额
        cost: API调用成本
        operation: 操作描述
    """
    if after_balance is None:
        return

    print()
    print("=" * 60)
    print(f"💰 账户余额信息 - {operation}")
    print("-" * 60)

    if before_balance is not None and cost is not None:
        actual_cost = before_balance - after_balance
        print(f"   调用前余额: ${before_balance:.4f}")
        print(f"   预计成本:   ${cost:.4f}")
        print(f"   实际成本:   ${actual_cost:.4f}")
        print(f"   调用后余额: ${after_balance:.4f}")

        # 如果实际成本与预计不符，显示警告
        if abs(actual_cost - cost) > 0.001:
            print(f"   ⚠️  实际成本与预计不符，差异: ${abs(actual_cost - cost):.4f}")
    else:
        print(f"   当前余额: ${after_balance:.4f}")

    print("=" * 60)
    print()

def print_welcome():
    """显示欢迎界面"""
    print("=" * 60)
    print("🎬 AI视频生成系统 v2.0（故事化增强版）")
    print("=" * 60)
    print()

def select_style():
    """选择视觉风格"""
    print("📐 请选择视觉风格：")
    print()

    styles = list(STYLE_TEMPLATES.items())
    for i, (key, style) in enumerate(styles, 1):
        print(f"  {i}. {style['name']}")

    print()

    while True:
        try:
            # 动态获取第一个风格作为默认值
            default_style_key = styles[0][0]
            default_style_name = styles[0][1]['name']
            choice = input(f"请输入编号 (1-{len(styles)}，默认1-{default_style_name}): ").strip()
            if not choice:
                return default_style_key

            choice_num = int(choice)
            if 1 <= choice_num <= len(styles):
                selected_key = styles[choice_num - 1][0]
                selected_name = styles[choice_num - 1][1]['name']
                print(f"✅ 已选择: {selected_name}\n")
                return selected_key
            else:
                print(f"❌ 请输入1-{len(styles)}之间的数字")
        except ValueError:
            print("❌ 请输入有效的数字")

def input_number(prompt, default, min_val, max_val):
    """输入数字，带验证"""
    while True:
        try:
            user_input = input(f"{prompt} ({min_val}-{max_val}，默认{default}): ").strip()
            if not user_input:
                print(f"✅ 使用默认值: {default}\n")
                return default

            value = int(user_input)
            if min_val <= value <= max_val:
                print(f"✅ 已设置: {value}\n")
                return value
            else:
                print(f"{Colors.RED}❌ 请输入{min_val}-{max_val}之间的数字{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}❌ 请输入有效的数字{Colors.RESET}")

def load_config_from_yaml(config_path='user.yaml'):
    """从YAML配置文件加载用户配置

    Args:
        config_path: 配置文件路径，默认为 user.yaml

    Returns:
        tuple: (user_config, concurrent_workers) 或 None
    """
    # 如果是相对路径，相对于项目根目录（脚本所在目录的父目录）
    config_file = Path(config_path)
    if not config_file.is_absolute():
        # 获取项目根目录（py脚本所在目录的父目录）
        project_root = Path(__file__).parent.parent
        config_file = project_root / config_path

    if not config_file.exists():
        return None

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        print(f"\n✅ 已从 {config_path} 加载配置\n")

        # 验证必需字段
        required_fields = ['topic', 'style', 'shot_count', 'shot_duration', 'resolution']
        for field in required_fields:
            if field not in config_data:
                print(f"❌ 配置文件缺少必需字段: {field}")
                return None

        # ========== 数字映射转换（用户友好配置） ==========
        # 转换风格：支持数字（1-10）或字符串（tech_product等）
        if isinstance(config_data['style'], int):
            if config_data['style'] in STYLE_NUMBER_MAP:
                original_num = config_data['style']
                config_data['style'] = STYLE_NUMBER_MAP[config_data['style']]
                print(f"   🔢 风格数字 {original_num} → {config_data['style']}")
            else:
                print(f"❌ 无效的风格编号: {config_data['style']}")
                print(f"   可选编号: 1-{len(STYLE_NUMBER_MAP)} (1=科技产品, 2=时尚奢华...)")
                return None

        # 转换分辨率：支持数字（1-3）或字符串（480p等）
        if isinstance(config_data['resolution'], int):
            if config_data['resolution'] in RESOLUTION_NUMBER_MAP:
                original_num = config_data['resolution']
                config_data['resolution'] = RESOLUTION_NUMBER_MAP[config_data['resolution']]
                print(f"   🔢 分辨率数字 {original_num} → {config_data['resolution']}")
            else:
                print(f"❌ 无效的分辨率编号: {config_data['resolution']}")
                print(f"   可选编号: 1=480p, 2=720p, 3=1080p")
                return None

        # 验证风格是否有效
        if config_data['style'] not in STYLE_TEMPLATES:
            print(f"❌ 无效的视觉风格: {config_data['style']}")
            print(f"   可选值: {', '.join(STYLE_TEMPLATES.keys())}")
            return None

        # 验证数值范围
        if not (2 <= config_data['shot_count'] <= 10):
            print(f"❌ 镜头数量必须在 2-10 之间，当前值: {config_data['shot_count']}")
            return None

        if not (3 <= config_data['shot_duration'] <= 5):
            print(f"❌ 每镜头时长必须在 3-5秒 之间，当前值: {config_data['shot_duration']}")
            return None

        if config_data['resolution'] not in ['480p', '720p', '1080p']:
            print(f"❌ 无效的分辨率: {config_data['resolution']}")
            print(f"   可选值: 480p, 720p, 1080p")
            return None

        # 构建配置字典
        user_config = {
            'topic': config_data['topic'],
            'style': config_data['style'],
            'shot_count': config_data['shot_count'],
            'shot_duration': config_data['shot_duration'],
            'resolution': config_data['resolution'],
            'timestamp': RUN_TIMESTAMP
        }

        # 处理主角配置
        character = config_data.get('character', {})
        # 转换布尔值：支持数字（0/1）或布尔值（true/false）
        if 'enabled' in character and isinstance(character['enabled'], int):
            character['enabled'] = BOOL_NUMBER_MAP.get(character['enabled'], False)

        if character.get('enabled', False):
            # 优先级：character_image > default_character_image > description生成
            has_image = character.get('character_image')
            has_description = character.get('description', '').strip()

            # 如果没有明确指定character_image，尝试使用默认图片
            if not has_image:
                default_image = character.get('default_character_image')
                if default_image:
                    # 如果是 URL，直接使用；如果是本地文件，检查是否存在
                    if default_image.startswith(('http://', 'https://')):
                        print(f"   将使用默认主角参考图（URL）: {default_image}")
                        has_image = default_image
                    elif Path(default_image).exists():
                        print(f"   将使用默认主角参考图（本地）: {default_image}")
                        has_image = default_image
                    else:
                        print(f"   ⚠️  默认图片不存在: {default_image}，将使用description生成")

            # 如果仍然没有图片，必须有description用于生成
            if not has_image and not has_description:
                print("❌ 启用主角一致性时必须提供以下之一：")
                print("   1. character_image（明确指定图片）")
                print("   2. default_character_image（默认图片）")
                print("   3. description（用于AI生成）")
                return None

            user_config['character'] = {
                'enabled': True,
                'description': character.get('description', '主角角色'),
                'character_image': has_image,
                'reference': None,
                'dna': None
            }
        else:
            user_config['character'] = {'enabled': False}

        # 处理品牌配置
        brand = config_data.get('brand', {})
        # 转换布尔值：支持数字（0/1）或布尔值（true/false）
        if 'enabled' in brand and isinstance(brand['enabled'], int):
            brand['enabled'] = BOOL_NUMBER_MAP.get(brand['enabled'], False)

        if brand.get('enabled', False):
            if not brand.get('name', '').strip():
                print("❌ 启用品牌logo时必须提供 name")
                return None
            user_config['brand'] = {
                'enabled': True,
                'name': brand['name'],
                'logo_image': brand.get('logo_image'),
                'default_logo_image': brand.get('default_logo_image', './resource/logo/aka.jpg'),
                'description': brand.get('description', '')
            }
        else:
            user_config['brand'] = {'enabled': False}

        # 处理字幕配置（可选）
        subtitle = config_data.get('subtitle', {})
        if subtitle:
            # 转换字幕位置：支持数字（1-3）或字符串（bottom等）
            position = subtitle.get('position', 'bottom')
            if isinstance(position, int):
                position = POSITION_NUMBER_MAP.get(position, 'bottom')

            user_config['subtitle'] = {
                'font_size': subtitle.get('font_size', 24),
                'font_color': subtitle.get('font_color', 'white'),
                'outline_color': subtitle.get('outline_color', 'black'),
                'outline_width': subtitle.get('outline_width', 2),
                'position': position
            }

        # 处理音频配置（可选）
        audio = config_data.get('audio', {})
        if audio:
            # 转换音色：支持数字（1-13）或字符串（zh-CN-XiaoxiaoNeural等）
            voice = audio.get('voice', 1)
            if isinstance(voice, int):
                if voice in VOICE_NUMBER_MAP:
                    voice_name = VOICE_NUMBER_MAP[voice]
                    voice_desc = VOICE_CONFIG.get(voice, {}).get('description', voice_name)
                    print(f"   🔢 音色数字 {voice} → {voice_desc}")
                    user_config['audio'] = {'voice_name': voice_name}
                else:
                    print(f"❌ 无效的音色编号: {voice}")
                    print(f"   可选编号: 1-{len(VOICE_NUMBER_MAP)} (1=晓晓, 6=云扬...)")
                    return None
            else:
                # 字符串格式，直接使用
                user_config['audio'] = {'voice_name': voice}

        # 处理并发配置
        workflow = config_data.get('workflow', {})
        concurrent_workers = workflow.get('concurrent_workers', 2)

        # 转换自动确认：支持数字（0/1）或布尔值（true/false）
        auto_confirm = workflow.get('auto_confirm', True)
        if isinstance(auto_confirm, int):
            auto_confirm = BOOL_NUMBER_MAP.get(auto_confirm, True)

        if not (1 <= concurrent_workers <= 9):
            print(f"❌ 并发线程数必须在 1-9 之间，当前值: {concurrent_workers}")
            return None

        # 处理 LLM 提供商配置
        llm_data = config_data.get('llm', {})
        if llm_data and 'provider' in llm_data:
            llm_choice = llm_data['provider']
            # 解析数字或字符串
            llm_provider_key = resolve_llm_provider(llm_choice)
            # 初始化 LLM 提供商
            try:
                init_llm_provider(llm_provider_key)
                print(f"   🤖 LLM提供商: {LLM_SETTINGS.get('name', llm_provider_key)}")
            except Exception as e:
                print(f"❌ LLM提供商初始化失败: {e}")
                return None

        # 处理多模态模型配置（图像和视频）
        models_data = config_data.get('models', {})
        if models_data:
            global CURRENT_IMAGE_MODEL, CURRENT_VIDEO_MODEL

            # 处理图像模型
            if 'image' in models_data:
                image_choice = models_data['image']
                image_number_map = CONFIG.get('models', {}).get('image', {}).get('number_map', {})

                # 支持数字或字符串
                if isinstance(image_choice, int) and image_choice in image_number_map:
                    CURRENT_IMAGE_MODEL = image_number_map[image_choice]
                    print(f"   🖼️  图像模型: {image_choice} → {CURRENT_IMAGE_MODEL}")
                elif isinstance(image_choice, str):
                    CURRENT_IMAGE_MODEL = image_choice
                    print(f"   🖼️  图像模型: {CURRENT_IMAGE_MODEL}")

            # 处理视频模型
            if 'video' in models_data:
                video_choice = models_data['video']
                video_number_map = CONFIG.get('models', {}).get('video', {}).get('number_map', {})

                # 支持数字或字符串
                if isinstance(video_choice, int) and video_choice in video_number_map:
                    CURRENT_VIDEO_MODEL = video_number_map[video_choice]
                    print(f"   🎬 视频模型: {video_choice} → {CURRENT_VIDEO_MODEL}")
                elif isinstance(video_choice, str):
                    CURRENT_VIDEO_MODEL = video_choice
                    print(f"   🎬 视频模型: {CURRENT_VIDEO_MODEL}")

                # 验证视频模型参数约束
                if CURRENT_VIDEO_MODEL in VIDEO_MODEL_CONFIG:
                    model_cfg = VIDEO_MODEL_CONFIG[CURRENT_VIDEO_MODEL]
                    constraints = model_cfg.get('constraints', {})

                    # 验证分辨率
                    if 'resolution_options' in constraints:
                        valid_resolutions = constraints['resolution_options']
                        if user_config['resolution'] not in valid_resolutions:
                            print(f"   ⚠️  {CURRENT_VIDEO_MODEL}不支持{user_config['resolution']}，支持的分辨率: {valid_resolutions}")
                            # 自动调整到最接近的分辨率
                            if '720p' in valid_resolutions:
                                user_config['resolution'] = '720p'
                            elif valid_resolutions:
                                user_config['resolution'] = valid_resolutions[0]
                            print(f"   ✓ 已自动调整为: {user_config['resolution']}")

                    # 验证时长
                    if constraints.get('duration_type') == 'fixed':
                        valid_durations = constraints.get('duration_options', [])
                        if user_config['shot_duration'] not in valid_durations:
                            print(f"   ⚠️  {CURRENT_VIDEO_MODEL}仅支持固定时长: {valid_durations}秒")
                            # 选择最接近的时长
                            closest = min(valid_durations, key=lambda x: abs(x - user_config['shot_duration']))
                            user_config['shot_duration'] = closest
                            print(f"   ✓ 已自动调整为: {user_config['shot_duration']}秒")
                    elif constraints.get('duration_type') == 'range':
                        duration_range = constraints.get('duration_range', [3, 10])
                        if user_config['shot_duration'] < duration_range[0] or user_config['shot_duration'] > duration_range[1]:
                            print(f"   ⚠️  {CURRENT_VIDEO_MODEL}时长范围: {duration_range[0]}-{duration_range[1]}秒")
                            user_config['shot_duration'] = max(duration_range[0], min(duration_range[1], user_config['shot_duration']))
                            print(f"   ✓ 已自动调整为: {user_config['shot_duration']}秒")

        # 显示配置摘要
        print("=" * 60)
        print("📋 配置摘要")
        print("=" * 60)
        print(f"  主题: {user_config['topic']}")
        print(f"  风格: {STYLE_TEMPLATES[user_config['style']]['name']}")
        print(f"  镜头数: {user_config['shot_count']}个")
        print(f"  单镜头时长: {user_config['shot_duration']}秒")
        print(f"  分辨率: {user_config['resolution']}")
        if user_config['character']['enabled']:
            print(f"  主角: {user_config['character']['description'][:40]}...")
            if user_config['character'].get('character_image'):
                print(f"  主角参考图: {user_config['character']['character_image']}")
        if user_config['brand']['enabled']:
            print(f"  品牌: {user_config['brand']['name']} logo")
            if user_config['brand'].get('logo_image'):
                print(f"  Logo参考图: {user_config['brand']['logo_image']}")
        if user_config.get('audio', {}).get('voice_name'):
            voice_name = user_config['audio']['voice_name']
            # 查找音色描述
            voice_desc = voice_name
            for v_info in VOICE_CONFIG.values():
                if isinstance(v_info, dict) and v_info.get('name') == voice_name:
                    voice_desc = v_info.get('description', voice_name)
                    break
            print(f"  旁白音色: {voice_desc}")
        if LLM_SETTINGS:
            print(f"  故事生成LLM: {LLM_SETTINGS.get('name', CURRENT_LLM_PROVIDER)}")
        # 显示多模态模型选择
        if CURRENT_IMAGE_MODEL:
            image_config = IMAGE_MODEL_CONFIG.get(CURRENT_IMAGE_MODEL, {})
            print(f"  图像模型: {CURRENT_IMAGE_MODEL} (${image_config.get('cost', 0)}, {image_config.get('quality', 'N/A')})")
        if CURRENT_VIDEO_MODEL:
            video_config = VIDEO_MODEL_CONFIG.get(CURRENT_VIDEO_MODEL, {})
            print(f"  视频模型: {CURRENT_VIDEO_MODEL} (${video_config.get('cost', 0)}, {video_config.get('quality', 'N/A')})")
        print(f"  并发线程数: {concurrent_workers}")
        print(f"  预计总时长: {user_config['shot_count'] * 3}秒（每镜头剪辑为3秒）")
        print("=" * 60)

        # 询问确认（如果未设置自动确认）
        if not auto_confirm:
            confirm = input("\n确认开始生成? (y/n，默认y): ").strip().lower()
            if confirm and confirm != 'y':
                print("❌ 已取消")
                sys.exit(0)

        print("✅ 开始生成...\n")

        return user_config, concurrent_workers

    except Exception as e:
        # 捕获所有YAML解析错误和其他异常
        if 'YAML' in str(type(e).__name__) or 'yaml' in str(type(e).__name__).lower():
            print(f"{Colors.RED}❌ YAML配置文件解析错误: {e}{Colors.RESET}")
        else:
            print(f"{Colors.RED}❌ 加载配置文件时出错: {e}{Colors.RESET}")
        return None

def interactive_setup():
    """交互式配置向导"""
    print_welcome()

    # 1. 输入主题
    print("💡 视频主题")
    topic = input("请输入视频主题（如：Akamai推出AI推理云）: ").strip()
    while not topic:
        topic = input("⚠️  主题不能为空，请重新输入: ").strip()
    print(f"✅ 主题: {topic}\n")

    # 2. 选择风格
    style = select_style()

    # 3. 配置镜头数
    shot_count = input_number("📹 镜头数量", default=2, min_val=2, max_val=10)

    # 4. 配置时长
    duration = input_number("⏱️  每镜头时长(秒)", default=5, min_val=3, max_val=5)

    # 5. 选择分辨率
    print("📺 视频分辨率")
    print("  1. 480p (较快，成本低)")
    print("  2. 720p (推荐，平衡)")
    print("  3. 1080p (高清，较慢)")
    print()

    resolution_map = {
        1: "480p",
        2: "720p",
        3: "1080p"
    }

    while True:
        try:
            res_choice = input("请选择分辨率 (1-3，默认1-480p): ").strip()
            if not res_choice:
                resolution = "480p"
                print(f"✅ 使用默认: {resolution}\n")
                break

            res_num = int(res_choice)
            if 1 <= res_num <= 3:
                resolution = resolution_map[res_num]
                print(f"✅ 已选择: {resolution}\n")
                break
            else:
                print("❌ 请输入1-3之间的数字")
        except ValueError:
            print("❌ 请输入有效的数字")

    # 6. 主角配置（一致性保障）
    print("=" * 60)
    print("👤 主角一致性配置（可选）")
    print("=" * 60)
    print("提示：如果需要所有镜头使用同一个主角，请在此配置")
    print()

    character_config = {'enabled': False}

    has_character = input("是否需要固定主角形象? (y/n，默认n): ").strip().lower()
    if has_character == 'y':
        character_desc = input("请详细描述主角外观（中文）: ").strip()
        while not character_desc:
            character_desc = input("⚠️  描述不能为空，请重新输入: ").strip()

        character_config = {
            'enabled': True,
            'description': character_desc,
            'reference': None,  # 稍后生成
            'dna': None         # 稍后生成
        }
        print(f"✅ 主角: {character_desc[:50]}...\n")
    else:
        print("⏭️  跳过主角配置\n")

    # 7. 品牌配置（logo叠加）
    print("=" * 60)
    print("🏢 品牌元素配置（可选）")
    print("=" * 60)
    print("提示：系统会在每个镜头右下角添加品牌logo水印")
    print()

    brand_config = {'enabled': False}

    has_brand = input("是否需要添加品牌logo? (y/n，默认y): ").strip().lower()
    if not has_brand or has_brand == 'y':
        brand_name = input("品牌名称（如Akamai）: ").strip()
        if brand_name:
            brand_config = {
                'enabled': True,
                'name': brand_name
            }
            print(f"✅ 品牌: {brand_name}\n")
        else:
            print("⏭️  品牌名称为空，跳过\n")
    else:
        print("⏭️  跳过品牌配置\n")

    # 8. 确认配置
    print("=" * 60)
    print("📋 配置确认")
    print("=" * 60)
    print(f"  主题: {topic}")
    print(f"  风格: {STYLE_TEMPLATES[style]['name']}")
    print(f"  镜头数: {shot_count}个")
    print(f"  单镜头时长: {duration}秒")
    print(f"  分辨率: {resolution}")
    if character_config['enabled']:
        print(f"  主角: {character_config['description'][:40]}...")
    if brand_config['enabled']:
        print(f"  品牌: {brand_config['name']} logo")
    print(f"  预计总时长: {shot_count * 3}秒（每镜头剪辑为3秒）")
    print("=" * 60)

    confirm = input("\n确认开始生成? (y/n，默认y): ").strip().lower()
    if confirm and confirm != 'y':
        print("❌ 已取消")
        sys.exit(0)

    print("✅ 开始生成...\n")

    return {
        'topic': topic,
        'style': style,
        'shot_count': shot_count,
        'shot_duration': duration,
        'resolution': resolution,
        'character': character_config,
        'brand': brand_config,
        'timestamp': RUN_TIMESTAMP
    }

def ask_concurrent_workers():
    """询问用户选择并发线程数

    Returns:
        int: 用户选择的并发线程数（3-9）
    """
    print("\n" + "=" * 60)
    print("⚙️  并发设置")
    print("=" * 60)
    print("视频生成支持并发加速，请选择并发线程数：")
    print("  • 3线程（推荐）- 稳定可靠，极少限流")
    print("  • 5线程 - 更快，偶尔可能触发限流")
    print("  • 7-9线程 - 最快，限流风险较高")
    print()

    while True:
        try:
            choice = input("请输入并发线程数 [3-9，默认3]: ").strip()

            # 默认值
            if not choice:
                return 3

            workers = int(choice)
            if 3 <= workers <= 9:
                print(f"\n{Colors.GREEN}✓ 已设置并发线程数: {workers}{Colors.RESET}")
                return workers
            else:
                print(f"{Colors.RED}❌ 请输入3-9之间的数字{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}❌ 无效输入，请输入数字{Colors.RESET}")
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}⚠️  用户取消，使用默认值: 3{Colors.RESET}")
            return 3

def validate_config():
    """验证配置和环境

    Raises:
        ValueError: 配置缺失或无效
    """
    errors = []

    # 检查API密钥
    default_llm = resolve_llm_provider()
    llm_key = get_llm_api_key(default_llm)
    if not llm_key:
        errors.append(f"缺少 {default_llm} 的API密钥 (可在环境变量或 config.yaml 配置)")

    if not WAVESPEED_API_KEY:
        errors.append("缺少环境变量 Wavespeed_API_KEY")

    # 检查模型配置
    if not USE_DIRECT_T2V and CURRENT_IMAGE_MODEL not in IMAGE_MODEL_CONFIG:
        errors.append(f"无效的图像模型: {CURRENT_IMAGE_MODEL}")

    if CURRENT_VIDEO_MODEL not in VIDEO_MODEL_CONFIG:
        errors.append(f"无效的视频模型: {CURRENT_VIDEO_MODEL}")

    # 检查输出目录权限
    if not WORK_DIR.exists():
        try:
            WORK_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"无法创建输出目录 {WORK_DIR}: {e}")

    if not os.access(WORK_DIR, os.W_OK):
        errors.append(f"输出目录不可写: {WORK_DIR}")

    # 检查必需的依赖
    try:
        import imageio_ffmpeg
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        if not Path(ffmpeg_bin).exists():
            errors.append("FFmpeg 不可用")
    except Exception as e:
        errors.append(f"FFmpeg 检查失败: {e}")

    if errors:
        error_msg = "❌ 配置验证失败:\n" + "\n".join(f"  • {e}" for e in errors)
        raise ValueError(error_msg)

    print("✅ 配置验证通过")

def smart_retry(max_attempts=3, backoff_factor=2, max_backoff=60):
    """智能重试装饰器，使用指数退避策略

    Args:
        max_attempts: 最大尝试次数
        backoff_factor: 退避因子
        max_backoff: 最大退避时间（秒）
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except TaskFailedError:
                    # 任务失败，不重试
                    raise

                except APIError as e:
                    # API错误，使用自定义的重试时间
                    last_exception = e
                    if attempt < max_attempts:
                        wait_time = e.retry_after or min(backoff_factor ** attempt, max_backoff)
                        log(f"   ⚠️  API错误 (尝试 {attempt}/{max_attempts}): {e}", "WARN")
                        log(f"   ⏰ {wait_time}秒后重试...")
                        time.sleep(wait_time)
                    else:
                        log(f"   ❌ API错误，已达最大重试次数", "ERROR")

                except requests.exceptions.RequestException as e:
                    # 网络错误，使用指数退避
                    last_exception = e
                    if attempt < max_attempts:
                        wait_time = min(backoff_factor ** attempt, max_backoff)
                        log(f"   ⚠️  网络错误 (尝试 {attempt}/{max_attempts}): {e}", "WARN")
                        log(f"   ⏰ {wait_time}秒后重试...")
                        time.sleep(wait_time)
                    else:
                        log(f"   ❌ 网络错误，已达最大重试次数", "ERROR")

                except Exception as e:
                    # 其他未知错误，不重试
                    log(f"   ❌ 未知错误: {type(e).__name__}: {e}", "ERROR")
                    raise

            # 所有重试都失败
            raise last_exception

        return wrapper
    return decorator

def load_checkpoint():
    """加载检查点文件

    Returns:
        dict: 包含阶段进度和镜头完成情况的字典
    """
    checkpoint_file = WORK_DIR / '00_checkpoint.json'
    default_checkpoint = {
        'stages': {
            'character_reference': False,    # 参考图生成
            'story_outline': False,          # 故事大纲
            'narration_framework': False,    # 广告词框架
            'shots_script': False,           # 分镜脚本
            'images_generated': False,       # 所有图像生成完成
            'videos_generated': False,       # 所有视频生成完成
            'brand_elements': False,         # 品牌元素添加
            'narrations_generated': False,   # 旁白生成
            'audio_subtitle': False,         # 整条旁白与字幕
            'final_composition': False       # 最终合成
        },
        'completed_shots': [],
        'failed_shots': []
    }

    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 兼容旧版checkpoint，合并stages字段
                if 'stages' not in data:
                    data['stages'] = default_checkpoint['stages']
                else:
                    # 补齐缺失的阶段
                    for stage in default_checkpoint['stages']:
                        if stage not in data['stages']:
                            data['stages'][stage] = False
                return data
        except Exception as e:
            log(f"⚠️  加载检查点失败: {e}，将从头开始", "WARN")
            return default_checkpoint
    return default_checkpoint

def save_checkpoint(checkpoint):
    """保存检查点文件

    Args:
        checkpoint: dict, 包含stages(阶段进度), completed_shots和failed_shots
    """
    checkpoint_file = WORK_DIR / '00_checkpoint.json'
    checkpoint['last_update'] = datetime.now().isoformat()
    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log(f"⚠️  保存检查点失败: {e}", "WARN")

def find_latest_task_dir():
    """查找最新的任务目录

    Returns:
        Path or None: 最新的任务目录，如果没有则返回None
    """
    if not OUTPUT_BASE.exists():
        return None

    # 获取所有 aka-* 目录
    task_dirs = [d for d in OUTPUT_BASE.iterdir()
                 if d.is_dir() and d.name.startswith('aka-')]

    if not task_dirs:
        return None

    # 按名称排序（时间戳格式保证了字母序=时间序）
    return sorted(task_dirs)[-1]

def check_task_completeness(task_dir):
    """检查任务完整性

    Args:
        task_dir: Path, 任务目录

    Returns:
        dict: {
            'complete': bool,     # 是否完整
            'script': bool,       # 是否有脚本
            'images': (int, int), # (已完成数, 总数)
            'videos': (int, int), # (已完成数, 总数)
            'final': bool         # 是否有最终视频
        }
    """
    result = {
        'complete': False,
        'script': False,
        'images': (0, 0),
        'videos': (0, 0),
        'final': False
    }

    # 检查脚本文件
    script_file = task_dir / '22_shots_script.json'
    if script_file.exists():
        result['script'] = True

        # 读取镜头数量
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                shot_count = len(data.get('shots', []))

                # 检查图像
                image_count = sum(1 for i in range(1, shot_count + 1)
                                if (task_dir / f'{30 + (i - 1):02d}_shot_{i:02d}_image.png').exists())
                result['images'] = (image_count, shot_count)

                # 检查视频
                video_count = sum(1 for i in range(1, shot_count + 1)
                                if (task_dir / f'{50 + (i - 1):02d}_shot_{i:02d}.mp4').exists())
                result['videos'] = (video_count, shot_count)
        except Exception:
            pass

    # 检查最终视频
    if (task_dir / '90_final.mp4').exists():
        result['final'] = True

    # 判断是否完整（有脚本且有最终视频即为完整）
    if result['script'] and result['final']:
        result['complete'] = True

    return result

def auto_resume_check():
    """自动检查是否需要断点继续

    Returns:
        Path or None: 如果需要继续，返回任务目录；否则返回None
    """
    latest_dir = find_latest_task_dir()

    if not latest_dir:
        print(f"{Colors.BLUE}✨ 没有检测到之前的任务，开始新任务{Colors.RESET}\n")
        return None

    completeness = check_task_completeness(latest_dir)

    if completeness['complete']:
        print(f"{Colors.GREEN}✅ 最近的任务 {latest_dir.name} 已完成，开始新任务{Colors.RESET}\n")
        return None

    # 任务未完成，显示详情
    print(f"\n{Colors.CYAN}📂 检测到未完成的任务: {latest_dir.name}{Colors.RESET}")
    print("─" * 60)

    if completeness['script']:
        print(f"{Colors.GREEN}   ✓ 故事脚本已生成{Colors.RESET}")
    else:
        print(f"{Colors.GRAY}   ✗ 故事脚本未生成{Colors.RESET}")

    if completeness['images'][1] > 0:
        img_done, img_total = completeness['images']
        if img_done == img_total:
            print(f"{Colors.GREEN}   ✓ 图像: {img_done}/{img_total} 已完成{Colors.RESET}")
        elif img_done > 0:
            print(f"{Colors.YELLOW}   ⚠️  图像: {img_done}/{img_total} 已完成{Colors.RESET}")
        else:
            print(f"{Colors.GRAY}   ✗ 图像: {img_done}/{img_total} 已完成{Colors.RESET}")

    if completeness['videos'][1] > 0:
        vid_done, vid_total = completeness['videos']
        if vid_done == vid_total:
            print(f"{Colors.GREEN}   ✓ 视频: {vid_done}/{vid_total} 已完成{Colors.RESET}")
        elif vid_done > 0:
            print(f"{Colors.YELLOW}   ⚠️  视频: {vid_done}/{vid_total} 已完成{Colors.RESET}")
        else:
            print(f"{Colors.GRAY}   ✗ 视频: {vid_done}/{vid_total} 已完成{Colors.RESET}")

    if completeness['final']:
        print(f"{Colors.GREEN}   ✓ 最终视频已生成{Colors.RESET}")
    else:
        print(f"{Colors.GRAY}   ✗ 最终视频未生成{Colors.RESET}")

    print("─" * 60)

    # 询问用户
    try:
        response = input("\n是否从断点继续？(y/n) [默认: y]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n\n⚠️  用户中断")
        return None

    if response in ['', 'y', 'yes', '是']:
        return latest_dir
    else:
        print("✨ 开始新任务\n")
        return None

def parse_api_response(response_json, context="API调用"):
    """解析API响应，统一处理不同格式

    Args:
        response_json: API返回的JSON对象
        context: 调用上下文，用于日志

    Returns:
        dict: 解析后的数据字典

    Raises:
        ValueError: 响应格式无效
    """
    # 调试：打印原始响应（仅在DEBUG模式）
    if os.getenv('DEBUG') == '1':
        log(f"   [DEBUG] {context} 原始响应: {json.dumps(response_json, ensure_ascii=False)[:200]}...")

    # 处理嵌套格式：{"code": 200, "data": {...}}
    if 'code' in response_json:
        if response_json.get('code') != 200:
            error_msg = response_json.get('message', '未知错误')
            raise APIError(f"API返回错误: {error_msg}")

        # 解包data字段
        if 'data' in response_json:
            return response_json['data']
        else:
            # 某些API只有code和message，没有data
            return response_json

    # 扁平格式：直接返回
    return response_json

def validate_task_id(task_id, context="任务"):
    """验证任务ID有效性

    Args:
        task_id: 任务ID
        context: 上下文描述

    Raises:
        APIError: task_id无效
    """
    if not task_id or task_id == 'None' or not isinstance(task_id, str):
        raise APIError(f"{context}ID无效: {task_id}，请检查API响应格式")

def show_progress_bar(current, total, label="进度"):
    """显示进度信息（不使用\\r，直接输出）"""
    percent = int(current / total * 100)
    log(f"   {label}: {current}/{total} ({percent}%)")

# ============================================================
# 一致性保障系统（Consistency Assurance System）
# ============================================================

def generate_character_reference(character_description_cn):
    """生成主角参考图（用于一致性保障）

    Args:
        character_description_cn: str, 用户输入的中文角色描述

    Returns:
        str: 生成的参考图URL
    """
    log("")
    log("="*60)
    log("👤 阶段0: 生成主角参考图（AI自动生成）")
    log("="*60)

    # 翻译为英文prompt
    translation_prompt = get_prompt(
        'character_translation',
        description_cn=character_description_cn
    )

    log("📝 翻译角色描述为英文prompt...")

    color_parts = [c.strip() for c in style_template.get('color_palette', '').split(',') if c.strip()]
    primary_color_1 = color_parts[0] if color_parts else ''
    primary_color_2 = color_parts[1] if len(color_parts) > 1 else primary_color_1

    prompt = get_prompt(
        'story_outline',
        shot_count=config['shot_count'],
        topic=config['topic'],
        style_name=style_template['name'],
        visual_style=style_template['visual_style'],
        color_palette=style_template['color_palette'],
        primary_color_1=primary_color_1,
        primary_color_2=primary_color_2,
        mood=style_template.get('mood', '')
    )

    shot_summaries = "\n".join([f"{i+1}. {beat['scene_summary']} - {beat['key_action']}" for i, beat in enumerate(outline['shot_breakdown'])])

    prompt = get_prompt(
        'narration_framework',
        topic=config['topic'],
        title=outline.get('title', 'N/A'),
        theme=outline.get('theme', 'N/A'),
        total_duration=total_duration,
        shot_count=config['shot_count'],
        shot_duration=shot_duration,
        chars_per_second=CHARS_PER_SECOND,
        shot_summaries=shot_summaries
    )

    reference_note = "注意：用户已提供参考图片，此描述将与参考图配合使用，请提供详细文字特征以增强一致性。" if has_reference_image else ""

    dna_prompt = get_prompt(
        'character_dna',
        description_cn=description,
        prompt_en=character_ref.get('prompt_en', description),
        reference_note=reference_note
    )

    try:
        english_prompt = llm_complete(translation_prompt, temperature=0.3, context="主角描述翻译")

        # 移除可能的引号
        if english_prompt.startswith('"') and english_prompt.endswith('"'):
            english_prompt = english_prompt[1:-1]

        log(f"✅ 英文prompt: {english_prompt[:100]}...")

        # 使用WavespeedAI生成参考图
        log("")
        log("🎨 生成主角参考图...")

        image_url = generate_image(english_prompt, shot_id=0, shot_count=1)

        # 保存prompt到文件
        ref_file = WORK_DIR / '12_character_reference_prompt.txt'
        with open(ref_file, 'w', encoding='utf-8') as f:
            f.write(f"中文描述：{character_description_cn}\n\n")
            f.write(f"英文Prompt：{english_prompt}\n\n")
            f.write(f"参考图URL：{image_url}\n")

        log(f"✅ 主角参考图已生成")
        log(f"   参考图URL: {image_url}")
        log("")

        return {
            'description_cn': character_description_cn,
            'prompt_en': english_prompt,
            'image_url': image_url
        }

    except Exception as e:
        log(f"❌ 生成主角参考图失败: {e}", "ERROR")
        raise

def extract_character_dna(character_ref):
    """使用LLM提取角色DNA（详细外观描述）

    Args:
        character_ref: dict, 包含description_cn, prompt_en, image_url

    Returns:
        str: 角色DNA（详细英文描述，用于所有镜头）
    """
    log("🧬 提取角色DNA（详细特征描述）...")

    # 检查是否有有意义的描述
    description = character_ref.get('description_cn', '').strip()

    # 只有在完全没有描述，或者是默认占位符时，才使用纯参考图模式
    is_default_placeholder = (
        not description or
        description in ['主角角色', 'character', 'protagonist', '角色', '主角']
    )

    if is_default_placeholder:
        simple_dna = "The character as shown in the reference image."
        log(f"   ⚠️  未提供主角描述，仅依赖参考图")
        dna_file = WORK_DIR / '10_character_dna.txt'
        with open(dna_file, 'w', encoding='utf-8') as f:
            f.write(simple_dna)
        log(f"✅ 角色DNA已生成（纯参考图模式）\n")
        return simple_dna

    # 有描述时，始终生成详细DNA（即使有参考图也要结合文字描述）
    has_reference_image = character_ref.get('image_url') is not None
    if has_reference_image:
        log(f"   模式: 参考图 + 文字描述（双重约束）")
    else:
        log(f"   模式: 纯文字描述生成")
    log(f"   输入描述: {description}")

    dna_prompt = f"""基于以下角色描述，生成一个**极其详细**的英文外观描述（Character DNA），
用于AI图像/视频生成时保持角色一致性。

原始描述：{description}
参考prompt：{character_ref.get('prompt_en', description)}
{"注意：用户已提供参考图片，此描述将与参考图配合使用，请提供详细文字特征以增强一致性。" if has_reference_image else ""}

请生成一个70-100词的详细英文描述，**必须包含以下关键视觉特征**：
1. 性别、年龄、身高体型
2. **最显著的**面部特征（眼睛、发型、肤色）
3. **🎨 服装细节（重点！至少20-30词）**：
   - 具体款式（如：长袖/短袖、领口样式、裙长/裤长）
   - 精确颜色（主色调+辅助色，如"深红色"而非"红色"）
   - 材质质感（如：丝绸、棉质、皮革、针织）
   - 关键细节（纽扣、图案、装饰、配件）
4. **最独特的**标识（如有纹身、logo、特殊配饰）
5. 整体气质（1-2个形容词）

⚠️ **服装一致性是角色识别的关键！必须详细描述服装的颜色、款式、材质和细节。**

格式要求：
- 用英文
- 第三人称描述（如"She has..."、"He wears..."）
- 适合作为AI视频生成prompt的一部分
- 具体、详细、专业
- 重点描述关键视觉特征

示例1（东方女性，约90词，强调服装）：
"An East Asian woman in her early 20s, approximately 165cm tall with a slender graceful build. She has shoulder-length straight jet-black hair with subtle layers, warm porcelain complexion, and almond-shaped dark brown eyes. **CLOTHING DETAILS**: She wears a vibrant crimson red long-sleeve silk qipao dress with a fitted bodice. The dress features a high mandarin collar with delicate golden frog button closures, knee-length hem with elegant side slits revealing black silk stockings. Gold floral embroidery patterns adorn the right shoulder area. She pairs this with simple white pearl earrings and black low-heeled shoes. Overall demeanor: elegant and graceful."

示例2（商务女性，约85词，强调服装）：
"A professional woman in her mid-30s, 170cm tall with an athletic build. She has short, neat dark brown bob-cut hair styled with professional precision, fair complexion, and sharp hazel eyes behind thin-rimmed glasses. **CLOTHING DETAILS**: She wears a tailored navy blue wool blazer with notched lapels and two front buttons, paired with a crisp white cotton button-down shirt underneath. The outfit includes matching navy blue slim-fit trousers with a subtle pinstripe pattern and black leather belt. Silver wristwatch on left wrist. Black leather oxford shoes. Confident, authoritative presence."

只返回英文描述，不要其他内容。
"""

    try:
        character_dna = llm_complete(dna_prompt, temperature=0.5, context="角色DNA提取")

        # 移除可能的引号
        if character_dna.startswith('"') and character_dna.endswith('"'):
            character_dna = character_dna[1:-1]

        # 保存DNA到文件
        dna_file = WORK_DIR / '10_character_dna.txt'
        with open(dna_file, 'w', encoding='utf-8') as f:
            f.write(character_dna)

        log(f"✅ 角色DNA已生成")
        log(f"   {character_dna[:80]}...")
        log("")

        return character_dna

    except Exception as e:
        log(f"❌ 提取角色DNA失败: {e}", "ERROR")
        raise

def prepare_brand_assets(brand_config):
    """准备品牌资产（logo等）

    Args:
        brand_config: dict, 品牌配置信息（包含default_logo_image）

    Returns:
        dict: 品牌资产信息
    """
    log("")
    log("="*60)
    log("🏢 准备品牌资产")
    log("="*60)

    assets = {
        'enabled': brand_config.get('enabled', False),
        'name': brand_config.get('name', ''),
        'logo_path': None,
        'position': brand_config.get('position', 'top-right'),
        'scale': 100,  # logo宽度（像素）
        'opacity': 0.9
    }

    if not assets['enabled']:
        log("   品牌叠加未启用")
        return assets

    # 检查用户是否提供了logo图片
    logo_path = brand_config.get('logo_image')
    if logo_path:
        log(f"   使用用户指定的Logo: {logo_path}")
    else:
        # 使用默认logo（从配置文件读取）
        logo_path = brand_config.get('default_logo_image', './resource/logo/aka.jpg')
        log(f"   使用默认Logo: {logo_path}")

    # 检查是 URL 还是本地文件
    if logo_path.startswith(('http://', 'https://')):
        # URL 图片，直接使用
        log(f"   ✓ 使用在线Logo（URL）")
        assets['logo_path'] = logo_path
    else:
        # 本地文件，检查是否存在并复制到工作目录
        logo_file = Path(logo_path)
        if not logo_file.exists():
            log(f"⚠️  Logo文件不存在: {logo_path}，跳过品牌叠加", "WARN")
            assets['enabled'] = False
            return assets

        # 复制logo到工作目录（保留原始扩展名）
        logo_ext = logo_file.suffix
        work_logo = WORK_DIR / f'11_brand_logo{logo_ext}'
        import shutil
        shutil.copy(logo_file, work_logo)

        assets['logo_path'] = str(work_logo)
        log(f"   ✓ Logo已拷贝到项目目录")

    log(f"✅ 品牌资产已准备")
    log(f"   Logo: {assets['logo_path']}")
    log(f"   位置: {assets['position']}")
    log(f"   大小: {assets['scale']}px")
    log("")

    return assets

def add_brand_overlay(video_path, brand_assets):
    """使用FFmpeg为视频添加品牌logo水印

    Args:
        video_path: str, 输入视频路径
        brand_assets: dict, 品牌资产配置

    Returns:
        str: 添加品牌后的视频路径
    """
    if not brand_assets.get('enabled') or not brand_assets.get('logo_path'):
        return video_path

    import subprocess

    output_path = video_path.replace('.mp4', '_branded.mp4')

    # 计算logo位置
    position_map = {
        'bottom-right': 'W-w-20:H-h-20',
        'bottom-left': '20:H-h-20',
        'top-right': 'W-w-20:20',
        'top-left': '20:20'
    }

    position = position_map.get(brand_assets['position'], 'W-w-20:20')

    # FFmpeg命令：叠加logo
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-i', brand_assets['logo_path'],
        '-filter_complex',
        f"[1:v]scale={brand_assets['scale']}:-1[logo];"
        f"[0:v][logo]overlay={position}:format=auto",
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'copy',
        '-y',  # 覆盖输出文件
        output_path
    ]

    try:
        log(f"   🎨 添加品牌logo到视频...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            log(f"⚠️  FFmpeg警告: {result.stderr[:200]}", "WARN")
            # 如果失败，返回原视频
            return video_path

        # 删除原视频，重命名为原文件名（节省空间）
        import os
        os.remove(video_path)
        os.rename(output_path, video_path)

        log(f"   ✅ 品牌logo已添加")
        return video_path

    except subprocess.TimeoutExpired:
        log(f"⚠️  添加品牌超时，使用原视频", "WARN")
        return video_path
    except Exception as e:
        log(f"⚠️  添加品牌失败: {e}，使用原视频", "WARN")
        return video_path

# ============================================================
# 背景一致性系统
# ============================================================

def plan_backgrounds(outline, shot_count, config):
    """规划2-3个背景池，避免场景数随镜头数爆炸

    Args:
        outline: dict, 故事大纲
        shot_count: int, 镜头总数
        config: dict, 配置信息（包含风格模板、自定义背景等）

    Returns:
        tuple: (backgrounds_list, shot_bg_map)
            - backgrounds_list: list of dict, 每个背景的描述 [{id, name, prompt}, ...]
            - shot_bg_map: dict, 镜头→背景ID的映射 {shot_index: bg_id}
    """
    log("")
    log("=" * 60)
    log("🎬 规划背景池（2-3个背景，保持一致性）")
    log("=" * 60)

    # 检查用户是否提供了自定义背景预设（从config.yaml或user.yaml）
    custom_bg_presets = config.get('background_presets')

    if custom_bg_presets:
        log("   📋 使用用户自定义背景预设")
        backgrounds_list = custom_bg_presets
        bg_count = len(backgrounds_list)
    else:
        # 根据镜头数自动决定背景数量
        if shot_count <= 3:
            bg_count = 2
        elif shot_count <= 6:
            bg_count = 2
        else:
            bg_count = 3

        log(f"   📊 根据{shot_count}个镜头，自动生成{bg_count}个背景")

        # 使用LLM生成背景描述
        style_template = STYLE_TEMPLATES[config['style']]

        prompt = f"""你是专业的场景设计师。为这个{shot_count}镜头的短视频规划{bg_count}个不同的背景场景。

主题：{config['topic']}
视觉风格：{style_template['visual_style']}
色彩方案：{style_template['color_palette']}

要求：
1. 生成{bg_count}个不同的背景场景（如：办公室内部、城市街景、数据中心等）
2. 每个背景必须是完整、独立的场景环境
3. 背景之间要有明显区别，但符合同一视觉风格
4. 每个背景的描述要足够详细，包括：环境、光线、道具、氛围
5. 描述用英文，适合AI图像/视频生成

请以JSON格式输出：
{{
  "backgrounds": [
    {{
      "id": "BG1",
      "name": "场景名称（中文）",
      "prompt": "Detailed English description of the background scene with environment, lighting, props, and atmosphere. Keep the same visual style throughout."
    }},
    // ... {bg_count}个背景
  ]
}}
"""

        try:
            response_text = call_llm_api(prompt, config, "background_planning")
            response_json = extract_json_from_text(response_text)
            backgrounds_list = response_json.get('backgrounds', [])

            if len(backgrounds_list) != bg_count:
                log(f"   ⚠️  LLM返回了{len(backgrounds_list)}个背景，预期{bg_count}个", "WARN")

        except Exception as e:
            log(f"   ⚠️  背景生成失败，使用默认背景: {e}", "WARN")
            # 降级方案：使用简单的默认背景
            backgrounds_list = [
                {"id": "BG1", "name": "主场景", "prompt": f"{style_template['visual_style']}, main scene with {style_template['color_palette']} colors and {style_template['lighting']} lighting"},
                {"id": "BG2", "name": "次场景", "prompt": f"{style_template['visual_style']}, secondary scene with {style_template['color_palette']} colors and {style_template['lighting']} lighting"}
            ][:bg_count]

    # 为每个背景ID添加到列表（如果缺失）
    for i, bg in enumerate(backgrounds_list):
        if 'id' not in bg:
            bg['id'] = f"BG{i+1}"

    # 镜头→背景的映射策略：均匀分配或基于场景类型
    shot_bg_map = {}
    for i in range(shot_count):
        # 简单策略：循环分配（可以后续改为基于场景语义匹配）
        bg_idx = i % len(backgrounds_list)
        shot_bg_map[i] = backgrounds_list[bg_idx]['id']

    # 打印规划结果
    log("")
    log("   ✅ 背景规划完成:")
    for bg in backgrounds_list:
        log(f"      {bg['id']}: {bg['name']}")
        log(f"         → {bg['prompt'][:60]}...")

    log("")
    log("   📌 镜头→背景映射:")
    for shot_idx, bg_id in shot_bg_map.items():
        bg_name = next((bg['name'] for bg in backgrounds_list if bg['id'] == bg_id), bg_id)
        log(f"      镜头{shot_idx+1} → {bg_id} ({bg_name})")

    log("=" * 60)

    return backgrounds_list, shot_bg_map

# ============================================================
# 故事生成系统
# ============================================================

def generate_story_outline(config):
    """生成故事大纲（第一阶段）

    Args:
        config: dict, 包含topic, style, shot_count等配置

    Returns:
        dict: 故事大纲数据
    """
    log("-" * 30)
    log("📖 阶段1: 生成故事大纲")
    log("-" * 60)

    style_template = STYLE_TEMPLATES[config['style']]

    prompt = f"""你是一位专业的视频脚本策划师。请为以下主题创作一个{config['shot_count']}镜头的短视频故事大纲。

主题：{config['topic']}
视觉风格：{style_template['name']}
镜头数：{config['shot_count']}个

故事结构要求（起承转合）：
1. 每个镜头是故事的有机组成部分，不是独立的片段
2. 镜头之间有明确的因果关系或时间推进
3. 视觉风格统一：{style_template['visual_style']}
4. 色彩基调：{style_template['color_palette']}

请以JSON格式输出故事大纲：
{{
  "title": "故事标题",
  "theme": "核心主题（一句话）",
  "visual_theme": {{
    "primary_colors": ["{style_template['color_palette'].split(',')[0].strip()}", "{style_template['color_palette'].split(',')[1].strip()}"],
    "mood": "{style_template['mood']}"
  }},
  "shot_breakdown": [
    {{
      "shot_number": 1,
      "scene_summary": "镜头内容概要（20字内）",
      "key_action": "关键动作或视觉重点",
      "transition_to_next": "与下一镜头的连接点"
    }}
    // ... {config['shot_count']}个镜头
  ]
}}
"""

    try:
        log(f"   📤 准备调用LLM ({LLM_SETTINGS.get('name', CURRENT_LLM_PROVIDER)}) ...")
        log("")
        log("=" * 60)
        log("📝 发送的提示词:")
        log("=" * 60)
        log(prompt)
        log("=" * 60)
        log("")

        log(f"   🔄 正在调用 {LLM_SETTINGS.get('name', CURRENT_LLM_PROVIDER)}，请稍候...")
        content = llm_complete(prompt, temperature=0.8, context="故事大纲")

        log("")
        log("=" * 60)
        log(f"📥 {LLM_SETTINGS.get('name', CURRENT_LLM_PROVIDER)} 返回结果:")
        log("=" * 60)
        log(content)
        log("=" * 60)
        log("")

        # 提取JSON
        log("   🔍 正在解析JSON...")
        json_content = content
        if '```json' in content:
            json_content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            json_content = content.split('```')[1].split('```')[0].strip()

        outline = json.loads(json_content)

        log("   ✅ JSON解析成功")
        log("")
        log("=" * 60)
        log("📊 解析后的故事大纲:")
        log("=" * 60)
        log(json.dumps(outline, indent=2, ensure_ascii=False))
        log("=" * 60)
        log("")

        # 保存故事大纲
        outline_file = WORK_DIR / '20_story_outline.json'
        with open(outline_file, 'w', encoding='utf-8') as f:
            json.dump(outline, f, indent=2, ensure_ascii=False)

        log(f"✅ 故事大纲已生成：{outline_file}")
        log(f"   标题: {outline.get('title', 'N/A')}")
        log(f"   主题: {outline.get('theme', 'N/A')}")
        log(f"   镜头数: {len(outline.get('shot_breakdown', []))}")
        log("")

        # 详细显示每个镜头的大纲
        log("📋 故事大纲详情:")
        for i, shot in enumerate(outline.get('shot_breakdown', []), 1):
            log(f"   镜头 {i}:")
            log(f"      场景: {shot.get('scene_summary', 'N/A')}")
            log(f"      动作: {shot.get('key_action', 'N/A')}")
            if shot.get('transition_to_next'):
                log(f"      转场: {shot.get('transition_to_next', 'N/A')}")
            log("")

        log("-" * 60)

        return outline

    except Exception as e:
        log(f"❌ 生成故事大纲失败：{e}", "ERROR")
        raise

def generate_narration_framework(outline, config):
    """生成广告词整体框架（新增阶段1.5）

    Args:
        outline: dict, 故事大纲
        config: dict, 配置信息

    Returns:
        dict: 广告词框架 {
            "overall_tagline": "整体主线",
            "narration_style": "语言风格",
            "shot_points": [每个镜头的核心要点]
        }
    """
    log("")
    log("-" * 30)
    log("🎙️  阶段1.5: 生成广告词框架")
    log("-" * 60)

    # 计算每个镜头的时长（从config中获取，默认5秒）
    shot_duration = config.get('duration', 5)
    total_duration = shot_duration * config['shot_count']

    # 从配置文件读取旁白语速（默认3.0字/秒，更保守自然）
    audio_config = CONFIG.get('audio', {})
    CHARS_PER_SECOND = audio_config.get('chars_per_second', 3.0)
    log(f"   旁白语速: {CHARS_PER_SECOND}字/秒")

    prompt = f"""你是一位资深广告文案大师。请为以下故事创作广告词整体框架。

主题：{config['topic']}
故事标题：{outline.get('title', 'N/A')}
核心主题：{outline.get('theme', 'N/A')}
视频总时长：{total_duration}秒（{config['shot_count']}个镜头，每镜头{shot_duration}秒）
配音语速：{CHARS_PER_SECOND}字/秒

故事分镜概要：
{chr(10).join([f"{i+1}. {beat['scene_summary']} - {beat['key_action']}" for i, beat in enumerate(outline['shot_breakdown'])])}

创作要求：
1. **整体定位**：确定广告词的主线（一句话，如"探索未知，点燃激情"）
2. **语言风格**：定义文案的语言特色，要求：
   - ❌ 禁止四字成语堆砌
   - ✅ 必须长短句结合（短句冲击+长句铺陈）
   - 自然流畅，像真实的广告配音
   - 风格示例："诗意叙事型"、"悬念递进型"、"情感共鸣型"
3. **分段要点**：为每个镜头分配核心表达要点，确保：
   - 全片叙事连贯递进（引入→展开→高潮→升华）
   - 每段要点不重复、不跳跃
   - 与画面内容紧密呼应

注意事项：
- 不要生成具体文案，只需框架性指导
- 确保情感递进自然（平和→激昂→震撼）
- 避免空洞词汇（创新、强大、完美等）
- 强调长短句交替的节奏感

请以JSON格式输出：
{{
  "overall_tagline": "整体主线（一句话）",
  "narration_style": "语言风格描述",
  "emotion_arc": "情感曲线（如：平静→好奇→振奋→震撼）",
  "shot_points": [
    {{
      "shot_number": 1,
      "core_message": "本镜头核心要传达的信息",
      "emotion": "本镜头的情感基调",
      "connection": "与上下镜头的关系"
    }}
    // ... {config['shot_count']}个镜头
  ]
}}
"""

    try:
        log(f"   🔄 正在调用{LLM_SETTINGS.get('name', CURRENT_LLM_PROVIDER)}生成广告词框架...")
        content = llm_complete(prompt, temperature=0.8, context="广告词框架")

        # 提取JSON
        json_content = content
        if '```json' in content:
            json_content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            json_content = content.split('```')[1].split('```')[0].strip()

        framework = json.loads(json_content)

        # 保存框架
        framework_file = WORK_DIR / '21_narration_framework.json'
        with open(framework_file, 'w', encoding='utf-8') as f:
            json.dump(framework, f, indent=2, ensure_ascii=False)

        log(f"✅ 广告词框架已生成：{framework_file}")
        log(f"   主线: {framework.get('overall_tagline', 'N/A')}")
        log(f"   风格: {framework.get('narration_style', 'N/A')}")
        log(f"   情感曲线: {framework.get('emotion_arc', 'N/A')}")
        log("")

        # 显示每个镜头的要点
        log("📋 分镜要点:")
        for point in framework.get('shot_points', []):
            log(f"   镜头 {point['shot_number']}: {point['core_message']}")
        log("")
        log("-" * 60)

        return framework

    except Exception as e:
        log(f"❌ 生成广告词框架失败：{e}", "ERROR")
        raise

def generate_coherent_shots(outline, config, narration_framework=None):
    """基于故事大纲生成连贯的分镜脚本（第二阶段）

    Args:
        outline: dict, 故事大纲
        config: dict, 配置信息
        narration_framework: dict, 广告词框架（可选）

    Returns:
        dict: 包含连贯镜头描述的字典
    """
    log("")
    log("-" * 30)
    log("🎬 阶段2: 生成连贯分镜脚本（不含旁白）")
    log("-" * 60)

    # 🎬 规划背景池（2-3个背景，避免场景爆炸）
    backgrounds_list, shot_bg_map = plan_backgrounds(outline, config['shot_count'], config)

    style_template = STYLE_TEMPLATES[config['style']]
    shots = []

    for i, beat in enumerate(outline['shot_breakdown']):
        prev_beat = outline['shot_breakdown'][i-1] if i > 0 else None
        next_beat = outline['shot_breakdown'][i+1] if i < len(outline['shot_breakdown'])-1 else None

        log("")
        log(f"   📝 生成镜头 {i+1}/{config['shot_count']}: {beat['scene_summary']}")

        # 🎬 获取智能运镜模式
        camera_code, camera_config = get_camera_movement(i, config['shot_count'], beat['scene_summary'])
        log(f"   🎬 运镜模式: {camera_code} - {camera_config['name']} ({camera_config['suitable_for']})")

        # 准备主角信息（如果启用）
        character_section = ""
        if config.get('character', {}).get('enabled') and config['character'].get('dna'):
            character_dna = config['character']['dna']
            character_section = f"""
⚠️ 主角信息（CRITICAL - 必须严格遵守，逐字复制到prompt开头）：
{character_dna}

🎨 **服装一致性要求（最高优先级）**：
- 主角在**每个镜头**中的服装必须**100%一致**（颜色、款式、材质、细节）
- **禁止**改变服装颜色、款式或任何细节
- **禁止**添加或移除任何服装配件
- 只有姿势、动作、场景可以变化，服装**绝对不能变**
"""

        prompt = f"""基于故事大纲，生成第{i+1}个镜头的详细英文prompt（用于AI视频生成）。

整体故事：{outline['theme']}
视觉主题：色调{outline['visual_theme']['primary_colors']}，氛围{outline['visual_theme']['mood']}
{character_section}
当前镜头（{i+1}/{config['shot_count']}）：
- 场景概要：{beat['scene_summary']}
- 关键动作：{beat['key_action']}

{"前一镜头：" + prev_beat['key_action'] if prev_beat else "这是开场镜头"}
{"下一镜头铺垫：" + beat['transition_to_next'] if next_beat else "这是结束镜头"}

风格要求：
- 视觉风格：{style_template['visual_style']}
- 色彩方案：{style_template['color_palette']}
- 光影：{style_template['lighting']}
- 镜头运动（必须严格遵守）：{camera_config['description']}

请生成一个90-150词的详细英文prompt，要求：
1. {"🔴 **必须以完整的主角描述作为prompt开头**（逐字复制上述主角DNA的全部内容，特别是服装细节：颜色、款式、材质、配件）" if character_section else "包含具体的视觉描述（场景、主体、动作）"}
2. {"然后描述主角在当前场景中的姿势、动作、位置" if character_section else ""}
3. {"体现与前一镜头的连续性" if prev_beat else "开场要吸引人"}
4. {"为下一镜头做铺垫" if next_beat else "结尾要有升华"}
5. 严格遵守上述风格模板
6. 使用cinematic专业术语

⚠️ **关键提醒**：如果有主角，prompt的前50词必须是主角外观描述（包含完整服装细节），然后才是场景和动作！

只返回prompt文本，不要其他内容。
"""
        visual_theme = outline.get('visual_theme', {})
        visual_colors = visual_theme.get('primary_colors', []) or []
        if isinstance(visual_colors, list):
            visual_colors_str = ', '.join([str(c) for c in visual_colors])
        else:
            visual_colors_str = str(visual_colors)

        previous_line = f"前一镜头：{prev_beat['key_action']}" if prev_beat else "这是开场镜头"
        next_line = f"下一镜头铺垫：{beat['transition_to_next']}" if next_beat else "这是结束镜头"

        first_requirement = "如果有主角，必须以主角描述作为开头（完整复制主角信息）" if character_section else "包含具体的视觉描述（场景、主体、动作）"
        second_requirement = "体现与前一镜头的连续性" if prev_beat else "开场要吸引人"
        third_requirement = "为下一镜头做铺垫" if next_beat else "结尾要有升华"

        # 🎬 准备背景一致性约束
        bg_id = shot_bg_map.get(i, '')
        bg_info = next((bg for bg in backgrounds_list if bg['id'] == bg_id), None)
        background_note = ""
        if bg_info:
            background_note = f"""
🌐 **背景一致性约束（CRITICAL - 最高优先级）**：
背景#{bg_info['id']}：{bg_info['name']}
{bg_info['prompt']}

⚠️ **所有使用此背景的镜头必须保持相同场景/灯光/道具，仅人物动作和运镜可变，禁止新增或更换场景元素**
"""

        prompt = get_prompt(
            'shot_prompt',
            shot_index=i + 1,
            shot_total=config['shot_count'],
            story_theme=outline['theme'],
            visual_colors=visual_colors_str,
            visual_mood=visual_theme.get('mood'),
            character_section=character_section,
            background_note=background_note,
            scene_summary=beat['scene_summary'],
            key_action=beat['key_action'],
            previous_line=previous_line,
            next_line=next_line,
            visual_style=style_template['visual_style'],
            color_palette=style_template['color_palette'],
            lighting=style_template['lighting'],
            camera_description=camera_config['description'],
            first_requirement=first_requirement,
            second_requirement=second_requirement,
            third_requirement=third_requirement
        )

        try:
            shot_prompt = llm_complete(prompt, temperature=0.7, context=f"镜头{i+1}脚本")

            # 移除可能的markdown格式
            if shot_prompt.startswith('"') and shot_prompt.endswith('"'):
                shot_prompt = shot_prompt[1:-1]

            # 保存镜头数据（旁白将在视频生成后的阶段2.5生成）
            shot_data = {
                'id': beat['shot_number'],
                'summary_cn': beat['scene_summary'],
                'description': shot_prompt,
                'camera_movement': {
                    'code': camera_code,
                    'name': camera_config['name'],
                    'description': camera_config['description']
                },
                'visual_continuity': {
                    'from_previous': prev_beat['key_action'] if prev_beat else None,
                    'to_next': beat.get('transition_to_next')
                }
            }

            # 🎬 附加背景信息（用于生成阶段保持一致性）
            if bg_info:
                shot_data['background'] = {
                    'id': bg_info['id'],
                    'name': bg_info['name'],
                    'prompt': bg_info['prompt']
                }

            shots.append(shot_data)

            log(f"   ✓ 镜头 {i+1} 完成:")
            log(f"      场景: {beat['scene_summary']}")
            log(f"      运镜: {camera_code} - {camera_config['name']}")
            log(f"      Prompt: {shot_prompt[:80]}...")
            log("")

        except Exception as e:
            log(f"   ❌ 镜头 {i+1} 生成失败：{e}", "ERROR")
            raise

    shots_data = {'shots': shots}

    # 保存分镜脚本
    script_file = WORK_DIR / '22_shots_script.json'
    with open(script_file, 'w', encoding='utf-8') as f:
        json.dump(shots_data, f, indent=2, ensure_ascii=False)

    log("")
    log(f"✅ 连贯分镜脚本已生成：{script_file}")
    log(f"   共 {len(shots)} 个镜头")
    log("")

    # 总结显示所有镜头
    log("📋 完整镜头列表:")
    for shot in shots:
        log(f"   镜头 {shot['id']}: {shot['summary_cn']} [{shot['camera_movement']['code']}]")

    log("-" * 60)

    return shots_data

def generate_shots_script(config=None):
    """使用LLM生成镜头脚本（支持故事化）

    Args:
        config: dict, 可选。如果提供则使用故事化生成，否则使用旧版本

    Returns:
        dict: shots_data字典
    """
    if config is not None:
        # 新版本：故事化生成（三阶段）
        log("=" * 60)
        log("📚 故事化生成模式（已升级：整体框架 + 精确时长匹配）")
        log("=" * 60)

        # 第一阶段：生成故事大纲
        outline = generate_story_outline(config)

        # 第二阶段：生成广告词框架（新增！）
        narration_framework = generate_narration_framework(outline, config)

        # 第三阶段：基于大纲和框架生成连贯分镜
        shots_data = generate_coherent_shots(outline, config, narration_framework)

        return shots_data

    # 兼容旧版本：直接生成3个独立镜头
    log("-" * 30)
    log("📝 正在生成镜头脚本（简单模式）...")

    prompt = """请为"Akamai推出AI推理云"生成3个视频广告镜头的描述。每个镜头3秒。
要求：
1. 科技感/未来风格
2. 使用科技元素：数据流、全息投影、芯片、服务器、云计算可视化
3. 色调：蓝色、紫色、霓虹色
4. 每个镜头要有清晰的视觉描述

请以JSON格式返回，格式如下：
{
  "shots": [
    {"id": 1, "description": "镜头1的详细英文prompt描述"},
    {"id": 2, "description": "镜头2的详细英文prompt描述"},
    {"id": 3, "description": "镜头3的详细英文prompt描述"}
  ]
}
"""

    try:
        content = llm_complete(prompt, temperature=0.7, context="简易镜头脚本")

        # 提取JSON部分
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        shots_data = json.loads(content)

        # 保存脚本
        script_file = WORK_DIR / '22_shots_script.json'
        with open(script_file, 'w', encoding='utf-8') as f:
            json.dump(shots_data, f, indent=2, ensure_ascii=False)

        log(f"✅ 镜头脚本已生成：{script_file}")
        log(f"   共 {len(shots_data['shots'])} 个镜头")
        log("")

        # 详细显示每个镜头的描述
        log("📋 镜头脚本详情:")
        for shot in shots_data['shots']:
            log(f"   镜头 {shot['id']}:")
            log(f"      Prompt: {shot['description']}")
            log("")

        log("-" * 30)
        return shots_data

    except Exception as e:
        log(f"❌ 生成脚本失败：{e}", "ERROR")
        raise

def condense_narration_text(original_text, target_duration, current_duration, max_retries=3):
    """使用LLM精简文案，使其适配目标时长

    Args:
        original_text: 原始文案
        target_duration: 目标时长（秒）
        current_duration: 当前配音时长（秒）
        max_retries: 最大重试次数

    Returns:
        str: 精简后的文案，如果失败则返回None
    """
    # 计算压缩比例
    compression_ratio = target_duration / current_duration
    original_chars = len(original_text)
    target_chars = int(original_chars * compression_ratio * 0.9)  # 保守估计，留10%余量

    log(f"   📉 需要精简文案:")
    log(f"      原文: {original_chars}字, {current_duration:.2f}秒")
    log(f"      目标: {target_chars}字左右, {target_duration:.2f}秒")

    prompt = get_prompt(
        'condense_narration',
        original_chars=original_chars,
        original_text=original_text,
        target_chars=target_chars
    )

    llm_name = LLM_SETTINGS.get('name', CURRENT_LLM_PROVIDER)

    for attempt in range(max_retries):
        try:
            log(f"   🔄 {llm_name} 精简文案 (尝试 {attempt + 1}/{max_retries})...")
            condensed_text = llm_complete(prompt, temperature=0.5, context="旁白精简")
            # 清理文本
            condensed_text = condensed_text.strip('"').strip("'").strip()
            if '\n' in condensed_text:
                condensed_text = condensed_text.split('\n')[0]

            condensed_chars = len(condensed_text)
            log(f"   ✅ 精简完成: {condensed_chars}字")
            log(f"      精简后: {condensed_text}")

            return condensed_text

        except Exception as e:
            log(f"   ⚠️  精简失败 (尝试 {attempt + 1}/{max_retries}): {e}", "WARN")
            if attempt == max_retries - 1:
                log(f"   ❌ 达到最大重试次数，精简失败", "ERROR")
                return None
            time.sleep(2)  # 短暂等待后重试

    return None

def generate_images_parallel(shots, shot_count, character_image_path=None):
    """并发生成所有图像（优化日志显示）

    Args:
        shots: 待处理的镜头列表
        shot_count: 总镜头数
        character_image_path: 主角参考图路径（可选）

    Returns:
        dict: {shot_id: image_url} 映射字典
    """
    if not shots:
        return {}

    # 阶段1：批量提交（显示整体信息）
    log("=" * 60)
    log(f"🎨 开始批量生成 {len(shots)} 个图像...")
    max_workers = min(MAX_CONCURRENT_WORKERS, len(shots))
    log(f"   📊 并发线程数: {max_workers}")
    log(f"   ⏱️  预计总等待时间: {len(shots) * 20}-{len(shots) * 30}秒")
    log(f"   💡 提示: 任务并发执行中，完成后将按顺序显示结果")
    log("=" * 60)

    results = {}
    failed = []
    task_start_time = time.time()

    # 用于标记第一个任务（显示详细日志）
    import threading
    first_task_lock = threading.Lock()
    first_task_flag = [True]  # 使用列表以便在闭包中修改

    def generate_with_flag(shot_desc, shot_id, shot_cnt, char_img_path, bg_prompt=None):
        """包装函数：为第一个任务设置详细日志标志"""
        with first_task_lock:
            is_first = first_task_flag[0]
            if is_first:
                first_task_flag[0] = False

        # 第一个任务显示详细日志，其他任务简化日志
        return generate_image(shot_desc, shot_id, shot_cnt, char_img_path, bg_prompt, verbose=is_first)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_shot = {
            executor.submit(
                generate_with_flag,
                shot['description'],
                shot['id'],
                shot_count,
                character_image_path,
                shot.get('background', {}).get('prompt')  # 🎬 传入背景提示
            ): shot
            for shot in shots
        }

        # 阶段2：收集结果并按完成顺序显示
        for future in as_completed(future_to_shot):
            shot = future_to_shot[future]
            try:
                image_url = future.result()
                results[shot['id']] = image_url

                # 显示完成信息
                elapsed = time.time() - task_start_time
                log("-" * 60)
                log(f"✅ 镜头 {shot['id']}/{shot_count} 图像已完成")
                log(f"   📊 进度: {len(results)}/{len(shots)} 已完成")
                log(f"   ⏱️  累计耗时: {elapsed:.1f}秒")
                log("-" * 60)

            except Exception as e:
                failed.append((shot['id'], str(e)))
                log(f"   ❌ 镜头 {shot['id']} 图像生成失败: {e}", "ERROR")

    if failed:
        log(f"⚠️  {len(failed)} 个图像生成失败，这些镜头将被跳过", "WARN")

    log(f"✅ 图像生成完成: {len(results)}/{len(shots)} 成功")
    return results

def is_transient_video_error(error_message: str) -> bool:
    """判断视频生成错误是否为可重试的临时问题"""
    msg = (error_message or "").lower()
    transient_markers = [
        "failed to download image",
        "download image",
        "url for downloading content",
        "read timed out",
        "timeout",
    ]
    return any(marker in msg for marker in transient_markers)


def generate_videos_parallel(shots_with_images, shot_count, resolution="720p"):
    """并发生成所有视频（支持429错误重试）

    Args:
        shots_with_images: 列表，每个元素为 (shot, image_url) 或 (shot, None)
        shot_count: 总镜头数
        resolution: 视频分辨率，默认720p

    Returns:
        dict: {shot_id: video_file} 成功生成的视频映射
        list: [(shot_id, error)] 失败的镜头列表
    """
    if not shots_with_images:
        return {}, []

    log(f"🎬 并发生成 {len(shots_with_images)} 个视频...")
    max_workers = min(MAX_CONCURRENT_WORKERS, len(shots_with_images))
    log(f"   并发数: {max_workers}")
    log(f"   ⚠️  注意: 如遇429限流错误，将自动重试")

    results = {}
    failed = []

    def generate_video_with_retry(shot, image_url, max_retries=3):
        """生成视频，支持限流和临时错误重试"""
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                # 传入运镜信息和背景信息
                camera_movement = shot.get('camera_movement', {})
                background_prompt = shot.get('background', {}).get('prompt')  # 🎬 获取背景提示
                video_file = generate_video(image_url, shot['description'], shot['id'], shot_count, resolution, camera_movement, background_prompt)
                return shot['id'], video_file, None
            except requests.exceptions.HTTPError as e:
                # 检查是否是429错误
                if e.response.status_code == 429:
                    last_error = e
                    if attempt < max_retries:
                        wait_time = 10 * attempt  # 渐进式等待：10s, 20s, 30s
                        log(f"   ⚠️  镜头{shot['id']} 触发限流(429)，{wait_time}秒后重试 (尝试{attempt}/{max_retries})", "WARN")
                        time.sleep(wait_time)
                    else:
                        log(f"   ❌ 镜头{shot['id']} 达到最大重试次数", "ERROR")
                else:
                    # 其他HTTP错误，不重试
                    return shot['id'], None, str(e)
            except (TaskFailedError, requests.exceptions.RequestException, APIError) as e:
                err_msg = str(e)
                if is_transient_video_error(err_msg) and attempt < max_retries:
                    wait_time = 10 * attempt
                    log(
                        f"   ⚠️  镜头{shot['id']} 遇到临时错误，{wait_time}秒后重试 (尝试{attempt}/{max_retries}): {err_msg[:120]}",
                        "WARN",
                    )
                    time.sleep(wait_time)
                else:
                    return shot['id'], None, err_msg
            except Exception as e:
                # 其他错误，不重试
                return shot['id'], None, str(e)

        return shot['id'], None, f"429错误，已重试{max_retries}次: {last_error}"

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_shot = {
            executor.submit(generate_video_with_retry, shot, image_url): shot
            for shot, image_url in shots_with_images
        }

        # 收集结果
        for future in as_completed(future_to_shot):
            shot = future_to_shot[future]
            try:
                shot_id, video_file, error = future.result()

                if video_file:
                    results[shot_id] = video_file
                    log(f"   ✅ 镜头 {shot_id} 视频生成完成 ({len(results)}/{len(shots_with_images)})")
                else:
                    failed.append((shot_id, error))
                    log(f"   ❌ 镜头 {shot_id} 视频生成失败: {error}", "ERROR")
            except Exception as e:
                failed.append((shot['id'], str(e)))
                log(f"   ❌ 镜头 {shot['id']} 异常: {e}", "ERROR")

    if failed:
        log(f"⚠️  {len(failed)} 个视频生成失败", "WARN")

    log(f"✅ 视频生成完成: {len(results)}/{len(shots_with_images)} 成功")
    return results, failed

def upload_image_to_cloudinary(image_source):
    """上传图片到图床并获取URL，支持多图床自动容错

    优先顺序：catbox.moe (最稳定) → sm.ms → telegraph → imgbb (备用)

    Args:
        image_source: 本地图片路径或公网URL

    Returns:
        str: 上传后的图片URL
    """
    import base64
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    # 读取图片数据（所有图床都需要）
    if isinstance(image_source, str) and image_source.startswith(('http://', 'https://')):
        # 直接拉取远程图片，再上传，避免第三方API无法访问原URL
        resp = requests.get(image_source, timeout=30)
        resp.raise_for_status()
        image_data = resp.content
    else:
        with open(image_source, 'rb') as f:
            image_data = f.read()

    # 定义图床列表（按优先级排序）
    image_hosts = IMAGE_UPLOAD_CONFIG.get('hosts', [
        {'name': 'catbox.moe', 'type': 'catbox'},
        {'name': 'sm.ms', 'type': 'smms'},
        {'name': 'telegraph', 'type': 'telegraph'},
        {'name': 'imgbb', 'type': 'imgbb', 'api_key': IMAGE_UPLOAD_CONFIG.get('api_key')}
    ])

    timeout_seconds = IMAGE_UPLOAD_CONFIG.get('timeout_seconds', 30)
    retry_config = IMAGE_UPLOAD_CONFIG.get('retry', {})
    retry_total = retry_config.get('total', 3)
    retry_backoff = retry_config.get('backoff_factor', 1)
    retry_statuses = retry_config.get('status_forcelist', [429, 500, 502, 503, 504])
    connect_timeout_seconds = retry_config.get('connect_timeout_seconds', 10)
    request_timeout = (connect_timeout_seconds, timeout_seconds)

    session = requests.Session()
    retry = Retry(
        total=retry_total,
        connect=retry_total,
        read=retry_total,
        status=retry_total,
        backoff_factor=retry_backoff,
        status_forcelist=retry_statuses,
        allowed_methods=frozenset(['POST'])
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({'User-Agent': 'aka-video-uploader/1.0'})
    errors = []

    # 依次尝试每个图床
    for host_config in image_hosts:
        host_name = host_config['name']
        host_type = host_config['type']

        try:
            log(f"   → 尝试图床: {host_name}")
            if host_type == 'catbox':
                # Catbox.moe - 匿名上传，最稳定
                files = {'fileToUpload': ('image.jpg', image_data, 'image/jpeg')}
                data = {'reqtype': 'fileupload'}
                response = session.post(
                    'https://catbox.moe/user/api.php',
                    files=files,
                    data=data,
                    timeout=request_timeout
                )
                if response.status_code == 200 and response.text.startswith('http'):
                    log(f"   ✓ 图片已上传到 {host_name}")
                    return response.text.strip()
                else:
                    raise ValueError(f"上传失败: {response.text}")

            elif host_type == 'smms':
                # SM.MS - 国内稳定
                files = {'smfile': ('image.jpg', image_data, 'image/jpeg')}
                response = session.post(
                    'https://sm.ms/api/v2/upload',
                    files=files,
                    timeout=request_timeout
                )
                result = response.json()
                if result.get('success'):
                    log(f"   ✓ 图片已上传到 {host_name}")
                    return result['data']['url']
                else:
                    raise ValueError(f"上传失败: {result.get('message', 'Unknown error')}")

            elif host_type == 'telegraph':
                # Telegraph - Telegram官方
                files = {'file': ('image.jpg', image_data, 'image/jpeg')}
                response = session.post(
                    'https://telegra.ph/upload',
                    files=files,
                    timeout=request_timeout
                )
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    image_path = result[0].get('src', '')
                    if image_path:
                        image_url = f"https://telegra.ph{image_path}"
                        log(f"   ✓ 图片已上传到 {host_name}")
                        return image_url
                raise ValueError("上传失败: 响应格式异常")

            elif host_type == 'imgbb':
                # ImgBB - 需要API key（备用）
                api_key = host_config.get('api_key')
                if not api_key:
                    raise ValueError("缺少API key")

                base64_image = base64.b64encode(image_data).decode('utf-8')
                params = {"key": api_key}
                payload = {"image": base64_image}

                response = session.post(
                    "https://api.imgbb.com/1/upload",
                    params=params,
                    data=payload,
                    timeout=request_timeout
                )
                result = response.json()
                if result.get('success') and 'data' in result:
                    log(f"   ✓ 图片已上传到 {host_name}")
                    return result['data']['url']
                else:
                    error_msg = result.get('error', {}).get('message', 'Unknown error')
                    raise ValueError(f"上传失败: {error_msg}")

        except Exception as e:
            error_msg = str(e)
            errors.append(f"{host_name}: {error_msg}")
            log(f"   ✗ {host_name} 失败: {error_msg[:50]}...", "WARN")
            continue

    # 所有图床都失败
    raise ValueError(f"所有图床上传失败:\n" + "\n".join(errors))

@smart_retry(max_attempts=3, backoff_factor=2)
def generate_image(prompt, shot_id, shot_count, character_image_path=None, background_prompt=None, verbose=True):
    """使用配置的模型生成图像（支持参考图和背景一致性）

    Args:
        prompt: 文本提示词
        shot_id: 镜头ID
        shot_count: 总镜头数
        character_image_path: 主角参考图路径（可选）
        background_prompt: 背景一致性提示（可选）
        verbose: 是否显示详细日志（默认True）

    Returns:
        str: 图像URL（公网可访问）
    """
    model_config = IMAGE_MODEL_CONFIG[CURRENT_IMAGE_MODEL]
    api_cost = model_config['cost']

    # 只有详细模式才显示开始信息
    if verbose:
        log("=" * 60)
        log(f"🎨 正在生成镜头 {shot_id}/{shot_count} 的图像...")
        log(f"   📦 模型: {CURRENT_IMAGE_MODEL}")
        log(f"   💵 成本: ${api_cost}")
        log(f"   🎯 质量: {model_config['quality']}")
        log(f"   📝 提示词: {prompt[:80]}...")

    # 检查是否支持参考图
    support_reference = model_config.get('support_reference', False)
    if verbose:
        if character_image_path and support_reference:
            log(f"   📷 使用参考图: {Path(character_image_path).name}")
        elif character_image_path and not support_reference:
            log(f"   ⚠️  当前模型不支持参考图，将忽略参考图", "WARN")

    # 查询调用前余额（仅详细模式）
    before_balance = None
    if verbose:
        before_balance = get_wavespeed_balance()
        if before_balance is not None:
            log(f"   💰 调用前余额: ${before_balance:.4f}")

    url = f"https://api.wavespeed.ai{model_config['endpoint']}"
    headers = {
        "Authorization": f"Bearer {WAVESPEED_API_KEY}",
        "Content-Type": "application/json"
    }

    # 合并提示词和模型特定参数
    prompt_text = prompt

    # 🎬 拼接背景一致性提示（如果有）
    if background_prompt:
        prompt_text = f"BACKGROUND: {background_prompt.strip()}\n\nSCENE: {prompt_text.strip()}"

    # 拼接主角参考图提示（如果有）
    if character_image_path:
        prompt_text = f"{prompt_text.strip()} 保持人物面部特征与人物参考图完全相同"

    payload = {"prompt": prompt_text}
    payload.update(model_config['params'])

    if IMAGE_DURATION is not None:
        payload.setdefault('duration', IMAGE_DURATION)
    if IMAGE_SEED is not None:
        payload.setdefault('seed', IMAGE_SEED)
    payload.setdefault('enable_prompt_expansion', IMAGE_PROMPT_EXPANSION)

    # 如果模型支持参考图且提供了参考图，则处理参考图URL
    if support_reference and character_image_path:
        try:
            # 如果是公网URL，直接使用（不需要重新上传）
            if character_image_path.startswith(('http://', 'https://')):
                if verbose:
                    log(f"   🔗 使用参考图URL（直接引用）")
                reference_image_url = character_image_path
            else:
                # 本地文件需要上传到图床
                if not Path(character_image_path).exists():
                    raise FileNotFoundError(f"参考图不存在: {character_image_path}")
                if verbose:
                    log(f"   📤 上传本地参考图到图床...")
                reference_image_url = upload_image_to_cloudinary(character_image_path)
                if verbose:
                    log(f"   ✓ 参考图已上传: {reference_image_url[:70]}...")

            payload['images'] = [reference_image_url]
        except Exception as e:
            if verbose:
                log(f"   ⚠️  参考图处理失败: {e}，将使用纯文本模式", "WARN")

    if verbose:
        log(f"   📤 提交图像生成任务...")

    # API限流控制
    image_limiter.acquire()
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    raw_result = response.json()

    # 统一解析响应格式
    result = parse_api_response(raw_result, f"图像生成-{CURRENT_IMAGE_MODEL}")

    # 提取并验证任务ID
    task_id = result.get('id')
    validate_task_id(task_id, "图像生成任务")

    if verbose:
        log(f"   ✓ 任务已提交，ID: {task_id}")
        log(f"   ⏳ 预计等待时间: 10-30秒")
        log(f"   🔄 开始轮询结果...")

    # 等待图像生成
    image_url = wait_for_result(task_id, "图像", max_wait=MAX_WAIT_IMAGE)

    # 下载图像（保存到本地用于查看）
    if verbose:
        log(f"   📥 正在下载图像...")
    image_num = 30 + (shot_id - 1)
    image_file = WORK_DIR / f'{image_num:02d}_shot_{shot_id:02d}_image.png'
    download_file(image_url, image_file)

    # 详细模式才显示完整信息
    if verbose:
        file_size = image_file.stat().st_size / (1024 * 1024)
        log(f"✅ 镜头 {shot_id}/{shot_count} 图像已生成")
        log(f"   📄 本地文件: {image_file}")
        log(f"   🔗 图像URL: {image_url[:80]}...")
        log(f"   📦 文件大小: {file_size:.2f} MB")

        # 查询调用后余额并显示
        after_balance = get_wavespeed_balance()
        if before_balance is not None and after_balance is not None:
            display_balance(before_balance, after_balance, api_cost, f"图像生成 (镜头{shot_id})")
        log("=" * 60)

    # 返回公网URL，供I2V使用
    return image_url

@smart_retry(max_attempts=3, backoff_factor=2)
def generate_video(image_url, prompt, shot_id, shot_count, resolution="720p", camera_movement=None, background_prompt=None):
    """使用配置的模型生成视频（第二步：图像生成视频 或 直接文本生成视频）

    Args:
        image_url: 图像的公网URL（I2V时使用）或 None（T2V时）
        prompt: 原始提示词（场景描述）
        shot_id: 镜头ID
        shot_count: 总镜头数
        resolution: 视频分辨率，默认720p
        camera_movement: dict, 运镜信息 {'code': 'M1', 'name': '推进特写', 'description': '...'}
        background_prompt: str, 背景一致性提示（可选）
    """
    model_config = VIDEO_MODEL_CONFIG[CURRENT_VIDEO_MODEL]
    api_cost = get_video_cost(CURRENT_VIDEO_MODEL, resolution)

    log("-" * 30)
    log(f"🎬 正在生成镜头 {shot_id}/{shot_count} 的视频...")
    log(f"   模型: {CURRENT_VIDEO_MODEL} (成本${api_cost}, 预计{model_config['speed']})")
    log(f"   分辨率: {resolution}")

    # 查询调用前余额
    before_balance = get_wavespeed_balance()
    if before_balance is not None:
        log(f"   💰 调用前余额: ${before_balance:.4f}")

    url = f"https://api.wavespeed.ai{model_config['endpoint']}"
    headers = {
        "Authorization": f"Bearer {WAVESPEED_API_KEY}",
        "Content-Type": "application/json"
    }

    # 从模型配置中获取默认参数
    default_params = model_config.get('params', {}).copy()

    # 根据模型类型构建payload
    if model_config['type'] == 'i2v':
        log(f"   输入图像URL: {image_url[:80]}...")

        scene_prompt = prompt.strip() if isinstance(prompt, str) else ""

        # 使用运镜描述作为prompt（如果有）
        if camera_movement and 'description' in camera_movement:
            camera_prompt = camera_movement['description']
            camera_code = camera_movement.get('code', 'N/A')
            camera_name = camera_movement.get('name', 'N/A')
            log(f"   🎬 运镜模式: {camera_code} - {camera_name}")
            log(f"   📝 运镜描述: {camera_prompt[:100]}...")
        else:
            # 回退到默认prompt
            camera_prompt = "Camera movement with smooth motion, cinematic feel"
            log(f"   ⚠️  未找到运镜信息，使用默认prompt", "WARN")

        prompt_parts = []
        # 🎬 优先拼接背景一致性约束（如果有）
        if background_prompt:
            prompt_parts.append(f"BACKGROUND: {background_prompt.strip()}")
        if scene_prompt:
            prompt_parts.append(scene_prompt)
        if camera_prompt:
            prompt_parts.append(f"Camera movement: {camera_prompt}")
        final_prompt = "\n\n".join(prompt_parts) if prompt_parts else camera_prompt

        # 构建基础payload
        payload = {
            "image": image_url,
            "prompt": final_prompt,
        }
        log(f"   📝 场景+运镜提示: {final_prompt[:120]}...")

        # 根据模型添加特定参数
        if CURRENT_VIDEO_MODEL == 'hailuo-2.3-pro':
            # Hailuo特殊处理：没有resolution/duration，prompt可选
            if default_params.get('enable_prompt_expansion') is not None:
                payload["enable_prompt_expansion"] = default_params['enable_prompt_expansion']
        elif CURRENT_VIDEO_MODEL == 'veo-3.1-i2v':
            # VEO 3.1特殊参数
            payload["resolution"] = default_params.get('resolution', resolution)
            payload["duration"] = default_params.get('duration', VIDEO_DURATION_DEFAULT)
            payload["aspect_ratio"] = default_params.get('aspect_ratio', '16:9')
            payload["generate_audio"] = default_params.get('generate_audio', True)
            if default_params.get('negative_prompt'):
                payload["negative_prompt"] = default_params['negative_prompt']
            if default_params.get('seed', -1) != -1:
                payload["seed"] = default_params['seed']
            if default_params.get('last_image'):
                payload["last_image"] = default_params['last_image']
        else:
            # WAN 2.5/2.6 I2V等通用参数
            payload["resolution"] = resolution
            payload["duration"] = default_params.get('duration', VIDEO_DURATION_DEFAULT)
            payload["enable_prompt_expansion"] = default_params.get('enable_prompt_expansion', VIDEO_PROMPT_EXPANSION)
            payload["seed"] = default_params.get('seed', VIDEO_SEED_DEFAULT)

            # WAN 2.6特有参数
            if 'shot_type' in default_params:
                payload["shot_type"] = default_params['shot_type']

            # 可选参数
            if default_params.get('audio'):
                payload["audio"] = default_params['audio']
            if default_params.get('negative_prompt'):
                payload["negative_prompt"] = default_params['negative_prompt']

    else:  # t2v
        log(f"   提示词: {prompt[:80]}...")
        payload = {
            "prompt": prompt,
        }

        # WAN 2.6 T2V使用size而非resolution
        if CURRENT_VIDEO_MODEL == 'wan-2.6-t2v':
            # 将用户的resolution转换为size格式
            size_mapping = {
                "480p": "1280*720",   # 回退到720p
                "720p": "1280*720",
                "1080p": "1920*1080"
            }
            payload["size"] = default_params.get('size', size_mapping.get(resolution, "1280*720"))
            payload["duration"] = default_params.get('duration', VIDEO_DURATION_DEFAULT)
            payload["shot_type"] = default_params.get('shot_type', 'single')
            payload["enable_prompt_expansion"] = default_params.get('enable_prompt_expansion', VIDEO_PROMPT_EXPANSION)
            payload["seed"] = default_params.get('seed', VIDEO_SEED_DEFAULT)

            if default_params.get('audio'):
                payload["audio"] = default_params['audio']
            if default_params.get('negative_prompt'):
                payload["negative_prompt"] = default_params['negative_prompt']
        else:
            # 其他T2V模型（如有）
            payload["resolution"] = resolution
            payload["duration"] = default_params.get('duration', VIDEO_DURATION_DEFAULT)
            payload["enable_prompt_expansion"] = default_params.get('enable_prompt_expansion', VIDEO_PROMPT_EXPANSION)
            payload["seed"] = default_params.get('seed', VIDEO_SEED_DEFAULT)

    log(f"   📤 提交视频生成任务...")
    log(f"   🔍 调试payload: {payload}")  # 调试用
    # API限流控制
    video_limiter.acquire()
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    raw_result = response.json()

    # 统一解析响应格式
    result = parse_api_response(raw_result, f"视频生成-{CURRENT_VIDEO_MODEL}")

    # 提取并验证任务ID
    task_id = result.get('id')
    validate_task_id(task_id, "视频生成任务")

    log(f"   ✓ 任务已提交，ID: {task_id}")
    log(f"   ⏳ 预计等待时间: 2-3分钟")

    # 轮询等待任务完成（增加超时时间）
    video_url = wait_for_result(task_id, "视频", max_wait=MAX_WAIT_VIDEO)

    # 下载视频
    log(f"   📥 正在下载视频...")
    video_num = 50 + (shot_id - 1)
    video_file = WORK_DIR / f'{video_num:02d}_shot_{shot_id:02d}.mp4'
    download_file(video_url, video_file)

    file_size = video_file.stat().st_size / (1024 * 1024)
    log(f"✅ 镜头 {shot_id}/{shot_count} 视频已生成：{video_file}")
    log(f"   文件大小: {file_size:.2f} MB")

    # 查询调用后余额并显示
    after_balance = get_wavespeed_balance()
    if before_balance is not None and after_balance is not None:
        display_balance(before_balance, after_balance, api_cost, f"视频生成 (镜头{shot_id})")

    show_progress_bar(shot_id, shot_count, "📊 总体进度")
    log("-" * 30)
    return video_file

def generate_music():
    """生成背景音乐（WAN 2.6支持音视频同步，此处跳过单独音乐生成）"""
    print("🎵 背景音乐将在视频合成时添加...")
    # WAN 2.6支持原生音视频同步，但Hailuo不支持
    # 为简化流程，暂时跳过单独音乐生成，使用无声视频
    return None


class SequentialPollingCoordinator:
    """确保轮询按提交顺序串行进行"""

    def __init__(self):
        self._queue = queue.Queue()
        self._worker = None
        self._lock = threading.Lock()

    def _ensure_worker(self):
        with self._lock:
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._worker_loop, daemon=True)
                self._worker.start()

    def _worker_loop(self):
        while True:
            func, args, kwargs, done_event, result_holder = self._queue.get()
            try:
                result_holder["value"] = func(*args, **kwargs)
            except Exception as exc:
                result_holder["error"] = exc
            finally:
                done_event.set()
                self._queue.task_done()

    def run(self, func, *args, **kwargs):
        self._ensure_worker()
        done_event = threading.Event()
        result_holder = {}
        self._queue.put((func, args, kwargs, done_event, result_holder))
        done_event.wait()

        if "error" in result_holder:
            raise result_holder["error"]
        return result_holder.get("value")


polling_coordinator = SequentialPollingCoordinator()


def download_file(url, filepath):
    """下载文件"""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    with open(filepath, 'wb') as f:
        f.write(response.content)

def wait_for_result(task_id, result_type="视频", max_wait=None):
    """等待任务完成（通用函数，支持图像和视频，串行轮询）"""
    return polling_coordinator.run(_wait_for_result_core, task_id, result_type, max_wait)


def _wait_for_result_core(task_id, result_type="视频", max_wait=None):
    """实际轮询逻辑，保证单线程依次执行"""
    url = f"https://api.wavespeed.ai/api/v3/predictions/{task_id}/result"
    headers = {"Authorization": f"Bearer {WAVESPEED_API_KEY}"}

    start_time = time.time()
    check_interval = POLLING_INTERVAL
    retry_count = 0
    max_retries = MAX_NETWORK_RETRIES

    if max_wait is None:
        max_wait = MAX_WAIT_VIDEO if result_type == "视频" else MAX_WAIT_IMAGE

    log(f"   ⏳ 等待{result_type}生成完成 (任务ID: {task_id})...")

    while time.time() - start_time < max_wait:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            raw_result = response.json()

            retry_count = 0

            try:
                result = parse_api_response(raw_result, f"查询{result_type}状态")
            except ValueError as e:
                log(f"   ⚠️  API错误: {e}，继续等待...", "WARN")
                time.sleep(check_interval)
                continue

            status = result.get('status')

            if status == 'completed':
                outputs = result.get('outputs', [])
                if not outputs:
                    raise TaskFailedError(f"{result_type}生成完成但无输出，响应: {json.dumps(result, ensure_ascii=False)[:200]}")

                elapsed = int(time.time() - start_time)
                log(f"   ✅ 生成完成！用时 {elapsed} 秒")
                return outputs[0]

            if status == 'failed':
                error = result.get('error', '未知错误')
                raise TaskFailedError(f"{result_type}生成失败: {error}")

            elapsed = int(time.time() - start_time)
            remaining = max_wait - elapsed
            log(f"   ⏱️  状态: {status or 'processing'} | 已等待: {elapsed}s | 剩余: {remaining}s")

            time.sleep(check_interval)

        except requests.exceptions.RequestException as e:
            retry_count += 1
            if retry_count > max_retries:
                log(f"   ❌ 网络错误超过最大重试次数 ({max_retries})", "ERROR")
                raise

            wait_time = min(BACKOFF_SECONDS * retry_count, MAX_BACKOFF_SECONDS)
            log(f"   ⚠️  查询出错 (重试 {retry_count}/{max_retries}): {e}，{wait_time}秒后重试...", "WARN")
            time.sleep(wait_time)

    raise TimeoutError(f"{result_type}生成超时（超过{max_wait}秒）")

def merge_videos(shot_count):
    """使用FFmpeg Concat Demuxer合并视频片段（无损、快速）"""
    log("🎞️  正在合成最终视频...")

    try:
        import subprocess
        import imageio_ffmpeg

        # 获取ffmpeg路径
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        log(f"   🔧 使用FFmpeg: {Path(ffmpeg_bin).name}")

        # 检查视频文件
        video_files = []
        log(f"   📂 检查 {shot_count} 个镜头...")
        for i in range(1, shot_count + 1):
            video_num = 50 + (i - 1)
            video_file = WORK_DIR / f'{video_num:02d}_shot_{i:02d}.mp4'
            if video_file.exists():
                size_mb = video_file.stat().st_size / 1024 / 1024
                log(f"   ✓ 镜头 {i}/{shot_count}: {video_file.name} ({size_mb:.2f} MB)")
                video_files.append(video_file)
            else:
                log(f"   ⚠️  镜头 {i} 文件不存在: {video_file.name}", "WARN")

        if not video_files:
            raise ValueError("没有找到任何视频文件")

        # 创建FFmpeg concat文件列表
        filelist_path = WORK_DIR / '85_filelist.txt'
        with open(filelist_path, 'w') as f:
            for vf in video_files:
                f.write(f"file '{vf.name}'\n")

        log(f"   📝 创建文件列表: {filelist_path.name}")

        # 输出文件
        output_file = WORK_DIR / '90_final.mp4'

        # 执行FFmpeg合成
        log("   🔗 正在合成视频 (FFmpeg Concat Demuxer, Stream Copy)...")

        cmd = [
            ffmpeg_bin,
            "-f", "concat",
            "-safe", "0",
            "-i", "85_filelist.txt",
            "-c", "copy",  # stream copy，不重新编码，保持原质量
            "-y",
            "90_final.mp4"
        ]

        result = subprocess.run(
            cmd,
            cwd=str(WORK_DIR),
            capture_output=True,
            text=True,
            timeout=60
        )

        # 清理临时文件列表
        if filelist_path.exists():
            filelist_path.unlink()

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg执行失败: {result.stderr}")

        if not output_file.exists():
            raise RuntimeError("输出文件未生成")

        # 输出统计信息
        output_size_mb = output_file.stat().st_size / 1024 / 1024
        total_input_size = sum(vf.stat().st_size for vf in video_files) / 1024 / 1024

        log(f"✅ 最终视频已生成：{output_file.name}")
        log(f"   输入: {len(video_files)} 个视频片段")
        log(f"   输入总大小: {total_input_size:.2f} MB")
        log(f"   输出大小: {output_size_mb:.2f} MB")
        log(f"   合成方式: Stream Copy (无损)")

        return output_file

    except subprocess.TimeoutExpired:
        log(f"❌ 视频合成超时（>60秒）", "ERROR")
        raise
    except Exception as e:
        log(f"❌ 视频合成失败：{e}", "ERROR")
        raise

def batch_merge_all():
    """批量合成所有output子目录下的视频"""
    import subprocess
    import imageio_ffmpeg

    print("=" * 60)
    print("🚀 批量视频合成模式")
    print("=" * 60)
    print(f"📂 扫描目录: {OUTPUT_BASE.absolute()}\n")

    # 获取ffmpeg
    try:
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        print(f"❌ 无法获取ffmpeg: {e}")
        return 1

    # 查找所有aka-*子目录
    subdirs = sorted([d for d in OUTPUT_BASE.glob("aka-*") if d.is_dir()])

    if not subdirs:
        print("❌ 未找到任何aka-*子目录")
        return 1

    print(f"✓ 找到 {len(subdirs)} 个子目录\n")

    # 统计
    success_count = 0
    skip_count = 0
    fail_count = 0

    # 逐个处理
    for work_dir in subdirs:
        print(f"\n{'='*60}")
        print(f"📂 处理目录: {work_dir.name}")
        print(f"{'='*60}")

        # 检查是否已有合成视频
        output_file = work_dir / "90_final.mp4"
        if output_file.exists():
            size_mb = output_file.stat().st_size / 1024 / 1024
            print(f"   ✓ 已存在合成视频: {output_file.name} ({size_mb:.2f} MB)")
            print(f"   ⏭️  跳过此目录")
            skip_count += 1
            continue

        # 查找所有编号的镜头视频文件（50-69系列）
        video_files = sorted(work_dir.glob("[0-9][0-9]_shot_[0-9][0-9].mp4"))

        if not video_files:
            print(f"   ⚠️  未找到分镜头文件，跳过")
            skip_count += 1
            continue

        print(f"   📹 找到 {len(video_files)} 个分镜头:")
        total_input_size = 0
        for vf in video_files:
            size_mb = vf.stat().st_size / 1024 / 1024
            total_input_size += size_mb
            print(f"      - {vf.name}: {size_mb:.2f} MB")

        # 创建文件列表
        filelist_path = work_dir / "85_filelist.txt"
        with open(filelist_path, "w") as f:
            for vf in video_files:
                f.write(f"file '{vf.name}'\n")

        # 执行FFmpeg合成
        print(f"   🔗 开始合成...")

        cmd = [
            ffmpeg_bin,
            "-f", "concat",
            "-safe", "0",
            "-i", "85_filelist.txt",
            "-c", "copy",
            "-y",
            "90_final.mp4"
        ]

        try:
            start_time = datetime.now()

            result = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=60
            )

            # 清理临时文件
            if filelist_path.exists():
                filelist_path.unlink()

            if result.returncode != 0:
                print(f"   ❌ 合成失败: {result.stderr[:200]}")
                fail_count += 1
                continue

            if not output_file.exists():
                print(f"   ❌ 合成失败: 输出文件未生成")
                fail_count += 1
                continue

            # 统计信息
            elapsed = (datetime.now() - start_time).total_seconds()
            output_size_mb = output_file.stat().st_size / 1024 / 1024

            print(f"   ✅ 合成成功！")
            print(f"      输出: {output_file.name}")
            print(f"      输入大小: {total_input_size:.2f} MB")
            print(f"      输出大小: {output_size_mb:.2f} MB")
            print(f"      耗时: {elapsed:.1f}秒")

            success_count += 1

        except subprocess.TimeoutExpired:
            print(f"   ❌ 合成超时（>60秒）")
            fail_count += 1
        except Exception as e:
            print(f"   ❌ 合成失败: {e}")
            fail_count += 1

    # 输出总结
    print(f"\n{'='*60}")
    print(f"📊 批量合成完成")
    print(f"{'='*60}")
    print(f"   总计: {len(subdirs)} 个目录")
    print(f"   ✅ 成功合成: {success_count} 个")
    print(f"   ⏭️  已存在跳过: {skip_count} 个")
    print(f"   ❌ 失败: {fail_count} 个")

    # 列出所有合成视频
    all_finals = sorted(OUTPUT_BASE.glob("aka-*/90_final.mp4"))
    if all_finals:
        print(f"\n📹 所有合成视频:")
        for final in all_finals:
            size_mb = final.stat().st_size / 1024 / 1024
            print(f"   - {final.parent.name}/90_final.mp4 ({size_mb:.2f} MB)")

    return 0 if fail_count == 0 else 1

def _generate_single_narration(shot, actual_duration, framework, previous_narrations, shot_index, total_shots):
    """为单个镜头生成精确旁白

    Args:
        shot: dict, 镜头数据（包含id, summary_cn, description等）
        actual_duration: float, 视频实际时长（秒）
        framework: dict, 旁白框架（可选）
        previous_narrations: list, 前序旁白列表
        shot_index: int, 当前镜头索引（0-based）
        total_shots: int, 总镜头数

    Returns:
        str: 生成的旁白文本
    """
    # 从配置文件读取旁白语速
    audio_config = CONFIG.get('audio', {})
    CHARS_PER_SECOND = audio_config.get('chars_per_second', 3.0)

    # 计算目标字数（基于实际视频时长）
    target_chars = int(actual_duration * CHARS_PER_SECOND)
    min_chars = int(target_chars * 0.85)
    max_chars = int(target_chars * 1.15)

    llm_name = LLM_SETTINGS.get('name', CURRENT_LLM_PROVIDER)

    log(f"   📊 视频实际时长: {actual_duration:.2f}秒 → 目标字数: {target_chars} ({min_chars}-{max_chars})")

    # 获取框架指导信息
    framework_guidance = ""
    if framework and framework.get('shot_points'):
        shot_point = framework['shot_points'][shot_index]
        framework_guidance = f"""
【广告词框架指导】
整体主线：{framework.get('overall_tagline', '')}
语言风格：{framework.get('narration_style', '')}
本镜头要点：{shot_point.get('core_message', '')}
情感基调：{shot_point.get('emotion', '')}
与前后关系：{shot_point.get('connection', '')}
"""

    # 构建前文概要
    previous_context = ""
    if previous_narrations:
        previous_context = f"\n【前序旁白】（保持连贯，避免重复）\n" + "\n".join([f"镜头{idx+1}: \"{text}\"" for idx, text in enumerate(previous_narrations)])

    # 生成旁白（支持重试机制）
    narration_text = None
    max_retries = 2

    for attempt in range(max_retries + 1):
        narration_prompt = get_prompt(
            'narration_shot',
            scene_summary=shot['summary_cn'],
            shot_index=shot_index + 1,
            shot_total=total_shots,
            actual_duration=f"{actual_duration:.2f}",
            framework_guidance=framework_guidance,
            previous_context=previous_context,
            target_chars=target_chars,
            continuity="自然衔接" if previous_narrations else "震撼开场",
            emotion_arc=framework.get('emotion_arc', '递进') if framework else '递进',
            ending_requirement="结尾要有升华和余味，可用疑问或号召" if shot_index == total_shots - 1 else "为下一镜头埋下伏笔"
        )

        try:
            narration_text = llm_complete(
                narration_prompt,
                temperature=0.75,
                context=f"镜头{shot_index + 1}旁白"
            )

            # 清理文本
            narration_text = narration_text.strip('"').strip("'").strip()
            if '\n' in narration_text:
                narration_text = narration_text.split('\n')[0]
            narration_text = narration_text.replace('*', '').replace('_', '').replace('#', '').replace('`', '').strip()

            # 验证字数
            char_count = len(narration_text)
            if char_count > max_chars:
                # 智能截断：尝试在句号、逗号处截断
                truncate_pos = max_chars
                for i in range(max_chars-1, max(max_chars-10, 0), -1):
                    if narration_text[i] in '。！？，、':
                        truncate_pos = i + 1
                        break
                narration_text = narration_text[:truncate_pos]
                char_count = len(narration_text)
                log(f"   ⚠️  旁白字数超限，智能截断至{char_count}字", "WARN")

            # 验证时长
            approx_duration = char_count / CHARS_PER_SECOND
            duration_diff = abs(approx_duration - actual_duration)
            tolerance = actual_duration * 0.15  # 15%容差

            if duration_diff <= tolerance:
                log(f"   ✅ 旁白生成成功: {char_count}字, 约{approx_duration:.2f}s (实际视频{actual_duration:.2f}s, 误差{duration_diff:.2f}s)")
                break
            else:
                if attempt < max_retries:
                    # 调整目标字数
                    if approx_duration > actual_duration:
                        target_chars = int(target_chars * 0.9)
                        log(f"   🔄 重试 {attempt+1}/{max_retries}: 旁白过长，减少至{target_chars}字", "WARN")
                    else:
                        target_chars = int(target_chars * 1.1)
                        log(f"   🔄 重试 {attempt+1}/{max_retries}: 旁白过短，增加至{target_chars}字", "WARN")
                    continue
                else:
                    log(f"   ⚠️  已达最大重试次数，使用当前版本", "WARN")
                    break

        except Exception as e:
            log(f"   ❌ 旁白生成失败 (尝试{attempt+1}/{max_retries+1}): {e}", "ERROR")
            if attempt == max_retries:
                # 回退方案：使用场景摘要
                narration_text = shot['summary_cn'][:target_chars]
                log(f"   🔄 使用回退方案（场景摘要）", "WARN")
                break

    # 如果所有尝试都失败
    if narration_text is None:
        narration_text = shot['summary_cn'][:target_chars]

    return narration_text


def generate_narrations_for_videos(shots_data, video_durations, narration_framework):
    """基于实际视频时长生成完整旁白（一次性生成，不分镜头）

    Args:
        shots_data: dict, 分镜脚本数据（来自22_shots_script.json）
        video_durations: dict, {shot_id: actual_duration_seconds}
        narration_framework: dict, 广告词框架（来自21_narration_framework.json）

    Returns:
        dict: {"global": {'narration': text, 'video_duration': seconds, 'narration_chars': int}}
    """
    # 计算全片总时长
    total_duration = sum(video_durations.values())

    # 从配置读取旁白语速
    audio_config = CONFIG.get('audio', {})
    chars_per_second = audio_config.get('chars_per_second', 3.5)

    # 计算建议字数（仅作参考，不强制限制）
    suggested_chars = int(total_duration * chars_per_second)

    llm_name = LLM_SETTINGS.get('name', CURRENT_LLM_PROVIDER)

    log(f"🎤 生成完整旁白（一次性，不分镜头）...")
    log(f"   全片时长: {total_duration:.2f}秒")
    log(f"   建议字数: {suggested_chars}字左右 (语速{chars_per_second}字/秒)")
    log("")

    # 构建故事概览（用于prompt）
    story_overview = []
    for i, shot in enumerate(shots_data['shots'], 1):
        story_overview.append(f"镜头{i}: {shot['summary_cn']}")
    story_context = "\n".join(story_overview)

    # 获取框架信息
    framework_info = ""
    if narration_framework:
        framework_info = f"""
【广告词框架】
整体主线：{narration_framework.get('overall_tagline', '')}
语言风格：{narration_framework.get('narration_style', '')}
情感曲线：{narration_framework.get('emotion_arc', '')}
"""

    # 构建prompt（生成完整旁白）
    prompt = get_prompt(
        'full_narration',
        total_duration=f"{total_duration:.2f}",
        shot_count=len(shots_data['shots']),
        story_context=story_context,
        framework_info=framework_info,
        min_chars=max(suggested_chars - 10, 1),
        max_chars=suggested_chars + 5,
        chars_per_second=chars_per_second,
        suggested_chars=suggested_chars
    )

    try:
        log(f"   🎙️  调用{llm_name}生成完整旁白...")
        narration_text = llm_complete(prompt, temperature=0.8, context="完整旁白")

        # 清理文本
        narration_text = narration_text.strip('"').strip("'").strip()
        narration_text = narration_text.replace('*', '').replace('_', '').replace('#', '').replace('`', '').strip()
        # 移除可能的markdown段落分隔
        narration_text = narration_text.replace('\n\n', '').replace('\n', '')

        # 检查字数是否超出（如果超出20%以上，让LLM重新缩写）
        char_count = len(narration_text)
        max_chars_threshold = suggested_chars * 1.2  # 允许20%的超出

        if char_count > max_chars_threshold:
            log(f"   ⚠️  旁白超出过多({char_count}字 > {suggested_chars}字+20%)，请求{llm_name}缩写...", "WARN")

            # 让 LLM 缩写
            rewrite_prompt = get_prompt(
                'rewrite_narration',
                target_chars=suggested_chars,
                char_count=char_count,
                original_chars=char_count,
                original_text=narration_text
            )

            narration_text = llm_complete(rewrite_prompt, temperature=0.7, context="旁白缩写")

            # 再次清理
            narration_text = narration_text.strip('"').strip("'").strip()
            narration_text = narration_text.replace('*', '').replace('_', '').replace('#', '').replace('`', '').strip()
            narration_text = narration_text.replace('\n\n', '').replace('\n', '')

            char_count = len(narration_text)
            log(f"   ✅ 缩写完成，新字数: {char_count}字")

        approx_duration = char_count / chars_per_second

        log(f"   ✅ 旁白生成成功!")
        log(f"      字数: {char_count}字")
        log(f"      预计时长: {approx_duration:.2f}秒 (视频{total_duration:.2f}秒)")
        log(f"      旁白内容: {narration_text[:100]}{'...' if len(narration_text) > 100 else ''}")
        log("")

        # 返回完整旁白（使用"global"键）
        return {
            "global": {
                'narration': narration_text,
                'video_duration': total_duration,
                'narration_chars': char_count
            }
        }

    except Exception as e:
        log(f"   ❌ 旁白生成失败: {e}", "ERROR")
        # 回退方案：拼接所有镜头摘要
        fallback_text = "。".join([shot['summary_cn'] for shot in shots_data['shots']])
        log(f"   🔄 使用回退方案（拼接镜头摘要）", "WARN")
        return {
            "global": {
                'narration': fallback_text,
                'video_duration': total_duration,
                'narration_chars': len(fallback_text)
            }
        }


def main():
    """主流程"""
    global MAX_CONCURRENT_WORKERS, WORK_DIR, LOG_FILE, RUN_TIMESTAMP
    start_time = time.time()

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='AI视频生成系统 - 智能断点继续')
    parser.add_argument('--resume', type=str, metavar='DIR_NAME',
                       help='手动指定恢复的工作目录 (例如: aka-12221430)')
    parser.add_argument('--no-auto-resume', action='store_true',
                       help='禁用自动断点检测，强制创建新任务')
    args = parser.parse_args()

    # 初始化工作目录
    OUTPUT_BASE.mkdir(exist_ok=True)

    # 优先级：手动指定 > 自动检测 > 新建
    if args.resume:
        # 用户明确指定恢复目录
        WORK_DIR = OUTPUT_BASE / args.resume
        if not WORK_DIR.exists():
            print(f"❌ 错误: 指定的目录不存在: {WORK_DIR}")
            print(f"   请检查 output/ 目录下是否有 {args.resume}")
            return 1
        RUN_TIMESTAMP = args.resume.replace('aka-', '')
        print(f"🔄 手动恢复: {WORK_DIR.name}\n")
    elif not args.no_auto_resume:
        # 自动检测是否需要恢复
        resume_dir = auto_resume_check()
        if resume_dir:
            WORK_DIR = resume_dir
            RUN_TIMESTAMP = resume_dir.name.replace('aka-', '')
            print(f"🔄 自动恢复: {WORK_DIR.name}\n")
        else:
            # 开始新任务
            RUN_TIMESTAMP = datetime.now().strftime("%m%d%H%M")
            WORK_DIR = OUTPUT_BASE / f'aka-{RUN_TIMESTAMP}'
            WORK_DIR.mkdir(exist_ok=True)
            print(f"🆕 新建任务: {WORK_DIR.name}\n")
    else:
        # 用户禁用自动检测，强制新建
        RUN_TIMESTAMP = datetime.now().strftime("%m%d%H%M")
        WORK_DIR = OUTPUT_BASE / f'aka-{RUN_TIMESTAMP}'
        WORK_DIR.mkdir(exist_ok=True)
        print(f"🆕 新建任务: {WORK_DIR.name} (已禁用自动检测)\n")

    LOG_FILE = WORK_DIR / '01_log.txt'

    # 验证配置
    try:
        validate_config()
    except ValueError as e:
        print(str(e))
        print("\n请检查 .env 文件并确保所有必需的配置正确")
        return 1

    # 显示初始余额
    print()
    print("=" * 60)
    print("💰 账户余额查询")
    print("=" * 60)
    initial_balance = get_wavespeed_balance()
    if initial_balance is not None:
        print(f"{Colors.GREEN}✅ WavespeedAI 账户余额: ${initial_balance:.4f}{Colors.RESET}")
        if initial_balance < 1.0:
            print(f"{Colors.YELLOW}⚠️  余额较低，建议充值以确保任务顺利完成{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}⚠️  无法查询余额，将继续执行（可能是网络问题）{Colors.RESET}")
    print("=" * 60)
    print()

    # 尝试从YAML配置文件加载配置
    config_result = load_config_from_yaml('user.yaml')

    if config_result:
        # 从YAML成功加载
        user_config, concurrent_workers = config_result
        MAX_CONCURRENT_WORKERS = concurrent_workers

        # 如果user.yaml中有字幕配置，覆盖config.yaml中的字幕配置
        if 'subtitle' in user_config:
            if 'subtitle' not in CONFIG:
                CONFIG['subtitle'] = {}
            CONFIG['subtitle'].update(user_config['subtitle'])
    else:
        # 回退到交互式输入
        print(f"\n{Colors.YELLOW}⚠️  未找到或无法加载 user.yaml，切换到交互式配置模式{Colors.RESET}\n")
        print(f"{Colors.GRAY}提示：创建 user.yaml 文件可跳过交互式输入{Colors.RESET}")
        print(f"{Colors.GRAY}参考示例：复制并修改当前目录的 user.yaml{Colors.RESET}\n")

        # 用户交互：获取配置
        user_config = interactive_setup()

        # 询问并发线程数
        MAX_CONCURRENT_WORKERS = ask_concurrent_workers()

    # 清空旧日志
    if LOG_FILE.exists():
        LOG_FILE.unlink()

    log("=" * 60)
    log("🎬 AI视频生成系统 v2.0")
    log("=" * 60)
    log(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"运行ID: aka-{RUN_TIMESTAMP}")
    log(f"主题: {user_config['topic']}")
    log(f"风格: {STYLE_TEMPLATES[user_config['style']]['name']}")
    log(f"镜头数: {user_config['shot_count']}个")
    log(f"单镜头时长: {user_config['shot_duration']}秒")
    log(f"并发线程数: {MAX_CONCURRENT_WORKERS}")
    log(f"输出目录: {WORK_DIR.absolute()}")
    log(f"日志文件: {LOG_FILE.absolute()}")
    log("=" * 60)

    try:
        # 初始化音视频服务
        audio_config = CONFIG.get('audio', {}).copy()  # 复制以避免修改全局配置
        subtitle_config = CONFIG.get('subtitle', {})

        # 用户配置的音色优先级更高，覆盖默认配置
        if user_config.get('audio', {}).get('voice_name'):
            audio_config['voice_name'] = user_config['audio']['voice_name']
            log(f"✓ 使用用户指定音色: {audio_config['voice_name']}")

        voice_service = VoiceService(provider=audio_config.get('voice_provider', 'edge'))
        subtitle_service = SubtitleService(provider=subtitle_config.get('subtitle_provider', 'submaker'))
        video_composer = VideoComposer(temp_dir=str(WORK_DIR), config=CONFIG)

        log("✓ 音视频服务初始化完成")

        # 加载checkpoint
        checkpoint = load_checkpoint()

        # 阶段0: 一致性资产生成（如果启用）
        if user_config.get('character', {}).get('enabled'):
            # 检查checkpoint，看是否已生成参考图
            if checkpoint['stages'].get('character_reference', False):
                log("")
                log("="*60)
                log("👤 检测到已有参考图，跳过生成")
                log("="*60)
                # 从文件加载参考图信息
                ref_prompt_file = WORK_DIR / '12_character_reference_prompt.txt'
                dna_file = WORK_DIR / '10_character_dna.txt'
                ref_image_file = WORK_DIR / '29_shot_00_image.png'

                if ref_image_file.exists() and dna_file.exists():
                    # 加载DNA
                    with open(dna_file, 'r', encoding='utf-8') as f:
                        character_dna = f.read()

                    character_ref = {
                        'description_cn': user_config['character']['description'],
                        'prompt_en': user_config['character']['description'],
                        'image_url': str(ref_image_file)
                    }
                    user_config['character']['reference'] = character_ref
                    user_config['character']['dna'] = character_dna
                    log(f"   ✓ 已加载参考图: {ref_image_file.name}")
                    log(f"   ✓ 已加载角色DNA ({len(character_dna)} 字符)")
                    log("✓ 阶段0完成（从缓存加载）\n")
                else:
                    log("   ⚠️  参考图文件不完整，将重新生成", "WARN")
                    checkpoint['stages']['character_reference'] = False

            if not checkpoint['stages'].get('character_reference', False):
                character_image_path = user_config['character'].get('character_image')

                # 检查是否有可用的参考图
                if character_image_path:
                    log("")
                    log("="*60)
                    log("👤 阶段0: 准备主角参考图（使用提供的图片）")
                    log("="*60)
                    log(f"   参考图来源: {character_image_path}")

                    # 检查是 URL 还是本地文件
                    resource_pic_dir = Path(__file__).parent.parent / 'resource' / 'pic'
                    resource_pic_dir.mkdir(parents=True, exist_ok=True)

                    def copy_reference_to_resource(src_path: Path, extension: str) -> Path | None:
                        """将参考图拷贝到资源目录，使用15前缀"""
                        import shutil
                        dest_path = resource_pic_dir / f'15_character_reference{extension}'
                        shutil.copy(src_path, dest_path)
                        log(f"   ✓ 参考图已拷贝到资源目录: {dest_path.name}")
                        return dest_path

                    if character_image_path.startswith(('http://', 'https://')):
                        # URL 图片，下载到项目运行目录（仅用于本地查看进度）
                        log(f"   📥 检测到在线图片（URL），正在下载到本地...")

                        # 确定文件扩展名
                        url_lower = character_image_path.lower()
                        if '.png' in url_lower:
                            ext = '.png'
                        elif '.jpg' in url_lower or '.jpeg' in url_lower:
                            ext = '.jpg'
                        elif '.webp' in url_lower:
                            ext = '.webp'
                        else:
                            ext = '.jpg'  # 默认jpg

                        # 生成文件名（12开头）
                        downloaded_filename = f'12_character_reference{ext}'
                        downloaded_path = WORK_DIR / downloaded_filename

                        # 下载文件到本地（仅用于查看）
                        try:
                            download_file(character_image_path, downloaded_path)
                            log(f"   ✓ 图片已下载到项目目录: {downloaded_filename}")
                            try:
                                copy_reference_to_resource(downloaded_path, ext)
                            except Exception as e:
                                log(f"   ⚠️  拷贝到资源目录失败: {e}", "WARN")
                        except Exception as e:
                            log(f"   ⚠️  下载失败（不影响使用）: {e}", "WARN")

                        # API使用原始URL（不需要上传图床）
                        character_ref_image_path = character_image_path
                        log(f"   ✓ API将直接使用原始URL")
                    else:
                        # 本地文件，检查是否存在并复制到工作目录
                        char_img_file = Path(character_image_path)
                        if not char_img_file.exists():
                            log(f"❌ 主角参考图不存在: {character_image_path}", "ERROR")
                            raise FileNotFoundError(f"主角参考图文件不存在: {character_image_path}")

                        # 复制参考图到工作目录（保留原始扩展名）
                        import shutil
                        char_img_ext = char_img_file.suffix
                        work_char_img = WORK_DIR / f'character_reference{char_img_ext}'
                        shutil.copy(char_img_file, work_char_img)
                        log(f"   ✓ 参考图已拷贝到项目目录: {work_char_img.name}")
                        try:
                            copy_reference_to_resource(work_char_img, char_img_ext)
                        except Exception as e:
                            log(f"   ⚠️  拷贝到资源目录失败: {e}", "WARN")
                        character_ref_image_path = str(work_char_img)

                    # 使用参考图路径
                    character_ref = {
                        'description_cn': user_config['character']['description'],
                        'prompt_en': user_config['character']['description'],
                        'image_url': character_ref_image_path
                    }
                    character_dna = extract_character_dna(character_ref)

                    user_config['character']['reference'] = character_ref
                    user_config['character']['dna'] = character_dna
                    log("✓ 主角一致性资产准备完成（使用参考图）\n")
                else:
                    # 自动生成主角参考图
                    character_ref = generate_character_reference(
                        user_config['character']['description']
                    )
                    character_dna = extract_character_dna(character_ref)

                    # 更新config
                    user_config['character']['reference'] = character_ref
                    user_config['character']['dna'] = character_dna

                    log("✓ 主角一致性资产准备完成（已生成）\n")

                # 标记参考图阶段完成
                checkpoint['stages']['character_reference'] = True
                save_checkpoint(checkpoint)

        # 准备品牌资产
        brand_assets = prepare_brand_assets(user_config.get('brand', {}))

        # 阶段1: 生成故事化镜头脚本（支持断点续传）
        log("\n📋 阶段 1: 生成故事化镜头脚本")
        log("=" * 60)

        # 检查checkpoint，看分镜脚本是否已完成
        if checkpoint['stages'].get('shots_script', False):
            script_file = WORK_DIR / '22_shots_script.json'
            if script_file.exists():
                log("📂 检测到已有分镜脚本，跳过故事生成阶段")
                try:
                    with open(script_file, 'r', encoding='utf-8') as f:
                        shots_data = json.load(f)
                    shot_count = len(shots_data['shots'])
                    log(f"   已加载 {shot_count} 个镜头")
                    log(f"✓ 阶段1完成（从缓存加载）\n")
                except Exception as e:
                    log(f"⚠️  加载分镜脚本失败: {e}，将重新生成", "WARN")
                    checkpoint['stages']['shots_script'] = False
            else:
                log("   ⚠️  脚本文件不存在，将重新生成", "WARN")
                checkpoint['stages']['shots_script'] = False

        if not checkpoint['stages'].get('shots_script', False):
            shots_data = generate_shots_script(config=user_config)
            shot_count = user_config['shot_count']

            # 标记阶段完成
            checkpoint['stages']['story_outline'] = True
            checkpoint['stages']['narration_framework'] = True
            checkpoint['stages']['shots_script'] = True
            save_checkpoint(checkpoint)
            log(f"✓ 阶段1完成\n")

        # 获取已完成的镜头ID
        completed_ids = set(checkpoint.get('completed_shots', []))

        if completed_ids:
            log(f"📂 检测到检查点文件")
            log(f"   已完成镜头: {sorted(completed_ids)}")
            log(f"   将跳过已完成的镜头，继续未完成部分\n")

        # 过滤出待处理的镜头
        pending_shots = [shot for shot in shots_data['shots'] if shot['id'] not in completed_ids]

        if not pending_shots:
            log("✅ 所有镜头都已完成，跳到合成阶段\n")
        else:
            log(f"📋 需要处理 {len(pending_shots)}/{shot_count} 个镜头\n")

        # 阶段2: 生成图像和视频
        resolution = user_config['resolution']

        if USE_DIRECT_T2V:
            log("🎬 阶段 2: 生成视频（直接T2V）")
            log("-" * 60)
            log(f"使用方案2：速度优先 - WAN 2.6 T2V")
            log(f"需要生成 {shot_count} 个镜头")
            video_config = VIDEO_MODEL_CONFIG[CURRENT_VIDEO_MODEL]
            video_cost = get_video_cost(CURRENT_VIDEO_MODEL, resolution)
            log(f"预计每个镜头: {video_config['speed']}")
            log(f"单镜头成本: ${video_cost:.2f} ({resolution})")
            log(f"总成本: ${video_cost * shot_count:.2f}")
        else:
            log("🎬 阶段 2: 生成图像和视频（I2V两步流程）")
            log("-" * 60)
            log(f"使用方案1：性价比方案")
            log(f"需要生成 {shot_count} 个镜头")
            image_config = IMAGE_MODEL_CONFIG[CURRENT_IMAGE_MODEL]
            video_config = VIDEO_MODEL_CONFIG[CURRENT_VIDEO_MODEL]
            video_cost = get_video_cost(CURRENT_VIDEO_MODEL, resolution)

            # 计算总成本（包括主角参考图）
            character_ref_cost = image_config['cost'] if user_config.get('character', {}).get('enabled') else 0
            total_cost = character_ref_cost + (image_config['cost'] + video_cost) * shot_count

            log(f"图像模型: {CURRENT_IMAGE_MODEL} (${image_config['cost']}/个)")
            log(f"视频模型: {CURRENT_VIDEO_MODEL} (${video_cost:.2f}/个 @ {resolution})")
            log(f"单镜头成本: ${image_config['cost'] + video_cost:.2f}")
            if character_ref_cost > 0:
                log(f"主角参考图: ${character_ref_cost:.2f}")
            log(f"预计总成本: ${total_cost:.2f}")

        # 记录成功和失败的镜头
        successful_shots = list(completed_ids)  # 已完成的镜头
        failed_shots = checkpoint.get('failed_shots', [])

        if USE_DIRECT_T2V:
            # 方案2: 直接T2V - 并发处理
            shots_with_images = [(shot, None) for shot in pending_shots]

            if shots_with_images:
                # 并发生成所有视频（T2V，无需图像）
                video_results, video_failures = generate_videos_parallel(shots_with_images, shot_count, user_config['resolution'])

                # 更新成功列表
                for shot_id in video_results.keys():
                    successful_shots.append(shot_id)

                # 更新失败列表
                failed_shots.extend(video_failures)

                # 保存检查点
                checkpoint['completed_shots'] = successful_shots
                checkpoint['failed_shots'] = failed_shots
                save_checkpoint(checkpoint)
                log(f"   💾 检查点已保存")

        else:
            # 方案1: I2V两步模式 - 图像并发，视频并发
            log("🎨 阶段 3a: 并发生成图像")
            log("-" * 60)

            # 检查已存在的图像文件
            image_urls = {}
            shots_need_images = []

            for shot in pending_shots:
                image_num = 30 + (shot['id'] - 1)
                image_file = WORK_DIR / f"{image_num:02d}_shot_{shot['id']:02d}_image.png"
                if image_file.exists():
                    # 图像已存在，需要上传到图床获取公网URL（用于I2V）
                    log(f"✓ 镜头 {shot['id']} 图像已存在，正在上传获取公网URL...")
                    try:
                        image_url = upload_image_to_cloudinary(str(image_file))
                        image_urls[shot['id']] = image_url
                        log(f"   ✓ 已上传: {image_url[:70]}...")
                    except Exception as e:
                        log(f"   ⚠️  上传失败: {e}，将重新生成图像", "WARN")
                        shots_need_images.append(shot)
                else:
                    shots_need_images.append(shot)

            # 并发生成缺失的图像
            if shots_need_images:
                log(f"📋 需要生成 {len(shots_need_images)}/{len(pending_shots)} 个图像")

                # 获取主角参考图路径（如果启用）
                character_image_path = None
                if user_config.get('character', {}).get('enabled'):
                    character_ref = user_config.get('character', {}).get('reference', {})
                    character_image_path = character_ref.get('image_url')

                new_image_urls = generate_images_parallel(shots_need_images, shot_count, character_image_path)
                image_urls.update(new_image_urls)
            else:
                log("✓ 所有图像都已存在，跳过图像生成")

            log("\n🎬 阶段 3b: 并发生成视频")
            log("-" * 60)

            # 准备并发生成数据（只处理图像生成成功的镜头）
            shots_with_images = [
                (shot, image_urls.get(shot['id']))
                for shot in pending_shots
                if shot['id'] in image_urls
            ]

            if not shots_with_images:
                log("⚠️  没有可用的图像，跳过视频生成", "WARN")
            else:
                # 并发生成所有视频
                video_results, video_failures = generate_videos_parallel(shots_with_images, shot_count, user_config['resolution'])

                # 更新成功列表
                for shot_id in video_results.keys():
                    successful_shots.append(shot_id)

                # 更新失败列表
                failed_shots.extend(video_failures)

                # 保存检查点
                checkpoint['completed_shots'] = successful_shots
                checkpoint['failed_shots'] = failed_shots
                save_checkpoint(checkpoint)
                log(f"   💾 检查点已保存")

        # 报告结果
        log(f"\n📊 生成结果汇总:")
        log(f"   ✅ 成功: {len(successful_shots)}/{shot_count}")
        log(f"   ❌ 失败: {len(failed_shots)}/{shot_count}")

        if failed_shots:
            log(f"\n⚠️  失败的镜头:")
            for shot_id, error in failed_shots:
                log(f"   - 镜头 {shot_id}: {error[:100]}...")

        if len(successful_shots) == 0:
            raise RuntimeError("所有镜头都生成失败，无法继续")

        # 标记图像和视频生成完成
        checkpoint['stages']['images_generated'] = True
        checkpoint['stages']['videos_generated'] = True
        save_checkpoint(checkpoint)

        log(f"✓ 阶段2完成\n")

        # 阶段2.5: 添加品牌元素（如果启用）
        if brand_assets.get('enabled'):
            if not checkpoint['stages'].get('brand_elements', False):
                log("🏢 阶段 2.5: 添加品牌元素")
                log("-" * 60)

                # 为所有已生成的镜头添加品牌
                for shot_id in range(1, shot_count + 1):
                    video_num = 50 + (shot_id - 1)
                    video_path = WORK_DIR / f'{video_num:02d}_shot_{shot_id:02d}.mp4'

                    if video_path.exists():
                        log(f"   🎨 为镜头 {shot_id}/{shot_count} 添加品牌logo...")
                        add_brand_overlay(str(video_path), brand_assets)
                    else:
                        log(f"   ⏭️  镜头 {shot_id} 不存在，跳过")

                checkpoint['stages']['brand_elements'] = True
                save_checkpoint(checkpoint)
                log(f"✓ 阶段2.5完成\n")
            else:
                log("📂 品牌元素已添加，跳过\n")

        # 统计视频时长（用于全片旁白）
        log("⏱️  统计视频时长并准备全片拼接...")
        video_durations = {}
        total_video_duration = 0.0
        shot_durations_list = []
        for i in range(1, shot_count + 1):
            video_num = 50 + (i - 1)
            vf = WORK_DIR / f"{video_num:02d}_shot_{i:02d}.mp4"
            if vf.exists():
                dur = get_video_duration_seconds(vf)
                video_durations[i] = dur
                shot_durations_list.append(dur)
                total_video_duration += dur
                log(f"   镜头 {i}: {dur:.2f}s")
            else:
                log(f"   ⚠️ 镜头 {i} 视频缺失，跳过时长统计", "WARN")
                shot_durations_list.append(0.0)

        log(f"⏱️  全片时长（静音版）: {total_video_duration:.2f}s\n")

        # 阶段2.6: 基于实际视频时长生成精确旁白
        log("🎤 阶段 2.6: 基于实际视频时长生成精确旁白")
        log("-" * 60)

        narrations_file = WORK_DIR / '70_narrations.json'
        if checkpoint['stages'].get('narrations_generated', False) and narrations_file.exists():
            log("📂 检测到已有旁白文件，跳过生成")
            with open(narrations_file, 'r', encoding='utf-8') as f:
                narrations_data = json.load(f)
            # 适配新旧格式
            if "global" in narrations_data:
                char_count = narrations_data["global"]['narration_chars']
                log(f"   已加载完整旁白 ({char_count}字)")
            else:
                log(f"   已加载旁白 ({len(narrations_data)}个镜头，旧格式)")
        else:
            # 加载旁白框架（如果存在）
            narration_framework_file = WORK_DIR / '21_narration_framework.json'
            narration_framework = None
            if narration_framework_file.exists():
                with open(narration_framework_file, 'r', encoding='utf-8') as f:
                    narration_framework = json.load(f)

            # 生成旁白
            narrations_data = generate_narrations_for_videos(
                shots_data=shots_data,
                video_durations=video_durations,
                narration_framework=narration_framework
            )

            # 保存到文件
            checkpoint['stages']['narrations_generated'] = True
            save_checkpoint(checkpoint)
            with open(narrations_file, 'w', encoding='utf-8') as f:
                json.dump(narrations_data, f, indent=2, ensure_ascii=False)
            log(f"   旁白已保存到: {narrations_file.name}")

        log(f"✓ 阶段2.6完成\n")

        # 阶段3: 整条旁白与字幕（单条音轨，保持同步）
        log("🎤 阶段 3: 整条旁白与字幕")
        log("=" * 60)

        global_audio = WORK_DIR / "70_global_narration.mp3"
        global_subtitle = WORK_DIR / "71_global_subtitle.srt"

        if checkpoint['stages'].get('audio_subtitle', False) and global_audio.exists() and global_subtitle.exists():
            log("✓ 检测到全片旁白与字幕，跳过生成")
            # 读取音频时长
            from moviepy.editor import AudioFileClip
            with AudioFileClip(str(global_audio)) as audio_clip:
                audio_duration = audio_clip.duration
        else:
            sentences = generate_global_narration(shots_data, video_durations)

            full_text = "\n".join(sentences)
            log("   🎙️  调用TTS生成整片旁白音频...")
            sub_maker, audio_duration = voice_service.generate_audio(
                text=full_text,
                output_file=str(global_audio),
                voice_name=audio_config.get('voice_name', 'zh-CN-XiaoxiaoNeural')
            )

            if not sub_maker:
                log("❌ 整片旁白生成失败，终止", "ERROR")
                return 1

            raw_srt = WORK_DIR / "73_global_subtitle_raw.srt"
            write_srt_from_submaker(sub_maker, raw_srt)

            # 目标时长：全片时长减去2秒缓冲（精确控制）
            target_total = total_video_duration - 2.0
            if target_total <= 0:
                target_total = 0.5

            scaled = False
            speed_factor = 1.0
            if audio_duration > target_total:
                speed_factor = min(1.8, audio_duration / target_total)
                adjusted = WORK_DIR / "72_global_narration_speed.mp3"
                if speedup_audio_file(global_audio, adjusted, speed_factor):
                    global_audio.unlink(missing_ok=True)
                    adjusted.rename(global_audio)
                    audio_duration = audio_duration / speed_factor
                    scaled = True
                    log(f"   ⚠️  旁白超时，已加速 {speed_factor:.2f}x → {audio_duration:.2f}s")
                else:
                    log("   ⚠️  加速失败，继续使用原始音频", "WARN")

            if scaled:
                rescale_srt_timestamps(str(raw_srt), str(global_subtitle), 1 / speed_factor)
            else:
                raw_srt.rename(global_subtitle)
            raw_srt.unlink(missing_ok=True)

            checkpoint['stages']['audio_subtitle'] = True
            save_checkpoint(checkpoint)
            log(f"✓ 阶段3完成（旁白 {audio_duration:.2f}s）\n")

        # 阶段4: 整片音视频合成
        log("🎞️  阶段 4: 整片音视频合成")
        log("-" * 60)

        # 4a. 拼接所有镜头（静音/已加品牌）
        log("🎞️  步骤4a: 拼接所有镜头...")
        video_files = []
        for i in range(1, shot_count + 1):
            video_num = 50 + (i - 1)
            shot_path = WORK_DIR / f"{video_num:02d}_shot_{i:02d}.mp4"
            if shot_path.exists():
                video_files.append(str(shot_path))
            else:
                log(f"  ⚠️  镜头 {i} 视频缺失，跳过", "WARN")

        temp_output = WORK_DIR / "80_temp_concat.mp4"
        if video_files:
            log(f"  🎬 拼接 {len(video_files)} 个镜头...")
            success = video_composer.concatenate_videos(video_files, str(temp_output))
        else:
            success = False

        if success:
            # 4b. 叠加整片旁白
            temp_with_audio = WORK_DIR / "81_temp_with_audio.mp4"
            global_audio = WORK_DIR / "70_global_narration.mp3"
            if global_audio.exists():
                log("🎙️  步骤4b: 叠加整片旁白音频...")
                success_audio = video_composer.add_audio_to_video(
                    str(temp_output),
                    str(global_audio),
                    str(temp_with_audio)
                )
                if not success_audio:
                    log("❌  整片旁白添加失败", "ERROR")
                    temp_with_audio = temp_output
            else:
                log("⚠️  未找到整片旁白音频，直接使用静音拼接视频", "WARN")
                temp_with_audio = temp_output

            # 4c. 添加整片字幕
            final_no_bgm = WORK_DIR / "82_temp_with_subtitle.mp4"
            global_subtitle = WORK_DIR / "71_global_subtitle.srt"
            if global_subtitle.exists():
                log("📝 步骤4c: 添加整片字幕...")
                font_config = subtitle_config.get('font_name', '')
                if font_config and not font_config.startswith('/') and not font_config.endswith('.ttc') and not font_config.endswith('.ttf'):
                    font_path = VideoComposer.get_system_font()
                else:
                    font_path = font_config if font_config else VideoComposer.get_system_font()

                success_sub = video_composer.add_subtitles_to_video(
                    str(temp_with_audio),
                    str(global_subtitle),
                    str(final_no_bgm),
                    style_config={
                        'font': font_path,
                        'fontsize': subtitle_config.get('font_size', 48),
                        'color': subtitle_config.get('font_color', 'white'),
                        'stroke_color': subtitle_config.get('outline_color', 'black'),
                        'stroke_width': subtitle_config.get('outline_width', 2),
                    }
                )
                if not success_sub:
                    log("⚠️  字幕添加失败，使用无字幕版本", "WARN")
                    final_no_bgm = temp_with_audio
            else:
                log("⚠️  未找到整片字幕，跳过字幕添加", "WARN")
                final_no_bgm = temp_with_audio

            # 4d. 添加背景音乐（可选）
            final_video_path = WORK_DIR / "90_final.mp4"
            if audio_config.get('enable_background_music', False):
                log("\n🎵 步骤4d: 添加背景音乐...")
                music_service = MusicService(
                    music_dir=audio_config.get('music_dir', './resource/songs')
                )
                music_added = False
                max_music_attempts = 3
                available_music = music_service.get_available_music(validate=True)

                if not available_music:
                    log("  ℹ️  未找到有效的背景音乐文件，跳过")
                    final_no_bgm.rename(final_video_path)
                else:
                    # 智能音乐匹配（新功能）
                    use_intelligent = audio_config.get('use_intelligent_music_matching', False)

                    if use_intelligent:
                        log("  🧠 使用智能音乐匹配（基于旁白音频分析）...")

                        # 收集旁白音频文件（优先使用全局旁白）
                        narration_audio_files = []
                        global_narration = WORK_DIR / "70_global_narration.mp3"
                        if global_narration.exists():
                            narration_audio_files.append(global_narration)
                        else:
                            # 降级：尝试收集分镜头旁白（旧版本兼容）
                            for i in range(1, shot_count + 1):
                                audio_num = 30 + (i - 1)
                                audio_path = WORK_DIR / f"{audio_num:02d}_narration_{i:02d}.mp3"
                                if audio_path.exists():
                                    narration_audio_files.append(audio_path)

                        if narration_audio_files:
                            music_file_path = music_service.select_music_intelligent(
                                narration_audio_files=narration_audio_files,
                                visual_style=user_config.get('style')
                            )
                        else:
                            log("  ⚠️  未找到旁白音频文件，降级到关键词匹配", "WARN")
                            use_intelligent = False

                    if not use_intelligent:
                        log("  🔍 使用关键词匹配...")
                        music_file_path = music_service.select_music(
                            style=user_config.get('style'),
                            prefer_style=audio_config.get('prefer_style_match', True)
                        )

                    # 尝试添加音乐（重试机制）
                    for attempt in range(max_music_attempts):
                        if attempt > 0:
                            # 第一次尝试失败后，重新选择音乐
                            log(f"  🔄 尝试选择其他音乐 ({attempt + 1}/{max_music_attempts})...")
                            music_file_path = music_service.select_music(
                                style=user_config.get('style'),
                                prefer_style=audio_config.get('prefer_style_match', True)
                            )

                        if not music_file_path:
                            log("  ℹ️  未找到背景音乐，跳过")
                            final_no_bgm.rename(final_video_path)
                            break

                        music_file = str(music_file_path)
                        final_output = final_video_path

                        log(f"  🎵 尝试添加音乐: {music_file_path.name}")
                        success = video_composer.add_background_music(
                            str(final_no_bgm),
                            music_file,
                            str(final_output),
                            voice_volume=audio_config.get('voice_volume', 1.0),
                            music_volume=audio_config.get('music_volume', 0.25)
                        )

                        if success:
                            log("  ✅ 背景音乐添加成功")
                            music_added = True
                            break
                        else:
                            log(f"  ⚠️  音乐添加失败: {music_file_path.name}", "WARN")
                            if attempt < max_music_attempts - 1:
                                log(f"  🔄 尝试选择其他音乐 ({attempt + 2}/{max_music_attempts})...")
                                if music_file_path in available_music:
                                    available_music.remove(music_file_path)
                            else:
                                log("  ⚠️  达到最大重试次数，使用无背景音乐版本", "WARN")
                                final_no_bgm.rename(final_video_path)
            else:
                # 不添加背景音乐，直接重命名
                final_no_bgm.rename(final_video_path)
                log("  ℹ️  背景音乐功能未启用")

            # 4e. 添加Logo动画（可选，片尾淡入）
            logo_config = CONFIG.get('logo', {})
            if logo_config.get('enabled', False):
                log("\n🎨 步骤4e: 添加Logo动画...")
                logo_file_path = Path(logo_config.get('logo_file', './resource/logo/aka.jpg'))

                # 检查logo文件是否存在
                if logo_file_path.exists():
                    current_video = final_video_path
                    temp_logo_output = WORK_DIR / "83_temp_with_logo.mp4"

                    if not current_video.exists():
                        log("  ⚠️  未找到最终视频，跳过Logo动画", "WARN")
                    else:
                        success = video_composer.add_logo_animation(
                            video_file=str(current_video),
                            logo_file=str(logo_file_path),
                            output_file=str(temp_logo_output),
                            position=logo_config.get('position', 'end'),
                            duration=logo_config.get('duration', 2.0),
                            fadein_time=logo_config.get('fadein_time', 1.0),
                            fadeout_time=logo_config.get('fadeout_time', 0.0),
                            logo_scale=logo_config.get('logo_scale', 0.3)
                        )

                        if success:
                            # 删除旧文件，重命名新文件
                            current_video.unlink()
                            temp_logo_output.rename(current_video)
                            log("  ✅ Logo动画添加成功")
                        else:
                            log("  ⚠️  Logo添加失败，使用无Logo版本", "WARN")
                            # 删除失败的临时文件
                            if temp_logo_output.exists():
                                temp_logo_output.unlink()
                else:
                    log(f"  ⚠️  Logo文件不存在: {logo_file_path}", "WARN")
                    log("  ℹ️  跳过Logo添加")
            else:
                log("  ℹ️  Logo功能未启用")
        else:
            log("  ❌ 没有可用的视频文件，无法合成", "ERROR")

        checkpoint['stages']['final_composition'] = True
        save_checkpoint(checkpoint)
        log(f"✓ 阶段4完成\n")

        # 成本验证
        log("")
        log("=" * 60)
        log("💰 成本验证")
        log("=" * 60)
        final_balance = get_wavespeed_balance()
        if initial_balance is not None and final_balance is not None:
            actual_cost = initial_balance - final_balance
            log(f"初始余额: ${initial_balance:.4f}")
            log(f"最终余额: ${final_balance:.4f}")
            log(f"实际花费: ${actual_cost:.4f}")

            # 计算预期成本
            image_config = IMAGE_MODEL_CONFIG.get(CURRENT_IMAGE_MODEL, {})
            video_cost_per_shot = get_video_cost(CURRENT_VIDEO_MODEL, resolution)
            character_ref_cost = image_config.get('cost', 0) if user_config.get('character', {}).get('enabled') else 0

            if USE_DIRECT_T2V:
                expected_cost = video_cost_per_shot * shot_count
            else:
                expected_cost = character_ref_cost + (image_config.get('cost', 0) + video_cost_per_shot) * shot_count

            log(f"预期花费: ${expected_cost:.4f}")

            # 计算差异
            diff = actual_cost - expected_cost
            diff_percent = (diff / expected_cost * 100) if expected_cost > 0 else 0

            if abs(diff_percent) > 10:  # 差异超过10%
                if diff > 0:
                    log(f"⚠️  实际成本高于预期: +${diff:.4f} (+{diff_percent:.1f}%)", "WARN")
                else:
                    log(f"✅ 实际成本低于预期: ${diff:.4f} ({diff_percent:.1f}%)")
            else:
                log(f"✅ 成本符合预期 (差异: {diff_percent:.1f}%)")
        else:
            log("⚠️  无法验证成本（余额查询失败）", "WARN")
        log("=" * 60)
        log("")

        # 完成
        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)

        log("=" * 60, "SUCCESS")
        log("🎉 广告视频制作完成！", "SUCCESS")
        log("=" * 60, "SUCCESS")
        log(f"✓ 运行ID: aka-{RUN_TIMESTAMP}", "SUCCESS")
        log(f"✓ 输出目录: {WORK_DIR.absolute()}", "SUCCESS")
        log(f"✓ 最终视频: {WORK_DIR}/90_final.mp4", "SUCCESS")
        log(f"✓ 日志文件: {LOG_FILE}", "SUCCESS")
        log(f"✓ 总耗时: {mins}分{secs}秒", "SUCCESS")
        log(f"✓ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "SUCCESS")
        log("=" * 60, "SUCCESS")

    except Exception as e:
        elapsed = int(time.time() - start_time)
        log(f"\n❌ 发生错误：{e}", "ERROR")
        import traceback
        error_trace = traceback.format_exc()
        log(error_trace, "ERROR")
        log(f"失败时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log(f"已运行: {elapsed}秒")
        log(f"输出目录: {WORK_DIR.absolute()}")
        log(f"日志文件: {LOG_FILE}")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
