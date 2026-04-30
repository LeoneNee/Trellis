---
description: Systematically QA test a web application and fix bugs found
allowed-tools: "Skill, Bash, Read, Write, Edit, Glob, Grep"
---
Run systematic QA testing, then iteratively fix bugs found.

## Step 1: Load Trellis Task Context (Optional)

Run:
```bash
python3 .trellis/scripts/task.py list
```

If there is a current task, read its `task.json` for context:
- `title` and `description` — what feature is being tested
- `package` — scope if monorepo

## Step 2: Invoke QA Skill

Use the Skill tool to invoke: `qa`
