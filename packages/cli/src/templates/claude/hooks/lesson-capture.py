#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lesson Capture Hook - SubagentStop

在 sub-agent 完成错误修复时自动记录 lesson 到 .trellis/lessons/

触发条件（满足任一）：
1. 消息中包含 "bug", "fix", "修复", "error", "issue" 等关键词
2. git diff 中有 "fix", "bug", "patch" 等关键词
3. 最后一条 assistant 消息中包含修复相关的标记

写入位置: .trellis/lessons/YYYY-MM-DD-{slug}.md
"""

from __future__ import annotations

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

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
    for _ in range(8):
        if (current / ".git").exists():
            return str(current)
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def is_error_fix_session(input_data: dict) -> tuple:
    """判断是否完成了真正的错误修复，返回 (is_fix, reason)

    条件：必须有 git diff 内容，且 agent 消息中有实质性修复相关关键词。
    """
    last_msg = input_data.get("last_assistant_message", "") or ""
    agent_type = input_data.get("agent_type", "") or ""

    # 关键词模式（排除 prefix/suffix/affix 等误触发）
    fix_patterns = [
        r"(?<!\w)fix(ed|es|ing)?(?!\w*(?:ture|ed|prefix|suffix|affix|mixfix|postfix|infix|transfix|crucifix))\b",
        r"\bbug\b",
        r"\brepair(ed)?\b",
        r"\bpatch(ed)?\b",
        r"\bhotfix\b",
        r"\bhot-fix\b",
        r"\bbugfix\b",
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
            ["git", "diff", "HEAD", "--stat", "-p", "--", "*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.go"],
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


def infer_module(files_changed: list[str]) -> str:
    """从改动文件路径推断模块"""
    if not files_changed:
        return "unspecified"
    first = files_changed[0]
    parts = Path(first).parts
    if len(parts) >= 2:
        top = parts[0]
        if top in ("frontend", "backend", "packages", "src"):
            return f"{top}/{parts[1]}" if len(parts) > 2 else top
    return parts[0] if parts else "unspecified"


def infer_tags(diff_content: str, files_changed: list[str]) -> list[str]:
    """从文件扩展名和 diff 内容推断标签"""
    tags = []
    ext_map = {
        ".tsx": "react",
        ".jsx": "react",
        ".ts": "typescript",
        ".js": "javascript",
        ".py": "python",
        ".css": "css",
        ".html": "html",
        ".sql": "database",
    }
    for f in files_changed:
        ext = Path(f).suffix
        tag = ext_map.get(ext)
        if tag and tag not in tags:
            tags.append(tag)

    # 从 diff 内容检测技术关键词
    tech_patterns = {
        "jwt": r"\bjwt\b|\bJwtService\b|\bJwtModule\b",
        "auth": r"\bauthenticat|\bAuthoriz|\bGuard\b",
        "api": r"\bapi\b|\bendpoint\b|\bcontroller\b",
        "sse": r"\bSSE\b|\bEventSource\b|\btext/event-stream",
        "test": r"\btest\b|\bspec\b|\bdescribe\(|\bit\(",
        "database": r"\bprisma\b|\btypeorm\b|\bmongoose\b|\b\.sql\b",
        "hook": r"\buse[A-Z]\w+|useCallback|useEffect|useState|useMemo",
        "regex": r"\bRegExp\b|regex|正则",
    }
    diff_lower = diff_content.lower()
    for tag, pattern in tech_patterns.items():
        if re.search(pattern, diff_lower) and tag not in tags:
            tags.append(tag)

    return tags or ["untagged"]


def extract_keywords(files_changed: list[str], diff_content: str, assistant_summary: str) -> list[str]:
    """从文件名、diff 和 assistant 消息中提取搜索关键词"""
    keywords = []

    # 文件名中的技术词
    for f in files_changed:
        stem = Path(f).stem
        # 拆分 camelCase 和 kebab-case
        words = re.findall(r"[a-zA-Z][a-z0-9]*", stem)
        for w in words:
            if len(w) > 2 and w.lower() not in keywords:
                keywords.append(w.lower())

    # diff 中的标识符（函数名、类名等）
    for line in diff_content.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            stripped = line[1:].strip()
            # 提取函数/方法调用
            calls = re.findall(r"\b([a-z][a-zA-Z]{3,})\s*\(", stripped)
            for c in calls:
                if c.lower() not in keywords:
                    keywords.append(c.lower())

    # assistant 消息中的错误关键词
    error_patterns = [
        r"`([^`]{3,40})`",  # 反引号包裹的代码/错误
        r"Error[:\s]+([^\n]{5,50})",
        r"错误[：:]\s*([^\n]{5,50})",
    ]
    for pat in error_patterns:
        for m in re.finditer(pat, assistant_summary):
            kw = m.group(1).strip().lower()
            if kw and len(kw) > 2 and kw not in keywords:
                keywords.append(kw)

    return keywords[:12]


def extract_root_cause_hint(assistant_summary: str) -> str:
    """从 assistant 消息中尝试提取根因描述"""
    patterns = [
        r"(?:root cause|根因|原因[是为])\s*[:：]?\s*(.+?)(?:\n|$)",
        r"(?:问题[是在]|原因[是为])\s*[:：]?\s*(.+?)(?:\n|$)",
        r"(?:fix|修复|解决)\s*[:：]\s*(.+?)(?:\n|$)",
    ]
    for pat in patterns:
        m = re.search(pat, assistant_summary, re.IGNORECASE)
        if m:
            text = m.group(1).strip()
            if len(text) > 10:
                return text[:300]

    # 回退：取 assistant 消息中第一个实质性句子
    for line in assistant_summary.split("\n"):
        line = line.strip()
        if len(line) > 20 and not line.startswith("#") and not line.startswith("```"):
            return line[:300]

    return ""


def extract_fix_content(input_data: dict, diff_content: str) -> dict:
    """从会话和 diff 中提取修复内容"""
    last_msg = input_data.get("last_assistant_message", "") or ""

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

    change_snippet = "\n".join(changes[:10])
    assistant_summary = last_msg[:1500]

    # 自动提取结构化字段
    module = infer_module(files_changed)
    tags = infer_tags(diff_content, files_changed)
    keywords = extract_keywords(files_changed, diff_content, assistant_summary)
    root_cause_hint = extract_root_cause_hint(assistant_summary)

    return {
        "files": files_changed,
        "change_snippet": change_snippet,
        "assistant_summary": assistant_summary,
        "module": module,
        "tags": tags,
        "keywords": keywords,
        "root_cause_hint": root_cause_hint,
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
    """写入标准模板格式的 lesson 文件"""
    if not is_fix or not should_create_lesson(repo_root, content):
        return None

    lessons_dir = Path(repo_root) / LESSONS_DIR
    lessons_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    # 从第一个文件路径生成有意义的 slug
    files = content.get("files", [])
    first_file = files[0] if files else "unknown"
    # 用文件名（去掉扩展名）作为 slug 的一部分
    stem = Path(first_file).stem
    slug = re.sub(r"[^\w\-]", "-", stem)[:50]
    if not slug or slug == "unknown":
        slug = re.sub(r"[^\w\-]", "-", first_file)[:50]
    filename = f"{date_str}-{slug}.md"
    filepath = lessons_dir / filename

    # 如果文件已存在，加序号
    counter = 1
    while filepath.exists():
        filename = f"{date_str}-{slug}-{counter}.md"
        filepath = lessons_dir / filename
        counter += 1

    # 提取结构化字段
    module = content.get("module", "unspecified")
    tags = content.get("tags", ["untagged"])
    keywords = content.get("keywords", [])
    root_cause_hint = content.get("root_cause_hint", "")
    assistant_summary = content.get("assistant_summary", "")
    change_snippet = content.get("change_snippet", "")

    # 从 assistant 消息中提取标题（取第一个非空非标题行，截取到第一个句号）
    title = "Bug Fix — Auto-captured"
    for line in assistant_summary.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("```") and not line.startswith("**"):
            # 截取到第一个句号
            for end in ["。", ".", "！", "!"]:
                pos = line.find(end)
                if 10 < pos < 80:
                    title = line[:pos].strip()
                    break
            else:
                title = line[:60].rstrip("。.,;")
            break

    # 按标准模板格式构建 lesson
    lines = [
        f"# {title}",
        "",
        "## Basic Info",
        f"- Date: {date_str}",
        f"- Module: {module}",
        f"- Problem Type: Bug Fix",
        f"- Tags: {', '.join(tags)}",
        "- Related Files:",
    ]
    for f in files:
        lines.append(f"  - {f}")

    lines.append("")

    # Symptom — 从 assistant 消息中提取问题描述
    lines.append("## Symptom")
    symptom = _extract_symptom(assistant_summary)
    if symptom:
        lines.append(symptom)
    else:
        lines.append(f"触发原因: {reason}")
    lines.append("")

    # Root Cause
    lines.append("## Root Cause")
    if root_cause_hint:
        lines.append(root_cause_hint)
    else:
        lines.append(f"见下方改动摘要和关键修复点。")
    lines.append("")

    # Solution — diff 摘要
    lines.append("## Solution")
    if change_snippet:
        lines.append("```diff")
        lines.append(change_snippet[:1000])
        lines.append("```")
    else:
        lines.append("_无 staged diff 内容_")
    lines.append("")

    # 关键修复点 — assistant 消息摘要
    lines.append("## 关键修复点")
    if assistant_summary:
        lines.append(assistant_summary[:500])
        if len(assistant_summary) > 500:
            lines.append("...")
    lines.append("")

    # Reusable Lesson
    lines.append("## Reusable Lesson")
    lesson_text = _extract_reusable_lesson(assistant_summary, tags)
    if lesson_text:
        lines.append(lesson_text)
    else:
        lines.append("_待人工补充_")
    lines.append("")

    # Search Keywords
    lines.append("## Search Keywords")
    for kw in keywords:
        lines.append(f"- {kw}")
    lines.append("")

    try:
        filepath.write_text("\n".join(lines), encoding="utf-8")
        return str(filepath)
    except Exception as e:
        print(f"Failed to write lesson: {e}", file=sys.stderr)
        return None


def _extract_symptom(assistant_summary: str) -> str:
    """从 assistant 消息中提取症状描述"""
    patterns = [
        r"(?:symptom|症状|现象|表现)[：:]\s*(.+?)(?=\n##|\n\n|\Z)",
        r"(?:问题描述|问题[是为])\s*[：:]?\s*(.+?)(?=\n##|\n\n|\Z)",
    ]
    for pat in patterns:
        m = re.search(pat, assistant_summary, re.IGNORECASE | re.DOTALL)
        if m:
            text = m.group(1).strip()[:300]
            if len(text) > 10:
                return text
    return ""


def _extract_reusable_lesson(assistant_summary: str, tags: list[str]) -> str:
    """尝试从 assistant 消息中提取可复用的教训"""
    patterns = [
        r"(?:reusable lesson|教训|经验|原则|总结)[：:]\s*(.+?)(?=\n##|\Z)",
        r"(?:prevention|预防|避免)[：:]\s*(.+?)(?=\n##|\Z)",
    ]
    for pat in patterns:
        m = re.search(pat, assistant_summary, re.IGNORECASE | re.DOTALL)
        if m:
            text = m.group(1).strip()[:300]
            if len(text) > 10:
                return text
    return ""


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
            if stripped and not stripped.startswith(("//", "/*", "*", "#", "--")):
                code_change_lines += 1
        elif line.startswith("-") and not line.startswith("---"):
            stripped = line[1:].strip()
            if stripped and not stripped.startswith(("//", "/*", "*", "#", "--")):
                code_change_lines += 1
    return code_change_lines >= 2


def main():
    try:
        raw = sys.stdin.read(1_000_000)  # limit to 1MB
        if not raw:
            sys.exit(0)
        input_data = json.loads(raw)
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
