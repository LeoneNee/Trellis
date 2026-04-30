#!/usr/bin/env python3
"""
Claude Code Commit Review Wrapper
调用 consensus-debate 多模型博弈进行代码审查，解析 P0/P1 问题。
Exit 0 = 无 P0/P1，可提交
Exit 1 = 发现 P0/P1，阻断提交
Exit 2 = 配置错误
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent
DEBATE_SCRIPT = SKILL_DIR / "run_debate.py"


def run_debate_review(content: str) -> dict:
    """调用 run_debate.py 进行 review，返回解析后的结果."""
    env = os.environ.copy()
    if not env.get("LOCAL_MODEL_CONFIGS"):
        local_models = SKILL_DIR / "models.json"
        if local_models.exists():
            raw = local_models.read_text(encoding="utf-8")
            try:
                configs = json.loads(raw)
                has_valid_key = any(c.get("api_key", "").strip() for c in configs if isinstance(c, dict))
                if not has_valid_key:
                    print("[review-wrapper] SKIP: models.json has no valid API keys, skipping multi-model review", file=sys.stderr)
                    sys.exit(0)
            except json.JSONDecodeError:
                print("[review-wrapper] SKIP: models.json is invalid JSON, skipping multi-model review", file=sys.stderr)
                sys.exit(0)
            env["LOCAL_MODEL_CONFIGS"] = raw
        else:
            print("[review-wrapper] SKIP: no models.json found, skipping multi-model review", file=sys.stderr)
            sys.exit(0)

    cmd = [
        sys.executable, str(DEBATE_SCRIPT),
        "--task", "代码审查：检查以下改动的 P0（崩溃/bug/数据丢失）和 P1（逻辑错误/安全隐患/严重性能问题）问题",
        "--content", content,
        "--scene", "review",
        "--review-mode", "summarized",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    stdout = result.stdout.strip()

    # 解析 JSON 输出
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        print(f"[review-wrapper] DEBUG stdout: {stdout[:500]}", file=sys.stderr)
        print(f"[review-wrapper] DEBUG stderr: {result.stderr[:500]}", file=sys.stderr)
        print("[review-wrapper] ERROR: failed to parse JSON from run_debate.py", file=sys.stderr)
        sys.exit(2)


def extract_p0_p1_issues(final_plan: str) -> list:
    """从 final_plan 中提取 P0/P1 问题列表."""
    issues = []
    lines = final_plan.split("\n")
    current_issue = None
    current_level = None

    for line in lines:
        line = line.strip()
        upper = line.upper()
        # 检测 P0/P1 标记
        if any(tag in upper for tag in ["[P0]", "**[P0]**", "P0:", "**P0"]):
            current_level = "P0"
            current_issue = line
        elif any(tag in upper for tag in ["[P1]", "**[P1]**", "P1:", "**P1"]):
            current_level = "P1"
            current_issue = line
        elif current_issue and line and not line.startswith("#") and not line.startswith("-"):
            # 继续收集问题内容（排除列表符号）
            current_issue += " " + line
        elif current_issue and (not line or line.startswith("#")):
            # 问题段结束
            if current_level and current_issue:
                issues.append(f"[{current_level}] {current_issue}")
            current_issue = None
            current_level = None

    # 最后一条
    if current_issue and current_level:
        issues.append(f"[{current_level}] {current_issue}")

    return issues


def main():
    # 读取 stdin（来自 git diff --cached 的管道输入）
    diff_content = sys.stdin.read() if not sys.stdin.isatty() else ""

    parser = argparse.ArgumentParser(description="Claude Code multi-model review wrapper")
    parser.add_argument("--message", type=str, default="", help="Commit message")
    args = parser.parse_args()

    content = diff_content if diff_content else "(空diff，请人工审核)"
    message = args.message or ""

    print(f"[review-wrapper] Starting multi-model review...", file=sys.stderr)
    if message:
        print(f"[review-wrapper] Commit: {message[:80]}", file=sys.stderr)
    if diff_content:
        print(f"[review-wrapper] Diff size: {len(diff_content)} chars", file=sys.stderr)

    try:
        result = run_debate_review(content)
    except Exception as e:
        print(f"[review-wrapper] ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    final_plan = result.get("final_plan", "")
    models = result.get("models_participated", [])
    failed = result.get("models_failed", [])

    print(f"[review-wrapper] Models participated: {', '.join(models)}", file=sys.stderr)
    if failed:
        print(f"[review-wrapper] Models failed: {', '.join(failed)}", file=sys.stderr)

    issues = extract_p0_p1_issues(final_plan)

    if issues:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"[review-wrapper] BLOCKED: Found {len(issues)} P0/P1 issues!", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)
        for issue in issues:
            print(f"  {issue}", file=sys.stderr)
        print(f"\n{'='*60}", file=sys.stderr)
        print("请修复以上问题后重新提交。", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"[review-wrapper] No P0/P1 issues found. Proceed with commit.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
