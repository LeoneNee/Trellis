#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lesson Capture Hook - SubagentStop

在 sub-agent 完成错误修复时自动记录 lesson 到 .harness/lessons/

触发条件（满足任一）：
1. 消息中包含 "bug", "fix", "修复", "error", "issue" 等关键词
2. git diff 中有 "fix", "bug", "patch" 等关键词
3. 最后一条 assistant 消息中包含修复相关的标记

写入位置: .harness/lessons/YYYY-MM-DD-{slug}.md
"""

from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

LESSONS_DIR = ".trellis/lessons"


def find_repo_root(start_path: str) -> Optional[str]:
    current = Path(start_path).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def is_error_fix_session(input_data: dict) -> tuple:
    """判断是否完成了真正的错误修复，返回 (is_fix, reason)

    条件：必须有 git diff 内容，且 agent 消息中有实质性修复相关关键词。
    """
    last_msg = input_data.get("last_assistant_message", "") or ""
    agent_type = input_data.get("agent_type", "") or ""

    # 宽松的关键词模式（任何 agent 都可能修 bug）
    fix_patterns = [
        r"\bfix(ed|es|ing)?\b",
        r"\bbug\b",
        r"\brepair(ed)?\b",
        r"\bpatch(ed)?\b",
        r"\bhotfix\b",
        r"\bhot-fix\b",
    ]

    combined = last_msg.lower()
    keyword_matches = []
    for pattern in fix_patterns:
        if re.search(pattern, combined, re.IGNORECASE):
            keyword_matches.append(pattern)

    # 必须有实质性的修复关键词才继续（避免误触发）
    if not keyword_matches:
        return False, ""

    # 标记类模式（更强的信号）
    tag_patterns = [
        r"\[(FIX|BUG|PATCH|FIXED|BUGFIX|HOTFIX|HOT-FIX)\]",
        r"\{(fix|bug|patch|hotfix)\}",
    ]
    for pattern in tag_patterns:
        if re.search(pattern, last_msg, re.IGNORECASE):
            return True, f"tag_match={pattern}"

    # 有关键词 + diff 内容才写 lesson
    # diff 检查由 main() 在调用前完成
    return True, f"keywords={keyword_matches}"


def get_git_diff_summary(repo_root: str) -> str:
    """获取最近一次 commit 的 diff 摘要"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--stat", "-p", "--", "*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.go"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout[:2000]  # 限制长度
    except Exception:
        pass
    return ""


def extract_fix_content(input_data: dict, diff_content: str) -> dict:
    """从会话和 diff 中提取修复内容"""
    last_msg = input_data.get("last_assistant_message", "") or ""
    cwd = input_data.get("cwd", "") or ""

    # 尝试从 diff 中提取文件名和改动
    files_changed = []
    changes = []

    if diff_content:
        lines = diff_content.split("\n")
        for line in lines:
            # diff --git a/file b/file
            m = re.match(r"diff --git a/(.+) b/(.+)", line)
            if m:
                files_changed.append(m.group(1))
            # + 或 - 开头的行（简化处理）
            if line.startswith("+") and not line.startswith("+++"):
                changes.append(line[:100])

    return {
        "files": files_changed,
        "change_snippet": "\n".join(changes[:10]),
        "assistant_summary": last_msg[:1000],
    }


def should_create_lesson(repo_root: str, content: dict) -> bool:
    """判断 lesson 内容是否值得记录"""
    # 有文件改动
    if content.get("files"):
        return True
    # 或者有实质性的 assistant 消息
    if len(content.get("assistant_summary", "")) > 50:
        return True
    return False


def write_lesson(repo_root: str, is_fix: bool, reason: str, content: dict) -> Optional[str]:
    """写入 lesson 文件，返回文件路径"""
    if not is_fix or not should_create_lesson(repo_root, content):
        return None

    lessons_dir = Path(repo_root) / LESSONS_DIR
    lessons_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    # 生成 slug
    first_file = (content.get("files") or ["unknown"])[0]
    slug = re.sub(r"[^\w\-]", "_", first_file)[:40]
    filename = f"{date_str}-{slug}.md"
    filepath = lessons_dir / filename

    # 如果文件已存在，加序号
    counter = 1
    while filepath.exists():
        filename = f"{date_str}-{slug}-{counter}.md"
        filepath = lessons_dir / filename
        counter += 1

    # 构建 lesson 内容
    lines = [
        f"# Lesson — {now.strftime('%Y-%m-%d %H:%M')}",
        "",
        f"**触发原因**: {reason}",
        "",
        "## 改动文件",
    ]
    for f in content.get("files", []):
        lines.append(f"- {f}")

    lines.append("")
    lines.append("## 改动摘要")

    snippet = content.get("change_snippet", "")
    if snippet:
        lines.append("```diff")
        lines.append(snippet[:1000])
        lines.append("```")
    else:
        lines.append("_无显著 diff 内容_")

    lines.append("")
    lines.append("## 关键修复点")

    # 从 assistant 消息中提取关键信息
    assistant_summary = content.get("assistant_summary", "")
    if assistant_summary:
        # 取前 500 字
        lines.append(assistant_summary[:500])
        if len(assistant_summary) > 500:
            lines.append("...")

    lines.append("")
    lines.append(f"**记录时间**: {now.isoformat()}")

    try:
        filepath.write_text("\n".join(lines), encoding="utf-8")
        return str(filepath)
    except Exception as e:
        print(f"Failed to write lesson: {e}", file=sys.stderr)
        return None


def is_meaningful_diff(diff_content: str) -> bool:
    """判断 diff 是否有实质性代码改动（不只是空行或注释变化）"""
    if not diff_content:
        return False
    lines = diff_content.split("\n")
    code_change_lines = 0
    for line in lines:
        if line.startswith("+") and not line.startswith("+++"):
            # 跳过空行和纯注释行
            stripped = line[1:].strip()
            if stripped and not stripped.startswith("//") and not stripped.startswith("/*") and not stripped.startswith("*"):
                code_change_lines += 1
        elif line.startswith("-") and not line.startswith("---"):
            stripped = line[1:].strip()
            if stripped and not stripped.startswith("//") and not stripped.startswith("/*") and not stripped.startswith("*"):
                code_change_lines += 1
    return code_change_lines >= 2


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    if hook_event != "SubagentStop":
        sys.exit(0)

    cwd = input_data.get("cwd", os.getcwd())
    repo_root = find_repo_root(cwd)
    if not repo_root:
        sys.exit(0)

    # 检查是否是修复会话
    is_fix, reason = is_error_fix_session(input_data)
    if not is_fix:
        print(json.dumps({"decision": "allow"}, ensure_ascii=False))
        return

    # 获取 diff 内容，必须有实质性改动才写 lesson
    diff_content = get_git_diff_summary(repo_root)
    if not is_meaningful_diff(diff_content):
        print(json.dumps({"decision": "allow"}, ensure_ascii=False))
        return

    # 提取修复内容
    content = extract_fix_content(input_data, diff_content)

    # 写入 lesson
    lesson_path = write_lesson(repo_root, is_fix, reason, content)

    if lesson_path:
        print(json.dumps({
            "decision": "allow",
            "lesson_recorded": lesson_path,
            "reason": f"Error fix detected ({reason}). Lesson written to {lesson_path}."
        }, ensure_ascii=False))
    else:
        print(json.dumps({"decision": "allow"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
