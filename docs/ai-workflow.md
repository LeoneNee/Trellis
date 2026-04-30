# AI Workflow Guide

> One-page reference for setting up the AI-assisted development environment for this project.

## Required Tools

| Tool | Purpose | Install |
|------|---------|---------|
| Claude Code | AI assistant IDE | [Install](https://claude.ai/code) |
| GitNexus | Code intelligence (MCP) | `npm install -g gitnexus` |
| pnpm | Package manager | [Install](https://pnpm.io/installation) |
| Node.js | Runtime | v18+ |

## Quick Start

```bash
git clone <repo-url>
cd Trellis
python3 .trellis/scripts/init_developer.py <your-name>
npx gitnexus analyze
pnpm install
```

## Verify Environment

```bash
pnpm test && pnpm build          # Backend verification
./scripts/check-ai-workflow.sh   # Full environment check
```

## 7-Stage Workflow

```
Stage 1 → Skill("office-hours")              Product exploration
Stage 2 → Skill("superpowers:writing-plans")   Plan decomposition
Stage 3 → Skill("plan-eng-review")             Engineering review
Stage 4 → Skill("superpowers:dispatching-parallel-agents")  TDD execution
Stage 5 → Skill("review")                      Code review
Stage 6 → Skill("qa") or Skill("browse")       QA testing
Stage 7 → Skill("ship")                        Ship (PR)
```

## Optional Skills

The following skills enhance the workflow but are not required:

- `review`, `qa`, `ship` — gstack shipping pipeline
- `investigate`, `health` — debugging and quality checks
- `retro`, `plan-ceo-review` — team ceremonies

Install via `~/.claude/skills/` or copy to project-level `.claude/skills/` when a shared standard is needed.
