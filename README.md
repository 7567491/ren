# 数字人生成 Web 项目

基于 WaveSpeedAI API 的全流程数字人生成与播放平台：前端负责配置与预览，后端协同 WaveSpeedAI 完成“形象 → 语音 → 唇同步”流水线。域名 `ren.linapp.fun` 通过 Nginx 反代后端 `:18005`，整体架构延续原故事化视频系统的配置/日志/限流体系。

> ✅ 数字人能力规范请参考 `doc/数字人.md`，所有接口、模型与示例都以该文档为准。

---

## 🔑 核心特性
- **Web 低门槛**：在浏览器内输入提示词/脚本、上传头像或选择模板，即可生成数字人视频。
- **三阶段流水线**：自动串联 Seedream 头像、MiniMax 语音、Infinitetalk 唇同步，支持双角色扩展。
- **任务状态轮询**：前端轮询 `GET /api/tasks/<id>`，实时展示头像、语音、视频的进度与日志。
- **成本可控**：默认调试模式限制 10 秒语音，<5 美分即可完成冒烟；生产模式支持 1 分钟以上视频。
- **可扩展架构**：保留原 `py/services/`、`py/function/` 模块划分，便于复用日志、重试、限流等基础设施。

---

## 🧱 架构概览

```
Browser (frontend/)  ──HTTPS──>  Nginx (ren.linapp.fun)
                                   ├── /  -> frontend/dist 静态资源
                                   └── /api -> 127.0.0.1:18005 (ad-back.py)

ad-back.py
  ├─ py/api/routes_digital_human.py     REST API
  ├─ py/services/digital_human_service  WaveSpeed API 封装
  ├─ py/services/storage_service        生成资产存储
  └─ py/function/*                      任务状态机、配置、日志
```

---

## 🎭 角色库（Character Library）

- **存储**：预制人物素材位于 `resource/pic/*.jpg` + `.json`，可通过 `python3 py/scripts/migrate_characters.py` 生成统一的 `resource/characters/prebuilt.json`。用户上传的角色写入 `resource/characters/user_defined.json`，图片保存在 `character_library.storage_dir`（生产建议 `/mnt/www/ren/resource/pic/user/`，本地自动回落到 `./resource/pic/user/`，已加入 `.gitignore`）。
- **配置**：`config.yaml` 新增 `character_library` 段，可配置 `storage_dir / uploads_subdir / public_base_url` 等，也支持 `CHARACTER_STORAGE_DIR`、`CHARACTER_PUBLIC_BASE_URL` 环境变量覆盖。默认 `public_base_url=/api/characters/assets`，由 FastAPI 直接回源图片文件；如需走 CDN，可自行设置完整的 CDN URL。
- **API**：
  - `GET /api/characters`：返回预制+用户角色，包含 `appearance/voice/tags/image_url`。
  - `POST /api/characters`：`multipart/form-data` 上传图片（PNG/JPG，≤10MB）及名称/描述，返回 `character_id`。
  - `PUT /api/characters/{id}`：更新描述或重传头像；`DELETE` 将角色标记为 `disabled`。
- **任务集成**：`POST /api/tasks` 新增 `character_id` 参数。后端会自动拼接角色的中文/英文外观描述、推荐音色 ID，并在上传模式下复用角色头像。`task.json` 与 `output/<job_id>/log.txt` 均会记录 `assets.character`，日志行形如 `🎭 使用角色 暗影玫瑰 (char-scalet)`，方便追溯。
- **前端体验**：`frontend/src/App.vue` 展示角色卡片（可刷新），并提供“上传新人物”折叠面板。选择角色后无需再上传头像即可创建任务，同时会自动切换至推荐音色。

---

## 📁 目录结构

```
frontend/        # Web UI，负责任务创建、轮询与播放器
ad-back.py       # 后端主入口（Flask/FastAPI），监听 0.0.0.0:18005
py/
  ├── api/       # REST 路由、鉴权、中间件
  ├── function/  # 配置解析、任务上下文、流水线步骤
  ├── services/  # WaveSpeed API 客户端、存储/BGM/字幕等
  └── test_network.py
doc/
  ├── 数字人.md  # WaveSpeed 数字人 API 指南（唯一权威）
  └── ...
output/aka-*/    # 任务资产：avatar.png、speech.mp3、digital_human.mp4、task.json、log.txt
output/smoke/    # 冒烟脚本产物（结构与正式任务一致，可定期清理）
```

> `output/` 已在 `.gitignore` 中排除，可按 `test/test-digital-human.md` 的脚本定期清理历史任务，仅保留最近一次冒烟记录。

---

## ⚙️ 快速开始

```bash
# 1. 后端依赖
cd /home/ren
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 复制并填写密钥
cp .env.example .env
# 编辑 .env，填入 `WAVESPEED_API_KEY`、`MINIMAX_API_KEY`、`STORAGE_BUCKET_URL` 等必填字段

# 3. 启动后端（默认 0.0.0.0:18005，可用 --debug reload）
python3 ad-back.py --port 18005 --debug

# 4. 前端开发/打包
cd frontend
npm install
npm run dev          # 开发模式
npm run build        # 打包 -> frontend/dist
```

测试 WaveSpeed API：

```bash
python3 py/test_network.py --digital-human
```

## ✅ 本地构建与测试

项目提供 `run_tests.sh` 统一执行前端打包与 Python 测试：

```bash
PYTEST_WAVESPEED_MOCK=1 ./run_tests.sh
# CI/CD 可直接调用
./ci.sh
```

脚本会在 `frontend/` 下自动安装依赖（`npm ci`/`npm install`）并执行 `npm run build`，随后激活虚拟环境运行 `pytest`。如需传递额外 pytest 选项，可直接追加在命令末尾（例如 `./run_tests.sh -k digital_human`）。

### 冒烟脚本

真实联调可直接运行封装好的冒烟脚本（默认 10 秒文案，成本 < \$0.1）：

```bash
./test/smoke_digital_human.sh
# 或者传入其他参数
SMOKE_TEXT="欢迎体验数字人" ./test/smoke_digital_human.sh --resolution 1080p
```

脚本会调用 `python3 py/test_network.py --digital-human`，并将头像/语音/视频与 `task.json`、`log.txt` 写入 `output/smoke/aka-test-*/`。日志采用 `[timestamp][LEVEL][trace=xxx] message` 结构，可直接用于 WaveSpeed 工单排障。更详细的验证步骤见 `test/test-digital-human.md`。

---

## 🔧 配置说明

### `.env` 示例
```env
WAVESPEED_API_KEY=your_wavespeed_key
MINIMAX_API_KEY=your_minimax_key
STORAGE_BUCKET_URL=https://s.linapp.fun/digital-human
DEBUG_MODE=true
```

> `.env` 仅存放密钥/敏感参数，切勿提交；可参照仓库根目录的 `.env.example` 快速复制模版。`ad-back.py` 启动时会验证上述键是否存在，缺失时会给出错误提示。

### `config.yaml`
- `server.port`: 默认为 18005，可覆盖命令行参数
- `storage.output_dir`: 本地输出目录（默认 `output/`）
- `tasks.max_avatar_workers`: Seedream 并发数量
- `tasks.retry`: 重试次数、指数退避间隔
- `frontend.public_url`: Nginx 暴露的地址（`https://ren.linapp.fun`）

### `user.yaml`
- 提供本地调试默认的 `avatar_prompt`、`speech_text` 等，可快速进行冒烟测试。

---

## 🛠️ 数字人生成流程

| 阶段 | 描述 | 关键实现 |
|------|------|----------|
| 0. 任务创建 | 前端提交 `avatar_mode`、脚本、语音参数、分辨率 | `POST /api/tasks` |
| 1. 形象生成 | 上传头像或调用 `bytedance/seedream-v4` 生成 1024x1024 肖像 | `services/digital_human_service.generate_avatar` |
| 2. 语音生成 | 调 `minimax/speech-02-hd` 生成音频，可调速/情绪/音调 | `generate_voice` |
| 3. 唇同步 | 调 `wavespeed-ai/infinitetalk`（或 multi）并轮询任务 | `animate_avatar` |
| 4. 发布 | 将视频上传至 `output/`/OSS，更新任务状态，前端轮询到 `finished` | `storage_service.persist_result` |

所有 API 调用遵循 `doc/数字人.md` 的示例与参数说明。

---

## 🧭 仪表盘使用指南

1. **API Key 卡片**：输入 Wavespeed Key，点击 👁️ 切换明文/密文，💾 保存到 localStorage，✖️ 清除。右下角“刷新余额”会调用 `/api/wavespeed/balance` 并覆盖 Pinia Store。
2. **任务管理卡片**：上半区列出历史任务，可直接切换/移除，并附有“刷新”“暂停轮询”按钮。下半区是任务创建表单（头像模式、播报文本、高级参数、调试模式），校验错误都会在卡片内提示。
3. **任务进度卡片**：顶部显示任务 ID 与聚合进度条，三段管线按照 20%/30%/50% 权重显示头像、语音、视频阶段，颜色/emoji 显示状态。卡片尾部是播放器和下载/复制操作。
4. **素材目录卡片**：展示 `/mnt/www/ren/<job_id>/` 目录映射，输出 avatar/audio/video/log 条目，默认同时显示本地路径与公网 URL 并附带复制/打开按钮。

> 移动端默认只展开前两张卡片，可根据优先级逐一展开，其状态与桌面端共享。

## 🔌 API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST /api/tasks` | 创建数字人任务，返回 `task_id` |
| `GET /api/tasks/<task_id>` | 查询任务状态、头像/语音/视频 URL、日志 |
| `POST /api/assets/upload` | 可选：上传自定义头像或字幕文件 |
| `GET /api/health` | 健康检查 |

响应中的 `status` 至少包含：`pending`, `avatar_ready`, `speech_ready`, `video_rendering`, `finished`, `failed`。失败时返回 `error_code` 与 WaveSpeed trace id。

---

## 🌐 部署与 Nginx

1. **后端**：以 systemd 方式运行 `python3 ad-back.py --port 18005`。
2. **前端**：`npm run build` 后将 `frontend/dist` 发布到站点根目录（如 `/var/www/wave-frontend` 或 `/home/ren/frontend/dist`）。
3. **Nginx 示例 (`ren.linapp.fun`)**

```nginx
server {
    listen 80;
    listen 443 ssl;
    server_name ren.linapp.fun;

    root /var/www/wave-frontend;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:18005/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }

    location / {
        try_files $uri /index.html;
    }
}
```

> HTTPS 证书可使用 Certbot；需要更长的代理超时时间，以容纳唇同步轮询。
> `ren2.linapp.fun` 使用同样的反代规则，直接挂载 `frontend/dist` 静态页并使用 `*.linapp.fun` 证书，详见 `doc/nginx-ren2.linapp.fun.md`。

---

## 💰 成本与测试

| 服务 | 估算成本 |
|------|---------|
| Seedream 头像 | \$0.02–\$0.05 / 张 |
| MiniMax 语音 | \$0.01–\$0.03 / 分钟 |
| Infinitetalk 唇同步 | \$0.10–\$0.20 / 分钟 |

- **冒烟测试**：10 秒脚本 ≈ \$0.02（语音） + \$0.03（唇同步） ≈ \$0.05。
- `./test/smoke_digital_human.sh` 自动执行真实冒烟，结果写入 `output/smoke/aka-test-*/log.txt`。
- `python3 py/test_network.py --digital-human` 会依次测试三阶段 API。
- `PYTEST_WAVESPEED_MOCK=1 pytest test/test-digital-human.py` 可在无真实调用下验证任务状态机。

---

## 📚 相关文档

- `doc/数字人.md`：WaveSpeed 数字人 API 指南（头像/语音/唇同步）。
- `AGENTS.md`：仓库协作规范。
- `CLAUDE.md`：面向 Claude Code 的开发说明。
- `test/test-digital-human.md`：端到端冒烟与日志核查指引。
- `doc/ops_manual.md`：运维手册（扩容、排障、清理、冒烟记录）。
- `doc/部署配置.md`（如有）：补充部署细节、对象存储策略。

如需新增数字人模板、语音模型或多角色逻辑，请先更新 `doc/数字人.md` 并在 README 中同步说明，然后再提交代码。欢迎针对前端体验、后端稳定性提出改进建议。🎬

---

## 🎨 前端界面设计

### 页面概览

**页面名称**：数字人空间
**访问地址**：`https://ren.linapp.fun/`

### 核心功能

#### 1. 用户输入

**头像模式选择**
- Prompt 生成模式：输入文本描述生成头像
- 上传模式：上传自己的头像图片（PNG/JPG，最大 5MB）

**播报文本**
- 多行文本输入
- 实时字数统计
- 预估时长和成本

**音色选择**
- `female-shaonv` - 女声-少女
- `female-yujie` - 女声-御姐
- `male-qn-qingse` - 男声-青涩
- `male-qn-jingying` - 男声-精英

**高级选项**（折叠面板）
- 分辨率：720p / 1080p
- 语速：0.5 - 2.0
- 音调：-12 ~ 12
- 情绪：neutral / happy / sad / angry
- 随机种子、蒙版图片等
- 上传体验：集成 FilePond（含类型/大小校验与预览）

#### 2. 进度显示

三阶段状态展示：
```
⏳ 头像生成  →  ⏳ 语音生成  →  ⏳ 唇同步视频
```

状态图标：
- ⏳ 待处理 (pending)
- ⚙️ 进行中 (in-progress)
- ✅ 已完成 (done)
- ❌ 失败 (failed)

#### 3. 结果展示

- video.js 播放器（视频）+ 浏览器原生音频
- 成本信息展示
- 下载按钮和分享链接

### 界面布局

详细的界面设计和交互流程请参考 `doc/前端设计.md`。

### 前端技术栈

- 纯 HTML + CSS + JavaScript（或可选 Vue.js/React）
- 响应式设计（支持移动端）
- 轮询机制实现任务状态更新

### API 交互示例

```javascript
// 创建任务
const response = await fetch('/api/tasks', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    avatar_mode: "prompt",
    avatar_prompt: "一位专业的女性播音员，微笑，正面照",
    speech_text: "大家好，欢迎收看今天的节目",
    voice_id: "female-shaonv",
    resolution: "720p"
  })
});

// 轮询状态
const pollTaskStatus = async (jobId) => {
  const interval = setInterval(async () => {
    const task = await fetch(`/api/tasks/${jobId}`).then(r => r.json());

    if (task.status === 'finished' || task.status === 'failed') {
      clearInterval(interval);
    }
  }, 2000);
};
```
