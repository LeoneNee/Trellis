"""
Shared utilities for Trellis Claude Code hooks.

Provides:
- find_repo_root: Walk up from a path to find the git repo root
- normalize_task_ref: Normalize a task reference string
- resolve_task_dir: Resolve a task reference to an absolute directory path
- get_task_status: Check current task status and return a structured string
"""

import json
import sys
from pathlib import Path


def find_repo_root(start_path: str) -> str | None:
    """Walk up from start_path to find git repo root.

    Returns:
        Repo root path, or None if not found.
    """
    current = Path(start_path).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def normalize_task_ref(task_ref: str) -> str:
    """Normalize a task reference string.

    Handles:
    - Stripping whitespace
    - Converting backslashes to forward slashes
    - Removing leading './'
    - Prefixing 'tasks/' with '.trellis/'
    - Preserving absolute paths
    """
    normalized = task_ref.strip()
    if not normalized:
        return ""

    path_obj = Path(normalized)
    if path_obj.is_absolute():
        return str(path_obj)

    normalized = normalized.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]

    if normalized.startswith("tasks/"):
        return f".trellis/{normalized}"

    return normalized


def resolve_task_dir(trellis_dir: Path, task_ref: str) -> Path:
    """Resolve a task reference to an absolute directory path.

    Args:
        trellis_dir: Path to the .trellis directory
        task_ref: Raw task reference string

    Returns:
        Resolved Path to the task directory
    """
    normalized = normalize_task_ref(task_ref)
    path_obj = Path(normalized)
    if path_obj.is_absolute():
        return path_obj
    if normalized.startswith(".trellis/"):
        return trellis_dir.parent / path_obj
    return trellis_dir / "tasks" / path_obj


def get_task_status(trellis_dir: Path) -> str:
    """Check current task status and return structured status string.

    Args:
        trellis_dir: Path to the .trellis directory

    Returns:
        Multi-line status string describing the current task state
    """
    current_task_file = trellis_dir / ".current-task"
    if not current_task_file.is_file():
        return "Status: NO ACTIVE TASK\nNext: Describe what you want to work on"

    task_ref = normalize_task_ref(current_task_file.read_text(encoding="utf-8").strip())
    if not task_ref:
        return "Status: NO ACTIVE TASK\nNext: Describe what you want to work on"

    # Resolve task directory
    task_dir = resolve_task_dir(trellis_dir, task_ref)
    if not task_dir.is_dir():
        return f"Status: STALE POINTER\nTask: {task_ref}\nNext: Task directory not found. Run: python3 ./.trellis/scripts/task.py finish"

    # Read task.json
    task_json_path = task_dir / "task.json"
    task_data = {}
    if task_json_path.is_file():
        try:
            task_data = json.loads(task_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, PermissionError):
            pass

    task_title = task_data.get("title", task_ref)
    task_status = task_data.get("status", "unknown")

    if task_status == "completed":
        return f"Status: COMPLETED\nTask: {task_title}\nNext: Archive with `python3 ./.trellis/scripts/task.py archive {task_dir.name}` or start a new task"

    # Check if context is configured (jsonl files exist and non-empty)
    has_context = False
    for jsonl_name in ("implement.jsonl", "check.jsonl", "spec.jsonl"):
        jsonl_path = task_dir / jsonl_name
        if jsonl_path.is_file() and jsonl_path.stat().st_size > 0:
            has_context = True
            break

    has_prd = (task_dir / "prd.md").is_file()

    if not has_prd:
        return f"Status: NOT READY\nTask: {task_title}\nMissing: prd.md not created\nNext: Write PRD, then research -> init-context -> start"

    if not has_context:
        return f"Status: NOT READY\nTask: {task_title}\nMissing: Context not configured (no jsonl files)\nNext: Complete Phase 2 (research -> init-context -> start) before implementing"

    return f"Status: READY\nTask: {task_title}\nNext: Continue with implement or check"
