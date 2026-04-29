---
description: Systematic debugging with root cause investigation
allowed-tools: "Skill, Read, Write, Edit, Bash, Glob, Grep"
---
Iron law: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.

## Step 1: Load Trellis Task Context

Run:
```bash
python3 .trellis/scripts/task.py list
```

If there is a current task (`<- current` marker), read its `task.json`:
```bash
cat .trellis/.current-task
```

Extract context for debugging:
- `title` and `description` — what feature is being debugged
- `package` — scope if monorepo
- `current_phase` — where in the workflow the bug was found
- `notes` — any prior context from implementation

If NO current task is set, proceed without task context.

## Step 2: Invoke Investigate Skill

Use the Skill tool to invoke: `investigate`

## Step 3: Record Findings in Task (Optional)

After investigation completes, if a current task exists, update task.json:

Read the current task path from `.trellis/.current-task`, then use Edit to append to `notes`:
- `"notes"` — append: `"Investigation: <root cause summary>"`

Do NOT modify `current_phase` — investigation is not a workflow phase transition.
