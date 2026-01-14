#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CharacterRepository 功能测试。"""

from pathlib import Path
import importlib
import importlib.util
import sys

import pytest

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


character_repository_module = _import_project_module("py.services.character_repository")
CharacterRepository = character_repository_module.CharacterRepository


@pytest.fixture()
def repo(tmp_path: Path) -> CharacterRepository:
    storage_dir = tmp_path / "pic"
    prebuilt_file = tmp_path / "characters" / "prebuilt.json"
    library_file = tmp_path / "characters" / "user.json"
    prebuilt_file.parent.mkdir(parents=True, exist_ok=True)
    prebuilt_file.write_text(
        """
[
  {
    "id": "char-test",
    "name": "测试角色",
    "image_path": "test.jpg",
    "appearance": {"zh": "测试", "en": "test"},
    "voice": {"zh": "声音"},
    "tags": ["prebuilt"],
    "status": "active",
    "source": "prebuilt",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z",
    "created_by": "system"
  }
]
""",
        encoding="utf-8",
    )
    (storage_dir / "test.jpg").parent.mkdir(parents=True, exist_ok=True)
    (storage_dir / "test.jpg").write_bytes(b"fake")
    repo = CharacterRepository(
        storage_dir=storage_dir,
        prebuilt_file=prebuilt_file,
        user_library_file=library_file,
        public_base_url="/static/pic",
        uploads_subdir="user",
    )
    return repo


def test_list_characters_includes_prebuilt(repo: CharacterRepository):
    characters = repo.list_characters()
    assert characters, "应返回预制角色"
    first = characters[0]
    assert first["id"] == "char-test"
    assert first["image_url"].startswith("/static/pic")


def test_create_character_persists_image_and_record(repo: CharacterRepository, tmp_path: Path):
    payload = repo.create_character(
        name="新角色",
        appearance={"zh": "新的", "en": "new"},
        voice={"prompt": "calm"},
        image_bytes=b"hello-bytes",
        image_filename="pic.png",
        tags=["custom"],
        created_by="tester",
    )
    assert payload["name"] == "新角色"
    assert payload["appearance"]["zh"] == "新的"
    image_url = payload["image_url"]
    assert image_url and image_url.endswith(".png")

    absolute = repo.resolve_image_path(payload)
    assert absolute.exists(), "图片应被保存"


def test_update_and_disable_character(repo: CharacterRepository):
    created = repo.create_character(
        name="待更新",
        appearance={"zh": "原始"},
        voice={"prompt": "calm"},
        image_bytes=b"bytes",
        image_filename="origin.jpg",
        tags=["user"],
    )
    updated = repo.update_character(
        created["id"],
        name="已更新",
        appearance={"zh": "更新值"},
        voice={"prompt": "new"},
        status="active",
        tags=["user", "vip"],
    )
    assert updated["name"] == "已更新"
    assert updated["appearance"]["zh"] == "更新值"
    assert "vip" in updated["tags"]

    disabled = repo.disable_character(created["id"])
    assert disabled["status"] == "disabled"
