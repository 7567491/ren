# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 基本原则

- 用中文对话
- 用最简单的方法完成任务
- 不要创建新文件，除非明确要求
- 不要生成新的md文档，除非我告诉你需要
所有新增md文件放在./doc目录
所有测试相关文件放在./test目录

## 项目定位

**本项目是前后端分离的AI视频生成系统**

- **主程序**: `html/` (前端) + `ad-back.py` (后端API)
- **参考脚本**: `ad-aka.py` (独立脚本，仅供参考，不要变更)

## 项目概述

**AI故事化视频生成系统** - 基于 DeepSeek 和 WavespeedAI 的智能视频制作工具

- **核心功能**: 从主题到成片的全自动故事化视频生成
- **技术架构**: DeepSeek(故事生成) → Edge TTS(配音) → WavespeedAI(视频生成) → MoviePy(合成)
- **技术栈**: Python 3.10+, DeepSeek API, WavespeedAI API, Edge TTS, MoviePy

## 常用命令

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动后端API服务（主程序）
python3 ad-back.py

# 前端访问
# 打开浏览器访问 html/index.html 或部署的前端地址

# 测试网络连接
python3 py/test_network.py

# 参考脚本（不推荐直接使用）
# python3 ad-aka.py
```

## 配置层级
- `.env`：存放 API 密钥，不提交。
- `config.yaml`：全局默认与限流/路径/模型配置。
- `user.yaml`：运行时用户参数覆盖（主题、镜头、分辨率、角色/Logo、并发等），缺省回落 `config.yaml`。

## 项目结构

```
wavespeed/
├── 【主程序 - 前后端分离架构】
│   ├── html/             # 前端页面（主程序前端）
│   └── ad-back.py        # 后端API服务（主程序后端）
│
├── 【参考脚本 - 不要变更】
│   └── ad-aka.py         # 独立脚本，仅供参考
│
├── py/                   # 后端核心模块
│   ├── api/              # Workflow 对外 API
│   ├── function/         # 配置/上下文/steps/pipeline 等模块
│   ├── services/         # 语音/字幕/合成/音乐等原有服务
│   ├── py1/              # 独立工具脚本
│   ├── test_network.py   # 网络测试
│   └── test-*.py         # 其他测试脚本
│
├── .test/                # 内部测试样例
├── output/               # 输出目录(自动创建)
├── resource/             # 资源目录（含 songs/）
├── test/                 # 测试脚本目录
├── doc/                  # 文档目录
├── venv/                 # Python虚拟环境
├── .env                  # API密钥配置
├── config.yaml           # 系统配置文件
├── requirements.txt      # Python依赖
└── README.md             # 项目说明
```

### 音乐脚本（统一放在 `music/`）
- `1-download-yt-music.py`：按 `music-urls.txt` 下载 YouTube 音乐
- `2-download-incompetech.py`：Incompetech 免费曲库并发直链（`--count`/`--filter`）
- `3-download-freesound.py`：Freesound API 下载，支持 `--mode epic` + `--bpm-min`
- `4-preprocess_music.py`：生成 `resource/music_features.json`（智能选曲缓存）
- `5-check-music.py`：校验/清理 `resource/songs/` 中损坏或过短文件
- `6-extract-music-climax.py`：按能量截取高潮片段到 `resource/songs/`
- `7-example_music_usage.py`：背景音乐服务示例

## 核心架构

### 视频生成流程(5阶段) - **已升级支持配音和字幕！**

**阶段0: 配置与交互**
- 验证API密钥和环境
- 用户输入主题、选择风格、设置参数
- 确认配置并创建工作目录

**阶段1: 故事生成(DeepSeek API)**
- 生成故事大纲(起承转合结构)
- 生成连贯的分镜脚本（画面描述 + 旁白文案）
- 输出: `story_outline.json`, `shots_script.json`

**阶段2: 配音和字幕生成(Edge TTS) ⭐新增**
- 2a: 为每个镜头的旁白生成配音（Edge TTS，免费）
- 2b: 自动生成精确时间戳的SRT字幕（SubMaker）
- 输出: `shot_X_audio.mp3`, `shot_X_subtitle.srt`

**阶段3: 视频生成(WavespeedAI API)**
- 3a: 并发生成图像(2线程,Seedream v4)
- 3b: 串行生成视频(WAN 2.5 I2V模式)
- 支持断点续传
- 输出: `shot_X_image.png`, `shot_X.mp4`(静音视频)

**阶段4: 音视频合成(MoviePy) ⭐增强**
- 4a: 为每个镜头添加配音音频
- 4b: 渲染字幕到视频（可自定义样式）
- 4c: 混合背景音乐（可选）
- 4d: 拼接所有镜头
- 输出: `final_video.mp4`(完整带音字幕视频)

### 关键设计模式

**错误处理与重试**
- 自定义异常体系: `APIError`(可重试) vs `TaskFailedError`(不可重试)
- 指数退避策略: 3次重试,间隔递增(5s→10s→15s)
- 完整日志记录到文件和控制台

**并发优化**
- 图像生成阶段: 使用 `ThreadPoolExecutor` 2线程并发
- 视频生成阶段: 串行处理(避免API限流)

**智能断点续传**
- **自动检测** - 启动时自动查找最近任务,判断是否完整
- **完成度展示** - 显示故事/图像/视频各阶段进度
- **用户确认** - 询问是否继续未完成任务
- **智能跳过** - 已完成的阶段自动跳过:
  - 已有 `shots_script.json` → 跳过故事生成
  - 已有 `shot_X_image.png` → 跳过图像生成
  - 已有 `shot_X.mp4` → 跳过视频生成
- **灵活控制** - 支持 `--no-auto-resume` 强制新建

### 风格模板系统

10种预定义视觉风格,每种包含:
- `visual_style`: 视觉描述
- `color_palette`: 色彩方案
- `lighting`: 光照效果
- `camera_movement`: 镜头运动
- `mood`: 情绪氛围

风格列表: 科技/仙侠/赛博朋克/动画/3D/水墨/蒸汽朋克/太空/魔法/电影

## 配置说明

### 环境变量(.env)

```env
DeepSeek_API_KEY=your_deepseek_key
# Wavespeed_API_KEY=不需要后端配置，通过前端网页输入并记住
```

**注意**: Wavespeed API密钥**不需要在后端配置**，而是通过前端网页界面输入，浏览器会自动记住（localStorage），提供更好的用户体验和安全性。

### 用户可配置参数

- **主题**: 任意文本描述
- **视觉风格**: 10选1(科技/仙侠/赛博朋克/动画/3D/水墨/蒸汽朋克/太空/魔法/电影)
- **镜头数**: 1-10个
- **时长**: 每镜头3-5秒
- **分辨率**: 480p/720p/1080p

### 输出文件结构

```
output/aka-{mmddhhmm}/
├── story_outline.json    # 故事大纲(起承转合)
├── shots_script.json     # 分镜脚本(连贯描述)
├── checkpoint.json       # 断点续传检查点
├── shot_1_image.png      # 镜头1关键帧
├── shot_1.mp4           # 镜头1视频
├── shot_2.mp4           # 镜头2视频
├── shot_N.mp4           # 镜头N视频
├── final_video.mp4      # 最终合成视频
└── log.txt              # 完整运行日志
```

## API集成

### DeepSeek API
- **用途**: 故事大纲和分镜脚本生成
- **端点**: `https://api.deepseek.com/v1/chat/completions`
- **成本**: 约$0.002-0.004/次

### WavespeedAI API
- **用途**: 文本→图像, 图像→视频
- **模型**: WAN 2.5 (文本生成图像$0.15, I2V$0.15)
- **端点**: `https://api.wavespeed.ai/v1/generations`
- **轮询**: 每5秒检查任务状态

## 成本估算

**I2V模式(推荐)**:
- 3镜头720p: ~$0.90
- 5镜头720p: ~$1.50
- 10镜头1080p: ~$5.00

## 开发注意事项

1. **前后端分离架构**:
   - 前端: `html/` 目录中的Web界面
   - 后端: `ad-back.py` 提供RESTful API服务
   - 参考脚本: `ad-aka.py` 仅供参考，不要变更

2. **编码处理**: 脚本已设置UTF-8编码处理,避免中文输入中断

3. **日志系统**: 双重记录(控制台+文件),带时间戳

4. **网络要求**: 需稳定国际网络连接

5. **成本控制**: 建议先用480p+3镜头测试($0.60)

6. **API限流**: 视频生成串行处理,避免并发限流

7. **智能断点续传**: 通过API支持任务恢复和进度查询
