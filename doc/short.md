# AI故事化视频生成系统 - 功能扩展设计方案

> 基于 ShortGPT 项目分析，结合 WavespeedAI API 能力的功能补充方案
>
> 文档版本：v1.0
> 创建时间：2025-12-22

---

## 📋 目录

1. [ShortGPT 架构分析](#shortgpt-架构分析)
2. [功能对比与补充建议](#功能对比与补充建议)
3. [WavespeedAI API 能力评估](#wavespeedai-api-能力评估)
4. [实施方案](#实施方案)

---

## ShortGPT 架构分析

### 最值得参考的三大架构设计

#### 🥇 第一：状态持久化与断点续传机制

**ShortGPT 的实现：**
- 使用 **TinyDB/TinyMongo** 数据库存储所有中间状态
- 通过 `AbstractContentEngine` 实现 `_db_` 前缀的属性自动持久化
- 每个步骤完成后自动保存 `last_completed_step`

**当前项目的问题：**
- 简单的 `checkpoint.json` 只记录已完成镜头
- 无法保存故事、配置等中间状态
- 故事生成失败需要重新开始

**参考价值：** ⭐⭐⭐⭐⭐
- 可以保存故事大纲、分镜脚本、用户配置、每个镜头的状态
- 支持任意阶段断点恢复
- 失败后可以精确从失败步骤继续

---

#### 🥈 第二：步骤化引擎架构（Step-based Engine）

**ShortGPT 的实现：**
```python
self.stepDict = {
    1: self._generateScript,
    2: self._generateTempAudio,
    3: self._speedUpAudio,
    4: self._timeCaptions,
    ...
}

def makeContent(self):
    while not self.isShortDone():
        currentStep = self._db_last_completed_step + 1
        self.stepDict[currentStep]()
        self._db_last_completed_step = currentStep
```

**当前项目的问题：**
- 用 `if-elif` 判断阶段
- 步骤逻辑混在一起
- 难以扩展和维护

**参考价值：** ⭐⭐⭐⭐
- 每个步骤是独立函数，职责清晰
- 容易添加、删除、重排步骤
- 配合数据库可以精确断点续传

---

#### 🥉 第三：资源管理系统（Asset Management）

**ShortGPT 的实现：**
```python
AssetDatabase.add_local_asset("my_bg", AssetType.VIDEO, "/path/to/file.mp4")
AssetDatabase.get_asset_link("my_bg")  # 自动返回正确路径
```

**当前项目的问题：**
- 所有文件路径硬编码：`f"{WORK_DIR}/shot_{i}_image.png"`
- 没有统一的资源管理

**参考价值：** ⭐⭐⭐⭐
- 集中管理所有素材
- 支持远程 URL 和本地文件
- 自动缓存和重用资源

---

**优先级建议：** 第一点 > 第二点 > 第三点

---

## 功能对比与补充建议

### 最值得补充的三大功能

#### 🥇 第一：配音系统（AI语音旁白）

**ShortGPT 的实现：**
- 支持多种TTS引擎：ElevenLabs（高质量付费）、EdgeTTS（免费）
- 自动将故事脚本转为语音
- 支持30+语言
- **自动语音加速**：如果超过60秒，自动压缩到60秒内（Short视频限制）

**当前项目的问题：**
- ❌ **完全没有声音**
- 只有视觉画面，观众需要通过字幕理解故事
- 无法传达情绪和氛围

**参考价值：** ⭐⭐⭐⭐⭐
- **必备功能**：视频没有声音等于失去50%吸引力
- 可以用免费的 EdgeTTS 或者付费的 ElevenLabs
- 实现简单，收益巨大

**建议实现流程：**
```
阶段1.5: 语音生成
  - 读取分镜脚本的旁白文本
  - 调用TTS API（EdgeTTS免费 或 ElevenLabs高质量）
  - 生成每个镜头的旁白音频
  - 合成时叠加到视频上
```

---

#### 🥈 第二：字幕系统（自动时间轴同步）

**ShortGPT 的实现：**
- 使用 **Whisper** 将语音转为文字（带精确时间戳）
- 自动生成逐字字幕，每1-2秒切换
- 字幕与语音完美同步
- 支持自定义字幕样式（字体、颜色、位置、动画）

**当前项目的问题：**
- ❌ **没有字幕**
- 观众在静音环境无法理解内容
- 失去社交媒体流量（抖音/YouTube Shorts 70%用户静音观看）

**参考价值：** ⭐⭐⭐⭐⭐
- **社交媒体必备**：抖音/YouTube Shorts 大部分用户静音刷视频
- 提升完播率和参与度
- 增强可访问性（听障人士）

**建议实现流程：**
```
阶段2.5: 字幕生成
  - 如果有语音：用Whisper提取字幕+时间轴
  - 如果没有语音：LLM生成字幕文本 + 按镜头时长分配
  - 使用MoviePy添加字幕到视频
```

---

#### 🥉 第三：背景音乐系统

**ShortGPT 的实现：**
- 资源库管理：本地音乐文件 + 远程URL
- 自动循环：音乐时长 < 视频时长时自动循环
- **音量控制**：背景音乐音量自动降低到11%，避免盖过旁白
- 支持从YouTube提取音频作为BGM

**当前项目的问题：**
- ❌ **没有背景音乐**
- 视频缺乏情绪渲染
- 观众容易失去兴趣

**参考价值：** ⭐⭐⭐⭐
- **氛围增强**：音乐能强化故事情绪（紧张/悬疑/欢快）
- 提升专业度
- 掩盖视频生成的不自然停顿

**建议实现流程：**
```
阶段3.5: 背景音乐
  - 根据视觉风格选择匹配的BGM（科技风→电子乐，仙侠→古风音乐）
  - 使用FFmpeg自动循环和音量控制
  - 与旁白混音，保持旁白为主BGM为辅
```

---

### 其他值得参考的次要功能（按优先级排序）

#### 4️⃣ YouTube元数据自动生成（发布优化）
- LLM根据故事内容生成吸引人的标题
- 生成SEO友好的描述和标签
- 保存为 `.txt` 文件方便复制粘贴

**实现示例：**
```python
# 阶段4: YouTube元数据
title, description = generate_youtube_metadata(story_script, style)
# 保存到 final_video_metadata.txt
```

---

#### 5️⃣ 视频时长智能控制（平台适配）
- 自动检测总时长
- 超过60秒（YouTube Shorts限制）自动提示或压缩
- 支持不同平台的时长预设
  - 抖音：15s/60s
  - YouTube Shorts：60s
  - Instagram Reels：90s

---

#### 6️⃣ 水印功能（品牌标识）
- 在视频右下角添加文字/图片水印
- 防止二次搬运

---

#### 7️⃣ 搜索引擎素材获取（降低成本）
- 从 Pexels/Unsplash 免费获取背景图片/视频
- 减少AI生成成本
- 适合不需要100%原创的场景

---

## WavespeedAI API 能力评估

### ✅ WavespeedAI 可以实现的功能

#### 1️⃣ 配音系统（TTS - 文本转语音）✅

**API 端点：** `/api/v3/alibaba/qwen/tts`

**支持的功能：**
- 文本转语音（Qwen3 TTS Flash）
- 支持中文和英文
- 高质量语音合成

**API 示例：**
```json
{
    "endpoint": "/api/v3/alibaba/qwen/tts",
    "data": {
        "text": "这是要转换的文本",
        "language": "zh"
    }
}
```

**应用场景：**
- 为每个镜头的旁白文本生成语音
- 替代 ElevenLabs（付费）或 EdgeTTS（免费）
- 一站式解决方案，不需要额外集成其他TTS服务

---

#### 2️⃣ 背景音乐生成 ✅

**支持两种音乐生成 API：**

**A. Song Generation（LeVo 模型）**
- 开源文本转歌曲模型
- 支持控制：性别、音色、流派、情绪、乐器、BPM
- 可以定义歌词和歌曲结构

**B. Minimax Music 01**
- 同时合成伴奏和人声
- 生成完整歌曲
- 支持多种音乐风格

**应用场景：**
- 根据视觉风格自动生成匹配的BGM
  - 科技风 → 电子音乐
  - 仙侠风 → 古风音乐
  - 赛博朋克 → 合成器音乐
- 每个项目生成独特的背景音乐，避免版权问题

---

#### 3️⃣ 字幕系统 ❌ 不直接支持

**WavespeedAI 不提供：**
- 语音识别（STT）
- Whisper 时间轴同步
- 字幕烧录

**替代方案：**
- 使用 OpenAI Whisper（开源免费）
- 或者用 DeepSeek 生成字幕文本 + 手动时间轴分配
- 用 MoviePy 添加字幕到视频

---

#### 4️⃣ 视频编辑和合成 ❌ 不直接支持

**WavespeedAI 不提供：**
- 视频拼接
- 转场效果
- 音视频混音
- 字幕烧录

**需要使用：**
- FFmpeg（本地工具）
- MoviePy（Python库）

---

### 📊 功能对照表

| 功能 | WavespeedAI 支持 | 替代方案 | 优先级 |
|------|-----------------|---------|--------|
| **配音（TTS）** | ✅ Qwen TTS | ElevenLabs / EdgeTTS | ⭐⭐⭐⭐⭐ |
| **背景音乐生成** | ✅ LeVo / Minimax Music | 免费音乐库 | ⭐⭐⭐⭐ |
| **字幕时间轴** | ❌ | OpenAI Whisper | ⭐⭐⭐⭐⭐ |
| **字幕烧录** | ❌ | MoviePy / FFmpeg | ⭐⭐⭐⭐⭐ |
| **视频拼接** | ❌ | FFmpeg / MoviePy | ⭐⭐⭐⭐⭐ |
| **转场效果** | ❌ | MoviePy | ⭐⭐⭐ |
| **音视频混音** | ❌ | FFmpeg | ⭐⭐⭐⭐⭐ |
| **水印** | ❌ | MoviePy / FFmpeg | ⭐⭐⭐ |

---

## 实施方案

### 混合方案（推荐）

#### 完全基于 WavespeedAI 的功能：
1. ✅ **配音**：用 Qwen TTS 生成旁白
2. ✅ **背景音乐**：用 LeVo 或 Minimax Music 生成BGM

#### 需要补充的本地工具：
3. **字幕**：
   - OpenAI Whisper（开源免费）：语音 → 带时间轴的字幕
   - MoviePy：烧录字幕到视频

4. **视频合成**：
   - FFmpeg：拼接视频、混音、转场
   - MoviePy：Python 封装，更易用

---

### 最小可行方案（MVP）

```python
# ============================================================
# 阶段0: 配置与交互（现有）
# ============================================================
- 验证API密钥和环境
- 用户输入主题、选择风格、设置参数
- 确认配置并创建工作目录

# ============================================================
# 阶段1: 故事生成（现有）
# ============================================================
- DeepSeek API 生成故事大纲
- DeepSeek API 生成分镜脚本
- 输出: story_outline.json, shots_script.json

# ============================================================
# 阶段2: 图像生成（现有）
# ============================================================
- WavespeedAI 并发生成图像（2线程）
- 输出: shot_X_image.png

# ============================================================
# 阶段2.5: 配音生成（新增 - 用WavespeedAI）
# ============================================================
for shot in shots:
    # 提取旁白文本
    narration = shot['narration']

    # 调用 Qwen TTS
    audio = generate_tts_wavespeed(narration)

    # 保存音频
    save_audio(f'shot_{shot_id}_voice.mp3', audio)

# ============================================================
# 阶段2.6: 背景音乐生成（新增 - 用WavespeedAI）
# ============================================================
# 根据视觉风格和总时长生成BGM
style = config['style']  # technology/xianxia/cyberpunk...
total_duration = shot_count * shot_duration

bgm = generate_music_wavespeed(
    style=style,
    duration=total_duration,
    mood=STYLE_TEMPLATES[style]['mood']
)

save_audio('background_music.mp3', bgm)

# ============================================================
# 阶段3: 视频生成（现有）
# ============================================================
- WavespeedAI 串行生成视频（I2V模式）
- 输出: shot_X.mp4

# ============================================================
# 阶段3.5: 字幕生成（新增 - 用本地工具）
# ============================================================
# 方案A：如果有语音，用 Whisper 提取字幕
for shot_audio in shot_audios:
    subtitles = whisper_extract(shot_audio)
    save_subtitles(f'shot_{shot_id}_subs.srt', subtitles)

# 方案B：如果没语音，用 DeepSeek 生成字幕文本
for shot in shots:
    subtitle_text = shot['narration']
    # 按镜头时长分配时间轴
    subtitles = generate_subtitle_timeline(subtitle_text, shot_duration)

# ============================================================
# 阶段4: 视频合成（需要改进）
# ============================================================
# 步骤1: 拼接所有镜头视频
ffmpeg -i shot_1.mp4 -i shot_2.mp4 ... -filter_complex concat -o merged.mp4

# 步骤2: 混音：视频 + 配音 + BGM
ffmpeg -i merged.mp4 \
       -i voice.mp3 \
       -i bgm.mp3 \
       -filter_complex "[2:a]volume=0.1[a2];[1:a][a2]amix" \
       -o final_with_audio.mp4

# 步骤3: 添加字幕（MoviePy）
video = VideoFileClip('final_with_audio.mp4')
# 添加字幕 TextClip...
video.write_videofile('final_video.mp4')

# 输出: final_video.mp4
```

---

### 优先级实施计划

#### 立即实现（核心功能）：
1. ✅ **配音系统**（WavespeedAI Qwen TTS，1小时集成）
2. ✅ **字幕系统**（Whisper + MoviePy，2小时实现）
3. ✅ **背景音乐**（WavespeedAI LeVo/Minimax，1小时集成）
4. ✅ **音视频混音**（FFmpeg，30分钟实现）

#### 短期实现（发布优化）：
5. YouTube元数据生成（DeepSeek API，20分钟）
6. 视频时长检测和警告（10分钟）

#### 长期实现（可选增强）：
7. 水印功能（MoviePy，30分钟）
8. 搜索引擎素材获取（2小时）
9. 持久化数据库（TinyDB，4小时）
10. 步骤化引擎重构（8小时）

---

### 技术栈总结

**AI 服务：**
- DeepSeek API：故事生成、字幕文本
- WavespeedAI API：图像生成、视频生成、TTS配音、背景音乐

**本地工具：**
- FFmpeg：视频拼接、音视频混音、转场
- MoviePy：字幕烧录、Python封装
- OpenAI Whisper：语音识别、字幕时间轴（可选）
- TinyDB：状态持久化（可选）

---

## 参考资料

### ShortGPT 项目
- GitHub: https://github.com/RayVentura/ShortGPT
- 核心模块：`editing_framework`, `engine`, `audio`, `gpt`

### WavespeedAI API
- 官方文档: https://wavespeed.ai/docs/docs
- TTS API: Alibaba Qwen TTS Flash
- 音乐生成: LeVo Song Generation, Minimax Music 01

### 开源工具
- FFmpeg: https://ffmpeg.org/
- MoviePy: https://zulko.github.io/moviepy/
- OpenAI Whisper: https://github.com/openai/whisper
- TinyDB: https://tinydb.readthedocs.io/

---

**文档结束**
