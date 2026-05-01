---
name: multi-review
description: |
  Multi-agent code review using Codex CLI and Kimi CLI.
  Each agent can execute code to verify findings, eliminating false positives
  that plague API-only text analysis.
  Triggers on: "multi-review", "review this change", "review commit", "P0 check".
---

# Multi-Agent Code Review

Runs parallel code reviews using Codex CLI and Kimi CLI.
Each reviewer can **execute code** to verify findings — unlike API-only models.

## Prerequisites

- `codex` CLI installed and authenticated
- `kimi` CLI installed and authenticated
- Configuration: `.claude/skills/multi-review/scripts/config.json`

## Workflow

1. **Confirm parameters** (or extract from context):
   - `diff` (required): code changes to review
   - `focus` (optional): "security", "correctness", "performance", "all" (default: "all")

2. **Gather diff**: use `git diff` for uncommitted changes or `git diff --cached` for staged

3. **Run review engine**:
   ```bash
   python3 <skill-path>/scripts/review_engine.py \
     --diff "<diff content>" \
     --focus all \
     --output json
   ```

4. **Parse result**: JSON output with fields:
   - `confirmed_issues`: issues confirmed by 2+ reviewers (high confidence)
   - `unverified_issues`: issues reported by only 1 reviewer (lower confidence)
   - `reviewers`: list of participating reviewer agents
   - `review_details`: per-reviewer raw output

5. **Present results**:
   - Show confirmed issues prominently with severity and source
   - Note unverified as warnings
   - If no issues: confirm clean review

6. **Persistence (optional)**: ask user if they want to save to `docs/multi-review/`

## Key Design Principles

- **Code execution > text analysis**: Reviewers run actual code to verify claims
- **Cross-validation**: Only issues confirmed by multiple reviewers are reported as blocking
- **Graceful degradation**: If a reviewer CLI is missing or times out, proceed with available reviewers
- **No false positives by design**: Single-reporter issues are downgraded to warnings

## Error Handling

- If no reviewer CLIs are available: skip review, do not block
- If a reviewer times out (25s): skip that reviewer, proceed with others
- If config.json is missing: skip review
