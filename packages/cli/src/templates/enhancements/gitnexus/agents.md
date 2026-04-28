<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

Use the `/trellis:start` command when starting a new session to:
- Initialize your developer identity
- Understand current project context
- Read relevant guidelines

Use `@/.trellis/` to learn:
- Development workflow (`workflow.md`)
- Project structure guidelines (`spec/`)
- Developer workspace (`workspace/`)

If you're using Codex, project-scoped helpers may also live in:
- `.agents/skills/` for reusable Trellis skills
- `.codex/agents/` for optional custom subagents

Keep this managed block so 'trellis update' can refresh the instructions.

---

## Core Principles

1. **Think Before Coding** — Don't assume, surface concerns and trade-offs
2. **Simplicity First** — Minimal code, no speculative complexity
3. **Surgical Changes** — Precise changes, only touch what must change
4. **Goal-Driven Execution** — Define verifiable success criteria

---

## 7-Stage Workflow

```
Stage 1 → /trellis:brainstorm          Product exploration (YC Office Hours)
Stage 2 → /trellis:write-plan           Plan decomposition + GitNexus impact
Stage 3 → /plan-eng-review              Plan review (eng manager perspective)
Stage 4 → /trellis:subagent-dispatch    TDD execution + GitNexus change detection
Stage 5 → /review                        Code review + GitNexus API compat check
Stage 6 → /qa or /browse                QA testing (headless browser)
Stage 7 → /ship                          Ship (test → review → CHANGELOG → PR)
```

Always available:
- `/investigate` — root cause debugging + GitNexus tracing
- `/consensus-debate` — multi-model debate review
- `/trellis:debug-systematic` — systematic debugging

---

## Skill Routing

**When matching requests, invoke the corresponding Skill tool as the FIRST action.**

| Request | Skill | Source |
|---------|-------|--------|
| Product ideas / brainstorm | `office-hours` | gstack |
| Write implementation plan | `superpowers:writing-plans` | Superpowers |
| Execute plan | `superpowers:executing-plans` | Superpowers |
| Parallel development | `superpowers:dispatching-parallel-agents` | Superpowers |
| Bugs / errors | `investigate` | gstack |
| Code review | `review` | gstack |
| QA / find bugs | `qa` or `browse` | gstack |
| Deploy / push / PR | `ship` | gstack |
| TDD | `superpowers:test-driven-development` | Superpowers |
| Plan review / arch review | `plan-eng-review` | gstack |
| Multi-model debate | `consensus-debate` | local |
| Code quality | `health` | gstack |
| Weekly retrospective | `retro` | gstack |
| Verify before delivery | `superpowers:verification-before-completion` | Superpowers |
| Finish branch | `superpowers:finishing-a-development-branch` | Superpowers |
| Systematic debugging | `superpowers:systematic-debugging` | Superpowers |
| Request code review | `superpowers:requesting-code-review` | Superpowers |
| Receive code review | `superpowers:receiving-code-review` | Superpowers |

---

## GitNexus Code Intelligence

**Run impact analysis before editing any symbol.**

| When | Tool | Purpose |
|------|------|---------|
| Before editing | `gitnexus_impact` | Blast radius analysis |
| After editing | `gitnexus_detect_changes` | Confirm affected scope |
| Locating issues | `gitnexus_query` | Search execution flows |
| Understanding symbols | `gitnexus_context` | 360-degree view |
| API changes | `gitnexus_shape_check` | Response compat check |

---

## Verification Loop

**Iron rule: edit code → run tests → read output → fix → re-run → pass before delivery**

```bash
pnpm test && pnpm build    # backend verification
pnpm dev                    # frontend integration test
```

**For fullstack features: test through the frontend end-to-end**
- Backend API address vs frontend API address must match
- Parameter names / types must be consistent
- Often backend tests pass but frontend can't connect

**Never:** Deliver without running tests / Guess without reading output / Test only backend for fullstack features

<!-- TRELLIS:END -->
