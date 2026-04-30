<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

Use the `/trellis:start` command when starting a new session to:
- Initialize your developer identity
- Understand current project context
- Read relevant guidelines

Use `@/.trellis/` to learn:
- Development workflow (`workflow.md`)
- Project structure guidelines (`structure/`)
- Session traces (`agent-traces/`)

If you're using Codex, project-scoped helpers may also live in:
- `.agents/skills/` for reusable Trellis skills
- `.codex/agents/` for optional custom subagents

Keep this managed block so 'trellis update' can refresh the instructions.

<!-- TRELLIS:END -->

<!-- GitNexus Quick Reference (Codex-compatible) -->
- MUST run `gitnexus_impact` before editing any symbol
- MUST run `gitnexus_detect_changes` before committing
- NEVER ignore HIGH/CRITICAL risk warnings
- Full guide and tools reference: see CLAUDE.md
