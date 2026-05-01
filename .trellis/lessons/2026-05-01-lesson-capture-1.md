# 确认了 Kimi 发现的一个问题：`review_wrapper

## Basic Info
- Date: 2026-05-01
- Module: .claude
- Problem Type: Bug Fix
- Tags: python
- Related Files:
  - .claude/hooks/lesson-capture.py
  - .claude/hooks/lesson-search.py

## Symptom
触发原因: keywords=['\\bbug\\b']

## Root Cause
确认了 Kimi 发现的一个问题：`review_wrapper.py` 的 `main()` 没有 `argparse`，`--message` 被传入但被忽略。现在完整汇总审核结果。

## Solution
```diff
+    for _ in range(8):
+        parent = current.parent
+        if parent == current:
+            break
+        current = parent
+        raw = sys.stdin.read(1_000_000)  # limit to 1MB
+        if not raw:
+            sys.exit(0)
+        input_data = json.loads(raw)
```

## 关键修复点
确认了 Kimi 发现的一个问题：`review_wrapper.py` 的 `main()` 没有 `argparse`，`--message` 被传入但被忽略。现在完整汇总审核结果。

---

## 审核汇总报告

### 审核方式

使用 Codex CLI (gpt-5.5) 和 Kimi CLI 分别独立审核，然后交叉对比。

---

### 确认存在的问题

#### P0 — 大 diff 通过 CLI 参数传递会触发系统限制

- **文件**: `.claude/skills/multi-review/scripts/review_wrapper.py:51-54`, `.claude/skills/multi-review/scripts/review_engine.py:95-100`
- **Codex**: 确认 P1
- **Kimi**: 确认 P0
- **结论**: **确认存在（P0）**。`review_wrapper.py` 将 diff_content 作为 `--diff` 参数传给子进程，`review_engine.py` 又将包含 
...

## Reusable Lesson
_待人工补充_

## Search Keywords
- lesson
- capture
- search
- range
- read
- exit
- loads
- review_wrapper.py
- main()
- argparse
- --message
- --diff
