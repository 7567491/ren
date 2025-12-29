#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频合成服务模块
负责音视频字幕的最终合成

注意：需要先安装 moviepy 和系统依赖（如 ImageMagick）
"""

import os
import random
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from loguru import logger
from services import font_manager

try:
    from PIL import ImageFont
except ImportError:  # pragma: no cover - Pillow 在运行时安装
    ImageFont = None  # type: ignore[assignment]

# 抑制MoviePy读取视频最后一帧的警告（不影响功能）
warnings.filterwarnings('ignore', message='.*bytes wanted but 0 bytes read.*')

# MoviePy导入（可选，如果未安装会fallback到简单模式）
try:
    # MoviePy 2.x 使用新的导入路径
    from moviepy import (
        VideoFileClip,
        AudioFileClip,
        TextClip,
        ImageClip,
        CompositeVideoClip,
        CompositeAudioClip,
        concatenate_videoclips
    )
    from moviepy.video.tools import subtitles
    import moviepy.config as mpconfig

    # 配置ImageMagick路径（macOS Homebrew）
    if os.path.exists('/opt/homebrew/bin/magick'):
        mpconfig.IMAGEMAGICK_BINARY = '/opt/homebrew/bin/magick'
    elif os.path.exists('/usr/local/bin/magick'):
        mpconfig.IMAGEMAGICK_BINARY = '/usr/local/bin/magick'

    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger.warning("⚠️  MoviePy未安装，视频合成功能将受限")


class VideoComposer:
    """视频合成器"""

    DEFAULT_FONT_CANDIDATES = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]

    def __init__(self, temp_dir: str = "./temp", config: Optional[Dict] = None):
        """
        初始化视频合成器

        Args:
            temp_dir: 临时文件目录
            config: 配置字典（可选）
        """
        self.config = config or self._load_config()
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.local_font_candidates = font_manager.ensure_fonts()

        if not MOVIEPY_AVAILABLE:
            logger.error("❌ MoviePy未安装！请先运行: pip install moviepy")

        encoding_config = self.config.get('video_encoding', {})

        # 统一的视频写入参数，提高编码质量
        self.write_params = {
            'codec': encoding_config.get('codec', 'libx264'),
            'audio_codec': encoding_config.get('audio_codec', 'aac'),
            'preset': encoding_config.get('preset', 'medium'),
            'logger': encoding_config.get('logger'),
            'threads': encoding_config.get('threads', 4),
            'ffmpeg_params': encoding_config.get('ffmpeg_params', ['-pix_fmt', 'yuv420p']),
        }

        self.subtitle_style_config = self.config.get('subtitles', {}).get('default_style', {})

    @staticmethod
    def _load_config() -> Dict:
        """加载config.yaml"""
        config_file = Path(__file__).parent.parent.parent / 'config.yaml'
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"⚠️ 配置文件未找到: {config_file}")
            return {}

    def add_audio_to_video(
        self,
        video_file: str,
        audio_file: str,
        output_file: str
    ) -> bool:
        """
        为视频添加音频

        Args:
            video_file: 输入视频文件
            audio_file: 音频文件
            output_file: 输出视频文件

        Returns:
            bool: 是否成功
        """
        if not MOVIEPY_AVAILABLE:
            logger.error("❌ MoviePy未安装，无法合成视频")
            return False

        try:
            video = VideoFileClip(video_file)
            audio = AudioFileClip(audio_file)

            # 如果音频长于视频，裁剪音频；音频短于视频则保持视频长度不变
            if audio.duration > video.duration:
                logger.warning(f"   ⚠️  音频({audio.duration:.2f}s)长于视频({video.duration:.2f}s)，裁剪音频")
                audio = audio.subclipped(0, video.duration)
            elif audio.duration < video.duration:
                # 让音频保持原时长，视频保持完整，MoviePy会自动在后段保持静音
                logger.info(f"   ℹ️  音频短于视频 ({audio.duration:.2f}s < {video.duration:.2f}s)，视频保持完整")

            video = video.with_audio(audio)
            video.write_videofile(output_file, **self.write_params)

            video.close()
            audio.close()

            logger.success(f"✅ 音频添加成功: {output_file}")
            return True

        except Exception as e:
            logger.error(f"❌ 音频添加失败: {str(e)}")
            return False

    def add_subtitles_to_video(
        self,
        video_file: str,
        subtitle_file: str,
        output_file: str,
        style_config: Optional[Dict] = None
    ) -> bool:
        """
        为视频添加字幕

        Args:
            video_file: 输入视频文件
            subtitle_file: SRT字幕文件
            output_file: 输出视频文件
            style_config: 字幕样式配置

        Returns:
            bool: 是否成功
        """
        if not MOVIEPY_AVAILABLE:
            logger.error("❌ MoviePy未安装，无法添加字幕")
            return False

        try:
            if style_config is None:
                style_config = self._default_subtitle_style()

            font_name = self._resolve_subtitle_font(style_config)
            if not font_name:
                logger.error("❌ 找不到可用字体，请安装中文字体或在config.yaml中配置 subtitles.default_style.font")
                return False

            video = VideoFileClip(video_file)

            # 字幕生成器
            def generator(txt):
                return TextClip(
                    font=font_name,
                    text=txt,
                    font_size=style_config.get('fontsize', 48),
                    color=style_config.get('color', 'white'),
                    stroke_color=style_config.get('stroke_color', 'black'),
                    stroke_width=style_config.get('stroke_width', 2),
                    method='caption',
                    size=(int(video.w * 0.9), None),
                    text_align='center'
                )

            # 读取字幕
            subs = subtitles.file_to_subtitles(subtitle_file, encoding='utf-8')

            bottom_margin = style_config.get('bottom_margin', 60)  # 保持底部留白，避免贴边
            offset_ratio = style_config.get('line_offset_ratio', 0)

            # 创建字幕clips
            subtitle_clips = []
            for ((start, end), txt) in subs:
                clip = generator(txt)
                base_y = max(0, video.h - clip.h - bottom_margin)
                # 按配置抬升字幕，避免始终上移半行导致底部被裁
                y_pos = max(0, base_y - clip.h * offset_ratio)
                clip = clip.with_position(('center', y_pos))
                clip = clip.with_start(start)
                clip = clip.with_duration(end - start)
                subtitle_clips.append(clip)

            # 合成
            final = CompositeVideoClip([video] + subtitle_clips)
            final.write_videofile(output_file, **self.write_params)

            video.close()
            final.close()

            logger.success(f"✅ 字幕添加成功: {output_file}")
            return True

        except Exception as e:
            logger.error(f"❌ 字幕添加失败: {str(e)}")
            logger.error(f"   错误类型: {type(e).__name__}")
            logger.info(f"   提示: 请确保已安装ImageMagick")
            # 打印详细堆栈
            import traceback
            logger.error(f"   详细错误:\n{traceback.format_exc()}")
            return False

    def _resolve_subtitle_font(self, style_config: Dict) -> Optional[str]:
        """
        选择一个可用的字幕字体。优先用户配置，其次 fallback。
        """
        requested = style_config.get('font')
        fallback_cfg = self.config.get('subtitles', {}).get('fallback_fonts', [])
        fallback_list = fallback_cfg if isinstance(fallback_cfg, list) else []
        style_candidates = style_config.get('font_candidates', [])
        if isinstance(style_candidates, list):
            fallback_style = [c for c in style_candidates if c]
        else:
            fallback_style = []

        candidates = [requested] if requested else []
        candidates.extend(fallback_style)
        candidates.extend(fallback_list)
        candidates.extend(self.local_font_candidates)
        candidates.extend(self.DEFAULT_FONT_CANDIDATES)

        for font in candidates:
            resolved = self._validate_font(font)
            if resolved:
                if font != requested and requested:
                    logger.warning(f"⚠️ 字体 {requested} 不可用，改用 {resolved}")
                return resolved
        return self._validate_font("DejaVuSans") or None

    @staticmethod
    def _validate_font(font: Optional[str]) -> Optional[str]:
        if not font:
            return None
        path = Path(font).expanduser()
        if path.exists():
            return str(path)
        if ImageFont is None:
            return None
        try:
            ImageFont.truetype(font, size=48)
            return font
        except Exception:
            return None

    def add_background_music(
        self,
        video_file: str,
        music_file: str,
        output_file: str,
        voice_volume: float = 1.0,
        music_volume: float = 0.3
    ) -> bool:
        """
        为视频添加背景音乐

        Args:
            video_file: 输入视频文件（已有配音）
            music_file: 背景音乐文件
            output_file: 输出视频文件
            voice_volume: 配音音量（0.0-1.0）
            music_volume: 背景音乐音量（0.0-1.0）

        Returns:
            bool: 是否成功
        """
        if not MOVIEPY_AVAILABLE:
            logger.error("❌ MoviePy未安装，无法添加背景音乐")
            return False

        # 验证文件是否存在
        from pathlib import Path
        if not Path(video_file).exists():
            logger.error(f"❌ 视频文件不存在: {video_file}")
            return False

        if not Path(music_file).exists():
            logger.error(f"❌ 音乐文件不存在: {music_file}")
            return False

        try:
            logger.info(f"🎵 开始添加背景音乐: {Path(music_file).name}")

            # 加载视频文件
            video = VideoFileClip(video_file)
            logger.info(f"   视频时长: {video.duration:.2f}秒")

            # 加载背景音乐（这里可能会失败，如果文件损坏）
            try:
                bg_music = AudioFileClip(music_file)
            except Exception as audio_error:
                logger.error(f"❌ 无法加载音乐文件: {Path(music_file).name}")
                logger.error(f"   错误详情: {str(audio_error)}")
                logger.info(f"💡 建议: 该音乐文件可能已损坏，请删除或替换")
                logger.info(f"   文件路径: {music_file}")
                video.close()
                return False

            # 调整音量
            bg_music = bg_music.with_volume_scaled(music_volume)
            logger.info(f"   音乐时长: {bg_music.duration:.2f}秒, 音量: {music_volume * 100:.0f}%")

            # 背景音乐循环或裁剪
            if bg_music.duration < video.duration:
                # 循环播放 - 重复多次直到达到所需时长
                import math
                repeat_times = math.ceil(video.duration / bg_music.duration)
                from moviepy import concatenate_audioclips
                logger.info(f"   音乐循环 {repeat_times} 次以匹配视频时长")
                bg_music = concatenate_audioclips([bg_music] * repeat_times)
                bg_music = bg_music.subclipped(0, video.duration)
            else:
                # 裁剪
                logger.info(f"   裁剪音乐至 {video.duration:.2f}秒")
                bg_music = bg_music.subclipped(0, video.duration)

            # 混合原音频和背景音乐
            if video.audio:
                voice_audio = video.audio.with_volume_scaled(voice_volume)
                final_audio = CompositeAudioClip([voice_audio, bg_music])
                logger.info(f"   混合配音（{voice_volume * 100:.0f}%）和背景音乐")
            else:
                final_audio = bg_music
                logger.warning("   视频无原音频，仅使用背景音乐")

            video = video.with_audio(final_audio)
            logger.info(f"   正在导出视频...")
            video.write_videofile(output_file, **self.write_params)

            video.close()
            bg_music.close()

            logger.success(f"✅ 背景音乐添加成功: {output_file}")
            return True

        except Exception as e:
            logger.error(f"❌ 背景音乐添加失败: {str(e)}")
            logger.error(f"   错误类型: {type(e).__name__}")
            # 打印详细错误信息
            import traceback
            logger.error(f"   详细错误:\n{traceback.format_exc()}")
            return False

    def add_logo_animation(
        self,
        video_file: str,
        logo_file: str,
        output_file: str,
        position: str = 'end',
        duration: float = 2.0,
        fadein_time: float = 1.0,
        fadeout_time: float = 0.0,
        logo_scale: float = 0.3
    ) -> bool:
        """
        为视频添加logo动画（淡入淡出效果）

        Args:
            video_file: 输入视频文件
            logo_file: logo图片文件（PNG/JPG，推荐透明PNG）
            output_file: 输出视频文件
            position: logo显示位置，固定为片尾
            duration: logo展示总时长（秒）
            fadein_time: 淡入时长（秒）
            fadeout_time: 保留参数（未使用，淡出关闭）
            logo_scale: logo缩放比例（相对视频宽度，0.3=视频宽度的30%）

        Returns:
            bool: 是否成功
        """
        if not MOVIEPY_AVAILABLE:
            logger.error("❌ MoviePy未安装，无法添加logo")
            return False

        try:
            video = VideoFileClip(video_file)
            logo = ImageClip(logo_file)

            # 背景音乐在尾部渐强配置
            bgm_boost_factor = 3.0  # 最终增益倍数
            bgm_boost_duration = 2.0  # 渐强时长

            # 仅支持片尾展示，其他设置强制为片尾
            if position != 'end':
                logger.info("   ℹ️ Logo动画仅展示片尾，忽略其他位置设置")
            position = 'end'

            # 在尾部做BGM渐强（与logo展示时长一致，在原视频上进行）
            if video.audio and duration > 0:
                try:
                    import moviepy.audio.fx as afx
                    ramp_start = max(video.duration - bgm_boost_duration, 0)
                    main_audio = video.audio.subclipped(0, ramp_start)
                    tail_audio = video.audio.subclipped(ramp_start, video.duration)
                    tail_audio = tail_audio.with_effects([
                        afx.MultiplyVolume(bgm_boost_factor),
                        afx.AudioFadeIn(bgm_boost_duration)
                    ])
                    final_audio = CompositeAudioClip([
                        main_audio,
                        tail_audio.with_start(ramp_start)
                    ])
                    video = video.with_audio(final_audio)
                except Exception:
                    logger.warning("⚠️  背景音乐渐强处理失败，使用原音量")

            # 时长兜底，避免logo时长超过视频时长
            duration = min(duration, video.duration)
            if duration <= 0:
                logger.error("❌ 视频时长过短，无法添加logo动画")
                video.close()
                logo.close()
                return False

            # 根据视频尺寸调整logo大小
            target_width = int(video.w * logo_scale)
            logo = logo.resized(width=target_width)

            # 创建logo clips列表
            logo_clips = []

            # 片尾logo
            logo_end = logo.with_duration(duration)
            logo_end = logo_end.with_position('center')  # 正中间
            logo_end = logo_end.with_start(video.duration - duration)
            # 兼容MoviePy不同版本的淡入实现
            try:
                if hasattr(logo_end, "fadein"):
                    logo_end = logo_end.fadein(fadein_time)
                else:
                    from moviepy.video.fx import FadeIn
                    logo_end = logo_end.with_effects([FadeIn(fadein_time)])
            except Exception:
                logger.warning("⚠️  Logo淡入效果应用失败，改为直接展示")
            logo_clips.append(logo_end)
            logger.info(f"   📍 片尾logo: {video.duration - duration:.1f}s-{video.duration:.1f}s (淡入{fadein_time}s)")

            # 片尾原视频淡出（变暗）
            try:
                if hasattr(video, "fadeout"):
                    video_with_fade = video.fadeout(duration)
                else:
                    from moviepy.video.fx import FadeOut
                    video_with_fade = video.with_effects([FadeOut(duration)])
            except Exception:
                logger.warning("⚠️  视频淡出效果应用失败，使用原视频结尾")
                video_with_fade = video

            # 合成视频和logo
            final = CompositeVideoClip([video_with_fade] + logo_clips)
            final.write_videofile(output_file, **self.write_params)

            video.close()
            logo.close()
            final.close()

            logger.success(f"✅ Logo动画添加成功: {output_file}")
            return True

        except Exception as e:
            logger.error(f"❌ Logo添加失败: {str(e)}")
            import traceback
            logger.error(f"   详细错误:\n{traceback.format_exc()}")
            return False

    def concatenate_videos(
        self,
        video_files: List[str],
        output_file: str,
        transition_duration: float = 0.5,
        transitions: Optional[List[str]] = None
    ) -> bool:
        """
        拼接多个视频

        Args:
            video_files: 视频文件列表
            output_file: 输出视频文件
            transition_duration: 转场时长（秒，暂未使用）
            transitions: 对应每个片段的转场类型（cut/fade），长度与video_files相同或None

        Returns:
            bool: 是否成功
        """
        if not MOVIEPY_AVAILABLE:
            logger.error("❌ MoviePy未安装，无法拼接视频")
            return False

        try:
            clips = []
            transitions = transitions or []
            # 为每个clip应用转场（简单支持fade/交叉淡化），第一个片段无需处理
            for idx, f in enumerate(video_files):
                clip = VideoFileClip(f)
                trans = transitions[idx] if idx < len(transitions) else "cut"
                if trans and trans.lower() != "cut":
                    try:
                        clip = clip.crossfadein(transition_duration)
                    except Exception:
                        logger.warning(f"⚠️  片段 {f} 转场应用失败，回退为直接拼接")
                clips.append(clip)

            # 拼接（对有crossfadein的片段使用padding实现交叉淡入）
            has_fade = any((t and t.lower() != "cut") for t in transitions)
            padding = -transition_duration if has_fade else 0
            final = concatenate_videoclips(clips, method="compose", padding=padding)

            final.write_videofile(output_file, **self.write_params)

            for clip in clips:
                clip.close()
            final.close()

            logger.success(f"✅ 视频拼接成功: {output_file}, 共 {len(video_files)} 个片段")
            return True

        except Exception as e:
            logger.error(f"❌ 视频拼接失败: {str(e)}")
            return False

    @staticmethod
    def get_random_music(music_dir: str = "./resource/songs") -> Optional[str]:
        """
        从音乐库随机选择背景音乐

        Args:
            music_dir: 音乐目录

        Returns:
            str: 音乐文件路径，如果目录为空返回None
        """
        music_path = Path(music_dir)
        if not music_path.exists():
            logger.warning(f"⚠️  音乐目录不存在: {music_dir}")
            return None

        music_files = list(music_path.glob("*.mp3")) + list(music_path.glob("*.wav"))

        if not music_files:
            logger.warning(f"⚠️  音乐目录为空: {music_dir}")
            return None

        selected = random.choice(music_files)
        logger.info(f"🎵 随机选择背景音乐: {selected.name}")
        return str(selected)

    def _default_subtitle_style(self) -> Dict:
        """
        默认字幕样式

        Returns:
            dict: 样式配置
        """
        style = self.subtitle_style_config or {}
        font_candidates = style.get('font_candidates', [
            '/System/Library/Fonts/STHeiti Medium.ttc',
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            'C:\\Windows\\Fonts\\msyh.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
        ])

        deduped_candidates: List[str] = []
        seen: set[str] = set()
        for candidate in font_candidates + self.local_font_candidates:
            if not candidate:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            deduped_candidates.append(candidate)

        font = None
        for path in deduped_candidates:
            if os.path.exists(path):
                font = path
                logger.info(f"   使用字体: {os.path.basename(path)}")
                break

        if not font:
            fallback_font = style.get('fallback_font')
            if not fallback_font and self.local_font_candidates:
                fallback_font = self.local_font_candidates[0]
            font = fallback_font or 'Arial'
            if font == 'Arial':
                logger.warning("⚠️  未找到中文字体，使用Arial作为回退字体（可能无法显示中文）。建议安装中文字体或保持网络畅通以自动下载。")
            else:
                logger.info(f"   使用回退字体: {os.path.basename(font)}")

        return {
            'font': font,
            'fontsize': style.get('fontsize', 48),
            'color': style.get('color', 'white'),
            'stroke_color': style.get('stroke_color', 'black'),
            'stroke_width': style.get('stroke_width', 2),
            'bottom_margin': style.get('bottom_margin', 60)
        }

    @staticmethod
    def get_system_font() -> str:
        """
        获取系统中文字体路径

        Returns:
            str: 字体文件路径
        """
        resource_dir = Path(__file__).resolve().parents[2] / 'resource' / 'fonts'
        candidate_paths: List[str] = []

        # 1) 优先使用已下载的字体（Noto Sans等），保证跨平台可用
        try:
            candidate_paths.extend(font_manager.ensure_fonts())
        except Exception:
            # 字体模块异常时继续尝试系统字体
            pass

        # 2) 自动发现 resource/fonts 目录下的字体文件
        if resource_dir.exists():
            for font_file in sorted(resource_dir.glob('*.tt*')) + sorted(resource_dir.glob('*.otf')):
                candidate_paths.append(str(font_file))

        # 3) 常见操作系统自带字体
        candidate_paths.extend([
            '/System/Library/Fonts/STHeiti Medium.ttc',
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            'C:\\Windows\\Fonts\\msyh.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf',
        ])

        for path in candidate_paths:
            if path and os.path.exists(path):
                return path

        return 'Arial'  # 回退字体，确保函数总有返回值
