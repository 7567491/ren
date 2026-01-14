"""
pytest 配置和共享 fixtures

提供测试所需的 mock 数据、fixture 和工具函数
"""
import os
import sys
import pytest
from pathlib import Path
from typing import Dict, Any
import json

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# pytest 在加载自身依赖时可能已经导入 pip 的 `py` 包。
# 为了让仓库内的 `py/` 子模块也能被找到，将项目目录添加到该包的 __path__。
if "py" in sys.modules:
    sys.modules.pop("py")

# 重新导入项目内的 `py` 包（位于项目根目录）。
import importlib  # noqa: E402  # isort:skip

importlib.import_module("py")
importlib.import_module("py.services")
importlib.import_module("py.function")


# ============================================================================
# 环境配置
# ============================================================================

@pytest.fixture(scope="session")
def use_mock():
    """是否使用 mock 数据（通过环境变量控制）"""
    return os.getenv("PYTEST_WAVESPEED_MOCK", "1") == "1"


@pytest.fixture(scope="session")
def api_keys():
    """API 密钥（从环境变量读取）"""
    return {
        "wavespeed": os.getenv("WAVESPEED_API_KEY", "test-key-wavespeed"),
        "minimax": os.getenv("MINIMAX_API_KEY", "test-key-minimax"),
    }


@pytest.fixture(scope="session")
def test_output_dir(tmp_path_factory):
    """测试输出目录"""
    output_dir = tmp_path_factory.mktemp("test_output")
    return output_dir


# ============================================================================
# Mock 数据
# ============================================================================

@pytest.fixture
def mock_seedream_response():
    """Mock Seedream API 响应"""
    return {
        "output": {
            "image_url": "https://example.com/test-avatar.png",
            "width": 1024,
            "height": 1024,
            "seed": 42
        },
        "task_id": "seedream-task-123",
        "status": "completed"
    }


@pytest.fixture
def mock_minimax_response():
    """Mock MiniMax TTS API 响应"""
    return {
        "output": {
            "audio_url": "https://example.com/test-speech.mp3",
            "duration": 12.5,
            "sample_rate": 32000,
            "channel": 1
        },
        "task_id": "minimax-task-456",
        "status": "completed"
    }


@pytest.fixture
def mock_infinitetalk_submit_response():
    """Mock Infinitetalk 提交任务响应"""
    return {
        "task_id": "infinitetalk-task-789",
        "status": "pending",
        "message": "任务已创建"
    }


@pytest.fixture
def mock_infinitetalk_status_response():
    """Mock Infinitetalk 任务状态响应"""
    return {
        "task_id": "infinitetalk-task-789",
        "state": "completed",
        "progress": 100,
        "output": {
            "video_url": "https://example.com/test-video.mp4",
            "duration": 12.5,
            "resolution": "720p",
            "fps": 25
        },
        "created_at": "2025-12-30T10:00:00Z",
        "completed_at": "2025-12-30T10:05:00Z"
    }


@pytest.fixture
def mock_task_params():
    """Mock 任务参数"""
    return {
        "avatar_mode": "prompt",
        "avatar_prompt": "专业女性播音员，微笑，正面照",
        "speech_text": "大家好，欢迎收看今天的节目。",
        "voice_id": "female-shaonv",
        "resolution": "720p",
        "speed": 1.0,
        "pitch": 0,
        "emotion": "neutral",
        "seed": 42,
        "mask_image": None
    }


@pytest.fixture
def mock_task_json(mock_task_params):
    """Mock task.json 数据"""
    return {
        "job_id": "aka-test-123",
        "status": "pending",
        "created_at": "2025-12-30T10:00:00Z",
        "updated_at": "2025-12-30T10:00:00Z",
        "params": mock_task_params,
        "assets": {},
        "external_task_ids": {},
        "cost": {},
        "metadata": {},
        "error": None,
        "trace_id": "trace-test-123",
        "config_hash": "hash-abc",
        "logs": ["[INFO] mock log"],
    }


# ============================================================================
# 测试工具函数
# ============================================================================

@pytest.fixture
def create_test_task_dir(test_output_dir):
    """创建测试任务目录的工厂函数"""
    def _create(job_id: str = "aka-test-123"):
        task_dir = test_output_dir / job_id
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir
    return _create


@pytest.fixture
def write_task_json(create_test_task_dir):
    """写入 task.json 的辅助函数"""
    def _write(job_id: str, data: Dict[str, Any]):
        task_dir = create_test_task_dir(job_id)
        task_file = task_dir / "task.json"
        task_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return task_file
    return _write


@pytest.fixture
def read_task_json():
    """读取 task.json 的辅助函数"""
    def _read(task_dir: Path) -> Dict[str, Any]:
        task_file = task_dir / "task.json"
        if not task_file.exists():
            return {}
        return json.loads(task_file.read_text())
    return _read


# ============================================================================
# Mock HTTP 客户端
# ============================================================================

class MockHTTPResponse:
    """Mock HTTP 响应对象"""
    def __init__(self, json_data: Dict[str, Any], status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest.fixture
def mock_http_client(use_mock):
    """Mock HTTP 客户端"""
    class MockClient:
        def __init__(self):
            self.requests = []
            self.responses = {}

        def set_response(self, endpoint: str, response_data: Dict[str, Any], status_code: int = 200):
            """设置 mock 响应"""
            self.responses[endpoint] = MockHTTPResponse(response_data, status_code)

        async def post(self, url: str, **kwargs):
            """Mock POST 请求"""
            self.requests.append({"method": "POST", "url": url, "kwargs": kwargs})
            # 提取 endpoint
            endpoint = url.split("/")[-1] if "/" in url else url
            return self.responses.get(endpoint, MockHTTPResponse({"status": "ok"}))

        async def get(self, url: str, **kwargs):
            """Mock GET 请求"""
            self.requests.append({"method": "GET", "url": url, "kwargs": kwargs})
            endpoint = url.split("/")[-1] if "/" in url else url
            return self.responses.get(endpoint, MockHTTPResponse({"status": "ok"}))

    return MockClient() if use_mock else None


# ============================================================================
# 清理
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_files(test_output_dir):
    """自动清理测试文件"""
    yield
    # 测试结束后清理
    # 注意: tmp_path_factory 会自动清理，这里只是示例


# ============================================================================
# 测试标记
# ============================================================================

def pytest_configure(config):
    """pytest 配置钩子"""
    config.addinivalue_line(
        "markers", "digital_human: 数字人系统相关测试"
    )
    config.addinivalue_line(
        "markers", "real_api: 调用真实 API 的测试（需要设置 API key）"
    )
