# Git Worktree 三路并行开发方案

## 📋 战略总览

本方案基于 **design.md**、**plan.md** 和 **CLAUDE.md**，设计一套 git worktree 工作流，让 **三个 Claude CLI 实例** 在不同分支并行开发数字人生成系统的三大模块，最大化开发效率并最小化文件冲突。

---

## 🎯 模块划分原则

根据 plan.md 的 60 个任务和项目架构，将开发工作分为三条相对独立的路径：

### 路径A：前端界面与交互
**负责人**：Claude CLI #1
**核心任务**：plan.md 任务 1-14
**主要职责**：用户界面、表单组件、状态轮询、视频播放器

### 路径B：后端API与服务层
**负责人**：Claude CLI #2
**核心任务**：plan.md 任务 15-23 + 32-37
**主要职责**：REST API、数字人服务集成、存储管理

### 路径C：核心业务逻辑
**负责人**：Claude CLI #3
**核心任务**：plan.md 任务 24-31 + 38-42
**主要职责**：任务状态机、配置加载、异常处理、日志

---

## 🌲 Git Worktree 架构设计

### 分支策略

```
main (主分支，保护分支)
├── feature/frontend-ui          (路径A - 前端开发)
├── feature/backend-api          (路径B - 后端API)
└── feature/core-logic           (路径C - 核心逻辑)
```

### Worktree 目录结构

```
/home/ren/                       # 主工作目录（main分支，只读参考）
├── .git/                        # Git 仓库元数据
├── ...                          # 现有项目文件
│
/home/ren-frontend/              # Worktree #1 - 前端开发
├── frontend/                    # 🔥 主战场
├── doc/                         # 📖 参考文档
├── CLAUDE.md                    # 项目指引
└── plan.md                      # 任务清单

/home/ren-backend/               # Worktree #2 - 后端API
├── py/api/                      # 🔥 主战场
├── py/services/                 # 🔥 主战场
│   ├── digital_human_service.py # 新增
│   └── storage_service.py       # 新增
├── ad-back.py                   # 后端入口
├── doc/数字人.md                # API协议
└── requirements.txt             # 依赖管理

/home/ren-core/                  # Worktree #3 - 核心逻辑
├── py/function/                 # 🔥 主战场
│   ├── task_runner.py           # 新增
│   └── config_loader.py         # 升级
├── py/services/
│   └── task_manager.py          # 任务队列
├── config.yaml                  # 配置文件
└── .env.example                 # 环境变量模板
```

---

## 🚀 实施步骤

### 阶段0：准备主分支

在 `/home/ren` 主目录执行：

```bash
# 确保在 main 分支且代码已提交
cd /home/ren
git status
git add .
git commit -m "chore: 保存当前进度，准备并行开发"

# 创建三个功能分支
git branch feature/frontend-ui
git branch feature/backend-api
git branch feature/core-logic
```

### 阶段1：创建 Worktree

```bash
# Worktree #1 - 前端开发
git worktree add ../ren-frontend feature/frontend-ui

# Worktree #2 - 后端API
git worktree add ../ren-backend feature/backend-api

# Worktree #3 - 核心逻辑
git worktree add ../ren-core feature/core-logic
```

### 阶段2：启动三个 Claude CLI 实例

#### Claude CLI #1 (前端开发)
```bash
cd /home/ren-frontend
claude

# 首条指令
"根据 plan.md 任务 1-14，开发前端界面。重点文件：
- frontend/ (全部)
- 参考 CLAUDE.md 的前端技术栈
- 参考 doc/数字人.md 的 API 协议"
```

#### Claude CLI #2 (后端API)
```bash
cd /home/ren-backend
claude

# 首条指令
"根据 plan.md 任务 15-23 和 32-37，开发后端API。重点文件：
- py/api/ (全部)
- py/services/digital_human_service.py (新建)
- py/services/storage_service.py (新建)
- ad-back.py (入口改造)
- 严格遵循 doc/数字人.md 的 API 协议"
```

#### Claude CLI #3 (核心逻辑)
```bash
cd /home/ren-core
claude

# 首条指令
"根据 plan.md 任务 24-31 和 38-42，开发核心业务逻辑。重点文件：
- py/function/task_runner.py (新建)
- py/function/config_loader.py (升级)
- py/services/task_manager.py (升级)
- 设计任务状态机与异常处理"
```

---

## 📦 文件责任矩阵

| 文件/目录 | 路径A (前端) | 路径B (API) | 路径C (核心) | 冲突风险 |
|-----------|-------------|------------|-------------|---------|
| `frontend/**` | ✅ 主要 | ❌ 不碰 | ❌ 不碰 | 🟢 无 |
| `py/api/**` | ❌ 不碰 | ✅ 主要 | ❌ 不碰 | 🟢 无 |
| `py/services/digital_human_service.py` | ❌ 不碰 | ✅ 主要 | 🔶 读取 | 🟡 低 |
| `py/services/storage_service.py` | ❌ 不碰 | ✅ 主要 | 🔶 读取 | 🟡 低 |
| `py/services/task_manager.py` | ❌ 不碰 | 🔶 读取 | ✅ 主要 | 🟡 低 |
| `py/function/task_runner.py` | ❌ 不碰 | ❌ 不碰 | ✅ 主要 | 🟢 无 |
| `py/function/config_loader.py` | ❌ 不碰 | 🔶 读取 | ✅ 主要 | 🟡 低 |
| `ad-back.py` | ❌ 不碰 | ✅ 主要 | 🔶 读取 | 🟡 低 |
| `config.yaml` | 🔶 读取 | 🔶 读取 | ✅ 主要 | 🟡 低 |
| `requirements.txt` | 🔶 追加 | ✅ 主要 | 🔶 追加 | 🔴 中 |
| `CLAUDE.md` | 🔶 读取 | 🔶 读取 | 🔶 读取 | 🟢 无 |
| `doc/数字人.md` | 🔶 读取 | 🔶 读取 | 🔶 读取 | 🟢 无 |

**图例**：
- ✅ 主要 = 主要负责该文件的开发
- 🔶 读取 = 可读取但不修改（或仅追加注释）
- ❌ 不碰 = 完全不接触该文件

---

## 🔥 冲突预防机制

### 1. 高风险文件 - requirements.txt
**问题**：三个路径都可能新增依赖。

**解决方案**：
```bash
# 各路径在本地维护独立的依赖文件
# 路径A: frontend/package.json (前端依赖，不冲突)
# 路径B: py/requirements-api.txt (临时)
# 路径C: py/requirements-core.txt (临时)

# 合并时手动整合
cat requirements.txt \
    py/requirements-api.txt \
    py/requirements-core.txt \
    | sort | uniq > requirements-final.txt
```

### 2. 中风险文件 - config.yaml
**问题**：核心逻辑可能新增配置项。

**解决方案**：
- 路径C 在 `config.yaml` 中新增节点（如 `task_runner:`, `retry_policy:`）
- 路径A/B 仅读取现有配置，不新增字段
- 冲突时以路径C 的版本为准

### 3. 接口文件 - py/services/*
**问题**：API层调用服务层的接口。

**解决方案**：
- **先定义接口，后实现**：
  - Day 1：路径B 先定义服务层接口的 **函数签名**（docstring + type hints）
  - Day 2：路径C 实现具体业务逻辑
  - 使用 Python 的 `typing.Protocol` 或抽象基类确保接口稳定

```python
# 路径B 在 py/services/digital_human_service.py 中先定义接口
from typing import Protocol

class DigitalHumanServiceProtocol(Protocol):
    def generate_avatar(self, prompt: str) -> str:
        """生成头像，返回 image_url"""
        ...

    def generate_speech(self, text: str, voice_id: str) -> str:
        """生成语音，返回 audio_url"""
        ...

    def generate_video(self, image_url: str, audio_url: str) -> str:
        """生成唇同步视频，返回 video_url"""
        ...

# 路径C 实现具体逻辑
class DigitalHumanService(DigitalHumanServiceProtocol):
    def generate_avatar(self, prompt: str) -> str:
        # 实现细节...
        pass
```

---

## 🔄 定期同步策略

### 每日同步（推荐）

各路径在每天工作结束时，将 **main 分支的最新代码** 合并到自己的分支：

```bash
# 在各自的 worktree 中执行
cd /home/ren-frontend  # 或 ren-backend、ren-core

# 拉取主分支最新代码
git fetch origin main

# 合并到当前功能分支
git merge origin/main

# 如有冲突，按照"文件责任矩阵"解决
# - 如果冲突文件属于自己的责任范围，保留自己的改动
# - 如果属于其他路径，保留 main 的版本并重新适配
```

### 里程碑同步（关键节点）

以下时机必须同步：
1. **接口定义完成**（Day 1 下班前）：路径B 提交服务层接口到 main
2. **前端Mock完成**（Day 2）：路径A 提交带 Mock 数据的前端到 main
3. **后端API完成**（Day 3）：路径B 提交可调用的 REST API 到 main
4. **核心逻辑完成**（Day 4）：路径C 提交状态机和任务调度到 main

---

## 🧪 集成测试阶段

### 阶段3：分支合并策略

```bash
# 在主目录 /home/ren 执行
cd /home/ren

# 步骤1：合并前端分支
git checkout main
git merge feature/frontend-ui
# 解决冲突（如果有）
git commit -m "feat: 合并前端界面开发"

# 步骤2：合并后端API分支
git merge feature/backend-api
# 解决冲突（重点关注 requirements.txt, config.yaml）
git commit -m "feat: 合并后端API开发"

# 步骤3：合并核心逻辑分支
git merge feature/core-logic
# 解决冲突
git commit -m "feat: 合并核心业务逻辑"

# 步骤4：集成测试
source venv/bin/activate
pip install -r requirements.txt

# 启动后端
python3 ad-back.py --port 18005 &

# 启动前端
cd frontend && npm run dev &

# 运行测试
python3 py/test_network.py --digital-human
pytest test/
```

---

## 📊 并行开发时间表

| 时间 | 路径A (前端) | 路径B (API) | 路径C (核心) | 同步点 |
|------|-------------|------------|-------------|--------|
| **Day 0** | 创建 Worktree | 创建 Worktree | 创建 Worktree | ⚙️ 初始化 |
| **Day 1** | 表单组件开发 | 定义服务接口 | 设计状态机 | 🔄 接口定义 |
| **Day 2** | 轮询器+Mock | 实现 REST API | 任务调度器 | 🔄 Mock数据 |
| **Day 3** | 播放器组件 | 集成 WaveSpeed | 配置加载器 | 🔄 API上线 |
| **Day 4** | 错误处理UI | 存储服务 | 异常处理+日志 | 🔄 核心完成 |
| **Day 5** | 前端构建 | API文档 | 测试脚本 | ✅ 集成测试 |

---

## 🛠️ 快速命令参考

### 查看所有 Worktree
```bash
git worktree list
```

### 清理 Worktree
```bash
# 完成开发后清理
git worktree remove /home/ren-frontend
git worktree remove /home/ren-backend
git worktree remove /home/ren-core

# 删除功能分支（可选）
git branch -d feature/frontend-ui
git branch -d feature/backend-api
git branch -d feature/core-logic
```

### 在 Worktree 间切换
```bash
# 方法1: cd 切换目录
cd /home/ren-frontend

# 方法2: 使用 tmux/screen 多窗口管理
tmux new-session -s frontend -c /home/ren-frontend
tmux new-window -t frontend -n backend -c /home/ren-backend
tmux new-window -t frontend -n core -c /home/ren-core
```

---

## 🎓 Claude CLI 使用指南

### 传递文件策略

#### Claude CLI #1 (前端)
```bash
# 在 /home/ren-frontend 启动
claude

# 初始化时明确范围
"我负责前端开发（plan.md 任务1-14），主要文件：
- frontend/ (全部开发)
- 参考 CLAUDE.md 和 doc/数字人.md
- 不修改 py/ 目录
- 如需 API 接口，先使用 Mock 数据"

# 后续对话时持续强调边界
"继续开发表单组件，不要修改后端代码"
```

#### Claude CLI #2 (后端API)
```bash
cd /home/ren-backend
claude

"我负责后端API开发（plan.md 任务15-23, 32-37），主要文件：
- py/api/ (全部开发)
- py/services/digital_human_service.py (新建)
- py/services/storage_service.py (新建)
- ad-back.py (入口改造)
- 不修改 frontend/ 和 py/function/
- 严格遵循 doc/数字人.md 的协议"
```

#### Claude CLI #3 (核心逻辑)
```bash
cd /home/ren-core
claude

"我负责核心业务逻辑开发（plan.md 任务24-31, 38-42），主要文件：
- py/function/task_runner.py (新建)
- py/function/config_loader.py (升级)
- py/services/task_manager.py (升级)
- 不修改 frontend/ 和 py/api/
- 专注于状态机、配置、异常处理、日志"
```

### 跨路径协作示例

#### 场景1：前端需要 API 返回格式
```bash
# Claude CLI #1 (前端)
"我需要知道 POST /api/tasks 的返回格式，去读取 py/api/routes_digital_human.py 的接口定义"

# 如果文件不存在，使用约定格式
{
  "task_id": "aka-20251230-001",
  "status": "pending_avatar",
  "message": "任务已创建",
  "poll_url": "/api/tasks/aka-20251230-001"
}
```

#### 场景2：后端需要调用核心逻辑
```bash
# Claude CLI #2 (后端API)
"我需要调用任务状态机，先检查 py/function/task_runner.py 是否已定义接口"

# 如果未定义，先定义接口规范
class TaskRunner:
    def run_step_avatar(self, task_id: str, params: dict) -> dict:
        """执行形象生成步骤"""
        pass

    def run_step_speech(self, task_id: str, params: dict) -> dict:
        """执行语音生成步骤"""
        pass

    def run_step_video(self, task_id: str, params: dict) -> dict:
        """执行唇同步步骤"""
        pass
```

---

## ⚠️ 常见问题与解决

### Q1: Worktree 创建失败
```bash
# 错误: fatal: '/home/ren-frontend' already exists
# 解决: 先删除目录
rm -rf /home/ren-frontend
git worktree add ../ren-frontend feature/frontend-ui
```

### Q2: 合并时出现大量冲突
```bash
# 原因: 未遵循"文件责任矩阵"，多人改同一文件
# 解决:
git merge --abort  # 先取消合并
# 与团队对齐，明确各自的文件责任范围
# 重新合并时使用策略
git merge -X theirs feature/backend-api  # 优先采用某个分支的版本
```

### Q3: Claude CLI 误修改其他路径的文件
```bash
# 预防: 在每次启动 Claude CLI 时明确说明
"IMPORTANT: 我只负责 frontend/ 目录，绝对不要修改 py/ 下的任何文件"

# 如果已修改: 使用 git checkout 恢复
git checkout HEAD -- py/  # 恢复 py/ 目录的所有改动
```

---

## 📝 任务分配详细清单

### 路径A：前端界面（任务1-14）

| 任务ID | 描述 | 主要文件 | 预估时间 |
|--------|------|---------|---------|
| 1 | 梳理 API 参数清单 | doc/数字人.md | 1h |
| 2 | 起草前端原型图 | doc/frontend-prototype.md | 2h |
| 3 | 创建 Vite/Vue 项目 | frontend/ | 2h |
| 4 | 实现表单字段 | frontend/src/components/TaskForm.vue | 4h |
| 5 | Debug 模式开关 | frontend/src/components/DebugSwitch.vue | 2h |
| 6 | 头像上传组件 | frontend/src/components/AvatarUpload.vue | 3h |
| 7 | 表单提交逻辑 | frontend/src/api/tasks.js | 3h |
| 8 | 状态轮询器 | frontend/src/composables/usePolling.js | 4h |
| 9 | 进度面板 | frontend/src/components/ProgressPanel.vue | 4h |
| 10 | 播放器卡片 | frontend/src/components/PlayerCard.vue | 4h |
| 11 | 成本估算组件 | frontend/src/components/CostEstimate.vue | 2h |
| 12 | 错误提示弹层 | frontend/src/components/ErrorDialog.vue | 3h |
| 13 | 环境变量支持 | frontend/.env.example | 1h |
| 14 | 构建脚本 | frontend/vite.config.js | 2h |

**小计**：37小时

### 路径B：后端API（任务15-23, 32-37）

| 任务ID | 描述 | 主要文件 | 预估时间 |
|--------|------|---------|---------|
| 15 | ad-back.py 参数解析 | ad-back.py | 2h |
| 16 | 加载 .env 验证密钥 | ad-back.py | 2h |
| 17 | 初始化 Flask/FastAPI | ad-back.py | 3h |
| 18 | 创建路由蓝图 | py/api/routes_digital_human.py | 2h |
| 19 | POST /api/tasks 请求模型 | py/api/routes_digital_human.py | 3h |
| 20 | POST /api/tasks 实现 | py/api/routes_digital_human.py | 4h |
| 21 | GET /api/tasks/<id> 实现 | py/api/routes_digital_human.py | 3h |
| 22 | POST /api/assets/upload | py/api/routes_digital_human.py | 4h |
| 23 | GET /api/health | py/api/routes_digital_human.py | 2h |
| 32 | 封装 Seedream 请求 | py/services/digital_human_service.py | 4h |
| 33 | 封装 MiniMax TTS | py/services/digital_human_service.py | 4h |
| 34 | 封装 Infinitetalk | py/services/digital_human_service.py | 5h |
| 35 | ExternalAPIError 定义 | py/services/digital_human_service.py | 2h |
| 36 | 指数退避重试 | py/services/digital_human_service.py | 3h |
| 37 | storage 本地输出 | py/services/storage_service.py | 3h |
| 38 | storage OSS 上传 | py/services/storage_service.py | 4h |

**小计**：50小时

### 路径C：核心逻辑（任务24-31, 39-42）

| 任务ID | 描述 | 主要文件 | 预估时间 |
|--------|------|---------|---------|
| 24 | 创建 task_runner | py/function/task_runner.py | 3h |
| 25 | 设计状态枚举 | py/function/task_runner.py | 2h |
| 26 | TaskContext 封装 | py/function/task_runner.py | 3h |
| 27 | run_step_avatar() | py/function/task_runner.py | 4h |
| 28 | run_step_speech() | py/function/task_runner.py | 4h |
| 29 | run_step_video() | py/function/task_runner.py | 5h |
| 30 | update_state() | py/function/task_runner.py | 2h |
| 31 | Debug/生产模式切换 | py/function/task_runner.py | 2h |
| 39 | config_loader 新增字段 | py/function/config_loader.py | 3h |
| 40 | 配置哈希校验 | py/function/task_runner.py | 2h |
| 41 | 全局异常处理 | py/api/__init__.py | 3h |
| 42 | 结构化日志 | py/function/logger.py | 4h |

**小计**：37小时

---

## 🎉 成功标准

开发完成的标志：

1. ✅ **前端**：可在浏览器访问 `http://localhost:5173`，提交表单后显示轮询状态
2. ✅ **后端**：`curl http://localhost:18005/api/health` 返回 200
3. ✅ **集成**：创建一个10秒数字人视频，从提交到播放全流程无报错
4. ✅ **测试**：`pytest test/` 通过所有单元测试
5. ✅ **文档**：`README.md` 和 `doc/` 更新完整

---

## 🔗 相关文档

- [CLAUDE.md](/home/ren/CLAUDE.md) - 项目开发指南
- [plan.md](/home/ren/doc/plan.md) - 60个任务清单
- [数字人.md](/home/ren/doc/数字人.md) - WaveSpeed API 协议
- [designw.md](/home/ren/designw.md) - 旧设计方案参考

---

**文档版本**：v1.0
**创建日期**：2025-12-30
**适用项目**：Digital Human Studio (数字人生成系统)
**Git 策略**：Worktree 三路并行开发

---

## 💡 UltraThink 深度分析

### 设计哲学

本方案的核心设计理念：

1. **最小依赖原则**：三个路径的文件依赖关系呈 **树状结构**，而非网状：
   ```
   前端 (UI) → 后端 (API) → 核心 (Logic)
   ├─ 无依赖     ├─ 依赖接口   ├─ 无外部依赖
   ```

2. **接口优先开发**：先定义契约（函数签名 + 类型注解），再各自实现，避免接口冲突。

3. **渐进式集成**：不等所有模块完成再集成，而是每日同步，持续集成。

4. **故障隔离**：任一路径出错不影响其他路径，可独立修复。

### 风险评估

| 风险类型 | 概率 | 影响 | 缓解措施 |
|---------|------|------|---------|
| requirements.txt 冲突 | 🔴 高 | 中 | 各路径维护独立文件，最后手动合并 |
| 接口定义不一致 | 🟡 中 | 高 | Day 1 强制同步接口定义 |
| Claude CLI 越界修改 | 🟡 中 | 中 | 启动时明确指令，定期 code review |
| 状态机设计分歧 | 🟢 低 | 高 | 路径C 独占设计权，其他路径仅读取 |

### 时间成本分析

- **串行开发**：37h + 50h + 37h = **124小时** ≈ 15.5 工作日
- **并行开发**：max(37h, 50h, 37h) = **50小时** ≈ 6.25 工作日
- **时间节省**：**59.7%**（假设三个 Claude CLI 完全并行）

### 适用场景

✅ **适合使用本方案的场景**：
- 项目模块边界清晰（前端/API/核心）
- 团队成员（或 AI 助手）>=3
- 开发周期紧张，需要加速交付

❌ **不适合的场景**：
- 模块高度耦合，无法拆分
- 需要频繁跨模块修改同一文件
- 团队规模 <3 人

---

**END OF DOCUMENT**
