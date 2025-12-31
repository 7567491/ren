# Repository Guidelines

中文对话

## 项目定位
- 本仓库现为**数字人生成 Web 项目**，前端负责配置、头像上传与播放展示，后端聚焦编排数字人三阶段（形象→语音→唇形）生成。
- 所有数字人生成能力以 `doc/数字人.md` 的 WaveSpeedAI API 规范为准：Seedream 图像、MiniMax 语音、Infinitetalk 唇同步等模型需在 `py/services/` 中封装为可复用客户端。
- 继承原故事化视频工程的日志、配置与限流体系，确保新功能沿用既有 `py/function/`、`py/api/` 的架构与异常处理模式。

## 目录与模块
- **前端 (`frontend/`)**：基于 Vite + Vue 3 的 SPA（`src/App.vue`），`npm run build` 输出 `frontend/dist/`，`config.js` 启动时自动推导 `API_BASE`；负责提示词/脚本/角色参数输入与任务轮询、播放器/下载交互。
- **后端 (`ad-back.py` + `py/`)**：保留 Flask/FastAPI 结构，新增 `digital_human` 相关蓝图，暴露任务编排、任务状态查询与素材上传 API。端口固定 **18005** (供 `ren.linapp.fun` Nginx 反代)。
- **配置**：`.env` 存放 WaveSpeed API Key 等敏感信息；`config.yaml` 负责任务超时、并发、静态资源目录；`user.yaml` 仅保留示例参数。
- **文档**：除 `README.md` 以外的新增文档只放在 `doc/`，测试说明集中在 `test/`；`doc/design.md` 为唯一权威架构文档，历史 `doc/plan.md` 已下线，新的进度说明请写入 `doc/工作流.md`。

## 开发与测试
- Python 3.10+ 且遵循 PEP 8，组件之间优先通过服务层交互（例如 `services/digital_human_service.py`）。前端保持 ESLint/Prettier 默认配置，提交前运行 `npm run build`（如适用）。
- 常用命令：
  - `source venv/bin/activate && pip install -r requirements.txt`
  - `python3 ad-back.py --port 18005` 或 `restart_api_server.sh`（自动加载 `.env` 并重启 uvicorn）
  - `npm install && npm run dev`（位于 `frontend/`）
- `python3 py/test_network.py --digital-human` 或 `test/smoke_digital_human.sh`（10 秒冒烟，输出到 `output/smoke/aka-*`）
- 提交前默认运行 `PYTEST_WAVESPEED_MOCK=1 ./run_tests.sh`（聚合 `npm run build` + `pytest`）；CI/预提交可直接调用 `./ci.sh` 以保持一致。
- 后端涉及付费 API 的联调需使用最短文本、低分辨率头像以控制成本；本地调试优先使用 mock，并记录 `trace_id` + 成本至 `test/test-digital-human.md`。
- `TaskResponse.assets.local_video_url` 必须指向 `/output/<job_id>/digital_human.mp4`，前端会优先使用该本地域名播放/下载；若返回 CDN URL 需放在 `video_url` 备用。

## 部署与安全
- Nginx 需将 `ren.linapp.fun` 的 HTTPS 流量转发到 `127.0.0.1:18005`，并开启 `/api/` 的超时 120s 以容纳视频合成轮询。
- 同步部署 `frontend/dist` 到 Nginx 根目录，`client_max_body_size 200m` 以便上传头像/脚本，并通过 `location /output/ { alias /home/ren/output/; }` 公开任务产物；其余未命中路由需回退到 `index.html`。
- `.env` 永不提交；若需要演示配置，提供 `.env.example` 并写明需要的 Key：`WAVESPEED_API_KEY`、`MINIMAX_KEY` 等。
- 静态文件（例如生成后的数字人片段）统一放到 `output/` 子目录或对象存储挂载点，Git 忽略。

## 代码与提交流程
- 提交信息使用祈使句（如 “add digital human service client”），一次提交聚焦单变更。
- PR 说明需覆盖：数字人 API 调用更改、前后端交互协议、测试命令（含 mock/真实调用）、可能成本。
- 引入新第三方库时同步更新 `requirements.txt` 或前端 `package.json`，并在 README 记录用途。

## 质量保障
- 关键路径必须有最小化端到端验证：调用接口生成 1 段短语音 + 5-10 秒唇同步视频；通过 `test/test-digital-human.md` 记录命令、job_id、trace_id、cost。
- 继续沿用原项目日志与重试策略，任何调用 WaveSpeed API 的地方默认 3 次指数退避重试并输出 trace id；`output/<job_id>/log.txt` 必须保持 `[ISO][LEVEL][trace=xxx] message` 结构。
