# 方案A（前端单页 + 轻量后端API）设计稿

## 目标与约束
- 后端核心逻辑保持不变：`ad-aka.py` 原地保留，复制为 `ad-back.py` 供 API 子进程调用。
- 输出/中间文件命名与目录兼容：继续使用 `output/aka-*`、原日志/素材/成品命名；不新增不兼容的路径规则。
- 无鉴权、无 S3：结果直接返回本地文件路径（如需要可映射静态 URL）；前端/接口全部 JSON。
- 不改写生成流程与断点续传行为，`--resume/--no-auto-resume` 等参数语义不变。

## 目录规划
- `py/ad-aka.py`：旧入口，保持可独立 CLI 使用。
- `py/ad-back.py`：`ad-aka.py` 的拷贝/薄封装，接受 CLI/JSON 参数，写入原有输出目录与日志。
- `py/api_server.py`：极简 REST API（FastAPI/Flask 皆可），负责参数校验、任务入队、调用 `ad-back.py` 子进程、读取状态/日志。
- `py/services/task_manager.py`（可选）：内存 + JSON/SQLite 持久化的任务表，文件放 `temp/` 不影响原输出命名。
- `frontend/`（可选）：单文件或简易 SPA，表单 + 状态 + 日志滚动，纯 JSON 轮询。

## 后端执行流程
1. `POST /api/jobs`：接收 `preset_name` 或 `user_yaml` 文本，生成 `job_id`（沿用 `aka-YYYYMMDD-xxx`），写任务表 `queued`。
2. 后台线程/进程池启动命令：`python3 py/ad-back.py --resume {job_id}`（或 `--no-auto-resume`），把参数写入 `temp/user-{job_id}.yaml` 供脚本按原逻辑读取。
3. 子进程 stdout/stderr 重定向到 `output/aka-{job_id}/log.txt`（保持原格式）；实时 tail 更新任务表 `status/progress/message`。
4. 结束时读取原生成的最终视频（如 `final_video.mp4`），记录 `result_path`；失败则标记 `failed` 并保留日志。

## API（JSON）
- `POST /api/jobs` → `{job_id, status:"queued"}`；请求体：`preset_name?`, `user_yaml?`, `resume_id?`, `no_auto_resume?`, 可选分辨率/镜头数等。
- `GET /api/jobs/{id}` → `{status, message, progress, result_path?}`，`status ∈ {queued,running,succeeded,failed}`。
- `GET /api/jobs/{id}/log` → `{lines:["..."], eof:bool}`，支持 `lines`/`offset`，直接读取 `output/aka-{id}/log.txt`。
- `GET /api/jobs/{id}/result` → `{result_path}`（本地路径或静态映射）。
- `GET /api/presets`（可选）→ 列出可用模板供前端选择。

## 状态与存储
- 任务表：内存 dict + `temp/jobs.json`/SQLite 持久化，字段 `{job_id,status,message,progress,result_path,log_path,created_at}`。
- 参数文件：`temp/user-{job_id}.yaml`；可选择保留以支持 resume；命名与现有逻辑兼容。
- 日志：沿用 `output/aka-*` 原文件，API 仅做 tail，不改变格式。

## 并发与队列
- 线程/进程池限制同时运行的 `ad-back.py` 数量（默认 1，可从配置读取但不影响原参数）。
- 简单 FIFO 队列；失败不自动重试，依赖日志人工排查。

## 前端交互（单页）
- 纯 HTML/JS，表单提交 `POST /api/jobs`；轮询 `GET /api/jobs/{id}` 和 `/log`；所有状态/日志均为 JSON。
- 展示字段：`status`、`progress`、`message`、`result_path`；日志区域滚动显示最新若干行。

## 验证与运行
- 启动 API：`uvicorn py.api_server:app --host 0.0.0.0 --port 8000`（激活 venv 后）。
- 最小化验证：3 镜头 + 480p，调用 `POST /api/jobs`，轮询至完成，确认 `result_path` 指向 `output/aka-*` 下的成品；检查日志无异常堆栈。
