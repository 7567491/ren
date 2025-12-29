#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音乐文件检测和清理工具（已移动至 music/）
"""

import sys
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "py"))

from services.music_service import MusicService  # noqa: E402


# 配置logger输出到控制台
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
    level="INFO"
)


def main() -> None:
    print("=" * 60)
    print("🎵 音乐文件检测工具")
    print("=" * 60)

    music_dir = Path("./resource/songs")
    if not music_dir.exists():
        print(f"❌ 音乐目录不存在: {music_dir}")
        return

    music_service = MusicService(music_dir=str(music_dir))
    all_files = music_service.get_available_music(validate=False)

    print(f"\n📂 扫描目录: {music_dir}")
    print(f"📊 找到 {len(all_files)} 个音频文件\n")

    if not all_files:
        print("✅ 音乐目录为空")
        return

    valid_files = []
    invalid_files = []

    print("🔍 开始验证文件...\n")
    for i, music_file in enumerate(all_files, 1):
        print(f"[{i}/{len(all_files)}] 检查: {music_file.name}")

        is_valid = music_service.validate_audio_file(music_file)
        if is_valid:
            info = music_service.get_music_info(music_file)
            if 'error' not in info:
                valid_files.append(music_file)
                print(f"   ✅ 有效 - 时长: {info.get('duration', 0):.2f}秒")
            else:
                invalid_files.append(music_file)
                print(f"   ❌ 无效 - {info['error']}")
        else:
            invalid_files.append(music_file)

        print()

    print("=" * 60)
    print("📊 检测结果汇总")
    print("=" * 60)
    print(f"✅ 有效文件: {len(valid_files)} 个")
    print(f"❌ 无效文件: {len(invalid_files)} 个")
    print()

    if invalid_files:
        print("❌ 以下文件无效或损坏:")
        for invalid_file in invalid_files:
            print(f"   - {invalid_file.name}")
            print(f"     路径: {invalid_file}")
        print()

        response = input("是否删除这些损坏的文件？(y/n): ").strip().lower()
        if response == 'y':
            print("\n🗑️  开始删除损坏文件...")
            deleted_count = 0
            for invalid_file in invalid_files:
                try:
                    invalid_file.unlink()
                    print(f"   ✅ 已删除: {invalid_file.name}")
                    deleted_count += 1
                except Exception as e:  # noqa: BLE001
                    print(f"   ❌ 删除失败: {invalid_file.name} - {e}")
            print(f"\n✅ 成功删除 {deleted_count} 个文件")
        else:
            print("\n⚠️  已跳过删除。建议手动删除或替换损坏的文件。")
    else:
        print("✅ 所有音乐文件都有效！")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
