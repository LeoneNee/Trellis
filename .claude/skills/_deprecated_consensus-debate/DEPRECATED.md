# DEPRECATED

This skill has been replaced by `multi-review`.

**Why**: consensus-debate used API-only models that cannot execute code,
resulting in a 75% false positive rate (3/4 P0 issues were wrong).

**Migration**: Use `/multi-review` instead, which uses Codex CLI and Kimi CLI
to run code and verify findings.

**Removed**: 2026-04-30
