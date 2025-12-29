#!/usr/bin/env python3
"""
YouTube音乐下载脚本
使用yt-dlp从YouTube或其他平台下载免费音乐
"""

import os
import sys
from pathlib import Path
import yt_dlp
import json

# 配置
MUSIC_DIR = Path(__file__).parent  # ./music目录
URLS_FILE = MUSIC_DIR / "music-urls.txt"
DOWNLOAD_DIR = Path("./resource/songs")  # 下载到项目音乐目录

# 视频风格对应的推荐搜索（YouTube Audio Library）
STYLE_SEARCH_URLS = {
    "realistic_3d": [
        "https://www.youtube.com/results?search_query=cinematic+orchestral+no+copyright",
        "https://www.youtube.com/results?search_query=epic+trailer+music+free",
        "https://www.youtube.com/results?search_query=dramatic+film+music+royalty+free",
    ],
    "technology": [
        "https://www.youtube.com/results?search_query=electronic+corporate+no+copyright",
        "https://www.youtube.com/results?search_query=tech+background+music+free",
    ],
    "cyberpunk": [
        "https://www.youtube.com/results?search_query=cyberpunk+synthwave+no+copyright",
        "https://www.youtube.com/results?search_query=dark+electronic+royalty+free",
    ],
    "fantasy_magic": [
        "https://www.youtube.com/results?search_query=fantasy+orchestral+no+copyright",
        "https://www.youtube.com/results?search_query=medieval+music+free",
    ],
    "cinematic": [
        "https://www.youtube.com/results?search_query=movie+trailer+music+no+copyright",
        "https://www.youtube.com/results?search_query=orchestral+epic+free",
    ]
}

def download_audio(url, output_dir):
    """
    从URL下载音频

    Args:
        url: 视频URL
        output_dir: 输出目录
    """
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)

    # yt-dlp配置
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'ignoreerrors': True,  # 跳过错误继续下载
        'geo_bypass': True,
        'nocheckcertificate': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"\n⬇️  开始下载: {url}")
            info = ydl.extract_info(url, download=True)

            if info:
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                print(f"✅ 下载成功: {title} ({duration}秒)")
                return True
            else:
                print(f"⚠️ 无法获取视频信息")
                return False

    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return False

def read_urls_from_file(file_path):
    """从文件读取URL列表"""
    if not file_path.exists():
        return []

    urls = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if line and not line.startswith('#'):
                urls.append(line)

    return urls

def create_sample_urls_file():
    """创建示例URL文件"""
    sample_urls = """# YouTube免费音乐下载列表
# 格式：每行一个YouTube视频URL
# 注释行以#开头

# ============================================================
# 电影风/史诗音乐 (Cinematic/Epic) - 适合realistic_3d风格
# ============================================================

# Cinematic Epic Music
https://www.youtube.com/watch?v=example1

# Dramatic Orchestral
https://www.youtube.com/watch?v=example2

# ============================================================
# 使用说明
# ============================================================
# 1. 访问 YouTube Audio Library: https://studio.youtube.com
# 2. 搜索你需要的音乐风格（如：cinematic, epic, orchestral）
# 3. 找到喜欢的音乐，复制视频URL
# 4. 粘贴到此文件（删除上面的example行）
# 5. 运行: python3 music/download-yt-music.py
#
# ============================================================
# 推荐免费音乐频道
# ============================================================
# - Audio Library — Music for content creators
# - NoCopyrightSounds
# - Royalty Free Music
# - Free Music for Videos
# - Incompetech
#
# 搜索关键词建议：
# - "no copyright music"
# - "royalty free music"
# - "audio library"
# - "free music for videos"
"""

    with open(URLS_FILE, 'w', encoding='utf-8') as f:
        f.write(sample_urls)

    print(f"✅ 已创建示例URL文件: {URLS_FILE}")

def batch_download():
    """批量下载音乐"""
    print("=" * 60)
    print("🎵 YouTube音乐批量下载工具")
    print("=" * 60)

    # 检查URL文件
    if not URLS_FILE.exists():
        print(f"\n⚠️ URL列表文件不存在: {URLS_FILE}")
        print("正在创建示例文件...")
        create_sample_urls_file()
        print(f"\n📝 请编辑 {URLS_FILE} 文件，添加要下载的YouTube URL")
        print("然后重新运行此脚本")
        return

    # 读取URL列表
    urls = read_urls_from_file(URLS_FILE)

    if not urls:
        print(f"\n⚠️ URL列表为空")
        print(f"请在 {URLS_FILE} 中添加YouTube视频URL（每行一个）")
        print("\n💡 示例格式:")
        print("https://www.youtube.com/watch?v=xxxxx")
        return

    print(f"\n📋 找到 {len(urls)} 个URL")
    print(f"📁 下载目录: {DOWNLOAD_DIR.absolute()}")
    print(f"\n开始下载...\n")

    # 下载统计
    success_count = 0
    failed_count = 0

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] 处理: {url}")

        if download_audio(url, DOWNLOAD_DIR):
            success_count += 1
        else:
            failed_count += 1

    # 输出统计
    print("\n" + "=" * 60)
    print("📊 下载统计")
    print("=" * 60)
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {failed_count}")
    print(f"📁 保存位置: {DOWNLOAD_DIR.absolute()}")
    print("\n🎉 下载完成！")

def show_help():
    """显示帮助信息"""
    help_text = """
🎵 YouTube音乐下载工具使用指南

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 使用步骤：

1. 编辑URL列表文件
   vim music/music-urls.txt

2. 添加YouTube视频URL（每行一个）
   https://www.youtube.com/watch?v=xxxxx
   https://www.youtube.com/watch?v=yyyyy

3. 运行下载脚本
   python3 music/download-yt-music.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 如何找免费音乐：

方法1：YouTube Audio Library（官方，最推荐）
  - 访问: https://studio.youtube.com（需登录YouTube账号）
  - 左侧菜单 → 音频库 (Audio Library)
  - 选择你喜欢的音乐
  - 点击下载按钮旁的"..."→ 复制链接

方法2：YouTube搜索免费音乐
  - 搜索关键词: "no copyright music cinematic"
  - 筛选: 4分钟以下（适合背景音乐）
  - 复制视频URL

方法3：推荐频道
  - Audio Library — Music for content creators
  - NoCopyrightSounds
  - Royalty Free Music - No Copyright Music

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 风格推荐搜索关键词（realistic_3d - 电影风）：

YouTube搜索：
  - "cinematic orchestral no copyright"
  - "epic trailer music free"
  - "dramatic film music royalty free"
  - "heroic orchestral background"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 提示：
  - 下载的音乐将保存到 resource/songs/ 目录
  - 音乐会自动转换为MP3格式（192kbps）
  - 建议下载15-20首音乐，系统会随机选择
  - 下载的音乐时长建议30秒-3分钟

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    print(help_text)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
    else:
        batch_download()
