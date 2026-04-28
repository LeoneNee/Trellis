---
description: Write an implementation plan using Superpowers structured planning workflow
allowed-tools: "Skill, Read, Glob, Grep, Bash, Write, Edit"
---
Write a structured implementation plan with clear steps, dependencies, and verification criteria.

## Step 1: Load Trellis Task Context

Before invoking the planning skill, load context from the current Trellis task.

Run:
```bash
python3 .trellis/scripts/task.py list
```

If there is a current task (`<- current` marker), read its `task.json` to gather context:
```bash
cat .trellis/.current-task
```
Then read the task.json at that path. Extract:
- `title` and `description` — feed into the plan's Goal section
- `dev_type` — informs tech stack decisions
- `package` — scope file paths if monorepo
- `design_path` — the design spec from office-hours (if brainstorm was run)
- `assignee` — for context

If NO current task is set, warn the user:
> "No Trellis task is currently active. Use `python3 .trellis/scripts/task.py start <dir>` first, or proceed without Trellis integration."

## Step 2: Invoke Planning Skill

Use the Skill tool to invoke: `superpowers:writing-plans`

The skill will guide you through creating a comprehensive plan with bite-sized tasks following TDD principles.

## Step 3: Update Trellis Task After Plan is Saved

After the plan file is written (to `docs/superpowers/plans/YYYY-MM-DD-<name>.md` or user-specified location), sync the Trellis task.

Read the current task path from `.trellis/.current-task`, then update its `task.json`:

```bash
# Get current task dir
TASK_DIR=$(cat .trellis/.current-task)
```

Use the Edit tool to update the task.json with these fields:
- `"current_phase": 2` — planning/research complete
- `"status": "in_progress"` — actively working
- `"notes"` — append: `"Implementation plan saved to docs/superpowers/plans/..."`

If the plan path is known, also set a custom field:
- `"plan_path": "docs/superpowers/plans/YYYY-MM-DD-<name>.md"`

This ensures `task.py list` shows the task as `in_progress`, and any downstream tools can locate the plan file.

## Step 4: Offer Execution Options

Follow the superpowers:writing-plans skill's handoff — offer the user Subagent-Driven or Inline Execution.
