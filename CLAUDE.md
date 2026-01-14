# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 基本原则

- 用中文对话
- 用最简单的方法完成任务
- 不要创建新文件，除非明确要求
- 不要生成新的 md 文档，除非我告诉你需要；所有新增 md 文档放在 `./doc`
- 所有测试相关文件放在 `./test`

## 项目定位

**面向 Web 的数字人生成系统 (Digital Human Studio)**

- 主架构：`frontend/dist/index.html` (单页静态 HTML) + `py/api_server.py` (FastAPI)
- 三阶段流水线：形象生成 → 语音合成 → 唇同步视频
- 部署：Nginx (`ren.linapp.fun`) → `127.0.0.1:18005`
- 历史脚本 `ad-aka.py` 仅供参考，新功能必须通过 API 实现
- **前端架构**：使用单个 HTML 文件（无构建步骤），包含所有 CSS 和 JavaScript

## 核心架构

### 模块调用链

```
前端 (Vue) → Nginx → FastAPI (py/api_server.py)
                        ↓
              routes_digital_human.py (REST API 层)
                        ↓
              task_runner.py (状态机 + 任务调度)
                        ↓
              digital_human_service.py (三阶段编排)
                        ↓
         ┌──────────────┼──────────────┐
         ↓              ↓              ↓
   Seedream API   MiniMax TTS   Infinitetalk API
   (形象生成)      (语音合成)      (唇同步)
```

### 任务状态机

**完整状态流转**：
```
pending → avatar_generating → avatar_ready →
speech_generating → speech_ready → video_rendering →
finished / failed
```

- 状态管理：`py/function/task_runner.py`
- 持久化：`output/aka-<task_id>/task.json`
- 状态查询：`GET /api/tasks/<task_id>`

### 关键技术决策

1. **服务入口**：使用 `py.api_server:app` 作为 uvicorn 入口，`ad-back.py` 仅作 CLI 启动器
2. **输出目录**：
   - 本地：`output/aka-<task_id>/` (avatar.png, speech.mp3, digital_human.mp4, task.json, log.txt)
   - 公网：复制到 `/mnt/www/ren/ren_MMDDHHMM/` 供 CDN 访问
3. **角色库**：`py/services/character_repository.py` 管理预制角色，前端通过 `character_id` 参数复用形象和音色
4. **并发控制**：Seedream ≤2 并发，Infinitetalk 串行 (≤1 QPS)
5. **错误处理**：统一抛 `ExternalAPIError`，包含 provider/status/trace_id，前端可追溯

## 常用命令

### 后端开发

```bash
# 激活虚拟环境并安装依赖
source venv/bin/activate
pip install -r requirements.txt

# 启动后端（开发模式，自动重载）
python3 ad-back.py --port 18005 --debug

# 生产模式启动（优雅重启，自动加载 .env）
./restart_api_server.sh

# 查看 API 日志
tail -f logs/api-server.log

# 停止后端服务
pkill -f "py.api_server:app"
# 或强制停止
pkill -9 -f "py.api_server:app"

# 健康检查
curl http://localhost:18005/api/health
```

### 前端开发

```bash
# 前端为单个静态 HTML 文件，无需构建步骤
# 直接编辑文件：frontend/dist/index.html

# 前端文件位置
ls -la /home/ren/frontend/dist/index.html

# Vue 旧架构已归档到
ls -la /home/ren/frontend-vue-archive/
```

### 测试

```bash
# 运行后端测试
source venv/bin/activate
pytest

# 运行特定测试文件
pytest test/test_digital_human_storage_flow.py

# 运行特定测试函数
pytest test/test_infinitetalk_client.py::test_submit_task -v

# WaveSpeed API 连通性测试
python3 py/test_network.py --digital-human

# 真实冒烟测试（10秒脚本，<$0.1成本）
./test/smoke_digital_human.sh
```

### 调试与运维

```bash
# 查看任务状态
cat output/aka-<task_id>/task.json | python3 -m json.tool

# 查看任务日志
cat output/aka-<task_id>/log.txt

# 查看最近的任务
ls -lt output/ | head -10

# 清理测试输出
rm -rf output/smoke/

# 检查进程
ps aux | grep -E "(uvicorn|api_server)"

# 检查端口占用
sudo netstat -tlnp | grep 18005
# 或使用 lsof
sudo lsof -i :18005
```

## 配置层级

### 环境变量优先级

`.env` > 命令行参数 > `config.yaml` 默认值

### 配置文件说明

| 文件 | 用途 | 是否提交 | 关键字段 |
|------|------|---------|---------|
| `.env` | 敏感信息（API Keys、凭证） | ❌ 不提交 | `WAVESPEED_API_KEY`, `MINIMAX_API_KEY`, `STORAGE_BUCKET_URL` |
| `config.yaml` | 全局参数（并发、重试、目录） | ✅ 提交 | `tasks.max_avatar_workers`, `tasks.retry`, `storage.output_dir` |
| `user.yaml` | 本地调试默认值（可选） | ❌ 不提交 | `avatar_prompt`, `speech_text`, `voice_id` |
| `doc/数字人.md` | WaveSpeed API 协议规范 | ✅ 提交 | API 端点、参数、示例代码 |

**重要**：新增 API 字段或模型前，必须先更新 `doc/数字人.md`

## 项目结构

```
/home/ren/
├── frontend/                    # 前端静态文件
│   └── dist/
│       ├── index.html          # 单页应用（包含所有 CSS/JS）
│       ├── config.js           # 配置文件
│       ├── favicon.svg         # 网站图标
│       └── preset-topics.json  # 预设主题
│
├── frontend-vue-archive/       # Vue 旧架构归档（已废弃）
│   ├── src/                    # Vue 源代码
│   ├── node_modules/           # npm 依赖
│   └── package.json            # 依赖配置
│
├── py/
│   ├── api_server.py           # FastAPI 应用入口 (uvicorn 启动)
│   ├── api/
│   │   └── routes_digital_human.py  # REST API 路由
│   ├── function/
│   │   ├── task_runner.py      # 任务状态机与调度
│   │   ├── infinitetalk_client.py  # Infinitetalk 客户端
│   │   ├── config_loader.py    # 配置解析
│   │   └── env_loader.py       # 环境变量加载
│   ├── services/
│   │   ├── digital_human_service.py  # 三阶段编排
│   │   ├── minimax_tts_service.py    # MiniMax TTS 客户端
│   │   ├── storage_service.py        # 资产存储与发布
│   │   └── character_repository.py   # 角色库管理
│   ├── exceptions/
│   │   └── external_api_error.py     # 统一异常类
│   └── test_network.py         # API 连通性测试
│
├── test/                       # 自动化测试
│   ├── smoke_digital_human.sh  # 冒烟测试脚本
│   └── test_*.py               # pytest 测试用例
│
├── output/                     # 任务输出（不提交）
│   └── aka-<task_id>/
│       ├── avatar.png
│       ├── speech.mp3
│       ├── digital_human.mp4
│       ├── task.json           # 状态、配置、成本
│       └── log.txt             # 任务日志
│
├── doc/                        # 设计文档
│   ├── 数字人.md               # WaveSpeed API 协议（权威）
│   ├── design.md               # 架构设计
│   └── *.md                    # 其他文档
│
├── ad-back.py                  # CLI 启动器（加载 .env 并启动 uvicorn）
├── restart_api_server.sh       # 生产重启脚本
├── run_tests.sh                # CI 测试脚本
├── .env                        # 敏感配置（不提交）
├── config.yaml                 # 全局配置
└── requirements.txt            # Python 依赖
```

## 数字人生成流程

### 五阶段流水线

| 阶段 | 描述 | 关键模块 | 输出 |
|------|------|----------|------|
| 0. 创建 | 前端提交配置，后端初始化任务 | `routes_digital_human.py` | `task.json` (状态: pending) |
| 1. 形象 | 上传头像或 Seedream 生成 | `digital_human_service.generate_avatar()` | `avatar.png` (状态: avatar_ready) |
| 2. 语音 | MiniMax TTS 生成音频 | `minimax_tts_service.py` | `speech.mp3` (状态: speech_ready) |
| 3. 唇同步 | Infinitetalk 合成视频 | `infinitetalk_client.py` | `digital_human.mp4` (状态: video_rendering) |
| 4. 发布 | 复制到公网目录 | `storage_service.publish_video()` | CDN URL (状态: finished) |

### 关键设计模式

**错误处理**
- 统一异常类：`py/exceptions/external_api_error.py`
- 包含字段：`provider`, `status_code`, `trace_id`, `error_message`
- FastAPI 全局 handler：自动将异常转为 JSON 响应

**重试策略**
- 默认配置：3 次重试，指数退避 (5s → 10s → 15s)
- 可重试错误：429 (限流)、5xx (服务器错误)
- 不重试错误：4xx (参数错误)
- 日志记录：每次重试写入 `output/<job_id>/log.txt`

**任务恢复**
- 服务重启后，通过 `task.json` 中的状态和 `config_hash` 判断是否可继续
- 已完成的阶段不会重复执行（通过检查 avatar.png/speech.mp3 文件存在性）

## API 接口

### 对外 REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST /api/tasks` | 创建数字人任务 | 返回 `task_id` 和轮询链接 |
| `GET /api/tasks/<task_id>` | 查询任务状态 | 返回状态、URLs、成本、日志 |
| `POST /api/assets/upload` | 上传头像/素材 | 返回临时 URL (5MB 限制) |
| `GET /api/characters` | 获取角色库 | 返回预制和用户角色列表 |
| `POST /api/characters` | 创建新角色 | 上传头像和描述 |
| `GET /api/health` | 健康检查 | 返回服务状态和 API 可用性 |

### WaveSpeed API 集成

详见 `doc/数字人.md`，关键端点：

- **Seedream v4**: `POST https://api.wavespeed.ai/api/v3/bytedance/seedream-v4`
- **MiniMax TTS**: `POST https://api.wavespeed.ai/api/v3/minimax/speech-02-hd`
- **Infinitetalk**: `POST https://api.wavespeed.ai/api/v3/wavespeed-ai/infinitetalk`
- **任务查询**: `GET https://api.wavespeed.ai/api/v3/tasks/{task_id}`

## 成本估算

| 服务 | 估算成本 | 备注 |
|------|---------|------|
| Seedream 头像 | $0.02–0.05/张 | 1024x1024 图像 |
| MiniMax 语音 | $0.01–0.03/分钟 | speech-02-hd 模型 |
| Infinitetalk 唇同步 | $0.10–0.20/分钟 | 720p/1080p |

**测试建议**：调试时使用 10 秒脚本，总成本 < $0.05

## 前端架构说明

### 当前架构：单页静态 HTML

**文件位置**：`/home/ren/frontend/dist/index.html`

**特点**：
- ✅ 无需构建步骤，直接编辑 HTML 文件即可
- ✅ 所有 CSS 和 JavaScript 内联在单个文件中
- ✅ 包含 API Key 输入、余额查询、任务创建等完整功能
- ✅ 使用 localStorage 持久化存储用户的 API Key
- ✅ 响应式设计，支持移动端

**主要功能模块**：
1. **API 配置面板**：输入 Wavespeed API Key、查询余额
2. **形象准备**：上传头像或输入提示词
3. **脚本与音色**：输入播报文本、选择音色和分辨率
4. **任务监控**：实时轮询任务状态、显示生成进度
5. **历史记录**：查看历史生成的视频

**修改前端**：
```bash
# 直接编辑 HTML 文件
vim /home/ren/frontend/dist/index.html

# 修改后刷新浏览器即可（无需重启服务）
```

### 旧架构归档（Vue 3 + Vite）

**归档位置**：`/home/ren/frontend-vue-archive/`

**包含内容**：
- `src/` - Vue 3 组件和源代码
- `node_modules/` - npm 依赖包
- `package.json` - 依赖配置
- `vite.config.ts` - Vite 构建配置
- `tsconfig*.json` - TypeScript 配置

**注意**：Vue 架构已废弃，不再维护。如需参考可查看归档目录。

---

## 开发注意事项

### 安全

- ✅ **API Key 由用户输入**：前端要求用户在浏览器中输入自己的 Wavespeed API Key
- ✅ **localStorage 存储**：API Key 保存在用户浏览器的 localStorage，不上传到服务器
- ✅ **请求时传递**：每次创建任务时，API Key 通过 POST 请求传递给后端
- ✅ **后端不存储**：后端仅在请求期间使用 API Key，不持久化存储
- ✅ 上传文件需校验类型 (PNG/JPG) 和大小 (≤5MB)
- ✅ 使用 ACL 控制用户目录权限（`setfacl` 设置 ccp/ren 共享）

### 日志规范

- 格式：`[ISO时间][级别][trace=xxx] 消息`
- 位置：`output/<job_id>/log.txt` + `logs/api-server.log`
- 包含：外部 task_id、WaveSpeed trace_id、成本累计

### Nginx 配置要点

- 反代：`/api/` → `http://127.0.0.1:18005`
- 超时：`proxy_read_timeout 120s` (唇同步轮询需要)
- 静态：`/` → `frontend/dist`
- 资产：`/output/` → `alias /home/ren/output/`

### 部署检查清单

- [ ] `.env` 配置了 `STORAGE_BUCKET_URL` 等必需配置（不再需要 API Keys）
- [ ] `frontend/dist/index.html` 存在并可访问
- [ ] 后端进程运行在 18005 端口
- [ ] 访问 `/api/health` 返回 200
- [ ] 前端输入 Wavespeed API Key 并查询余额成功
- [ ] 创建测试任务能正常完成三阶段流程
- [ ] 生成的视频 URL 可在浏览器播放
