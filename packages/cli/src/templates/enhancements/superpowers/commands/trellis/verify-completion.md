---
description: Verify work is complete before claiming success
allowed-tools: "Skill, Read, Bash, Glob, Grep, Edit"
---
Run verification commands and confirm output before declaring work done.

## Step 1: Load Trellis Task Context

```bash
python3 .trellis/scripts/task.py list
```

If a current task exists, read its `task.json`. Note:
- `current_phase` — should be 4 (check phase) after execute-plan
- `status` — should be `review`
- `plan_path` — to know what was being implemented
- `branch` — to know which branch to verify

## Step 2: Run Verification in Worktree

If `worktree_path` is set in task.json, tests must run inside the worktree (not the main repo):

```bash
cd <worktree_path> && pnpm test && pnpm build   # or the project's specific commands
```

If no worktree was used, run in the current directory:

```bash
pnpm test && pnpm build
```

Read the output carefully. If tests fail, do NOT proceed — fix first.

## Step 3: Invoke Verification Skill

Use the Skill tool to invoke: `superpowers:verification-before-completion`

This skill enforces "evidence before assertions" — you must confirm output before claiming success.

## Step 4: Update Trellis Task Based on Result

### If verification passes:
The task is ready for branch finalization. Keep as-is:
- `"status": "review"` — stays in review for `finish-branch` to handle
- `"notes"` — append: `"Verification passed. Ready for /trellis:finish-branch."`

Tell the user: "Verification passed. Run `/trellis:finish-branch` to create PR and archive."

### If verification fails:
Update task.json via Edit:
- `"current_phase": 3` — back to implementation phase
- `"status": "in_progress"` — back to work
- `"notes"` — append: `"Verification failed: <summary>. Fix and re-verify."`

Do NOT advance. The user should fix issues and re-run verification.
