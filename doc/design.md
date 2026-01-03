# 数字人生成 Web 项目设计文档 v3.0

> **最后更新**：2025-12-31  
> **作者**：Claude Opus 4.5 / WaveSpeed 团队  
> **适用范围**：`frontend/`、`ad-back.py`、`py/`、Nginx @ `ren.linapp.fun`  
> **状态**：设计签核通过，阶段 3 实施中

---

## 0. 背景与声明

### 0.1 项目定位
- **当前线上形态**：故事化广告视频引擎（8 阶段流水线，依赖 DeepSeek/Kimi、Runway、Edge TTS、MoviePy 等）。
- **目标形态**：数字人生成 Web 项目（头像→语音→唇同步 3 阶段），以 `doc/数字人.md` 中 WaveSpeed API 规范为唯一契约。
- **迁移策略**：沿用日志、配置、限流体系；数字人相关代码新增于 `py/api`、`py/function/task_runner.py`、`py/services/`，不破坏旧故事生产链路。

### 0.2 当前系统 vs 目标系统对比

| 维度 | 现状（故事视频） | 目标（数字人） | 说明 |
|------|-----------------|----------------|------|
| 业务流程 | 8 阶段（脚本→镜头→图像→视频→配音→字幕→音乐→合成） | 3 阶段（头像→语音→唇同步） | 需新状态机 |
| 前端 | `frontend/index.html`，字段 `topic/preset_name/num_shots` | 数字人 UI（头像模式、语音脚本、音色参数） | 需重写 |
| 后端入口 | `api_server.py` + CLI `ad-back.py` | FastAPI 蓝图 `digital_human` + 任务调度器 | 需扩展 |
| API | `POST /api/jobs` | `POST /api/tasks`、`GET /api/tasks/<id>`、`POST /api/assets/upload` | 需新增 |
| 语音 | Edge TTS（免费） | MiniMax speech-02-hd（付费） | 需新服务 |
| 视频 | Runway/Minimax 场景视频 | Infinitetalk/MultiTalk 唇同步 | 需新客户端 |
| 成本 | $0.1-1 / 视频 | $0.60-0.72 /10s，$3.64+ /60s | 成本显著上升 |
| 输出 | `output/aka-*/90_final.mp4` | `output/aka-*/{avatar,speech,digital_human}.` | 需新结构 |

> **本文目标**：给出数字人架构、接口、任务流与实施计划，帮助团队从故事引擎平滑迁移到数字人系统。

---

## 1. 现有方案问题与结论

1. 业务目标错位：旧文档聚焦故事视频，缺失数字人所需的 Web 前端、任务状态 API、Nginx 反代说明。
2. API 过时：继续引用 DeepSeek/Edge TTS，多镜头 I2V，与 `doc/数字人.md` 的 WaveSpeed 规范不符。
3. 数据结构不符：仍强调 `story_outline.json / shots_script.json`，没有 `avatar.png / speech.mp3 / digital_human.mp4 / task.json`。
4. 缺少错误处理与成本策略：未描述任务状态机、重试策略、调试模式、成本估算。
5. 缺少部署指引：未给出 18005 端口、Nginx 转发、静态部署位置。

> **结论**：必须以数字人三阶段流程为主线重新设计，并在实施阶段逐步落地状态机、服务封装与部署脚本。

---

## 2. 设计目标

1. **Web 低门槛**：浏览器填写提示词/脚本 → 后端 orchestrate WaveSpeed API → 返回可访问的视频 URL。
2. **极简 Hero + 三栏布局**：首屏只保留一句价值主张与「开始创建」按钮，下方固定左中右三栏（密钥与任务 / 输入素材 / 输出过程）确保信息分区明确。
3. **三阶段流水线**：头像（Seedream/上传）→ 语音（MiniMax）→ 唇同步（Infinitetalk/MultiTalk）。
4. **任务可观测性**：提供任务状态轮询、阶段日志、成本估算、 trace id。
5. **安全与成本控制**：密钥置于 `.env`，调试模式限制 10 秒语音，默认重试 3 次指数退避。
6. **部署一体化**：Nginx 提供 HTTPS 与静态资源，后端监听 `0.0.0.0:18005`，域名 `ren.linapp.fun` 通过 `/api/` 反代。

---

## 3. 总体架构

```
Browser (frontend/) ──HTTPS──> Nginx (ren.linapp.fun)
                               ├─ /          -> frontend/dist
                               └─ /api       -> 127.0.0.1:18005

ad-back.py / api_server.py (FastAPI)
 ├─ py/api/routes_digital_human.py      REST 接口
 ├─ py/function/task_runner.py          状态机 & 调度
 ├─ py/services/digital_human_service   WaveSpeed API 封装
 ├─ py/services/storage_service         输出资产 & CDN
 └─ py/services/logging/retry/...       公共基础设施
```

依赖：`doc/数字人.md`（API 契约）、`config.yaml`（并发/重试/输出）、`.env`（密钥）、`frontend/`。

---

## 4. 模块设计

### 4.1 前端 `frontend/`
- **Hero 极简化**：首屏 Hero 仅包含一句价值主张（“10 秒配置，即刻生成数字人”）、副标题（说明成本/时长）与主按钮（`开始创建`）。Hero 下沿接三栏布局的顶端，视觉上通过浅色背景与 16px 投影过渡，保证用户视线迅速落到工作区域。
- **三栏布局骨架**：Hero 之后的主内容由一个 12 列 CSS Grid 划分成 3:5:4 的三栏。布局固定，可在窄屏降级为纵向折叠。三栏的语义如下：
  - **左栏（系统栏）**：集中所有和账户/任务相关的控件：
    - API Key 模块：输入框 + “校验”按钮 + 状态徽章（`未配置/有效/过期`），说明所需 Key（WaveSpeed、MiniMax），旁边提供 `.env.example` 下载链接。
    - 任务管理：列出最近 5 个 `task_id`，展示状态、耗时、成本；支持“新标签页打开 / 复制 Trace ID / 停止任务”操作，并在顶部提供筛选（全部/进行中/失败）。
    - 全局设置：限流策略、调试模式开关（提示 10 秒语音限制）放在此处，避免干扰输入栏。
  - **中栏（输入栏）**：承载所有创造性输入与素材上传：
    - 将字段拆为“形象配置”“语音脚本”“高级参数”三折叠面板，默认展开前两块。字段包含 `avatar_mode/avatar_prompt`、上传头像（FilePond + 5MB 校验）、`speech_text`、`voice{voice_id,speed,pitch,emotion}`、`resolution`、`seed`、`debug_mode`、`mask_image`。
    - 在折叠标题上显示推荐值与剩余字数/体积，减少用户在多字段中迷失。
    - 素材区展示最近上传的头像、脚本模板，支持一键复用，所有上传通过 `POST /api/assets/upload`，结果回填在当前面板中。
  - **右栏（输出栏）**：聚焦任务执行状态与结果资产：
    - 顶部是“Avatar → Speech → Video”水平时间条，节点展示状态、耗时、trace id。节点下方同步成本小计。
    - 中段为日志摘要（最近 5 条）与“展开全部日志”按钮；展开后在抽屉内加载完整日志。
    - 底部为播放器卡片（video.js），主按钮默认播放 `/output/<job_id>/digital_human.mp4`，旁边文字链接提示“备用 CDN”。同一卡片包含音频试听、下载按钮，以及任务完成后的分享链接。
- **交互与技术栈**：
  - Vite + Vue 3（`frontend/src/App.vue`）渲染整页，`npm run build` 输出到 `frontend/dist/`。
  - 页面初始化时加载 `frontend/dist/config.js` 动态推导 `API_BASE`，并通过 `window.__APP_CONFIG__` 设置轮询间隔、列宽断点。
  - 使用 Vue 状态管理（Pinia）集中管理任务列表与当前任务，以便左栏与右栏共享状态。
  - `POST /api/tasks` 创建任务，轮询 `GET /api/tasks/<id>` 更新右栏；若任务在左栏切换即停止当前轮询并加载新任务。
  - 上传组件沿用 FilePond，校验 5MB PNG/JPG 并在上传后生成缩略图展示于中栏素材区；播放器依旧依赖 video.js。
  - SPA 回退：未知路由回退到 `index.html`；资源优先使用 `assets.local_video_url`，失败后右栏提示自动切换 CDN。

### 4.2 后端入口 `ad-back.py`
- CLI 参数：`--port`、`--config`、`--debug`，默认端口 `18005`。
- 加载 `.env`、`config.yaml`；注册 FastAPI app、日志中间件、trace id。
- 将 `/api` 路由注册至 `py/api/`，复用原日志/限流设施。

### 4.3 API 层 `py/api/`
- `routes_digital_human.py`：`POST /api/tasks`、`GET /api/tasks/<task_id>`、`POST /api/assets/upload`、`GET /api/health`。
- 使用 Pydantic 校验请求/响应，统一 JSON 错误格式，透出 `trace_id`、`error_code`。
- 通过 `task_runner` 触发后台执行，并返回 `task_id` 与轮询链接。

### 4.4 状态机 `py/function/task_runner.py`
- 状态流：`pending → avatar_generating → avatar_ready → speech_ready → video_rendering → finished/failed`。
- 维护 `task.json`，记录配置、阶段状态、WaveSpeed task_id、成本、时间戳。
- 控制并发（Seedream <=2、MiniMax <=2、Infinitetalk 单线程），支持调试模式（10 秒语音上限）。
- 每个阶段调用 `digital_human_service`，并写 `output/aka-*/log.txt`。

### 4.5 服务层 `py/services/`
- `digital_human_service.py`：封装完整三阶段流程，统一重试与成本累积。
- `minimax_tts_service.py`：Speech-02-hd 客户端，支持语速/音调/情绪、自带音频下载。
- `media_clients.py`：`InfiniteTalkClient` 与 Seedream 客户端，复用轮询机制。
- `storage_service.py`：本地输出 + `/mnt/www/ren/ren_{MMDDHHMM}/digital_human.mp4` + 可选对象存储。
- `env_loader`, `config_loader`: 校验环境变量、解析端口/并发/重试等。

### 4.6 配置与敏感信息
- `.env`：`WAVESPEED_API_KEY`、`MINIMAX_API_KEY`、`STORAGE_BUCKET_URL`、`DEBUG_MODE`；提供 `.env.example`。
- `config.yaml`：任务超时、并发、前端 public_url、输出目录；`user.yaml` 仅留示例参数。

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

- 生成完成后复制到 `/mnt/www/ren/ren_{MMDDHHMM}/digital_human.mp4`，供 `https://s.linapp.fun/ren/...` 访问，同时通过 Nginx `alias /home/ren/output/` 暴露 `/output/<job_id>/digital_human.mp4` 以便本地播放/下载。
- `task.json` 记录阶段状态、WaveSpeed task_id、成本、时间戳、配置哈希；`TaskResponse.assets.local_video_url` 恒指向 `/output/<job_id>/digital_human.mp4`。

---

## 6. 工作流（阶段）

1. **阶段 0：任务创建** —— 前端提交配置，后端写入 `task.json`、初始化状态并返回 `task_id`。
2. **阶段 1：形象生成** —— `avatar_mode=upload` 直接存储；`prompt` 模式调用 Seedream v4，存储并回填 URL。
3. **阶段 2：语音生成** —— 调用 MiniMax speech-02-hd，写入 `speech.mp3`，记录时长与成本。
4. **阶段 3：唇同步视频** —— 调 Infinitetalk，轮询 `/api/v3/predictions/<id>/result`，直至完成；下载视频并落盘。
5. **阶段 4：发布** —— 上传/复制最终视频，更新 `task.json`、成本、日志，通知前端。

---

## 7. API 契约

### POST `/api/tasks`
请求示例：
```json
{
  "avatar_mode": "prompt",
  "avatar_prompt": "25岁职业女性，正面微笑",
  "speech_text": "大家好...",
  "voice": {"voice_id": "Wise_Woman", "speed": 1.0, "emotion": "neutral"},
  "resolution": "720p",
  "seed": 42,
  "debug_mode": true
}
```
响应示例：
```json
{
  "task_id": "aka-123456",
  "status": "pending",
  "links": {"poll": "/api/tasks/aka-123456"}
}
```

### GET `/api/tasks/<task_id>`
```json
{
  "task_id": "aka-123456",
  "status": "speech_ready",
  "avatar_url": "https://...",
  "audio_url": "https://...",
  "video_url": null,
  "assets": {
    "local_video_url": "/output/aka-123456/digital_human.mp4"
  },
  "stages": {"avatar": {...}, "speech": {...}, "video": {...}},
  "cost_estimate_usd": 0.045,
  "trace_id": "req-789",
  "logs": ["2025-12-30 13:30 avatar ready", "..."]
}
```

### POST `/api/assets/upload`
- 用于前端上传头像或字幕，返回临时 URL（限制 5MB PNG/JPG）。

### GET `/api/health`
- 返回版本信息、WaveSpeed API 网络可用性、密钥加载状态。

---

## 8. 错误处理与重试
- `digital_human_service` 统一抛 `ExternalAPIError(provider,status_code,trace_id)`，API 层转为 HTTP JSON。
- 重试策略：指数退避 5s/10s/15s，共 3 次；超过次数即失败并记录。
- 网络/限流错误会自动重试，参数错误直接失败。
- 每阶段写入 trace id、WaveSpeed task id，便于与官方支持对接。

---

## 9. 部署拓扑

1. 后端：`source venv/bin/activate && python3 ad-back.py --port 18005 --config config.yaml`。
2. 前端：`npm run build` → 部署 `frontend/dist`。
3. Nginx：`ren.linapp.fun` 代理 `/api/` → `127.0.0.1:18005`，`proxy_read_timeout 120s`。
4. systemd：`restart_api_server.sh` 负责拉起后端并加载新环境变量。

示例 Nginx：
```nginx
server {
    listen 80;
    server_name ren.linapp.fun;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ren.linapp.fun;

    ssl_certificate /etc/letsencrypt/live/linapp.fun/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/linapp.fun/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    client_max_body_size 200m;
    root /home/ren/frontend/dist;
    index index.html;

    access_log /var/log/nginx/ren.linapp.fun.access.log;
    error_log /var/log/nginx/ren.linapp.fun.error.log;

    location /api/ {
        proxy_pass http://127.0.0.1:18005;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_connect_timeout 15s;
        proxy_buffering off;
    }

    location /output/ {
        alias /home/ren/output/;
        add_header Access-Control-Allow-Origin *;
        try_files $uri $uri/ =404;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 10. 实施路线图

### 阶段 0：前期准备（2h）
- [ ] 备份现有项目、创建 `digital-human` 分支。
- [ ] 更新 `requirements.txt`、准备 `WAVESPEED_API_KEY`、`MINIMAX_API_KEY`。
- [ ] 预估真实 API 成本预算（$50+）。

### 阶段 1：核心服务实现（20h）
1. **Infinitetalk 客户端**（5h） —— 在 `py/function/media_clients.py` 新增 `InfiniteTalkClient`，支持提交/轮询/下载/成本计算并附单测。
2. **MiniMax TTS 服务**（3h） —— 在 `py/services/minimax_tts_service.py` 新建客户端，参数校验、音频下载、成本追踪。
3. **数字人服务编排**（8h） —— `py/services/digital_human_service.py` 完成三阶段 orchestration、状态记录、成本统计。
4. **数字人 API 路由**（4h） —— `py/api/routes_digital_human.py` 定义 `POST/GET /api/tasks`、`assets/upload`，集成到 FastAPI。

### 阶段 2：前端适配（10h）
- 重写 `frontend/`（Vite + Vue 单页应用）界面，支持 Prompt/Upload、调试模式、三阶段进度展示、成本显示、播放器。
- 轮询 `GET /api/tasks/<id>`，同步阶段 icon、错误弹层；更新构建脚本，`run_tests.sh` 统一执行 `npm run build` + `pytest`。

### 阶段 3：测试与部署（10-15h）
- 单元测试：`test/test_infinitetalk_client.py`、`test/test_minimax_tts_service.py`、`test/test_digital_human_service.py`，支持 `PYTEST_WAVESPEED_MOCK=1`。
- 集成测试：`py/test_network.py --digital-human` 串联真实 API；记录 10s 冒烟脚本与成本数据。
- 部署验证：Nginx/systemd 配置、`restart_api_server.sh`，最终在 `ren.linapp.fun` 生成 10 秒视频并校验链接。

---

## 11. 成本对比

| 系统 | 10 秒视频 | 60 秒视频 | 备注 |
|------|-----------|-----------|------|
| 故事视频现状 | $0.1-0.5 | $0.5-1.5 | Edge TTS 免费、MoviePy 合成 |
| 数字人方案 | $0.60-0.72 | $3.64-4.32 | Seedream + MiniMax + Infinitetalk |

数字人成本拆分（60 秒）：
```
Seedream 头像：$0.02-0.05
MiniMax TTS：  $0.02
Infinitetalk： $3.60（720p，$0.06/秒）
---------------------------------
合计：        $3.64 以上
```

---

## 12. 附录

- 现有故事系统优势：成熟脚本/镜头生成、智能音乐匹配、低成本产出；短期内可与数字人并行提供不同能力。
- 参考文档：`doc/数字人.md`（API 规范）、`doc/frontend_task_flow.md`、`doc/wave-ren.md`、`doc/部署配置.md`（需更新）。
- 术语：`task_id` 与旧 `aka-*` 命名兼容；`output/aka-*` 目录保留用于断点续传。
