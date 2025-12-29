# 方案三详细实施方案：双轨制AI广告工作坊
## WaveSpeed AI × Linode - 1小时极速广告制作

---

## 📋 目录

1. [核心设计理念](#核心设计理念)
2. [详细时间线（分钟级）](#详细时间线)
3. [技术派轨道详细设计](#技术派轨道)
4. [商业派轨道详细设计](#商业派轨道)
5. [合流协作机制](#合流协作机制)
6. [现场布置方案](#现场布置方案)
7. [风险预案与应急方案](#风险预案)
8. [评分标准与激励机制](#评分标准)
9. [准备工作清单](#准备工作清单)
10. [后续转化方案](#后续转化方案)

---

## 🎯 核心设计理念

### 设计哲学
```
技术 × 创意 = 真实生产力
代码 + 故事 = 商业价值
学习 + 社交 = 长期关系
```

### 三大核心目标
1. **技术目标**：让开发者掌握可复用的agent架构和prompt工程技巧
2. **商业目标**：让创业者理解AI如何服务真实业务场景
3. **社交目标**：促成技术与商业的跨界连接，形成潜在合作

### 差异化价值主张
- ❌ 不是：单纯的产品演示（太浅）
- ❌ 不是：纯技术培训（太窄）
- ✅ 而是：真实团队协作的微缩版，1小时体验完整产品周期

---

## ⏱️ 详细时间线（60分钟）

### 阶段一：破冰与分组（0:00-0:05，5分钟）

#### 0:00-0:02（2分钟）- 主持人开场
**内容**：
```
大家好！接下来60分钟，我们要完成一个看似不可能的任务：
从0到1制作一支30秒的广告视频。

但今天的特别之处在于：
- 技术派朋友：你们将搭建真实的AI agent系统
- 商业派朋友：你们将设计完整的广告创意策略
- 最激动人心的是：两个世界将在30分钟后碰撞融合

现在，请大家做一个选择...
```

**操作**：
- 大屏幕显示两个轨道的预览视频（各30秒）
- 技术派视频：代码界面、终端操作、架构图
- 商业派视频：创意工作坊、情绪板、品牌策略

#### 0:02-0:04（2分钟）- 自我标签与分组
**流程**：
1. 参与者举手选择轨道
   - "我是技术派" → 左侧集合
   - "我是商业派" → 右侧集合
   - "我都感兴趣" → 由工作人员根据比例分配

2. 混合分组（每组4人）
   ```
   理想配比：1技术派 + 3商业派
   可接受范围：1-2技术派 + 2-3商业派
   ```

3. 分配组号和工位
   - 技术派：获得Linode实例账号卡片
   - 商业派：获得创意工具包
   - 全组：获得协作白板

#### 0:04-0:05（1分钟）- 快速破冰
**方法**：60秒自我介绍接龙
```
格式：姓名 + 一句话专长 + 今天想做什么广告
示例："我是张三，擅长Python，今天想做个AI宠物用品的广告"
```

**目的**：
- 快速建立组内信任
- 初步确定广告主题方向
- 识别技能互补性

---

### 阶段二：双轨并行（0:05-0:35，30分钟）

#### 技术派轨道时间线

##### 0:05-0:10（5分钟）- 环境初始化

**0:05-0:07（2分钟）**
操作：登录Linode实例
```bash
# 扫描桌上卡片二维码，获得：
- IP地址：xxx.xxx.xxx.xxx
- SSH密钥：自动下载
- 用户名：team-01

# 自动执行登录脚本（一键式）
ssh -i team-01.pem team-01@xxx.xxx.xxx.xxx
```

验证：看到欢迎界面
```
🎉 Welcome to WaveSpeed AI Workshop
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Instance: Linode 8GB (4 vCPU)
Region: Singapore
Pre-installed: Docker, Python 3.11, Node.js 20
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Next step: cd /workshop && ls
```

**0:07-0:10（3分钟）**
操作：启动预装容器
```bash
cd /workshop
docker-compose up -d

# 输出：
# ✓ agent-framework ... done
# ✓ wavespeed-api    ... done
# ✓ web-interface    ... done
# ✓ redis-cache      ... done

# 验证服务
curl localhost:8080/health
# {"status": "ready", "agents": ["text", "image", "video"]}
```

浏览器访问：`http://[你的IP]:8080`
看到：Agent控制台界面

##### 0:10-0:20（10分钟）- Agent配置与调试

**0:10-0:13（3分钟）- 理解架构**
打开预装文件：`/workshop/README.md`
```markdown
# 三Agent架构

workflow/
├── text_agent/          # 文案生成
│   ├── agent.py         # 主逻辑
│   └── prompts/         # Prompt模板
│       ├── script.jinja2
│       └── cta.jinja2
├── image_agent/         # 视觉生成
│   ├── agent.py
│   └── prompts/
│       └── scene.jinja2
└── video_agent/         # 视频合成
    ├── agent.py
    └── prompts/
        └── storyboard.jinja2

数据流：
商业派输入 → text_agent → image_agent → video_agent → 成片
```

**0:13-0:18（5分钟）- 配置Text Agent**

编辑：`text_agent/prompts/script.jinja2`
```jinja2
你是一位资深广告文案，需要为以下产品创作30秒视频脚本。

【产品信息】
名称：{{ product_name }}
类别：{{ category }}
核心卖点：{{ selling_points }}
目标受众：{{ target_audience }}

【要求】
1. 时长：严格控制在30秒（约75-90字）
2. 结构：痛点(5秒) → 方案(15秒) → 行动(10秒)
3. 调性：{{ tone }}（可选：专业/活泼/温情/科技）
4. 必须包含明确的CTA（Call to Action）

【输出格式】
返回JSON：
{
  "hook": "开场钩子（1句话吸引注意）",
  "problem": "痛点描述",
  "solution": "解决方案（产品价值）",
  "cta": "行动号召",
  "full_script": "完整旁白文本",
  "estimated_duration": 30
}
```

测试调用：
```bash
cd /workshop
python test_agent.py text \
  --product "AI智能日历" \
  --category "效率工具" \
  --selling_points "自动整理日程,智能提醒,跨平台同步" \
  --target_audience "25-35岁职场人士" \
  --tone "科技感"

# 输出示例（5秒内）：
# ✓ Generated script (87 words, ~29s)
# ✓ Hook: "每天20+会议，你还在手动记录？"
```

**0:18-0:20（2分钟）- 快速浏览Image和Video Agent**
```bash
# Image Agent - 关键参数
cat image_agent/config.yaml
# model: wavespeed/flux-pro
# aspect_ratio: 16:9
# style_presets: [cinematic, commercial, clean]

# Video Agent - 关键参数
cat video_agent/config.yaml
# model: wavespeed/runway-gen3
# duration: 3s_per_scene
# transition: crossfade
# audio: auto_voiceover + bgm
```

**导师提示**：
"这两个agent已经预配置好，如果时间充裕可以调整参数，但现在先确保能跑通流程"

##### 0:20-0:30（10分钟）- 构建协作界面

**0:20-0:25（5分钟）- 修改Web表单**

编辑：`web-interface/src/InputForm.jsx`
```jsx
// 已有基础表单，任务：添加自定义字段

export default function InputForm() {
  const [formData, setFormData] = useState({
    product_name: '',
    category: '',
    selling_points: '',
    target_audience: '',
    tone: 'professional',
    // 👇 添加你的自定义字段
    brand_color: '#000000',  // 品牌色
    must_include: '',        // 必须出现的元素
    avoid: '',               // 需要避免的内容
  });

  return (
    <form onSubmit={handleGenerate}>
      {/* 现有字段... */}

      {/* 👇 新增部分 */}
      <ColorPicker
        label="品牌主色调"
        value={formData.brand_color}
        onChange={(c) => setFormData({...formData, brand_color: c})}
      />

      <TextArea
        label="必须包含的元素（例如：公司logo、特定场景）"
        value={formData.must_include}
        onChange={(e) => setFormData({...formData, must_include: e.target.value})}
      />

      <button type="submit">🚀 生成广告</button>
    </form>
  );
}
```

保存后自动热更新（浏览器刷新即可看到新表单）

**0:25-0:28（3分钟）- 连接后端API**

编辑：`web-interface/src/api.js`
```javascript
export async function generateAd(formData) {
  const response = await fetch('/api/generate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(formData)
  });

  // 返回Server-Sent Events流
  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const {done, value} = await reader.read();
    if (done) break;

    const event = decoder.decode(value);
    // event格式：
    // data: {"stage": "text_agent", "status": "completed", "result": {...}}

    yield JSON.parse(event.data);
  }
}
```

**0:28-0:30（2分钟）- 全流程测试**
```bash
# 重启服务
docker-compose restart web-interface

# 打开浏览器，填写测试数据
# 点击"生成广告"，观察：
# ✓ Text Agent: 正在生成文案... (进度条)
# ✓ Image Agent: 正在生成场景1/6... (进度条)
# ✓ Video Agent: 正在合成视频... (进度条)
# ✓ 完成！点击预览

# 如果成功：✅ 技术轨道搭建完成
# 如果失败：查看日志 docker-compose logs -f
```

**里程碑检查点**：
- [ ] 能否访问Web界面？
- [ ] 提交表单后是否有实时进度？
- [ ] 能否获得任何输出（即使质量不佳）？

##### 0:30-0:35（5分钟）- 等待商业派 + 优化

**如果提前完成，可选优化**：
1. **Prompt工程**：调整文案agent的创意度
   ```python
   # text_agent/agent.py
   temperature: 0.7  # 提高到0.9增加创意
   top_p: 0.95      # 控制多样性
   ```

2. **并行优化**：让image_agent并行生成多个场景
   ```python
   # image_agent/agent.py
   concurrent_scenes = 3  # 从1改为3
   ```

3. **添加错误处理**：
   ```javascript
   // web-interface/src/api.js
   try {
     yield await generateAd(formData);
   } catch (error) {
     yield {stage: 'error', message: error.message};
   }
   ```

**导师巡场**：
- 检查每组进度
- 回答技术问题
- 提示："10分钟后商业派会来，准备好演示你的系统"

---

#### 商业派轨道时间线

##### 0:05-0:15（10分钟）- 创意策略构建

**0:05-0:07（2分钟）- 破题与案例启发**

导师播放3个案例视频（各20秒）：
1. **案例A - DTC品牌**：Cole Haan鞋履广告
   - 痛点：传统皮鞋不舒适
   - 方案：科技鞋垫+时尚设计
   - CTA：扫码领取新人优惠
   - **关键学习**：如何在5秒内建立痛点共鸣

2. **案例B - SaaS产品**：Notion AI广告
   - 痛点：知识管理混乱
   - 方案：AI自动整理
   - CTA：免费试用
   - **关键学习**：产品演示的视觉化表达

3. **案例C - 本地服务**：健身房推广
   - 痛点：办卡后不去
   - 方案：1对1私教+灵活约课
   - CTA：到店体验
   - **关键学习**：情感化叙事技巧

**讨论**：
"注意到了吗？所有广告都遵循 痛点→方案→行动 三段式"

**0:07-0:10（3分钟）- 确定广告主题**

使用《产品速写卡》（工具包内）：
```
┌─────────────────────────────┐
│  我们要推广的产品/服务是：    │
│  ___________________________│
│                             │
│  它解决的核心问题是：        │
│  ___________________________│
│                             │
│  我们的独特优势是：          │
│  ___________________________│
│                             │
│  目标客户最关心的是：        │
│  ___________________________│
└─────────────────────────────┘
```

**小组讨论**：5分钟限时，达成共识
- 可以推广组内某人的真实项目
- 也可以选择虚拟产品（如"AI宠物陪伴机器人"）

**导师建议**：
"如果纠结，选一个你自己会买的产品，这样更容易共情"

**0:10-0:15（5分钟）- 受众洞察与情绪定位**

使用《受众画像工作表》：
```
╔═══════════════════════════════════╗
║  目标受众画像                      ║
╠═══════════════════════════════════╣
║ 基础属性                          ║
║ • 年龄段：[    ]                  ║
║ • 职业：[    ]                    ║
║ • 收入水平：[    ]                ║
║                                   ║
║ 心理属性                          ║
║ • 核心痛点：[               ]     ║
║ • 内心渴望：[               ]     ║
║ • 决策障碍：[               ]     ║
║                                   ║
║ 行为属性                          ║
║ • 常用平台：[    ]                ║
║ • 观看习惯：[ ]短视频 [ ]长视频   ║
║ • 信任来源：[    ]                ║
╚═══════════════════════════════════╝
```

填写后，导师引导：
"现在闭眼想象，这个人刷到你的广告时，正在做什么？心情如何？"

情绪定位选择（圈出1-2个）：
```
[ ] 焦虑（效率工具常用）
[ ] 渴望（奢侈品常用）
[ ] 好奇（创新产品常用）
[ ] 温暖（家庭产品常用）
[ ] 兴奋（娱乐产品常用）
[ ] 信任（企业服务常用）
```

##### 0:15-0:25（10分钟）- 脚本与视觉设计

**0:15-0:20（5分钟）- 脚本创作**

使用《30秒脚本模板》（A3大纸）：
```
┌────────────────────────────────────────┐
│  0-5秒：开场钩子 (HOOK)                │
├────────────────────────────────────────┤
│  画面：                                │
│  ________________________________      │
│                                        │
│  旁白/文字：                           │
│  ________________________________      │
│                                        │
│  目的：吸引注意，建立痛点共鸣          │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  5-20秒：解决方案 (SOLUTION)          │
├────────────────────────────────────────┤
│  画面1（5-10秒）：                     │
│  ________________________________      │
│  旁白：                                │
│  ________________________________      │
│                                        │
│  画面2（10-15秒）：                    │
│  ________________________________      │
│  旁白：                                │
│  ________________________________      │
│                                        │
│  画面3（15-20秒）：                    │
│  ________________________________      │
│  旁白：                                │
│  ________________________________      │
│                                        │
│  目的：展示产品价值，建立信任          │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  20-30秒：行动号召 (CTA)              │
├────────────────────────────────────────┤
│  画面：                                │
│  ________________________________      │
│                                        │
│  旁白/文字：                           │
│  ________________________________      │
│                                        │
│  转化路径：                            │
│  [ ] 扫码  [ ] 搜索  [ ] 访问网站     │
│  [ ] 下载APP  [ ] 到店                │
│                                        │
│  目的：驱动行动，可衡量转化            │
└────────────────────────────────────────┘
```

**填写技巧**（导师讲解）：
- 画面描述要具体："一个焦虑的职场人盯着满屏的日程"（✅）vs "一个人在工作"（❌）
- 旁白要口语化："每天20+会议，你还在手动记录？"（✅）vs "日程管理很重要"（❌）
- 每个画面控制在3-7秒

**0:20-0:25（5分钟）- 视觉风格设计**

使用《情绪板工具包》（内含色卡、风格卡）：

**步骤1：选择视觉风格**
```
可选风格卡（每张卡有参考图）：
┌──────┬──────┬──────┬──────┐
│科技感│温情感│专业感│活力感│
│Cyber │Warm  │Pro   │Energy│
│风    │暖色  │冷静  │明快  │
└──────┴──────┴──────┴──────┘
```

**步骤2：确定色彩方案**
从色卡中选择：
- 主色调（1个）：代表品牌
- 辅助色（1-2个）：画面层次
- 禁用色（可选）：避免混淆

**步骤3：准备品牌素材**
- 上传logo（如果有）
- 提供产品图（手机拍照即可）
- 准备参考图（从网上找相似风格）

##### 0:25-0:35（10分钟）- 结构化输入准备

**0:25-0:30（5分钟）- 填写《技术对接表》**

这张表将交给技术派，格式要严格：
```json
{
  "基础信息": {
    "产品名称": "AI智能日历",
    "类别": "效率工具",
    "目标受众": "25-35岁职场人士"
  },

  "创意策略": {
    "核心卖点": [
      "自动整理日程",
      "智能提醒",
      "跨平台同步"
    ],
    "情感调性": "科技感 + 一点温度",
    "痛点描述": "每天被碎片化会议淹没，手动整理耗时费力"
  },

  "脚本内容": {
    "开场钩子": "每天20+会议，你还在手动记录？",
    "核心文案": "AI智能日历，一句话创建日程，自动识别时间地点参会人，跨设备实时同步，让你专注重要的事。",
    "行动号召": "扫码免费试用，前100名送高级版"
  },

  "视觉要求": {
    "风格": "现代科技感",
    "主色调": "#0066FF",
    "辅助色": "#FFFFFF",
    "必须包含": "产品界面截图，logo",
    "禁止出现": "竞品logo，混乱的场景"
  },

  "技术参数": {
    "画面比例": "9:16（竖屏）或 16:9（横屏）",
    "时长": "严格30秒",
    "配音": "男声/女声/不需要",
    "背景音乐": "轻快电子乐 / 舒缓钢琴 / 无"
  },

  "补充素材": {
    "logo文件": "已上传到 /team-01/logo.png",
    "产品截图": "已上传到 /team-01/screenshots/",
    "参考视频": "链接：https://example.com/ref.mp4"
  }
}
```

**导师检查**：
- 是否填写完整？
- 文案是否控制在90字以内？
- 素材是否已上传？

**0:30-0:35（5分钟）- 彩排与优化**

**小组内部预演**：
1. 一人读旁白，掐秒表
2. 其他人闭眼想象画面
3. 互相反馈：
   - 哪里听不懂？
   - 哪里没有画面感?
   - CTA够不够清晰？

**快速迭代**：
根据反馈调整脚本，重新计时

**准备对接**：
- 指定1人为"对接人"（将与技术派沟通）
- 其他人准备讲解创意策略的逻辑

---

### 阶段三：合流协作（0:35-0:55，20分钟）

#### 0:35-0:40（5分钟）- 第一次对接

**场景**：商业派对接人走到技术派工位

**对接流程**：

**Step 1：需求交接（2分钟）**
```
商业派："我们准备好需求了，这是《技术对接表》"
技术派："好，我先看一下...（浏览）...有个问题，'科技感+一点温度'
        具体是什么意思？"
商业派："就是整体冷色调，但出现人物时用暖光"
技术派："明白了，我会在prompt里加上这个"
```

**Step 2：技术解读（2分钟）**
```
技术派："我给你看一下系统界面...（打开浏览器）
        这里填你们的文案，这里上传logo，
        这个下拉菜单选择'科技感'风格，
        点击'生成'后大概需要8-10分钟"
商业派："能实时看到进度吗？"
技术派："可以，这里有进度条，每个agent完成会有通知"
```

**Step 3：启动生成（1分钟）**
```
技术派操作：
1. 将《技术对接表》的内容复制到Web表单
2. 上传logo和素材
3. 检查配置
4. 点击"🚀 生成广告"

系统响应：
✓ 任务已提交
✓ 预计完成时间：0:48（13分钟后）
✓ Text Agent 启动中...
```

商业派回到座位，等待中间结果

#### 0:40-0:48（8分钟）- 生成过程与实时监控

**技术派视角**：
```
0:41 - ✓ Text Agent 完成
       查看输出：
       {
         "hook": "每天20+会议，你还在手动记录？",
         "full_script": "...",
         "estimated_duration": 29
       }

       → 通知商业派："文案生成好了，要看吗？"

0:42 - 商业派查看并反馈
       "第二句话太生硬，能改成'AI帮你一句话搞定'吗？"

       技术派修改prompt并重新生成（2分钟）

0:44 - ✓ Text Agent 重新完成（优化版）
       ✓ Image Agent 开始生成场景1/6

0:45 - ✓ 场景1完成：职场人物特写（焦虑表情）
       ✓ 场景2生成中...

0:46 - ⚠️ 场景2失败：提示词包含敏感词

       技术派排查："logo.png里有文字被识别成敏感内容"
       解决：裁剪logo，重新上传

       ✓ 场景2重新生成

0:47 - ✓ 场景2-6全部完成
       ✓ Video Agent 开始合成

0:48 - ✓ 视频合成完成
       ✓ 正在添加配音...
       ✓ 正在混音...
```

**商业派视角**：
```
在等待过程中，商业派做什么？
1. 准备demo演讲稿（如何介绍这支广告）
2. 设计转化落地页的草图
3. 思考投放策略（投哪些平台？预算多少？）
```

**导师巡场**：
- 解答技术问题
- 提醒时间："还剩7分钟"
- 鼓励："已经有3个组生成成功了"

#### 0:48-0:53（5分钟）- 初稿评审与迭代

**0:48-0:50（2分钟）- 全组观看初稿**

技术派投屏：播放生成的30秒视频

全组快速反馈：
```
✅ 好的地方：
- 整体节奏流畅
- 品牌色应用正确
- 配音清晰

❌ 需要改进：
- 第3个场景太暗，看不清产品界面
- 背景音乐太激烈，不符合"温度"调性
- 最后CTA的二维码太小
```

**0:50-0:53（3分钟）- 快速迭代**

技术派操作：
```
# 方案A：微调参数重新生成（风险：可能来不及）
# 方案B：手动调整（推荐）

使用简单的视频编辑API：
```python
from workshop.video import VideoEditor

editor = VideoEditor('output.mp4')

# 调整场景3亮度
editor.adjust_scene(3, brightness=1.3)

# 替换背景音乐
editor.replace_audio('bgm.mp3', volume=0.6)

# 放大二维码
editor.overlay_image('qr.png',
                     position='bottom-right',
                     scale=2.0)

# 导出最终版
editor.export('final.mp4')
# 耗时：~30秒
```

**0:53 - 最终版完成**
```
✓ final.mp4 已生成
✓ 时长：30秒
✓ 分辨率：1080p
✓ 文件大小：12.3 MB
```

#### 0:53-0:55（2分钟）- 导出与准备展示

**技术派导出**：
```bash
# 上传到WaveSpeed CDN
workshop-cli upload final.mp4

# 输出：
# ✓ 已上传: https://cdn.wavespeed.ai/workshop/team-01/final.mp4
# ✓ 分享链接: https://share.wavespeed.ai/abc123
# ✓ 嵌入代码: <iframe src="...">
```

**全组准备**：
1. 商业派准备讲解：创意策略（1分钟）
2. 技术派准备讲解：技术实现（1分钟）
3. 确定谁播放视频，谁操作PPT

---

### 阶段四：成果展示（0:55-1:00，5分钟）

#### 展示流程（每组3分钟，限2组demo）

**第1分钟 - 视频播放**
```
主持人："有请第一组！"

组员播放30秒视频（投屏）
全场观看

播放结束，掌声
```

**第2分钟 - 创意策略讲解**
```
商业派代表发言：

"我们这支广告的目标受众是25-35岁的职场人士，
他们的核心痛点是会议多、日程乱。

我们用'痛点-方案-行动'三段式结构：
- 开场5秒用问句制造共鸣
- 中间15秒展示AI如何解决问题
- 最后10秒给明确的福利驱动下载

在视觉上，我们选择了科技蓝作为主色调，
但在人物特写时加了暖光，传递'科技有温度'的理念。

预估这支广告在抖音投放，CPM约80元，
转化率如果能到3%，获客成本约27元，
远低于行业平均的50元。"
```

**第3分钟 - 技术实现讲解**
```
技术派代表发言：

"技术实现上，我们在Linode上部署了三个agent：

Text Agent用的是WaveSpeed的Claude Sonnet，
我特别调整了prompt，加入了'控制字数'和'口语化'的要求，
这样生成的文案更适合短视频。

Image Agent用的是Flux Pro，我们传入了品牌色#0066FF，
模型自动生成了6个风格统一的场景。

Video Agent负责合成，这里有个技巧：
我们用了scene-level的参数控制，
让第3个场景的亮度提高30%，这样产品界面更清晰。

整个流程从输入到输出用了11分钟，
如果优化并行度，理论上可以压缩到5分钟。

最重要的是，这套架构是可复用的，
我已经把代码推到了GitHub，大家可以直接用。"
```

**Q&A（30秒）**
```
主持人："有什么问题吗？"
观众："如果要改文案，要重新生成所有内容吗？"
技术派："不用，我们做了模块化，可以只重新跑Text Agent"
```

**切换到下一组**

#### 0:58-1:00 - 总结与颁奖

**主持人总结**：
```
"60分钟，我们见证了技术与创意的碰撞。

技术派朋友：你们搭建的agent系统，不仅能做广告，
还能应用到内容创作、自动化报告、数据分析等无数场景。

商业派朋友：你们掌握的创意方法论，是AI无法替代的，
因为真正的洞察来自对人性的理解。

当两者结合，1+1>2，这就是未来工作方式。"
```

**颁发奖项**：
- 🏆 **最佳创意奖**：由现场投票选出（创意最独特）
- 🏆 **最佳技术奖**：由技术导师选出（实现最优雅）
- 🏆 **最佳协作奖**：由主持人选出（团队配合最默契）

**奖品**：
- WaveSpeed AI高级版（3个月免费）
- Linode云服务$100额度
- 精美周边礼包

**合影**：全体参与者 + 大屏幕播放所有作品

---

## 🖥️ 技术派轨道详细设计

### 预装环境架构

#### Linode实例配置
```yaml
规格：
  - CPU: 4 vCPU (AMD EPYC或Intel Xeon)
  - 内存: 8GB RAM
  - 存储: 160GB SSD
  - 网络: 5TB传输量/月
  - 区域: Singapore (低延迟)

操作系统：
  - Ubuntu 22.04 LTS

预装软件：
  - Docker 24.x + Docker Compose
  - Python 3.11 + pip + venv
  - Node.js 20 LTS + npm
  - Nginx (反向代理)
  - Redis (缓存)
  - FFmpeg (视频处理)

安全配置：
  - SSH密钥认证（禁用密码登录）
  - UFW防火墙（仅开放22, 80, 8080端口）
  - 自动安全更新
```

#### Docker Compose架构
```yaml
# /workshop/docker-compose.yml

version: '3.8'

services:
  # Agent框架后端
  agent-framework:
    image: workshop/agent-framework:latest
    ports:
      - "5000:5000"
    environment:
      - WAVESPEED_API_KEY=${WAVESPEED_API_KEY}
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./workflow:/app/workflow
      - ./outputs:/app/outputs
    depends_on:
      - redis
    restart: unless-stopped

  # WaveSpeed API代理（处理认证和限流）
  wavespeed-api:
    image: workshop/wavespeed-proxy:latest
    ports:
      - "5001:5001"
    environment:
      - API_KEY=${WAVESPEED_API_KEY}
      - RATE_LIMIT=100/minute
    restart: unless-stopped

  # Web界面
  web-interface:
    image: workshop/web-ui:latest
    ports:
      - "8080:80"
    environment:
      - API_ENDPOINT=http://agent-framework:5000
    volumes:
      - ./web-interface/src:/app/src  # 支持热更新
    restart: unless-stopped

  # Redis缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  # 监控面板（可选）
  monitor:
    image: workshop/monitor:latest
    ports:
      - "3000:3000"
    environment:
      - GRAFANA_ADMIN_PASSWORD=workshop2024
    restart: unless-stopped
```

### Agent框架代码详解

#### 1. Text Agent（文案生成）

**文件：`/workshop/workflow/text_agent/agent.py`**
```python
import os
from typing import Dict, Any
from wavespeed import WaveSpeedClient
from jinja2 import Template

class TextAgent:
    """
    文案生成Agent
    负责根据产品信息生成30秒视频脚本
    """

    def __init__(self):
        self.client = WaveSpeedClient(
            api_key=os.getenv('WAVESPEED_API_KEY')
        )
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> Template:
        """加载Jinja2模板"""
        with open('prompts/script.jinja2', 'r', encoding='utf-8') as f:
            return Template(f.read())

    def generate(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成广告脚本

        Args:
            inputs: {
                'product_name': str,
                'category': str,
                'selling_points': str,
                'target_audience': str,
                'tone': str,
                'brand_color': str (可选),
                'must_include': str (可选),
                'avoid': str (可选)
            }

        Returns:
            {
                'hook': str,           # 开场钩子
                'problem': str,        # 痛点描述
                'solution': str,       # 解决方案
                'cta': str,            # 行动号召
                'full_script': str,    # 完整脚本
                'estimated_duration': int,  # 预估时长（秒）
                'word_count': int      # 字数
            }
        """

        # 1. 渲染prompt
        prompt = self.prompt_template.render(**inputs)

        # 2. 调用WaveSpeed API
        response = self.client.chat.completions.create(
            model="claude-sonnet-4",
            messages=[
                {
                    "role": "system",
                    "content": "你是资深广告文案，擅长30秒短视频脚本创作"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,  # 创意度
            max_tokens=1000,
            response_format={"type": "json_object"}  # 要求JSON输出
        )

        # 3. 解析结果
        result = response.choices[0].message.content

        # 4. 验证与优化
        result = self._validate_and_optimize(result, inputs)

        return result

    def _validate_and_optimize(
        self,
        result: Dict[str, Any],
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证输出质量并优化
        """
        # 检查字数（30秒约75-90字）
        word_count = len(result.get('full_script', ''))
        if word_count > 100:
            # 太长，要求缩减
            result['full_script'] = self._shorten_script(
                result['full_script'],
                target_length=90
            )
            word_count = 90

        # 检查是否包含必需元素
        if inputs.get('must_include'):
            must_include = inputs['must_include']
            if must_include not in result['full_script']:
                # 插入必需元素
                result['solution'] += f" {must_include}"

        # 检查是否包含禁止内容
        if inputs.get('avoid'):
            avoid_words = inputs['avoid'].split(',')
            for word in avoid_words:
                result['full_script'] = result['full_script'].replace(
                    word.strip(),
                    ''
                )

        # 更新元数据
        result['word_count'] = word_count
        result['estimated_duration'] = max(25, min(32, word_count // 3))

        return result

    def _shorten_script(self, script: str, target_length: int) -> str:
        """使用AI缩减文案长度"""
        response = self.client.chat.completions.create(
            model="claude-haiku-3.5",  # 用更快的模型
            messages=[{
                "role": "user",
                "content": f"将以下文案缩减到{target_length}字以内，保留核心信息：\n\n{script}"
            }],
            max_tokens=200
        )
        return response.choices[0].message.content

# 测试代码
if __name__ == "__main__":
    agent = TextAgent()
    result = agent.generate({
        'product_name': 'AI智能日历',
        'category': '效率工具',
        'selling_points': '自动整理日程,智能提醒,跨平台同步',
        'target_audience': '25-35岁职场人士',
        'tone': '科技感'
    })
    print(result)
```

**Prompt模板：`prompts/script.jinja2`**
```jinja2
你是一位资深广告文案，需要为以下产品创作30秒视频脚本。

【产品信息】
名称：{{ product_name }}
类别：{{ category }}
核心卖点：{{ selling_points }}
目标受众：{{ target_audience }}
情感调性：{{ tone }}

{% if must_include %}
【必须包含】
{{ must_include }}
{% endif %}

{% if avoid %}
【禁止出现】
{{ avoid }}
{% endif %}

【创作要求】
1. **时长控制**：严格30秒（75-90字）
2. **结构**：
   - 0-5秒：开场钩子（用问句或冲突场景抓注意力）
   - 5-20秒：解决方案（展示产品如何解决痛点）
   - 20-30秒：行动号召（明确的CTA，如"立即下载""扫码试用"）
3. **语言风格**：
   - 口语化，避免书面语
   - 短句为主，节奏感强
   - 具体而非抽象（"每天节省2小时" > "提高效率"）
4. **情感调性**：{{ tone }}

【输出格式】
返回JSON：
{
  "hook": "开场钩子（一句话，10-15字）",
  "problem": "痛点描述（20-30字）",
  "solution": "解决方案（40-50字，产品核心价值）",
  "cta": "行动号召（10-15字，包含具体动作和利益点）",
  "full_script": "完整旁白文本（将以上内容串联，75-90字）",
  "visual_hints": ["画面1提示", "画面2提示", "画面3提示"]
}

开始创作：
```

#### 2. Image Agent（视觉生成）

**文件：`/workshop/workflow/image_agent/agent.py`**
```python
import os
import asyncio
from typing import Dict, Any, List
from wavespeed import WaveSpeedClient
from PIL import Image
import aiohttp

class ImageAgent:
    """
    图像生成Agent
    根据脚本生成6-8个关键帧
    """

    def __init__(self):
        self.client = WaveSpeedClient(
            api_key=os.getenv('WAVESPEED_API_KEY')
        )

    async def generate(
        self,
        text_output: Dict[str, Any],
        visual_requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        生成场景图像

        Args:
            text_output: Text Agent的输出
            visual_requirements: {
                'style': str,           # 风格（科技感/温情/专业等）
                'primary_color': str,   # 主色调（HEX）
                'aspect_ratio': str,    # 比例（16:9或9:16）
                'must_include': List[str],  # 必须出现的元素
                'brand_assets': List[str]   # 品牌素材路径
            }

        Returns:
            List of {
                'scene_id': int,
                'image_url': str,
                'prompt': str,
                'duration': float  # 建议持续时长（秒）
            }
        """

        # 1. 规划场景
        scenes = self._plan_scenes(text_output, visual_requirements)

        # 2. 并行生成图像
        tasks = [
            self._generate_single_scene(scene, visual_requirements)
            for scene in scenes
        ]
        results = await asyncio.gather(*tasks)

        # 3. 后处理（统一风格、添加品牌元素）
        results = await self._post_process(results, visual_requirements)

        return results

    def _plan_scenes(
        self,
        text_output: Dict[str, Any],
        visual_requirements: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        根据脚本规划场景
        使用AI自动分镜
        """
        prompt = f"""
根据以下广告脚本，规划6个关键场景（每个场景3-5秒）。

脚本：
{text_output['full_script']}

视觉提示：
{text_output.get('visual_hints', [])}

要求：
1. 每个场景要有清晰的视觉焦点
2. 场景之间要有逻辑递进
3. 符合{visual_requirements['style']}风格

返回JSON数组：
[
  {{
    "scene_id": 1,
    "timing": "0-5秒",
    "description": "具体画面描述",
    "camera_angle": "特写/中景/远景",
    "mood": "情绪氛围"
  }},
  ...
]
"""

        response = self.client.chat.completions.create(
            model="claude-sonnet-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        return response.choices[0].message.content['scenes']

    async def _generate_single_scene(
        self,
        scene: Dict[str, str],
        visual_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成单个场景图像
        """
        # 构建图像生成prompt
        image_prompt = self._build_image_prompt(scene, visual_requirements)

        # 调用WaveSpeed图像API
        response = await self.client.images.generate_async(
            model="flux-pro-1.1",
            prompt=image_prompt,
            width=1920 if visual_requirements['aspect_ratio'] == '16:9' else 1080,
            height=1080 if visual_requirements['aspect_ratio'] == '16:9' else 1920,
            num_images=1,
            style_preset=visual_requirements['style'],
            color_palette=[visual_requirements['primary_color']]
        )

        return {
            'scene_id': scene['scene_id'],
            'image_url': response.data[0].url,
            'prompt': image_prompt,
            'duration': self._calculate_duration(scene),
            'metadata': scene
        }

    def _build_image_prompt(
        self,
        scene: Dict[str, str],
        visual_requirements: Dict[str, Any]
    ) -> str:
        """
        构建图像生成的详细prompt
        """
        # 基础描述
        prompt_parts = [scene['description']]

        # 风格控制
        style_map = {
            '科技感': 'futuristic, clean, minimalist, neon accents, digital interface',
            '温情': 'warm lighting, soft focus, natural tones, human connection',
            '专业': 'corporate, professional, clean lines, business environment',
            '活力': 'vibrant colors, dynamic composition, energetic, youthful'
        }
        prompt_parts.append(style_map.get(visual_requirements['style'], ''))

        # 色彩控制
        prompt_parts.append(f"dominant color: {visual_requirements['primary_color']}")

        # 镜头控制
        prompt_parts.append(f"{scene['camera_angle']} shot")

        # 质量控制
        prompt_parts.append("high quality, 4k, professional photography")

        # 必须包含的元素
        if visual_requirements.get('must_include'):
            prompt_parts.append(f"must include: {', '.join(visual_requirements['must_include'])}")

        return ', '.join(prompt_parts)

    async def _post_process(
        self,
        images: List[Dict[str, Any]],
        visual_requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        后处理：添加logo、统一色调等
        """
        processed = []

        for img_data in images:
            # 下载图像
            async with aiohttp.ClientSession() as session:
                async with session.get(img_data['image_url']) as resp:
                    img_bytes = await resp.read()

            # 使用PIL处理
            img = Image.open(io.BytesIO(img_bytes))

            # 如果有logo，添加水印
            if visual_requirements.get('brand_assets'):
                logo_path = visual_requirements['brand_assets'][0]
                img = self._add_logo(img, logo_path)

            # 色彩校正（确保主色调一致）
            img = self._color_correction(
                img,
                visual_requirements['primary_color']
            )

            # 保存
            output_path = f"/app/outputs/scene_{img_data['scene_id']}.png"
            img.save(output_path)

            img_data['processed_path'] = output_path
            processed.append(img_data)

        return processed

    def _add_logo(self, image: Image, logo_path: str) -> Image:
        """在图像右下角添加logo水印"""
        logo = Image.open(logo_path).convert("RGBA")

        # 调整logo大小（占图像宽度的10%）
        logo_width = int(image.width * 0.1)
        aspect_ratio = logo.height / logo.width
        logo_height = int(logo_width * aspect_ratio)
        logo = logo.resize((logo_width, logo_height))

        # 计算位置（右下角，留20px边距）
        position = (
            image.width - logo_width - 20,
            image.height - logo_height - 20
        )

        # 粘贴logo
        image.paste(logo, position, logo)
        return image

    def _color_correction(self, image: Image, target_color: str) -> Image:
        """
        色彩校正，增强目标颜色
        """
        # 将HEX转RGB
        target_rgb = tuple(int(target_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

        # 简单的色彩增强（实际可用更复杂的算法）
        # 这里仅作示意
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.2)  # 增强饱和度

        return image

    def _calculate_duration(self, scene: Dict[str, str]) -> float:
        """
        根据场景内容计算建议持续时间
        """
        timing = scene.get('timing', '0-5秒')
        # 解析timing字符串
        start, end = timing.replace('秒', '').split('-')
        return float(end) - float(start)

# 测试代码
if __name__ == "__main__":
    import asyncio

    agent = ImageAgent()

    text_output = {
        'full_script': '每天20+会议，你还在手动记录？AI智能日历帮你一句话搞定！',
        'visual_hints': ['焦虑的职场人', 'AI界面特写', '轻松的表情']
    }

    visual_requirements = {
        'style': '科技感',
        'primary_color': '#0066FF',
        'aspect_ratio': '16:9',
        'must_include': ['产品界面'],
        'brand_assets': ['/path/to/logo.png']
    }

    result = asyncio.run(agent.generate(text_output, visual_requirements))
    print(result)
```

#### 3. Video Agent（视频合成）

**文件：`/workshop/workflow/video_agent/agent.py`**
```python
import os
from typing import Dict, Any, List
from wavespeed import WaveSpeedClient
import subprocess
import json

class VideoAgent:
    """
    视频合成Agent
    将图像、文案、配音、音乐合成最终视频
    """

    def __init__(self):
        self.client = WaveSpeedClient(
            api_key=os.getenv('WAVESPEED_API_KEY')
        )

    async def generate(
        self,
        text_output: Dict[str, Any],
        image_outputs: List[Dict[str, Any]],
        audio_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成最终视频

        Args:
            text_output: Text Agent输出
            image_outputs: Image Agent输出的场景列表
            audio_requirements: {
                'voiceover': bool,      # 是否需要配音
                'voice_type': str,      # 男声/女声
                'bgm_style': str,       # 背景音乐风格
                'bgm_volume': float     # 音乐音量（0-1）
            }

        Returns:
            {
                'video_url': str,
                'duration': float,
                'file_size': int,
                'thumbnail_url': str
            }
        """

        # 1. 生成配音（如果需要）
        voiceover_path = None
        if audio_requirements.get('voiceover'):
            voiceover_path = await self._generate_voiceover(
                text_output['full_script'],
                audio_requirements['voice_type']
            )

        # 2. 选择背景音乐
        bgm_path = await self._select_bgm(audio_requirements['bgm_style'])

        # 3. 使用FFmpeg合成视频
        video_path = await self._compose_video(
            image_outputs,
            voiceover_path,
            bgm_path,
            audio_requirements
        )

        # 4. 生成缩略图
        thumbnail_path = self._generate_thumbnail(video_path)

        # 5. 上传到CDN
        video_url, thumbnail_url = await self._upload_to_cdn(
            video_path,
            thumbnail_path
        )

        return {
            'video_url': video_url,
            'duration': sum(img['duration'] for img in image_outputs),
            'file_size': os.path.getsize(video_path),
            'thumbnail_url': thumbnail_url,
            'local_path': video_path
        }

    async def _generate_voiceover(
        self,
        script: str,
        voice_type: str
    ) -> str:
        """
        使用WaveSpeed TTS生成配音
        """
        voice_map = {
            '男声': 'zh-CN-YunxiNeural',
            '女声': 'zh-CN-XiaoxiaoNeural',
            '儿童': 'zh-CN-XiaoyiNeural'
        }

        response = await self.client.audio.speech.create_async(
            model="azure-tts",  # 或使用WaveSpeed自己的TTS
            voice=voice_map.get(voice_type, 'zh-CN-XiaoxiaoNeural'),
            input=script,
            speed=1.0,  # 语速
            pitch=1.0   # 音调
        )

        # 保存音频
        output_path = "/app/outputs/voiceover.mp3"
        with open(output_path, 'wb') as f:
            f.write(response.content)

        return output_path

    async def _select_bgm(self, style: str) -> str:
        """
        选择背景音乐
        可以从预设库选择，或使用AI生成
        """
        # 方案A：从预设库选择
        bgm_library = {
            '轻快电子乐': '/assets/bgm/upbeat-electronic.mp3',
            '舒缓钢琴': '/assets/bgm/calm-piano.mp3',
            '激励节奏': '/assets/bgm/motivational-beat.mp3',
            '科技感': '/assets/bgm/tech-ambient.mp3'
        }

        if style in bgm_library:
            return bgm_library[style]

        # 方案B：使用AI生成（如果有预算）
        # response = await self.client.audio.music.generate_async(
        #     prompt=f"{style}风格，30秒，适合广告背景",
        #     duration=30
        # )
        # return response.url

        return bgm_library['科技感']  # 默认

    async def _compose_video(
        self,
        scenes: List[Dict[str, Any]],
        voiceover_path: str,
        bgm_path: str,
        audio_requirements: Dict[str, Any]
    ) -> str:
        """
        使用FFmpeg合成视频
        """
        # 1. 创建FFmpeg滤镜脚本
        filter_complex = self._build_filter_complex(scenes, audio_requirements)

        # 2. 构建FFmpeg命令
        cmd = [
            'ffmpeg',
            '-y',  # 覆盖输出文件
        ]

        # 添加输入文件（所有场景图片）
        for scene in scenes:
            cmd.extend([
                '-loop', '1',
                '-t', str(scene['duration']),
                '-i', scene['processed_path']
            ])

        # 添加音频输入
        if voiceover_path:
            cmd.extend(['-i', voiceover_path])
        cmd.extend(['-i', bgm_path])

        # 添加滤镜
        cmd.extend([
            '-filter_complex', filter_complex,
            '-map', '[v]',  # 视频轨
            '-map', '[a]',  # 音频轨
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', '+faststart',  # 优化在线播放
            '/app/outputs/final.mp4'
        ])

        # 3. 执行
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if process.returncode != 0:
            raise Exception(f"FFmpeg失败: {process.stderr}")

        return '/app/outputs/final.mp4'

    def _build_filter_complex(
        self,
        scenes: List[Dict[str, Any]],
        audio_requirements: Dict[str, Any]
    ) -> str:
        """
        构建FFmpeg滤镜复杂图
        """
        filters = []

        # 视频部分：拼接所有场景并添加转场效果
        video_inputs = []
        for i, scene in enumerate(scenes):
            # 缩放到统一尺寸
            filters.append(f"[{i}:v]scale=1920:1080,setsar=1[v{i}]")
            video_inputs.append(f"[v{i}]")

        # 拼接视频，添加交叉淡入淡出转场
        concat_filter = ''.join(video_inputs)
        concat_filter += f"concat=n={len(scenes)}:v=1:a=0[vconcat]"
        filters.append(concat_filter)

        # 添加淡入淡出效果
        filters.append("[vconcat]fade=t=in:st=0:d=0.5,fade=t=out:st=29.5:d=0.5[v]")

        # 音频部分：混合配音和背景音乐
        audio_filters = []
        audio_inputs_count = len(scenes)

        if audio_requirements.get('voiceover'):
            # 有配音
            voiceover_index = audio_inputs_count
            bgm_index = audio_inputs_count + 1

            # 调整BGM音量
            bgm_volume = audio_requirements.get('bgm_volume', 0.3)
            audio_filters.append(
                f"[{bgm_index}:a]volume={bgm_volume}[bgm];"
                f"[{voiceover_index}:a][bgm]amix=inputs=2:duration=first[a]"
            )
        else:
            # 无配音，只有BGM
            bgm_index = audio_inputs_count
            audio_filters.append(f"[{bgm_index}:a]volume=0.5[a]")

        filters.extend(audio_filters)

        return ';'.join(filters)

    def _generate_thumbnail(self, video_path: str) -> str:
        """
        生成视频缩略图（取第1秒的帧）
        """
        thumbnail_path = '/app/outputs/thumbnail.jpg'

        subprocess.run([
            'ffmpeg',
            '-y',
            '-i', video_path,
            '-ss', '00:00:01',
            '-vframes', '1',
            '-q:v', '2',
            thumbnail_path
        ])

        return thumbnail_path

    async def _upload_to_cdn(
        self,
        video_path: str,
        thumbnail_path: str
    ) -> tuple:
        """
        上传到WaveSpeed CDN
        """
        # 上传视频
        with open(video_path, 'rb') as f:
            video_upload = await self.client.files.upload_async(
                file=f,
                purpose='video'
            )

        # 上传缩略图
        with open(thumbnail_path, 'rb') as f:
            thumb_upload = await self.client.files.upload_async(
                file=f,
                purpose='image'
            )

        return (video_upload.url, thumb_upload.url)

# 测试代码
if __name__ == "__main__":
    import asyncio

    agent = VideoAgent()

    # 模拟输入
    text_output = {'full_script': '每天20+会议...'}
    image_outputs = [
        {'scene_id': 1, 'processed_path': '/path/1.png', 'duration': 5},
        {'scene_id': 2, 'processed_path': '/path/2.png', 'duration': 10},
        # ...
    ]
    audio_requirements = {
        'voiceover': True,
        'voice_type': '女声',
        'bgm_style': '科技感',
        'bgm_volume': 0.3
    }

    result = asyncio.run(agent.generate(
        text_output,
        image_outputs,
        audio_requirements
    ))
    print(result)
```

### Web界面代码

**文件：`/workshop/web-interface/src/App.jsx`**
```jsx
import React, { useState } from 'react';
import InputForm from './components/InputForm';
import ProgressMonitor from './components/ProgressMonitor';
import VideoPreview from './components/VideoPreview';
import './App.css';

function App() {
  const [stage, setStage] = useState('input'); // input | generating | complete
  const [progress, setProgress] = useState([]);
  const [result, setResult] = useState(null);

  const handleSubmit = async (formData) => {
    setStage('generating');

    // 调用后端API
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(formData)
    });

    // 处理Server-Sent Events
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;

      const lines = decoder.decode(value).split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const event = JSON.parse(line.slice(6));

          setProgress(prev => [...prev, event]);

          if (event.stage === 'complete') {
            setResult(event.result);
            setStage('complete');
          }
        }
      }
    }
  };

  return (
    <div className="App">
      <header>
        <h1>🎬 AI广告生成器</h1>
        <p>WaveSpeed AI × Linode</p>
      </header>

      <main>
        {stage === 'input' && (
          <InputForm onSubmit={handleSubmit} />
        )}

        {stage === 'generating' && (
          <ProgressMonitor progress={progress} />
        )}

        {stage === 'complete' && (
          <VideoPreview result={result} onRegenerate={() => setStage('input')} />
        )}
      </main>
    </div>
  );
}

export default App;
```

（由于篇幅限制，完整代码已提供核心部分，其他组件类似）

---

## 🎨 商业派轨道详细设计

### 创意工具包内容清单

#### 1. 纸质工具（每组一套）

**《产品速写卡》**
- 尺寸：A5（148mm × 210mm）
- 材质：250g铜版纸
- 内容：结构化表单，引导快速提炼产品核心信息

**《受众画像工作表》**
- 尺寸：A4（210mm × 297mm）
- 材质：双面印刷
- 正面：定量属性（年龄、职业、收入等）
- 反面：定性属性（痛点、渴望、行为习惯）

**《30秒脚本模板》**
- 尺寸：A3（297mm × 420mm）
- 材质：白板纸（可擦写）
- 配套：水性笔3支（黑/蓝/红）
- 布局：三段式结构，每段有画面栏和文案栏

**《情绪板拼贴纸》**
- 尺寸：A4
- 内容：100+小图片（各种场景、人物、物品、色彩）
- 用途：剪裁拼贴，可视化创意想法

**《色彩卡》**
- 尺寸：名片大小
- 数量：30张
- 内容：每张一种颜色+情感标签（如"#FF6B6B-激情红-紧迫感"）

**《风格参考卡》**
- 尺寸：明信片大小
- 数量：12张
- 内容：每张展示一种广告风格（科技、温情、专业等）+ 文案示例

#### 2. 数字工具（平板电脑/电脑访问）

**《案例库网页》**
- URL: `http://workshop.local/cases`
- 内容：
  - 50+优秀广告案例（按行业分类）
  - 每个案例有：视频、脚本文本、数据分析（点击率、转化率）
  - 筛选功能：按行业/时长/风格/预算筛选

**《创意生成器》**
- URL: `http://workshop.local/ideator`
- 功能：
  - 输入关键词，AI生成10个创意方向
  - 提供"痛点库"（1000+常见痛点）
  - 提供"CTA库"（100+高转化行动号召）

**《视觉素材库》**
- URL: `http://workshop.local/assets`
- 内容：
  - 免费商用图片库（Unsplash API）
  - 免费图标库（Flaticon）
  - 音乐库试听（按情绪分类）

#### 3. 引导手册

**《15分钟创意冲刺指南》**
- 格式：折页小册子（A4折3折）
- 内容：
  ```
  第1-5分钟：产品定义
  ├─ 填写《产品速写卡》
  ├─ 用"一句话介绍法"描述产品
  └─ 确定核心卖点（不超过3个）

  第6-10分钟：受众洞察
  ├─ 填写《受众画像工作表》
  ├─ 共情练习：假装你就是目标用户
  └─ 找到"痛点-渴望"的落差

  第11-15分钟：创意构思
  ├─ 参考3个案例（不同风格）
  ├─ 用"what if"头脑风暴
  └─ 选定1个最强创意方向
  ```

### 导师引导话术库

#### 开场引导（0:05-0:07）

**话术1：案例启发**
```
"大家看这三个案例，虽然行业不同，但都遵循一个黄金公式：
痛点 → 方案 → 行动

第一个Cole Haan的广告，开场5秒就让你想到'对啊，皮鞋确实不舒服'，
这就是痛点共鸣的力量。

接下来10分钟，你们的任务是找到自己产品的'那个痛点'。"
```

**话术2：降低焦虑**
```
"我知道10分钟策划一个广告听起来很疯狂，但别担心，
我们提供了所有工具，你只需要回答几个问题：
1. 你的用户最头疼什么？
2. 你的产品怎么帮他？
3. 他为什么要现在行动？

想清楚这三个，广告就有了。"
```

#### 受众洞察引导（0:10-0:15）

**话术3：共情练习**
```
"现在请大家闭眼，想象一下：
你的目标用户，早上7点醒来，第一件事做什么？
通勤路上在想什么？
工作中遇到什么烦恼？
晚上刷手机时在寻找什么？

好，睁眼。把刚才想到的场景，写在《受众画像》的'核心痛点'栏。"
```

**话术4：痛点挖掘**
```
"痛点不是'我们的产品不够好'，而是'用户的生活哪里不舒服'。

举例：
❌ 错误："市面上的日历App功能太少" → 这是竞品分析
✅ 正确："每天被碎片化会议淹没，找不到完整时间深度工作" → 这是用户痛点

大家再看看自己写的，是痛点还是产品缺陷？"
```

#### 脚本创作引导（0:15-0:20）

**话术5：开场钩子技巧**
```
"开场5秒是生死线，用户决定划走还是继续看。

三种高效钩子：
1. 问句式："你是不是也..."（制造共鸣）
2. 冲突式："为什么别人XX，而你..."（激发好奇）
3. 数据式："每天XX次/XX%的人..."（建立权威）

现在用一种方式，写出你的钩子，15字以内。"
```

**话术6：视觉化描述**
```
"写画面描述时，要具体到导演能直接拍。

对比：
❌ '一个人在工作' → 导演不知道怎么拍
✅ '一个穿白衬衫的男人，盯着三个显示器，眉头紧锁，快速切换标签页' → 画面感强

大家把脚本里的画面描述，加上至少一个具体细节。"
```

#### 巡场问题解答

**Q1："我们组想法太多，选不出来怎么办？"**
```
A: "很好！说明大家很有创意。现在用'30秒测试'：
每个想法用一句话说清楚，计时30秒讲给组员听。
听众如果点头or眼睛亮了，就是好创意。
听众如果皱眉or问'什么意思'，就放弃。"
```

**Q2："我们的产品太复杂，30秒讲不清楚怎么办？"**
```
A: "广告不是产品说明书，只需要传递一个核心价值。
问自己：如果用户只能记住一句话，你希望是什么？
把那句话放在15-20秒的位置，反复强调。"
```

**Q3："我们不知道目标受众是谁，怎么定位？"**
```
A: "从'谁会为这个买单'倒推。
想象有人掏钱买你的产品，他当时在什么场景？遇到什么问题？
描述那个场景和人，就是你的受众。"
```

### 《技术对接表》详细模板

**数字版表单（自动生成JSON）**

访问：`http://workshop.local/handoff-form`

```
┌────────────────────────────────────────┐
│  WaveSpeed AI 广告生成 - 创意输入表    │
├────────────────────────────────────────┤
│                                        │
│  📦 基础信息                           │
│                                        │
│  产品名称: [___________________]       │
│  产品类别: [下拉选择: SaaS/电商/...] │
│  目标受众: [___________________]       │
│                                        │
├────────────────────────────────────────┤
│  💡 创意策略                           │
│                                        │
│  核心卖点 (最多3个):                  │
│  1. [_____________________________]   │
│  2. [_____________________________]   │
│  3. [_____________________________]   │
│                                        │
│  情感调性: [多选: □科技 □温情 □专业] │
│                                        │
│  核心痛点描述:                        │
│  [________________________________]   │
│  [________________________________]   │
│                                        │
├────────────────────────────────────────┤
│  ✍️ 脚本内容                           │
│                                        │
│  开场钩子 (0-5秒):                    │
│  [________________________________]   │
│  字数: 0/15                           │
│                                        │
│  核心文案 (5-20秒):                   │
│  [________________________________]   │
│  [________________________________]   │
│  字数: 0/60                           │
│                                        │
│  行动号召 (20-30秒):                  │
│  [________________________________]   │
│  字数: 0/15                           │
│                                        │
│  [预览完整脚本] 总字数: 0/90          │
│  [试读脚本 🔊] 预计时长: 0秒          │
│                                        │
├────────────────────────────────────────┤
│  🎨 视觉要求                           │
│                                        │
│  风格: [滑块选择]                     │
│  ├─ 科技感 ━━●━━━━━━ 温情感           │
│  ├─ 冷色调 ━━━━●━━━ 暖色调           │
│  └─ 极简   ━━━━━●━━ 丰富             │
│                                        │
│  主色调: [🎨] #______                 │
│  辅助色: [🎨] #______                 │
│                                        │
│  必须包含元素:                        │
│  [________________________________]   │
│  例如：logo、产品截图、特定场景        │
│                                        │
│  禁止出现:                            │
│  [________________________________]   │
│  例如：竞品、特定颜色、敏感内容        │
│                                        │
├────────────────────────────────────────┤
│  🎬 技术参数                           │
│                                        │
│  画面比例:                            │
│  ○ 16:9 (横屏，适合电脑/电视)         │
│  ○ 9:16 (竖屏，适合手机/抖音)         │
│  ○ 1:1  (方形，适合Instagram)         │
│                                        │
│  配音:                                │
│  ○ 男声  ○ 女声  ○ 不需要            │
│                                        │
│  背景音乐:                            │
│  [下拉选择: 轻快电子乐/舒缓钢琴/...] │
│  音量: ━━━●━━━━━━ 50%                │
│  [试听 🔊]                            │
│                                        │
├────────────────────────────────────────┤
│  📎 补充素材                           │
│                                        │
│  logo: [上传文件] ✓ logo.png (已上传) │
│  产品图: [上传文件] ✓ 3张已上传       │
│  参考视频: [粘贴链接] ________________│
│                                        │
├────────────────────────────────────────┤
│  ⚙️ 高级选项 (可选)                   │
│                                        │
│  [展开]                               │
│  ├─ 场景数量: [滑块] 6场景            │
│  ├─ 转场效果: [下拉] 交叉淡入淡出     │
│  ├─ 字幕: □ 自动添加字幕              │
│  └─ 特效: □ 动态文字 □ 镜头运动      │
│                                        │
├────────────────────────────────────────┤
│  📋 检查清单                           │
│                                        │
│  ✓ 脚本字数在75-90之间                │
│  ✓ 已填写所有必填项                  │
│  ✓ 已上传必要素材                    │
│  ✓ 已试读脚本确认时长                │
│                                        │
│  [生成预览JSON]  [提交给技术派 🚀]   │
└────────────────────────────────────────┘
```

**自动验证规则**：
```javascript
// 前端验证逻辑
const validation = {
  product_name: {
    required: true,
    maxLength: 20,
    message: "产品名称不能超过20字"
  },
  selling_points: {
    required: true,
    minItems: 1,
    maxItems: 3,
    message: "请填写1-3个核心卖点"
  },
  script: {
    hook: {
      required: true,
      maxLength: 15,
      message: "开场钩子不超过15字"
    },
    core: {
      required: true,
      minLength: 40,
      maxLength: 60,
      message: "核心文案40-60字"
    },
    cta: {
      required: true,
      maxLength: 15,
      mustInclude: ['扫码', '下载', '访问', '搜索', '试用'], // 至少包含一个行动词
      message: "行动号召必须包含明确动作"
    },
    total: {
      minLength: 75,
      maxLength: 90,
      message: "总字数必须在75-90之间（对应30秒）"
    }
  },
  visual: {
    primary_color: {
      required: true,
      format: /^#[0-9A-F]{6}$/i,
      message: "请选择有效的颜色"
    }
  },
  assets: {
    logo: {
      required: true,
      maxSize: 5 * 1024 * 1024, // 5MB
      formats: ['png', 'jpg', 'svg'],
      message: "logo必须上传，支持PNG/JPG/SVG，不超过5MB"
    }
  }
};

// 实时字数统计
function updateWordCount(text, fieldName) {
  const count = text.length;
  const limit = validation.script[fieldName].maxLength;
  const indicator = document.getElementById(`${fieldName}-count`);

  indicator.textContent = `${count}/${limit}`;
  indicator.style.color = count > limit ? 'red' : 'green';
}

// 试读功能（预估时长）
function previewScript() {
  const fullScript = [
    document.getElementById('hook').value,
    document.getElementById('core').value,
    document.getElementById('cta').value
  ].join(' ');

  const wordCount = fullScript.length;
  const estimatedDuration = Math.round(wordCount / 3); // 平均3字/秒

  document.getElementById('duration-estimate').textContent =
    `${estimatedDuration}秒`;

  // 如果浏览器支持，朗读出来
  if ('speechSynthesis' in window) {
    const utterance = new SpeechSynthesisUtterance(fullScript);
    utterance.lang = 'zh-CN';
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
  }
}

// 提交前最终检查
function submitToTech() {
  const errors = [];

  // 检查所有必填项
  if (!validation.product_name.required) errors.push('产品名称必填');
  // ... 其他检查

  if (errors.length > 0) {
    alert('请修正以下问题:\n' + errors.join('\n'));
    return false;
  }

  // 生成JSON
  const formData = {
    // ... 收集所有表单数据
  };

  // 显示二维码（技术派扫描获取数据）
  const qrCode = generateQRCode(JSON.stringify(formData));
  showModal('请技术派扫描此二维码获取创意需求', qrCode);

  // 同时通过网络发送
  fetch('/api/handoff', {
    method: 'POST',
    body: JSON.stringify(formData)
  });
}
```

---

## 🔄 合流协作机制详细设计

### 对接界面设计

**技术派视角**：
```
┌───────────────────────────────────────────┐
│  🎨 创意需求已接收                        │
├───────────────────────────────────────────┤
│  来自: 第3组 - 商业派                     │
│  产品: AI智能日历                        │
│  时间: 14:35                             │
├───────────────────────────────────────────┤
│  📋 需求概览                              │
│                                           │
│  核心卖点:                               │
│  • 自动整理日程                          │
│  • 智能提醒                              │
│  • 跨平台同步                            │
│                                           │
│  脚本字数: 87字 ✓                        │
│  素材完整度: 100% ✓                      │
│  预计生成时间: 10-12分钟                  │
│                                           │
├───────────────────────────────────────────┤
│  🚨 需要确认的技术细节                    │
│                                           │
│  ⚠️ "科技感+一点温度"如何理解？           │
│  [回复商业派] [查看参考图]               │
│                                           │
│  ⚠️ 产品截图分辨率较低，是否需要重新提供？ │
│  [接受] [请求重新上传]                    │
│                                           │
│  ⚠️ 背景音乐"轻快电子乐"有3个选项：       │
│  [ ] 选项A [试听]                        │
│  [ ] 选项B [试听]                        │
│  [ ] 选项C [试听]                        │
│  [让商业派选择]                          │
│                                           │
├───────────────────────────────────────────┤
│  ⚙️ Agent配置预览                        │
│                                           │
│  Text Agent:                             │
│  ├─ Model: Claude Sonnet 4               │
│  ├─ Temperature: 0.8                     │
│  └─ Prompt: [查看完整prompt]             │
│                                           │
│  Image Agent:                            │
│  ├─ Model: Flux Pro 1.1                  │
│  ├─ Style: cinematic + tech              │
│  ├─ Color: #0066FF (主色)                │
│  └─ Scenes: 6场景                        │
│                                           │
│  Video Agent:                            │
│  ├─ Resolution: 1920x1080 (16:9)         │
│  ├─ Voiceover: 女声 (zh-CN-Xiaoxiao)     │
│  ├─ BGM: tech-ambient.mp3 (30%)          │
│  └─ Duration: ~30s                       │
│                                           │
├───────────────────────────────────────────┤
│  [修改配置] [开始生成 🚀] [通知商业派]    │
└───────────────────────────────────────────┘
```

**商业派视角（在自己电脑上看到）**：
```
┌───────────────────────────────────────────┐
│  ⏳ 技术派正在处理你的需求...             │
├───────────────────────────────────────────┤
│  当前状态: 等待你确认技术细节              │
│                                           │
│  📩 技术派的问题:                         │
│                                           │
│  ❓ "科技感+一点温度"具体是什么意思？      │
│                                           │
│  你的回复:                               │
│  [______________________________]         │
│  [发送] 或 [上传参考图]                  │
│                                           │
│  💡 提示: 可以说"整体冷色调蓝色，但人物   │
│     用暖光照亮"                           │
│                                           │
├───────────────────────────────────────────┤
│  🎵 请选择背景音乐:                       │
│                                           │
│  ( ) 选项A - 明快节奏型 [试听30s]         │
│  ( ) 选项B - 舒缓氛围型 [试听30s]         │
│  (●) 选项C - 科技感电子型 [试听30s] ✓     │
│                                           │
│  [确认选择]                              │
│                                           │
├───────────────────────────────────────────┤
│  预计还需: 2分钟确认 + 10分钟生成          │
│                                           │
│  💬 与技术派对话:                         │
│  [打开聊天窗口]                          │
└───────────────────────────────────────────┘
```

### 实时沟通机制

#### 方案A：即时通讯组件
```javascript
// 基于WebSocket的实时聊天

// 技术派发送消息
function askBusinessTeam(question) {
  const message = {
    from: 'tech',
    to: 'business',
    type: 'question',
    content: question,
    timestamp: Date.now()
  };

  ws.send(JSON.stringify(message));

  // 显示在界面上
  appendMessage('你问商业派', question, 'outgoing');

  // 等待回复（设置30秒超时）
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error('商业派30秒未回复，使用默认设置'));
    }, 30000);

    ws.onmessage = (event) => {
      const reply = JSON.parse(event.data);
      if (reply.type === 'answer') {
        clearTimeout(timeout);
        appendMessage('商业派回复', reply.content, 'incoming');
        resolve(reply.content);
      }
    };
  });
}

// 商业派接收并回复
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === 'question') {
    showNotification('技术派有问题需要确认');
    appendMessage('技术派问', message.content, 'incoming');

    // 显示快捷回复按钮
    showQuickReplies([
      '按默认处理',
      '我来详细说明',
      '看参考图'
    ]);
  }
};
```

#### 方案B：物理对接（推荐用于工作坊）
```
更简单直接的方式：
1. 商业派的"对接人"直接走到技术派工位
2. 面对面沟通2-3分钟
3. 技术派现场演示系统界面
4. 商业派直接在技术派电脑上操作表单提交
```

### 进度可视化设计

**大屏幕投影（全场共享）**：
```
┌─────────────────────────────────────────────────────────────────┐
│  🏆 WaveSpeed AI 广告生成挑战 - 实时进度                        │
├──────────┬──────────────────────┬─────────────┬─────────────────┤
│  小组    │  当前阶段            │  进度       │  预计完成       │
├──────────┼──────────────────────┼─────────────┼─────────────────┤
│  第1组   │  ✓ 文案生成完成      │  ████████░░ │  14:46 (8分钟)  │
│          │  → 图像生成中 (3/6)  │     80%     │                 │
├──────────┼──────────────────────┼─────────────┼─────────────────┤
│  第2组   │  ✓ 所有素材完成      │  ██████████ │  14:43 (已完成) │
│  🏆      │  → 正在导出视频      │    100%     │  [播放预览]     │
├──────────┼──────────────────────┼─────────────┼─────────────────┤
│  第3组   │  ⚠️ 等待商业派确认    │  ███░░░░░░░ │  14:50 (12分钟) │
│          │  (技术派已就绪)      │     30%     │  [查看问题]     │
├──────────┼──────────────────────┼─────────────┼─────────────────┤
│  第4组   │  ✓ 图像生成完成      │  █████████░ │  14:47 (9分钟)  │
│          │  → 视频合成中        │     90%     │                 │
├──────────┼──────────────────────┼─────────────┼─────────────────┤
│  第5组   │  ⚠️ 遇到错误          │  █████░░░░░ │  需要帮助!      │
│  🆘     │  场景2生成失败       │     50%     │  [呼叫导师]     │
└──────────┴──────────────────────┴─────────────┴─────────────────┘

最快完成: 第2组 (11分32秒) 🥇
平均进度: 70%
预计全部完成: 14:50
```

**单组详细进度（组内屏幕）**：
```
┌─────────────────────────────────────────┐
│  第3组 - 生成进度                       │
├─────────────────────────────────────────┤
│  14:38:05  ✓ 需求提交成功               │
│  14:38:12  ✓ Text Agent 启动            │
│  14:38:45  ✓ 文案生成完成               │
│            ├─ hook: "每天20+会议..."    │
│            ├─ 字数: 87字                │
│            └─ 时长: 29秒 ✓              │
│                                         │
│  14:39:00  ✓ Image Agent 启动           │
│  14:39:45  ✓ 场景1: 职场人物特写        │
│            [预览图] [放大] [重新生成]   │
│  14:40:30  ✓ 场景2: AI界面展示          │
│            [预览图]                    │
│  14:41:10  ⚠️ 场景3: 生成失败            │
│            错误: "logo包含不支持的文字"  │
│            解决: 已裁剪logo重新上传     │
│  14:41:50  ✓ 场景3: 重新生成成功        │
│  14:42:20  ✓ 场景4-6: 全部完成          │
│                                         │
│  14:42:30  ▶ Video Agent 运行中...      │
│            ├─ 合成视频: ████░░░ 60%    │
│            ├─ 生成配音: ██████ 100% ✓  │
│            └─ 混合音频: ███░░░ 50%     │
│                                         │
│  预计完成: 14:44 (还剩2分钟)             │
│                                         │
│  [暂停] [取消] [查看日志]               │
└─────────────────────────────────────────┘
```

### 协作中的常见场景与处理

#### 场景1：商业派中途想改文案
```
时间点: 14:42 (Image Agent已生成3个场景)

商业派: "我们想把开场改成'你的日历是不是总是乱糟糟？'"
技术派选项:
  A. 全部重新生成 (耗时+8分钟，风险大)
  B. 只重新生成Text+剩余Image (耗时+5分钟)
  C. 完成现有版本，导出后手动配音 (耗时+2分钟)

推荐: B
理由: 已生成的3个场景可能不受文案影响，只需调整后续场景
```

#### 场景2：技术派遇到API限流
```
时间点: 14:40 (Image Agent第2个场景)

错误: "WaveSpeed API rate limit exceeded"

应急方案:
1. 切换到备用API key (每组预分配3个key)
   ```python
   # 自动failover
   if error.code == 'rate_limit':
       switch_to_backup_key()
       retry_request()
   ```

2. 降低并发度
   ```python
   # 从3并发降到1并发
   concurrent_scenes = 1
   ```

3. 使用缓存素材库
   ```python
   # 如果完全无法调用API，使用预生成的场景模板
   use_cached_scenes(style='tech', count=6)
   ```
```

#### 场景3：成果不满意，需要快速迭代
```
时间点: 14:48 (初稿已完成，但第3个场景太暗)

快速修复流程:
1. 技术派不重新生成，直接调整
   ```python
   from workshop.video import quick_edit

   quick_edit.adjust_brightness(
       video_path='output.mp4',
       scene_index=3,
       brightness=1.4,
       output='output_v2.mp4'
   )
   # 耗时: 15秒
   ```

2. 商业派同步修改文案措辞
   ```python
   # 使用字幕覆盖（不重新配音）
   quick_edit.overlay_text(
       video_path='output_v2.mp4',
       new_text="让AI帮你搞定一切",
       timecode='00:00:15',
       output='output_final.mp4'
   )
   # 耗时: 10秒
   ```

总耗时: <30秒完成迭代
```

---

(由于篇幅限制，以下部分概述要点，完整内容继续...)

## 🏢 现场布置方案

### 空间规划
- **技术区** (左侧): 每桌2人，配电脑×2、大显示器×1、共享白板
- **商业区** (右侧): 每桌4人，配平板×2、纸质工具包、画板
- **合流区** (中间): 站立式高桌，便于两派对接
- **展示区** (前方): 大屏幕×2,一个显示全场进度，一个播放成果

### 设备清单
- Linode实例: 预部署20个 (4核8G)
- 电脑: 技术派自带笔记本 + 备用电脑×3
- 网络: 企业级Wi-Fi + 有线备份 + 4G热点备用
- 投影: 4K投影仪×2 + HDMI切换器

---

## 🚨 风险预案

### 技术风险
| 风险 | 概率 | 影响 | 预案 |
|------|------|------|------|
| API调用失败 | 中 | 高 | 3组备用API key + 本地模型fallback |
| 网络中断 | 低 | 高 | 4G热点 + 离线模式（预缓存素材） |
| 实例宕机 | 低 | 高 | 主备实例 + 15分钟内迁移 |

### 时间风险
- **缓冲时间**: 每个阶段预留20%缓冲
- **快速通道**: 如果某组严重落后，提供"模板模式"一键生成

---

## 🏆 评分标准

### 最佳创意奖 (40%)
- 创意独特性 (15分)
- 情感共鸣度 (15分)
- 商业可行性 (10分)

### 最佳技术奖 (30%)
- 代码质量 (10分)
- Agent架构优雅度 (10分)
- 问题解决能力 (10分)

### 最佳协作奖 (30%)
- 沟通效率 (10分)
- 角色互补性 (10分)
- 最终成果完整度 (10分)

---

## 📅 准备工作清单

### D-7 (活动前一周)
- [ ] Linode实例批量部署
- [ ] Docker镜像构建并测试
- [ ] 工具包印刷 (100套)
- [ ] 讲师培训 (3小时)

### D-3 (活动前三天)
- [ ] 全流程彩排 (模拟一组完整操作)
- [ ] 网络压力测试
- [ ] 应急预案演练

### D-1 (活动前一天)
- [ ] 现场布置
- [ ] 设备调试
- [ ] 备用物料到位

### D-Day (活动当天)
- [ ] 提前2小时到场
- [ ] 技术支持就位
- [ ] 最后一次系统检查

---

## 🔄 后续转化方案

### 活动结束后
1. **技术派**: 获得完整代码仓库访问权 + 1对1技术咨询30分钟
2. **商业派**: 获得创意方法论手册 + 营销资源包
3. **全员**: 加入「WaveSpeed AI创作者社群」,定期分享案例

### 长期价值
- 技术派可将agent系统商业化 (WaveSpeed提供扶持计划)
- 商业派可用生成的广告真实投放 (WaveSpeed赠送$100广告金)
- 促成技术+商业的合作项目

---

**文档版本**: v1.0-detailed
**最后更新**: 2025年12月
**预计实施时间**: 60分钟 ± 5分钟
**成功率预估**: 90%+ (基于充分准备)
