---
description: Pre-landing code review with scope drift and slop detection
allowed-tools: "Skill, Read, Bash, Glob, Grep"
---
Analyze diff for SQL safety, LLM trust boundary violations, conditional side effects, and other structural issues.

## Step 1: Load Trellis Task Context (Optional)

Run:
```bash
python3 .trellis/scripts/task.py list
```

If there is a current task, read its `task.json` for context on what's being reviewed:
- `title` and `description` — scope of the review
- `package` — monorepo package scope

## Step 2: Invoke Review Skill

Use the Skill tool to invoke: `review`
