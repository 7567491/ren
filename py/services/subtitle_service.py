#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕生成服务模块
支持 SubMaker（从Edge TTS字幕时间戳生成SRT）
"""

import re
from pathlib import Path
from typing import List, Dict
from loguru import logger


class SubtitleService:
    """字幕生成服务"""

    def __init__(self, provider="submaker"):
        """
        初始化字幕服务

        Args:
            provider: 服务提供商，目前只支持"submaker"
        """
        self.provider = provider

    @staticmethod
    def split_by_punctuation(text: str) -> List[str]:
        """
        按标点符号分割文本

        Args:
            text: 输入文本

        Returns:
            list: 分割后的句子列表
        """
        # 清理文本
        text = text.replace("\n", " ")
        text = text.replace("[", " ")
        text = text.replace("]", " ")
        text = text.replace("(", " ")
        text = text.replace(")", " ")
        text = text.replace("{", " ")
        text = text.replace("}", " ")
        text = text.strip()

        # 中文和英文标点符号
        punctuations = r'[。！？，；：、,.!?;:\n]'
        lines = re.split(punctuations, text)
        return [line.strip() for line in lines if line.strip()]

    def create_from_submaker(
        self,
        sub_maker: object,
        script_text: str,
        output_file: str
    ) -> bool:
        """
        从Edge TTS的SubMaker生成字幕

        Args:
            sub_maker: Edge TTS返回的SubMaker对象
            script_text: 原始旁白文案
            output_file: 输出SRT文件路径

        Returns:
            bool: 是否成功
        """
        try:
            if not sub_maker or not sub_maker.cues:
                logger.warning("⚠️  SubMaker为空或没有字幕数据")
                return False

            # 直接使用SubMaker生成的SRT
            # SubMaker已经按句子分好了，我们直接使用
            srt_content = sub_maker.get_srt()

            # 如果需要，可以根据script_text的分句来重新组织字幕
            # 但通常SubMaker的分句已经很好了

            # 创建输出目录
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)

            # 写入SRT文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(srt_content)

            subtitle_count = len(sub_maker.cues)
            logger.success(f"✅ 字幕生成成功: {output_file}, 共 {subtitle_count} 条")
            return True

        except Exception as e:
            logger.error(f"❌ 字幕生成失败: {str(e)}")
            return False

    def create_simple_subtitle(
        self,
        script_text: str,
        audio_duration: float,
        output_file: str
    ) -> bool:
        """
        基于文案和音频时长生成简单字幕（备用方案）

        Args:
            script_text: 旁白文案
            audio_duration: 音频总时长（秒）
            output_file: 输出SRT文件路径

        Returns:
            bool: 是否成功
        """
        try:
            script_lines = self.split_by_punctuation(script_text)

            if not script_lines:
                logger.warning("⚠️  文案为空，无法生成字幕")
                return False

            # 平均分配时间
            time_per_line = audio_duration / len(script_lines)
            subtitles = []

            for i, line in enumerate(script_lines):
                start = i * time_per_line
                end = (i + 1) * time_per_line

                subtitles.append({
                    'index': i + 1,
                    'start': self._format_time_seconds(start),
                    'end': self._format_time_seconds(end),
                    'text': line
                })

            # 创建输出目录
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)

            # 写入SRT文件
            self._write_srt(subtitles, output_file)

            logger.success(f"✅ 简单字幕生成成功: {output_file}, 共 {len(subtitles)} 条")
            return True

        except Exception as e:
            logger.error(f"❌ 简单字幕生成失败: {str(e)}")
            return False

    @staticmethod
    def _format_time_seconds(seconds: float) -> str:
        """
        格式化时间为SRT格式（HH:MM:SS,mmm）

        Args:
            seconds: 秒数

        Returns:
            str: SRT格式时间字符串
        """
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    @staticmethod
    def _write_srt(subtitles: List[Dict], output_file: str):
        """
        写入SRT文件

        Args:
            subtitles: 字幕列表
            output_file: 输出文件路径
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            for sub in subtitles:
                f.write(f"{sub['index']}\n")
                f.write(f"{sub['start']} --> {sub['end']}\n")
                f.write(f"{sub['text']}\n\n")
