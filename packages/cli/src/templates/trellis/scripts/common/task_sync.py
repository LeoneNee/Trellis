"""
Plan-to-Trellis task synchronization.

Bridges superpowers writing-plans with the trellis task system:
  - Parse plan markdown files for task blocks
  - Import plan tasks into trellis task directories
  - Sync trellis task status back to plan markdown

Provides:
    _extract_task_blocks  — Parse task sections from plan markdown
    cmd_import_plan       — Create/update trellis tasks from plan
    cmd_sync_status       — Write trellis states back to plan markdown
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from .io import read_json, write_json
from .log import Colors, colored
from .paths import (
    FILE_TASK_JSON,
    generate_task_date_prefix,
    get_developer,
    get_repo_root,
    get_tasks_dir,
)
from .task_store import ensure_tasks_dir
from .tasks import iter_active_tasks


# =============================================================================
# Helpers
# =============================================================================

def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug.

    Lowercase, replace non-alphanumeric/CJK characters with '-',
    collapse consecutive dashes, strip leading/trailing dashes,
    truncate to 60 characters.
    """
    result = text.lower()
    # Keep alphanumeric, CJK unified ideographs (U+4E00-U+9FFF),
    # Hiragana, Katakana, and hyphens
    result = re.sub(r"[^\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff-]", "-", result)
    result = re.sub(r"-+", "-", result)
    result = result.strip("-")
    return result[:60]


def _find_existing_task(
    tasks_dir: Path, plan_file: str, plan_task_index: int
) -> Path | None:
    """Find an existing trellis task matching plan_file + plan_task_index.

    Returns the task directory path if found, None otherwise.
    """
    if not tasks_dir.is_dir():
        return None

    for task_dir in tasks_dir.iterdir():
        if not task_dir.is_dir() or task_dir.name == "archive":
            continue
        task_json = task_dir / FILE_TASK_JSON
        if not task_json.is_file():
            continue
        data = read_json(task_json)
        if not data:
            continue
        meta = data.get("meta", {})
        if (
            meta.get("plan_file") == plan_file
            and meta.get("plan_task_index") == plan_task_index
        ):
            return task_dir

    return None


# =============================================================================
# Plan Markdown Parser
# =============================================================================

# Match: ## Task N: Title  or  ## Task N — Title  (with optional (BLOCKER) tag)
_TASK_HEADER_RE = re.compile(
    r"^##\s+Task\s+(\d+)\s*[:\u2014\-]\s*(.+)$",
    re.MULTILINE,
)


def _extract_task_blocks(content: str) -> list[dict]:
    """Parse task sections from plan markdown content.

    Each task block starts with a ``## Task N: Title`` or ``## Task N — Title``
    header and extends to the next task header or a ``---`` separator line.

    Returns a list of dicts with keys:
        index, title, raw_title, priority, description, files_create,
        files_modify, files_test, step_count, slug, section_start, section_end
    """
    matches = list(_TASK_HEADER_RE.finditer(content))
    if not matches:
        return []

    tasks: list[dict] = []

    for i, match in enumerate(matches):
        task_index = int(match.group(1))
        raw_title = match.group(2).strip()
        section_start = match.start()
        # Section ends at next task header or end of content
        if i + 1 < len(matches):
            section_end = matches[i + 1].start()
        else:
            section_end = len(content)

        section = content[section_start:section_end]

        # --- Priority ---
        # Check for BLOCKER in raw_title or in the first paragraph
        first_lines = section[: min(200, len(section))]
        is_blocker = "BLOCKER" in raw_title.upper() or "BLOCKER" in first_lines.upper()
        priority = "P0" if is_blocker else "P2"

        # Clean title — remove (BLOCKER) tag
        title = re.sub(r"\s*\(BLOCKER\)\s*", " ", raw_title).strip()

        # --- Description ---
        # First paragraph after the header line (non-empty, non-Files, non-code)
        description = ""
        header_end = section.index("\n") + 1  # skip the header line itself
        rest = section[header_end:]
        desc_lines: list[str] = []
        for line in rest.splitlines():
            stripped = line.strip()
            if not stripped:
                if desc_lines:
                    break  # end of first paragraph
                continue
            if stripped.startswith("**Files:**") or stripped.startswith("```"):
                break
            # Skip lines that are just markdown separators
            if stripped == "---":
                break
            desc_lines.append(stripped)
        description = " ".join(desc_lines)

        # --- Files ---
        files_create: list[str] = []
        files_modify: list[str] = []
        files_test: list[str] = []

        # Find the **Files:** block
        files_match = re.search(r"\*\*Files:\*\*\s*\n", section)
        if files_match:
            files_block_start = files_match.end()
            # Collect until blank line or next section
            files_lines: list[str] = []
            for line in section[files_block_start:].splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("```") or stripped.startswith("- ["):
                    break
                # Match lines like: "- Create: `path`" or "- Modify: `path`"
                # or "- Test: `path`" or "- Create: path"
                fm = re.match(r"-\s+(Create|Modify|Test):\s*`?([^`>\n]+)`?", stripped)
                if fm:
                    category = fm.group(1).lower()
                    filepath = fm.group(2).strip()
                    if category == "create":
                        files_create.append(filepath)
                    elif category == "modify":
                        files_modify.append(filepath)
                    elif category == "test":
                        files_test.append(filepath)
                    else:
                        files_lines.append(stripped)
                else:
                    # Might be continuation or other format
                    files_lines.append(stripped)

        # --- Step count ---
        # Count `- [ ]` checkbox lines (but not inside code blocks)
        step_count = 0
        in_code_block = False
        for line in section.splitlines():
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if not in_code_block and re.match(r"^\s*- \[ \]", line):
                step_count += 1

        # --- Slug ---
        slug = _slugify(f"task-{task_index}-{title}")
        if not slug:
            slug = f"task-{task_index}"

        tasks.append({
            "index": task_index,
            "title": title,
            "raw_title": raw_title,
            "priority": priority,
            "description": description,
            "files_create": files_create,
            "files_modify": files_modify,
            "files_test": files_test,
            "step_count": step_count,
            "slug": slug,
            "section_start": section_start,
            "section_end": section_end,
        })

    return tasks


# =============================================================================
# Command: import-plan
# =============================================================================

def cmd_import_plan(args: argparse.Namespace) -> int:
    """Create or update trellis tasks from a plan markdown file.

    For each task block in the plan:
    - If a matching trellis task exists (same plan_file + plan_task_index),
      update title, description, priority, files, step_count (NOT status).
    - If no match, create a new task directory with standard trellis fields.

    Idempotent: re-running updates existing tasks without changing status.
    """
    repo_root = get_repo_root()
    plan_path = Path(args.plan_file)

    # Resolve plan_file relative to repo root
    if not plan_path.is_absolute():
        plan_path = repo_root / plan_path

    if not plan_path.is_file():
        print(colored(f"Error: Plan file not found: {args.plan_file}", Colors.RED), file=sys.stderr)
        return 1

    content = plan_path.read_text(encoding="utf-8")
    plan_tasks = _extract_task_blocks(content)

    if not plan_tasks:
        print(colored("No task blocks found in plan", Colors.YELLOW), file=sys.stderr)
        return 0

    # Store plan_file as repo-relative path for portability
    try:
        plan_file_rel = str(plan_path.relative_to(repo_root))
    except ValueError:
        plan_file_rel = str(plan_path)

    developer = get_developer(repo_root)
    if not developer:
        developer = "unknown"

    tasks_dir = ensure_tasks_dir(repo_root)
    date_prefix = generate_task_date_prefix()
    today = datetime.now().strftime("%Y-%m-%d")

    created = 0
    updated = 0

    for pt in plan_tasks:
        existing_dir = _find_existing_task(tasks_dir, plan_file_rel, pt["index"])

        if existing_dir is not None:
            # --- Update existing task ---
            task_json_path = existing_dir / FILE_TASK_JSON
            data = read_json(task_json_path)
            if not data:
                print(
                    colored(f"Warning: Could not read {task_json_path}, skipping", Colors.YELLOW),
                    file=sys.stderr,
                )
                continue

            data["title"] = pt["title"]
            data["description"] = pt["description"]
            data["priority"] = pt["priority"]
            data["relatedFiles"] = pt["files_create"] + pt["files_modify"]
            data["meta"].update({
                "plan_file": plan_file_rel,
                "plan_task_index": pt["index"],
                "plan_task_title": pt["title"],
                "plan_step_count": pt["step_count"],
                "plan_files_create": pt["files_create"],
                "plan_files_modify": pt["files_modify"],
                "plan_files_test": pt["files_test"],
            })

            write_json(task_json_path, data)
            updated += 1
            print(
                colored(
                    f"  Updated: Task {pt['index']} — {pt['title']} [{pt['priority']}]",
                    Colors.BLUE,
                ),
                file=sys.stderr,
            )
        else:
            # --- Create new task ---
            dir_name = f"{date_prefix}-{pt['slug']}"
            task_dir = tasks_dir / dir_name
            task_json_path = task_dir / FILE_TASK_JSON

            # Avoid collisions
            if task_dir.exists():
                suffix = 2
                while (tasks_dir / f"{dir_name}-{suffix}").exists():
                    suffix += 1
                dir_name = f"{dir_name}-{suffix}"
                task_dir = tasks_dir / dir_name

            task_dir.mkdir(parents=True, exist_ok=True)

            task_data = {
                "id": pt["slug"],
                "name": pt["slug"],
                "title": pt["title"],
                "description": pt["description"],
                "status": "planning",
                "dev_type": None,
                "scope": None,
                "package": None,
                "priority": pt["priority"],
                "creator": developer,
                "assignee": developer,
                "createdAt": today,
                "completedAt": None,
                "branch": None,
                "base_branch": None,
                "worktree_path": None,
                "current_phase": 0,
                "next_action": [],
                "commit": None,
                "pr_url": None,
                "subtasks": [],
                "children": [],
                "parent": None,
                "relatedFiles": pt["files_create"] + pt["files_modify"],
                "notes": "",
                "meta": {
                    "plan_file": plan_file_rel,
                    "plan_task_index": pt["index"],
                    "plan_task_title": pt["title"],
                    "plan_step_count": pt["step_count"],
                    "plan_files_create": pt["files_create"],
                    "plan_files_modify": pt["files_modify"],
                    "plan_files_test": pt["files_test"],
                },
            }

            write_json(task_json_path, task_data)
            created += 1
            print(
                colored(
                    f"  Created: Task {pt['index']} — {pt['title']} [{pt['priority']}] ({dir_name})",
                    Colors.GREEN,
                ),
                file=sys.stderr,
            )

    print("", file=sys.stderr)
    print(
        colored(f"Import complete: {created} created, {updated} updated", Colors.GREEN),
        file=sys.stderr,
    )
    return 0


# =============================================================================
# Command: sync-status
# =============================================================================

def cmd_sync_status(args: argparse.Namespace) -> int:
    """Write trellis task statuses back to the plan markdown file.

    For completed tasks: replace ``- [ ]`` with ``- [x]`` in that task's section.
    For in_progress tasks: add ``<!-- status: in_progress -->`` after the task header.

    Processes tasks in reverse order (by plan_task_index) to avoid offset shifts
    from checkbox replacements. Only modifies checkbox lines, never touches code blocks.
    """
    repo_root = get_repo_root()
    plan_path = Path(args.plan_file)

    if not plan_path.is_absolute():
        plan_path = repo_root / plan_path

    if not plan_path.is_file():
        print(colored(f"Error: Plan file not found: {args.plan_file}", Colors.RED), file=sys.stderr)
        return 1

    # Resolve plan_file relative to repo root for matching
    try:
        plan_file_rel = str(plan_path.relative_to(repo_root))
    except ValueError:
        plan_file_rel = str(plan_path)

    # Find all trellis tasks linked to this plan
    tasks_dir = get_tasks_dir(repo_root)
    if not tasks_dir.is_dir():
        print(colored("No tasks directory found", Colors.YELLOW), file=sys.stderr)
        return 0

    matching_tasks: list[dict] = []
    for task_dir in tasks_dir.iterdir():
        if not task_dir.is_dir() or task_dir.name == "archive":
            continue
        task_json = task_dir / FILE_TASK_JSON
        if not task_json.is_file():
            continue
        data = read_json(task_json)
        if not data:
            continue
        meta = data.get("meta", {})
        if meta.get("plan_file") == plan_file_rel:
            matching_tasks.append(data)

    if not matching_tasks:
        print(colored("No trellis tasks linked to this plan", Colors.YELLOW), file=sys.stderr)
        return 0

    content = plan_path.read_text(encoding="utf-8")
    plan_tasks = _extract_task_blocks(content)

    if not plan_tasks:
        print(colored("No task blocks found in plan", Colors.YELLOW), file=sys.stderr)
        return 0

    # Build a map: plan_task_index -> trellis status
    status_map: dict[int, str] = {}
    for td in matching_tasks:
        idx = td.get("meta", {}).get("plan_task_index")
        if idx is not None:
            status_map[idx] = td.get("status", "planning")

    # Process in reverse order to preserve offsets
    changed = 0
    for pt in reversed(plan_tasks):
        task_index = pt["index"]
        if task_index not in status_map:
            continue

        status = status_map[task_index]
        section = content[pt["section_start"]:pt["section_end"]]

        if status in ("completed", "done"):
            # Replace - [ ] with - [x] in this section (not inside code blocks)
            new_section = _check_all_boxes(section)
            if new_section != section:
                content = (
                    content[: pt["section_start"]]
                    + new_section
                    + content[pt["section_end"]:]
                )
                changed += 1
                print(
                    colored(
                        f"  Task {task_index}: marked steps complete",
                        Colors.GREEN,
                    ),
                    file=sys.stderr,
                )

        elif status in ("in_progress",):
            # Add <!-- status: in_progress --> after header if not already there
            header_line_end = section.index("\n") + 1
            header_after = section[header_line_end:header_line_end + 100]
            if "<!-- status: in_progress -->" not in header_after:
                insertion = "<!-- status: in_progress -->\n"
                offset = pt["section_start"] + header_line_end
                content = content[:offset] + insertion + content[offset:]
                changed += 1
                print(
                    colored(
                        f"  Task {task_index}: added in_progress marker",
                        Colors.CYAN,
                    ),
                    file=sys.stderr,
                )

    if changed > 0:
        plan_path.write_text(content, encoding="utf-8")
        print(
            colored(f"Sync complete: {changed} task(s) updated", Colors.GREEN),
            file=sys.stderr,
        )
    else:
        print(colored("No changes needed", Colors.GREEN), file=sys.stderr)

    return 0


def _check_all_boxes(section: str) -> str:
    """Replace all ``- [ ]`` with ``- [x]`` outside of code blocks."""
    lines = section.split("\n")
    in_code_block = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if not in_code_block and re.match(r"^(\s*)- \[ \]", line):
            lines[i] = re.sub(r"^- \[ \]", "- [x]", line, count=1)
    return "\n".join(lines)
