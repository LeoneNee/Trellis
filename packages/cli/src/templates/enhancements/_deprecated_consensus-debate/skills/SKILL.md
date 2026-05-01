---
name: consensus-debate
description: |
  运行多模型共识博弈（三阶段：提案→交叉评审→Judge汇总）。
  当用户需要多模型讨论、方案评审、架构决策、代码审查、Debug分析时触发。
  只要用户提到"多个模型讨论一下"、"让几个AI评审这个方案"、"共识"、"debate"、"多 Agent 评审"、"planning/review/arch/debug" 等场景，就使用此技能。
---

# 多模型共识博弈 Skill

## 功能
并发调用多个配置的 AI 模型进行三阶段博弈，输出一份经过交叉评审和 Judge 汇总的最终共识方案。

## 使用场景
- **planning**：技术方案设计、项目规划
- **review**：代码审查、文档评审
- **arch**：架构决策、技术选型
- **debug**：故障分析、根因排查

## 前置要求

模型配置文件 `models.json`，放置在脚本同目录：
```
~/.claude/skills/consensus-debate/scripts/models.json
```

格式为 JSON 数组，至少包含 2 个模型配置，其中恰好 1 个 `role` 为 `judge`，其余为 `participant`。

示例：
```json
[
  {"name":"kimi-k2.5","endpoint":"https://api.moonshot.cn/v1/chat/completions","api_key": "***","model":"moonshot-v1-8k","role":"judge","protocol":"openai"},
  {"name":"minimax-m2.7","endpoint":"https://api.minimax.chat/v1/chat_completion_pro","api_key": "***","model":"MiniMax-Text-01","role":"participant","protocol":"openai"},
  {"name":"glm-5.1","endpoint":"https://open.bigmodel.cn/api/paas/v4/chat/completions","api_key": "***","model":"glm-4-flash","role":"participant","protocol":"openai"}
]
```

- `protocol` 可选 `"openai"` 或 `"anthropic"`，默认 `"openai"`。
- `PROJECT_ROOT` 环境变量可选，用于决定 Markdown 输出目录，默认使用当前工作目录。

## 工作流程

1. **确认参数**：向用户确认（或直接提取）以下参数
   - `task`（必填）：核心任务描述
   - `content`（可选）：相关代码或上下文
   - `scene`（必填）：`planning`、`review`、`arch`、`debug` 之一
   - `review_mode`（可选）：`summarized` 或 `full`，默认 `summarized`

2. **运行脚本**：调用本 Skill 附带的 `scripts/run_debate.py` 脚本：
   ```bash
   python <skill-path>/scripts/run_debate.py \
     --task "任务描述" \
     --content "相关上下文" \
     --scene planning \
     --review-mode summarized
   ```
   脚本会输出 JSON 结果到 stdout。

3. **解析结果**：读取 stdout 中的 JSON，包含以下字段：
   - `final_plan`：Judge 汇总的最终共识方案（Markdown 格式）
   - `models_participated`：成功参与的模型别名列表
   - `models_failed`：调用失败的模型别名列表
   - `model_mapping`：别名到真实模型名的映射（如 `{"minimax-m2.7": "MiniMax-M2.7-highspeed"}`）
   - `proposals`：各模型在提案阶段的输出
   - `reviews`：各模型在评审阶段的输出

4. **结果展示**：
   - 将 `final_plan` 以 Markdown 形式展示给用户
   - 列出参与模型时，使用 `model_mapping` 展示真实模型名（如 `minimax-m2.7 (MiniMax-M2.7-highspeed)`）
   - 简要列出失败模型（如有）
   - 询问用户是否需要查看原始提案和评审意见的详细内容

5. **文件持久化（可选）**：
   - 询问用户是否保存为 Markdown 文件
   - 如需保存，调用 `scripts/save_result.py` 或在当前对话中直接写入 `docs/consensus-debate/{plan,codereview,arch,debug}/YYYYMMDD_HHMM_{scene}.md`

## 输出示例

```markdown
## 最终共识方案

（final_plan 内容）

---
- 参与模型：minimax-m2.7 (MiniMax-M2.7-highspeed), glm-5.1 (glm-5.1), kimi-k2.5 (kimi-k2.5)
- 失败模型：无
```

## 错误处理
- 若 `LOCAL_MODEL_CONFIGS` 未设置：提示用户设置环境变量，并给出配置示例
- 若提案阶段成功模型不足 2 个：告知用户哪些模型失败了，并建议检查网络或配置
- 若 Judge 汇总失败：返回已收集的 proposals 和 reviews，让用户手动参考
