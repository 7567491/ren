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
```

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
```

脚本会在 `frontend/` 下自动安装依赖（`npm ci`/`npm install`）并执行 `npm run build`，随后激活虚拟环境运行 `pytest`。如需传递额外 pytest 选项，可直接追加在命令末尾（例如 `./run_tests.sh -k digital_human`）。

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
2. **前端**：`npm run build` 后将 `frontend/dist` 发布到 `/var/www/wave-frontend`。
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

---

## 💰 成本与测试

| 服务 | 估算成本 |
|------|---------|
| Seedream 头像 | \$0.02–\$0.05 / 张 |
| MiniMax 语音 | \$0.01–\$0.03 / 分钟 |
| Infinitetalk 唇同步 | \$0.10–\$0.20 / 分钟 |

- **冒烟测试**：10 秒脚本 ≈ \$0.02（语音） + \$0.03（唇同步） ≈ \$0.05。
- `python3 py/test_network.py --digital-human` 会依次测试三阶段 API。
- `PYTEST_WAVESPEED_MOCK=1 pytest test/test-digital-human.py` 可在无真实调用下验证任务状态机。

---

## 📚 相关文档

- `doc/数字人.md`：WaveSpeed 数字人 API 指南（头像/语音/唇同步）。
- `AGENTS.md`：仓库协作规范。
- `CLAUDE.md`：面向 Claude Code 的开发说明。
- `doc/部署配置.md`（如有）：补充部署细节、对象存储策略。

如需新增数字人模板、语音模型或多角色逻辑，请先更新 `doc/数字人.md` 并在 README 中同步说明，然后再提交代码。欢迎针对前端体验、后端稳定性提出改进建议。🎬

---

## 🎨 前端界面设计

### 页面概览

**页面名称**：数字人生成工作室
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
