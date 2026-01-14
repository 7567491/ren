# 数字人生成系统 API 参数清单

> 基于 design.md 和 doc/数字人.md 整理
> 更新时间: 2025-12-30

---

## 阶段1: 头像生成 (Seedream v4)

### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 | 范围/示例 |
|------|------|------|--------|------|-----------|
| `prompt` | string | 是 | - | 头像描述提示词 | "专业女性播音员，微笑，正面照" |
| `negative_prompt` | string | 否 | "低质量，模糊，变形" | 负面提示词 | - |
| `width` | integer | 否 | 1024 | 图像宽度 | 512/1024 |
| `height` | integer | 否 | 1024 | 图像高度 | 512/1024 |
| `num_inference_steps` | integer | 否 | 50 | 推理步数 | 20-100 |
| `guidance_scale` | float | 否 | 7.5 | 引导系数 | 1.0-20.0 |

### 响应字段

```json
{
  "output": {
    "image_url": "string",      // 生成的图像URL
    "width": 1024,              // 图像宽度
    "height": 1024,             // 图像高度
    "seed": 42                  // 使用的随机种子
  },
  "task_id": "string",          // 任务ID（如果异步）
  "cost": 0.03                  // 成本估算（美元）
}
```

---

## 阶段2: 语音生成 (MiniMax speech-02-hd)

### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 | 范围/示例 |
|------|------|------|--------|------|-----------|
| `text` | string | 是 | - | 播报文本 | "大家好，欢迎收看..." |
| `voice_id` | string | 是 | "male-qn-qingse" | 音色ID | female-shaonv/male-qn-jingying 等 |
| `speed` | float | 否 | 1.0 | 语速 | 0.5-2.0 |
| `pitch` | integer | 否 | 0 | 音调 | -12 至 12 |
| `emotion` | string | 否 | "neutral" | 情绪 | neutral/happy/sad/angry |
| `sample_rate` | integer | 否 | 32000 | 采样率 | 16000/24000/32000 |
| `channel` | integer | 否 | 1 | 声道数 | 1=单声道, 2=立体声 |
| `english_normalization` | boolean | 否 | true | 英文数字自然发音 | true/false |
| `bitrate` | integer | 否 | 128000 | 比特率 | - |

### 可用音色列表

| voice_id | 描述 | 性别 | 特征 |
|----------|------|------|------|
| `female-shaonv` | 女声-少女 | 女 | 年轻、活泼 |
| `female-yujie` | 女声-御姐 | 女 | 成熟、稳重 |
| `male-qn-qingse` | 男声-青涩 | 男 | 年轻、清新 |
| `male-qn-jingying` | 男声-精英 | 男 | 专业、自信 |
| `Wise_Woman` | 智慧女性 | 女 | 知性、沉稳 |
| `Young_Male` | 年轻男性 | 男 | 朝气、友好 |
| `Professional_Female` | 职业女性 | 女 | 专业、干练 |

### 响应字段

```json
{
  "output": {
    "audio_url": "string",      // 生成的音频URL
    "duration": 12.5,           // 音频时长（秒）
    "sample_rate": 32000,       // 采样率
    "channel": 1                // 声道数
  },
  "task_id": "string",          // 任务ID
  "cost": 0.025                 // 成本估算（美元）
}
```

---

## 阶段3: 唇同步视频 (Infinitetalk)

### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 | 范围/示例 |
|------|------|------|--------|------|-----------|
| `image_url` | string | 是 | - | 数字人头像URL | 阶段1生成的image_url |
| `audio_url` | string | 是 | - | 配音音频URL | 阶段2生成的audio_url |
| `resolution` | string | 否 | "720p" | 视频分辨率 | "720p" / "1080p" |
| `seed` | integer | 否 | 42 | 随机种子 | 任意整数 |
| `mask_image` | string | 否 | null | 蒙版图片URL | 定义可动画区域 |
| `prompt` | string | 否 | "" | 额外定制指令 | - |

### 响应字段（提交任务）

```json
{
  "task_id": "string",          // 任务ID（用于轮询）
  "status": "pending",          // 初始状态
  "message": "任务已创建"
}
```

### 响应字段（轮询状态）

```json
{
  "task_id": "string",
  "state": "completed",         // pending/processing/completed/failed
  "progress": 100,              // 进度百分比
  "output": {
    "video_url": "string",      // 生成的视频URL
    "duration": 12.5,           // 视频时长（秒）
    "resolution": "720p",       // 分辨率
    "fps": 25                   // 帧率
  },
  "cost": 0.75,                 // 成本（美元）
  "error": null,                // 错误信息（如失败）
  "created_at": "2025-12-30T10:00:00Z",
  "completed_at": "2025-12-30T10:05:00Z"
}
```

### 成本计算规则

- **720p**: $0.06/秒
- **1080p**: $0.12/秒

示例: 60秒视频 @ 720p = 60 × $0.06 = $3.60

---

## 我们的系统 API（前后端接口）

### POST /api/tasks - 创建数字人任务

#### 请求体

```json
{
  "avatar_mode": "prompt",                    // 必填: "upload" 或 "prompt"
  "avatar_prompt": "专业女性播音员...",       // avatar_mode=prompt 时必填
  "avatar_upload_url": "https://...",         // avatar_mode=upload 时必填
  "speech_text": "大家好，欢迎收看...",       // 必填: 播报文本
  "voice_id": "female-shaonv",               // 必填: 音色ID
  "resolution": "720p",                      // 可选: 默认 720p
  "speed": 1.0,                              // 可选: 默认 1.0
  "pitch": 0,                                // 可选: 默认 0
  "emotion": "neutral",                      // 可选: 默认 neutral
  "seed": 42,                                // 可选: 默认 42
  "mask_image": null                         // 可选: 默认 null
}
```

#### 请求验证规则

```python
# 必填字段
assert avatar_mode in ["upload", "prompt"]
assert len(speech_text) > 0

# 条件必填
if avatar_mode == "prompt":
    assert avatar_prompt is not None and len(avatar_prompt) > 0
if avatar_mode == "upload":
    assert avatar_upload_url is not None and len(avatar_upload_url) > 0

# 范围验证
assert voice_id in VALID_VOICE_IDS
assert resolution in ["720p", "1080p"]
assert 0.5 <= speed <= 2.0
assert -12 <= pitch <= 12
assert emotion in ["neutral", "happy", "sad", "angry"]
```

#### 响应

```json
{
  "job_id": "aka-12301230",
  "status": "pending",
  "message": "任务已创建，开始生成数字人视频...",
  "cost_estimate": {
    "avatar": 0.03,
    "speech": 0.02,
    "video_per_second": 0.06,
    "total_min": 0.65,          // 假设10秒视频
    "total_max": 4.32           // 假设60秒视频
  }
}
```

---

### GET /api/tasks/{job_id} - 查询任务状态

#### 响应

```json
{
  "job_id": "aka-12301230",
  "status": "video_rendering",               // 当前状态
  "message": "正在生成数字人视频（5-10分钟）...",
  "progress": {
    "avatar": "completed",                   // completed/in_progress/pending/failed
    "speech": "completed",
    "video": "in_progress"
  },
  "assets": {
    "avatar_url": "https://.../avatar.png",  // 头像URL（如已生成）
    "audio_url": "https://.../speech.mp3",   // 音频URL（如已生成）
    "video_url": null                        // 视频URL（生成中）
  },
  "metadata": {
    "duration": 12.5,                        // 音频/视频时长
    "resolution": "720p",
    "voice_id": "female-shaonv"
  },
  "cost": {
    "avatar": 0.03,
    "speech": 0.025,
    "video": null,                           // 视频未完成
    "total": null
  },
  "error": null,                             // 错误信息（如失败）
  "trace_id": "trace-abc123",                // 追踪ID
  "created_at": "2025-12-30T10:00:00Z",
  "updated_at": "2025-12-30T10:02:30Z"
}
```

#### 状态流转

```
pending
  ↓
avatar_generating
  ↓
avatar_ready
  ↓
speech_generating
  ↓
speech_ready
  ↓
video_rendering
  ↓
finished / failed
```

---

### POST /api/assets/upload - 上传头像

#### 请求（multipart/form-data）

```
file: <binary>     // 图片文件
```

#### 验证规则

- 文件类型: PNG, JPG, JPEG, WEBP
- 文件大小: < 5MB
- 图像分辨率: 建议 1024x1024

#### 响应

```json
{
  "url": "https://s.linapp.fun/upload/avatar-xxx.png",
  "filename": "avatar-xxx.png",
  "size": 245678,                            // 字节
  "content_type": "image/png"
}
```

---

### GET /api/health - 健康检查

#### 响应

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-12-30T10:00:00Z",
  "services": {
    "wavespeed_api": "available",            // available/unavailable
    "minimax_api": "available",
    "storage": "available"
  }
}
```

---

## 任务持久化格式 (task.json)

存储在 `output/aka-{job_id}/task.json`：

```json
{
  "job_id": "aka-12301230",
  "status": "finished",
  "created_at": "2025-12-30T10:00:00Z",
  "updated_at": "2025-12-30T10:07:00Z",
  "completed_at": "2025-12-30T10:07:00Z",

  "params": {
    "avatar_mode": "prompt",
    "avatar_prompt": "专业女性播音员...",
    "speech_text": "大家好...",
    "voice_id": "female-shaonv",
    "resolution": "720p",
    "speed": 1.0,
    "pitch": 0,
    "emotion": "neutral",
    "seed": 42,
    "mask_image": null
  },

  "assets": {
    "avatar_url": "https://.../avatar.png",
    "avatar_path": "output/aka-12301230/avatar.png",
    "audio_url": "https://.../speech.mp3",
    "audio_path": "output/aka-12301230/speech.mp3",
    "video_url": "https://.../digital_human.mp4",
    "video_path": "output/aka-12301230/digital_human.mp4"
  },

  "external_task_ids": {
    "seedream": "task-xyz",
    "minimax": "task-abc",
    "infinitetalk": "task-def"
  },

  "cost": {
    "avatar": 0.03,
    "speech": 0.025,
    "video": 0.75,
    "total": 0.805
  },

  "metadata": {
    "duration": 12.5,
    "resolution": "720p",
    "fps": 25
  },

  "error": null,
  "trace_id": "trace-abc123"
}
```

---

## 错误响应格式

### 客户端错误 (4xx)

```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "avatar_mode=prompt 时必须提供 avatar_prompt",
    "field": "avatar_prompt",
    "trace_id": "trace-abc123"
  }
}
```

### 服务端错误 (5xx)

```json
{
  "error": {
    "code": "EXTERNAL_API_ERROR",
    "message": "Infinitetalk API 超时",
    "provider": "wavespeed-infinitetalk",
    "status_code": 500,
    "trace_id": "trace-abc123",
    "retry_after": 60                        // 建议重试间隔（秒）
  }
}
```

### 错误码清单

| 错误码 | HTTP状态 | 说明 |
|--------|----------|------|
| `INVALID_PARAMETER` | 400 | 请求参数无效 |
| `MISSING_REQUIRED_FIELD` | 400 | 缺少必填字段 |
| `TASK_NOT_FOUND` | 404 | 任务不存在 |
| `UPLOAD_FILE_TOO_LARGE` | 413 | 上传文件过大 |
| `UNSUPPORTED_FILE_TYPE` | 415 | 不支持的文件类型 |
| `EXTERNAL_API_ERROR` | 502 | 外部API错误 |
| `TASK_TIMEOUT` | 504 | 任务超时 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求频率超限 |

---

## 环境变量配置

```env
# 必填
WAVESPEED_API_KEY=wavespeed_xxx        # 控制台原样复制即可，无需添加 sk- 前缀
MINIMAX_API_KEY=sk-xxx

# 可选 - 对象存储
STORAGE_BUCKET_URL=https://s.linapp.fun
OSS_ACCESS_KEY=xxx
OSS_SECRET_KEY=xxx

# 可选 - 服务配置
API_PORT=18000
API_HOST=0.0.0.0
PUBLIC_URL=https://ren.linapp.fun

# 可选 - 并发与重试
MAX_CONCURRENT_TASKS=3
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_SECONDS=5,10,15

# 可选 - 调试
DEBUG=false
LOG_LEVEL=INFO
```

---

## 配置文件 (config.yaml) 示例

```yaml
# 数字人系统配置
digital_human:
  # 并发控制
  concurrency:
    max_tasks: 3                         # 最大并发任务数
    seedream: 2                          # Seedream 并发限制
    infinitetalk: 1                      # Infinitetalk 串行执行

  # 重试策略
  retry:
    max_attempts: 3
    backoff_seconds: [5, 10, 15]
    retry_on_status: [429, 500, 502, 503, 504]

  # 超时配置
  timeout:
    avatar_generation: 60                # 秒
    speech_generation: 120               # 秒
    video_rendering: 600                 # 秒（10分钟）

  # 默认参数
  defaults:
    resolution: "720p"
    speed: 1.0
    pitch: 0
    emotion: "neutral"
    seed: 42

  # Debug 模式
  debug:
    enabled: false
    max_speech_length: 50                # Debug 模式下限制文本长度
    mock_external_api: false             # 使用 mock 数据

# 前端配置
frontend:
  public_url: "https://ren.linapp.fun"
  poll_interval: 2000                    # 轮询间隔（毫秒）

# 存储配置
storage:
  output_dir: "output"
  upload_dir: "output/uploads"
  max_upload_size: 5242880               # 5MB
  allowed_extensions: [".png", ".jpg", ".jpeg", ".webp"]

  # 对象存储（可选）
  oss:
    enabled: false
    bucket: "s.linapp.fun"
    prefix: "digital-human"

# 日志配置
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  output_file: "logs/api.log"
```

---

## 总结

### 核心数据流

```
用户输入
  ↓
POST /api/tasks (验证参数)
  ↓
创建 task.json (status: pending)
  ↓
[阶段1] Seedream API → avatar_url
  ↓
更新 task.json (status: avatar_ready)
  ↓
[阶段2] MiniMax API → audio_url
  ↓
更新 task.json (status: speech_ready)
  ↓
[阶段3] Infinitetalk API → task_id
  ↓
轮询 task_id 直到 completed
  ↓
下载 video_url → 本地文件
  ↓
更新 task.json (status: finished)
  ↓
前端轮询 GET /api/tasks/{id}
  ↓
显示视频播放器
```

### 关键注意事项

1. **参数验证**: 所有用户输入必须严格验证范围和类型
2. **错误处理**: 外部API错误必须携带 trace_id 和 provider
3. **重试机制**: 429/5xx 错误需要指数退避重试
4. **成本追踪**: 每个阶段完成后立即记录成本
5. **状态持久化**: 每次状态变更都要写入 task.json
6. **日志完整性**: 所有外部API调用必须记录到 log.txt

---

**文档版本**: 1.0
**更新时间**: 2025-12-30
