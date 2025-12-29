# 详细设计文档 v2.0 - AI视频生成系统（故事化增强版）

## 系统架构

### 1. 整体流程（更新）
```
用户交互 → 风格配置 → 故事大纲生成 → 分镜脚本生成 →
并发图像生成 → 串行视频生成 → 视频合成 → 输出成品
```

### 2. 核心模块设计

#### 2.1 用户交互模块（新增✨）
**功能**：收集用户输入，配置生成参数

**交互流程**：
```python
def interactive_setup():
    """交互式配置向导"""
    # 1. 欢迎界面
    print_welcome()

    # 2. 输入主题
    topic = input("请输入视频主题: ")

    # 3. 选择风格
    style = select_style()  # 返回风格名称

    # 4. 配置镜头数
    shot_count = input_number("镜头数量", default=3, min=1, max=10)

    # 5. 配置时长
    duration = input_number("每镜头时长(秒)", default=5, min=3, max=5)

    # 6. 确认配置
    confirm_config(topic, style, shot_count, duration)

    return ProjectConfig(topic, style, shot_count, duration)
```

**输出**：ProjectConfig对象
```python
@dataclass
class ProjectConfig:
    topic: str           # 主题
    style: str           # 风格名称
    shot_count: int      # 镜头数
    shot_duration: int   # 单镜头时长
    timestamp: str       # 运行时间戳
```

#### 2.2 风格模板系统（新增✨）
**功能**：管理10种预定义视觉风格

**风格数据结构**：
```python
STYLE_TEMPLATES = {
    "technology": {
        "name": "科技/未来风",
        "name_en": "Technology/Futuristic",
        "description": "未来科技感，强调数据可视化和AI元素",
        "visual_style": "futuristic, high-tech, digital, holographic",
        "color_palette": "blue, purple, neon, cyan",
        "lighting": "neon lighting, digital glow, volumetric light",
        "camera_movement": "smooth tracking, orbital rotation, dolly zoom",
        "typical_elements": [
            "data streams", "holographic displays",
            "circuit boards", "server rooms", "AI visualization"
        ],
        "mood": "innovative, cutting-edge, advanced",
        "reference_style": "cyberpunk 2077, tron, blade runner 2049"
    },

    "xianxia": {
        "name": "仙侠/东方奇幻",
        "name_en": "Xianxia/Oriental Fantasy",
        "description": "中国风仙侠，飘逸灵动",
        "visual_style": "ethereal, Chinese mythology, martial arts fantasy",
        "color_palette": "jade green, gold, misty white, crimson",
        "lighting": "soft volumetric fog, divine glow, moonlight",
        "camera_movement": "floating crane shot, slow motion, spiral ascent",
        "typical_elements": [
            "flying swords", "misty mountains", "celestial palaces",
            "martial arts", "mystical creatures", "flowing robes"
        ],
        "mood": "transcendent, mystical, elegant",
        "reference_style": "Chinese wuxia films, genshin impact"
    },

    "cyberpunk": {
        "name": "赛博朋克",
        "name_en": "Cyberpunk",
        "description": "霓虹都市，反乌托邦科技",
        "visual_style": "dystopian, neon-noir, urban decay, high-tech low-life",
        "color_palette": "neon pink, electric blue, toxic green, dark purple",
        "lighting": "neon signs, rain reflections, volumetric fog",
        "camera_movement": "handheld gritty, rain soaked tracking, dutch angle",
        "typical_elements": [
            "neon signs", "rainy streets", "megacorporations",
            "cybernetic implants", "flying cars", "dark alleyways"
        ],
        "mood": "gritty, rebellious, dystopian",
        "reference_style": "blade runner, ghost in the shell, cyberpunk 2077"
    },

    # ... 其他7种风格类似结构
}
```

**风格应用函数**：
```python
def apply_style_to_prompt(base_prompt: str, style: dict) -> str:
    """将风格模板应用到基础提示词"""
    enhanced = f"{base_prompt}, "
    enhanced += f"{style['visual_style']}, "
    enhanced += f"color palette: {style['color_palette']}, "
    enhanced += f"{style['lighting']}, "
    enhanced += f"{style['camera_movement']}, "
    enhanced += f"mood: {style['mood']}"
    return enhanced
```

#### 2.3 故事生成模块（核心改进✨）
**功能**：两阶段生成连贯故事

**阶段1：故事大纲生成**
```python
def generate_story_outline(config: ProjectConfig) -> StoryOutline:
    """生成完整故事大纲"""

    style_template = STYLE_TEMPLATES[config.style]

    prompt = f"""
你是一位专业的视频脚本策划师。请为以下主题创作一个{config.shot_count}镜头的短视频故事大纲。

主题：{config.topic}
视觉风格：{style_template['name']}（{style_template['description']})
镜头数：{config.shot_count}个
总时长：{config.shot_count * config.shot_duration}秒

故事结构要求：
1. 起承转合结构清晰
2. 每个镜头是故事的有机组成部分
3. 镜头之间有明确的因果关系或时间推进
4. 视觉风格统一：{style_template['visual_style']}
5. 色彩基调：{style_template['color_palette']}
6. 典型元素：{', '.join(style_template['typical_elements'][:3])}

请以JSON格式输出故事大纲：
{{
  "title": "故事标题",
  "theme": "核心主题",
  "story_arc": {{
    "setup": "开场设定（30字内）",
    "development": "情节发展（30字内）",
    "climax": "高潮转折（30字内）",
    "resolution": "结局升华（30字内）"
  }},
  "visual_theme": {{
    "primary_colors": ["主色调1", "主色调2"],
    "key_elements": ["核心视觉元素1", "核心视觉元素2"],
    "lighting_mood": "整体光影氛围"
  }},
  "shot_breakdown": [
    {{
      "shot_number": 1,
      "story_beat": "起",
      "scene_summary": "镜头内容概要（20字内）",
      "key_action": "关键动作",
      "transition_to_next": "与下一镜头的连接"
    }},
    // ... 其他镜头
  ]
}}
"""

    response = call_deepseek_api(prompt)
    return parse_story_outline(response)
```

**阶段2：分镜脚本生成**
```python
def generate_shot_scripts(outline: StoryOutline, config: ProjectConfig) -> List[ShotScript]:
    """基于故事大纲生成详细分镜"""

    shots = []
    style_template = STYLE_TEMPLATES[config.style]

    for i, beat in enumerate(outline.shot_breakdown):
        # 获取前后镜头信息用于连贯性
        prev_shot = outline.shot_breakdown[i-1] if i > 0 else None
        next_shot = outline.shot_breakdown[i+1] if i < len(outline.shot_breakdown)-1 else None

        prompt = f"""
基于以下故事大纲，生成第{i+1}个镜头的详细英文prompt（用于AI视频生成）。

整体故事：{outline.theme}
视觉主题：主色调{outline.visual_theme['primary_colors']},
          核心元素{outline.visual_theme['key_elements']},
          光影氛围{outline.visual_theme['lighting_mood']}

当前镜头：
- 镜头编号：{beat['shot_number']}/{config.shot_count}
- 故事节拍：{beat['story_beat']}
- 场景概要：{beat['scene_summary']}
- 关键动作：{beat['key_action']}

前一镜头连接：{prev_shot['transition_to_next'] if prev_shot else '开场'}
下一镜头铺垫：{beat['transition_to_next']}

风格要求：
- 视觉风格：{style_template['visual_style']}
- 色彩方案：{style_template['color_palette']}
- 光影：{style_template['lighting']}
- 镜头运动：{style_template['camera_movement']}
- 氛围：{style_template['mood']}

请生成一个80-120词的详细英文prompt，要求：
1. 包含具体的视觉描述（场景、主体、动作）
2. 体现与前一镜头的连续性
3. 为下一镜头做铺垫
4. 严格遵守风格模板
5. 描述要cinemat ic和专业

只返回prompt文本，不要其他内容。
"""

        response = call_deepseek_api(prompt)
        shot_prompt = response.strip()

        shots.append(ShotScript(
            id=beat['shot_number'],
            story_beat=beat['story_beat'],
            summary_cn=beat['scene_summary'],
            prompt_en=shot_prompt,
            visual_continuity={
                'from_previous': prev_shot['key_action'] if prev_shot else None,
                'to_next': beat['transition_to_next']
            }
        ))

    return shots
```

**数据结构**：
```python
@dataclass
class StoryOutline:
    title: str
    theme: str
    story_arc: dict      # {setup, development, climax, resolution}
    visual_theme: dict   # {primary_colors, key_elements, lighting_mood}
    shot_breakdown: list # 每个镜头的概要

@dataclass
class ShotScript:
    id: int
    story_beat: str              # 起/承/转/合
    summary_cn: str              # 中文概要
    prompt_en: str               # 英文prompt（用于生成）
    visual_continuity: dict      # 连贯性信息
```

#### 2.2 视频素材生成模块（使用WavespeedAI API）
- **图像生成**：根据prompt生成关键帧
- **视频生成**：基于图像或prompt生成3秒视频片段
- **音频生成**：生成科技感背景音乐（电子、氛围音乐）
- **参数配置**：
  - 分辨率：1080p或4K
  - 帧率：30fps或60fps
  - 视频时长：3秒/镜头

#### 2.3 视频合成模块
- **工具**：使用FFmpeg或moviepy库
- **功能**：
  - 拼接多个视频片段
  - 添加背景音乐
  - 可选：添加淡入淡出转场效果
  - 音视频同步
- **输出格式**：MP4（H.264编码）

### 3. 数据流设计（更新）

```
阶段0: 配置与验证
├─ 验证API密钥
├─ 用户交互获取配置
└─ 创建工作目录

阶段1: 故事策划（新增✨）
├─ 调用DeepSeek生成故事大纲
│  └─ 输出：story_outline.json
├─ 显示故事结构给用户确认
└─ 调用DeepSeek生成分镜脚本
   └─ 输出：shots_script.json（包含连贯的镜头描述）

阶段2: 并发图像生成
├─ 并发调用WavespeedAI（3个并发）
│  └─ 输入：每个镜头的prompt
│  └─ 输出：shot_1_image.png, shot_2_image.png, ...
└─ 保存检查点

阶段3: 串行视频生成
├─ 遍历每个镜头（带检查点恢复）
│  └─ 调用WavespeedAI I2V API
│  └─ 输出：shot_1.mp4, shot_2.mp4, ...
│  └─ 保存检查点
└─ 进度显示

阶段4: 视频合成
├─ 使用FFmpeg拼接所有镜头
└─ 输出：final_video.mp4
```

### 4. 关键算法设计

#### 4.1 连贯性提示词生成算法
```python
def enhance_prompt_with_continuity(
    shot: ShotScript,
    prev_shot: Optional[ShotScript],
    next_hint: str,
    style: dict
) -> str:
    """增强提示词的连贯性"""

    # 基础prompt
    prompt = shot.prompt_en

    # 添加前一镜头的视觉延续
    if prev_shot:
        continuity_prefix = f"Continuing from previous scene with {prev_shot.visual_continuity['to_next']}, "
        prompt = continuity_prefix + prompt

    # 添加风格一致性描述
    style_suffix = f", {style['visual_style']}, "
    style_suffix += f"color grading: {style['color_palette']}, "
    style_suffix += f"{style['lighting']}, "
    style_suffix += f"{style['camera_movement']}, "
    style_suffix += f"{style['mood']} atmosphere"

    prompt += style_suffix

    # 添加为下一镜头的过渡
    if next_hint:
        transition_suffix = f", transitioning towards {next_hint}"
        prompt += transition_suffix

    return prompt
```

#### 4.2 故事节拍分配算法
```python
def assign_story_beats(shot_count: int) -> List[str]:
    """根据镜头数分配起承转合"""

    if shot_count == 3:
        return ['起', '承转', '合']
    elif shot_count == 4:
        return ['起', '承', '转', '合']
    elif shot_count == 5:
        return ['起', '承', '承转', '转', '合']
    else:  # 6-10个镜头
        beats = ['起']
        development_count = (shot_count - 3) // 2
        climax_count = (shot_count - 3) - development_count

        beats.extend(['承'] * development_count)
        beats.extend(['转'] * climax_count)
        beats.append('合')

        return beats
```

### 4. 错误处理
- API调用失败重试机制（最多3次）
- 超时处理（设置合理timeout）
- 文件生成验证（检查文件大小和完整性）
- 日志记录（记录关键步骤和错误）

### 5. 配置文件设计
**.env文件**：
```
DEEPSEEK_API_KEY=your_key
WAVESPEED_API_KEY=your_key
WAVESPEED_API_URL=api_endpoint
```

### 6. 输出目录结构
```
./akamAI/
  ├── shots_script.json      # 镜头脚本
  ├── shot_1.mp4             # 镜头1
  ├── shot_2.mp4             # 镜头2
  ├── shot_3.mp4             # 镜头3
  ├── background_music.mp3   # 背景音乐
  ├── final_video.mp4        # 最终成品
  └── logs.txt               # 日志文件
```

### 7. 技术选型
- **Python 3.8+**
- **依赖库**：
  - `requests`：API调用
  - `python-dotenv`：环境变量管理
  - `moviepy`或`ffmpeg-python`：视频处理
  - `openai`或`requests`：DeepSeek API调用

### 8. 性能考虑
- 异步处理可以加快多个镜头的并行生成
- 但考虑到简单性，初版使用同步顺序处理
- 预计总耗时：5-10分钟（取决于API响应速度）
