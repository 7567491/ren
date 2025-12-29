#!/usr/bin/env python3
"""
批量视频合成脚本 - 处理output目录下所有aka-*子目录的分镜头
使用FFmpeg Concat Demuxer (无损、快速)
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

# 获取ffmpeg路径
try:
    import imageio_ffmpeg
    FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
except Exception as e:
    print(f"❌ 无法获取ffmpeg: {e}")
    sys.exit(1)

# 输出目录
OUTPUT_BASE = Path("output")

if not OUTPUT_BASE.exists():
    print(f"❌ 输出目录不存在: {OUTPUT_BASE}")
    sys.exit(1)

def merge_videos_in_dir(work_dir):
    """合成指定目录下的视频文件"""
    print(f"\n{'='*60}")
    print(f"📂 处理目录: {work_dir.name}")
    print(f"{'='*60}")

    # 检查是否已有合成视频
    output_file = work_dir / "final_video.mp4"
    if output_file.exists():
        size_mb = output_file.stat().st_size / 1024 / 1024
        print(f"   ✓ 已存在合成视频: {output_file.name} ({size_mb:.2f} MB)")
        print(f"   ⏭️  跳过此目录")
        return True

    # 查找所有shot_*.mp4文件
    video_files = sorted(work_dir.glob("shot_*.mp4"))

    if not video_files:
        print(f"   ⚠️  未找到分镜头文件，跳过")
        return False

    print(f"   📹 找到 {len(video_files)} 个分镜头:")
    total_input_size = 0
    for vf in video_files:
        size_mb = vf.stat().st_size / 1024 / 1024
        total_input_size += size_mb
        print(f"      - {vf.name}: {size_mb:.2f} MB")

    # 创建文件列表
    filelist_path = work_dir / "filelist.txt"
    with open(filelist_path, "w") as f:
        for vf in video_files:
            f.write(f"file '{vf.name}'\n")

    # 执行FFmpeg合成
    print(f"   🔗 开始合成...")

    cmd = [
        FFMPEG_BIN,
        "-f", "concat",
        "-safe", "0",
        "-i", "filelist.txt",
        "-c", "copy",  # stream copy，不重新编码
        "-y",
        "final_video.mp4"
    ]

    try:
        start_time = datetime.now()

        result = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=60
        )

        # 清理临时文件
        if filelist_path.exists():
            filelist_path.unlink()

        if result.returncode != 0:
            print(f"   ❌ 合成失败: {result.stderr[:200]}")
            return False

        if not output_file.exists():
            print(f"   ❌ 合成失败: 输出文件未生成")
            return False

        # 统计信息
        elapsed = (datetime.now() - start_time).total_seconds()
        output_size_mb = output_file.stat().st_size / 1024 / 1024

        print(f"   ✅ 合成成功！")
        print(f"      输出: {output_file.name}")
        print(f"      输入大小: {total_input_size:.2f} MB")
        print(f"      输出大小: {output_size_mb:.2f} MB")
        print(f"      耗时: {elapsed:.1f}秒")

        return True

    except subprocess.TimeoutExpired:
        print(f"   ❌ 合成超时（>60秒）")
        return False
    except Exception as e:
        print(f"   ❌ 合成失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 批量视频合成工具")
    print(f"📂 扫描目录: {OUTPUT_BASE.absolute()}\n")

    # 查找所有aka-*子目录
    subdirs = sorted([d for d in OUTPUT_BASE.glob("aka-*") if d.is_dir()])

    if not subdirs:
        print("❌ 未找到任何aka-*子目录")
        sys.exit(1)

    print(f"✓ 找到 {len(subdirs)} 个子目录\n")

    # 统计
    success_count = 0
    skip_count = 0
    fail_count = 0

    # 逐个处理
    for subdir in subdirs:
        result = merge_videos_in_dir(subdir)

        # 检查是否已有final_video.mp4
        if (subdir / "final_video.mp4").exists():
            # 判断是本次合成还是之前就有
            if result:
                success_count += 1
            else:
                skip_count += 1
        else:
            fail_count += 1

    # 输出总结
    print(f"\n{'='*60}")
    print(f"📊 处理完成")
    print(f"{'='*60}")
    print(f"   总计: {len(subdirs)} 个目录")
    print(f"   ✅ 成功合成: {success_count} 个")
    print(f"   ⏭️  已存在跳过: {skip_count} 个")
    print(f"   ❌ 失败: {fail_count} 个")

    # 列出所有合成视频
    print(f"\n📹 所有合成视频:")
    all_finals = sorted(OUTPUT_BASE.glob("aka-*/final_video.mp4"))
    for final in all_finals:
        size_mb = final.stat().st_size / 1024 / 1024
        print(f"   - {final.parent.name}/final_video.mp4 ({size_mb:.2f} MB)")

if __name__ == "__main__":
    main()
