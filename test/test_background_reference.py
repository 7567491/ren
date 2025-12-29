#!/usr/bin/env python3
"""
TDD 测试：背景图生成与参考图传递
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "py"))

from py.function.config_loader import load_config  # noqa: E402
from py.function.context import RunContext  # noqa: E402
from py.function.steps import background_image, images  # noqa: E402
from py.function import media_clients  # noqa: E402


class DummyLogger:
    def info(self, *_: Any, **__: Any) -> None:
        pass

    def warning(self, *_: Any, **__: Any) -> None:
        pass

    def error(self, *_: Any, **__: Any) -> None:
        pass


class DummyMediaClient:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    async def generate_images(
        self,
        prompts: List[str],
        output_dir: Path,
        reference_images: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        self.calls.append({"prompts": prompts, "output_dir": output_dir, "reference_images": reference_images})
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "img_001.png"
        path.write_text("image", encoding="utf-8")
        return [{"path": path, "url": "https://example.com/img.png"}]


class FakeWSClient:
    def __init__(self) -> None:
        self.payloads: List[Dict[str, Any]] = []
        self.endpoint_calls: List[str] = []

    async def submit(self, endpoint: str, payload: Dict[str, Any]) -> str:
        self.endpoint_calls.append(endpoint)
        self.payloads.append(payload)
        return f"task-{len(self.payloads)}"

    async def wait_for_result(self, task_id: str, result_type: str = "结果", max_wait: Optional[int] = None) -> str:  # noqa: ARG002, D401
        return f"https://example.com/{task_id}.png"

    async def download(self, url: str, target: Path) -> Path:  # noqa: D401
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("payload", encoding="utf-8")
        return target


def _init_ctx(tmp_dir: Path) -> RunContext:
    config = load_config()
    config.merged.setdefault("api", {})["wavespeed_key"] = "dummy-key"

    ctx = RunContext(config=config)
    ctx.work_dir = tmp_dir
    ctx.logger = DummyLogger()
    ctx.state = {"steps": {}}
    ctx.assets = {}
    ctx.clients = {}
    return ctx


def test_background_step_generates_reference_image() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ctx = _init_ctx(Path(tmp))
        ctx.state["steps"]["script"] = {"topic": "测试产品", "style": "technology"}
        ctx.state["steps"]["shots"] = {
            "prompts": [
                "Shot 1 | style: 技术未来 | visual tone: neon | city skyline focus",
                "Shot 2 | 风格延续 | 其他提示",
            ],
            "style": "technology",
        }

        bg_dir = Path(tmp) / "background"
        dummy_client = DummyMediaClient()
        ctx.clients["media"] = dummy_client

        asyncio.run(background_image.run(ctx, bg_dir))

        assert dummy_client.calls, "背景图生成客户端未被调用"
        called_prompt = dummy_client.calls[0]["prompts"][0]
        assert "Shot 1" in called_prompt, "背景图提示词应包含首个镜头信息"
        assert ctx.assets.get("background_image_url") == "https://example.com/img.png", "应记录背景图URL"
        bg_state = ctx.state["steps"].get("background_image", {})
        assert Path(bg_state.get("file", "")).exists(), "背景图文件路径应存在"


def test_images_step_passes_background_reference() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ctx = _init_ctx(Path(tmp))
        ctx.state["steps"]["shots"] = {
            "prompts": ["Shot 1 prompt"],
            "style": "technology",
            "resolution": "720p",
        }
        ctx.assets["background_image_url"] = "https://example.com/bg.png"

        dummy_client = DummyMediaClient()
        ctx.clients["media"] = dummy_client

        asyncio.run(images.run(ctx, Path(tmp) / "images"))

        assert dummy_client.calls, "图像生成未被调用"
        assert dummy_client.calls[0]["reference_images"] == ["https://example.com/bg.png"], "应传递背景参考图"


def test_media_client_payload_includes_references() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        config = load_config()
        config.merged.setdefault("api", {})["wavespeed_key"] = "dummy-key"

        client = media_clients.MediaGenClient(config, DummyLogger(), dry_run=False)
        client.ws_client = FakeWSClient()

        prompts = ["Prompt 1 details", "Prompt 2 details"]
        ref_urls = ["https://example.com/bg.png"]

        asyncio.run(client.generate_images(prompts, Path(tmp) / "imgs", reference_images=ref_urls))

        assert len(client.ws_client.payloads) == 2, "每个提示词都应提交任务"
        for payload in client.ws_client.payloads:
            assert payload.get("images") == ref_urls, "payload 应包含参考图URL"


if __name__ == "__main__":
    all_passed = True
    for test_func in [
        test_background_step_generates_reference_image,
        test_images_step_passes_background_reference,
        test_media_client_payload_includes_references,
    ]:
        try:
            test_func()
            print(f"✓ {test_func.__name__} 通过")
        except AssertionError as exc:
            all_passed = False
            print(f"✗ {test_func.__name__} 失败: {exc}")

    if not all_passed:
        raise SystemExit(1)
