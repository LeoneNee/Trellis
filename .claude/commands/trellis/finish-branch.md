---
description: Finish development branch - merge, PR, or cleanup
allowed-tools: "Skill, Read, Edit, Bash"
---
Complete development work: decide merge strategy, create PR, or cleanup.

## Step 1: Pre-Flight Trellis Check

```bash
python3 .trellis/scripts/task.py list
```

Read the current task's `task.json`. Verify:
- `current_phase` is 4 — confirms execution and verification are done. If lower, warn:
  > "Task has not completed execution and verification. Run `/trellis:verify-completion` first."
- `status` is `review` — confirms verification passed. If `in_progress`, warn that work may not be complete.
- `plan_path` exists — confirms a plan was written and tracked
- `branch` — the feature branch name
- `worktree_path` — the isolated worktree location

If no current task is set, warn:
> "No Trellis task is currently active. Branch finalization will proceed without task tracking."

## Step 2: Invoke Finishing Skill

Use the Skill tool to invoke: `superpowers:finishing-a-development-branch`

This skill will:
1. Verify tests pass on the feature branch
2. Present options: merge to base, create PR, keep branch, or discard
3. Execute the chosen path

## Step 3: Cleanup Worktree

After the skill completes successfully:

If a worktree was created (check `worktree_path` in task.json):
```bash
# Remove the worktree
git worktree remove <worktree-path>
```

Verify cleanup:
```bash
git worktree list
```

## Step 4: Post-Completion Trellis Sync

### If PR was created:
Update task.json via Edit:
- `"status": "review"` — stays in review until PR is merged
- `"notes"` — append: `"PR created: <url>"`
- Set `pr_url` if available

Then clear current task:
```bash
python3 .trellis/scripts/task.py finish
```

### If branch was merged:
Update task.json via Edit:
- `"status": "completed"`
- `"completedAt": "<today's date YYYY-MM-DD>"`
- `"notes"` — append: `"Branch merged successfully."`

Then finish and archive:
```bash
python3 .trellis/scripts/task.py finish
python3 .trellis/scripts/task.py archive <task-name>
```
This triggers `after_finish` + `after_archive` hooks (e.g., Linear sync to "Done").

## Error Handling

If the finishing skill fails or the user aborts:
- Do NOT update task.json status
- Leave the task as `in_progress` or `review`
- Append to `notes`: `"Finish attempted but not completed: <reason>"`
- Do NOT remove the worktree — leave it for retry
