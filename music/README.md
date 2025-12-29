# 🎵 音乐工具集（全部集中在 `music/` 目录）

## 📁 文件说明

```
music/
├── 1-download-yt-music.py     # YouTube/yt-dlp 下载（使用 music-urls.txt）
├── 2-download-incompetech.py  # Incompetech 免费曲库一键下载（并发）
├── 3-download-freesound.py    # Freesound API 下载（支持快节奏模式）
├── 4-preprocess_music.py      # 生成 music_features.json（智能匹配缓存）
├── 5-check-music.py           # 扫描并清理损坏的音频文件
├── 6-extract-music-climax.py  # 能量分析截取高潮片段
├── 7-example_music_usage.py   # MusicService 使用示例
├── music-urls.txt             # YouTube URL 列表模板
└── README.md                  # 本文件
```

所有脚本默认输出到 `resource/songs/`。

## 🚀 常用脚本

### 1）YouTube 下载（高质量，需手动准备 URL）
```bash
vim music/music-urls.txt   # 填写视频 URL（每行一个）
python3 music/1-download-yt-music.py
```

### 2）Incompetech 批量直链下载（零成本，含多种风格）
```bash
# 默认下载15首（可用 --count 指定，--filter 按标题过滤）
python3 music/2-download-incompetech.py --count 20
```

### 3）Freesound API 下载（需配置 FREESOUND_API_KEY）
```bash
export FREESOUND_API_KEY=your_key
# 普通模式，按风格关键词搜索
python3 music/3-download-freesound.py --style technology --count 15

# 快节奏/史诗模式，带 BPM 过滤
python3 music/3-download-freesound.py --mode epic --bpm-min 120 --count 20
```

### 4）预处理与质量控制
```bash
# 生成音乐特征缓存，用于智能匹配
python3 music/4-preprocess_music.py

# 校验文件是否损坏、时长过短
python3 music/5-check-music.py

# 提取高潮片段（默认从 resource/songs/epic 输出到 resource/songs）
python3 music/6-extract-music-climax.py
```

## 🎨 搜索关键词参考（YouTube/Freesound）

| 风格 | 推荐关键词 |
|------|------------|
| realistic_3d/cinematic | cinematic orchestral, epic trailer |
| technology | electronic corporate, tech background |
| cyberpunk | cyberpunk synthwave, dark electronic |
| fantasy_magic | fantasy orchestral, medieval music |
| anime | anime background music |
| xianxia | chinese traditional music |
| space_scifi | space ambient music |

## 🔧 依赖与检查

- Python: `requests`, `yt-dlp`, `moviepy`, `librosa`, `dotenv`（见根目录 `requirements.txt`）
- 系统依赖：`ffmpeg`（用于音频转换与截取）
- 快速自检：
  ```bash
  yt-dlp --version
  ffmpeg -version
  ```

## 💡 提示
- 需要付费/限流接口时，优先用低分辨率、少量镜头测试。
- 下载后可按风格归类，或结合 `music/preprocess_music.py` 生成缓存，提升智能选曲效果。
- Incompetech 曲目为 CC BY 3.0，使用时注明：`Music by Kevin MacLeod (incompetech.com)`。
