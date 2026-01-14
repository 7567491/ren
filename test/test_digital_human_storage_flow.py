import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from py.services.digital_human_service import DigitalHumanService
from py.services.storage_service import StorageService


@pytest.mark.asyncio
@pytest.mark.digital_human
async def test_digital_human_storage_publish(api_keys, tmp_path):
    output_root = tmp_path / "output"
    public_root = tmp_path / "public"
    storage = StorageService(
        output_root=output_root,
        public_base_url="https://cdn.example.com",
        public_export_dir=public_root,
        namespace="case",
    )

    service = DigitalHumanService(
        wavespeed_key=api_keys["wavespeed"],
        minimax_key=api_keys["minimax"],
        storage_service=storage,
    )

    job_id = "aka-storage-001"
    provider_video = tmp_path / "provider.mp4"
    provider_video.write_bytes(b"video-bytes")

    with patch.object(service.avatar_client, "generate_images", new_callable=AsyncMock) as mock_avatar, \
         patch.object(service.voice_client, "generate_voice", new_callable=AsyncMock) as mock_voice, \
         patch.object(service.infinitetalk_client, "generate_video", new_callable=AsyncMock) as mock_video, \
         patch.object(service.task_manager, "update_status") as mock_update:

        mock_avatar.return_value = [{"url": "https://example.com/avatar.png"}]
        mock_voice.return_value = {
            "audio_url": "https://example.com/speech.mp3",
            "audio_path": str(output_root / job_id / "speech.mp3"),
            "duration": 11.0,
            "cost": 0.02,
        }
        mock_video.return_value = {
            "task_id": "task-123",
            "video_url": "https://example.com/raw.mp4",
            "video_path": str(provider_video),
            "duration": 11.0,
            "cost": 0.6,
        }

        result = await service.generate_digital_human(
            job_id=job_id,
            avatar_mode="prompt",
            avatar_prompt="测试头像",
            speech_text="hello world",
        )

    task_paths = storage.prepare_task_paths(job_id)
    assert Path(result["video_path"]) == task_paths.video_path
    assert result["video_url"].startswith("https://cdn.example.com/case/")
    assert Path(result["assets"]["public_video_path"]).exists()

    meta = storage.load_metadata(job_id)
    assert meta["video_url"] == result["video_url"]
    assert meta["assets"]["public_video_path"] == result["assets"]["public_video_path"]
