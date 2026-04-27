#!/usr/bin/env python3
"""
GitNexus augment hook - enriches search results with knowledge graph context.
Triggered on Grep/Glob tool calls when GitNexus is enabled.

Reads the tool call from stdin (JSON), extracts the search query,
and outputs additional context from the GitNexus knowledge graph.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List


def load_config(trellis_dir: Path) -> Dict[str, Any]:
    """Load .trellis/config.yaml and check if gitnexus is enabled."""
    config_path = trellis_dir / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        content = config_path.read_text(encoding="utf-8")
        # Simple check: gitnexus: enabled: true
        if "gitnexus:" in content and "enabled: true" in content:
            return {"gitnexus": {"enabled": True}}
    except Exception:
        pass
    return {}


def check_gitnexus_available() -> bool:
    """Check if gitnexus CLI is available."""
    try:
        result = subprocess.run(
            ["gitnexus", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def query_gitnexus(query_text: str) -> Optional[str]:
    """Query GitNexus for related execution flows."""
    try:
        # Use gitnexus CLI to query
        result = subprocess.run(
            ["gitnexus", "query", query_text],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def extract_search_query(tool_input: Dict[str, Any], tool_name: str) -> Optional[str]:
    """Extract search query from tool call input."""
    if tool_name in ("Grep", "Glob"):
        return tool_input.get("pattern", "")
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        # Extract grep/find/rg patterns from bash commands
        for cmd in ["grep", "rg", "find", "ag"]:
            if cmd in command:
                parts = command.split()
                for i, part in enumerate(parts):
                    if part == cmd and i + 1 < len(parts):
                        return parts[i + 1].strip("'\"")
    return None


def main():
    try:
        # Read tool call context from stdin
        input_data = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}
    except Exception:
        input_data = {}

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Find project root
    cwd = os.getcwd()
    trellis_dir = Path(cwd) / ".trellis"

    # Check if GitNexus is enabled
    config = load_config(trellis_dir)
    if not config.get("gitnexus", {}).get("enabled"):
        sys.exit(0)

    if not check_gitnexus_available():
        sys.exit(0)

    # Extract search query
    query = extract_search_query(tool_input, tool_name)
    if not query or len(query) < 3:
        sys.exit(0)

    # Query GitNexus
    result = query_gitnexus(query)
    if result:
        print(f"\n<gitnexus-context>\n{result}\n</gitnexus-context>")

    sys.exit(0)


if __name__ == "__main__":
    main()
