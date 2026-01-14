#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""针对 py/test_network.py 的最小化回归测试。"""

from __future__ import annotations

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _import_project_module(name: str):
    saved_py = sys.modules.get("py")
    spec = importlib.util.spec_from_file_location(
        "py", PROJECT_ROOT / "py" / "__init__.py"
    )
    if not spec or not spec.loader:  # pragma: no cover - 理论上不会发生
        raise RuntimeError("无法创建 py 包的加载配置")

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


test_network = _import_project_module("py.test_network")


@pytest.mark.asyncio
async def test_run_digital_human_uses_args_and_env(monkeypatch, tmp_path):
    """确保 run_digital_human 会读取 env/参数并调用 DigitalHumanService。"""

    called_kwargs = {}

    def fake_init(self, wavespeed_key, minimax_key, storage_service, task_manager):
        self._wavespeed_key = wavespeed_key
        self._minimax_key = minimax_key
        self._storage = storage_service
        self._tm = task_manager

    async def fake_generate(self, **kwargs):
        nonlocal called_kwargs
        called_kwargs = kwargs
        return {
            "job_id": "aka-test-1234",
            "status": "finished",
            "stages": {
                "avatar": {"state": "completed", "message": "ok"},
                "speech": {"state": "completed", "message": "ok"},
                "video": {"state": "completed", "message": "ok"},
            },
            "assets": {"video_url": "https://example.com/video.mp4"},
            "cost": 0.05,
        }

    monkeypatch.setenv("WAVESPEED_API_KEY", "test-wavespeed")
    monkeypatch.setenv("MINIMAX_API_KEY", "test-minimax")

    monkeypatch.setattr(test_network.DigitalHumanService, "__init__", fake_init)
    monkeypatch.setattr(
        test_network.DigitalHumanService,
        "generate_digital_human",
        fake_generate,
    )

    args = SimpleNamespace(
        digital_human=True,
        avatar_mode="prompt",
        avatar_prompt="test prompt",
        avatar_upload=None,
        speech_text="test text",
        voice_id="Wise_Woman",
        resolution="720p",
        seed=42,
        output_dir=str(tmp_path / "output"),
        temp_dir=str(tmp_path / "temp"),
        public_url=None,
        public_export_dir=None,
        namespace="ren",
        json=False,
    )

    record = await test_network.run_digital_human(args)
    assert record["status"] == "finished"
    assert called_kwargs["avatar_mode"] == "prompt"
    assert called_kwargs["speech_text"] == "test text"
