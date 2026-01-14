# 前端任务流（Vue SPA）

> 2025.02 版以多卡片仪表盘为主视图，节点顺序与 `/home/wave` 老项目对齐：顶部 API Key → 任务管理 → 进度 → 素材目录。所有卡片均可折叠，移动端默认只展开 API Key/任务卡片。

本文梳理 `frontend/src/App.vue` 当前的交互节奏，作为阶段 3 研发/联调时的基线原型。流程拆分为任务创建（表单）、进度轮询与结果播放三大块。

## 1. 顶层序列

```
用户输入 → 本地校验/估算 → (可选) 头像上传 → 创建任务 → 进入进度卡片 → 周期性轮询 → 完成/失败分支 → 结果展示或错误提示
```

关键约束：

- API 基址 `API_BASE` 与轮询间隔 `POLL_INTERVAL` 从 `config.js` 注入（默认同源 + 2s）。
- 调试模式下限制字符数（10 秒 ≈ 50 字），优先展示预估成本。

## 2. 卡片节点 & 表单

| 卡片 | 关键字段 | 交互要点 |
|------|----------|----------|
| API Key 卡片 | `apiKeyInput`、`balanceValue` | 迷你输入框 + 三个图标按钮（显隐/保存/清除）。为空时会提示“Key 不能为空”，按钮置灰。余额按钮调用 `/api/wavespeed/balance` 并在卡片右下角显示更新时间。 |
| 任务管理卡片 | 任务列表、轮询按钮、折叠表单 | 任务列表可立即切换 job，右上角两个文本按钮负责刷新和暂停/恢复轮询。下半段表单等同旧版 `App.vue` 逻辑，但头像模式/角色选择统一放在 `CardContainer` 内，任何校验错误都通过卡片内 `formAlert` 提示。 |
| 进度卡片 | `stageDefinitions`、`overallProgress`、播放器 | 顶部是聚合进度条（按头像/语音/视频 20/30/50% 加权），下方三段 stage 列表显示状态 + emoji + 文案颜色。卡片尾部复用播放器/下载操作。 |
| 素材卡片 | `materialItems`、路径复制按钮 | 首先展示 `/mnt/www/ren/<job_id>/` 根目录，然后按 avatar/audio/video/log 四类列出本地/公网路径，并提供复制/打开按钮。 |

任务表单中的字段与之前一致，但基于卡片实现：

- Prompt / Upload / 预制人物三种模式互斥，切换时会自动 `clearAvatarFile()`；选择角色后自动补充推荐音色。
- Debug 模式仍然限制 50 字（10 秒），提示语更新为“调试模式开启：限制 50 字以内”。
- API Key 与任务表单之间通过 Pinia `dashboardStore` 共享状态，卡片间无需 `props` 传递。

## 3. 进度轮询面板（卡片内部）

```
startPolling()
  └── setInterval (POLL_INTERVAL)
        ├── GET /api/tasks/{job_id}
        ├── updateProgress(task) → 根据 status 更新阶段卡片 (avatar/speech/video)
        ├── updateCostEstimate(task.cost_estimate)
        └── 若 status ∈ {finished, failed} → clearInterval → handleComplete(task)
```

- `updateStage()` 依据状态名是否包含 `avatar_generating` 等关键词，切换阶段卡片的 `pending/active/done` 样式，并更新图标。
- 状态消息 `statusMessage` 优先展示接口返回 `message`。
- 轮询出错时仅打印到控制台，下一次继续尝试。

## 4. 结果与错误/通知分支

| 场景 | UI 行为 |
|------|---------|
| 成功 (`finished`) | 进度卡片显示✅+成本合计，播放器自动载入 `TaskResponse.assets.local_video_url`（若为空回退 `video_url`）。 |
| 失败 (`failed`) | 卡片转为红色提示，`errorDialog` 弹出 trace id/错误码，任务列表/Store 会把错误信息落盘。 |
| 任意错误 | API Key 卡片、任务卡片、素材卡片都通过 `dashboardStore.errors[key]` 共享错误状态，卡片头部会出现红色错误条；同时触发 toast。 |

## 5. 任务流与 API 对应关系

| 前端阶段 | API 调用 | 备注 |
|----------|----------|------|
| 头像上传 | `POST /api/assets/upload` | 返回 `url` 后写入任务创建参数。 |
| 创建任务 | `POST /api/tasks` | 返回 `job_id` + `cost_estimate`。 |
| 状态轮询 | `GET /api/tasks/{job_id}` | 负责驱动阶段 UI、结果播放、错误展示。 |

该原型后续可直接用于绘制更正式的流程图或调整交互。若 API 协议有变动，请同步更新此文档并在 `doc/plan.md` 中标注。

## 6. Vue 组件拆分（迁移规划）

| 组件 | 作用 | 备注 |
|------|------|------|
| `CardContainer` | 提供统一的卡片骨架、折叠按钮、错误展示。 | API Key/任务/进度/素材四张卡片均继承该结构，移动端默认折叠低优先级卡片。 |
| `DashboardGrid` | 仪表盘布局容器，负责响应式栅格。 | 页面唯一布局容器，宽屏双列、窄屏单列。 |
| `TaskForm` | 头像模式、播报文本、音频参数与调试模式表单。 | 表单逻辑与 `/home/wave` 的流程相同，封装在任务卡片内部。 |
| `StagePipeline`（内嵌） | 三阶段状态行 + 进度条。 | 根据 `stageDefinitions` 和轮询返回的状态自动标记 ⚙️/✅/⚠️。 |

`useAppConfig` 负责从 `window.APP_CONFIG` 读取运行时配置；`useMediaQuery('(max-width: 768px)')` 决定卡片初始折叠状态；轮询逻辑仍位于 `App.vue` 内部，下一步可拆为独立 composable。
