# 整合工作流指南

> 本项目集成了 Trellis + Superpowers + gstack + GitNexus 四套工具。

## 工作流阶段

### 阶段 1: 产品探索
- **触发**: `/trellis:office-hours` 或 `/trellis:brainstorm`
- **工具**: gstack office-hours (YC 式追问)
- **知识图谱**: GitNexus `query()` 了解现有架构
- **输出**: 设计文档 → `.trellis/spec/`

### 阶段 2: 规划
- **触发**: `/trellis:write-plan`
- **工具**: Superpowers writing-plans
- **知识图谱**: GitNexus `impact()` 评估变更范围
- **输出**: 实施计划 → `docs/superpowers/plans/`

### 阶段 3: 执行
- **触发**: `/trellis:subagent-dispatch` 或 `/trellis:execute-plan`
- **工具**: Superpowers subagent-driven-development + TDD
- **知识图谱**: GitNexus `detect_changes()` 监控变更影响
- **输出**: 实现代码 + 测试

### 阶段 4: 代码审查
- **触发**: `/trellis:review` 或 `/trellis:code-review`
- **工具**: gstack review + Superpowers code-review
- **知识图谱**: GitNexus `shape_check()` + `route_map()` 检查 API 兼容
- **输出**: 审查报告

### 阶段 5: QA 测试
- **触发**: `/trellis:browse` 或 `/trellis:qa`
- **工具**: gstack browse (无头浏览器) + qa
- **输出**: QA 报告 + Bug 列表

### 阶段 6: 发布
- **触发**: `/trellis:ship`
- **工具**: gstack ship
- **知识图谱**: GitNexus `detect_changes()` 最终确认
- **输出**: PR

## 全程可用的技能

| 命令 | 来源 | 用途 |
|------|------|------|
| `/trellis:investigate` | gstack | 根因调试 |
| `/trellis:tdd` | Superpowers | 测试驱动开发 |
| `/trellis:debug-systematic` | Superpowers | 系统化调试 |
| `/trellis:verify-completion` | Superpowers | 完成验证 |
| `/trellis:health` | gstack | 代码质量仪表板 |
| `/trellis:design-review` | gstack | 视觉设计审查 |
| `/trellis:retro` | gstack | 周度回顾 |

## GitNexus 工具使用

当 GitNexus 已启用 (`.trellis/config.yaml` → `gitnexus.enabled: true`):

- `mcp__gitnexus__query` — 搜索执行流和符号
- `mcp__gitnexus__context` — 符号 360 度视图 (调用者/被调用者)
- `mcp__gitnexus__impact` — 变更影响分析 (爆炸半径)
- `mcp__gitnexus__detect_changes` — 检测未提交变更的影响
- `mcp__gitnexus__shape_check` — API 响应形状检查
- `mcp__gitnexus__route_map` — API 路由映射

## 铁律

1. **改代码 → 跑测试 → 读输出 → 修复 → 再跑 → 通过才交付**
2. **没有根因调查不做修复** (investigate 铁律)
3. **每个 subagent 只做一件事** (superpowers 铁律)
4. **先写测试再写实现** (TDD 铁律)
5. **编辑前查影响范围** (GitNexus 铁律)
6. **前后端功能必须通过前端走完整测试流程**
