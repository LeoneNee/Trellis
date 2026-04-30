---
description: Ship workflow - test, review, changelog, commit, push, create PR
allowed-tools: "Skill, Read, Write, Edit, Bash, Glob, Grep"
---
Complete ship workflow: detect base branch, run tests, review diff, bump version, update changelog, commit, push, create PR.

## Step 1: Pre-Flight Trellis Check

Run:
```bash
python3 .trellis/scripts/task.py list
```

If there is a current task, read its `task.json`. Verify:
- `current_phase` is 4 — confirms execution and verification are done. If lower, warn:
  > "Task has not completed verification. Run `/trellis:verify-completion` first."
- `status` is `review` — confirms work is ready to ship

If no current task is set, proceed without task tracking.

## Step 2: Invoke Ship Skill

Use the Skill tool to invoke: `ship`

## Step 3: Post-Ship Trellis Sync

After the ship skill completes:

If a current task exists and a PR was created:

Update task.json via Edit:
- `"status": "review"` — stays in review until PR is merged
- `"notes"` — append: `"Shipped: PR created."`

Then finish the task:
```bash
python3 .trellis/scripts/task.py finish
```

If the PR was merged instead of just created:
- `"status": "completed"`
- `"completedAt": "<today's date YYYY-MM-DD>"`
- `"notes"` — append: `"Shipped and merged."`
- Then finish and archive:
```bash
python3 .trellis/scripts/task.py finish
python3 .trellis/scripts/task.py archive <task-name>
```
