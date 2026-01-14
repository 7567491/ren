import json
from pathlib import Path

from py.services.history_service import HistoryService
from py.services.storage_service import StorageService


def create_task_meta(base_dir: Path, job_id: str, payload: dict) -> None:
    task_dir = base_dir / job_id
    task_dir.mkdir(parents=True, exist_ok=True)
    meta_path = task_dir / "task.json"
    meta_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_list_recent_videos(tmp_path):
    storage = StorageService(
        output_root=tmp_path / "output",
        public_base_url="https://s.linapp.fun",
        public_export_dir=tmp_path / "mnt",
        namespace="ren",
    )
    history = HistoryService(storage)

    # 准备挂载目录中的视频文件
    assert storage.public_root is not None
    publish_dir = storage.public_root / "ren_01010100"  # type: ignore[operator]
    publish_dir.mkdir(parents=True, exist_ok=True)  # type: ignore[union-attr]
    publish_file = publish_dir / storage.final_video_name  # type: ignore[operator]
    publish_file.write_bytes(b"mp4data")

    publish_dir2 = storage.public_root / "ren_01010000"  # type: ignore[operator]
    publish_dir2.mkdir(parents=True, exist_ok=True)  # type: ignore[union-attr]
    publish_file2 = publish_dir2 / storage.final_video_name  # type: ignore[operator]
    publish_file2.write_bytes(b"demo")

    create_task_meta(
        storage.output_root,
        "aka-001",
        {
            "job_id": "aka-001",
            "status": "finished",
            "message": "ok",
            "created_at": "2025-01-01T09:59:00+00:00",
            "updated_at": "2025-01-01T10:03:00+00:00",
            "assets": {
                "video_url": "https://s.linapp.fun/ren/ren_01010100/digital_human.mp4",
                "local_video_url": "/output/aka-001/digital_human.mp4",
                "public_video_path": str(publish_file),
                "video_stage_completed_at": "2025-01-01T10:02:00+00:00",
                "duration": 8.5,
            },
        },
    )

    # 较旧的条目
    create_task_meta(
        storage.output_root,
        "aka-0002",
        {
            "job_id": "aka-0002",
            "status": "finished",
            "updated_at": "2025-01-01T08:00:00+00:00",
            "assets": {
                "local_video_url": "/output/aka-0002/digital_human.mp4",
                "public_video_path": str(publish_file2),
            },
        },
    )

    all_items = history.list_recent_videos(limit=10)
    assert len(all_items) == 2
    assert all_items[0]["job_id"] == "aka-001"
    assert all_items[0]["file_size"] == len(b"mp4data")
    assert all_items[1]["job_id"] == "aka-0002"
    assert all_items[0]["web_url"].startswith("https://s.linapp.fun")
    assert all_items[0]["relative_url"].startswith("/ren/")
    assert all_items[1]["web_url"].startswith("https://s.linapp.fun")
    assert all_items[1]["relative_url"].startswith("/ren/")

    top_one = history.list_recent_videos(limit=1)
    assert len(top_one) == 1
    assert top_one[0]["job_id"] == "aka-001"
