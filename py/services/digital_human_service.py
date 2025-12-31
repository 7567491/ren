"""
数字人服务编排

为外部调用者提供统一入口，内部由 TaskRunner 控制三阶段流程。
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from py.function.media_clients import InfiniteTalkClient
from py.function.task_runner import TaskRequest, TaskRunner
from py.exceptions import ExternalAPIError
from py.function.config_loader import load_config, LoadedConfig
from py.services.minimax_tts_service import MiniMaxTTSService
from py.services.storage_service import StorageService
from py.services.task_manager import TaskManager


class DigitalHumanService:
    """数字人生成服务。"""

    def __init__(
        self,
        wavespeed_key: str,
        minimax_key: str,
        storage_service: Optional[StorageService] = None,
        task_manager: Optional[TaskManager] = None,
        loaded_config: Optional[LoadedConfig] = None,
    ):
        self.task_manager = task_manager or TaskManager()
        self.wavespeed_key = wavespeed_key
        self.voice_client = MiniMaxTTSService(minimax_key)
        self.infinitetalk_client = InfiniteTalkClient(wavespeed_key)
        self.logger = logging.getLogger("DigitalHumanService")
        self.loaded_config = loaded_config
        if self.loaded_config is None:
            try:
                self.loaded_config = load_config()
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("加载 config.yaml 失败：%s", exc)
                self.loaded_config = None
        self.storage = storage_service or StorageService(
            output_root=os.getenv("DIGITAL_HUMAN_OUTPUT_DIR", "output"),
            public_base_url=(
                os.getenv("DIGITAL_HUMAN_PUBLIC_BASE_URL")
                or os.getenv("STORAGE_BUCKET_URL")
            ),
            public_export_dir=os.getenv("DIGITAL_HUMAN_PUBLIC_EXPORT_DIR"),
            namespace=os.getenv("DIGITAL_HUMAN_PUBLIC_NAMESPACE", "ren"),
        )

        # avatar_client 默认指向自身（以便测试 mock generate_images）
        self.avatar_client = self

        async def upload_handler(task_id: str, upload_path: Optional[str], target_path: Path) -> str:
            return await self._handle_avatar_upload(task_id, upload_path, target_path)

        self.task_runner = TaskRunner(
            avatar_client=self.avatar_client,
            voice_client=self.voice_client,
            video_client=self.infinitetalk_client,
            storage_service=self.storage,
            task_manager=self.task_manager,
            avatar_upload_handler=upload_handler,
            logger=logging.getLogger("TaskRunner"),
            config_hash=self.loaded_config.config_hash if self.loaded_config else None,
        )

    async def generate_images(
        self,
        prompts: list,
        resolution: str = "1024x1024",
        num_images: int = 1,
        **kwargs,
    ) -> list:
        """调用 Seedream 生成头像，返回包含 URL/尺寸的字典列表。"""
        width, height = map(int, resolution.lower().split("x"))
        payload = {
            "prompt": prompts[0] if prompts else "",
            "width": width,
            "height": height,
            "num_images": num_images,
            "num_inference_steps": 28,
            "guidance_scale": 4.5,
        }

        headers = {
            "Authorization": f"Bearer {self.wavespeed_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.wavespeed.ai/api/v3/bytedance/seedream-v4",
                json=payload,
                headers=headers,
            )
            if not response.is_success:
                raise ExternalAPIError(
                    provider="seedream",
                    status_code=response.status_code,
                    message=response.text,
                    details={},
                )
            raw = response.json()
            data = self._unwrap_wavespeed_result(raw)

            image_url = self._extract_output_url(data, key="image_url")
            if not image_url:
                poll_url = (data.get("urls") or {}).get("get") or data.get("result_url")
                if not poll_url:
                    raise ExternalAPIError(
                        provider="seedream",
                        status_code=200,
                        message="Seedream 响应缺少 image_url",
                        response_data=raw,
                    )
                final_data = await self._poll_wavespeed_prediction(
                    poll_url, provider="seedream"
                )
                image_url = self._extract_output_url(final_data, key="image_url")
            if not image_url:
                raise ExternalAPIError(
                    provider="seedream",
                    status_code=200,
                    message="Seedream 未返回 image_url",
                    response_data=raw,
                )
            return [{"url": image_url, "width": width, "height": height}]

    async def generate_digital_human(
        self,
        job_id: str,
        avatar_mode: str,
        avatar_prompt: Optional[str] = None,
        avatar_upload_path: Optional[str] = None,
        speech_text: str = "",
        voice_id: str = "male-qn-qingse",
        resolution: str = "720p",
        speed: float = 1.0,
        pitch: int = 0,
        emotion: str = "neutral",
        seed: int = 42,
        mask_image: Optional[str] = None,
    ) -> Dict:
        """公开的数字人生成入口，返回最新的 task.json 数据。"""
        request = TaskRequest(
            avatar_mode=avatar_mode,
            avatar_prompt=avatar_prompt,
            avatar_upload_path=avatar_upload_path,
            speech_text=speech_text,
            voice_id=voice_id,
            resolution=resolution,
            speed=speed,
            pitch=pitch,
            emotion=emotion,
            seed=seed,
            mask_image=mask_image,
        )
        return await self.task_runner.run(job_id, request)

    async def _handle_avatar_upload(
        self,
        task_id: str,
        upload_path: Optional[str],
        target_path: Path,
    ) -> str:
        """复制上传头像到任务目录并返回可访问 URL。"""
        if not upload_path:
            raise ValueError("avatar_mode=upload 需要头像路径")

        source_path = Path(upload_path)
        if source_path.exists():
            self.storage.copy_into_task(source_path, target_path)
            return self._publish_avatar_asset(task_id, target_path)

        if upload_path.startswith(("http://", "https://")):
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.get(upload_path)
                if not response.is_success:
                    raise ExternalAPIError(
                        provider="avatar_upload",
                        status_code=response.status_code,
                        message=f"下载头像失败: {upload_path}",
                    )
            except httpx.TimeoutException as exc:
                raise ExternalAPIError(
                    provider="avatar_upload",
                    status_code=408,
                    message="下载头像超时",
                ) from exc
            except httpx.RequestError as exc:
                raise ExternalAPIError(
                    provider="avatar_upload",
                    status_code=0,
                    message=f"下载头像网络错误: {exc}",
                ) from exc

            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(response.content)
            return self._publish_avatar_asset(task_id, target_path)

        raise FileNotFoundError(f"头像文件不存在: {upload_path}")

    def _publish_avatar_asset(self, task_id: str, local_path: Path) -> str:
        """复制头像到 /mnt/www/output/<task_id>/ 并返回公网 URL。"""
        publish_info = None
        try:
            publish_info = self.storage.publish_task_asset(
                task_id, local_path, asset_dir="output", filename="avatar.png"
            )
        except PermissionError:
            publish_info = None

        if publish_info and publish_info.get("url"):
            return publish_info["url"]
        return self._build_public_avatar_url(local_path)

    def _build_public_avatar_url(self, target_path: Path) -> str:
        """生成指向 output 目录的公网 URL。"""
        output_root = self.storage.output_root
        try:
            relative = target_path.relative_to(output_root)
        except ValueError:
            relative = target_path
        public_path = Path("output") / relative
        return f"https://s.linapp.fun/{public_path.as_posix().lstrip('/')}"

    @staticmethod
    def _unwrap_wavespeed_result(payload: Dict[str, Any]) -> Dict[str, Any]:
        """兼容 WaveSpeed data 包裹结构。"""
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, dict):
                return data
        return payload

    @staticmethod
    def _extract_output_url(data: Dict[str, Any], key: str) -> Optional[str]:
        """从 output/outputs 中提取 URL。"""
        output = data.get("output")
        if isinstance(output, dict) and output.get(key):
            return output.get(key)
        outputs = data.get("outputs")
        if isinstance(outputs, list) and outputs:
            return outputs[0]
        return None

    async def _poll_wavespeed_prediction(
        self,
        poll_url: str,
        provider: str,
    ) -> Dict[str, Any]:
        """轮询 WaveSpeed 预测结果。"""
        headers = {"Authorization": f"Bearer {self.wavespeed_key}"}
        start = time.time()
        async with httpx.AsyncClient(timeout=30) as client:
            while time.time() - start < 300:
                try:
                    response = await client.get(poll_url, headers=headers)
                except httpx.TimeoutException:
                    await asyncio.sleep(3)
                    continue
                except httpx.RequestError as exc:
                    raise ExternalAPIError(
                        provider=provider,
                        status_code=0,
                        message=f"轮询 {provider} 任务失败: {exc}",
                    ) from exc

                if not response.is_success:
                    raise ExternalAPIError.from_response(
                        provider=provider,
                        response=response,
                        message=f"轮询 {provider} 任务失败",
                    )

                data = self._unwrap_wavespeed_result(response.json())
                status = data.get("status")
                if status in {"completed", "succeeded"}:
                    return data
                if status == "failed":
                    raise ExternalAPIError(
                        provider=provider,
                        status_code=200,
                        message=f"{provider} 任务失败: {data.get('error', 'unknown error')}",
                        response_data=data,
                    )
                await asyncio.sleep(3)

        raise ExternalAPIError(
            provider=provider,
            status_code=408,
            message="轮询 WaveSpeed 任务超时",
            response_data={"url": poll_url},
        )
