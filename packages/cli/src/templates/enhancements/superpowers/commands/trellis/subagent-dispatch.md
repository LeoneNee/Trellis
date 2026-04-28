---
description: Execute implementation plan with subagent-driven development (per-task isolation + two-stage review)
allowed-tools: "Skill, Read, Write, Edit, Bash, Glob, Grep, Agent"
---
Execute an implementation plan by dispatching fresh subagents per task with spec + quality review.

## Step 1: Verify Trellis Task State

```bash
python3 .trellis/scripts/task.py list
```

If a current task exists, read its `task.json` to get:
- `plan_path` — locate the implementation plan
- `design_path` — locate the design spec (for spec reviewer)
- `status` — should be `in_progress`
- `branch` — check if a branch is already set

If no current task is set, warn the user but proceed.

## Step 2: Set Up Isolated Worktree

Before dispatching subagents, create an isolated workspace.

Use the Skill tool to invoke: `superpowers:using-git-worktrees`

This creates a git worktree with a feature branch. After it completes:

1. Record the worktree path and branch name
2. Update task.json via Edit:
   - `"worktree_path": "<worktree-path>"`
   - `"branch": "<branch-name>"`

```bash
python3 .trellis/scripts/task.py set-branch <task-dir> <branch-name>
```

If the task status is still `planning`, start it:
```bash
python3 .trellis/scripts/task.py start <task-dir>
```

Update task.json:
- `"status": "in_progress"`
- `"current_phase": 3` — implementation phase

## Step 3: Invoke Subagent-Driven Development

Use the Skill tool to invoke: `superpowers:subagent-driven-development`

This skill dispatches a **fresh subagent per plan task** with two-stage review:
1. **Implementer subagent** — implements, tests, commits, self-reviews
2. **Spec reviewer subagent** — confirms code matches the design spec
3. **Code quality reviewer subagent** — checks code quality

Each subagent gets isolated context — no session pollution.

## Step 4: Track Progress in Trellis Task

During execution, after each plan Task N is completed (both reviews passed):

Read the current task.json, then use Edit to update:
- `"notes"` — append: `"Task N: <name> — completed (spec ✓, quality ✓)"`

This creates a breadcrumb trail that survives session restarts.

## Step 5: Post-Execution Trellis Sync

After ALL plan tasks are complete and reviewed:

Update task.json via Edit:
- `"current_phase": 4` — check/review phase
- `"status": "review"`
- `"notes"` — append: `"All tasks completed. Ready for verification."`

Do NOT call `task.py finish` — leave that for `finish-branch`.

### If some tasks failed:
Update task.json:
- `"status": "in_progress"` — stays in progress
- `"notes"` — append with specific failure info:
  ```
  "Tasks completed: [Task 1: auth module, Task 2: API routes]. Tasks failed: [Task 3: payment integration — BLOCKED: timeout waiting for payment API]. Retry: re-run subagent-dispatch after fixing Task 3."
  ```

## Error Handling

If the worktree setup fails:
- Do NOT proceed with subagent dispatch
- Warn the user and suggest manual worktree creation
- Leave task.json status unchanged

If a subagent is BLOCKED:
- Record the blocker in task.json `"notes"`
- Do NOT advance `current_phase`
- Ask the user how to proceed
