#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音乐库预处理脚本 - 生成音频特征缓存（智能匹配）
"""

import sys
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "py" / "services"))

from audio_matcher import AudioMatcher  # noqa: E402


def main() -> None:
    logger.info("=" * 60)
    logger.info("🎵 音乐库预处理工具")
    logger.info("=" * 60)

    default_music_dir = PROJECT_ROOT / "resource" / "songs"
    default_output = PROJECT_ROOT / "resource" / "music_features.json"

    if len(sys.argv) > 1:
        music_dir = Path(sys.argv[1])
    else:
        music_dir = default_music_dir

    if len(sys.argv) > 2:
        output_cache = Path(sys.argv[2])
    else:
        output_cache = default_output

    if not music_dir.exists():
        logger.error(f"❌ 音乐目录不存在: {music_dir}")
        logger.info(f"💡 提示: 请将音乐文件放入 {music_dir}")
        return

    music_files = list(music_dir.glob('*.mp3')) + list(music_dir.glob('*.wav')) + list(music_dir.glob('*.m4a'))
    if not music_files:
        logger.error(f"❌ 未找到音乐文件: {music_dir}")
        logger.info("💡 支持格式: .mp3, .wav, .m4a")
        return

    logger.info(f"📂 音乐目录: {music_dir}")
    logger.info(f"📊 找到 {len(music_files)} 个音乐文件")
    logger.info(f"💾 输出缓存: {output_cache}")
    logger.info("")

    logger.info("🚀 开始分析音乐库（这可能需要几分钟）...")
    logger.info("")

    try:
        matcher = AudioMatcher()
        features = matcher.analyze_music_library(music_dir, str(output_cache))

        if features:
            logger.info("")
            logger.success("=" * 60)
            logger.success("✅ 预处理成功完成！")
            logger.success(f"📊 共分析 {len(features)} 首音乐")
            logger.success(f"💾 缓存文件: {output_cache}")
            logger.success("=" * 60)
            logger.info("")
            logger.info("🎉 现在可以使用智能音乐匹配功能了！")
            logger.info("   在 config.yaml 中设置: use_intelligent_music_matching: true")
        else:
            logger.error("❌ 预处理失败，未生成任何特征")

    except Exception as e:  # noqa: BLE001
        logger.error(f"❌ 预处理过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("=" * 60)
        print("音乐库预处理工具 - 使用说明")
        print("=" * 60)
        print()
        print("用法:")
        print("  python music/preprocess_music.py [music_dir] [output_cache]")
        print()
        print("参数:")
        print("  music_dir    : 音乐目录路径（默认: resource/songs）")
        print("  output_cache : 输出缓存路径（默认: resource/music_features.json）")
        print()
        print("示例:")
        print("  python music/preprocess_music.py")
        print("  python music/preprocess_music.py ./my_music ./my_cache.json")
        print("=" * 60)
    else:
        main()
