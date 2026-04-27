#!/usr/bin/env python3
"""
GitNexus pre-commit impact hook.
Runs before Edit/Write operations to check impact of pending changes.

Outputs a warning if the changes affect critical execution flows.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any


def load_config(trellis_dir: Path) -> Dict[str, Any]:
    """Load config and check gitnexus settings."""
    config_path = trellis_dir / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        content = config_path.read_text(encoding="utf-8")
        if "gitnexus:" in content:
            enabled = "enabled: true" in content
            check_edit = "impact_before_edit: true" in content
            return {
                "gitnexus": {
                    "enabled": enabled,
                    "impact_before_edit": check_edit,
                }
            }
    except Exception:
        pass
    return {}


def detect_impact(cwd: str) -> Optional[str]:
    """Run gitnexus detect-changes to get impact summary."""
    try:
        result = subprocess.run(
            ["gitnexus", "detect-changes", "--scope", "unstaged"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=cwd
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def check_gitnexus_available() -> bool:
    """Check if gitnexus is available."""
    try:
        result = subprocess.run(
            ["gitnexus", "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def main():
    cwd = os.getcwd()
    trellis_dir = Path(cwd) / ".trellis"

    config = load_config(trellis_dir)
    gn_config = config.get("gitnexus", {})

    if not gn_config.get("enabled") or not gn_config.get("impact_before_edit"):
        sys.exit(0)

    if not check_gitnexus_available():
        sys.exit(0)

    # Only run every N edits to avoid slowdown (use counter file)
    counter_file = trellis_dir / ".impact-check-counter"
    counter = 0
    try:
        if counter_file.exists():
            counter = int(counter_file.read_text().strip())
    except Exception:
        counter = 0

    counter += 1
    try:
        counter_file.write_text(str(counter))
    except Exception:
        pass

    # Only check every 5 edits
    if counter % 5 != 0:
        sys.exit(0)

    impact = detect_impact(cwd)
    if impact and ("HIGH" in impact or "CRITICAL" in impact):
        print(f"\n⚠️ GitNexus Impact Warning:\n{impact}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
