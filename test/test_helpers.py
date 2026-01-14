"""
测试辅助工具函数

提供常用的测试断言、数据生成和验证函数
"""
from typing import Dict, Any, Optional
import re


# ============================================================================
# 数据验证
# ============================================================================

def assert_valid_url(url: str, protocol: str = "https"):
    """验证 URL 格式"""
    assert url.startswith(f"{protocol}://"), f"URL 必须以 {protocol}:// 开头: {url}"
    assert len(url) > len(f"{protocol}://"), f"URL 不能为空: {url}"


def assert_valid_job_id(job_id: str):
    """验证 job_id 格式"""
    assert job_id.startswith("aka-"), f"job_id 必须以 aka- 开头: {job_id}"
    assert len(job_id) > 4, f"job_id 太短: {job_id}"


def assert_valid_trace_id(trace_id: str):
    """验证 trace_id 格式"""
    assert trace_id.startswith("trace-"), f"trace_id 必须以 trace- 开头: {trace_id}"


def assert_valid_task_status(status: str):
    """验证任务状态"""
    valid_statuses = [
        "pending",
        "avatar_generating",
        "avatar_ready",
        "speech_generating",
        "speech_ready",
        "video_rendering",
        "finished",
        "failed"
    ]
    assert status in valid_statuses, f"无效的状态: {status}"


def assert_valid_cost(cost: float):
    """验证成本值"""
    assert cost >= 0, f"成本不能为负数: {cost}"
    assert cost < 100, f"成本异常高: {cost}"


def assert_valid_duration(duration: float):
    """验证时长"""
    assert duration > 0, f"时长必须大于 0: {duration}"
    assert duration < 3600, f"时长异常长（超过1小时）: {duration}"


# ============================================================================
# API 响应验证
# ============================================================================

def assert_valid_seedream_response(response: Dict[str, Any]):
    """验证 Seedream API 响应格式"""
    assert "output" in response, "响应缺少 output 字段"
    output = response["output"]
    assert "image_url" in output, "output 缺少 image_url 字段"
    assert_valid_url(output["image_url"])
    assert output.get("width") == 1024, "宽度应为 1024"
    assert output.get("height") == 1024, "高度应为 1024"


def assert_valid_minimax_response(response: Dict[str, Any]):
    """验证 MiniMax TTS API 响应格式"""
    assert "output" in response, "响应缺少 output 字段"
    output = response["output"]
    assert "audio_url" in output, "output 缺少 audio_url 字段"
    assert_valid_url(output["audio_url"])
    assert "duration" in output, "output 缺少 duration 字段"
    assert_valid_duration(output["duration"])


def assert_valid_infinitetalk_response(response: Dict[str, Any]):
    """验证 Infinitetalk API 响应格式"""
    if response.get("state") == "completed":
        assert "output" in response, "完成的任务缺少 output 字段"
        output = response["output"]
        assert "video_url" in output, "output 缺少 video_url 字段"
        assert_valid_url(output["video_url"])
        assert "duration" in output, "output 缺少 duration 字段"
        assert_valid_duration(output["duration"])


def assert_valid_task_json(task_data: Dict[str, Any]):
    """验证 task.json 数据格式"""
    required_fields = ["job_id", "status", "created_at", "params"]
    for field in required_fields:
        assert field in task_data, f"task.json 缺少必填字段: {field}"

    assert_valid_job_id(task_data["job_id"])
    assert_valid_task_status(task_data["status"])
    assert "trace_id" in task_data, "task.json 缺少 trace_id"
    assert_valid_trace_id(task_data["trace_id"])

    # 验证 params
    params = task_data["params"]
    assert "avatar_mode" in params, "params 缺少 avatar_mode"
    assert params["avatar_mode"] in ["upload", "prompt"], f"无效的 avatar_mode: {params['avatar_mode']}"
    assert "speech_text" in params, "params 缺少 speech_text"
    assert len(params["speech_text"]) > 0, "speech_text 不能为空"


# ============================================================================
# 参数验证
# ============================================================================

def assert_valid_create_task_params(params: Dict[str, Any]):
    """验证创建任务的参数"""
    # 必填字段
    assert "avatar_mode" in params, "缺少 avatar_mode"
    assert "speech_text" in params, "缺少 speech_text"
    assert "voice_id" in params, "缺少 voice_id"

    # avatar_mode 验证
    avatar_mode = params["avatar_mode"]
    assert avatar_mode in ["upload", "prompt"], f"无效的 avatar_mode: {avatar_mode}"

    if avatar_mode == "prompt":
        assert "avatar_prompt" in params, "avatar_mode=prompt 时必须提供 avatar_prompt"
        assert len(params["avatar_prompt"]) > 0, "avatar_prompt 不能为空"
    elif avatar_mode == "upload":
        assert "avatar_upload_url" in params, "avatar_mode=upload 时必须提供 avatar_upload_url"
        assert_valid_url(params["avatar_upload_url"])

    # 范围验证
    if "speed" in params:
        speed = params["speed"]
        assert 0.5 <= speed <= 2.0, f"speed 必须在 0.5-2.0 之间: {speed}"

    if "pitch" in params:
        pitch = params["pitch"]
        assert -12 <= pitch <= 12, f"pitch 必须在 -12 至 12 之间: {pitch}"

    if "emotion" in params:
        emotion = params["emotion"]
        assert emotion in ["neutral", "happy", "sad", "angry"], f"无效的 emotion: {emotion}"

    if "resolution" in params:
        resolution = params["resolution"]
        assert resolution in ["720p", "1080p"], f"无效的 resolution: {resolution}"


# ============================================================================
# Mock 数据生成
# ============================================================================

def generate_mock_job_id(prefix: str = "aka-test") -> str:
    """生成 mock job_id"""
    import time
    timestamp = int(time.time() * 1000)
    return f"{prefix}-{timestamp}"


def generate_mock_trace_id(prefix: str = "trace-test") -> str:
    """生成 mock trace_id"""
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def generate_mock_task_params(**overrides) -> Dict[str, Any]:
    """生成 mock 任务参数"""
    defaults = {
        "avatar_mode": "prompt",
        "avatar_prompt": "专业女性播音员，微笑，正面照",
        "speech_text": "这是一段测试文本。",
        "voice_id": "female-shaonv",
        "resolution": "720p",
        "speed": 1.0,
        "pitch": 0,
        "emotion": "neutral",
        "seed": 42,
        "mask_image": None
    }
    defaults.update(overrides)
    return defaults


# ============================================================================
# 错误断言
# ============================================================================

def assert_error_response(response: Dict[str, Any], expected_code: Optional[str] = None):
    """验证错误响应格式"""
    assert "error" in response, "错误响应缺少 error 字段"
    error = response["error"]
    assert "code" in error, "error 缺少 code 字段"
    assert "message" in error, "error 缺少 message 字段"

    if expected_code:
        assert error["code"] == expected_code, f"期望错误码 {expected_code}，实际 {error['code']}"


def assert_has_trace_id(response: Dict[str, Any]):
    """验证响应包含 trace_id"""
    assert "trace_id" in response, "响应缺少 trace_id"
    assert_valid_trace_id(response["trace_id"])


# ============================================================================
# 时间相关
# ============================================================================

def assert_valid_timestamp(timestamp: str):
    """验证时间戳格式（ISO 8601）"""
    # 简单验证格式
    iso_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    assert re.match(iso_pattern, timestamp), f"无效的时间戳格式: {timestamp}"


# ============================================================================
# 文件操作
# ============================================================================

def assert_file_exists(file_path):
    """验证文件存在"""
    from pathlib import Path
    path = Path(file_path)
    assert path.exists(), f"文件不存在: {file_path}"
    assert path.is_file(), f"路径不是文件: {file_path}"


def assert_directory_exists(dir_path):
    """验证目录存在"""
    from pathlib import Path
    path = Path(dir_path)
    assert path.exists(), f"目录不存在: {dir_path}"
    assert path.is_dir(), f"路径不是目录: {dir_path}"
