"""
MiniMax TTS 服务

提供 MiniMax speech-02-hd TTS 服务
"""
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Callable

import httpx

from py.exceptions import ExternalAPIError


class MiniMaxTTSService:
    """MiniMax speech-02-hd TTS 客户端"""

    def __init__(self, api_key: str):
        """
        初始化 TTS 服务

        Args:
            api_key: MiniMax API 密钥（或 WaveSpeed API 密钥）
        """
        self.api_key = api_key
        self.base_url = "https://api.wavespeed.ai/api/v3"
        self.endpoint = f"{self.base_url}/minimax/speech-02-hd"

    async def generate_voice(
        self,
        text: str,
        voice_id: str = "male-qn-qingse",
        speed: float = 1.0,
        pitch: int = 0,
        emotion: str = "neutral",
        output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        生成语音

        Args:
            text: 文本内容
            voice_id: 音色ID
                - male-qn-qingse: 男声青涩
                - female-shaonv: 女声少女
                - male-qn-jingying: 男声精英
                - female-yujie: 女声御姐
                - Wise_Woman: 智慧女性
                - Young_Male: 年轻男性
                - Professional_Female: 职业女性
            speed: 语速 0.5-2.0
            pitch: 音调 -12~12
            emotion: 情绪 neutral/happy/sad/angry
            output_path: 输出路径（可选）

        Returns:
            {
                "audio_url": "https://...",
                "audio_path": "output/.../speech.mp3",  # 如果提供了 output_path
                "duration": 12.5,
                "cost": 0.025
            }

        Raises:
            ExternalAPIError: 外部 API 调用错误
        """
        # 构建请求参数
        payload = {
            "text": text,
            "voice_id": voice_id,
            "speed": speed,
            "pitch": pitch,
            "emotion": emotion,
            "sample_rate": 32000,
            "channel": 1,
            "english_normalization": True
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        result = await self._with_retry(lambda: self._request_tts(payload, headers))

        # 解析响应
        output = result.get("output", {})
        audio_url = output.get("audio_url")
        if not audio_url:
            raise ExternalAPIError(
                provider="minimax",
                message="API 响应缺少 audio_url",
                status_code=200,
                response_data=result
            )

        # 下载音频（如果提供了输出路径）
        audio_path_str = None
        if output_path:
            await self._download_audio(audio_url, output_path)
            audio_path_str = str(output_path)

        # 计算成本
        duration = output.get("duration", 0)
        cost = self._calculate_cost(duration)

        return {
            "audio_url": audio_url,
            "audio_path": audio_path_str,
            "duration": duration,
            "cost": cost
        }

    async def _download_audio(self, url: str, target: Path):
        """
        下载音频文件

        Args:
            url: 音频文件URL
            target: 目标路径

        Raises:
            ExternalAPIError: 下载失败
        """
        target.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.get(url)

                if not response.is_success:
                    raise ExternalAPIError(
                        provider="minimax",
                        message=f"下载音频失败: {url}",
                        status_code=response.status_code
                    )

                target.write_bytes(response.content)

        except httpx.TimeoutException as e:
            raise ExternalAPIError(
                provider="minimax",
                message="下载音频超时",
                status_code=408,
                original_exception=e
            )
        except httpx.RequestError as e:
            raise ExternalAPIError(
                provider="minimax",
                message=f"下载音频错误: {str(e)}",
                status_code=0,
                original_exception=e
            )
        except ExternalAPIError:
            raise
        except Exception as e:
            raise ExternalAPIError(
                provider="minimax",
                message=f"保存音频文件失败: {str(e)}",
                status_code=0,
                original_exception=e
            )

    async def _request_tts(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(self.endpoint, json=payload, headers=headers)

                if not response.is_success:
                    raise ExternalAPIError.from_response(
                        provider="minimax",
                        response=response,
                        message="MiniMax TTS 请求失败"
                    )

                return response.json()

        except httpx.TimeoutException as e:
            raise ExternalAPIError(
                provider="minimax",
                message="MiniMax TTS 请求超时",
                status_code=408,
                original_exception=e
            )
        except httpx.RequestError as e:
            raise ExternalAPIError(
                provider="minimax",
                message=f"MiniMax TTS 请求错误: {str(e)}",
                status_code=0,
                original_exception=e
            )
        except ExternalAPIError:
            raise
        except Exception as e:
            raise ExternalAPIError(
                provider="minimax",
                message=f"MiniMax TTS 未知错误: {str(e)}",
                status_code=0,
                original_exception=e
            )

    async def _with_retry(self, func: Callable[[], Any], max_attempts: int = 3, base_delay: int = 5):
        attempt = 0
        while True:
            attempt += 1
            try:
                return await func()
            except ExternalAPIError as err:
                if not err.is_retryable() or attempt >= max_attempts:
                    raise
                await asyncio.sleep(base_delay * attempt)

    def _calculate_cost(self, duration: float) -> float:
        """
        计算成本

        Args:
            duration: 音频时长（秒）

        Returns:
            成本（美元）

        规则:
            $0.02/分钟
        """
        return (duration / 60) * 0.02
