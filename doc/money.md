# WavespeedAI API 功能扩展设计方案

> 基于 WavespeedAI API 能力分析，实现完整的AI视频生成系统

**文档版本**: v1.0
**创建时间**: 2025-12-22
**目标**: 补充语音合成、字幕生成、背景音乐三大核心功能

---

## 📋 目录

- [功能对比分析](#功能对比分析)
- [WavespeedAI 支持的功能](#wavespeedai-支持的功能)
- [实现方案设计](#实现方案设计)
- [技术架构](#技术架构)
- [开发路线图](#开发路线图)

---

## 功能对比分析

### 当前 wavespeed 项目 vs MoneyPrinterTurbo

| 功能模块 | wavespeed (当前) | MoneyPrinterTurbo | 重要程度 |
|---------|-----------------|-------------------|---------|
| **故事生成** | ✅ DeepSeek | ✅ 多种LLM | ⭐⭐⭐⭐ |
| **视频生成** | ✅ WavespeedAI | ✅ Pexels素材 | ⭐⭐⭐⭐⭐ |
| **语音合成** | ❌ 无 | ✅ Edge TTS/Azure TTS | ⭐⭐⭐⭐⭐ |
| **字幕生成** | ❌ 无 | ✅ Edge/Whisper | ⭐⭐⭐⭐⭐ |
| **背景音乐** | ❌ 无 | ✅ 本地音乐库 | ⭐⭐⭐⭐ |
| **断点续传** | ✅ 智能自动 | ❌ 无 | ⭐⭐⭐⭐ |
| **字幕样式** | ❌ 无 | ✅ 样式自定义 | ⭐⭐⭐ |

### 优先级排序

**最重要的三个功能**（缺失且必需）:

1. **语音合成（配音）** - 完整视频必须有声音 ⭐⭐⭐⭐⭐
2. **字幕生成** - 短视频必备，提升可访问性 ⭐⭐⭐⭐⭐
3. **背景音乐** - 增强氛围，提升专业度 ⭐⭐⭐⭐

---

## WavespeedAI 支持的功能

### ✅ 1. 语音合成（TTS）

**可用模型**:

#### Qwen TTS（推荐）
```python
{
    "provider": "Alibaba",
    "model": "Qwen TTS",
    "features": [
        "文本转语音",
        "自然语音生成",
        "多种音色"
    ],
    "rating": "⭐⭐⭐⭐"
}
```

#### 通用语音合成
```python
{
    "providers": "多提供商",
    "features": [
        "自然语音生成",
        "多语言支持"
    ],
    "rating": "⭐⭐⭐⭐"
}
```

#### 声音克隆
```python
{
    "features": [
        "克隆特定音色",
        "个性化配音"
    ],
    "rating": "⭐⭐⭐⭐"
}
```

**优势**:
- ✅ 统一平台，无需额外配置
- ✅ API 调用简单
- ✅ 与视频生成在同一服务

---

### ✅ 2. 字幕生成（语音识别）

**可用模型**:

#### OpenAI Whisper（推荐）
```python
{
    "provider": "OpenAI",
    "model": "Whisper",
    "features": [
        "多语言语音转文字",
        "高精度识别",
        "自动时间戳"
    ],
    "rating": "⭐⭐⭐⭐⭐"
}
```

**实现方式**:

**方案A**: 音频 → 字幕
1. 先生成配音（TTS）
2. 用 Whisper 转换为带时间戳的字幕
3. 生成 SRT 格式文件

**方案B**: 文案 → 字幕
1. 直接基于文案分段
2. 计算每句时长
3. 生成 SRT 文件

---

### ✅ 3. 背景音乐

**可用功能**:

#### AI音乐生成
```python
{
    "providers": "多提供商",
    "features": [
        "AI作曲",
        "风格可控",
        "自动生成"
    ],
    "rating": "⭐⭐⭐⭐"
}
```

**对比**:
- **MoneyPrinterTurbo**: 本地音乐库（resource/songs/）
- **WavespeedAI**: AI自动生成，无需本地存储

---

### 🎬 重大发现：原生音视频同步！

某些视频模型**已经原生支持音视频同步**，无需额外处理：

#### WAN 2.6 ⭐⭐⭐⭐⭐
```python
{
    "price": "~$0.50",
    "resolution": "1080p",
    "features": [
        "统一多模态",
        "原生同步音视频",
        "电影级质量"
    ],
    "rating": "强烈推荐"
}
```

#### WAN 2.5 ⭐⭐⭐⭐⭐
```python
{
    "price": "$0.05-0.50",
    "resolution": "480p-1080p",
    "features": [
        "一步同步音视频",
        "比Veo3更快更便宜",
        "性价比极高"
    ],
    "rating": "强烈推荐"
}
```

---

## 实现方案设计

### 方案A: 极简方案（推荐）

**适用场景**: 快速实现，质量优先

```python
# 技术栈
1. DeepSeek → 生成故事文案
2. WAN 2.6 T2V → 生成带音频的视频（一步到位）
3. (可选) Whisper → 生成字幕

# 工作流程
story_text = deepseek_api.generate_story(topic)
for shot in shots:
    # WAN 2.6 直接生成带音频的视频
    video_with_audio = wavespeed_api.generate_video_t2v(
        prompt=shot.description,
        model="wan-2.6-t2v",
        audio=True  # 原生音频支持
    )
```

**成本分析**:
```
单镜头成本: $0.50
3镜头总成本: $1.50
5镜头总成本: $2.50
```

**优势**:
- ✅ **零配置** - 无需额外TTS设置
- ✅ **一步完成** - 文本直接生成带音频视频
- ✅ **质量最高** - 1080p + 原生音频同步
- ✅ **开发最快** - 修改现有代码即可

**劣势**:
- ⚠️ 音频内容不可控（AI自动生成）
- ⚠️ 无法自定义配音声音
- ⚠️ 成本略高（$0.50/镜头）

---

### 方案B: 完全定制方案

**适用场景**: 精细控制，专业制作

```python
# 技术栈
1. DeepSeek → 生成故事文案
2. Qwen TTS → 生成配音音频
3. WavespeedAI → 生成图像
4. WAN 2.5 I2V → 图像生成视频（静音）
5. OpenAI Whisper → 生成字幕（带时间戳）
6. AI音乐生成 → 背景音乐
7. MoviePy → 合成音频+字幕+视频

# 工作流程
# 1. 生成故事
story = deepseek_api.generate_story(topic)

# 2. 生成配音
for shot in shots:
    audio = wavespeed_api.qwen_tts(
        text=shot.narration,
        voice="zh-CN-XiaoxiaoNeural"
    )
    shot.audio_file = audio

# 3. 生成字幕
    subtitle = wavespeed_api.whisper(
        audio_file=audio,
        language="zh"
    )
    shot.subtitle_file = subtitle

# 4. 生成图像
    image = wavespeed_api.generate_image(
        prompt=shot.description,
        model="seedream-v4"
    )

# 5. 生成视频
    video = wavespeed_api.generate_video_i2v(
        image=image,
        model="wan-2.5-i2v"
    )

# 6. 生成背景音乐
background_music = wavespeed_api.generate_music(
    style=config.music_style,
    duration=total_duration
)

# 7. 合成最终视频
final_video = compose_video(
    video_clips=shots,
    audios=[shot.audio for shot in shots],
    subtitles=[shot.subtitle for shot in shots],
    background_music=background_music,
    volume_mix={
        "voice": 1.0,
        "music": 0.3
    }
)
```

**成本分析**:
```
单镜头成本:
- 图像: $0.027 (Seedream v4)
- 视频: $0.30 (WAN 2.5 I2V)
- 配音: ~$0.01 (Qwen TTS估算)
- 字幕: ~$0.01 (Whisper估算)
- 背景音乐: ~$0.05 (整个视频共享)
= 约 $0.37/镜头

3镜头总成本: ~$1.16
5镜头总成本: ~$1.90
```

**优势**:
- ✅ **完全控制** - 每个环节可自定义
- ✅ **质量可控** - 可选择最佳模型组合
- ✅ **成本更低** - 比方案A便宜约25%
- ✅ **功能完整** - 配音+字幕+背景音乐

**劣势**:
- ⚠️ 开发复杂度高
- ⚠️ 需要视频合成能力
- ⚠️ 调试时间长

---

### 方案C: 混合方案（平衡）

**适用场景**: 平衡开发成本和功能

```python
# 技术栈
1. DeepSeek → 生成故事文案
2. Qwen TTS → 生成配音
3. WAN 2.5 I2V → 生成视频
4. 基于文案生成简单字幕（无需Whisper）
5. 使用本地音乐库（无需AI生成）

# 特点
- 配音：可控（Qwen TTS）
- 字幕：基于文案自动生成
- 背景音乐：本地音乐库
- 成本：中等（~$0.35/镜头）
```

---

## 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    用户输入                               │
│              (主题 + 风格 + 参数)                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│            阶段1: 故事生成 (DeepSeek)                     │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 1. 生成故事大纲（起承转合）                        │   │
│  │ 2. 生成分镜脚本（连贯描述）                        │   │
│  └──────────────────────────────────────────────────┘   │
│           输出: shots_script.json                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         阶段2a: 配音生成 (Qwen TTS) [新增]               │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 1. 提取每个镜头的旁白文案                          │   │
│  │ 2. 调用 Qwen TTS 生成音频                         │   │
│  │ 3. 计算音频时长                                   │   │
│  └──────────────────────────────────────────────────┘   │
│           输出: shot_X_audio.mp3                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│        阶段2b: 字幕生成 (Whisper/文案) [新增]            │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 方案1: Whisper音频识别（精确时间戳）               │   │
│  │ 方案2: 基于文案+音频时长计算（简单快速）           │   │
│  └──────────────────────────────────────────────────┘   │
│           输出: shot_X_subtitle.srt                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│          阶段2c: 图像生成 (WavespeedAI)                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 1. 并发生成关键帧图像                             │   │
│  │ 2. 智能跳过已存在图像                             │   │
│  └──────────────────────────────────────────────────┘   │
│           输出: shot_X_image.png                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│        阶段2d: 视频生成 (WAN 2.5 I2V)                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 1. 图像→视频（I2V模式）                           │   │
│  │ 2. 智能跳过已存在视频                             │   │
│  │ 3. 断点续传支持                                   │   │
│  └──────────────────────────────────────────────────┘   │
│           输出: shot_X.mp4 (静音)                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│      阶段3: 音视频合成 (MoviePy) [新增]                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 1. 视频 + 配音音频合成                            │   │
│  │ 2. 添加字幕轨道（样式可自定义）                    │   │
│  │ 3. 混合背景音乐（音量可调）                        │   │
│  │ 4. 拼接所有镜头                                   │   │
│  └──────────────────────────────────────────────────┘   │
│           输出: final_video.mp4 (完整版)                 │
└─────────────────────────────────────────────────────────┘
```

### 新增模块设计

#### 1. 语音合成模块 (`voice.py`)

```python
class VoiceService:
    """语音合成服务"""

    def __init__(self, api_key):
        self.api_key = api_key
        self.tts_engine = "qwen-tts"  # 或 "voice-clone"

    def generate_audio(self, text, voice="default", speed=1.0):
        """
        生成语音音频

        Args:
            text: 文本内容
            voice: 音色选择
            speed: 语速调节

        Returns:
            audio_file: 音频文件路径
            duration: 音频时长（秒）
        """
        pass

    def get_available_voices(self):
        """获取可用音色列表"""
        pass
```

#### 2. 字幕生成模块 (`subtitle.py`)

```python
class SubtitleService:
    """字幕生成服务"""

    def __init__(self, api_key):
        self.api_key = api_key

    def generate_from_audio(self, audio_file, language="zh"):
        """
        从音频生成字幕（使用Whisper）

        Args:
            audio_file: 音频文件路径
            language: 语言代码

        Returns:
            subtitle_data: [{"text": "...", "start": 0.0, "end": 2.5}, ...]
        """
        pass

    def generate_from_text(self, text, duration):
        """
        从文本生成简单字幕

        Args:
            text: 文本内容
            duration: 总时长

        Returns:
            subtitle_data: 字幕数据
        """
        pass

    def export_srt(self, subtitle_data, output_file):
        """导出SRT格式字幕"""
        pass
```

#### 3. 音乐生成模块 (`music.py`)

```python
class MusicService:
    """背景音乐服务"""

    def __init__(self, api_key):
        self.api_key = api_key

    def generate_music(self, style, duration, mood="upbeat"):
        """
        AI生成背景音乐

        Args:
            style: 音乐风格
            duration: 时长（秒）
            mood: 情绪

        Returns:
            music_file: 音乐文件路径
        """
        pass

    def get_local_music(self, style="random"):
        """从本地音乐库获取（备用方案）"""
        pass
```

#### 4. 视频合成模块 (`composer.py`)

```python
class VideoComposer:
    """视频合成器"""

    def __init__(self):
        self.temp_dir = Path("./temp")

    def compose_final_video(
        self,
        video_clips,      # 视频片段列表
        audio_files,      # 配音文件列表
        subtitle_files,   # 字幕文件列表
        background_music, # 背景音乐
        config            # 合成配置
    ):
        """
        合成最终视频

        合成步骤:
        1. 加载所有视频片段
        2. 为每个片段添加对应配音
        3. 添加字幕轨道（样式自定义）
        4. 混合背景音乐（音量控制）
        5. 拼接所有片段
        6. 导出最终视频

        Returns:
            final_video_path: 最终视频路径
        """
        pass

    def add_subtitles(self, video, subtitle_file, style):
        """添加字幕（支持样式自定义）"""
        pass

    def mix_audio(self, voice_audio, background_music, voice_volume=1.0, music_volume=0.3):
        """混合音频（音量可控）"""
        pass
```

---

## 开发路线图

### 阶段1: 快速验证（1-2天）

**目标**: 验证 WavespeedAI TTS/Whisper API 可用性

**任务**:
- [ ] 调研 WavespeedAI TTS API 文档
- [ ] 编写 TTS 测试脚本
- [ ] 编写 Whisper 测试脚本
- [ ] 验证音频质量
- [ ] 评估成本

**交付物**:
- `test/test-tts.py` - TTS测试脚本
- `test/test-whisper.py` - Whisper测试脚本
- `doc/api-test-report.md` - 测试报告

---

### 阶段2: 核心功能开发（3-5天）

**目标**: 实现语音合成和字幕生成

**任务**:
- [ ] 实现 `VoiceService` 类
- [ ] 实现 `SubtitleService` 类
- [ ] 集成到主流程 `ad-aka.py`
- [ ] 添加配置参数（音色、语速等）
- [ ] 更新断点续传逻辑

**交付物**:
- `py/services/voice.py` - 语音服务
- `py/services/subtitle.py` - 字幕服务
- 更新 `py/ad-aka.py` - 主流程集成

---

### 阶段3: 视频合成（2-3天）

**目标**: 实现音视频字幕合成

**任务**:
- [ ] 安装 MoviePy 依赖
- [ ] 实现 `VideoComposer` 类
- [ ] 实现字幕样式自定义
- [ ] 实现音频混合功能
- [ ] 测试完整流程

**交付物**:
- `py/services/composer.py` - 视频合成器
- `requirements.txt` - 更新依赖
- 完整的带音频+字幕视频

---

### 阶段4: 背景音乐（1-2天）

**目标**: 添加背景音乐支持

**任务**:
- [ ] 实现 `MusicService` 类
- [ ] 测试 AI 音乐生成
- [ ] 实现本地音乐库备用方案
- [ ] 添加音量控制配置

**交付物**:
- `py/services/music.py` - 音乐服务
- `resource/songs/` - 本地音乐库（备用）

---

### 阶段5: 优化与测试（2-3天）

**目标**: 完善细节，测试稳定性

**任务**:
- [ ] 字幕样式优化（字体、位置、颜色、描边）
- [ ] 音量平衡调优
- [ ] 成本优化
- [ ] 性能优化（并发处理）
- [ ] 完整流程测试
- [ ] 文档更新

**交付物**:
- 优化的完整系统
- 更新的 README.md
- 更新的 CLAUDE.md
- 测试报告

---

## 技术依赖

### 新增 Python 包

```python
# requirements.txt 新增
moviepy>=1.0.3           # 视频编辑和合成
pysrt>=1.1.2             # SRT字幕处理
pillow>=9.5.0            # 字幕渲染（MoviePy依赖）
numpy>=1.24.0            # 音频处理（MoviePy依赖）
```

### API 依赖

```python
# WavespeedAI API (已有)
- Qwen TTS (新增调用)
- OpenAI Whisper (新增调用)
- AI音乐生成 (新增调用)
- 现有图像/视频生成API

# DeepSeek API (已有)
- 故事生成
```

---

## 成本分析

### 方案对比

| 方案 | 单镜头成本 | 3镜头成本 | 5镜头成本 | 开发难度 | 推荐度 |
|------|----------|----------|----------|---------|--------|
| **方案A (极简)** | $0.50 | $1.50 | $2.50 | ⭐ | ⭐⭐⭐⭐ |
| **方案B (定制)** | $0.37 | $1.16 | $1.90 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **方案C (混合)** | $0.35 | $1.10 | $1.80 | ⭐⭐⭐ | ⭐⭐⭐⭐ |

### 与 MoneyPrinterTurbo 对比

MoneyPrinterTurbo（素材方案）:
- 配音: 免费（Edge TTS）
- 素材: $0.00（Pexels免费）
- 合成: $0.00（本地处理）
- **总成本: 几乎免费**

Wavespeed（AI生成方案）:
- 配音: ~$0.01
- 图像: $0.027
- 视频: $0.30
- **总成本: ~$0.37/镜头**

**差异原因**: MoneyPrinterTurbo 使用免费素材库，wavespeed 使用 AI 生成，质量更高但有成本。

---

## 配置示例

### config.toml 新增配置

```toml
[audio]
    # 语音合成设置
    tts_provider = "qwen-tts"  # qwen-tts / voice-clone
    voice = "zh-CN-XiaoxiaoNeural"  # 音色选择
    voice_speed = 1.0  # 语速调节 (0.5-2.0)
    voice_volume = 1.0  # 音量 (0.0-1.0)

[subtitle]
    # 字幕生成设置
    subtitle_provider = "whisper"  # whisper / simple
    language = "zh"  # 语言

    # 字幕样式
    font_name = "STHeiti"  # 字体
    font_size = 48  # 字号
    font_color = "white"  # 颜色
    outline_color = "black"  # 描边颜色
    outline_width = 2  # 描边宽度
    position = "bottom"  # 位置: top / center / bottom

[music]
    # 背景音乐设置
    enable_background_music = true  # 启用背景音乐
    music_provider = "ai-generate"  # ai-generate / local
    music_style = "upbeat"  # 音乐风格
    music_volume = 0.3  # 背景音乐音量 (0.0-1.0)

[composer]
    # 合成设置
    video_codec = "libx264"  # 视频编码
    audio_codec = "aac"  # 音频编码
    bitrate = "5000k"  # 码率
```

---

## 总结

### 核心优势

1. **统一平台** - 所有AI能力在 WavespeedAI 一站完成
2. **原生音频** - WAN 2.6/2.5 原生支持音视频同步
3. **高质量** - AI 生成比素材库更可控
4. **完整功能** - 配音+字幕+背景音乐+视频

### 推荐方案

**短期（快速上线）**: 方案A - 使用 WAN 2.6 原生音视频
**中期（功能完善）**: 方案C - 混合方案，平衡质量和成本
**长期（专业制作）**: 方案B - 完全定制，每个环节可控

### 下一步行动

1. ✅ **立即**: 测试 WAN 2.6 音视频效果
2. ⏳ **本周**: 验证 TTS 和 Whisper API
3. 📅 **下周**: 开始核心功能开发

---

**文档维护者**: Claude Code
**最后更新**: 2025-12-22
