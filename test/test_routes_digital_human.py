"""
数字人 API 路由测试
"""
import io
import importlib
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _import_project_module(name: str):
    saved_py = sys.modules.get("py")
    spec = importlib.util.spec_from_file_location(
        "py",
        PROJECT_ROOT / "py" / "__init__.py",
        submodule_search_locations=[str(PROJECT_ROOT / "py")],
    )
    if not spec or not spec.loader:
        raise RuntimeError("无法加载 py 包")

    module = importlib.util.module_from_spec(spec)
    sys.modules["py"] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    try:
        return importlib.import_module(name)
    finally:
        if saved_py is not None:
            sys.modules["py"] = saved_py
        else:
            sys.modules.pop("py", None)


routes_module = _import_project_module("py.api.routes_digital_human")
router = routes_module.router
register_exception_handlers = routes_module.register_exception_handlers
resolve_upload_path = routes_module._resolve_upload_file_path


@pytest.fixture
def app():
    api = FastAPI()
    api.include_router(router)
    register_exception_handlers(api)
    return api


@pytest.fixture
def client(app):
    return TestClient(app)


class TestDigitalHumanRoutes:
    """数字人路由单测"""

    def test_create_task_prompt_mode(self, client):
        with patch.object(routes_module, "task_manager") as mock_tm, \
             patch.object(routes_module.asyncio, "create_task", side_effect=_consume_task) as mock_create_task:
            mock_tm.create_task.return_value = "aka-test-001"
            response = client.post("/api/tasks", json={
                "avatar_mode": "prompt",
                "avatar_prompt": "专业主持人",
                "speech_text": "欢迎来到数字人工作室"
            })
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "aka-test-001"
        assert data["status"] == "pending"
        assert data["links"]["self"] == "/api/tasks/aka-test-001"
        mock_create_task.assert_called_once()

    def test_create_task_upload_mode(self, client):
        with patch.object(routes_module, "task_manager") as mock_tm, \
             patch.object(routes_module.asyncio, "create_task", side_effect=_consume_task):
            mock_tm.create_task.return_value = "aka-test-002"
            response = client.post("/api/tasks", json={
                "avatar_mode": "upload",
                "avatar_upload_url": "/tmp/avatar.png",
                "speech_text": "请开始你的表演"
            })
        assert response.status_code == 200

    def test_create_task_missing_avatar_prompt(self, client):
        response = client.post("/api/tasks", json={
            "avatar_mode": "prompt",
            "speech_text": "测试"
        })
        assert response.status_code == 400
        assert "avatar_prompt" in response.json()["detail"]

    def test_create_task_missing_avatar_upload_url(self, client):
        response = client.post("/api/tasks", json={
            "avatar_mode": "upload",
            "speech_text": "测试"
        })
        assert response.status_code == 400

    def test_get_task_status(self, client):
        task_meta = {
            "job_id": "aka-test",
            "status": "finished",
            "avatar_url": "https://example.com/avatar.png",
            "audio_url": "https://example.com/audio.mp3",
            "video_url": "https://example.com/video.mp4",
            "billing": {
                "balance_before": 200.0,
                "balance_after": 198.5,
                "actual_cost": 1.5,
                "currency": "USD",
            },
            "cost": 0.5,
            "duration": 10.0,
            "stages": {"avatar": {"state": "completed"}},
            "assets": {"video_path": "/tmp/video.mp4"},
            "trace_id": "trace-test-meta",
            "config_hash": "hash-meta",
            "logs": ["[INFO] mock"],
        }
        with patch.object(routes_module, "task_manager") as mock_tm, \
             patch.object(routes_module, "storage_service") as mock_storage:
            mock_tm.get_task.return_value = {"status": "video_rendering", "message": "processing"}
            mock_storage.load_metadata.return_value = task_meta

            response = client.get("/api/tasks/aka-test")

        data = response.json()
        assert response.status_code == 200
        assert data["status"] == "finished"
        assert data["video_url"] == "https://example.com/video.mp4"
        assert data["links"]["self"] == "/api/tasks/aka-test"
        assert data["trace_id"] == "trace-test-meta"
        assert data["billing"]["actual_cost"] == pytest.approx(1.5)

    def test_get_task_status_not_found(self, client):
        with patch.object(routes_module, "task_manager") as mock_tm:
            mock_tm.get_task.return_value = None
            response = client.get("/api/tasks/aka-missing")
        assert response.status_code == 404

    def test_upload_avatar(self, client, tmp_path):
        file_path = tmp_path / "avatar.png"
        file_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

        with patch.object(routes_module, "UPLOAD_DIR", tmp_path), \
             patch.object(routes_module, "UPLOAD_PUBLIC_BASE", "https://cdn.example.com/uploads"):
            with open(file_path, "rb") as f:
                response = client.post(
                    "/api/assets/upload",
                    files={"file": ("avatar.png", f, "image/png")}
                )
        assert response.status_code == 200
        assert response.json()["url"].startswith("https://cdn.example.com/uploads")

    def test_upload_invalid_file_type(self, client):
        fake_file = io.BytesIO(b"not image")
        response = client.post(
            "/api/assets/upload",
            files={"file": ("avatar.txt", fake_file, "text/plain")}
        )
        assert response.status_code == 400
        assert "只支持图片" in response.json()["detail"]

    def test_create_task_with_optional_params(self, client):
        with patch.object(routes_module, "task_manager") as mock_tm, \
             patch.object(routes_module.asyncio, "create_task", side_effect=_consume_task):
            mock_tm.create_task.return_value = "aka-full"
            response = client.post("/api/tasks", json={
                "avatar_mode": "prompt",
                "avatar_prompt": "主播",
                "speech_text": "可选参数",
                "voice_id": "female-yujie",
                "resolution": "1080p",
                "speed": 1.2,
                "pitch": 1,
                "emotion": "happy",
                "seed": 99,
                "mask_image": "https://example.com/mask.png"
            })
        assert response.status_code == 200

    def test_create_task_parameter_validation(self, client):
        response = client.post("/api/tasks", json={
            "avatar_mode": "prompt",
            "avatar_prompt": "测试",
            "speech_text": "测试",
            "speed": 3.0
        })
        assert response.status_code == 422

    def test_create_task_with_character_not_found(self, client):
        with patch.object(routes_module, "character_repository") as mock_repo:
            mock_repo.get_internal.side_effect = KeyError("missing")
            response = client.post("/api/tasks", json={
                "avatar_mode": "upload",
                "speech_text": "测试",
                "character_id": "char-unknown"
            })
        assert response.status_code == 404

    def test_external_api_error_handler(self, client):
        from py.exceptions import ExternalAPIError

        with patch.object(routes_module, "task_manager") as mock_tm:
            mock_tm.get_task.side_effect = ExternalAPIError(
                provider="wavespeed",
                message="限流",
                status_code=429,
                trace_id="trace-handler",
            )
            response = client.get("/api/tasks/aka-error")

        data = response.json()
        assert response.status_code == 429
        assert data["error"]["code"] == "wavespeed_error"
        assert data["trace_id"] == "trace-handler"

    def test_resolve_upload_file_path_maps_public_url(self, tmp_path):
        file_path = tmp_path / 'uploads' / 'avatar.png'
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b'avatar-data')

        with patch.object(routes_module, 'UPLOAD_DIR', file_path.parent):
            resolved = resolve_upload_path('https://s.linapp.fun/uploads/avatar.png')

        assert resolved == str(file_path)

    def test_resolve_upload_file_path_fallback(self):
        url = 'https://cdn.example.com/avatar.png'
        assert resolve_upload_path(url) == url

    def test_list_characters_endpoint(self, client):
        sample = [{
            "id": "char-demo",
            "name": "Demo",
            "appearance": {"zh": "示例"},
            "voice": {},
            "tags": [],
            "status": "active",
            "source": "prebuilt",
            "created_at": "2025-01-01T00:00:00Z",
            "image_url": "/api/characters/assets/demo.jpg"
        }]
        with patch.object(routes_module, "character_repository") as mock_repo:
            mock_repo.list_characters.return_value = sample
            response = client.get("/api/characters")
        assert response.status_code == 200
        assert response.json()[0]["id"] == "char-demo"

    def test_character_asset_endpoint_serves_file(self, client, tmp_path):
        asset = tmp_path / "demo.jpg"
        asset.write_bytes(b"jpegdata")
        with patch.object(routes_module, "character_repository") as mock_repo:
            mock_repo.resolve_asset_path.return_value = asset
            response = client.get("/api/characters/assets/demo.jpg")
        assert response.status_code == 200
        assert response.headers["content-type"] in {"image/jpeg", "application/octet-stream"}

    def test_character_asset_endpoint_missing(self, client, tmp_path):
        asset = tmp_path / "missing.jpg"
        with patch.object(routes_module, "character_repository") as mock_repo:
            mock_repo.resolve_asset_path.return_value = asset
            response = client.get("/api/characters/assets/missing.jpg")
        assert response.status_code == 404

    def test_character_asset_endpoint_invalid_path(self, client):
        with patch.object(routes_module, "character_repository") as mock_repo:
            mock_repo.resolve_asset_path.side_effect = ValueError("非法素材路径")
            response = client.get("/api/characters/assets/bad.png")
        assert response.status_code == 400

    def test_create_character_endpoint(self, client):
        payload = {
            "id": "char-user",
            "name": "User",
            "appearance": {"zh": "用户"},
            "voice": {},
            "tags": ["user"],
            "status": "active",
            "source": "user",
            "created_at": "2025-01-01T00:00:00Z",
            "image_url": "/api/characters/assets/user/a.png"
        }
        with patch.object(routes_module, "character_repository") as mock_repo:
            mock_repo.create_character.return_value = payload
            response = client.post(
                "/api/characters",
                files={"file": ("avatar.jpg", b"123", "image/jpeg")},
                data={
                    "name": "User",
                    "appearance_zh": "用户描述"
                }
            )
        assert response.status_code == 200
        assert response.json()["id"] == "char-user"

    def test_update_character_endpoint(self, client):
        updated = {
            "id": "char-user",
            "name": "Updated",
            "appearance": {"zh": "更新"},
            "voice": {},
            "tags": ["user"],
            "status": "active",
            "source": "user",
            "created_at": "2025-01-01T00:00:00Z",
            "image_url": "/api/characters/assets/user/a.png"
        }
        with patch.object(routes_module, "character_repository") as mock_repo:
            mock_repo.update_character.return_value = updated
            response = client.put(
                "/api/characters/char-user",
                data={"name": "Updated"}
            )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"

    def test_delete_character_endpoint(self, client):
        disabled = {
            "id": "char-user",
            "status": "disabled",
            "appearance": {"zh": "demo"},
            "voice": {},
            "tags": [],
            "source": "user",
            "created_at": "2025-01-01T00:00:00Z",
            "image_url": "/api/characters/assets/user/a.png"
        }
        with patch.object(routes_module, "character_repository") as mock_repo:
            mock_repo.disable_character.return_value = disabled
            response = client.delete("/api/characters/char-user")
        assert response.status_code == 200
        assert response.json()["character"]["status"] == "disabled"

def _consume_task(coro, *args, **kwargs):
    """帮助函数：立即关闭协程，避免未 awaited 警告。"""
    coro.close()
    return MagicMock()
