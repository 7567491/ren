import json
from pathlib import Path

import pytest

from py.services.storage_service import StorageService


def test_prepare_task_paths(tmp_path):
    storage = StorageService(output_root=tmp_path)
    paths = storage.prepare_task_paths("aka-123456")

    assert paths.task_dir.exists()
    assert paths.avatar_path.name == "avatar.png"
    assert paths.speech_path.name == "speech.mp3"
    assert paths.video_path.name == "digital_human.mp4"
    assert paths.meta_path.name == "task.json"


def test_save_and_load_metadata(tmp_path):
    storage = StorageService(output_root=tmp_path)
    payload = {"job_id": "aka-1", "status": "pending"}
    storage.save_metadata("aka-1", payload)

    loaded = storage.load_metadata("aka-1")
    assert loaded == payload


def test_publish_video(tmp_path):
    output_root = tmp_path / "output"
    public_root = tmp_path / "public"

    storage = StorageService(
        output_root=output_root,
        public_base_url="https://cdn.example.com",
        public_export_dir=public_root,
        namespace="demo",
    )

    paths = storage.prepare_task_paths("aka-0001")
    video_file = paths.video_path
    video_file.write_bytes(b"video")

    publish_info = storage.publish_video("aka-0001", video_file)
    assert publish_info is not None

    public_path = Path(publish_info["path"])
    assert public_path.exists()
    assert publish_info["url"].startswith("https://cdn.example.com/demo/")
    assert public_path.read_bytes() == b"video"


def test_publish_video_with_mirror_targets(tmp_path):
    output_root = tmp_path / "output"
    public_root = tmp_path / "public"
    mirror_dir = tmp_path / "mirror"

    storage = StorageService(
        output_root=output_root,
        public_base_url="https://cdn.example.com",
        public_export_dir=public_root,
        namespace="demo",
        video_mirror_targets=[
            {
                "name": "wave-ad",
                "dir": str(mirror_dir),
                "base_url": "https://wave.example.com/ad",
                "filename_template": "{job_id}.mp4",
            }
        ],
    )

    paths = storage.prepare_task_paths("aka-7777")
    video_file = paths.video_path
    video_file.write_bytes(b"video")

    publish_info = storage.publish_video("aka-7777", video_file)
    assert publish_info is not None
    mirrors = publish_info.get("mirrors")
    assert mirrors
    wave_info = mirrors[0]
    assert wave_info["name"] == "wave-ad"
    assert wave_info["url"] == "https://wave.example.com/ad/aka-7777.mp4"
    mirror_path = Path(wave_info["path"])
    assert mirror_path.exists()
    assert mirror_path.read_bytes() == b"video"


def test_publish_video_without_public_config(tmp_path):
    storage = StorageService(output_root=tmp_path)
    paths = storage.prepare_task_paths("aka-0002")
    video_file = paths.video_path
    video_file.write_bytes(b"video")

    assert storage.publish_video("aka-0002", video_file) is None


def test_append_log(tmp_path):
    storage = StorageService(output_root=tmp_path)
    storage.append_log("aka-log", "开始生成头像", level="INFO", trace_id="trace-test")
    log_path = storage.prepare_task_paths("aka-log").log_path
    content = log_path.read_text()
    assert "开始生成头像" in content
    assert "trace-test" in content


def test_publish_task_asset_respects_namespace(tmp_path):
    storage = StorageService(
        output_root=tmp_path / "output",
        public_base_url="https://cdn.example.com/ren",
        public_export_dir=tmp_path / "public",
        namespace="ren",
    )

    local_file = tmp_path / "avatar.png"
    local_file.write_bytes(b"avatar")

    publish_info = storage.publish_task_asset(
        "aka-asset-1", local_file, asset_dir="output", filename="avatar.png"
    )
    assert publish_info is not None

    expected_path = tmp_path / "public" / "ren" / "output" / "aka-asset-1" / "avatar.png"
    assert Path(publish_info["path"]) == expected_path
    assert expected_path.read_bytes() == b"avatar"
    assert publish_info["url"] == "https://cdn.example.com/ren/output/aka-asset-1/avatar.png"
