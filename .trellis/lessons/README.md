# Lessons Knowledge Base

This directory stores project-specific learnings and insights discovered during development.

## Purpose

- Record non-obvious patterns, pitfalls, and architectural decisions
- Capture debugging solutions that took significant time to find
- Document team conventions that aren't in the formal spec

## When to Write a Lesson

- After fixing a tricky bug — record the root cause, not just the fix
- After discovering a project-specific quirk or workaround
- After a significant architectural decision with trade-offs
- When onboarding reveals gaps in existing documentation

## Format

Each lesson is a standalone `.md` file:

```markdown
# Lesson: Short Title

**Context**: What were you working on?
**Discovery**: What did you learn?
**Why it matters**: Why will this save time in the future?
**Related**: Links to relevant code, issues, or docs
```

## Usage

The session-start hook automatically summarizes recent lessons when starting a new session. Search relevant lessons before starting development tasks.
