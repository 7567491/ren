# Vue 3 前端架构归档

## 归档日期
2026-01-14

## 归档原因
项目前端架构从 Vue 3 + Vite 迁移到单页静态 HTML，以简化部署和维护。

## 当前前端架构
**位置**：`/home/ren/frontend/dist/index.html`

**特点**：
- 单个 HTML 文件，包含所有 CSS 和 JavaScript
- 无需构建步骤，直接编辑即可
- 支持 API Key 输入、余额查询、任务创建等完整功能

## 本目录内容

### 源代码
- `src/` - Vue 3 组件和 TypeScript 源代码
- `src/App.vue` - 主应用组件
- `src/stores/` - Pinia 状态管理
- `src/components/` - UI 组件库

### 依赖和配置
- `package.json` - npm 依赖配置
- `package-lock.json` - 依赖版本锁定
- `node_modules/` - npm 安装的依赖包（约 203 个包）

### 构建工具
- `vite.config.ts` - Vite 构建配置
- `tsconfig*.json` - TypeScript 配置
- `vitest.config.ts` - 单元测试配置
- `.vite/` - Vite 缓存目录

### 其他
- `public/` - 静态资源目录
- `tests/` - 单元测试文件
- `index.html.old` - 旧的静态 HTML（用于新架构的基础）

## 技术栈（已废弃）
- Vue 3 (Composition API)
- TypeScript
- Vite 5
- Pinia (状态管理)
- Vitest (单元测试)

## 如何恢复（如需要）

如果需要恢复 Vue 架构，执行以下步骤：

```bash
# 1. 复制归档文件回 frontend 目录
cp -r /home/ren/frontend-vue-archive/* /home/ren/frontend/

# 2. 安装依赖
cd /home/ren/frontend
npm install

# 3. 启动开发服务器
npm run dev

# 4. 构建生产版本
npm run build
```

## 注意事项
- 本目录仅作为备份和参考，不再维护
- 新功能开发应基于当前的静态 HTML 架构
- 归档文件占用约 200MB 磁盘空间（主要是 node_modules）
