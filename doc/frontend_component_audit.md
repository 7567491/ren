# 前端组件梳理与信息架构

更新时间：2026-01-03  
范围：`frontend/src`

## 组件清单 & 取舍

| 分类 | 组件/目录 | 状态 | 说明 |
|------|-----------|------|------|
| 布局 | `layout/CardContainer.vue` | 保留 | 抽象出统一的折叠面板，已在左栏/右栏全面复用 |
| 全局 | `stores/dashboard.ts`、`stores/layoutPrefs.ts` | 保留 | 管理任务与折叠偏好；后续精简只通过 Pinia 暴露状态 |
| 工作区 | `components/workspace/PreparationPanel.vue` | 保留 | 左栏系统列的唯一入口，挂载 API Key/任务管理/全局设置 |
| 工作区 | `components/workspace/TaskList.vue` | 新增 | 替换旧任务列表，实现状态筛选与 Trace 复制 |
| 业务面板 | `components/panels/AvatarConfigurator.vue` | 新增 | 头像/角色高频交互的子组件，封装 FilePond 与角色上传 |
| 业务面板 | `components/panels/ScriptEditor.vue` | 新增 | 脚本文本、模板按钮与音色控制的统一容器 |
| 业务面板 | `components/panels/MonitorPanel.vue` | 保留 | 已重构为横向阶段条 + 日志抽屉 |
| 业务面板 | `components/panels/ResultAssetSection.vue` | 保留 | 播放器/下载/素材目录，支持“本地 + 备用 CDN”双通道 |
| 遗留 | `components/panels/PreparationPanel.vue` | 下线 | 旧故事化 UI，已彻底删除避免混淆 |
| 其他 | `components/panels/CreationPanel.vue` | 保留 | 仅负责折叠状态与三个子组件的串接，逻辑已大幅瘦身 |

> 结论：剩余的故事化控件（镜头数、剧情面板等）已全部移除；若需新增业务面板，一律放在 `components/panels/` 并以子组件形式引入。

## 信息架构（IA）

| 区域 | 内容/控件 | 说明 |
|------|-----------|------|
| **Hero** | 标题 + CTA + 状态提示 | 单句价值主张 + “开始创建”，右侧提示当前任务状态 |
| **左栏（系统列）** | API Key 卡、任务列表、全局设置 | 一切与账号/任务调度相关的控件：Key 校验、余额查询、任务筛选、调试模式开关 |
| **中栏（输入列）** | AvatarConfigurator、ScriptEditor、Advanced 设置、提交按钮 | 仅保留与数字人生成直接相关的表单字段，使用折叠面板分组 |
| **右栏（输出列）** | MonitorPanel、ResultAssetSection | 展示阶段进度、日志/抽屉、素材卡片与播放器 |

### 字段归属表

| 字段/功能 | 来源 | 所属列 | 备注 |
|-----------|------|--------|------|
| API Key、余额查询 | 左栏 `PreparationPanel` | 左 | 仅展示 Wavespeed/WaveSpeed API 相关信息 |
| 任务筛选/Trace 复制 | 左栏 `TaskList` | 左 | 支持 `全部/执行中/已完成/失败` |
| Avatar Mode / Prompt / Upload / Character | `AvatarConfigurator` | 中 | 子组件封装 FilePond 与角色上传 |
| Script 文本 + 模板 | `ScriptEditor` | 中 | 模板数量严格控制在 3 个 |
| Voice (id/speed/pitch/emotion) | `ScriptEditor` | 中 | 集成在脚本侧边卡片 |
| Resolution / Seed | CreationPanel 高级段 | 中 | 非高频字段默认折叠 |
| 新任务提交 | CreationPanel | 中 | 按钮文案为 “生成数字人视频” |
| 阶段进度 / 倒计时 | MonitorPanel | 右 | 横向三节点 + 倒计时提示 |
| 日志预览 / 抽屉 | MonitorPanel | 右 | 默认显示 5 条，点击抽屉查看全部 |
| 播放器 + 备用 CDN | ResultAssetSection | 右 | 主按钮播放本地 `/output/...`，文字链接提示 CDN |

## 设计原则补充

1. **信息只出现一次**：任何字段仅出现在一个列中，避免重复输入或提示。
2. **强制分栏语义**：系统/输入/结果互不干扰，避免左右栏因滚动挤压内容。
3. **高频子组件化**：头像、脚本等复杂区域必须抽象为子组件，CreationPanel 只做 orchestration。
4. **默认折叠低频内容**：高级参数、日志抽屉均默认为折叠，界面维持清爽。
5. **Trace 可追溯**：任务列表、日志区均突出 trace id，配合后端日志规范。
