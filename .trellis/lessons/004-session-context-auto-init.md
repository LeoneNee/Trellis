# Lesson: Session Context Auto-Initialization

**Context**: Developer onboarding blocked by ERROR when `.trellis/.developer` is missing.
**Discovery**: `session_context.py` hard-failed with ERROR, preventing full context injection. Fixed by auto-initializing from `git config user.name` when available.
**Why it matters**: New team members clone the repo and immediately see ERROR — bad first impression. Auto-init removes friction while still warning.
**Related**: `.trellis/scripts/common/session_context.py:213-240`
