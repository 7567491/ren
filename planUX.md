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
- 左列“准备区 + 创作区”已经拆分成 `PreparationPanel` + `CreationPanel`，API Key 工具条与任务列表共享同一 panel，并可展开历史任务。
- `CreationPanel` 统一了承载角色/头像、脚本/音色和高级选项，FilePond、角色上传、费用预估等逻辑均通过 props/emit 反向驱动，`App.vue` 仅负责状态源。
- 右列 `MonitorPanel` 已经接入，阶段时间线、Trace 状态、倒计时、轮询控制、video.js 播放器与素材列表都迁移完成，桌面布局形成“准备→创作→监控”的旅程。
- `materialItems` 现默认输出公网 URL 并把本地路径折叠到“技术详情”，bucket 路径异常会直接回写错误；移动端通过抽屉复用 `MonitorPanel`，保证窄屏也能查看相同的监控数据。

# 监控区结构细化
- **阶段时间线**：`frontend/src/components/panels/MonitorPanel.vue` 逐项渲染 `stageDefinitions`（见 `frontend/src/App.vue:260-275`），每个阶段具备 icon、color、权重和描述，配合顶部 `overallProgress` 仪表显示完成度。
- **状态/倒计时/成本**：状态卡片联合 `statusMessage`、`statusAccent` 和 `monitorTraceId` 展示 trace，`countdownVisible`/`countdownLabel` 呈现剩余时间，`costEstimateValue` 与 `billingSummary` 则同步展示预估与实际耗费。
- **阶段资产**：头像和语音预览按阶段即时展示，最终视频仅在 `taskStatus === 'finished'` 时初始化 video.js，并提供下载、复制链接等动作。
- **素材目录**：卡片列表只默认展示公网地址，技术详情对本地路径使用 `<details>` 折叠，所有路径由 `materialItems` 统一归一化，并在 `dashboardStore` 中记录异常。

# 组件行为清单
- **ProgressPanel（legacy 行为）**：必须保留阶段状态提示（pending/active/done/failed）、Trace ID 展示、人工刷新/轮询切换、倒计时与异常消息，这些已经整合进 `MonitorPanel` 但仍需在线框与文案上体现。
- **MaterialPanel（legacy 行为）**：素材列表需维持“复制本地/公网”“打开公网链接”三类动作、空态提示与错误提醒，且必须把 `/output/<job_id>/digital_human.mp4` 指定为 `TaskResponse.assets.local_video_url`。
- **移动端抽屉**：保留底部浮动按钮 + overlay 的交互模式，抽屉内应完整重用桌面监控区而非降级版本，同时要重置 body scroll（`drawer-lock`）以避免穿透。

# 组件 props/emit 速查
- **PreparationPanel**（`frontend/src/components/workspace/PreparationPanel.vue`）  
  Props：`isMobile`、`apiKeyValue`、`apiKeyVisible`、`apiKeyError`、`isApiKeyValid`、`hasStoredKey`、`balanceDisplay`、`balanceLoading`、`errorMessage`、`taskError`、`taskHistory`、`latestTasks`、`extraTasks`、`extraTasksSummary`、`currentJobId`、`pollingActive`、`describeStatus`、`formatTimestamp`。  
  Emits：`update:apiKeyValue`、`update:apiKeyVisible`、`validate-api-key`、`save-api-key`、`clear-api-key`、`refresh-balance`、`refresh-selected-task`、`toggle-polling`、`select-task`、`remove-task`。
- **CreationPanel**（`frontend/src/components/panels/CreationPanel.vue`）  
  Props：`formAlert`、`avatarMode`、`avatarPrompt`、`avatarFileError`、`acceptedAvatarTypes`、`maxAvatarSizeLabel`、`pondLabel`、`speechText`、`charCount`、`estimatedDuration`、`estimatedCost`、`voiceId`、`resolution`、`speed`、`pitch`、`emotion`、`seed`、`debugMode`、`debugHint`、`submitting`、`characters`、`characterLoading`、`characterError`、`selectedCharacterId`、`selectedCharacter`、`characterPreviewUrl`、`newCharacterForm`、`newCharacterAlert`、`creatingCharacter`。  
  Emits：`update:avatar-mode`、`update:avatar-prompt`、`avatar-files-change`、`update:speech-text`、`update:voice-id`、`update:resolution`、`update:speed`、`update:pitch`、`update:emotion`、`update:seed`、`update:debug-mode`、`refresh-characters`、`update:selected-character-id`、`clear-character-selection`、`update:new-character-form`、`new-character-file-change`、`submit-new-character`、`submit`。
- **MonitorPanel**（`frontend/src/components/panels/MonitorPanel.vue`）  
  Props：`currentJobId`、`taskStatus`、`overallProgressPercent`、`overallProgressLabel`、`stageDefinitions`、`stageStatus`、`statusMessage`、`statusAccent`、`traceId`、`countdownVisible`、`countdownLabel`、`countdownSource`、`costEstimateValue`、`costEstimateDesc`、`avatarUrl`、`audioUrl`、`resultVideoUrl`、`totalCost`、`billingSummary`、`errorMessage`、`materialItems`、`pollingActive`。  
  Emits：`download-video`、`copy-video-link`、`copy-local-path`、`copy-public-link`、`open-public-link`、`refresh-task`、`toggle-polling`。

# 核心数据流梳理
- **阶段状态 & 进度**：`STAGE_PIPELINE` + `stageStatus`（`frontend/src/App.vue`）维护 avatar/speech/video 的状态描述，`overallProgress` 依据权重输出百分比，`statusAccent` 映射成功/失败样式，`monitorTraceId` 优先读取 `latestTaskSnapshot`。
- **倒计时 & 轮询控制**：`videoCountdown`（total/remaining/source/samples）与 `countdownVisible/Label/Source` hook 到 `MonitorPanel`；`pollTimer` 为 null 即视为暂停轮询，桌面和抽屉共用 `pollingActive`。
- **素材路径**：`materialItems`（`frontend/src/App.vue:553` 起）集中把 `assets` 与 `currentBucketDir` 归一化，通过 `normalizeMaterialPath` 和 `bucketPathToPublicUrl` 补全公网地址，并在路径越界时向 `dashboardStore` 写入错误。

# 移动端抽屉策略
- `useMediaQuery('(max-width: 768px)')` 控制是否进入抽屉模式，`drawerButtons` 当前仅包含“监控”按钮，预留日后扩展位置。
- `mobileDrawerPanel`、`drawerActive` 与 `drawerPanelTitle/Subtitle` 决定抽屉显隐，`drawer-lock` 类阻止 body 滚动，点击 overlay 可关闭。
- 抽屉内容直接渲染 `MonitorPanel`，与桌面右列共享 props/emit，确保刷新、复制、轮询等能力在移动端一致。

# 下一阶段关注
- 补齐 hero 顶部旅程提示条与 CTA，并与产品确定步骤文案/数据源后输出桌面 + 移动的线框稿。
- 把 `CreationPanel` 拆为四段式折叠（角色/脚本/音色/高级），提供粘性的实时预估组件以及明确的高级选项默认状态。
- 为监控区补充阶段开始/结束时间、`ResultAssetSection` 子组件与文档说明，同时在移动端验证 API Key 工具条与监控抽屉的可访问性。

# Hero 区 & 步骤提示条方案
- **结构分层**：hero 顶部保留背景图和标题，标题右侧加入一个“旅程状态条”，展示 Step 1-3（准备 API / 填脚本 / 监控进度），每个 step 包含图标、状态点与文字。进程点颜色映射任务状态：`#38bdf8` 代表当前阶段，`#94a3b8` 代表待开始，`#22c55e` 代表已完成。
- **任务摘要**：状态条下方显示当前选中任务（`job_id` + 状态 + 更新时间），若无任务则改为“尚未创建任务”。文案来源：`currentJobId`、`statusMessage` 和 `formatTimestamp(lastUpdated)`.
- **CTA & 辅助按钮**：hero 右下角放置主要 CTA「创建新任务」，次按钮为「查看监控」，桌面端 CTA 点击后滚动到 `.creation-panel`；次按钮定位 `#monitor-panel`，供调度/监控使用。
- **数据映射**：Step 状态判定依据 `stageStatus`；当视频阶段完成后 Step 3 自动点亮。状态条需要 `overallProgressLabel` 与 `countdownLabel` 作为辅助信息。
- **移动端策略**：在 768px 以下，旅程条收缩为横向滚动 pill，CTA 挪到 hero 下方，按钮变成全宽排列；任务摘要改为两行，Trace ID 省略，仅保留 job id。

# 桌面 / 移动线框（文字描述）
- **桌面**：
  - Hero：左侧标题+副标题，中间旅程提示条，右下 CTA 区域（主按钮 + 次按钮），底部引用最新任务摘要。
  - 左列：`PreparationPanel`（两卡片上下一体） + `CreationPanel`（折叠段栈式），右列 `MonitorPanel`（阶段时间线 → 状态卡 → 结果/素材）。
  - 预估组件：在 `CreationPanel` 的脚本段 header 右侧浮动，滚动时使用 `position: sticky` 保持可见。
- **移动**：
  - Hero 依序排列：标题、副标题、旅程 pill、CTA 全宽按钮、任务摘要；旅程 pill 使用横向滚动 + Step 标签。
  - 主体采用单列堆叠：准备 → 创作 → 手动提示“滑动查看监控”，随后通过底部抽屉访问 `MonitorPanel`。
  - 抽屉按钮显示 Step 3 进度和倒计时，抽屉内 sticky Header 显示 job id + `overallProgressLabel`。

# CTA 交互细则
- `创建新任务`：调用 `scrollIntoView({ behavior: 'smooth' })` 指向 `.creation-panel`，当 `submitting` 为 true 时按钮呈 loading 状态并禁用。
- `查看监控`：桌面端锚点跳到 `.monitor-panel`，移动端触发 `toggleMobileDrawer('monitor')` 并滚动至抽屉按钮区域。
- CTA 状态：
  - 当 `taskStatus === 'running'` 时 CTA 不禁用，允许创建更多任务，但在按钮旁提示“当前任务处理中”。
  - 当 `pollingActive` 为 false 时，在 CTA 区提示“监控已暂停”，点击二级按钮可恢复轮询。
- Hero 中的余额提示链接 `PreparationPanel`，“刷新余额”按钮 hover 时展示 tooltip 引导用户前往准备区卡片。

# 阶段时间线数据结构草案
- **统一结构**：新增 `StageTimelineEntry`（字段：`id`、`label`、`state`、`startedAt`、`endedAt`、`durationMs`、`traceId`、`message`），由后端响应或本地推断生成。`stageStatus` 将只负责文案和 icon 映射，时间/日志交由 `timelineEntries`。
- **填充策略**：
  - 当任务刚创建时写入 `startedAt = Date.now()`，`endedAt = null`。
  - 轮询接口若返回 `stage_events` 列表，优先按接口时间覆盖；若缺失则根据 `TaskResponse.logs` 中的 `[ISO]` 解析补齐。
  - `durationMs` 在 `endedAt` 存在时计算，否则用 `Date.now() - startedAt` 实时展示。
- **渲染方式**：`MonitorPanel` 顶部阶段列表在每个阶段下方附加开始/结束时间（例：`10:32 → 10:34 · 02:15`），hover 时显示 `message` 与 `traceId`。
- **移动端折叠**：在抽屉内默认折叠时间详情，只显示当前阶段的倒计时，其余信息放入 `<details>`。

# ResultAssetSection 交互稿
- **折叠触发**：当 `taskStatus === 'finished'` 或 `assets.ready === true` 时自动展开，若用户手动收起则记忆 `localStorage['result-section-collapsed']`，避免每次刷新都展开。
- **内容栈**：上方 video.js 播放器，右侧结合下载/复制按钮；下方展示资产列表（头像、音频、视频、日志）。播放器下方提供“成本摘要”与 `billingSummary`。
- **路径展示**：每个素材块默认显示公网 URL，附一键复制/打开；技术详情行展示本地路径与 `TaskResponse.assets.local_*` 字段，可在“更多”折叠中展开。
- **辅助提示**：当检测到 `TaskResponse.assets.local_video_url` 不在 `/output/<job_id>/digital_human.mp4` 时显示 warning badge，引导用户检查存储路径。
- **移动端**：ResultAssetSection 放在抽屉内部 video 后面，复制/下载按钮拉伸为全宽，素材项使用 accordion 形式避免列表过长。

# 准备区卡片布局草稿
- **卡片并排**：桌面端将 API Key 工具条与任务列表并排放置于同一 `CardContainer` 内，左侧宽度 40%（凭证），右侧 60%（任务列表）。使用 CSS Grid（`grid-template-columns: minmax(240px, 0.4fr) minmax(320px, 0.6fr)`）保证在 1024px 以上保持水平对齐。
- **API 工具条**：包含输入框、切换可见按钮、保存/清除/刷新余额按钮和余额状态，按钮组采用紧凑 icon-button 形态；当余额查询中时右上角显示 `spinner` 并置灰刷新按钮。
- **任务列表**：展示最近 3 个任务，底部 `<details>` 展开更多；每个任务行保留 ID+状态 pill+更新时间+消息。列表顶部提供“刷新任务”“暂停/恢复轮询”两个按钮，与 hero CTA 文案一致。
- **错误/空态**：当 `taskError` 存在时在卡片顶部横幅提示；无任务时右侧显示“创建第一个任务”并附上 CTA 链接（锚点到 `CreationPanel`）。
- **移动端**：栅格在 768px 以下自动堆叠，API Key 工具条位于任务列表上方。在抽屉中展示准备区时，API Key 输入框改为全宽，按钮改为文字按钮，轮询操作移到列表顶部。

# CreationPanel 折叠段与实时预估
- **折叠结构**：将表单拆为四个 `<details>` 段落：角色 & 头像、脚本输入、音色与节奏、 高级参数。默认展开前两个，后两个保持折叠。每段提供 `summary` + 副标题 + 状态提示（例如“选择了 Lisa · 上传头像1个”）。
- **折叠状态持久化**：使用 `Pinia` 或 `localStorage` 记录 `creationPanelSections`，组件挂载时读取，保证用户刷新后维持折叠偏好。
- **实时预估组件**：创建 `CostEstimateBadge`，展示“字符数 / 预估时长 / 预估成本”，并在 `CreationPanel` 内使用 `position: sticky; top: 1rem;` 固定在脚本段右侧。移动端将其放在脚本 textarea 下方，使用 pill 样式。
- **角色段内交互**：上传新人物改为 modal 或折叠面内的 `<dialog>`；角色列表加入搜索输入和标签过滤，便于快速定位常用角色。
- **脚本段强化**：添加“插入模板”按钮、字数预警（>800 字时提示“建议分批生成”）；当 `debugMode` 开启时在段顶部展示黄色提示条。
- **音色/高级段**：音色段提供试听按钮，点击调用 `previewVoice(voiceId)`；高级段合并分辨率、速度、音高、情绪、seed、调试模式等控件，并在 summary 上显示当前关键参数（例如“720p · 1.0x · neutral”）。

# MonitorPanel 深化设计
- **布局分层**：将 MonitorPanel 拆分为 `StageTimeline`, `StatusCard`, `CountdownHint`, `MediaPreview`, `ResultAssetSection`, `MaterialList` 子模块，便于逐步替换 legacy 组件。
- **StageTimeline**：利用 `StageTimelineEntry` 渲染进度条+节点卡片。各节点展示 icon、label、状态、`startedAt → endedAt`、`duration`；未完成阶段的 `endedAt` 以“进行中”提示。支持 hover tooltip 展示 `traceId` 与 `message`。
- **状态卡片**：扩展为 3 列信息：状态文案、Trace ID/复制按钮、手动刷新与轮询开关。失败状态显示红色背景与错误原因链接。
- **倒计时提示**：当 `countdownVisible` 时显示“预计剩余 · 来源”条；若 `videoStageStartAt` 为 null 则隐藏。移动端抽屉内贴合 StageTimeline 显示。
- **媒体预览**：头像/语音预览在阶段完成后展示，可点击放大或试听；视频播放模块使用 video.js dark skin，提供“重新加载”按钮和 `onbeforeunload` 释放资源。
- **日志入口**：在状态卡下方加入“查看任务日志”按钮，点击打开侧边滑出层，展示 `TaskResponse.logs` 与 `traceId`，支持复制/搜索。
- **错误处理**：监控区任何 API 错误通过 `statusMessage` + toast 双通路提示；MaterialList 检测路径异常时自动在卡片顶部展示 warning。

# 数据与状态同步要求
- **Pinia store**：新增 `layoutPrefs`（含 hero CTA 被引导次数、CreationPanel 折叠状态、ResultSection 折叠状态），在组件中通过 `storeToRefs` 双向绑定。
- **事件流**：`PreparationPanel` 的轮询按钮需向 store dispatch `togglePolling`，同时 hero CTA 的“监控已暂停”提示读取相同状态；`MonitorPanel` 的下载/复制事件继续冒泡到 `App.vue`，但 ResultAssetSection 将内部统一处理复制操作，再向上抛出 Toast。
- **可观测指标**：记录用户从 hero CTA 到创建区的滚动次数、ResultSection 展开率，为后续数据分析提供指标（埋点 ID：`hero_cta_click`, `result_section_toggle`）。

# layoutPrefs store 设计
- **数据结构**：
  ```ts
  interface LayoutPrefs {
    heroStepTooltipShown: boolean;
    creationSections: Record<'character' | 'script' | 'voice' | 'advanced', boolean>;
    resultSectionCollapsed: boolean;
    lastGuideTs?: number;
  }
  ```
- **初始化**：在 `useLayoutPrefsStore.ts` 中从 `localStorage.getItem('layout_prefs')` 读取并 JSON.parse，失败时回落到默认值；每次修改后 `requestIdleCallback` 写回，避免频繁同步。
- **暴露 API**：`toggleCreationSection(id)`, `setResultSectionCollapsed(value)`, `markHeroTooltipSeen()`, `resetPrefs()`。在 `App.vue` 通过 `storeToRefs` 获取，传入 `PreparationPanel`、`CreationPanel`、`MonitorPanel` 以保持状态一致。
- **移动端兼容**：当检测到 `isMobile` 时，`creationSections` 默认全部折叠，仅保留当前互动段展开；恢复桌面模式时依然读取 store 值，不做强制覆盖。

# 埋点方案
- **事件列表**：
  - `hero_cta_click`：点击“创建新任务”触发，payload 包含 `job_id`, `task_status`, `polling_active`。
  - `hero_monitor_click`：点击“查看监控”或抽屉按钮触发，payload 记录 `job_id`, `overall_progress`.
  - `result_section_toggle`：ResultAssetSection 展开/收起时触发，payload 附 `job_id`, `collapsed`.
  - `stage_timeline_hover`：用户查看阶段 tooltip 时触发，payload 包含 `stage_id`, `state`, `duration_ms`.
  - `layout_pref_reset`：用户点击重置布局偏好时触发。
- **上报机制**：统一使用 `useAnalytics()` composable，内部封装 `fetch('/api/analytics', ...)` 或控制台打印（开发模式）。为避免噪音，hover 事件做节流（同一阶段 10 秒内只上报一次）。
- **可视化**：将埋点指标同步到 `doc/工作流.md`，说明如何解读 CTA 点击率、ResultSection 使用率，便于产品评估布局升级价值。
# 任务清单
## 线框 / 英雄区 / 文案
[ ] 根据方案 B 的三段结构输出详细线框稿（桌面/移动双版本）。
[ ] 在 hero 区新增步骤提示条的 UI 文案，不更动其他区域，验证视觉效果。
[ ] 将 hero 区添加“创建任务” CTA，点击滚动到创建区。
[ ] 与产品/研发确认 hero 区新增步骤提示条的文案与数据来源。
[ ] 定义“步骤提示条”在不同任务状态下的颜色/图标规范。
[ ] 设计“准备区”卡片布局，将 API Key 工具条与任务列表并排展示。
[ ] 为移动端 hero pill 与 CTA 排列输出专用线框，并验证 768px 临界点的排版。
[ ] 确认 hero CTA 埋点（`hero_cta_click`）与 ResultSection 埋点（`result_section_toggle`）的触发条件与上报路径。
## 布局 / 样式
[x] 新增 `workspace` 布局容器，暂时包裹原有 `DashboardGrid`，不改内部组件。
[x] 创建 `workspace__column` 样式，预留左右分栏的 CSS 变量。
[x] 为未来的 `PreparationPanel`、`CreationPanel`、`MonitorPanel` 预留挂载点（占位 section）。
[x] 在布局层面替代 `DashboardGrid`，让左列包含 `PreparationPanel` + `CreationPanel`，右列包含 `MonitorPanel`。
[x] 重新排列 `DashboardGrid` 布局，使准备区/创作区占左列，监控区占右列。
[x] 更新全局样式文件，增加 `workspace`、`column-left/right` 等新类。
[x] 调整媒体查询，让窄屏下按“准备→创作→监控”堆叠显示。
[x] 调整 CSS 变量与媒体查询，确保左右分栏在 >1024px 时对齐。
[x] 为移动端定义堆叠顺序和折叠默认状态（准备→创作→监控）。
[ ] 清理遗留 `.dashboard-grid` 样式和未使用的容器，避免与 `workspace` 布局冲突。
[ ] 拆分创建表单为“角色”“脚本”“音色”“高级”四个折叠段的交互稿。
[ ] 设计右侧实时预估组件（字数/时长/成本）的粘性展示方式，并决定在折叠段中的位置。
## 数据与组件梳理
### 基础数据与方法
[x] 梳理现有 `App.vue` 中各卡片的模板/脚本分布，记录依赖关系。（基于首次拆分完成）
[x] 列出 ProgressPanel、MaterialPanel、移动端抽屉等现有组件需要保留的行为清单。
[x] 拆分 API Key 输入、任务列表、表单、进度、素材所使用的数据/方法，整理成映射表。（`PreparationPanel`/`CreationPanel` 已落地）
[x] 梳理 API Key 相关的方法（保存/清除/刷新余额），包装成独立函数，便于传入组件。
[x] 梳理任务列表操作（select/remove/refresh），准备迁移到 `PreparationPanel`。
[x] 梳理刷新/轮询控制逻辑，准备以 props/emit 形式下发。
[x] 梳理创建表单字段与验证逻辑，准备拆到 `CreationPanel`。
[x] 梳理角色上传与 FilePond 逻辑，评估如何通过 ref 传递。
[x] 梳理进度相关的 computed/watch（stageStatus、视频播放器），准备整合到 `MonitorPanel`。
[x] 梳理素材路径生成逻辑（materialItems），准备拆到 `MonitorPanel`。
[x] 设计 `PreparationPanel` 的 props/emit 列表并记录在注释/文档中。
[x] 设计 `CreationPanel` 的 props/emit 列表并记录在注释/文档中。
[x] 设计 `MonitorPanel` 的 props/emit 列表并记录在注释/文档中。
### PreparationPanel
[x] 将 `PreparationPanel` 挂载到 App.vue，先仅传入 API Key 状态/方法。
[x] 验证 `PreparationPanel` 保存/清除/刷新余额的动作能正确工作。
[x] 将任务历史数据/操作逐个传入 `PreparationPanel`，保留“最新 + 更多”逻辑。
[x] 调整 `PreparationPanel` 中文案和错误展示，保持与旧卡片一致。
[x] 逐步移除旧 API Key 卡片模板，改用 `PreparationPanel` 输出。
[x] 在 `PreparationPanel` 中加入轮询控制按钮，并连接 `togglePolling`。
[x] 在 `PreparationPanel` 中渲染“刷新任务”按钮，调用 `refreshSelectedTask`。
[x] 将 API Key 卡片缩减逻辑接入新的准备区视图。
[x] 评估任务列表 + API Key 同卡片后的 store 交互，更新事件流。
[x] 编写新的 `PreparationPanel.vue` 外层组件骨架。
[x] 将现有任务列表子组件迁移到 `PreparationPanel` 并保持功能完整。
[x] 调整任务列表的空态文案以指向“先创建任务”操作。
[ ] 验证 API Key 工具条在移动端抽屉中的交互和可访问性。
[ ] 更新 Pinia store 中与布局相关的持久化键值（比如卡片折叠状态）。
[ ] 移除遗留 `frontend/src/components/panels/PreparationPanel.vue`，防止双版本并存。
### CreationPanel
[x] 将 `CreationPanel` 挂载到 App.vue，并传入表单初始值。
[x] 验证 `CreationPanel` 的输入变化能同步更新 App.vue 的状态。
[x] 将 FilePond ref 与 `handleAvatarFiles` 逻辑注入 `CreationPanel`。
[x] 将角色列表、角色选择、上传新角色流程迁移到 `CreationPanel`。
[x] 确认 `CreationPanel` 内提交事件调用原 `handleSubmit`，且验证逻辑仍生效。
[x] 将原 `task-card` 模板移除，改用 `CreationPanel` 输出。
[x] 将“上传新人物”交互改为折叠面板，默认收起，并把上传表单移出主流程。
[x] 重构创建表单模板，按折叠段拆分为独立结构。
[x] 重新布局 FilePond 区域，保证在折叠展开时高度稳定。
[x] 在脚本段加入字数/时长/成本浮动提示，不依赖滚动查看。
[ ] 拆分创建表单为“角色”“脚本”“音色”“高级”四个折叠段的交互实现，并把折叠状态持久化。
[ ] 设计并实现 `CostEstimateBadge` 粘性组件，让字数/时长/成本在滚动时保持可见。
[ ] 为角色列表添加搜索/筛选交互，并评估 `CharacterRecord` 数据结构是否需要新增标签字段。
[ ] 将上传新人物交互迁移到独立 modal/dialog，并串联原文件上传逻辑。
[ ] 更新高级选项折叠的默认状态与入口文案。
### 监控区 / 素材
[x] 将 `MonitorPanel` 挂载到 App.vue，同时传入阶段状态、资产链接。
[x] 在 `MonitorPanel` 内复用现有 ProgressPanel/MaterialPanel 或直接继承其样式。
[x] 验证 `MonitorPanel` 中视频播放器初始化/销毁逻辑，确保不重复创建实例。
[x] 将素材列表交互（复制/打开链接）传递给 `MonitorPanel`。
[x] 将视频下载/复制链接按钮从 `App.vue` 挪到 `MonitorPanel` 并保持功能。
[x] 调整移动端抽屉逻辑，让其读取 `MonitorPanel` 的数据或复用旧组件。
[x] 设计并实现“状态消息 + Trace ID”小组件，固定在监控区顶部。
[x] 在监控区加入手动刷新与轮询切换按钮的新位置。
[ ] 重新定义监控区内阶段列表的数据结构，加入开始/结束时间与 `StageTimelineEntry`。
[ ] 拆分 `MonitorPanel` 子组件（`StageTimeline`, `StatusCard`, `ResultAssetSection`, `MaterialList`），并为每个子组件定义 props/emit。
[ ] 在 MonitorPanel 中加入日志滑出层，展示 `TaskResponse.logs`、trace id 与复制按钮。
[x] 新建 `MonitorPanel.vue` 承载阶段时间线、状态信息与日志入口。
[ ] 将视频播放器和素材列表封装为 `ResultAssetSection`，默认隐藏，任务完成后展开。
[ ] 为 `ResultAssetSection` 实现展开状态持久化（localStorage）与 warning badge 逻辑。
[x] 修改素材列表模板，仅默认展示公网 URL，本地路径放入“技术详情”折叠。
[ ] 在移动端抽屉中实现 ResultAssetSection 的 accordion 展示，并验证粘性按钮表现。
## 文档 / 测试 / 协作
[ ] 重新测试 hero CTA、API Key 操作、任务创建、进度轮询、素材播放等核心路径。
[ ] 更新 `plan-UI.md` 或相关设计文档，记录渐进式替换方案。
[ ] 在 `doc/工作流.md` 中补充新的布局和操作路径说明。
[ ] 更新 `doc/frontend_task_flow.md`（或新增文档）描述步骤提示条与阶段映射。
[ ] 为 `PreparationPanel`、`CreationPanel`、`MonitorPanel` 编写单元测试覆盖折叠逻辑。
[ ] 在端到端测试脚本中增加“创建任务→查看监控区→查看结果”完整旅程。
[ ] 对新布局进行可用性走查，收集制作者反馈并迭代。
[ ] 与后端对齐素材 API 字段调整（若新增 `public_url` 首选逻辑）。
[ ] 在 README 加入新版 UI 截图与操作说明。
[ ] 完成一次移动端真机测试，验证折叠/抽屉和播放器行为。
[ ] 设计 Pinia `layoutPrefs` store（字段、默认值、序列化策略），并在文档中说明与组件的绑定方式。
[ ] 补充埋点方案，定义 hero CTA、ResultSection 折叠、监控日志打开等事件的上报字段。
