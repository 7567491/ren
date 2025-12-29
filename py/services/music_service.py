#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
背景音乐服务模块
支持本地音乐库管理和音视频混音
支持基于旁白音频的智能匹配
"""

import random
import yaml
import json
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from loguru import logger

# MoviePy导入（用于音频处理）
try:
    from moviepy import AudioFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger.warning("⚠️  MoviePy未安装，音乐处理功能将受限")

# 音频匹配器导入
try:
    from .audio_matcher import AudioMatcher
    AUDIO_MATCHER_AVAILABLE = True
except ImportError:
    AUDIO_MATCHER_AVAILABLE = False
    logger.warning("⚠️  音频匹配器未安装，智能匹配功能将受限")


class MusicService:
    """背景音乐服务"""

    def __init__(self, music_dir: str = "./resource/songs", config: Optional[Dict] = None):
        """
        初始化音乐服务

        Args:
            music_dir: 本地音乐库目录
            config: 配置字典（可选，如不提供则自动加载config.yaml）
        """
        self.music_dir = Path(music_dir)

        if not MOVIEPY_AVAILABLE:
            logger.error("❌ MoviePy未安装！请先运行: pip install moviepy")

        # 加载配置
        if config is None:
            config_file = Path(__file__).parent.parent.parent / 'config.yaml'
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            except FileNotFoundError:
                logger.warning(f"⚠️ 配置文件未找到: {config_file}，使用空配置")
                config = {}

        # 从配置文件的视觉风格中提取音乐关键词映射
        self.style_keywords = {}
        visual_styles = config.get('visual_styles', {})
        for style_key, style_data in visual_styles.items():
            music_keywords = style_data.get('music_keywords', [])
            if music_keywords:
                self.style_keywords[style_key] = music_keywords
            else:
                # 如果没有定义music_keywords，使用默认值
                self.style_keywords[style_key] = ['default']

        if not self.style_keywords:
            logger.warning("⚠️ 未从配置文件加载到风格关键词，使用默认配置")

        # 初始化音频匹配器
        self.audio_matcher = None
        if AUDIO_MATCHER_AVAILABLE:
            music_features_cache = self.music_dir.parent / 'music_features.json'
            if music_features_cache.exists():
                self.audio_matcher = AudioMatcher(str(music_features_cache))
                logger.info(f"✅ 已加载音乐特征缓存: {music_features_cache}")
            else:
                logger.warning(f"⚠️ 音乐特征缓存未找到: {music_features_cache}")
                logger.info(f"💡 提示: 运行预处理生成缓存: python py/services/audio_matcher.py {self.music_dir}")

    def validate_audio_file(self, music_file: Path) -> bool:
        """
        验证音频文件是否有效

        Args:
            music_file: 音乐文件路径

        Returns:
            True=有效, False=无效
        """
        if not MOVIEPY_AVAILABLE:
            logger.warning("⚠️  MoviePy未安装，无法验证音频文件")
            return True  # 无法验证时假设有效

        try:
            # 尝试加载音频文件
            audio = AudioFileClip(str(music_file))
            duration = audio.duration
            audio.close()

            # 检查时长是否合理（至少1秒）
            if duration < 1.0:
                logger.warning(f"⚠️  音频文件太短: {music_file.name} ({duration:.2f}s)")
                return False

            return True

        except Exception as e:
            logger.warning(f"⚠️  音频文件损坏或无效: {music_file.name} - {str(e)}")
            return False

    def get_available_music(self, validate: bool = True) -> List[Path]:
        """
        获取所有可用音乐文件

        Args:
            validate: 是否验证音频文件有效性（默认True）

        Returns:
            音乐文件路径列表
        """
        if not self.music_dir.exists():
            logger.error(f"❌ 音乐目录不存在: {self.music_dir}")
            return []

        # 支持的音频格式
        music_files = []
        for ext in ['.mp3', '.wav', '.m4a']:
            music_files.extend(self.music_dir.glob(f'*{ext}'))

        if not music_files:
            logger.warning(f"⚠️  音乐目录为空: {self.music_dir}")
            return []

        # 如果需要验证，过滤掉无效文件
        if validate:
            valid_files = []
            invalid_count = 0
            for music_file in music_files:
                if self.validate_audio_file(music_file):
                    valid_files.append(music_file)
                else:
                    invalid_count += 1

            if invalid_count > 0:
                logger.warning(f"⚠️  发现 {invalid_count} 个无效音频文件，已自动跳过")

            return valid_files

        return music_files

    def select_music(
        self,
        style: Optional[str] = None,
        prefer_style: bool = True
    ) -> Optional[Path]:
        """
        选择背景音乐

        Args:
            style: 视觉风格（如 'technology', 'xianxia'）
            prefer_style: 是否优先匹配风格（True=优先匹配，False=完全随机）

        Returns:
            选中的音乐文件路径，如果没有可用音乐则返回None
        """
        music_files = self.get_available_music()

        if not music_files:
            return None

        # 如果指定了风格且需要优先匹配
        if style and prefer_style and style in self.style_keywords:
            keywords = self.style_keywords[style]
            matched_files = []

            # 查找文件名包含关键词的音乐
            for music_file in music_files:
                file_name_lower = music_file.stem.lower()
                if any(keyword in file_name_lower for keyword in keywords):
                    matched_files.append(music_file)

            # 如果找到匹配的，从匹配列表中随机选择
            if matched_files:
                selected = random.choice(matched_files)
                logger.info(f"🎵 根据风格'{style}'选择音乐: {selected.name}")
                return selected
            else:
                logger.info(f"ℹ️  未找到匹配风格'{style}'的音乐，随机选择")

        # 随机选择
        selected = random.choice(music_files)
        logger.info(f"🎵 随机选择音乐: {selected.name}")
        return selected

    def select_music_intelligent(
        self,
        narration_audio_files: List[Path],
        visual_style: Optional[str] = None
    ) -> Optional[Path]:
        """
        基于旁白音频的智能音乐匹配（纯算法）

        Args:
            narration_audio_files: 旁白音频文件列表 [shot_1_audio.mp3, ...]
            visual_style: 视觉风格（保留参数兼容性，暂未使用）

        Returns:
            选中的音乐文件路径
        """
        if not AUDIO_MATCHER_AVAILABLE or self.audio_matcher is None:
            logger.warning("⚠️  音频匹配器不可用，降级到关键词匹配")
            return self.select_music(visual_style)

        logger.info("🎯 启动智能音乐匹配（纯算法）...")

        # 1. 分析旁白音频特征
        logger.info("📊 步骤1: 分析旁白音频特征...")
        narration_features = self.audio_matcher.analyze_narration_audio(narration_audio_files)

        if not narration_features:
            logger.error("❌ 旁白音频分析失败，降级到关键词匹配")
            return self.select_music(visual_style)

        # 2. 计算候选音乐排名
        logger.info("🔍 步骤2: 计算音乐匹配分数...")
        candidates = self.audio_matcher.rank_music_candidates(narration_features, top_k=5)

        if not candidates:
            logger.error("❌ 未找到候选音乐，降级到关键词匹配")
            return self.select_music(visual_style)

        # 打印候选列表
        logger.info("🏆 Top 5 候选音乐:")
        for i, (music_name, score, details) in enumerate(candidates, 1):
            logger.info(f"  {i}. {music_name} (总分: {score:.3f})")
            logger.info(f"     节奏: {details['rhythm_score']:.2f} | 能量: {details['energy_score']:.2f} | 动态: {details['dynamics_score']:.2f}")

        # 3. 选择得分最高的音乐
        best_music = candidates[0][0]
        best_score = candidates[0][1]
        best_details = candidates[0][2]

        selected_path = self.music_dir / best_music

        logger.success(f"✅ 算法选择音乐: {best_music}")
        logger.info(f"   匹配得分: {best_score:.3f}")
        logger.info(f"   旁白节奏: {best_details['narration_bpm_est']:.1f} BPM ↔ 音乐: {best_details['music_bpm']:.1f} BPM")
        logger.info(f"   循环次数: {best_details['loops_needed']:.1f} 次")

        return selected_path

    def prepare_background_music(
        self,
        music_file: Path,
        target_duration: float,
        volume: float = 0.25,
        output_file: Optional[str] = None
    ) -> Optional[AudioFileClip]:
        """
        准备背景音乐（循环/裁剪至目标时长，调整音量）

        Args:
            music_file: 音乐文件路径
            target_duration: 目标时长（秒）
            volume: 音量（0.0-1.0），推荐0.2-0.3，不盖过旁白
            output_file: 可选的输出文件路径（如果需要保存处理后的音频）

        Returns:
            处理后的AudioFileClip对象，失败返回None
        """
        if not MOVIEPY_AVAILABLE:
            logger.error("❌ MoviePy未安装，无法处理音乐")
            return None

        # 验证文件是否存在
        if not music_file.exists():
            logger.error(f"❌ 音乐文件不存在: {music_file}")
            return None

        try:
            # 先验证文件是否有效
            if not self.validate_audio_file(music_file):
                logger.error(f"❌ 音乐文件无效或损坏: {music_file.name}")
                logger.info(f"💡 建议: 请删除或替换损坏的文件: {music_file}")
                return None

            # 加载音乐文件
            music = AudioFileClip(str(music_file))
            original_duration = music.duration

            logger.info(f"🎵 加载音乐: {music_file.name}, 原始时长: {original_duration:.2f}s")

            # 调整音量
            music = music.with_volume_scaled(volume)
            logger.info(f"🔊 设置音量: {volume * 100:.0f}%")

            # 根据时长进行处理
            if music.duration < target_duration:
                # 音乐太短 → 循环播放
                import math
                from moviepy import concatenate_audioclips
                repeat_times = math.ceil(target_duration / music.duration)
                logger.info(f"🔁 音乐时长不足，循环 {repeat_times} 次")
                music = concatenate_audioclips([music] * repeat_times)
                music = music.subclipped(0, target_duration)
            else:
                # 音乐太长 → 裁剪
                logger.info(f"✂️  裁剪音乐从 {original_duration:.2f}s 到 {target_duration:.2f}s")
                music = music.subclipped(0, target_duration)

            logger.success(f"✅ 背景音乐准备完成，最终时长: {music.duration:.2f}s")

            # 如果指定了输出文件，保存处理后的音频
            if output_file:
                Path(output_file).parent.mkdir(parents=True, exist_ok=True)
                # 根据文件扩展名选择正确的编码器
                output_ext = Path(output_file).suffix.lower()
                if output_ext == '.mp3':
                    codec = 'libmp3lame'
                elif output_ext == '.wav':
                    codec = 'pcm_s16le'
                else:
                    codec = 'aac'  # 默认

                music.write_audiofile(
                    output_file,
                    codec=codec,
                    logger=None  # 关闭MoviePy日志
                )
                logger.success(f"💾 处理后的音乐已保存: {output_file}")

            return music

        except Exception as e:
            logger.error(f"❌ 音乐处理失败: {music_file.name}")
            logger.error(f"   错误详情: {str(e)}")
            logger.info(f"💡 建议: 请检查文件是否损坏或格式不支持")
            return None

    def get_music_info(self, music_file: Path) -> dict:
        """
        获取音乐文件信息

        Args:
            music_file: 音乐文件路径

        Returns:
            音乐信息字典
        """
        if not MOVIEPY_AVAILABLE:
            return {
                'name': music_file.name,
                'path': str(music_file),
                'duration': 0.0,
                'error': 'MoviePy未安装'
            }

        try:
            music = AudioFileClip(str(music_file))
            info = {
                'name': music_file.name,
                'path': str(music_file),
                'duration': music.duration,
                'fps': music.fps,
                'channels': music.nchannels
            }
            music.close()
            return info

        except Exception as e:
            return {
                'name': music_file.name,
                'path': str(music_file),
                'error': str(e)
            }

    def list_all_music(self) -> List[dict]:
        """
        列出所有可用音乐及其信息

        Returns:
            音乐信息列表
        """
        music_files = self.get_available_music()
        music_list = []

        logger.info(f"📂 扫描音乐目录: {self.music_dir}")

        for music_file in music_files:
            info = self.get_music_info(music_file)
            music_list.append(info)

        logger.info(f"✅ 找到 {len(music_list)} 个音乐文件")
        return music_list


# 便捷函数
def get_background_music(
    style: Optional[str] = None,
    target_duration: float = 30.0,
    volume: float = 0.25,
    music_dir: str = "./resource/songs"
) -> Optional[AudioFileClip]:
    """
    便捷函数：一步获取处理好的背景音乐

    Args:
        style: 视觉风格
        target_duration: 目标时长（秒）
        volume: 音量（0.0-1.0）
        music_dir: 音乐目录

    Returns:
        处理后的AudioFileClip对象
    """
    service = MusicService(music_dir)
    music_file = service.select_music(style)

    if not music_file:
        logger.error("❌ 未找到可用音乐")
        return None

    return service.prepare_background_music(music_file, target_duration, volume)
