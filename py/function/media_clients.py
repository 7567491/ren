#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""媒体相关客户端适配（对接真实服务）。"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .config_loader import LoadedConfig
from ..services.music_service import MusicService
from ..services.subtitle_service import SubtitleService
from ..services.video_composer import VideoComposer
from ..services.voice_service import VoiceService


class WavespeedClient:
    def __init__(self, config: LoadedConfig, logger: Any, dry_run: bool = False):
        self.config = config
        self.logger = logger
        self.dry_run = dry_run
        merged = config.merged.get("wavespeed", {}) if isinstance(config.merged, dict) else {}
        self.base_url = merged.get("base_url", "https://api.wavespeed.ai")
        polling = merged.get("polling", {})
        retry_cfg = merged.get("retry", {})
        self.poll_interval = polling.get("interval", 5)
        self.max_wait_default = polling.get("max_wait", 600)
        self.retry_attempts = retry_cfg.get("max_attempts", 3)
        self.retry_initial_delay = retry_cfg.get("initial_delay", 5)
        self.retry_backoff = retry_cfg.get("backoff_multiplier", 2)

        self.api_key = os.getenv("Wavespeed_API_KEY") or (config.merged.get("api", {}) if isinstance(config.merged, dict) else {}).get("wavespeed_key", "")
        if not self.api_key and not self.dry_run:
            raise ValueError("缺少 Wavespeed API key")

        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def submit(self, endpoint: str, payload: Dict[str, Any]) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.post(f"{self.base_url}{endpoint}", headers=self.headers, json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:  # noqa: PERF203
                detail = exc.response.text
                self.logger.error(f"提交任务失败 {endpoint}: {exc} | {detail[:200]}")
                raise
            data = self._parse_response(response.json())
        task_id = data.get("id") or data.get("task_id")
        if not task_id:
            raise ValueError(f"未返回任务ID: {data}")
        return str(task_id)

    async def wait_for_result(self, task_id: str, result_type: str = "结果", max_wait: Optional[int] = None) -> str:
        max_wait = max_wait or self.max_wait_default
        start = time.time()
        url = f"{self.base_url}/api/v3/predictions/{task_id}/result"

        async with httpx.AsyncClient(timeout=30) as client:
            while time.time() - start < max_wait:
                response = await client.get(url, headers={"Authorization": f"Bearer {self.api_key}"})
                response.raise_for_status()
                data = self._parse_response(response.json())

                status = data.get("status")
                if status == "completed":
                    outputs = data.get("outputs") or []
                    if not outputs:
                        raise ValueError(f"{result_type}完成但无输出: {data}")
                    return outputs[0]
                if status == "failed":
                    raise ValueError(f"{result_type}任务失败: {data.get('error', '未知错误')}")

                await asyncio.sleep(self.poll_interval)

        raise TimeoutError(f"等待 {result_type} 超时 (task_id={task_id})")

    @staticmethod
    def _parse_response(resp: Dict[str, Any]) -> Dict[str, Any]:
        if "code" in resp:
            if resp.get("code") != 200:
                raise ValueError(resp.get("message") or "API 返回错误")
            if "data" in resp:
                return resp.get("data") or {}
        return resp

    async def download(self, url: str, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(url)
            response.raise_for_status()
            target.write_bytes(response.content)
        return target


def _resolve_model(config: LoadedConfig, kind: str) -> tuple[str, Dict[str, Any], Dict[str, Dict[str, Any]]]:
    base_models = (config.base_config.get("models", {}) or {}).get(kind, {}) if isinstance(config.base_config, dict) else {}
    user_models = (config.user_config.get("models", {}) or {}) if isinstance(config.user_config, dict) else {}
    merged_models = config.merged.get("models") if isinstance(config.merged, dict) else {}

    choice = user_models.get(kind)
    model_name: Optional[str] = None
    if isinstance(choice, int):
        model_name = (base_models.get("number_map") or {}).get(choice)
    elif isinstance(choice, str):
        model_name = choice

    if not model_name and isinstance(merged_models, dict):
        maybe = merged_models.get(kind)
        if isinstance(maybe, dict):
            model_name = maybe.get("current")

    if not model_name and isinstance(base_models, dict):
        model_name = base_models.get("current")

    available = base_models.get("available", {}) if isinstance(base_models, dict) else {}
    if model_name not in available and available:
        model_name = list(available.keys())[0]

    return model_name or "", available.get(model_name or "", {}), available


class VoiceClient:
    def __init__(self, config: LoadedConfig, logger: Any, dry_run: bool = False):
        self.config = config
        self.logger = logger
        self.dry_run = dry_run
        self.voice_service = VoiceService()

    async def synthesize(self, text: str, output: Path) -> tuple[Path, Any | None, float]:
        output.parent.mkdir(parents=True, exist_ok=True)

        if self.dry_run:
            output.write_text(text, encoding="utf-8")
            self.logger.info(f"旁白 dry-run: {output}")
            return output, None, 0.0

        voice_cfg = self.config.merged.get("audio", {}) if isinstance(self.config.merged, dict) else {}
        voice_name = voice_cfg.get("voice_name", "zh-CN-XiaoxiaoNeural")
        sub_maker, duration = await asyncio.to_thread(self.voice_service.generate_audio, text, str(output), voice_name)
        self.logger.info(f"生成旁白音频: {output}")
        return output, sub_maker, duration


class SubtitleClient:
    def __init__(self, config: LoadedConfig, logger: Any, dry_run: bool = False):
        self.config = config
        self.logger = logger
        self.dry_run = dry_run
        self.subtitle_service = SubtitleService()

    async def create_subtitle(self, voice_path: Path, subtitle_path: Path, text: str, sub_maker: Any | None = None, duration: float | None = None) -> Optional[Path]:
        subtitle_path.parent.mkdir(parents=True, exist_ok=True)

        if self.dry_run:
            subtitle_path.write_text("WEBVTT\n\n00:00.000 --> 00:05.000\n" + text + "\n", encoding="utf-8")
            self.logger.info(f"字幕 dry-run: {subtitle_path}")
            return subtitle_path

        if sub_maker:
            success = await asyncio.to_thread(self.subtitle_service.create_from_submaker, sub_maker, text, str(subtitle_path))
        elif duration:
            success = await asyncio.to_thread(self.subtitle_service.create_simple_subtitle, text, duration, str(subtitle_path))
        else:
            success = await asyncio.to_thread(self.subtitle_service.create_simple_subtitle, text, 5.0, str(subtitle_path))

        if success:
            return subtitle_path
        return None


class MusicClient:
    def __init__(self, config: LoadedConfig, logger: Any, dry_run: bool = False):
        self.config = config
        self.logger = logger
        self.dry_run = dry_run

    async def pick_music(self, music_dir: Path, target: Path, style: Optional[str] = None) -> Optional[Path]:
        if self.dry_run:
            self.logger.info("配乐 dry-run，跳过")
            return None

        service = MusicService(str(music_dir), config=self.config.merged if isinstance(self.config.merged, dict) else None)
        selected = await asyncio.to_thread(service.select_music, style, True)
        if not selected:
            return None

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(selected, target)
        self.logger.info(f"已选择背景音乐: {Path(selected).name}")
        return target


class MediaGenClient:
    def __init__(self, config: LoadedConfig, logger: Any, dry_run: bool = False):
        self.config = config
        self.logger = logger
        self.dry_run = dry_run
        self.ws_client = WavespeedClient(config, logger, dry_run=dry_run)

    async def generate_images(self, prompts: List[str], output_dir: Path) -> List[Dict[str, Any]]:
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.dry_run:
            results: List[Dict[str, Any]] = []
            for idx, prompt in enumerate(prompts, start=1):
                path = output_dir / f"img_{idx:03d}.png"
                path.write_text(f"[DRY-RUN IMAGE]\n{prompt}", encoding="utf-8")
                results.append({"path": path, "url": None})
            self.logger.info(f"生成 {len(results)} 张占位图片")
            return results

        model_name, model_cfg, available = _resolve_model(self.config, "image")
        if not model_cfg:
            raise ValueError("未找到图像模型配置")

        if model_cfg.get("support_reference") and model_cfg.get("endpoint", "").endswith("/edit"):
            fallback = next(((name, cfg) for name, cfg in available.items() if not cfg.get("support_reference")), None)
            if fallback:
                self.logger.warning(f"模型 {model_name} 需要参考图，切换到 {fallback[0]}")
                model_name, model_cfg = fallback

        params = model_cfg.get("params", {})
        results = []
        for idx, prompt in enumerate(prompts, start=1):
            payload = {"prompt": prompt}
            payload.update(params)
            task_id = await self.ws_client.submit(model_cfg.get("endpoint"), payload)
            url = await self.ws_client.wait_for_result(task_id, "图像", max_wait=model_cfg.get("max_wait"))
            path = output_dir / f"img_{idx:03d}.png"
            await self.ws_client.download(url, path)
            self.logger.info(f"图像生成完成: {path.name}")
            results.append({"path": path, "url": url})
        return results

    async def generate_videos(self, prompts: List[str], output_dir: Path, references: Optional[List[str]] = None, resolution: Optional[str] = None) -> List[Dict[str, Any]]:
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.dry_run:
            results: List[Dict[str, Any]] = []
            for idx, prompt in enumerate(prompts, start=1):
                path = output_dir / f"video_{idx:03d}.mp4"
                path.write_text(f"[DRY-RUN VIDEO]\n{prompt}", encoding="utf-8")
                results.append({"path": path, "url": None})
            self.logger.info(f"生成 {len(results)} 段占位视频")
            return results

        model_name, model_cfg, _available = _resolve_model(self.config, "video")
        if not model_cfg:
            raise ValueError("未找到视频模型配置")

        params = model_cfg.get("params", {}).copy()
        model_type = model_cfg.get("type", "i2v")
        results: List[Dict[str, Any]] = []

        for idx, prompt in enumerate(prompts, start=1):
            payload = {"prompt": prompt}
            payload.update(params)

            if resolution:
                payload["resolution"] = resolution

            if model_type == "i2v":
                image_url = references[idx - 1] if references and idx - 1 < len(references) else None
                if not image_url:
                    raise ValueError("I2V 模型需要提供参考图 URL")
                payload["image"] = image_url

            payload = {k: v for k, v in payload.items() if v is not None}

            task_id = await self.ws_client.submit(model_cfg.get("endpoint"), payload)
            url = await self.ws_client.wait_for_result(task_id, "视频", max_wait=model_cfg.get("max_wait"))
            path = output_dir / f"video_{idx:03d}.mp4"
            await self.ws_client.download(url, path)
            self.logger.info(f"视频生成完成: {path.name}")
            results.append({"path": path, "url": url})

        return results


class ComposerClient:
    def __init__(self, config: LoadedConfig, logger: Any, dry_run: bool = False):
        self.config = config
        self.logger = logger
        self.dry_run = dry_run
        self.composer = VideoComposer(temp_dir=str(config.project_root / "temp"), config=config.merged if isinstance(config.merged, dict) else None)

    async def compose(self, videos: List[Path], voice: Optional[Path], music: Optional[Path], subtitle: Optional[Path], output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)

        if self.dry_run:
            text = ["DRY RUN COMPOSE", f"videos:{','.join(p.name for p in videos)}"]
            if voice:
                text.append(f"voice:{voice.name}")
            if music:
                text.append(f"music:{music.name}")
            if subtitle:
                text.append(f"subtitle:{subtitle.name}")
            output.write_text("\n".join(text), encoding="utf-8")
            self.logger.info(f"生成占位合成文件: {output}")
            return output

        current = output
        if len(videos) == 1:
            shutil.copy(videos[0], current)
        else:
            concat_path = output.parent / "_concat.mp4"
            ok = await asyncio.to_thread(self.composer.concatenate_videos, [str(v) for v in videos], str(concat_path))
            if not ok:
                raise RuntimeError("视频拼接失败")
            current = concat_path

        if voice:
            voice_path = output.parent / "_voice.mp4"
            ok = await asyncio.to_thread(self.composer.add_audio_to_video, str(current), str(voice), str(voice_path))
            if not ok:
                raise RuntimeError("添加旁白失败")
            current = voice_path

        if music:
            music_path = output.parent / "_music.mp4"
            ok = await asyncio.to_thread(self.composer.add_background_music, str(current), str(music), str(music_path))
            if not ok:
                self.logger.warning("背景音乐添加失败，继续使用无配乐版本")
            else:
                current = music_path

        if subtitle:
            final_target = output
            ok = await asyncio.to_thread(self.composer.add_subtitles_to_video, str(current), str(subtitle), str(final_target))
            if not ok:
                self.logger.warning("字幕添加失败，输出无字幕版本")
                shutil.copy(current, output)
            else:
                current = final_target
        else:
            shutil.copy(current, output)

        self.logger.info(f"合成完成: {output}")
        return output


__all__ = [
    "VoiceClient",
    "SubtitleClient",
    "MusicClient",
    "MediaGenClient",
    "ComposerClient",
]
