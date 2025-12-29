# Repository Guidelines

中文对话

## Project Structure & Module Organization
- 主代码在 `py/`，其中 `ad-aka.py` 是故事化视频生成入口；`services/` 存放语音、字幕、合成等子模块。
- 资源文件放于 `resource/`，输出成品位于自动创建的 `output/aka-*/`；不要手动提交输出产物。
- 配置文件 `config.yaml`、环境变量 `.env` 位于根目录；测试与示例脚本在 `test/` 与 `py/test-*.py`。

## Build, Test, and Development Commands
- 激活虚拟环境：`source venv/bin/activate`。
- 安装依赖：`pip install -r requirements.txt`。
- 常规运行（自动断点续传）：`python3 py/ad-aka.py`。
- 强制新任务：`python3 py/ad-aka.py --no-auto-resume`；指定恢复：`python3 py/ad-aka.py --resume aka-xxxx`。
- 网络连通性自检：`python3 py/test_network.py`。涉及付费 API 的测试前优先使用低分辨率与少量镜头。

## Coding Style & Naming Conventions
- 代码使用 Python 3.10+，遵循 PEP 8，四空格缩进，函数/变量用 `snake_case`，类名用 `CamelCase`。
- 保持现有模块划分，复用日志与重试工具；新增函数优先放入对应 `services/` 子模块或与之并列的工具文件。
- 文本文件统一 UTF-8 编码；保持中文用户输出清晰简短，必要时添加类型注解以提升可读性。

## Testing Guidelines
- 本项目主要以脚本级验证为主：在修改 API 逻辑时，先运行 `python3 py/test_network.py` 确认网络，再以最小镜头数和低分辨率调用主流程。
- 避免无意义的重复付费调用；利用断点续传检测结果是否被复用，必要时删除对应 `output/aka-*` 目录后重跑。
- 提交前至少完成一次最小化集成验证并检查日志输出是否包含错误堆栈。

## Commit & Pull Request Guidelines
- 提交信息保持简洁、祈使句风格（如 “add retry to wavespeed client”），每次提交聚焦单一变更。
- PR 描述需包含：变更摘要、测试方式（含命令）、可能的成本影响或依赖变更；涉及界面或输出格式改动时附示例路径（如 `output/aka-*/final_video.mp4`）。
- 不提交 `.env`、生成的媒体文件或 `output/` 内容；敏感密钥仅存本地。

## Security & Configuration Tips
- `.env` 需包含 `DeepSeek_API_KEY` 与 `Wavespeed_API_KEY`，不要写入版本库；在新环境复制模板并确认权限。
- 费用相关接口建议先用 480p、3 镜头进行验证；并发度仅在允许范围调整，避免触发限流或额外计费。
