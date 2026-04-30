---
description: Execute an existing implementation plan with checkpoints (inline, non-subagent)
allowed-tools: "Skill, Read, Write, Edit, Bash, Glob, Grep"
---
Execute an implementation plan step-by-step with review checkpoints (inline mode).

Use this when subagent-driven development is not available (no Agent tool).
Otherwise prefer `/trellis:subagent-dispatch` for per-task isolation + two-stage review.

## Step 1: Ensure Trellis Task is Active

```bash
python3 .trellis/scripts/task.py list
```

Check for a current task. If not set, look for a task with a `plan_path`:
```bash
python3 .trellis/scripts/task.py start <task-dir>
```

Read task.json. Look for `plan_path` to locate the plan file.

If no task exists, warn the user but continue.

## Step 2: Set Up Isolated Worktree

Before executing, create an isolated workspace.

Use the Skill tool to invoke: `superpowers:using-git-worktrees`

After it completes:
1. Record the worktree path and branch name
2. Update task.json via Edit:
   - `"worktree_path": "<worktree-path>"`
   - `"branch": "<branch-name>"`

```bash
python3 .trellis/scripts/task.py set-branch <task-dir> <branch-name>
```

If the task status is still `planning`, transition it:
```bash
python3 .trellis/scripts/task.py start <task-dir>
```

Update task.json:
- `"status": "in_progress"`
- `"current_phase": 3` — implementation phase

## Step 3: Invoke Execution Skill

Use the Skill tool to invoke: `superpowers:executing-plans`

The skill will process the plan task-by-task with verification at each step.

## Step 4: Track Progress in Trellis Task

During execution, after each plan Task N is completed (all checkboxes done, verified):

Read the current task.json, then use Edit to update:
- `"notes"` — append: `"Task N completed."`

This creates a breadcrumb trail in the Trellis task that survives session restarts.

## Step 5: Post-Execution Trellis Update

After ALL plan tasks are complete and verified:

Update task.json via Edit:
- `"current_phase": 4` — check/review phase
- `"status": "review"`
- `"notes"` — append: `"All tasks completed. Ready for verification."`

Do NOT call `task.py finish` yet — that should happen after verification (`verify-completion`) and branch finalization (`finish-branch`).

## Error Handling

If execution is blocked or fails:
- Update task.json `"notes"` with the blocker description
- Leave status as `in_progress`
- Do NOT advance `current_phase`
