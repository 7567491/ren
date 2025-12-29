# user.yaml 使用说明

## 概述

已将配置文件从 `config.toml` 升级为 `user.yaml`：

- ✅ **YAML格式**：编辑器有语法高亮（蓝色、绿色等颜色）
- ✅ **数字配置**：保持简单，用户只需输入数字
- ✅ **简洁**：49行，包含所有必要配置
- ✅ **后台配置**：`config.yaml` 保持不变，包含详细的系统配置

## 工作流程

```
用户修改 user.yaml（数字）→ 程序数字映射 → 从 config.yaml 读取详细配置
```

**示例：**
```yaml
style: 4  # user.yaml中用户输入数字4
   ↓
4 → "realistic_3d"  # 程序映射
   ↓
config.yaml中的visual_styles.realistic_3d  # 读取详细配置
```

## user.yaml 配置字段

### 必填字段

```yaml
# 视频主题
topic: "云计算弹性扩容解决方案"

# 视觉风格（1-10）
style: 4

# 镜头数量（3-9）
shot_count: 6

# 每镜头时长（3-5秒）
shot_duration: 5

# 分辨率（1-480p 2-720p 3-1080p）
resolution: 1
```

### 可选字段

```yaml
# 主角一致性
character:
  enabled: 1  # 0-不启用 1-启用
  description: "东方少女，长发，红色衣服"
  default_character_image: "https://s.linapp.fun/mai.jpg"

# 品牌Logo
brand:
  enabled: 1  # 0-不显示 1-显示
  name: "Akamai"
  default_logo_image: "./resource/logo/aka.jpg"

# 工作流
workflow:
  concurrent_workers: 6  # 1-9线程
  auto_confirm: 1        # 0-需确认 1-自动开始

# 字幕
subtitle:
  font_size: 24
  position: 1  # 1-底部 2-中间 3-顶部
```

## 数字映射表

### 风格映射（style）

| 数字 | 映射值 | 说明 |
|------|--------|------|
| 1 | tech_product | 科技产品（Apple风格） |
| 2 | luxury_fashion | 时尚奢华（高端科技） |
| 3 | minimalist_brand | 简约品牌（极简设计） |
| 4 | realistic_3d | 3D写实（CG渲染） |
| 5 | cinematic | 电影写实（生活方式） |
| 6 | technology | 科技未来风（数据流） |
| 7 | cyberpunk | 赛博朋克（霓虹都市） |
| 8 | holographic | 全息投影（AR/VR） |
| 9 | corporate_tech | 企业科技（B2B风格） |
| 10 | data_visualization | 数据可视化（AI/大数据） |

### 分辨率映射（resolution）

| 数字 | 映射值 | 说明 |
|------|--------|------|
| 1 | 480p | 快速测试，成本低 (~$0.30/镜头) |
| 2 | 720p | 推荐使用，质量好 (~$1.00/镜头) |
| 3 | 1080p | 最高画质，较慢 (~$2.00/镜头) |

### 布尔值映射（enabled, auto_confirm）

| 数字 | 映射值 |
|------|--------|
| 0 | false |
| 1 | true |

### 字幕位置映射（position）

| 数字 | 映射值 |
|------|--------|
| 1 | bottom |
| 2 | center |
| 3 | top |

## 使用方法

### 1. 首次使用

复制当前的 `user.yaml` 并根据需求修改：

```bash
# user.yaml已经存在于项目根目录
# 直接修改数字即可
```

### 2. 修改配置

用任何文本编辑器打开 `user.yaml`：

```bash
# VS Code（推荐，有YAML语法高亮）
code user.yaml

# Vim
vim user.yaml

# 任何编辑器
open user.yaml
```

### 3. 运行脚本

```bash
python3 py/ad-aka.py
```

程序会自动：
1. 读取 `user.yaml`
2. 数字映射转换
3. 从 `config.yaml` 读取详细配置
4. 开始生成视频

## 配置验证

运行测试确认配置正确：

```bash
python3 test/test_user_yaml.py
```

**输出示例：**
```
✅ 成功加载 user.yaml

🔢 数字映射测试:
风格: 4 → realistic_3d
分辨率: 1 → 480p
主角启用: 1 → True
品牌启用: 1 → True
字幕位置: 1 → bottom
自动确认: 1 → True

✅ user.yaml配置测试通过！
```

## 常见问题

### Q1: 为什么改用YAML？

**A:** YAML格式在编辑器中有语法高亮（颜色），比TOML更易读。

**对比：**
```toml
# config.toml（无颜色）
style = 1
resolution = 2
```

```yaml
# user.yaml（有颜色高亮）
style: 1
resolution: 2
```

### Q2: 数字和字符串都支持吗？

**A:** 是的，两种都支持：

```yaml
# 方式1：数字（推荐，简单）
style: 4

# 方式2：字符串（高级用户）
style: "realistic_3d"
```

程序会自动识别并处理。

### Q3: config.yaml还有用吗？

**A:** **非常重要！** `config.yaml` 包含所有详细配置：

- 视觉风格的详细定义
- 提示词模板
- 音频参数
- 运镜系统

**用户只修改 `user.yaml`，`config.yaml` 保持不变。**

### Q4: 如何恢复默认配置？

```bash
# 复制当前的user.yaml作为备份
cp user.yaml user.yaml.backup

# 参考项目中的user.yaml重置
```

## 对比：TOML vs YAML

### config.toml（旧）

```toml
# 没有语法高亮（或很少编辑器支持）
[video]
topic = "云计算"
style = 1
shot_count = 6

[character]
enabled = 1
description = "技术总监"
```

### user.yaml（新）

```yaml
# 编辑器自动高亮（蓝色、绿色等）
topic: "云计算"
style: 1
shot_count: 6

character:
  enabled: 1
  description: "技术总监"
```

**优势：**
- ✅ 语法高亮
- ✅ 更易读的缩进
- ✅ 主流编辑器原生支持
- ✅ 更少的符号（不需要 `[section]`）

## 版本历史

- **v1.0** (2025-12-24): 从 config.toml 迁移到 user.yaml
  - 保留数字配置（用户友好）
  - 添加YAML语法高亮支持
  - 保持所有功能不变

## 参考文档

- [config.yaml](../config.yaml) - 系统详细配置（不要修改）
- [user.yaml](../user.yaml) - 用户配置（修改这个）
- [运镜系统说明.md](./运镜系统说明.md) - M1-M6运镜模式
- [最佳实践.md](./最佳实践.md) - 广告视频工作流
