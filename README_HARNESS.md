# Trellis 开发 Harness 审核报告 & 流程图

> 审核日期：2026-04-28 | 配置版本：superpowers 5.0.7 / gstack v1.15.0 (39 skills) / GitNexus hooks
> 修复日期：2026-04-27 | 全部问题已修复

---

## 一、配置总览

| 组件 | 状态 | 说明 |
|------|------|------|
| CLAUDE.md（全局指令） | ✅ 已修正 | Skill 路由表已映射到实际名称 |
| Hooks 系统 | ✅ 就绪 | 7 类钩子覆盖全生命周期 |
| GitNexus 集成 | ✅ 就绪 | Pre/Post 工具钩子 + MCP 工具 |
| Superpowers 插件 | ✅ 就绪 | 14 个 skill 已缓存 |
| gstack 技能 | ✅ 就绪 | 43 个 skill 已安装 (v1.15.0) |
| Harness 知识库 | ✅ 已注册 | PreToolUse(Edit\|Write\|Patch) 触发提醒 |
| Lesson Capture | ✅ 就绪 | prompt 匹配 + subagent 停止时捕获 |
| Auto-Approve | ✅ 就绪 | `trellis init --all` 自动创建 `.claude-approve` 标记 |
| 共识博弈 | ✅ 就绪 | 本地 skill，git commit 时自动触发 + Stop 钩子正确指向 |
| 计划自动审查 | ✅ 已修复 | Stop 钩子 → `/consensus-debate`（实际存在） |

---

## 二、完整开发流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          用户输入 Prompt                                      │
│                                                                             │
│  触发 Hook: UserPromptSubmit                                                │
│  ├── lesson-search.py   → 搜索 .harness/lessons/ 匹配经验注入上下文           │
│  └── plan-intent 检测   → 检测"制定计划"意图，标记 /tmp/claude_plan_intent_*  │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Skill 路由层（CLAUDE.md 技能路由表）                       │
│                                                                             │
│  匹配关键词 → Skill("name") 调用                                             │
│  ├── 产品想法/头脑风暴     → Skill("office-hours")              [gstack]    │
│  ├── 写计划/实施方案       → Skill("superpowers:writing-plans") [Super]     │
│  ├── 执行计划             → Skill("superpowers:executing-plans") [Super]     │
│  ├── 并行开发             → Skill("superpowers:dispatching-parallel-agents") │
│  ├── Bugs/报错            → Skill("investigate")               [gstack]    │
│  ├── 代码审查             → Skill("review")                    [gstack]    │
│  ├── QA/找bug             → Skill("qa") / Skill("browse")      [gstack]    │
│  ├── 部署/push/PR         → Skill("ship")                      [gstack]    │
│  ├── TDD                  → Skill("superpowers:test-driven-development")   │
│  ├── 计划评审/架构评审     → Skill("plan-eng-review")           [gstack]    │
│  ├── 多模型博弈           → Skill("consensus-debate")          [本地]      │
│  ├── 代码质量             → Skill("health")                    [gstack]    │
│  ├── 周度回顾             → Skill("retro")                     [gstack]    │
│  ├── 验证后交付           → Skill("superpowers:verification-before-completion") │
│  └── 系统化调试           → Skill("superpowers:systematic-debugging")        │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
          ┌────────────────────┼──────────────────────┐
          │                    │                      │
          ▼                    ▼                      ▼
   ┌──────────┐      ┌──────────────┐        ┌────────────┐
   │ 阶段1    │      │   阶段2-3    │        │  全程可用   │
   │ 产品探索  │      │   计划制定   │        │  调试/博弈  │
   └──────────┘      └──────────────┘        └────────────┘
```

### 7 阶段详细流程

```
═══════════════════════════════════════════════════════════════════════════════
 阶段 1: 产品探索 — Skill("office-hours")
═══════════════════════════════════════════════════════════════════════════════

 用户请求 ──→ Skill("office-hours")
                │
                └── YC 式六问 → 产品设计文档
                    │
                    └── 可选后续:
                        ├── Skill("plan-ceo-review")   → CEO 级评审
                        ├── Skill("plan-design-review") → 设计师视角评审
                        └── Skill("plan-eng-review")    → 工程经理评审


═══════════════════════════════════════════════════════════════════════════════
 阶段 2: 计划拆解 — Skill("superpowers:writing-plans")
═══════════════════════════════════════════════════════════════════════════════

 Skill("superpowers:writing-plans")
                │
                ├── 探索代码库
                │
                ├── Hook: PreToolUse(Grep|Glob|Bash)
                │   └── gitnexus-hook.cjs → 搜索时注入图谱上下文
                │
                ├── 查询 GitNexus impact（改代码前查影响范围）
                │   └── gitnexus_impact({target, direction: "upstream"})
                │
                ├── 撰写实施计划 → docs/superpowers/plans/*.md
                │
                └── Hook: PostToolUse(Write plans/*.md)
                    └── 标记计划意图 /tmp/claude_plan_intent_*


═══════════════════════════════════════════════════════════════════════════════
 阶段 3: 计划评审 — Skill("plan-eng-review") 或 Skill("consensus-debate")
═══════════════════════════════════════════════════════════════════════════════

 Skill("plan-eng-review")
                │
                └── 工程经理视角交互式评分
                    ├── 架构 / 数据流 / 边界 / 测试 / 性能

  或 Skill("consensus-debate")
                │
                └── 多模型博弈（minimax + glm → kimi-k2.5 judge）
                    ├── 提案 → 交叉评审 → Judge 汇总

  Hook: Stop（会话结束时）
                │
                └── 检测 plan_intent → 提示用 Skill("consensus-debate")


═══════════════════════════════════════════════════════════════════════════════
 阶段 4: TDD 执行 — Skill("superpowers:dispatching-parallel-agents")
═══════════════════════════════════════════════════════════════════════════════

 Skill("superpowers:dispatching-parallel-agents")
                │
                ├── 为每个独立任务创建 Todo
                ├── 分配给 subagent（team + worktree 隔离）
                │
                └── 每个 subagent 内部:
                    │
                    ├── Skill("superpowers:test-driven-development")
                    │   └── 红 → 绿 → 重构 循环
                    │
                    ├── Hook: PreToolUse(Grep|Glob|Bash)
                    │   └── gitnexus-hook.cjs → 搜索时注入图谱上下文
                    │
                    ├── Hook: PreToolUse(Edit|Write|Patch)
                    │   ├── auto-approve-hook.cjs → .claude-approve 自动授权
                    │   └── harness-hook.cjs     → 知识库提醒/初始化
                    │
                    ├── Hook: PermissionRequest(*)
                    │   └── auto-approve-hook.cjs → 权限自动审批
                    │
                    └── Hook: PostToolUse(Bash)
                        └── gitnexus-hook.cjs → 检测索引过期

  每个 subagent 完成后:
                │
                ├── gitnexus_detect_changes → 确认影响范围
                │
                └── Hook: SubagentStop
                    └── lesson-capture.py → 经验沉淀到 .harness/lessons/


═══════════════════════════════════════════════════════════════════════════════
 阶段 5: 代码审查 — Skill("review")
═══════════════════════════════════════════════════════════════════════════════

 Skill("review")
                │
                ├── PR 级 diff 审查：SQL安全/LLM信任边界/副作用
                │
                ├── Skill("superpowers:requesting-code-review")
                │   └── 验证工作满足要求后再提交审查
                │
                └── GitNexus API 兼容检查:
                    ├── gitnexus_shape_check  → 响应形状 vs 消费者
                    ├── gitnexus_api_impact   → API 路由消费者影响
                    └── gitnexus_detect_changes → 变更符号 + 受影响流程


═══════════════════════════════════════════════════════════════════════════════
 阶段 6: QA 测试 — Skill("qa") / Skill("browse")
═══════════════════════════════════════════════════════════════════════════════

 Skill("qa")
                │
                └── 系统化测试 → 发现 bug → 逐个修复 → 提交

 Skill("browse")
                │
                └── 无头浏览器：导航/交互/截图/响应式/表单

  验证循环（铁律）:
                │
                ├── pnpm test && pnpm build    # 后端
                ├── pnpm dev                    # 前端联调
                └── 前后端接口地址/参数一致性验证


═══════════════════════════════════════════════════════════════════════════════
 阶段 7: 发布 — Skill("ship")
═══════════════════════════════════════════════════════════════════════════════

 Skill("ship")
                │
                ├── 检测 + 合并 base branch
                ├── 跑测试
                ├── 审查 diff
                ├── bump VERSION
                ├── 更新 CHANGELOG
                │
                ├── git commit
                │   └── Hook: PreToolUse(Bash git commit*)
                │       └── consensus-debate/review_wrapper.py → 多模型博弈 review
                │
                ├── git push
                │
                └── Skill("superpowers:verification-before-completion")
                    └── 提交前必须跑验证命令 + 确认输出
```

---

## 三、钩子（Hooks）触发点汇总

```
┌────────────────────┬───────────────────┬───────────────────────────────────┐
│ Hook 类型          │ 匹配器             │ 触发的操作                         │
├────────────────────┼───────────────────┼───────────────────────────────────┤
│ UserPromptSubmit   │ .*                │ ① lesson-search.py 匹配经验注入   │
│                    │                   │ ② plan-intent 检测                │
├────────────────────┼───────────────────┼───────────────────────────────────┤
│ PreToolUse         │ Grep|Glob|Bash    │ gitnexus-hook.cjs 图谱上下文增强  │
│                    ├───────────────────┼───────────────────────────────────┤
│                    │ Edit|Write|Patch  │ ① auto-approve-hook.cjs 自动授权 │
│                    │                   │ ② harness-hook.cjs 知识库提醒     │
│                    ├───────────────────┼───────────────────────────────────┤
│                    │ Bash(git commit*) │ consensus-debate review_wrapper   │
├────────────────────┼───────────────────┼───────────────────────────────────┤
│ PostToolUse        │ Bash              │ gitnexus-hook.cjs 索引过期检测     │
│                    ├───────────────────┼───────────────────────────────────┤
│                    │ Write(plans/*.md) │ 清除 review_done 标记             │
├────────────────────┼───────────────────┼───────────────────────────────────┤
│ PermissionRequest  │ *                 │ auto-approve-hook.cjs 权限审批     │
├────────────────────┼───────────────────┼───────────────────────────────────┤
│ Stop               │ (session end)     │ 计划完成提示 → Skill("consensus-  │
│                    │                   │ debate")                          │
├────────────────────┼───────────────────┼───────────────────────────────────┤
│ SubagentStop       │ .*                │ lesson-capture.py 经验捕获         │
└────────────────────┴───────────────────┴───────────────────────────────────┘
```

---

## 四、数据流 & 知识循环

```
                    ┌──────────────────────┐
                    │   GitNexus 知识图谱    │
                    │  (.gitnexus/ 索引)    │
                    └──────┬───────────────┘
                           │
              ┌────────────┼────────────────┐
              │            │                │
              ▼            ▼                ▼
     PreToolUse      PostToolUse      手动调用
     搜索增强         索引过期提醒      impact/query/
     (自动)           (自动)           context/shape
              │            │                │
              └────────────┼────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  代码变更决策  │
                    └──────────────┘

     ┌──────────────────────────────────────────┐
     │            经验飞轮                        │
     │                                          │
     │  lesson-search.py ──→ 用户输入时匹配注入   │
     │         ↑                               │
     │         │                               │
     │  lesson-capture.py ←─ subagent 停止时捕获 │
     │         │                               │
     │         └──→ .harness/lessons/*.md       │
     │                                          │
     │  harness-hook.cjs ──→ 首次编辑时初始化     │
     │                  └──→ 后续编辑时提醒检查    │
     └──────────────────────────────────────────┘
```

---

## 五、Skill 来源映射表

### gstack Skills（本地安装，v1.15.0，43 个）

| Skill 名称 | 文件路径 | 阶段 |
|------------|---------|------|
| `office-hours` | `~/.claude/skills/gstack/office-hours/` | 阶段1 产品探索 |
| `investigate` | `~/.claude/skills/gstack/investigate/` | 全程 调试 |
| `review` | `~/.claude/skills/gstack/review/` | 阶段5 代码审查 |
| `qa` | `~/.claude/skills/gstack/qa/` | 阶段6 QA |
| `qa-only` | `~/.claude/skills/gstack/qa-only/` | 阶段6 只报告 |
| `browse` | `~/.claude/skills/gstack/browse/` | 阶段6 QA |
| `ship` | `~/.claude/skills/gstack/ship/` | 阶段7 发布 |
| `health` | `~/.claude/skills/gstack/health/` | 代码质量 |
| `retro` | `~/.claude/skills/gstack/retro/` | 周度回顾 |
| `plan-ceo-review` | `~/.claude/skills/gstack/plan-ceo-review/` | 阶段1+ CEO评审 |
| `plan-design-review` | `~/.claude/skills/gstack/plan-design-review/` | 阶段1+ 设计评审 |
| `plan-eng-review` | `~/.claude/skills/gstack/plan-eng-review/` | 阶段3 计划评审 |
| `plan-devex-review` | `~/.claude/skills/gstack/plan-devex-review/` | 阶段3 DX评审 |
| `plan-tune` | `~/.claude/skills/gstack/plan-tune/` | 计划调优 |
| `autoplan` | `~/.claude/skills/gstack/autoplan/` | 自动评审流水线 |
| `benchmark` | `~/.claude/skills/gstack/benchmark/` | 性能基准 |
| `benchmark-models` | `~/.claude/skills/gstack/benchmark-models/` | 模型对比 |
| `canary` | `~/.claude/skills/gstack/canary/` | 发布监控 |
| `careful` | `~/.claude/skills/gstack/careful/` | 危险操作警告 |
| `codex` | `~/.claude/skills/gstack/codex/` | Codex CLI 封装 |
| `connect-chrome` | `~/.claude/skills/gstack/connect-chrome/` | Chrome 连接 |
| `context-save` | `~/.claude/skills/gstack/context-save/` | 上下文保存 |
| `context-restore` | `~/.claude/skills/gstack/context-restore/` | 上下文恢复 |
| `cso` | `~/.claude/skills/gstack/cso/` | 安全审计 |
| `design-consultation` | `~/.claude/skills/gstack/design-consultation/` | 设计咨询 |
| `design-html` | `~/.claude/skills/gstack/design-html/` | HTML 设计 |
| `design-review` | `~/.claude/skills/gstack/design-review/` | 设计 QA |
| `design-shotgun` | `~/.claude/skills/gstack/design-shotgun/` | 设计变体 |
| `devex-review` | `~/.claude/skills/gstack/devex-review/` | DX 审计 |
| `document-release` | `~/.claude/skills/gstack/document-release/` | 文档更新 |
| `freeze` | `~/.claude/skills/gstack/freeze/` | 编辑范围锁定 |
| `unfreeze` | `~/.claude/skills/gstack/unfreeze/` | 解除锁定 |
| `guard` | `~/.claude/skills/gstack/guard/` | 安全守卫 |
| `land-and-deploy` | `~/.claude/skills/gstack/land-and-deploy/` | 合并+部署 |
| `landing-report` | `~/.claude/skills/gstack/landing-report/` | 发布队列 |
| `learn` | `~/.claude/skills/gstack/learn/` | 经验管理 |
| `make-pdf` | `~/.claude/skills/gstack/make-pdf/` | PDF 生成 |
| `pair-agent` | `~/.claude/skills/gstack/pair-agent/` | 远程 Agent 配对 |
| `setup-deploy` | `~/.claude/skills/gstack/setup-deploy/` | 部署配置 |
| `setup-browser-cookies` | `~/.claude/skills/gstack/setup-browser-cookies/` | Cookie 导入 |
| `setup-gbrain` | `~/.claude/skills/gstack/setup-gbrain/` | gbrain 配置 |
| `gstack-upgrade` | `~/.claude/skills/gstack/gstack-upgrade/` | gstack 升级 |
| `open-gstack-browser` | `~/.claude/skills/gstack/open-gstack-browser/` | GStack 浏览器启动 |

### Superpowers Skills（插件缓存 v5.0.7）

| Skill 名称 | 调用方式 | 阶段 |
|------------|---------|------|
| `writing-plans` | `superpowers:writing-plans` | 阶段2 计划拆解 |
| `executing-plans` | `superpowers:executing-plans` | 阶段4 执行 |
| `dispatching-parallel-agents` | `superpowers:dispatching-parallel-agents` | 阶段4 并行 |
| `test-driven-development` | `superpowers:test-driven-development` | 阶段4 TDD |
| `systematic-debugging` | `superpowers:systematic-debugging` | 全程调试 |
| `verification-before-completion` | `superpowers:verification-before-completion` | 阶段7 验证 |
| `requesting-code-review` | `superpowers:requesting-code-review` | 阶段5 审查 |
| `receiving-code-review` | `superpowers:receiving-code-review` | 阶段5 接收审查 |
| `finishing-a-development-branch` | `superpowers:finishing-a-development-branch` | 阶段7 分支 |
| `using-git-worktrees` | `superpowers:using-git-worktrees` | 阶段4 隔离 |
| `brainstorming` | `superpowers:brainstorming` | 阶段1 头脑风暴 |
| `writing-skills` | `superpowers:writing-skills` | 元技能 |

### 本地 Skills

| Skill 名称 | 路径 | 用途 |
|------------|-----|------|
| `consensus-debate` | `~/.claude/skills/consensus-debate/` | 多模型博弈评审 |

### 插件 Skills（已启用，5 个）

| 插件 | 版本 | Skills | 用途 |
|------|------|--------|------|
| `superpowers` | v5.0.7 | writing-plans, executing-plans, dispatching-parallel-agents, test-driven-development, systematic-debugging, verification-before-completion, requesting-code-review, receiving-code-review, finishing-a-development-branch, using-git-worktrees, brainstorming, writing-skills | 工作流编排 |
| `ui-ux-pro-max` | v2.5.0 | ui-ux-pro-max, design, banner-design, ui-styling, brand, slides, design-system | UI/UX 设计 |
| `document-skills` | - | pdf, xlsx, docx, pptx, claude-api, mcp-builder, skill-creator, frontend-design, web-artifacts-builder, webapp-testing, canvas-design, brand-guidelines, doc-coauthoring, slack-gif-creator, internal-comms, algorithmic-art, theme-factory | 文档/API |
| `feature-dev` | v1.0.0 | feature-dev | 功能开发 |
| `code-simplifier` | v1.0.0 | code-simplifier | 代码精简 |

### 其他已注册插件（未启用，通过 context7 MCP 服务提供）

| 插件 | 服务方式 | 用途 |
|------|---------|------|
| `context7` | MCP Server（resolve-library-id, query-docs） | 库文档实时查询 |

---

## 六、使用方式

### 6.1 环境准备（首次）

```bash
# 1. 从本地仓库构建并 link（包含自定义改动）
cd /path/to/Trellis
pnpm build && npm link

# 2. 在目标项目中初始化（生成 .trellis/ 结构 + 平台配置）
cd your-project
trellis init --claude --all -u yourname
# --all 会自动创建 .claude-approve（启用 auto-approve）+ 安装 hooks + 配置增强

# 3. 启动 Claude Code
claude
```

> **注意**: `npm install -g @mindfoldhq/trellis@latest` 安装的是原版 v0.4.0，不包含本仓库的自定义改动（task_sync、import-plan/sync-status 等）。必须用 `npm link` 从本地安装。

### 6.2 日常工作流（7 阶段）

直接用自然语言描述需求，Harness 会自动路由到对应 Skill。也可以显式调用：

| 你想做什么 | 在 Claude Code 中输入 | 触发的 Skill |
|-----------|----------------------|-------------|
| 探索产品想法 | `"帮我 brainstorm 这个功能"` 或 `/office-hours` | `office-hours` |
| 写实施计划 | `"为这个功能写个实施方案"` | `superpowers:writing-plans` |
| 评审计划 | `"评审这个计划"` 或 `/plan-eng-review` | `plan-eng-review` |
| 多模型评审 | `/consensus-debate` | `consensus-debate` |
| 开始开发 | `"按计划执行"` | `superpowers:executing-plans` |
| 并行开发多个任务 | `"并行开发这三个功能"` | `superpowers:dispatching-parallel-agents` |
| 调试 Bug | `"这个报错了，帮我查"` 或 `/investigate` | `investigate` |
| 代码审查 | `"review 我的改动"` 或 `/review` | `review` |
| QA 测试 | `/qa` | `qa` |
| 浏览器测试 | `/browse https://localhost:3000` | `browse` |
| 发布/创建 PR | `/ship` | `ship` |
| 代码质量检查 | `/health` | `health` |
| 周度回顾 | `/retro` | `retro` |

### 6.3 GitNexus 代码智能

GitNexus 通过 MCP 工具调用工作，由 AI agent 自动执行（非用户手动输入的 CLI 命令）：

```
# 改代码前 — 查爆炸半径
> gitnexus_impact({target: "functionName", direction: "upstream"})

# 改代码后 — 确认影响范围
> gitnexus_detect_changes({scope: "staged"})

# 搜索执行流
> gitnexus_query({query: "用户认证流程"})

# 查看符号完整上下文
> gitnexus_context({name: "validateUser"})

# API 兼容检查
> gitnexus_shape_check({route: "/api/users"})
```

### 6.4 验证循环（铁律）

**改代码 → 跑测试 → 读输出 → 修复 → 再跑 → 通过才交付**

```bash
pnpm test && pnpm build    # 后端验证
pnpm dev                   # 前端联调
```

前后端功能必须通过前端走完整测试流程：
- 后端接口地址 vs 前端接口地址是否一致
- 参数名/参数类型是否匹配

### 6.5 自动触发的 Hooks（无需手动）

| 时机 | 自动行为 |
|------|---------|
| 输入 Prompt 时 | lesson-search 自动匹配历史经验注入上下文 |
| 搜索代码时 | GitNexus 自动注入图谱上下文增强搜索 |
| 编辑文件时 | auto-approve 自动授权 + harness 知识库提醒 |
| git commit 时 | consensus-debate 自动触发多模型 review |
| 会话结束时 | 检测到计划意图时提示进行评审 |
| subagent 结束时 | lesson-capture 自动沉淀经验 |

### 6.6 Context 管理

```
/context   # 查看 token 使用量
/compact   # 接近上下文上限时压缩
/clear     # 开始新任务时清空
```

大任务用 Plan Mode（Shift+Tab）拆阶段，每阶段用 `/trellis:record-session` 保存 checkpoint。

### 6.7 典型场景示例

**场景 A：新功能开发（完整流程）**
```
1. 用户: "我想加一个用户认证功能"
   → /office-hours → YC 式追问澄清需求

2. 用户: "需求明确了，写实施方案"
   → /superpowers:writing-plans → 拆解计划 + GitNexus impact

3. 用户: "评审这个计划"
   → /plan-eng-review → 工程经理视角评分
   → /consensus-debate → 多模型博弈评审（可选）

4. 用户: "按计划执行"
   → /superpowers:executing-plans → TDD 执行

5. 用户: "review 一下"
   → /review → 代码审查 + API 兼容检查

6. 用户: "QA 测试"
   → /qa → 系统化测试 + 修复

7. 用户: "发布"
   → /ship → 测试→审查→CHANGELOG→PR
```

**场景 B：紧急 Bug 修复**
```
1. 用户: "线上报错了，/path/to/project/error.log"
   → /investigate → 根因调试 + GitNexus 定位

2. 修复后:
   → gitnexus_detect_changes → 确认影响范围

3. 用户: "review 并发布"
   → /review → /ship
```

**场景 C：并行开发**
```
1. 用户: "这三个功能并行开发"
   → /superpowers:dispatching-parallel-agents
   → 每个功能独立 worktree + subagent
   → 各自 TDD 循环
   → 完成后各自 gitnexus_detect_changes
   → 经验自动沉淀到 .harness/lessons/
```

---

## 七、修复记录

| # | 问题 | 修复 | 影响文件 |
|---|------|------|---------|
| 1 | Stop 钩子提示 `/review-plan` 不存在 | 改为 `/consensus-debate` | `settings.json` |
| 2 | harness-hook.cjs 未注册 | 添加到 PreToolUse(Edit\|Write\|Patch) 匹配器 | `settings.json` |
| 3 | CLAUDE.md 用 `/trellis:xxx` 格式无法映射 | 改为 `Skill("actual-name")` 格式 | `CLAUDE.md` |
| 4 | 阶段3 语义混淆（code-review vs plan review） | 阶段3 → `plan-eng-review`，阶段5 → `review` | `CLAUDE.md` |
| 5 | 路由表缺少 gstack↔superpowers 映射 | 补全映射表 + 扩展路由至 18 项 | `CLAUDE.md` |
| 6 | `.claude-approve` 缺失导致 auto-approve 不生效 | `configureGitnexus` 自动创建 `.claude-approve` | `enhancements.ts`, `readme_harness.md` |
| 7 | 6.3 节 GitNexus CLI 命令格式虚构 | 改为 MCP 工具调用格式（`gitnexus_impact(...)`） | `readme_harness.md` |
| 8 | gstack 技能数量错误（39→43）+ 缺少 `open-gstack-browser` | 更新数量 + 补充缺失技能 | `readme_harness.md` |
| 9 | `consensus-debate` 标注为插件但实际是本地 skill | 移至"本地 Skills"分类 | `readme_harness.md` |
| 10 | 插件表列出 `ralph-wiggum`、`code-review` 但未启用 | 移除未启用插件，保留已启用的 5 个 | `readme_harness.md` |
| 11 | 阶段7 流程图 `git commit + push` 混为一行 | 拆分为独立的 `git commit` + `git push` | `readme_harness.md` |
| 12 | `consensus-debate` models.json endpoint 缺少路径 | 添加 `/v1/chat/completions` 路径 | `models.json` |
| 13 | `run_debate.py` openai 协议缺少 `max_tokens` | 添加 `max_tokens: 16384` | `run_debate.py` |
