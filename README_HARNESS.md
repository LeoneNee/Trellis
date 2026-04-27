# Trellis Harness — 四合一 AI 编码工程化框架

基于 [Trellis v0.4.0](https://github.com/mindfold-ai/Trellis) 的增强版本，整合了四个项目的核心能力：

| 项目 | 角色 | 提供什么 |
|------|------|---------|
| **Trellis** | 骨架 | 项目结构、Spec 管理、Hook 注入、多平台、会话持久化 |
| **Superpowers** | 流程 | 计划编写、Subagent 执行、TDD、代码审查方法论 |
| **gstack** | 能力 | 产品思维 (office-hours)、代码审查、QA 浏览器、发布、学习系统 |
| **GitNexus** | 知识 | 代码知识图谱、影响分析、执行流追踪、变更检测 |

---

## 快速开始

### 1. 安装

```bash
# 从 GitHub 安装
npm install -g mindfold-ai/trellis#feature/harness-integration

# 或 clone 后本地链接
git clone -b feature/harness-integration https://github.com/mindfold-ai/Trellis.git trellis-harness
cd trellis-harness/packages/cli
npm link
```

### 2. 初始化项目

```bash
cd /your/project

# 完整版（推荐）
trellis init --claude --all -u yourname

# 按需选择
trellis init --claude --gitnexus -u yourname      # 只开 GitNexus
trellis init --claude --superpowers -u yourname    # 只开 Superpowers
trellis init --claude --gstack -u yourname         # 只开 gstack
```

### 3. 安装前置依赖

Trellis 生成的 command alias 只是路由层，实际技能需要单独安装：

```bash
# Superpowers（Claude Code 插件）
# 在 Claude Code 中运行：
/plugin install superpowers

# gstack（Claude Code Skills）
git clone https://github.com/garrytan/gstack ~/.claude/skills/gstack
cd ~/.claude/skills/gstack && ./setup

# GitNexus（知识图谱）
npm install -g gitnexus
# 在项目中索引：
npx gitnexus analyze
```

> **不需要全部安装**。缺少的技能会被自动跳过，不影响其他功能。

### 4. 开始使用

打开 Claude Code，使用 slash 命令：

```
/trellis:start           # 启动新会话，自动恢复上下文
/trellis:office-hours    # 产品思维探索
/trellis:write-plan      # 编写实施计划
/trellis:subagent-dispatch # 分派并行 Agent
/trellis:review          # 代码审查
/trellis:browse          # 浏览器 QA 测试
/trellis:ship            # 发布流程
/trellis:investigate     # 根因调试
```

---

## 整合工作流

```
阶段1: 产品探索 → /trellis:office-hours
阶段2: 规划     → /trellis:write-plan (+ GitNexus impact)
阶段3: 执行     → /trellis:subagent-dispatch (TDD + GitNexus 变更检测)
阶段4: 代码审查 → /trellis:review (+ GitNexus shape_check)
阶段5: QA 测试  → /trellis:browse
阶段6: 发布     → /trellis:ship
```

**全程**: GitNexus 提供代码知识图谱上下文（`query`、`context`、`impact`、`detect_changes`）

---

## 生成的文件结构

`trellis init --claude --all` 会生成：

```
.trellis/
├── config.yaml          # 含 gitnexus + skills 配置
├── workflow.md           # 整合工作流指南
├── spec/                 # 项目规范
├── tasks/                # 任务管理
├── workspace/{name}/     # 个人 journal + learnings
└── scripts/              # Python 脚本

.claude/
├── agents/               # 6 个 agent（4 个 GitNexus 增强版）
├── commands/trellis/     # 33 个 slash 命令
│   ├── (原有 14 个)
│   ├── write-plan.md     # → superpowers:writing-plans
│   ├── execute-plan.md   # → superpowers:executing-plans
│   ├── subagent-dispatch.md
│   ├── brainstorm.md
│   ├── tdd.md
│   ├── office-hours.md   # → gstack office-hours
│   ├── browse.md
│   ├── review.md
│   ├── ship.md
│   └── ...
└── hooks/                # 6 个 hook
    ├── session-start.py
    ├── gitnexus-augment.py      # GitNexus 搜索增强
    └── pre-commit-impact.py     # GitNexus 提交前影响检查
```

---

## 与原版 Trellis 的区别

| 功能 | 原版 | Harness 版 |
|------|------|-----------|
| CLI flags | `--claude --cursor` | 增加 `--gitnexus --superpowers --gstack --all` |
| config.yaml | session + monorepo | 增加 gitnexus + skills 路由 |
| Agents | 基础版 | GitNexus 增强版（影响分析、知识图谱搜索） |
| Commands | 14 个 | 33 个（+19 个技能路由命令） |
| Hooks | 4 个 | 6 个（+GitNexus 搜索增强 + 影响检查） |
| 工作流 | Trellis 原生 | 整合 7 阶段工作流 |

---

## 分享给其他人

### 方式 1: GitHub Fork（推荐）

```bash
# 1. 推送你的分支到 GitHub
cd /path/to/Trellis
git remote add myfork https://github.com/yourname/Trellis.git
git push myfork feature/harness-integration

# 2. 对方安装
npm install -g yourname/trellis#feature/harness-integration
```

### 方式 2: npm 发布

```bash
# 修改 packages/cli/package.json 中的 name
# "name": "@yourname/trellis"
npm publish --access public

# 对方安装
npm install -g @yourname/trellis
```

### 方式 3: 直接 clone

```bash
# 对方 clone 并链接
git clone -b feature/harness-integration https://github.com/yourname/Trellis.git
cd Trellis/packages/cli
pnpm install && pnpm build
npm link
```

---

## 铁律

1. **改代码 → 跑测试 → 读输出 → 修复 → 再跑 → 通过才交付**
2. **没有根因调查不做修复**
3. **每个 subagent 只做一件事**
4. **先写测试再写实现**
5. **编辑前查影响范围**（GitNexus impact）
6. **前后端功能必须通过前端走完整测试流程**

---

## 许可证

AGPL-3.0（继承自 Trellis 原版）
