#!/usr/bin/env python3
"""
Commit Review Wrapper (multi-review)
Runs Codex CLI + Kimi CLI code review, extracts confirmed P0/P1 issues.
Exit 0 = no confirmed P0/P1, proceed
Exit 1 = confirmed P0/P1 found, block commit
Exit 2 = configuration error
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).parent
ENGINE_SCRIPT = SKILL_DIR / "review_engine.py"
CONFIG_FILE = SKILL_DIR / "config.json"


def check_prerequisites() -> bool:
    if not CONFIG_FILE.exists():
        print("[review-wrapper] SKIP: no config.json found, skipping multi-review", file=sys.stderr)
        return False

    try:
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("[review-wrapper] SKIP: config.json is invalid JSON", file=sys.stderr)
        return False

    enabled = [r for r in config.get("reviewers", []) if r.get("enabled", True)]
    if not enabled:
        print("[review-wrapper] SKIP: no reviewers enabled in config.json", file=sys.stderr)
        return False

    available = []
    for r in enabled:
        cli_path = r.get("cli_path", "")
        if cli_path and Path(cli_path).exists():
            available.append(r["name"])

    if not available:
        print("[review-wrapper] SKIP: no reviewer CLIs found on disk", file=sys.stderr)
        return False

    return True


def run_review(diff_content: str, message: str = "") -> dict:
    env = os.environ.copy()
    # Write diff to temp file to avoid E2BIG on large diffs
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".diff", delete=False, prefix="review-")
    try:
        tmp.write(diff_content)
        tmp.close()
        cmd = [
            sys.executable, str(ENGINE_SCRIPT),
            "--diff", f"@{tmp.name}",
            "--output", "json",
        ]
        if message:
            cmd.extend(["--message", message[:200]])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=27,
        )
    except subprocess.TimeoutExpired:
        print("[review-wrapper] ERROR: review engine timed out", file=sys.stderr)
        sys.exit(2)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    stdout = result.stdout.strip()
    if not stdout:
        print(f"[review-wrapper] DEBUG stderr: {result.stderr[:300]}", file=sys.stderr)
        print("[review-wrapper] ERROR: empty output from review_engine.py", file=sys.stderr)
        sys.exit(2)

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        print(f"[review-wrapper] DEBUG stdout: {stdout[:500]}", file=sys.stderr)
        print("[review-wrapper] ERROR: failed to parse JSON from review_engine.py", file=sys.stderr)
        sys.exit(2)


def main():
    diff_content = sys.stdin.read(1_000_000) if not sys.stdin.isatty() else ""

    parser = argparse.ArgumentParser(description="Multi-agent review wrapper")
    parser.add_argument("--message", type=str, default="", help="Commit message")
    args = parser.parse_args()

    if not diff_content.strip():
        sys.exit(0)

    message = args.message or ""
    print("[review-wrapper] Starting multi-agent review...", file=sys.stderr)
    if message:
        print(f"[review-wrapper] Commit: {message[:80]}", file=sys.stderr)

    if not check_prerequisites():
        sys.exit(0)

    try:
        result = run_review(diff_content, message=message)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[review-wrapper] ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    reviewers = result.get("reviewers", [])
    confirmed = result.get("confirmed_issues", [])
    unverified = result.get("unverified_issues", [])

    print(f"[review-wrapper] Reviewers: {', '.join(reviewers)}", file=sys.stderr)

    p0_p1 = [i for i in confirmed if i.get("severity") in ("P0", "P1")]

    if p0_p1:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"[review-wrapper] BLOCKED: {len(p0_p1)} confirmed P0/P1 issues!", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)
        for issue in p0_p1:
            loc = f"{issue.get('file', '')}:{issue.get('line', '')}" if issue.get("file") else ""
            by = ", ".join(issue.get("confirmed_by", []))
            print(f"  [{issue['severity']}] {loc} — {issue['description']} (confirmed by {by})", file=sys.stderr)
        print(f"\n{'='*60}", file=sys.stderr)
        sys.exit(1)

    if unverified:
        print(f"[review-wrapper] INFO: {len(unverified)} unverified warnings (not blocking)", file=sys.stderr)
        for issue in unverified:
            print(f"  [{issue['severity']}] {issue.get('description', '')}", file=sys.stderr)

    print("[review-wrapper] No confirmed P0/P1 issues. Proceed with commit.", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
