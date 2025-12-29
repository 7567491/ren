# RCA 分析：进度条和日志无法显示问题

## 问题现象
用户点击"开始生成"后，浏览器中：
- ✅ 任务创建成功（status: "running"）
- ❌ 进度条始终显示 0%
- ❌ 日志区域显示"等待日志输出..."
- ❌ 用户感觉系统卡住了

## 五个为什么分析

### 问题1：为什么进度条没有显示？
**答：** 因为 TaskManager 中的 progress 字段没有更新（始终为 0.0）

### 问题2：为什么 progress 字段没有更新？
**答：** 因为 ad-back.py 作为子进程运行，它的进度信息无法传递给 api_server.py 的 TaskManager

### 问题3：为什么子进程的进度信息无法传递？
**答：** 因为 ad-back.py 和 api_server.py 之间**没有进程间通信（IPC）机制**

**证据：**
```python
# py/api_server.py:491-492
process = subprocess.Popen(...)
returncode = process.wait()  # 只等待结束，无法获取中间状态
```

### 问题4：为什么没有 IPC 机制？
**答：** 因为当前架构是"一次性执行"模式：
- `api_server.py` 启动子进程后就等待结束
- 只能通过进程退出码判断成功/失败
- 无法获取执行过程中的中间状态

### 问题5：为什么采用这种架构？
**答：** 因为 ad-back.py 原本是独立的 CLI 脚本，后来为了提供 Web API，简单地用 api_server.py 包装了一层，但**没有重构进度上报机制**

## 根本原因（可控的）

**核心问题：父子进程之间缺乏实时通信机制**

```
ad-back.py (子进程)      api_server.py (父进程)
┌─────────────┐          ┌──────────────┐
│ 执行任务     │ ❌ 无通信  │ TaskManager  │
│ 写日志到文件 │ ───────→ │ (progress=0) │
└─────────────┘          └──────────────┘
                              ↓
                         前端轮询API
                         拿到的永远是 0%
```

## 所有可能的原因列表

### ✅ 已排除的原因
1. **前端代码问题** ❌
   - 前端轮询逻辑正常（frontend/index.html:798-804）
   - 每2秒调用 `/api/jobs/{job_id}` 和 `/api/jobs/{job_id}/log`
   - 日志增量更新逻辑正确（offset机制）

2. **API端点不存在** ❌
   - `/api/jobs/{job_id}` 端点存在（api_server.py:376-384）
   - `/api/jobs/{job_id}/log` 端点存在（api_server.py:387-423）

3. **日志文件不存在** ❌
   - 日志文件正常生成：`/home/wave/output/aka-12271701/log.txt`
   - 文件大小 21KB，内容完整

4. **TaskManager读写问题** ❌
   - TaskManager正常工作，能正确保存到 `temp/jobs.json`
   - 状态能正确更新为 "running" → "failed"

### ⚠️ 真正的原因

#### 原因1：进度更新机制缺失 ⭐ **根本原因**
**位置：** `py/api_server.py:446-519` (run_video_generation函数)

**问题：**
```python
# 只在任务开始时更新一次状态
task_manager.update_status(job_id, 'running', '正在生成视频...')

# 启动子进程
process = subprocess.Popen(...)

# 等待子进程结束（阻塞）
returncode = process.wait()

# 只在任务结束时更新状态
if returncode == 0:
    task_manager.update_status(job_id, 'succeeded', '视频生成成功')
    task_manager.update_progress(job_id, 1.0, '已完成')
```

**缺失：**
- 在 `process.wait()` 期间，**没有任何进度更新**
- 子进程 ad-back.py 的执行进度**无法传递回父进程**
- 前端轮询时，永远拿到 progress=0.0

**影响：**
- 用户看到的进度条永远是 0%
- 用户不知道任务是否在执行
- 用户体验极差，感觉系统卡死

---

#### 原因2：日志文件延迟刷新 ⭐ **次要原因**
**位置：** `py/ad-back.py:409` (log函数)

**问题：**
```python
def log(message, level="INFO"):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(formatted_message)
    # 文件关闭后才会刷新到磁盘
```

**缺失：**
- 没有显式调用 `f.flush()` 或 `os.fsync()`
- Python文件对象默认有缓冲区
- 日志可能延迟数秒才写入磁盘

**影响：**
- 前端读取日志时，可能读到空文件或旧内容
- 日志显示滞后，用户看不到实时进展

---

#### 原因3：子进程stdout重定向到文件
**位置：** `py/api_server.py:480-487`

**问题：**
```python
with open(log_file, 'w', encoding='utf-8') as log_f:
    process = subprocess.Popen(
        cmd,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        ...
    )
```

**缺失：**
- stdout直接重定向到文件，父进程无法读取
- 无法解析子进程输出来提取进度信息
- 即使子进程打印进度，父进程也无法感知

---

#### 原因4：ad-back.py没有进度上报API
**位置：** `py/ad-back.py` 全文

**问题：**
- ad-back.py 是独立的 CLI 脚本
- 没有设计"进度上报"接口
- 不知道如何通知父进程当前进度

**缺失：**
- 没有调用 TaskManager 的 `update_progress()` 方法
- 没有通过任何机制（文件、socket、queue）传递进度
- 完全不知道自己在 API 模式下运行

---

#### 原因5：缺少checkpoint文件解析
**潜在机会：**
- ad-back.py 会生成 `00_checkpoint.json` 文件（ad-back.py:1353）
- checkpoint包含已完成的步骤信息
- 但 api_server.py **没有解析这个文件来推断进度**

**如果实现：**
```python
# 伪代码
while process.poll() is None:
    checkpoint = parse_checkpoint(job_id)
    progress = calculate_progress(checkpoint)
    task_manager.update_progress(job_id, progress)
    await asyncio.sleep(2)
```

---

## 验证方法

### 验证1：检查TaskManager状态
```bash
cat /home/wave/temp/jobs.json | python3 -m json.tool | grep -A10 "aka-12271701"
```
**结果：** progress始终为0.0 ✅

### 验证2：检查日志文件
```bash
ls -lh /home/wave/output/aka-12271701/log.txt
```
**结果：** 文件存在且大小21KB ✅

### 验证3：检查API端点
```bash
curl http://localhost:18000/api/jobs/aka-12271701
```
**结果：** 返回JSON，progress=0.0 ✅

### 验证4：检查日志API
```bash
curl http://localhost:18000/api/jobs/aka-12271701/log?lines=10
```
**结果：** 应该返回日志内容（待验证）

---

## 解决方案优先级

### 方案1：轻量级 - 解析checkpoint文件 ⭐ **推荐**
**难度：** ⭐⭐ (简单)
**效果：** ⭐⭐⭐⭐ (中等精度进度)

**实现：**
在 `run_video_generation` 的 `process.wait()` 改为异步轮询：
```python
while process.poll() is None:
    # 解析checkpoint文件
    checkpoint_file = Path(OUTPUT_DIR) / job_id / '00_checkpoint.json'
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)

        # 计算进度：已完成步骤/总步骤
        total_steps = ['story', 'images', 'videos', 'composition']
        completed = len(checkpoint.get('completed_steps', []))
        progress = completed / len(total_steps)

        task_manager.update_progress(job_id, progress, f'执行中 {completed}/{len(total_steps)}')

    await asyncio.sleep(2)
```

**优点：**
- 无需修改 ad-back.py
- 利用现有的checkpoint机制
- 实现简单，风险低

**缺点：**
- 进度精度较粗（只有4个阶段）
- 无法显示"图像生成 3/6"这种细节

---

### 方案2：中等 - 解析日志文件提取进度 ⭐⭐
**难度：** ⭐⭐⭐ (中等)
**效果：** ⭐⭐⭐⭐⭐ (高精度进度)

**实现：**
在日志中添加特殊标记，api_server解析：
```python
# ad-back.py 中添加
def report_progress(stage, current, total):
    """写入可解析的进度标记"""
    print(f"[PROGRESS] {stage}:{current}/{total}")

# api_server.py 中解析
def parse_log_for_progress(log_file):
    with open(log_file, 'r') as f:
        lines = f.readlines()

    for line in reversed(lines):
        if '[PROGRESS]' in line:
            # 解析 "images:3/6" 等
            match = re.search(r'\[PROGRESS\] (\w+):(\d+)/(\d+)', line)
            if match:
                stage, current, total = match.groups()
                return calculate_overall_progress(stage, int(current), int(total))
    return 0.0
```

**优点：**
- 进度精度高（可以显示"图像生成 3/6"）
- 用户体验好

**缺点：**
- 需要修改 ad-back.py
- 日志解析可能有延迟

---

### 方案3：重量级 - 使用消息队列（Redis/RabbitMQ） ⭐⭐⭐
**难度：** ⭐⭐⭐⭐⭐ (复杂)
**效果：** ⭐⭐⭐⭐⭐ (实时进度)

**实现：**
```python
# ad-back.py
import redis
r = redis.Redis()

def report_progress(job_id, progress):
    r.set(f'progress:{job_id}', progress)

# api_server.py
async def monitor_progress(job_id):
    while True:
        progress = r.get(f'progress:{job_id}')
        task_manager.update_progress(job_id, float(progress))
        await asyncio.sleep(1)
```

**优点：**
- 实时性最好
- 架构最健壮

**缺点：**
- 引入新依赖（Redis）
- 实现复杂度高
- 过度设计（对当前需求）

---

### 方案4：终极 - 重构为API模式
**难度：** ⭐⭐⭐⭐⭐ (非常复杂)
**效果：** ⭐⭐⭐⭐⭐ (完美)

**实现：**
将 ad-back.py 的核心逻辑抽取为类库，api_server 直接调用：
```python
# 不再使用subprocess，而是直接导入
from py.ad_back import VideoGenerator

async def run_video_generation(job_id, config):
    generator = VideoGenerator(job_id, config)

    # 注册进度回调
    generator.on_progress = lambda p: task_manager.update_progress(job_id, p)

    # 直接调用
    await generator.run()
```

**优点：**
- 进度上报完美
- 性能最好（无子进程开销）
- 架构最清晰

**缺点：**
- 需要大量重构
- 风险高
- 开发周期长

---

## 推荐方案

**立即实施：** 方案1（解析checkpoint文件）
**后续优化：** 方案2（解析日志进度标记）

---

## TDD 验证计划

### 测试1：验证checkpoint解析
```python
# test/test_progress_tracking.py
def test_parse_checkpoint():
    checkpoint = {
        'completed_steps': ['story', 'images']
    }
    progress = calculate_progress(checkpoint)
    assert progress == 0.5  # 2/4
```

### 测试2：验证进度更新
```python
async def test_progress_updates():
    job_id = create_test_job()
    await asyncio.sleep(5)

    task = task_manager.get_task(job_id)
    assert task['progress'] > 0.0  # 不再是0
```

### 测试3：验证日志显示
```python
async def test_log_display():
    job_id = create_test_job()
    await asyncio.sleep(2)

    response = await client.get(f'/api/jobs/{job_id}/log')
    assert len(response.json()['lines']) > 0
```

---

## 修复清单

- [ ] 实现checkpoint文件解析
- [ ] 修改run_video_generation为异步轮询
- [ ] 添加进度计算逻辑
- [ ] 在ad-back.py中添加显式flush
- [ ] 编写单元测试
- [ ] 编写集成测试
- [ ] 验证前端显示正常
- [ ] 文档更新
