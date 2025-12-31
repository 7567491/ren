# 背景与目标
- 数字人 Web 控制台当前把「任务列表 + 创建表单 + 进度/素材 + API Key」堆在同一屏幕，导致滚动过长、上下文频繁切换，对核心用户（数字人视频制作者）不够友好。
- 参考 `/home/wave/workflow.html` 的旅程式布局，希望在保持深色主题的同时，营造更清晰的左右分栏体验，让用户沿着“准备 → 创作 → 监控”路径完成一次任务。
- 本方案聚焦方案 B：通过重新排序现有卡片内容并加入折叠/提示，将信息密度控制在 3 个大面板内，减少首次进入的认知负担。

# 与 plan-UI.md 已完成工作的衔接
- `doc/plan-UI.md` 中已经完成了仪表盘栅格设计、卡片组件规范、API Key 卡片缩减与余额查询、进度/素材原型等基础性任务，本 plan 将直接复用这些成果，重点放在旅程视角下的分区重构与信息架构调整。
- 由于多卡片布局与 store 模型已经成型，本次调优不再重复组件层级设计，而是聚焦层次顺序、折叠策略、跨面板联动和移动端体验深化，确保在不破坏 `plan-UI.md` 已交付内容的前提下完成 UX 升级。
- 已经落地的素材映射与播放器逻辑，可迁移到新的“监控区”结构中，只需重新包装展示层即可，减少开发工作量。

# 当前痛点速记
- 任务管理卡片 (`App.vue` 中 `CardContainer.task-card`) 包含任务列表、创建表单、角色管理与高级选项，成为最多滚动的区块。
- 任务进度卡片既管实时阶段又承载播放器/素材，视觉焦点分散，状态提示缺乏时间信息。
- API Key 管理在首屏单独占卡，不像辅助工具。
- 素材目录暴露 `/mnt/www` 等运维路径，不符合制作者心智。

# 明确需求
- 目标用户：中高级数字人制作者，需要快速重复创建/监控任务。
- 视觉偏好：深色主题+左右分栏；旅程信息可在顶部 hero 内体现，无需新增独立旅程面板。
- 交互要求：必须展示完整的三阶段过程（头像→语音→视频）；视频播放器和素材信息可以在任务完成后再展开。
- 功能优先级：创建流程 > 进度监控 > 资产回收；API Key 作为辅助工具条放置即可。

# 新的页面架构
1. **顶部 hero + 步骤提示条**
   - 保留现有 hero 背景，但新增“步骤提示条（准备 API / 填脚本 / 监控进度）”和当前任务状态概览。
   - Hero 内放置“创建任务”主按钮和已选任务摘要，模拟 `/home/wave/workflow.html` 中的旅程提示。
2. **准备区（左列上方）**
   - 卡片合并 `Wavespeed API Key` + “任务列表”基础信息。
   - API Key 只占少量空间，提供显示/保存/余额查询按钮；任务列表保持简洁（ID、状态、最近更新），提供“查看 / 移除”操作。
3. **创作区（左列下方）**
   - 将创建表单拆成「角色与头像管理」「脚本与音色」「高级调参」三个折叠段。
   - “上传新人物”移到弹出层或折叠详情中，默认收起；高级选项默认折叠。
   - 右侧浮动展示实时预估（字数、时长、成本），避免用户下滚查看。
4. **监控区（右列）**
   - 顶部为“阶段时间线”卡片：进度条 + 三阶段卡片 + 时间/trace 信息。
   - 中部“任务日志/倒计时”区域，汇总状态消息、手动刷新控件。
   - 底部“结果与素材”卡片，仅在任务完成后自动展开播放器、下载、分享；素材路径默认显示公网 URL，本地路径折叠在“技术详情”中。
5. **响应式策略**
   - ≥1024px 以上采用左右分栏；窄屏下按“准备→创作→监控”顺序堆叠，并在每个卡片顶部保留旅程提示。
   - API Key 工具条固定在页面顶部或浮层中，移动端可放在折叠抽屉。

# 下一步建议
- 基于上述架构拆分现有 `CardContainer` 内容，新增 `PreparationPanel.vue`、`CreationPanel.vue`、`MonitorPanel.vue` 等中间层组件，复用现有 store 与逻辑。
- 定义“监控区”内部的阶段组件（如 `StageTimeline`）以承载耗时、trace、avatar/audio/video 状态，输出更清晰的阶段反馈。
- 调整素材卡片逻辑：若 `assets.public_url` 存在则优先展示，在“更多”折叠中提供 `/mnt/www` 路径与复制按钮。

# 最新进展
- 已完成左列“准备区 + 创作区”的首次拆分，`PreparationPanel` 合并 API Key、余额与任务列表操作，支持刷新、轮询、移除等交互。
- `CreationPanel` 现负责全部角色/脚本/高级选项流程，并透出预估字数/时长/成本，`App.vue` 只保留状态与方法映射，便于后续旅程式布局继续演进。
- 新增 `workspace` 布局容器与左右分栏样式，桌面端已呈现“准备→创作”分栏，右列预留监控区占位，等待 `MonitorPanel` 接入。

# 任务清单
[ ] 根据方案 B 的三段结构输出详细线框稿（桌面/移动双版本）。
[x] 梳理现有 `App.vue` 中各卡片的模板/脚本分布，记录依赖关系。（基于首次拆分完成）
[ ] 列出 ProgressPanel、MaterialPanel、移动端抽屉等现有组件需要保留的行为清单。
[x] 拆分 API Key 输入、任务列表、表单、进度、素材所使用的数据/方法，整理成映射表。（`PreparationPanel`/`CreationPanel` 已落地）
[ ] 在 hero 区新增步骤提示条的 UI 文案，不更动其他区域，验证视觉效果。
[ ] 将 hero 区添加“创建任务” CTA，点击滚动到创建区。
[x] 新增 `workspace` 布局容器，暂时包裹原有 `DashboardGrid`，不改内部组件。
[x] 创建 `workspace__column` 样式，预留左右分栏的 CSS 变量。
[ ] 将 `DashboardGrid` 的栅格调整为可在新容器内切换列宽。
[x] 为未来的 `PreparationPanel`、`CreationPanel`、`MonitorPanel` 预留挂载点（占位 div/section）。
[x] 梳理 API Key 相关的方法（保存/清除/刷新余额），包装成独立函数，便于传入组件。
[x] 梳理任务列表操作（select/remove/refresh），准备迁移到 `PreparationPanel`。
[x] 梳理刷新/轮询控制逻辑，准备以 props/emit 形式下发。
[x] 梳理创建表单字段与验证逻辑，准备拆到 `CreationPanel`。
[x] 梳理角色上传与 FilePond 逻辑，评估如何通过 ref 传递。
[ ] 梳理进度相关的 computed/watch（stageStatus、视频播放器），准备整合到 `MonitorPanel`。
[ ] 梳理素材路径生成逻辑（materialItems），准备拆到 `MonitorPanel`。
[x] 设计 `PreparationPanel` 的 props/emit 列表并记录在注释/文档中。
[x] 设计 `CreationPanel` 的 props/emit 列表并记录在注释/文档中。
[ ] 设计 `MonitorPanel` 的 props/emit 列表并记录在注释/文档中。
[x] 将 `PreparationPanel` 挂载到 App.vue，先仅传入 API Key 状态/方法。
[x] 验证 `PreparationPanel` 保存/清除/刷新余额的动作能正确工作。
[x] 将任务历史数据/操作逐个传入 `PreparationPanel`，保留“最新 + 更多”逻辑。
[x] 调整 `PreparationPanel` 中文案和错误展示，保持与旧卡片一致。
[x] 逐步移除旧 API Key 卡片模板，改用 `PreparationPanel` 输出。
[x] 在 `PreparationPanel` 中加入轮询控制按钮，并连接 `togglePolling`。
[x] 在 `PreparationPanel` 中渲染“刷新任务”按钮，调用 `refreshSelectedTask`。
[x] 将 `CreationPanel` 挂载到 App.vue，并传入表单初始值。
[x] 验证 `CreationPanel` 的输入变化能同步更新 App.vue 的状态。
[x] 将 FilePond ref 与 `handleAvatarFiles` 逻辑注入 `CreationPanel`。
[x] 将角色列表、角色选择、上传新角色流程迁移到 `CreationPanel`。
[x] 确认 `CreationPanel` 内提交事件调用原 `handleSubmit`，且验证逻辑仍生效。
[x] 将原 `task-card` 模板移除，改用 `CreationPanel` 输出。
[x] 将 `MonitorPanel` 挂载到 App.vue，同时传入阶段状态、资产链接。
[x] 在 `MonitorPanel` 内复用现有 ProgressPanel/MaterialPanel 或直接继承其样式。
[x] 验证 `MonitorPanel` 中视频播放器初始化/销毁逻辑，确保不重复创建实例。
[x] 将素材列表交互（复制/打开链接）传递给 `MonitorPanel`。
[x] 将视频下载/复制链接按钮从 `App.vue` 挪到 `MonitorPanel` 并保持功能。
[x] 调整移动端抽屉逻辑，让其读取 `MonitorPanel` 的数据或复用旧组件。
[x] 在布局层面替代 `DashboardGrid`，让左列包含 `PreparationPanel` + `CreationPanel`，右列包含 `MonitorPanel`。
[ ] 更新全局样式文件，增加 `workspace`、`column-left/right` 等新类。
[ ] 调整媒体查询，让窄屏下按“准备→创作→监控”堆叠显示。
[ ] 重新测试 hero CTA、API Key 操作、任务创建、进度轮询、素材播放等核心路径。
[ ] 更新 `plan-UI.md` 或相关设计文档，记录渐进式替换方案。
[ ] 在 `doc/工作流.md` 中补充新的布局和操作路径说明。
[ ] 与产品/研发确认 hero 区新增步骤提示条的文案与数据来源。
[ ] 设计“准备区”卡片布局，将 API Key 工具条与任务列表并排展示。
[ ] 将“上传新人物”交互改为模态框或折叠面板的小样。
[ ] 拆分创建表单为“角色”“脚本”“音色”“高级”四个折叠段的交互稿。
[ ] 设计右侧实时预估组件（字数/时长/成本）并决定在折叠段中的位置。
[ ] 定义“步骤提示条”在不同任务状态下的颜色/图标规范。
[ ] 将 API Key 卡片缩减逻辑接入新的准备区视图。
[ ] 评估任务列表 + API Key 同卡片后的 store 交互，更新事件流。
[ ] 编写新的 `PreparationPanel.vue` 外层组件骨架。
[ ] 将现有任务列表子组件迁移到 `PreparationPanel` 并保持功能完整。
[ ] 调整任务列表的空态文案以指向“先创建任务”操作。
[ ] 重构创建表单模板，按折叠段拆分为独立子组件文件。
[ ] 重新布局 FilePond 区域，保证在折叠展开时高度稳定。
[ ] 将“上传新人物”表单移出主流程，绑定至新折叠或弹窗。
[ ] 在脚本段加入字数/时长/成本浮动提示，不依赖滚动查看。
[ ] 更新高级选项折叠的默认状态与入口文案。
[ ] 重新定义监控区内阶段列表的数据结构，加入开始/结束时间。
[ ] 新建 `MonitorPanel.vue` 承载阶段时间线、状态信息与日志入口。
[ ] 将视频播放器和素材列表封装为 `ResultAssetSection`，默认隐藏，任务完成后展开。
[ ] 修改素材列表模板，仅默认展示公网 URL，本地路径放入“技术详情”折叠。
[x] 设计并实现“状态消息 + Trace ID”小组件，固定在监控区顶部。
[x] 在监控区加入手动刷新与轮询切换按钮的新位置。
[x] 重新排列 `DashboardGrid` 布局，使准备区/创作区占左列，监控区占右列（右列当前为占位，等待 MonitorPanel 接入）。
[x] 调整 CSS 变量与媒体查询，确保左右分栏在 >1024px 时对齐。
[x] 为移动端定义堆叠顺序和折叠默认状态（准备→创作→监控）。
[ ] 验证 API Key 工具条在移动端抽屉中的交互和可访问性。
[ ] 更新 Pinia store 中与布局相关的持久化键值（比如卡片折叠状态）。
[ ] 补充 `doc/工作流.md`，记录新的旅程式界面与操作路径。
[ ] 更新 `doc/frontend_task_flow.md`（或新增文档）描述步骤提示条与阶段映射。
[ ] 为 `PreparationPanel`、`CreationPanel`、`MonitorPanel` 编写单元测试覆盖折叠逻辑。
[ ] 在端到端测试脚本中增加“创建任务→查看监控区→查看结果”完整旅程。
[ ] 对新布局进行可用性走查，收集制作者反馈并迭代。
[ ] 与后端对齐素材 API 字段调整（若新增 `public_url` 首选逻辑）。
[ ] 在 README 加入新版 UI 截图与操作说明。
[ ] 完成一次移动端真机测试，验证折叠/抽屉和播放器行为。
