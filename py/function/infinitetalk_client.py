#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Infinitetalk 唇同步客户端，供数字人流水线复用。"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from py.exceptions import ExternalAPIError


class InfiniteTalkClient:
    """Wavespeed Infinitetalk API 的极简封装。"""

    def __init__(self, api_key: str, base_url: str = "https://api.wavespeed.ai/api/v3"):
        self.api_key = api_key
        self.base_url = base_url
        self.endpoint = "wavespeed-ai/infinitetalk"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def submit(self, endpoint: str, payload: Dict[str, Any]) -> str:
        """提交任务到 Wavespeed API。"""
        url = f"{self.base_url}/{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, headers=self.headers, json=payload)
                if not response.is_success:
                    raise ExternalAPIError.from_response(
                        provider="infinitetalk",
                        response=response,
                        message="提交 Infinitetalk 任务失败",
                    )
                data = self._unwrap_response(response.json())
        except httpx.TimeoutException as exc:
            raise ExternalAPIError(
                provider="infinitetalk",
                message="提交 Infinitetalk 任务超时",
                status_code=408,
                original_exception=exc,
            ) from exc
        except httpx.RequestError as exc:
            raise ExternalAPIError(
                provider="infinitetalk",
                message=f"提交 Infinitetalk 任务网络错误: {exc}",
                status_code=0,
                original_exception=exc,
            ) from exc
        except ExternalAPIError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ExternalAPIError(
                provider="infinitetalk",
                message=f"提交 Infinitetalk 任务未知错误: {exc}",
                status_code=0,
                original_exception=exc,
            ) from exc

        task_id = data.get("task_id") or data.get("id")
        if not task_id:
            raise ExternalAPIError(
                provider="infinitetalk",
                message="API 响应未返回任务ID",
                status_code=200,
                response_data=data,
            )
        return str(task_id)

    async def wait_for_result(
        self,
        task_id: str,
        max_wait: int = 600,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """轮询任务状态，直至完成或失败。"""
        status_url = f"{self.base_url}/predictions/{task_id}/result"
        start = asyncio.get_event_loop().time()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                while asyncio.get_event_loop().time() - start < max_wait:
                    try:
                        response = await client.get(status_url, headers=self.headers)
                        if not response.is_success:
                            raise ExternalAPIError.from_response(
                                provider="infinitetalk",
                                response=response,
                                message="查询 Infinitetalk 任务状态失败",
                            )
                        data = self._unwrap_response(response.json())
                    except httpx.RequestError:
                        await asyncio.sleep(poll_interval)
                        continue

                    state = data.get("state") or data.get("status")
                    if state == "completed":
                        output = data.get("output") or {}
                        outputs = data.get("outputs") or []
                        if not output and outputs:
                            output = {
                                "video_url": outputs[0],
                                "duration": data.get("duration")
                                or data.get("executionTime", 0) / 1000.0,
                            }
                        if not output:
                            raise ExternalAPIError(
                                provider="infinitetalk",
                                message="任务完成但无输出",
                                status_code=200,
                                response_data=data,
                            )
                        return output
                    if state == "failed":
                        error = data.get("error", "未知错误")
                        raise ExternalAPIError(
                            provider="infinitetalk",
                            message=f"Infinitetalk 任务失败: {error}",
                            status_code=200,
                            response_data=data,
                        )
                    await asyncio.sleep(poll_interval)
        except ExternalAPIError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ExternalAPIError(
                provider="infinitetalk",
                message=f"轮询 Infinitetalk 任务未知错误: {exc}",
                status_code=0,
                original_exception=exc,
            ) from exc

        raise ExternalAPIError(
            provider="infinitetalk",
            message=f"等待 Infinitetalk 任务完成超时 ({max_wait}秒)",
            status_code=408,
        )

    @staticmethod
    def _unwrap_response(resp: Dict[str, Any]) -> Dict[str, Any]:
        """兼容 Wavespeed {code,message,data} 响应。"""
        if isinstance(resp, dict):
            data = resp.get("data")
            if isinstance(data, dict):
                return data
        return resp

    async def download(self, url: str, target: Path) -> Path:
        """下载唇同步视频到本地。"""
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.get(url)
                if not response.is_success:
                    raise ExternalAPIError(
                        provider="infinitetalk",
                        message=f"下载 Infinitetalk 视频失败: {url}",
                        status_code=response.status_code,
                    )
                target.write_bytes(response.content)
        except httpx.TimeoutException as exc:
            raise ExternalAPIError(
                provider="infinitetalk",
                message="下载 Infinitetalk 视频超时",
                status_code=408,
                original_exception=exc,
            ) from exc
        except httpx.RequestError as exc:
            raise ExternalAPIError(
                provider="infinitetalk",
                message=f"下载 Infinitetalk 视频网络错误: {exc}",
                status_code=0,
                original_exception=exc,
            ) from exc
        except ExternalAPIError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ExternalAPIError(
                provider="infinitetalk",
                message=f"保存 Infinitetalk 视频失败: {exc}",
                status_code=0,
                original_exception=exc,
            ) from exc
        return target

    def _calculate_cost(self, duration: float, resolution: str) -> float:
        """根据时长和分辨率估算费用。"""
        rates = {
            "720p": 0.06,
            "1080p": 0.12,
        }
        return duration * rates.get(resolution, 0.06)

    async def generate_video(
        self,
        image_url: str,
        audio_url: str,
        resolution: str = "720p",
        seed: int = 42,
        mask_image: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """封装完整的唇同步生成流程。"""
        payload = {
            "image": image_url,
            "audio": audio_url,
            "image_url": image_url,
            "audio_url": audio_url,
            "resolution": resolution,
            "seed": seed,
        }
        if mask_image:
            payload["mask_image"] = mask_image
        if prompt:
            payload["prompt"] = prompt

        task_id = await self.submit(self.endpoint, payload)
        result = await self.wait_for_result(task_id, max_wait=600, poll_interval=5)

        video_url = result.get("video_url")
        if not video_url:
            raise ExternalAPIError(
                provider="infinitetalk",
                message="Infinitetalk 结果中缺少 video_url",
                status_code=200,
                response_data=result,
            )

        video_path = Path(f"output/{task_id}/digital_human.mp4")
        await self.download(video_url, video_path)

        duration = result.get("duration", 0)
        return {
            "task_id": task_id,
            "video_url": video_url,
            "video_path": str(video_path),
            "duration": duration,
            "cost": self._calculate_cost(duration, resolution),
        }


__all__ = ["InfiniteTalkClient"]
