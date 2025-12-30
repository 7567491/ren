# 数字人生成 Web 项目设计文档 v3.0

> 更新日期：2025-12-30  
> 适用范围：`frontend/`、`ad-back.py`、`py/`、Nginx @ `ren.linapp.fun`

本设计文档重构自 v2.0 故事化视频方案，聚焦于“数字人（Digital Human）”生成 Web 项目。内容包括对旧方案的批判性审视、全新架构设计、模块职责、数据流、接口约定及部署要求。

---

## 1. 现有方案问题（批判性建议）

1. **业务目标错位**：v2.0 围绕“多镜头故事 + DeepSeek + MoviePy”，与当前“头像+语音+唇同步”主线不符，导致开发人员无法按新需求实现。
2. **模块缺失**：文档未描述 Web 前端、任务状态 API、Nginx 反代 (`ren.linapp.fun → 18005`) 等关键组件，难以指导部署。
3. **API 过时**：仍引用 DeepSeek/Edge TTS，多镜头 I2V；未引用 `doc/数字人.md` 的 WaveSpeed API（Seedream、MiniMax、Infinitetalk）。
4. **数据结构不符**：继续强调 `story_outline.json / shots_script.json / shot_X.mp4`，无 `avatar.png / speech.mp3 / digital_human.mp4 / task.json` 等真实产物。
5. **错误处理与成本策略缺失**：未描述任务状态机、重试策略、调试模式、成本约束，容易造成浪费。

> **结论**：旧版设计已无法支撑当前目标，必须整体替换为数字人架构，并将 `doc/数字人.md` 视为 API 真正契约。

---

## 2. 设计目标

1. **Web 低门槛**：用户在浏览器填写提示词/脚本 → 后端 orchestrate WaveSpeed API → 返回视频 URL。
2. **三阶段流水线**：头像（Seedream/上传）→ 语音（MiniMax）→ 唇同步（Infinitetalk/Multitalk）。
3. **任务可观测性**：前端可轮询任务状态，看到每个阶段的进展、日志、成本估算。
4. **安全与成本控制**：密钥存于 `.env`，默认调试模式限制 10 秒语音，重试与限流策略内建。
5. **部署一体化**：Nginx 负责 SSL 与静态资源，后端监听 `0.0.0.0:18005`，域名 `ren.linapp.fun`。

---

## 3. 总体架构

```
Browser (frontend/) ──HTTPS──> Nginx (ren.linapp.fun)
                               ├─ /          -> frontend/dist
                               └─ /api       -> 127.0.0.1:18005

ad-back.py (Flask/FastAPI)
 ├─ py/api/routes_digital_human.py      REST
 ├─ py/function/task_runner.py          状态机 & 调度
 ├─ py/services/digital_human_service   WaveSpeed API 封装
 ├─ py/services/storage_service         输出资产 & CDN
 └─ py/services/logging/retry/...       公共基础设施
```

关键依赖：`doc/数字人.md`（API 说明）、`README.md`（快速开始）、`AGENTS.md`/`CLAUDE.md`（协作规范）。

---

## 4. 模块设计

### 4.1 前端 `frontend/`
- 表单：`avatar_mode (upload/prompt)`, `avatar_prompt`, `speech_text`, `voice_id/speed/pitch/emotion`, `resolution`, `seed`, `mask_image`。
- 交互：`POST /api/tasks` 创建任务，轮询 `GET /api/tasks/<id>` 获得状态、日志、视频 URL。
- 播放卡片：展示头像预览、音频试听、视频播放、成本估算。
- 技术栈：Vite + Vue/React 或纯静态资源；`npm run build` 输出 `frontend/dist`。

### 4.2 后端入口 `ad-back.py`
- 负责启动 Flask/FastAPI 服务（默认 `0.0.0.0:18005`），加载 `.env`、`config.yaml`。
- 提供 CLI 参数 `--port` / `--config` / `--debug`。
- 将请求分发到 `py/api` 蓝图，并注入日志/追踪上下文。

### 4.3 API 层 `py/api/`
- `routes_digital_human.py`：`POST /api/tasks`，`GET /api/tasks/<id>`，`POST /api/assets/upload`，`GET /api/health`。
- 请求体验证（Pydantic/Marshmallow），响应体包含 `status`, `links`, `cost`, `error_code`, `trace_id`。
- 将任务推送给 `task_runner`，返回 `task_id`。

### 4.4 任务调度 `py/function/task_runner.py`
- 状态机：`pending -> avatar_generating -> avatar_ready -> speech_ready -> video_rendering -> finished/failed`。
- 保存 `task.json`（含配置、状态、WaveSpeed task_id、成本、时间戳）。
- 按阶段调用 `services/digital_human_service`，并根据配置控制并发（Seedream <=2, Infinitetalk=1）。
- 支持“调试模式”限制语音 <= 10s，生成完成后更新 `output/aka-{task}/digital_human.mp4`。

### 4.5 服务层 `py/services/`
- `digital_human_service.py`：封装 WaveSpeed API（MiniMax 语音同样通过 WaveSpeed 提供的 `/minimax/speech-02-hd` 代理）：
  - `generate_avatar(prompt | upload_url)`
  - `generate_voice(text, voice_options)`
  - `animate_avatar(image_url, audio_url, mode=infinitetalk)`
  - 内含统一重试（3 次、指数 5s/10s/15s）与 trace 日志。
- `storage_service.py`：负责将生成文件存入 `output/` 或对象存储（如 `https://s.linapp.fun/digital-human/<task>.mp4`），并返回可访问 URL。
- 可选：`music_service`, `subtitle_service` 供后续增强。

### 4.6 配置
- `.env`: `WAVESPEED_API_KEY`, `MINIMAX_API_KEY`, `STORAGE_BUCKET_URL`, `DEBUG_MODE` 等。
- `config.yaml`: port、输出目录、并发/重试、Nginx public_url、调试限制。
- `user.yaml`: 本地预设测试参数，生产不读取。

---

## 5. 数据与文件结构

```
output/aka-{task_id}/
├── task.json             # 状态、配置、成本、trace
├── avatar.png            # Seedream 或上传头像副本
├── speech.mp3            # MiniMax 输出
├── digital_human.mp4     # Infinitetalk 视频
└── log.txt               # 本任务日志
```

除此之外，服务器挂载的 `/mnt/www`（已由运维映射到 `https://s.linapp.fun/`）下新建 `ren/` 目录，TaskRunner 会在生成完成时创建 `ren_{MMDDHHMM}` 子目录（例如 `ren_12301845`），并将最终视频复制为 `/mnt/www/ren/ren_{MMDDHHMM}/digital_human.mp4`。这样用户即可通过 `https://s.linapp.fun/ren/ren_{MMDDHHMM}/digital_human.mp4` 访问成果，无需额外 CDN 配置。

`task.json` 示例：
```json
{
  "task_id": "aka-123456",
  "status": "video_rendering",
  "config": { "voice_id": "Wise_Woman", "resolution": "720p" },
  "stages": {
    "avatar": { "state": "completed", "image_url": "https://..." },
    "speech": { "state": "completed", "audio_url": "https://..." },
    "video":  { "state": "running",   "wavespeed_task_id": "abc123" }
  },
  "cost_estimate_usd": 0.045,
  "created_at": "2025-12-30T05:30:00Z",
  "updated_at": "2025-12-30T05:31:20Z"
}
```

---

## 6. 工作流（阶段）

1. **阶段0：任务创建**
   - 前端提交配置 → 后端校验参数、写入 `task.json`、返回 `task_id`。
2. **阶段1：形象生成**
   - `avatar_mode=upload`：校验文件 → 存储 → 更新状态。
   - `avatar_mode=prompt`：调用 Seedream v4（`doc/数字人.md`）→ 保存 `avatar.png` → 状态 `avatar_ready`。
3. **阶段2：语音生成**
   - 调用 MiniMax speech-02-hd，参数：`text/voice_id/speed/pitch/emotion/sample_rate`。
   - 保存 `speech.mp3` 与 `audio_url`。
4. **阶段3：唇同步**
   - 调 Infinitetalk（或 Multi）→ 返回 `task_id` → 轮询 `/api/v3/tasks/<id>`，直至 `completed`。
   - 下载 `video_url`，写入 `digital_human.mp4`。
5. **阶段4：发布**
   - 资产上传至对象存储（或保留在 output + 提供本地 URL）。
   - 状态标记为 `finished`，记录成本，通知前端。

---

## 7. API 契约

### POST `/api/tasks`
请求：
```json
{
  "avatar_mode": "prompt",
  "avatar_prompt": "25岁职业女性...",
  "speech_text": "大家好...",
  "voice": { "voice_id": "Wise_Woman", "speed": 1.0, "emotion": "neutral" },
  "resolution": "720p",
  "seed": 42,
  "debug_mode": true
}
```
响应：
```json
{ "task_id": "aka-123456", "status": "pending", "links": { "poll": "/api/tasks/aka-123456" } }
```

### GET `/api/tasks/<task_id>`
返回：
```json
{
  "task_id": "aka-123456",
  "status": "speech_ready",
  "avatar_url": "https://...",
  "audio_url": "https://...",
  "video_url": null,
  "stages": { "avatar": {...}, "speech": {...}, "video": {...} },
  "cost_estimate_usd": 0.045,
  "trace_id": "req-789",
  "logs": ["2025-12-30 13:30 avatar ready", "..."]
}
```

### POST `/api/assets/upload`
- 供前端上传头像或字幕，可返回临时 URL。

---

## 8. 错误处理与重试

- `services/digital_human_service` 抛 `ExternalAPIError(code, message, provider_trace)`，API 层转换为 HTTP 4xx/5xx。
- 重试策略：指数退避 (5s/10s/15s)，超过次数标记任务失败并透传错误信息。
- 网络/限流错误 → 自动重试；参数错误 → 直接失败并返回可诊断信息。
- 所有阶段记录 trace id 与 provider task id，便于对接 WaveSpeed 官方支持。

---

## 9. 部署拓扑（Nginx + 后端）

1. 后端服务：
   ```bash
   source venv/bin/activate
   python3 ad-back.py --port 18005 --config config.yaml
   ```
2. 前端构建：`npm run build` → 部署 `frontend/dist` 至 `/var/www/digital-human`.
3. Nginx（关键点）：
   - `server_name ren.linapp.fun;`
   - `location /api/ { proxy_pass http://127.0.0.1:18005/; proxy_read_timeout 120s; }`
   - `location / { try_files $uri /index.html; }`
   - HTTPS 证书由 Certbot 管理。

---

## 10. 成本与调试

| 阶段 | 服务 | 成本估算 |
|------|------|---------|
| 形象 | Seedream v4 | \$0.02–0.05 / 张 |
| 语音 | MiniMax speech-02-hd | \$0.01–0.03 / 分钟 |
| 唇同步 | Infinitetalk | \$0.10–0.20 / 分钟 |

- **调试模式**（默认开启）：限制语音 <= 10s，预计总成本 < \$0.05。
- **生产模式**：取消限制，但需在任务创建时显式 `debug_mode=false`。
- `py/test_network.py --digital-human`：按顺序调用三阶段 API，验证 Key、网络、限流配置。

---

## 11. 测试策略

1. **Mock 单测**：`PYTEST_WAVESPEED_MOCK=1 pytest test/test-digital-human.py`。
2. **真实冒烟**：准备 8-10 秒文案，运行 `python3 py/test_network.py --digital-human`。
3. **前后端联调**：`npm run dev` + `python3 ad-back.py --port 18005`，从浏览器创建任务，观察状态转换。
4. **部署验证**：上线后访问 `https://ren.linapp.fun/api/health`，并生成一条 10 秒视频，确认 CDN URL 可播放。

---

## 12. 后续优化方向

- **多角色对话**：扩展 Infinitetalk Multi，支持左右角色、轮流说话。
- **字幕/水印**：复用 `services/subtitle_service` 将文本渲染到视频。
- **BGM 引擎**：整合 `music/` 工具，自动匹配场景氛围音乐。
+- **任务排队/优先级**：增加 Redis 队列或云函数以支撑大规模请求。

---

> 如需修改数字人 API 参数或新增模型，请先更新 `doc/数字人.md`，再同步 README/AGENTS/CLAUDE/本设计文档，确保全体成员可遵循最新架构实施。***
