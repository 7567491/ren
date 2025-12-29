#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音合成服务模块
支持 Edge TTS（免费、高质量）
"""

import asyncio
import edge_tts
from pathlib import Path
from typing import Optional, Tuple
from loguru import logger


class VoiceService:
    """语音合成服务"""

    def __init__(self, provider="edge"):
        """
        初始化语音服务

        Args:
            provider: 服务提供商，目前只支持"edge"
        """
        self.provider = provider

    def generate_audio(
        self,
        text: str,
        output_file: str,
        voice_name: str = "zh-CN-YunyangNeural"
    ) -> Tuple[Optional[object], float]:
        """
        使用Edge TTS生成配音

        Args:
            text: 旁白文案
            output_file: 输出音频文件路径
            voice_name: 音色名称

        Returns:
            (sub_maker, duration): SubMaker对象（包含字幕时间戳）和音频时长（秒）
        """
        try:
            async def _generate():
                communicate = edge_tts.Communicate(text, voice_name)
                sub_maker = edge_tts.SubMaker()

                # 创建输出目录
                Path(output_file).parent.mkdir(parents=True, exist_ok=True)

                with open(output_file, "wb") as file:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            file.write(chunk["data"])
                        elif chunk["type"] in ["WordBoundary", "SentenceBoundary"]:
                            # 记录字幕时间戳
                            sub_maker.feed(chunk)

                return sub_maker

            # 运行异步生成
            sub_maker = asyncio.run(_generate())

            # 计算音频时长
            duration = 0.0
            if sub_maker and sub_maker.cues:
                last_cue = sub_maker.cues[-1]
                duration = last_cue.end.total_seconds()

            logger.success(f"✅ 配音生成成功: {output_file}, 时长: {duration:.2f}s")
            return sub_maker, duration

        except Exception as e:
            logger.error(f"❌ 配音生成失败: {str(e)}")
            return None, 0.0

    @staticmethod
    def get_available_voices(language="zh-CN"):
        """
        获取可用音色列表

        Args:
            language: 语言代码，如"zh-CN"

        Returns:
            list: 音色字典列表 [{"name": "...", "gender": "...", "description": "..."}, ...]
        """
        # Edge TTS 常用中文音色
        voices = {
            "zh-CN": [
                {
                    "name": "zh-CN-XiaoxiaoNeural",
                    "gender": "Female",
                    "description": "晓晓（温柔女声）"
                },
                {
                    "name": "zh-CN-XiaoyiNeural",
                    "gender": "Female",
                    "description": "晓伊（活泼女声）"
                },
                {
                    "name": "zh-CN-YunjianNeural",
                    "gender": "Male",
                    "description": "云健（运动男声）"
                },
                {
                    "name": "zh-CN-YunxiNeural",
                    "gender": "Male",
                    "description": "云希（成熟男声）"
                },
                {
                    "name": "zh-CN-YunxiaNeural",
                    "gender": "Male",
                    "description": "云夏（阳光男声）"
                },
                {
                    "name": "zh-CN-YunyangNeural",
                    "gender": "Male",
                    "description": "云扬（年轻男声）"
                },
            ],
            "en-US": [
                {
                    "name": "en-US-AriaNeural",
                    "gender": "Female",
                    "description": "Aria (Female)"
                },
                {
                    "name": "en-US-GuyNeural",
                    "gender": "Male",
                    "description": "Guy (Male)"
                },
            ]
        }
        return voices.get(language, [])

    @staticmethod
    def get_default_voice(language="zh-CN", gender="Female"):
        """
        获取默认音色

        Args:
            language: 语言代码
            gender: 性别，"Female" 或 "Male"

        Returns:
            str: 音色名称
        """
        voices = VoiceService.get_available_voices(language)
        for voice in voices:
            if voice["gender"] == gender:
                return voice["name"]

        # 如果没找到，返回第一个
        return voices[0]["name"] if voices else "zh-CN-YunyangNeural"
