#!/usr/bin/env python3
"""
Multi-Agent Review Engine
Dispatches parallel reviews to Codex CLI and Kimi CLI,
merges results with cross-validation.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

SKILL_DIR = Path(__file__).parent
DEFAULT_CONFIG = SKILL_DIR / "config.json"
MAX_DIFF_SIZE = 1_000_000

REVIEW_PROMPT_TEMPLATE = """\
Review the following code diff for bugs, security issues, and correctness.
For each finding, verify it by running the actual code if possible.

Rules:
- Only report issues you can verify with code execution or clear evidence
- Mark severity: [P0] crash/data-loss/security, [P1] logic-error/race-condition, [P2] code-quality
- Format each issue as: [P0/P1/P2] <file>:<line> — <description>
- If you find NO issues, say "No issues found"
- Do NOT report stylistic issues or theoretical risks without evidence

Focus areas: {focus}
{message_context}
Diff:
{diff}
"""


@dataclass
class ReviewerConfig:
    name: str
    cli_path: str
    subcommand: str = ""
    flags: list = field(default_factory=list)
    timeout_seconds: int = 25
    enabled: bool = True


@dataclass
class Issue:
    severity: str
    description: str
    file: str = ""
    line: int = 0
    source: str = ""

    def key(self):
        return f"{self.severity}:{self.file}:{self.line}:{self.description[:60]}"


def load_config(config_path: Optional[str] = None) -> dict:
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    if not path.exists():
        return {"reviewers": [], "merge_policy": {}}
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def _resolve_cli_path(cli_path: str) -> str:
    """Resolve CLI path: exact path first, then shutil.which() fallback."""
    if cli_path and Path(cli_path).exists():
        return cli_path
    resolved = shutil.which(cli_path)
    return resolved or ""


# Flags that could enable command execution — reject these.
_DANGEROUS_FLAGS = {"--exec", "--eval", "--system", "--shell", "-e", "-c"}


def _validate_flags(flags: list) -> list:
    """Filter out flags that could enable arbitrary command execution."""
    safe = []
    for f in flags:
        if f in _DANGEROUS_FLAGS:
            print(f"[engine] WARN: rejecting dangerous flag: {f}", file=sys.stderr)
            continue
        safe.append(f)
    return safe


def get_enabled_reviewers(config: dict) -> list[ReviewerConfig]:
    reviewers = []
    for r in config.get("reviewers", []):
        if not r.get("enabled", True):
            continue
        cli_path = _resolve_cli_path(r.get("cli_path", ""))
        if not cli_path:
            print(f"[engine] SKIP: {r.get('name', '?')} CLI not found", file=sys.stderr)
            continue
        reviewers.append(ReviewerConfig(
            name=r["name"],
            cli_path=cli_path,
            subcommand=r.get("subcommand", ""),
            flags=_validate_flags(r.get("flags", [])),
            timeout_seconds=r.get("timeout_seconds", 25),
        ))
    return reviewers


def _try_claude_fallback() -> Optional[ReviewerConfig]:
    """If no external reviewers found, try Claude Code CLI as built-in fallback."""
    claude_path = _resolve_cli_path("claude")
    if not claude_path:
        return None
    print("[engine] No external reviewers found, using Claude CLI as fallback", file=sys.stderr)
    return ReviewerConfig(
        name="claude",
        cli_path=claude_path,
        flags=["-p", "--output-format", "text", "--max-turns", "1", "--no-input"],
        timeout_seconds=45,
    )


def build_review_prompt(diff_content: str, focus: str = "all", message: str = "") -> str:
    msg_ctx = f"\nCommit message: {message}\n" if message else ""
    return REVIEW_PROMPT_TEMPLATE.format(diff=diff_content[:MAX_DIFF_SIZE], focus=focus, message_context=msg_ctx)


def run_reviewer(reviewer: ReviewerConfig, prompt: str, cwd: str) -> dict:
    cmd = [reviewer.cli_path]
    if reviewer.subcommand:
        cmd.append(reviewer.subcommand)
    cmd.extend(reviewer.flags)

    is_claude = reviewer.name == "claude"

    if is_claude:
        # Claude CLI: pass prompt as the -p argument (last positional arg after flags)
        # Truncate to 200KB to stay well under ARG_MAX
        truncated = prompt[:200_000]
        cmd.append(truncated)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=reviewer.timeout_seconds,
                cwd=cwd,
            )
            return {
                "reviewer": reviewer.name,
                "raw_output": result.stdout + result.stderr,
                "timed_out": False,
                "error": "",
            }
        except subprocess.TimeoutExpired:
            return {
                "reviewer": reviewer.name,
                "raw_output": "",
                "timed_out": True,
                "error": "timeout",
            }
        except Exception as e:
            return {
                "reviewer": reviewer.name,
                "raw_output": "",
                "timed_out": False,
                "error": str(e),
            }
    else:
        # External CLIs: use temp file to avoid E2BIG
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, prefix="review-prompt-")
        try:
            tmp.write(prompt)
            tmp.close()
            cmd.append(f"@{tmp.name}")
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=reviewer.timeout_seconds,
                    cwd=cwd,
                )
                return {
                    "reviewer": reviewer.name,
                    "raw_output": result.stdout + result.stderr,
                    "timed_out": False,
                    "error": "",
                }
            except subprocess.TimeoutExpired:
                return {
                    "reviewer": reviewer.name,
                    "raw_output": "",
                    "timed_out": True,
                    "error": "timeout",
                }
            except Exception as e:
                return {
                    "reviewer": reviewer.name,
                    "raw_output": "",
                    "timed_out": False,
                    "error": str(e),
                }
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass


def parse_issues(raw_output: str, reviewer_name: str) -> list[Issue]:
    issues = []
    for line in raw_output.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"\[(P[012])\]\s*(\S+?)(?::(\d+))?\s*[—\-—]\s*(.+)", line)
        if m:
            issues.append(Issue(
                severity=m.group(1),
                file=m.group(2),
                line=int(m.group(3) or 0),
                description=m.group(4).strip(),
                source=reviewer_name,
            ))
            continue
        if any(tag in line.upper() for tag in ["[P0]", "[P1]", "[P2]"]):
            m2 = re.match(r"\[(P[012])\]\s*(.+)", line)
            if m2:
                issues.append(Issue(
                    severity=m2.group(1),
                    description=m2.group(2).strip(),
                    source=reviewer_name,
                ))
    return issues


def merge_reviews(
    all_issues: list[Issue],
    merge_policy: dict,
) -> dict:
    confirm_threshold = merge_policy.get("confirm_threshold", 2)

    groups: dict[str, list[Issue]] = {}
    for issue in all_issues:
        k = issue.key()
        groups.setdefault(k, []).append(issue)

    confirmed = []
    unverified = []
    for k, group in groups.items():
        sources = set(i.source for i in group)
        representative = group[0]
        if len(sources) >= confirm_threshold:
            confirmed.append({
                "severity": representative.severity,
                "file": representative.file,
                "line": representative.line,
                "description": representative.description,
                "confirmed_by": list(sources),
            })
        else:
            unverified.append({
                "severity": representative.severity,
                "file": representative.file,
                "line": representative.line,
                "description": representative.description,
                "reported_by": list(sources),
            })

    return {"confirmed_issues": confirmed, "unverified_issues": unverified}


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Review Engine")
    parser.add_argument("--diff", required=True, help="Diff content or @file path")
    parser.add_argument("--focus", default="all", help="Review focus: all, security, correctness, performance")
    parser.add_argument("--config", default=None, help="Path to config.json")
    parser.add_argument("--message", default="", help="Commit message for context")
    parser.add_argument("--output", default="json", choices=["json", "text"], help="Output format")
    args = parser.parse_args()

    # Load diff
    if args.diff.startswith("@"):
        diff_path = Path(args.diff[1:]).resolve()
        # Validate path is under cwd or /tmp to prevent path traversal
        allowed_prefixes = [Path.cwd().resolve(), Path("/tmp"), Path(tempfile.gettempdir())]
        if not any(str(diff_path).startswith(str(p)) for p in allowed_prefixes):
            print(f"[engine] ERROR: diff file path outside allowed directories: {diff_path}", file=sys.stderr)
            sys.exit(2)
        diff_content = diff_path.read_text(encoding="utf-8") if diff_path.exists() else ""
    elif Path(args.diff).exists() and "\n" not in args.diff:
        diff_content = Path(args.diff).read_text(encoding="utf-8")
    else:
        diff_content = args.diff

    if not diff_content.strip():
        json.dump({"confirmed_issues": [], "unverified_issues": [], "reviewers": []}, sys.stdout)
        return

    # Load config
    config = load_config(args.config)
    reviewers = get_enabled_reviewers(config)

    if not reviewers:
        # Fallback: try Claude Code CLI as built-in reviewer
        claude_fallback = _try_claude_fallback()
        if claude_fallback:
            reviewers = [claude_fallback]
            # Single reviewer: lower confirm_threshold so findings still get reported
            config.setdefault("merge_policy", {})["confirm_threshold"] = 1
        else:
            print("[engine] No reviewers available and Claude CLI not found. Skipping review.", file=sys.stderr)
            json.dump({"confirmed_issues": [], "unverified_issues": [], "reviewers": [], "error": "no reviewers available"}, sys.stdout)
            return

    # Build prompt
    prompt = build_review_prompt(diff_content, args.focus, getattr(args, "message", ""))
    cwd = os.getcwd()

    # Run reviewers in parallel
    results = []
    with ThreadPoolExecutor(max_workers=min(len(reviewers), 8)) as executor:
        futures = {executor.submit(run_reviewer, r, prompt, cwd): r for r in reviewers}
        for future in as_completed(futures):
            results.append(future.result())

    # Parse issues from each reviewer
    all_issues = []
    reviewer_names = []
    for result in results:
        name = result["reviewer"]
        reviewer_names.append(name)
        if result["timed_out"]:
            print(f"[engine] {name} timed out", file=sys.stderr)
            continue
        if result["error"]:
            print(f"[engine] {name} error: {result['error']}", file=sys.stderr)
            continue
        issues = parse_issues(result["raw_output"], name)
        all_issues.extend(issues)

    # Merge
    merged = merge_reviews(all_issues, config.get("merge_policy", {}))

    output = {
        "confirmed_issues": merged["confirmed_issues"],
        "unverified_issues": merged["unverified_issues"],
        "reviewers": reviewer_names,
        "review_details": {r["reviewer"]: r["raw_output"][:5000] for r in results},
    }

    if args.output == "json":
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    else:
        print("# Review Results\n")
        if output["confirmed_issues"]:
            print("## Confirmed Issues\n")
            for i in output["confirmed_issues"]:
                loc = f"{i['file']}:{i['line']}" if i.get("file") else ""
                print(f"- [{i['severity']}] {loc} — {i['description']} (confirmed by {', '.join(i['confirmed_by'])})")
        if output["unverified_issues"]:
            print("\n## Unverified Warnings\n")
            for i in output["unverified_issues"]:
                loc = f"{i['file']}:{i['line']}" if i.get("file") else ""
                print(f"- [{i['severity']}] {loc} — {i['description']} (only {', '.join(i['reported_by'])})")
        if not output["confirmed_issues"] and not output["unverified_issues"]:
            print("No issues found.")


if __name__ == "__main__":
    main()
