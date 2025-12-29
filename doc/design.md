# 广告视频生成重构设计

严格基于ad-aka.py进行重构，除了架构变化，代码不要自由发挥
输入文件和中间文件、输出项目目录逻辑、断点续传等保持不变，和原来程序保持高度兼容

## 目标与约束
- 入口脚本更名为 `py/ad.py`，主程序仅保留参数解析与启动说明。
- 形成可分步、可续跑的异步 Workflow API，便于未来网页化/分步交互。
- 纯本地单用户，不引入额外服务；保留旧 CLI 行为（兼容 `ad-aka.py`）。
- 所有非主程序代码放入 `./py/function/`，对外 API 统一放入 `./py/api/`；不再向 `./py/services/` 增量添加。

## 目录规划（新）
- `py/ad.py`：极薄入口，`asyncio.run(cli.main())`。
- `py/api/`
  - `workflow.py`：Session/Workflow 对外 API（对 CLI、未来 HTTP 统一）。
  - `__init__.py`：便捷导出。
- `py/function/`
  - `config_loader.py`：`.env + config.yaml + user.yaml` 合并、校验、数字映射。
  - `logger.py`：颜色化/文件双写、strip 颜色工具。
  - `context.py`：`RunContext`（路径、配置、限流器、session_id、日志句柄）。
  - `rate_limit.py`：协程安全封装现有限流逻辑（适配 asyncio）。
  - `storage.py`：工作目录、缓存/输出路径管理，断点续跑记录。
  - `llm_client.py`：LLM 提示拼装、调用、重试。
  - `media_clients.py`：图像/视频 API 调用与轮询；旁白/字幕/音乐选择桥接（可复用 `py/services/*`，仅作适配层）。
  - `pipeline.py`：核心调度（场景拆分、图像→视频、音频/字幕、合成）；暴露 async 步骤函数。
  - `cli.py`：参数解析、兼容旧 flags（`--resume/--no-auto-resume`）、调用 `api.workflow`。
  - `steps/`：细粒度步骤模块（脚本生成、镜头、图像、视频、旁白、字幕、音乐、合成、收尾）。

## 数据流与上下文
- `RunContext` 关键字段：`session_id`、`work_dir`、`config`、`logger`、`limiters`、`assets`（图/音/字幕路径）、`state`（可序列化 JSON 以便 resume）。
- `state` 持久化：`work_dir/state.json`，包含每个步骤完成标记、文件路径、模型/参数快照。

## API 草图（异步）
- `py/api/workflow.py`
  - `class Workflow:`
    - `@classmethod async def create(session_id: str | None = None, args=None) -> "Workflow"`
    - `async def run_all(self) -> RunContext`
    - 分步方法：`async def gen_script()`, `gen_shots()`, `gen_images()`, `gen_videos()`, `gen_voice()`, `gen_subtitle()`, `compose()`, `finalize()`。
    - `async def resume()`：读取 `state.json`，跳过已完成步骤。

- `py/function/pipeline.py`（示例）
  - `async def gen_script(ctx: RunContext) -> None`
  - `async def gen_shots(ctx: RunContext) -> None`
  - `async def gen_images(ctx: RunContext, sem: Semaphore)`
  - `async def gen_videos(ctx: RunContext, sem: Semaphore)`
  - `async def gen_voice(ctx: RunContext)`
  - `async def gen_subtitle(ctx: RunContext)`
  - `async def compose(ctx: RunContext)`
  - 每步更新 `ctx.state` 并落盘。

## 异步与并发控制
- 统一使用 `asyncio.Semaphore` 控制图像/视频并发（从配置读取 `concurrent_workers`）。
- 轮询改用 `asyncio.sleep`；限流适配器提供 `async with limiter`。
- LLM/媒体请求使用 `aiohttp` 或 `httpx.AsyncClient`（设计阶段先定义接口，落地时替换请求方）。

## 兼容策略
- `py/ad-aka.py` 保留为 shim：提示新入口并调用 `python -m py.ad`（不删除旧文件）。
- 保持原参数名与默认值，新增时保证向后兼容（旧脚本不报错）。

## 步骤拆分草图
1) **配置与上下文**：加载配置→合并→校验→创建 `RunContext`、工作目录、日志文件。
2) **脚本生成**：LLM 生成广告脚本与镜头概要。
3) **镜头拆分**：基于模板/运镜分配，生成分镜列表。
4) **图像生成**：并发提交图像任务，轮询获取结果。
5) **视频生成**：根据配置走 i2v 或 t2v，支持 direct 模式；并发轮询。
6) **旁白/字幕**：调用语音生成，随后做字幕时间轴。
7) **合成与配乐**：使用适配层调用现有合成功能，选择/匹配音乐。
8) **收尾**：写 `state.json` 终态，输出路径汇总。

## 关键适配点
- **配置映射**：将现有数字映射/提示模板搬到 `config_loader.py`，对外暴露结构化对象，减少全局变量。
- **日志**：`logger.py` 提供 `log(level, msg)`，CLI 默认控制台 + 文件双写，文件内容去掉 ANSI。
- **限流**：`rate_limit.py` 包装现有限流器，提供 `async enter`，保持每日/每分钟计数。
- **复用现有服务**：在 `media_clients.py`/`steps/*` 中薄适配 `py/services`（暂不修改服务代码），避免重复实现。

## 状态与断点续跑
- `state.json` 字段示例：
  ```json
  {
    "session_id": "aka-20250101-abc",
    "steps": {"script": "done", "images": ["img1.png", "img2.png"], ...},
    "config_hash": "...",
    "output": {"video": "output/aka-.../final.mp4"}
  }
  ```
- `resume` 时校验 `config_hash`，如不一致提示用户重新开始或强制继续。

## CLI 行为草图（`py/function/cli.py`）
- 参数：`--resume`, `--no-auto-resume`, `--style`, `--resolution`, `--shots`, `--use-intelligent-music`, `--image-model`, `--video-model`, `--dry-run` 等。
- 入口：`async def main()` → 解析参数 → `Workflow.create(args)` → `await workflow.run_all()`。

## 实施里程碑
1) 搭建目录与空模块、迁移 `ad.py` 入口与 `ad-aka.py` shim。
2) 搬迁配置/日志/上下文/限流到 `function` 层，保持单测/脚本可运行。
3) 步骤函数拆分与 async 化，保留原业务逻辑（调用服务适配层）。
4) 增加 `state.json` 持久化与 resume 路径。
5) 最小化集成验证：3 镜头 + 480p 跑通；更新 README/使用说明。
