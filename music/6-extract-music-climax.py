#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能音乐高潮提取工具（已移动至 music/）
"""

import sys
import numpy as np
from pathlib import Path
from moviepy import AudioFileClip
from loguru import logger

# 配置logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
    level="INFO"
)


def calculate_audio_energy(audio_clip, window_size=1.0):
    """计算音频能量曲线（使用滑动窗口）"""
    duration = audio_clip.duration
    fps = audio_clip.fps

    audio_data = audio_clip.to_soundarray(fps=fps)
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)

    window_samples = int(window_size * fps)
    hop_samples = window_samples // 4

    energy_values = []
    time_points = []

    for start in range(0, len(audio_data) - window_samples, hop_samples):
        window_data = audio_data[start:start + window_samples]
        rms_energy = np.sqrt(np.mean(window_data ** 2))
        energy_values.append(rms_energy)
        time_points.append((start + window_samples / 2) / fps)

    return time_points, energy_values


def find_climax_segment(audio_clip, target_duration=60, min_duration=30):
    """查找音频高潮片段"""
    duration = audio_clip.duration

    if duration <= min_duration:
        logger.info(f"   音乐时长 {duration:.1f}秒 ≤ {min_duration}秒，保留全部")
        return (0, duration)

    if duration <= target_duration * 1.2:
        logger.info(f"   音乐时长 {duration:.1f}秒 接近目标，保留全部")
        return (0, duration)

    logger.info("   分析能量曲线...")
    time_points, energy_values = calculate_audio_energy(audio_clip, window_size=2.0)

    if len(energy_values) == 0:
        logger.warning("   ⚠️ 能量分析失败，使用中段提取")
        start = (duration - target_duration) * 0.6
        return (start, start + target_duration)

    energy_values = np.array(energy_values)
    time_points = np.array(time_points)

    avg_window_time = np.mean(np.diff(time_points)) if len(time_points) > 1 else 0.25
    target_windows = int(target_duration / avg_window_time)

    if target_windows >= len(energy_values):
        logger.info("   窗口不足，保留全部")
        return (0, duration)

    max_energy_sum = 0
    best_start_idx = 0
    for i in range(len(energy_values) - target_windows + 1):
        window_energy_sum = np.sum(energy_values[i:i + target_windows])
        if window_energy_sum > max_energy_sum:
            max_energy_sum = window_energy_sum
            best_start_idx = i

    start_time = time_points[best_start_idx]
    end_idx = min(best_start_idx + target_windows, len(time_points) - 1)
    end_time = time_points[end_idx]

    actual_duration = end_time - start_time
    if actual_duration < target_duration * 0.8:
        end_time = min(start_time + target_duration, duration)

    if end_time > duration:
        end_time = duration
        start_time = max(0, end_time - target_duration)

    logger.info(f"   ✅ 高潮位置: {start_time:.1f}s - {end_time:.1f}s ({end_time-start_time:.1f}s)")
    return (start_time, end_time)


def extract_climax(input_file: Path, output_file: Path, target_duration=60):
    """提取单个音乐文件的高潮部分"""
    try:
        audio = AudioFileClip(str(input_file))
        original_duration = audio.duration

        logger.info(f"📄 {input_file.name} (时长: {original_duration:.1f}秒)")

        segment = find_climax_segment(audio, target_duration=target_duration)
        if segment is None:
            logger.warning("   ⚠️ 无法提取高潮，跳过")
            audio.close()
            return False

        start_time, end_time = segment

        if start_time == 0 and end_time == original_duration:
            logger.info("   ⏭️  无需提取，直接使用原文件")
            import shutil
            shutil.copy2(input_file, output_file)
            audio.close()
            return True

        climax_audio = audio.subclipped(start_time, end_time)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        climax_audio.write_audiofile(
            str(output_file),
            codec='libmp3lame',
            bitrate='192k',
            logger=None
        )

        logger.success(f"   ✅ 已保存: {output_file.name} ({end_time-start_time:.1f}秒)")
        climax_audio.close()
        audio.close()
        return True

    except Exception as e:  # noqa: BLE001
        logger.error(f"   ❌ 处理失败: {str(e)}")
        return False


def main() -> None:
    print("=" * 70)
    print("🎵 智能音乐高潮提取工具")
    print("=" * 70)

    music_dir = Path("./resource/songs/epic")
    output_dir = Path("./resource/songs")

    if not music_dir.exists():
        logger.error(f"❌ 音乐目录不存在: {music_dir}")
        return

    music_files = []
    for ext in ['.mp3', '.wav', '.m4a']:
        music_files.extend(music_dir.glob(f'*{ext}'))

    music_files = [f for f in music_files if '_climax' not in f.stem]
    if not music_files:
        logger.error(f"❌ 未找到音乐文件: {music_dir}")
        return

    print(f"\n📂 输入目录: {music_dir}")
    print(f"📁 输出目录: {output_dir}")
    print(f"📊 找到 {len(music_files)} 个音乐文件\n")

    print("请选择目标时长:")
    print("  1. 30秒 (适合短广告)")
    print("  2. 45秒 (平衡选择)")
    print("  3. 60秒 (标准广告)")
    print("  4. 自定义")

    try:
        choice = input("\n请输入选项 [1-4] (默认: 3): ").strip() or "3"
        if choice == "1":
            target_duration = 30
        elif choice == "2":
            target_duration = 45
        elif choice == "3":
            target_duration = 60
        elif choice == "4":
            custom = input("请输入自定义时长(秒): ").strip()
            target_duration = int(custom)
        else:
            target_duration = 60
    except (ValueError, KeyboardInterrupt):
        print("\n使用默认时长: 60秒")
        target_duration = 60

    print(f"\n🎯 目标时长: {target_duration}秒")
    print(f"\n{'='*70}")
    print("开始处理...\n")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, music_file in enumerate(music_files, 1):
        print(f"[{i}/{len(music_files)}]")
        output_file = output_dir / music_file.name

        if output_file.exists():
            logger.info(f"📄 {music_file.name}")
            logger.info("   ⏭️  已存在，跳过")
            skip_count += 1
            print()
            continue

        success = extract_climax(music_file, output_file, target_duration)
        if success:
            success_count += 1
        else:
            fail_count += 1
        print()

    print("=" * 70)
    print("📊 处理完成")
    print("=" * 70)
    print(f"✅ 成功: {success_count} 个")
    print(f"⏭️  跳过: {skip_count} 个")
    print(f"❌ 失败: {fail_count} 个")
    print(f"\n📁 输出目录: {output_dir.absolute()}")
    print("=" * 70)

    if success_count > 0 or skip_count > 0:
        print("\n💡 下一步:")
        print("   音乐已准备好，可以直接使用！")
        print("   在 config.yaml 中确认 music_dir: './resource/songs'")
        print("   或将 ./resource/songs/epic/ 的原始文件备份后删除")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
    except Exception as e:  # noqa: BLE001
        logger.error(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
