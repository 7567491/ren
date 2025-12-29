# 项目需求总览（Workflow + 参数 + 客户旅程）

## 核心功能
- 主题/脚本生成：基于 LLM 生成广告脚本、镜头概要和分镜提示。
- 视觉生成：按镜头生成图片（或直接 T2V），支持多模型选择与提示扩展。
- 视频生成：I2V/T2V 轮询获取视频片段，统一时长/分辨率。
- 音频生成：旁白合成、音乐智能匹配/随机选择，音量与淡入淡出处理。
- 字幕生成：自动时间轴、样式/位置配置、与旁白对齐。
- 合成：旁白+配乐+视频片段合成，输出成品视频与日志、状态文件。
- 断点续跑：会话 state 持久化，可 resume 跳过已完成步骤。
- 限流/重试：按配置限流 API，网络/任务失败重试与回退。

## 工作流（高层）
1) 初始化：加载 `.env` + `config.yaml` + `user.yaml`，生成 session_id/工作目录/日志。
2) 脚本与分镜：LLM 生成脚本 → 拆分镜头 → 运镜/风格分配。
3) 视觉生成：并发图像或直接 T2V 视频生成，轮询直至完成或超时。
4) 视频阶段：如走 I2V，则对每张图生成视频片段并轮询。
5) 音频与字幕：生成旁白 → 生成字幕时间轴/样式。
6) 配乐：智能匹配或随机音乐，裁剪/淡入淡出。
7) 合成：按镜头顺序合成最终视频，混音旁白与配乐。
8) 收尾：写入 `state.json`、输出路径汇总、兼容 resume。

## 主要参数（示例）
- 流程控制：`--resume`, `--no-auto-resume`, `--dry-run`。
- 视觉：`--style`, `--resolution`, `--shots`, `--image-model`, `--video-model`, `--seed`, `--duration`。
- 音频：`--voice`, `--voice-speed`, `--subtitle-position`, `--use-intelligent-music`。
- 资源/并发：`--concurrent-workers`, `--output-base`, `--workdir`。
- 提示控制：是否启用 prompt expansion、LLM 提供商/模型选择。

## 客户旅程（预期使用路径）
1) 准备阶段：配置 `.env`、`config.yaml`、`user.yaml`，放置资源（logo、音乐特征）。
2) 运行 CLI：`python py/ad.py --style cinematic --shots 3 --resolution 480p`。
3) 过程反馈：终端/日志显示每步进度；若中断可 `--resume` 继续。
4) 审阅与调整：查看输出视频/字幕/日志，根据反馈调整参数或提示词重新运行。
5) 集成扩展：未来可由网页/HTTP API 调用同一 Workflow，复用 state/resume 机制。

## 约束与边界
- 单用户本地运行，暂不考虑鉴权/多租户。
- 不新增外部基础设施（无队列/Redis/DB），依赖本地文件系统持久化。
- 与旧 CLI 兼容（`ad-aka.py` shim）；不修改现有 `py/services/*`，通过适配层调用。

