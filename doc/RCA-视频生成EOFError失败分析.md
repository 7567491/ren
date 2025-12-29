# RCA 根因分析：视频生成 EOFError 失败问题

**分析日期**: 2025-12-27
**问题ID**: aka-12271649
**严重程度**: 高（导致视频生成完全失败）
**分析方法**: 5 Why + TDD验证

> 🆕 **2025-12-28 更新**：根据最新需求，系统现已统一接受 **1-10 个镜头**（shot_count）。下文保留2025-12-27问题排查时的日志与代码片段，仍会出现“2-10”范围的描述，用于记录当时的真实环境。

---

## 1. 问题现象

### 1.1 表面症状
```
Traceback (most recent call last):
  File "/home/wave/py/ad-back.py", line 4585, in <module>
    sys.exit(main())
  File "/home/wave/py/ad-back.py", line 3785, in main
    user_config = interactive_setup()
  File "/home/wave/py/ad-back.py", line 1083, in interactive_setup
    topic = input("请输入视频主题（如：Akamai推出AI推理云）: ").strip()
EOFError: EOF when reading a line
```

### 1.2 发生时间和环境
- **时间**: 2025-12-27 16:49
- **任务ID**: aka-12271649
- **运行模式**: API后台进程（非交互式）
- **触发条件**: 用户通过Web前端提交视频生成请求

---

## 2. 五个为什么（5 Why）深度分析

### 🔍 Why #1: 为什么会出现 EOFError？
**答**: 程序在非交互式环境（后台进程）中调用了 `input()` 函数

**证据**:
```python
# ad-back.py:1083
topic = input("请输入视频主题（如：Akamai推出AI推理云）: ").strip()
```

**环境特征**:
- API服务通过 `subprocess.Popen` 启动后台进程
- stdout/stderr 重定向到日志文件
- 没有可交互的终端 (stdin 为空)

---

### 🔍 Why #2: 为什么代码会调用 input()？
**答**: 配置文件验证失败，代码回退到交互式配置模式

**证据**:
```python
# ad-back.py:3778-3785
else:
    # 回退到交互式输入
    print(f"\n{Colors.YELLOW}⚠️  未找到或无法加载 user.yaml，切换到交互式配置模式{Colors.RESET}\n")
    user_config = interactive_setup()  # ← 这里触发交互式输入
```

**日志输出**:
```
❌ 镜头数量必须在 2-10 之间，当前值: 1
⚠️  未找到或无法加载 user.yaml，切换到交互式配置模式
```

---

### 🔍 Why #3: 为什么配置验证失败？
**答**: 临时配置文件 `temp/user-aka-12271649.yaml` 中 `shot_count: 1`，不满足后端验证规则（2-10）

**证据**:
```yaml
# temp/user-aka-12271649.yaml
shot_count: 1  # ← 违反后端验证规则
```

```python
# ad-back.py:807-809
if not (2 <= config_data['shot_count'] <= 10):
    print(f"❌ 镜头数量必须在 2-10 之间，当前值: {config_data['shot_count']}")
    return None  # ← 验证失败，返回 None
```

---

### 🔍 Why #4: 为什么 shot_count 会是 1？
**答**: API层的验证规则允许 `shot_count = 1`（验证范围 1-10），与后端不一致

**证据**:
```python
# py/api_server.py:183-184
if shot_count < 1 or shot_count > 10:  # ← 允许 shot_count = 1
    raise ValueError(f"镜头数 {shot_count} 无效，有效范围: 1-10")
```

**API层验证**: 1-10 ✅ 允许 1
**后端验证**: 2-10 ❌ 拒绝 1

---

### 🔍 Why #5: 为什么三层验证规则不一致？
**答**: 缺少统一的配置规范和跨层验证协调机制

**三层不一致的证据**:

| 层级 | 验证范围 | 默认值 | 代码位置 |
|------|---------|--------|----------|
| **前端** | 1, 3, 4, 5, 6, 10 | **1** | `frontend/index.html:460` |
| **API层** | 1-10 | 5 | `py/api_server.py:183` |
| **后端** | 2-10 | 2 | `py/ad-back.py:807` |

**前端代码**:
```html
<!-- frontend/index.html:459-466 -->
<select id="num_shots" name="num_shots">
    <option value="1" selected>1个镜头（约5秒视频，快速测试）</option>  <!-- ← 默认值为1 -->
    <option value="3">3个镜头（约15秒视频）</option>
    <option value="4">4个镜头（约20秒视频）</option>
    ...
</select>
```

---

## 3. 根本原因（Root Cause）

### 3.1 直接原因
**配置验证失败导致代码回退到交互式模式，而后台进程无法支持交互式输入**

### 3.2 根本原因（可控）
1. **三层验证规则不一致**
   - 前端：允许选择1个镜头
   - API层：验证范围 1-10
   - 后端：验证范围 2-10（业务真实需求）

2. **缺少优雅降级机制**
   - 验证失败时不应回退到 `input()` 交互式模式
   - 应该直接返回错误码和详细错误信息

3. **前端默认值设置错误**
   - 默认值为1，不符合业务规则（最小2个镜头）

4. **缺少API请求前端验证**
   - 前端没有在提交前验证参数合法性

---

## 4. 影响范围分析

### 4.1 用户影响
- **严重性**: 🔴 高危（100%失败率）
- **触发条件**: 用户在前端选择"1个镜头"选项
- **失败模式**: 静默失败（后端日志有错误，前端可能看不到）
- **用户体验**: 极差（提交任务后无响应或报错不清晰）

### 4.2 系统影响
- **数据完整性**: 生成无效的配置文件和日志
- **资源浪费**: 占用任务ID和存储空间
- **监控盲区**: 无法通过API返回详细错误信息

### 4.3 已发生案例
- 任务ID: `aka-12271649` (2025-12-27 16:49)
- 任务ID: `aka-12271638` (可能存在相同问题，需验证)

---

## 5. 可能的其他原因（排除分析）

| 假设原因 | 验证方法 | 结论 |
|---------|----------|------|
| 网络超时 | 查看API请求日志 | ❌ 排除（API请求成功） |
| 权限问题 | 检查文件权限 | ❌ 排除（配置文件已成功写入） |
| 依赖库问题 | 检查导入错误 | ❌ 排除（无导入错误） |
| API密钥失效 | 余额查询失败 | ⚠️ 次要（不影响此错误） |
| 内存不足 | 检查系统资源 | ❌ 排除（进程正常启动） |

**主要原因占比**: 100% 配置验证不一致问题

---

## 6. TDD 测试设计

### 6.1 测试用例设计

#### 测试场景1：边界值测试
```python
def test_shot_count_validation():
    """测试镜头数验证边界条件"""
    # 测试非法值
    assert validate_shot_count(0) == False, "0应该被拒绝"
    assert validate_shot_count(1) == False, "1应该被拒绝（不符合业务需求）"
    assert validate_shot_count(11) == False, "11应该被拒绝"

    # 测试合法值
    assert validate_shot_count(2) == True, "2应该通过（最小值）"
    assert validate_shot_count(5) == True, "5应该通过"
    assert validate_shot_count(10) == True, "10应该通过（最大值）"
```

#### 测试场景2：三层一致性测试
```python
def test_three_layer_consistency():
    """验证前端、API层、后端的验证规则一致性"""
    from frontend.validation import FRONTEND_SHOT_RANGE
    from py.api_server import validate_config
    from py.ad_back import load_user_config

    # 所有层应该使用相同的范围
    assert FRONTEND_SHOT_RANGE == (2, 10), "前端范围应为 2-10"

    # 测试一致性
    for shot_count in [1, 2, 5, 10, 11]:
        frontend_valid = is_valid_in_frontend(shot_count)
        api_valid = is_valid_in_api(shot_count)
        backend_valid = is_valid_in_backend(shot_count)

        assert frontend_valid == api_valid == backend_valid, \
            f"shot_count={shot_count} 在三层验证结果不一致"
```

#### 测试场景3：错误处理测试
```python
def test_graceful_error_handling():
    """测试配置验证失败时的优雅错误处理"""
    config = {'shot_count': 1, 'topic': 'test'}

    # 应该抛出明确的异常，而不是回退到交互式模式
    with pytest.raises(ValidationError) as exc_info:
        load_user_config(config, is_api_mode=True)

    # 验证错误消息
    assert "镜头数量必须在 2-10 之间" in str(exc_info.value)
    assert exc_info.value.field == "shot_count"
    assert exc_info.value.invalid_value == 1
```

#### 测试场景4：API集成测试
```python
@pytest.mark.integration
def test_api_shot_count_validation():
    """测试API端到端的镜头数验证"""
    client = TestClient(app)

    # 测试非法值
    response = client.post("/api/jobs", json={
        "topic": "test",
        "num_shots": 1  # 非法值
    })
    assert response.status_code == 400
    assert "镜头数量必须在 2-10 之间" in response.json()['detail']

    # 测试合法值
    response = client.post("/api/jobs", json={
        "topic": "test",
        "num_shots": 3  # 合法值
    })
    assert response.status_code == 200
```

### 6.2 回归测试检查清单
- [ ] 前端表单验证：shot_count 必须 >= 2
- [ ] 前端默认值设置为 3（或更安全的值）
- [ ] API层验证范围修改为 2-10
- [ ] 后端验证范围保持 2-10
- [ ] 后端移除交互式回退逻辑（API模式）
- [ ] 错误消息统一且清晰
- [ ] 端到端测试通过

---

## 7. 修复方案

### 7.1 短期修复（紧急）
**优先级**: 🔴 P0
**目标**: 立即阻止错误继续发生

1. **修复API层验证范围**
   ```python
   # py/api_server.py:183
   - if shot_count < 1 or shot_count > 10:
   + if shot_count < 2 or shot_count > 10:
       raise ValueError(f"镜头数 {shot_count} 无效，有效范围: 2-10")
   ```

2. **修复前端默认值**
   ```html
   <!-- frontend/index.html:460 -->
   - <option value="1" selected>1个镜头（约5秒视频，快速测试）</option>
   + <!-- 移除1个镜头选项 -->
   - <option value="3">3个镜头（约15秒视频）</option>
   + <option value="3" selected>3个镜头（约15秒视频，推荐）</option>
   ```

3. **增强后端错误处理**
   ```python
   # py/ad-back.py:3778-3785
   - else:
   -     print(f"\n{Colors.YELLOW}⚠️  未找到或无法加载 user.yaml，切换到交互式配置模式{Colors.RESET}\n")
   -     user_config = interactive_setup()
   + else:
   +     # 检查是否为API模式（通过环境变量或参数）
   +     if is_api_mode or not sys.stdin.isatty():
   +         raise RuntimeError("配置验证失败且无法进入交互式模式（API后台运行）")
   +     else:
   +         print(f"\n{Colors.YELLOW}⚠️  未找到或无法加载 user.yaml，切换到交互式配置模式{Colors.RESET}\n")
   +         user_config = interactive_setup()
   ```

### 7.2 中期优化（改进）
**优先级**: 🟡 P1
**目标**: 提升系统健壮性

1. **统一配置验证模块**
   - 创建 `py/validation/config_validator.py`
   - 集中管理所有验证规则
   - 前端、API、后端共享同一份规则

2. **增强前端验证**
   - 添加表单提交前的JavaScript验证
   - 实时显示参数有效范围
   - 禁用非法选项

3. **改进错误响应**
   - API返回结构化错误信息（字段名、当前值、合法范围）
   - 前端友好展示验证错误
   - 添加详细的错误码系统

### 7.3 长期改进（架构）
**优先级**: 🟢 P2
**目标**: 从根本上防止类似问题

1. **配置即代码（Configuration as Code）**
   - 使用 Pydantic 定义配置模型
   - 自动生成前端表单验证规则
   - 自动生成API文档

2. **契约测试（Contract Testing）**
   - 前端、API、后端之间定义明确的契约
   - 自动化测试验证契约一致性

3. **配置管理中心**
   - 所有配置参数的元数据（范围、默认值、描述）存储在单一位置
   - 自动生成验证代码

---

## 8. 实施计划

### Phase 1: 紧急修复（立即执行）
- [x] 编写测试用例
- [ ] 修复API层验证（2分钟）
- [ ] 修复前端默认值（2分钟）
- [ ] 修复前端下拉选项（2分钟）
- [ ] 增强后端错误处理（5分钟）
- [ ] 执行集成测试（5分钟）
- [ ] 部署到生产环境

**预计时间**: 20分钟
**风险**: 低

### Phase 2: 验证和监控（24小时内）
- [ ] 监控API错误日志
- [ ] 收集用户反馈
- [ ] 分析历史任务是否有类似问题

### Phase 3: 长期优化（1周内）
- [ ] 重构配置验证模块
- [ ] 添加契约测试
- [ ] 更新文档

---

## 9. 预防措施

### 9.1 技术预防
1. **代码审查检查清单**
   - 所有涉及配置参数的PR必须验证三层一致性
   - 禁止在后台进程中使用 `input()`

2. **自动化测试**
   - CI/CD 中添加三层一致性测试
   - 前端表单验证测试
   - API契约测试

3. **静态分析**
   - 使用 mypy 强制类型检查
   - 使用 pylint 检测 `input()` 在非交互式代码中的使用

### 9.2 流程预防
1. **配置参数变更流程**
   - 任何验证规则变更必须同步更新三层
   - 必须附带测试用例

2. **发布检查清单**
   - 验证前端、API、后端的配置一致性
   - 运行端到端测试

---

## 10. 经验教训

### 10.1 做得好的地方
- 详细的日志记录帮助快速定位问题
- 配置文件设计支持审计追踪

### 10.2 需要改进的地方
1. **缺少跨层验证**
   - 教训：前端、API、后端的验证必须保持一致
   - 行动：建立统一的配置验证机制

2. **错误处理不够健壮**
   - 教训：不应在后台进程中回退到交互式模式
   - 行动：区分运行模式（交互式 vs API）

3. **默认值设置不当**
   - 教训：默认值必须是合法且推荐的值
   - 行动：使用业务推荐值作为默认值（如3个镜头）

4. **缺少前端验证**
   - 教训：不能完全依赖后端验证
   - 行动：前端添加实时验证

---

## 11. 相关问题追踪

- **问题ID**: #RCA-20251227-001
- **相关任务**: aka-12271649, aka-12271638
- **修复PR**: 待创建
- **验证测试**: 待执行

---

## 附录

### A. 完整错误日志
```
🔄 手动恢复: aka-12271649

✅ 配置验证通过

============================================================
💰 账户余额查询
============================================================
[WARN] ⚠️  查询余额失败: 401 Client Error: Unauthorized
⚠️  无法查询余额，将继续执行（可能是网络问题）
============================================================

✅ 已从 temp/user-aka-12271649.yaml 加载配置

   🔢 风格数字 4 → realistic_3d
❌ 镜头数量必须在 2-10 之间，当前值: 1

⚠️  未找到或无法加载 user.yaml，切换到交互式配置模式

提示：创建 user.yaml 文件可跳过交互式输入
参考示例：复制并修改当前目录的 user.yaml

============================================================
🎬 AI视频生成系统 v2.0（故事化增强版）
============================================================

💡 视频主题
请输入视频主题（如：Akamai推出AI推理云）: Traceback (most recent call last):
  File "/home/wave/py/ad-back.py", line 4585, in <module>
    sys.exit(main())
  File "/home/wave/py/ad-back.py", line 3785, in main
    user_config = interactive_setup()
  File "/home/wave/py/ad-back.py", line 1083, in interactive_setup
    topic = input("请输入视频主题（如：Akamai推出AI推理云）: ").strip()
EOFError: EOF when reading a line
```

### B. 涉及文件清单
- `py/ad-back.py` (后端主程序)
- `py/api_server.py` (API服务)
- `frontend/index.html` (前端界面)
- `temp/user-aka-12271649.yaml` (临时配置)
- `output/aka-12271649/log.txt` (任务日志)

### C. 参考资料
- [CLAUDE.md 项目规范](../CLAUDE.md)
- [配置文件说明](../README.md#配置层级)
- [API文档](../doc/API.md)

---

**分析完成时间**: 2025-12-27
**分析人员**: Claude Code Agent
**审核状态**: 待审核
