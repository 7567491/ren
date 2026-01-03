# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 基本原则

- 用中文对话
- 用最简单的方法完成任务
- 不要创建新文件，除非明确要求
- 不要生成新的 md 文档，除非我告诉你需要；所有新增 md 文档放在 `./doc`
- 所有测试相关文件放在 `./test`

## 项目定位

**本项目现为面向 Web 的数字人生成系统**

- 主程序 = `frontend/` Web 界面 + `ad-back.py`/`py/` 后端 API，统一 orchestrate WaveSpeedAI 数字人链路（详见 `doc/数字人.md`）。
- 仍保留 `ad-aka.py` 作为历史脚本参考，但任何上线逻辑必须以后端 API 为准；如需复用算法请抽象至 `py/services/`。

## 项目概述

**Digital Human Studio**：用户在浏览器输入提示词/脚本 → 后端串行执行“形象 → 语音 → 唇同步” → 返回可播放的视频 URL。

- 核心 API：`bytedance/seedream-v4`（头像）、`minimax/speech-02-hd`（语音）、`wavespeed-ai/infinitetalk`（唇同步）。
- 技术栈：Python 3.10+（Flask/FastAPI）、前端可采用 Vite + Vue/React 或纯静态页面，Nginx 将 `ren.linapp.fun` 反向代理至本地 `0.0.0.0:18005`。
- 提供 REST 接口：`POST /api/tasks` 创建任务、`GET /api/tasks/<id>` 查询状态、`POST /api/assets/upload` 上传头像等。

## 常用命令

```bash
# 激活虚拟环境并安装依赖
source venv/bin/activate
pip install -r requirements.txt

# 启动/重启后端（默认监听 18005）
python3 ad-back.py --port 18005
# 或使用 restart 脚本（自动加载 .env、优雅重启 uvicorn）
./restart_api_server.sh

# 前端开发
cd frontend && npm install && npm run dev

# WaveSpeed API 连通性 / 冒烟
python3 py/test_network.py --digital-human
./test/smoke_digital_human.sh        # 10 秒冒烟，输出到 output/smoke/aka-*

# 统一测试（CI 同步）
PYTEST_WAVESPEED_MOCK=1 ./run_tests.sh
```

## 配置层级

- `.env`：存放 `WAVESPEED_API_KEY`、`MINIMAX_API_KEY`、对象存储凭证等敏感信息，不提交；可提供 `.env.example`。
- `config.yaml`：全局参数（并发、重试、静态资源目录、Nginx 端口映射、调试模式）。
- `user.yaml`：仅本地调试时使用，预填默认头像/语音；线上请求通过前端传参。
- `doc/数字人.md`：数字人 API 协议的唯一来源，新增字段/模型前必须更新此文档。

## 项目结构

```
wavespeed/
├── frontend/            # Web UI，负责任务创建/状态轮询/播放
├── ad-back.py           # 后端入口，监听 18005
├── py/
│   ├── api/             # REST 路由、任务控制器
│   ├── function/        # 配置、上下文、步骤调度
│   ├── services/        # WaveSpeed API 客户端、存储、队列
│   ├── py1/             # 工具脚本
│   └── test_network.py  # 连通性检测
├── doc/                 # 设计/接口文档（含 数字人.md）
├── output/              # 任务资产（avatar/speech/video/log）
├── resource/            # 静态资源
├── test/                # 自动化测试
├── README.md
└── requirements.txt
```

## 数字人服务脚本

- `py/services/digital_human_service.py`（或等效模块）：封装 Seedream/Minimax/Infinitetalk 请求，提供 trace id、重试策略。
- `py/services/storage_service.py`：生成的视频上传到对象存储或 `output/`，返回可公网访问的 URL。
- `py/api/routes_digital_human.py`：REST API 入口，处理任务生命周期。
- `music/` 下历史 BGM 工具可选对接，为数字人视频添加背景音乐。

## 数字人生成流程

1. **阶段0 前端交互**
   - 用户填写 `avatar_mode`（上传/Prompt）、文本脚本、语音参数、分辨率。
   - 前端 POST `/api/tasks`，后端写入 `task.json`（含 `trace_id/config_hash`）并持久化任务。
2. **阶段1 形象生成**
   - 上传头像直接落盘 `output/<job_id>/avatar.png`；Prompt 模式调用 `bytedance/seedream-v4`，记录成本。
3. **阶段2 语音生成**
   - 调用 `minimax/speech-02-hd` 生成音频，落盘 `speech.mp3`，记录时长与成本。
4. **阶段3 唇同步**
   - 调 `wavespeed-ai/infinitetalk`（或 MultiTalk）并轮询 `/api/v3/predictions/<id>`，生成 `digital_human.mp4`。
5. **阶段4 发布**
   - 使用 `storage_service.publish_video()` 将视频复制到 `/mnt/www/ren/ren_MMDDHHMM/` 并返回外链；`task.json` 与 `log.txt` 同步更新，前端轮询到 `finished`。

## 关键设计模式

- **错误处理**：所有外部 API 抛 `ExternalAPIError`，附带 provider/status/trace_id；FastAPI 中统一注册 exception handler，将 `trace_id` 返回给前端对话框与日志。
- **重试策略**：默认 3 次指数退避（5s/10s/15s）；429 或 5xx 必须重试，客户端可在响应体中看到详细日志，`output/<job_id>/log.txt` 要完整记录。
- **任务状态机**：`pending → avatar_generating → avatar_ready → speech_generating → speech_ready → video_rendering → finished/failed`；服务重启后可继续，且会校验 `config_hash`。
- **并发控制**：Seedream <=2 并发，Infinitetalk 串行（<=1 QPS）；必要时通过信号量或调度器限制。

## 配置说明

### 环境变量示例

```env
WAVESPEED_API_KEY=your_wavespeed_key
MINIMAX_API_KEY=your_minimax_key
STORAGE_BUCKET=s.linapp.fun/background
NGINX_SERVER=ren.linapp.fun
```

### 用户参数（前端传递）

- `avatar_mode` (`upload/prompt`), `avatar_prompt` 或上传文件 URL
- `speech_text`, `voice_id`, `speed`, `pitch`, `emotion`, `english_normalization`
- `resolution` (720p/1080p), `seed`, `mask_image`
- 自定义水印/字幕开关（可复用原 `services/subtitle_service`）

### 输出结构

```
output/aka-{task_id}/
├── avatar.png
├── speech.mp3
├── digital_human.mp4
├── task.json
└── log.txt
```

## API 集成（依据 `doc/数字人.md`）

- **Seedream v4**
  - `POST https://api.wavespeed.ai/api/v3/bytedance/seedream-v4`
  - 参数：`prompt`, `negative_prompt`, `width`, `height`, `num_inference_steps`, `guidance_scale`
- **MiniMax speech-02-hd**
  - `POST https://api.wavespeed.ai/api/v3/minimax/speech-02-hd`
  - 参数：`text`, `voice_id`, `speed`, `pitch`, `emotion`, `sample_rate`, `channel`
- **Infinitetalk**
  - `POST https://api.wavespeed.ai/api/v3/wavespeed-ai/infinitetalk`
  - 轮询 `GET https://api.wavespeed.ai/api/v3/tasks/{task_id}`
  - 参数：`image_url`, `audio_url`, `mask_image`, `prompt`, `seed`

## 成本估算

| 服务 | 估算成本 |
|------|---------|
| Seedream 头像 | $0.02–0.05/张 |
| MiniMax 语音 | $0.01–0.03/分钟 |
| Infinitetalk 唇同步 | $0.10–0.20/分钟 |

单条 60 秒数字人视频 ≈ $0.13–0.28。调试时建议语音 < 10 秒，成本 < $0.05。

## 开发注意事项

1. **Nginx**：`ren.linapp.fun` 必须代理到 `127.0.0.1:18005`；`/` 提供前端静态资源，`/api/` 设置 `proxy_read_timeout 120s`。
2. **安全**：前端不得暴露 API Key；上传头像需校验文件类型、大小并落在受控目录或 OSS。
3. **日志**：每个任务写入 `log.txt`，包含外部 task_id，方便追踪。
4. **对象存储**：生成结果建议同步到 `https://s.linapp.fun/...`，返回可直接播放的 URL。
5. **兼容历史模块**：保留原有日志、限流、音乐服务；但所有新增逻辑以数字人业务为优先。

## 测试最佳实践

1. **Mock 测试**：`PYTEST_WAVESPEED_MOCK=1 pytest test/test-digital-human.py`，验证状态机与 API 返回。
2. **真实冒烟**：准备 8–10 秒脚本，运行 `python3 py/test_network.py --digital-human`；确认 Seedream/Minimax/Infinitetalk 均能返回 URL。
3. **前后端联调**：`npm run dev` + `python3 ad-back.py --port 18005`，通过浏览器创建任务并验证播放。
4. **部署验证**：上线后访问 `https://ren.linapp.fun/api/health`，确保 Nginx + 后端正常；生成一条 10 秒视频确认 CDN URL 可访问。
