# All 3 inline shell hook commands that use `SESSION_ID` are s

## Basic Info
- Date: 2026-04-30
- Module: packages/cli
- Problem Type: Bug Fix
- Tags: python
- Related Files:
  - packages/cli/src/templates/claude/hooks/lesson-capture.py
  - packages/cli/src/templates/enhancements/consensus-debate/scripts/review_wrapper.py

## Symptom
触发原因: keywords=['\\bfix(ed|es|ing)?\\b']

## Root Cause
**1. settings.json -- SESSION_ID sanitization with `tr -cd 'a-zA-Z0-9_-'`**

## Solution
```diff
+            ["git", "diff", "HEAD", "--stat", "-p", "--", "*.py", "*.ts", "*.tsx", "*.js", "*.jsx",
+        local_models = SKILL_DIR / "models.json"
+        if local_models.exists():
+            raw = local_models.read_text(encoding="utf-8")
+            try:
+                configs = json.loads(raw)
+                has_valid_key = any(c.get("api_key", "").strip() for c in configs if isinstance(c, 
+                if not has_valid_key:
+                    prin
```

## 关键修复点
## Final Round 3 Audit -- Verdict

### Verification Checklist

**1. settings.json -- SESSION_ID sanitization with `tr -cd 'a-zA-Z0-9_-'`**

All 3 inline shell hook commands that use `SESSION_ID` are sanitized:
- Line 115 (PostToolUse/Write): `SESSION_ID=$(echo "${CLAUDE_SESSION_ID:-default}" | tr -cd 'a-zA-Z0-9_-')`
- Line 143 (UserPromptSubmit): identical sanitization pattern
- Line 153 (Stop): identical sanitization pattern

CONFIRMED: Every inline `SESSION_ID` use is sanitized. No raw `${CLAU
...

## Reusable Lesson
_待人工补充_

## Search Keywords
- lesson
- capture
- review
- wrapper
- exists
- loads
- strip
- isinstance
- tr -cd 'a-za-z0-9_-'
- session_id
- ${claude_session_id}
- diff_content=$(git diff --cached ...)
