 [x] 创建目录：`py/api`、`py/function`、`py/function/steps` 空目录与 `__init__.py`。
 [x] 新建入口文件 `py/ad.py`（async 入口占位）。
 [x] 创建 `py/api/__init__.py` 占位。
 [x] 创建 `py/api/workflow.py` 空类占位。
 [x] 创建 `py/function/__init__.py` 占位。
 [x] 创建 `py/function/config_loader.py` 占位。
 [x] 创建 `py/function/logger.py` 占位。
 [x] 创建 `py/function/context.py` 占位。
 [x] 创建 `py/function/rate_limit.py` 占位。
 [x] 创建 `py/function/storage.py` 占位。
 [x] 创建 `py/function/llm_client.py` 占位。
 [x] 创建 `py/function/media_clients.py` 占位。
 [x] 创建 `py/function/pipeline.py` 占位。
 [x] 创建 `py/function/cli.py` 占位。
 [x] 在 `py/function/steps` 下创建 `__init__.py`。
 [x] 在 `py/function/steps` 创建 `script.py` 占位。
 [x] 在 `py/function/steps` 创建 `shots.py` 占位。
 [x] 在 `py/function/steps` 创建 `images.py` 占位。
 [x] 在 `py/function/steps` 创建 `videos.py` 占位。
 [x] 在 `py/function/steps` 创建 `voice.py` 占位。
 [x] 在 `py/function/steps` 创建 `subtitle.py` 占位。
 [x] 在 `py/function/steps` 创建 `music.py` 占位。
 [x] 在 `py/function/steps` 创建 `compose.py` 占位。
 [x] ad-aka 兼容层：修改 `py/ad-aka.py` 增加迁移提示与调用新入口。
 [x] config_loader：加载 `.env`、`config.yaml`、`user.yaml`。
 [x] config_loader：合并配置，按 user 覆盖 config。
 [x] config_loader：数字映射（style/resolution/voice/bool 等）构建。
 [x] config_loader：模型/并发/限流配置解析。
 [x] config_loader：校验必填项（visual_styles/camera_movements/prompt_templates）。
 [x] config_loader：输出结构化 Config 对象。
 [x] logger：实现颜色化控制台与文件双写。
 [x] logger：实现去色工具（strip ANSI）。
 [x] logger：支持日志路径在 RunContext 中注入。
 [x] context：定义 RunContext（session_id、config、work_dir、logger、state、assets）。
 [x] context：生成 session_id、初始化工作目录、日志文件路径。
 [x] context：初始化 state 容器（可序列化）。
 [x] rate_limit：协程安全计数器，支持 max/minute/day；提供 async context manager。
 [x] storage：创建输出/缓存目录（output_base/session_id）。
 [x] storage：state.json 读写（load_state/save_state）。
 [x] storage：config 哈希记录，用于 resume 校验。
 [x] llm_client：封装 LLM 请求（async），支持 provider/headers/timeout。
 [x] llm_client：提示模板填充工具，缺失变量报错。
 [x] media_clients：适配 VoiceService（同步→异步包装）。
 [x] media_clients：适配 SubtitleService（同步→异步包装）。
 [x] media_clients：适配 MusicService（选择/匹配）。
 [x] media_clients：适配 VideoComposer（合成）。
 [x] media_clients：图像/视频生成 HTTP 调用与轮询封装。
 [x] steps.script：调用 llm_client 生成脚本/镜头概要，写 ctx.state。
 [x] steps.shots：根据概要分镜，运镜分配，写 ctx.state。
 [x] steps.images：并发生成图像（含 prompt 扩展），写路径到 ctx.state。
 [x] steps.videos：并发生成视频（i2v/t2v），写路径到 ctx.state。
 [x] steps.voice：生成旁白音频，写 ctx.state。
 [x] steps.subtitle：生成字幕时间轴与文件，写 ctx.state。
 [x] steps.music：选曲/裁剪/淡入淡出，写 ctx.state。
 [x] steps.compose：调用合成，输出最终视频路径，写 ctx.state。
 [x] pipeline：定义 run_all 顺序，控制并发/重试/轮询。
 [x] pipeline：提供分步调用（可选跳过已完成步骤）。
 [x] pipeline：每步后持久化 state.json。
 [x] CLI：解析参数（含兼容旧 flags），构建 Workflow。
 [x] CLI：支持 --resume/--no-auto-resume 行为。
 [x] CLI：打印关键配置摘要与输出路径。
 [x] Workflow：create() 组装 RunContext/Config/Storage。
 [x] Workflow：run_all() 串联 pipeline。
[x] Workflow：分步方法（script/shots/images/...）。
[x] Workflow：resume 逻辑（读取 state，跳过完成步骤）。
[x] 状态校验：config 哈希不一致时提示用户选择重新开始或继续。
[x] 文档：更新 README 新入口/目录引用 design.md 与 need.md。
[x] 验证：以 3 镜头 480p 运行一次，检查日志与 output 结构（不提交产物）。
