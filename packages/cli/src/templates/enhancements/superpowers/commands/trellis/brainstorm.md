---
description: Explore requirements and design before implementation (YC Office Hours)
allowed-tools: "Skill, Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion, WebSearch"
---
Explore user intent, requirements, and design before writing any code.

## Step 1: Load Trellis Task Context

Before starting, load context from the current Trellis task.

```bash
python3 .trellis/scripts/task.py list
```

If there is a current task (`<- current` marker), read its `task.json` to gather context:
```bash
cat .trellis/.current-task
```
Then read the task.json at that path. Extract:
- `title` and `description` — the feature/product to explore
- `package` — scope if monorepo
- `assignee` — for context

If NO current task is set, warn the user:
> "No Trellis task is currently active. Use `python3 .trellis/scripts/task.py start <dir>` first, or proceed without Trellis integration."

## Step 2: Invoke Office Hours Skill

Use the Skill tool to invoke: `office-hours`

This runs YC-style product exploration:
- **Startup mode** — six forcing questions (demand reality, status quo, desperate specificity, narrowest wedge, observation, future-fit)
- **Builder mode** — design thinking brainstorming for side projects, hackathons, learning

The skill produces a **design doc** (not code), saved to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`.

**IMPORTANT:** Do NOT invoke any implementation skill. office-hours produces design docs only.

## Step 3: Update Trellis Task After Design Doc is Saved

After the design doc is written and approved by the user, sync the Trellis task.

Read the current task path from `.trellis/.current-task`, then use the Edit tool to update task.json:
- `"current_phase": 1` — brainstorm complete
- `"status": "in_progress"` — actively working
- `"notes"` — append: `"Design doc saved to docs/superpowers/specs/..."`

If the design doc path is known, also set:
- `"design_path": "docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md"`

This ensures downstream commands (write-plan) can locate the design spec.

## Step 4: Offer Next Steps

After the design doc is approved, offer the user:

1. **Plan review** — `/plan-eng-review` or `/consensus-debate` to review the design
2. **Write implementation plan** — `/trellis:write-plan` to create the execution plan

Follow the user's choice.
