#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音乐服务使用示例（已移动至 music/）
"""

import sys
from pathlib import Path
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "py"))

from services.music_service import MusicService, get_background_music  # noqa: E402


def example_1_basic_usage():
    print("\n" + "=" * 60)
    print("示例1：基本用法 - 为30秒视频添加背景音乐")
    print("=" * 60)
    service = MusicService()
    music_file = service.select_music(style='technology', prefer_style=True)
    if music_file:
        music_clip = service.prepare_background_music(
            music_file=music_file,
            target_duration=30.0,
            volume=0.25
        )
        if music_clip:
            logger.success(f"✅ 背景音乐准备完成: {music_clip.duration:.2f}秒")
            music_clip.close()


def example_2_one_liner():
    print("\n" + "=" * 60)
    print("示例2：便捷函数 - 一行代码获取背景音乐")
    print("=" * 60)
    music = get_background_music(
        style='cinematic',
        target_duration=45.0,
        volume=0.3
    )
    if music:
        logger.success(f"✅ 背景音乐准备完成: {music.duration:.2f}秒")
        music.close()


def example_3_integrate_with_video_composer():
    print("\n" + "=" * 60)
    print("示例3：与VideoComposer集成")
    print("=" * 60)

    from services.video_composer import VideoComposer  # noqa: WPS433

    video_files = [
        "output/aka-test/shot_1_with_audio.mp4",
        "output/aka-test/shot_2_with_audio.mp4",
    ]

    if not all(Path(f).exists() for f in video_files):
        logger.warning("⚠️  示例视频文件不存在，跳过此示例")
        return

    music_service = MusicService()
    music_file = music_service.select_music(style='technology')
    if not music_file:
        logger.error("❌ 未找到音乐文件")
        return

    composer = VideoComposer()
    output_dir = Path("output/music_example")
    output_dir.mkdir(parents=True, exist_ok=True)

    merged_video = output_dir / "merged_video.mp4"
    success = composer.concatenate_videos(
        video_files=video_files,
        output_file=str(merged_video)
    )
    if not success:
        logger.error("❌ 视频拼接失败")
        return

    final_video = output_dir / "final_with_music.mp4"
    success = composer.add_background_music(
        video_file=str(merged_video),
        music_file=str(music_file),
        output_file=str(final_video),
        voice_volume=1.0,
        music_volume=0.25
    )
    if success:
        logger.success(f"✅ 最终视频已生成: {final_video}")


def example_4_custom_music_dir():
    print("\n" + "=" * 60)
    print("示例4：使用自定义音乐目录")
    print("=" * 60)

    custom_service = MusicService(music_dir="./resource/custom_music")
    music_list = custom_service.list_all_music()
    if music_list:
        logger.info(f"找到 {len(music_list)} 个自定义音乐")
    else:
        logger.warning("自定义音乐目录为空或不存在")


def example_5_config_based():
    print("\n" + "=" * 60)
    print("示例5：基于配置文件的使用（推荐）")
    print("=" * 60)

    config = {
        'audio': {
            'enable_background_music': True,
            'music_dir': './resource/songs',
            'music_volume': 0.25
        },
        'video': {
            'style': 'technology',
            'shot_duration': 5,
            'shot_count': 3
        }
    }

    if not config['audio']['enable_background_music']:
        logger.info("未启用背景音乐")
        return

    service = MusicService(music_dir=config['audio']['music_dir'])
    music_file = service.select_music(style=config['video']['style'], prefer_style=True)
    if not music_file:
        logger.error("❌ 未找到音乐文件")
        return

    music_clip = service.prepare_background_music(
        music_file=music_file,
        target_duration=config['video']['shot_duration'] * config['video']['shot_count'],
        volume=config['audio']['music_volume']
    )
    if music_clip:
        logger.success(f"✅ 背景音乐准备完成: {music_clip.duration:.2f}秒")
        music_clip.close()


if __name__ == "__main__":
    example_1_basic_usage()
    example_2_one_liner()
    example_3_integrate_with_video_composer()
    example_4_custom_music_dir()
    example_5_config_based()
