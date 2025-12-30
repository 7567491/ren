# 数字人项目开发进度（唯一记录）

> 本文原合并 `ren.md`、`TDD_plan.md`、`TDD_PROGRESS.md`、`TDD开发总结.md` 等分散记录，现作为数字人项目的**唯一开发进度与待办追踪文件**。若需查看任何阶段状态、测试统计或待办事项，请以此文档为准。

- **最后更新**: 2025-12-30
- **负责范围**: 前端 `frontend/ren.html`、后端 `ad-back.py` + `py/`、WaveSpeed API 编排
- **当前版本**: v0.5（阶段 3 进行中）

---

## 状态概览

| 阶段 | 说明 | 状态 |
|------|------|------|
| 阶段 0 | 环境准备（依赖、预算、密钥） | ✅ 完成 |
| 阶段 1 | 核心服务实现（Seedream/MiniMax/Infinitetalk + API） | ✅ 完成 |
| 阶段 2 | 前端适配（`ren.html` UI、交互、静态部署） | ✅ 完成 |
| 阶段 3 | 测试、部署与运维（端到端冒烟、Nginx/systemd、监控） | ⏳ 进行中 |

- 后端 `DigitalHumanService`、`routes_digital_human.py`、MiniMax/InfiniteTalk 客户端已落地，任务 API 可创建/查询/上传素材。
- `frontend/ren.html` 已支持头像上传/Prompt、参数配置、三阶段进度 UI、成本估算、调试模式与错误弹层。
- 仍需完成任务状态机落地、后端重试/日志、端到端冒烟与部署文档更新。

---

## 关键成果

### 后端与服务
- ✅ `py/services/minimax_tts_service.py`：封装 MiniMax speech-02-hd，含参数验证、音频下载、成本追踪。
- ✅ `py/function/media_clients.py`：扩展 InfiniteTalkClient + MiniMax 集成，统一 `ExternalAPIError`（含 provider/status/trace）。
- ✅ `py/services/digital_human_service.py`：完成“头像→语音→唇同步”编排逻辑，产物落盘到 `output/aka-*`。
- ✅ `py/api/routes_digital_human.py`：`POST /api/tasks`、`GET /api/tasks/<id>`、`POST /api/assets/upload`、`GET /api/health`。

### 前端（`frontend/ren.html`）
- 🎨 单页 UI（渐变主题、移动端适配），支持 Prompt/Upload 模式切换。
- 🧾 表单字段齐备：提示词、脚本、音色、分辨率、语速/音调/情绪，高级选项可折叠。
- 🧪 调试模式：前端限制文案长度，提示成本与调试说明，提交时附带 `debug_mode`。
- 🔁 轮询面板：三阶段状态、任务 ID、状态消息、实时成本预估。
- ⚠️ 错误弹层：展示 `error_code`、`trace_id`，上方表单提示集中。
- 🎬 结果卡片：播放器 + 成本 + 下载/复制链接动作。

---

## 测试与质量

| 模块 | 测试文件 | 用例数 | 状态 |
|------|----------|--------|------|
| InfiniteTalkClient | `test/test_infinitetalk_client.py` | 11 | ✅ 通过（真实 API 1 个跳过） |
| MiniMaxTTSService | `test/test_minimax_tts_service.py` | 20 | ✅ 通过（真实 API 1 个跳过） |
| DigitalHumanService | `test/test_digital_human_service.py` | 7 | ✅ 通过 |
| API 路由 | `test/test_routes_digital_human.py` | 11 | ✅ 通过 |
| **合计** |  | **49**（含 2 个跳过） | ✅

- `PYTEST_WAVESPEED_MOCK=1` 已提供本地 mock，可在无真实 API key 下跑通测试。
- 待补：`py/test_network.py --digital-human` 真实链路验证、10s 冒烟脚本、CI 中增加 `npm run build` + `pytest`。

---

## 待办重点（阶段 3）
1. **任务状态机与存储**：实现 `task_runner` 各阶段、指数退避重试、结构化日志、存储/OSS 上传。
2. **API & 配置治理**：`.env` 校验、`config_loader` 扩展、`requirements.txt` 精简、`ad-back.py` argparse。
3. **前端补完**：任务轮询、进度面板细节、构建脚本/CI、`frontend/package.json` 整理。
4. **部署与文档**：Nginx/systemd 样例、`doc/部署配置.md`/`workflow.md` 更新、运维手册、最终回归测试。

---

## 详细任务看板
> ⚙️ 以下看板保留原 plan 清单，按领域重新分组；方括号即实时状态。

### 前端
- [x] 起草前端任务流原型图（表单、轮询、播放器），确认交互步骤（详见 `doc/frontend_task_flow.md`）  
- [x] 在 `frontend/` 创建基础 Vite/Vue 项目结构并配置汉化支持（Vite+Vue3+i18n，详见 `frontend/src/`）  
- [x] 实现前端表单字段：avatar_mode、avatar_prompt、speech_text、voice_id、speed、pitch、emotion、resolution、seed（Vite 版 `src/App.vue`）  
- [x] 前端表单增加 Debug 模式开关与字段校验提示  
- [x] 前端集成头像上传组件，支持预览与大小/格式校验（Vite 版 `src/App.vue`）  
- [x] 前端表单提交逻辑对接 `POST /api/tasks`，展示 task_id  
- [x] 编写前端任务状态轮询器，使用可配置间隔查询 `GET /api/tasks/<id>`（`useAppConfig` + 轮询封装，见 `src/App.vue`）  
- [x] 前端实现进度面板，按照 avatar/speech/video 阶段显示状态、错误与重试建议  
- [x] 前端播放器卡片展示 avatar 预览、speech 音频播放、最终视频播放（Vite 版 `src/App.vue`）  
- [x] 在 `frontend/` 添加成本估算显示组件，读取 API 返回的 cost_estimate  
- [x] 前端实现错误提示弹层，包含 trace_id 与错误码  
- [x] 为前端添加环境变量支持（API_BASE、POLL_INTERVAL 等）  
- [x] 完成前端构建脚本与 `npm run build` CI 检查（`run_tests.sh` 统一执行 npm build + pytest）  
- [x] 审核 `frontend/package.json`，移除无关依赖并添加播放器/上传组件（引入 FilePond + video.js）  

### 后端 / API / 状态机
- [x] 在 `ad-back.py` 接入 argparse，支持 `--port` `--config` `--debug`（根目录 `ad-back.py` CLI，调用 FastAPI）  
- [x] 加载 `.env` 并验证 `WAVESPEED_API_KEY`、`MINIMAX_API_KEY`、`STORAGE_BUCKET_URL` 必填（`ad-back.py` 调用 `py.function.env_loader.ensure_required_env`）  
- [ ] 初始化 Flask/FastAPI 应用，挂载日志与请求 trace 中间件  
- [ ] 创建 `py/api/routes_digital_human.py` 蓝图，注册到主应用  
- [ ] 定义 `POST /api/tasks` 请求模型（Pydantic/attrs），校验字段范围  
- [ ] `POST /api/tasks` 写入任务初始记录 `task.json` 并返回 task_id 与轮询 URL  
- [ ] 定义 `GET /api/tasks/<task_id>` 响应模型，聚合状态、资产 URL、成本、日志  
- [ ] 实现 `POST /api/assets/upload` 上传接口，校验文件类型并返回访问 URL  
- [ ] 提供 `GET /api/health` 健康检查，输出版本信息与外部 API 可用性  
- [ ] 在 `py/function/` 下创建 `task_runner.py`，负责调度任务状态机  
- [ ] 设计任务状态枚举与允许的状态转换表（pending→avatar_generating→…）  
- [ ] 在 `task_runner` 中创建 `TaskContext` 对象，封装 config、路径、logger、trace  
- [ ] 实现 `task_runner.run_step_avatar()`：上传或调用 Seedream 生成头像并写入 `task.json`  
- [ ] 实现 `task_runner.run_step_speech()`：调用 MiniMax 生成音频并保存 `speech.mp3`  
- [ ] 实现 `task_runner.run_step_video()`：调用 Infinitetalk/Multitalk，轮询直到完成并保存视频  
- [ ] 编写 `task_runner.update_state()` 帮助方法，统一写 `task.json` 和日志  
- [ ] 支持 Debug 模式（限制语音长度、提示成本）与生产模式的切换（后端治理）  

### 服务层与基础设施
- [x] 在 `py/services/minimax_tts_service.py` 实现 MiniMax TTS 服务（含测试）  
- [x] 在 `py/function/media_clients.py` 封装 MiniMax TTS 客户端集成  
- [x] 在 `py/function/media_clients.py` 实现 InfiniteTalk 客户端（含测试）  
- [x] 统一实现 ExternalAPIError，携带 `provider`, `status_code`, `trace_id`  
- [x] 在服务层加入指数退避重试（5s/10s/15s）与超时配置（MiniMaxTTSService 增加 `_with_retry`）  
- [ ] 在 `py/services/storage_service.py` 实现本地输出目录创建与 URL 生成（产物写入 `/mnt/www/ren/ren_MMDDHHMM/digital_human.mp4`）  
- [ ] storage 服务支持将结果推送到对象存储（若配置了 bucket，默认公开 URL `https://s.linapp.fun/ren/...`）  
- [x] 在 `py/function/config_loader.py` 新增字段以解析 `frontend.public_url`、并发限制、重试策略（`config.yaml` 扩展 + `LoadedConfig.frontend/workflow.retry`）  
- [ ] 任务创建时校验配置哈希，与 `task.json` 中记录的哈希一致性  
- [ ] 在 `py/api` 增加全局异常处理，将 ExternalAPIError 转换为统一 JSON 错误响应  
- [ ] 引入结构化日志（logger + trace_id），所有阶段写入 `output/aka-*/log.txt`  
- [ ] 在 `py/test_network.py` 添加 `--digital-human` 选项，依次调用三阶段 API 验证  

### 测试 / 文档 / 运维
- [x] 编写 `test/test-digital-human.py`，使用 mock 验证状态机流转与 API 响应  
- [x] 提供 `PYTEST_WAVESPEED_MOCK=1` 环境变量控制测试走假数据  
- [ ] 编写冒烟脚本（10s 文案）运行完整流程并记录成本  
- [ ] 更新 `README.md` 的“快速开始/架构/部署”章节引用最新流程  
- [ ] 在 `AGENTS.md` 和 `CLAUDE.md` 中确保与 design.md 的架构一致（已完成但需复核）  
- [ ] 在 `doc/md/design.md` 中补充迭代变更日志（v3.0）  
- [ ] 根据设计撰写 `doc/部署配置.md` 更新：Nginx 示例、systemd 服务、前端部署路径  
- [ ] 在 `doc/workflow.md` 补充数字人任务状态机与轮询时序图  
- [ ] 为 `output/` 新结构编写 `.gitignore` 与清理脚本说明  
- [ ] 编写 `restart_api_server.sh` 更新流程，确保加载新环境变量  
- [ ] 整理 `requirements.txt`：移除 DeepSeek/EdgeTTS 依赖，新增所需库（requests、FastAPI、pydantic、boto3 等）  
- [ ] 为关键服务添加类型注解与 docstring，便于 IDE 与审查  
- [ ] 在 CI/预提交脚本中加入 `npm run build` 与 `pytest` 步骤  
- [ ] 撰写运维手册：如何扩容任务、排查 WaveSpeed API 429/500  
- [ ] 规划后续增强任务（多角色对话、字幕/水印、BGM），整理进入 backlog  
- [ ] 最终回归测试：在 `ren.linapp.fun` 上生成 1 条 10 秒视频并验证播放/日志/成本  

---

## 备注
- `frontend/ren.html` 的设计细节原记于 `ren.md`，现统一搬迁到“关键成果/前端”与上述看板。
- 若需要补充新任务，请直接在本文件“详细任务看板”相应区域添加。
- 删除的旧文档：`TDD_plan.md`、`TDD_PROGRESS.md`、`TDD开发总结.md`；历史版本可在 Git 历史中查阅。
