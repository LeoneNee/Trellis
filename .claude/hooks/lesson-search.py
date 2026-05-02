#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lesson Search Hook - UserPromptSubmit

在用户输入 prompt 时，自动搜索 .trellis/lessons/ 中相关的 lessons，
通过 additionalContext 注入到对话中。

搜索策略：多维度加权匹配（文件名、Search Keywords、Tags、Module、正文）
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

# Force stdout to use UTF-8 (fixes UnicodeEncodeError on Windows and other platforms)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from common_hook import find_repo_root  # type: ignore[import-not-found]

# --- 停用词 ---

ENGLISH_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "because", "but", "and", "or", "if", "while", "about", "up", "its",
    "it", "this", "that", "these", "those", "i", "me", "my", "we", "our",
    "you", "your", "he", "him", "his", "she", "her", "they", "them", "their",
    "what", "which", "who", "whom", "whose", "also", "any",
})

CHINESE_STOP_WORDS = frozenset({
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
    "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会",
    "着", "没有", "看", "好", "自己", "这", "他", "她", "它", "们",
    "那", "些", "什么", "怎么", "如何", "为什么", "还是", "或者",
    "但是", "因为", "所以", "如果", "虽然", "可以", "需要", "应该",
    "能", "做", "让", "把", "被", "给", "从", "向", "比", "用",
    "这个", "那个", "一下", "一点", "一些", "不要", "没", "吧",
})


def tokenize(text: str) -> set[str]:
    """分词：英文按空格/标点，中文按 bigram，去停用词"""
    if not text:
        return set()

    text = text.lower()
    tokens: set[str] = set()

    # 英文：提取单词
    english_words = re.findall(r"[a-z][a-z0-9_\-\.]*", text)
    for w in english_words:
        if w not in ENGLISH_STOP_WORDS and len(w) > 1:
            tokens.add(w)

    # 中文：提取连续中文字符段，做 bigram
    chinese_segments = re.findall(r"[\u4e00-\u9fff]+", text)
    for seg in chinese_segments:
        # 单字
        for ch in seg:
            if ch not in CHINESE_STOP_WORDS:
                tokens.add(ch)
        # bigram（连续两字组合）
        for i in range(len(seg) - 1):
            bigram = seg[i : i + 2]
            if not all(ch in CHINESE_STOP_WORDS for ch in bigram):
                tokens.add(bigram)

    return tokens


def extract_section(content: str, heading: str) -> str:
    """提取 markdown 中某个 ## 标题下的内容，到下一个 ## 或文件末尾"""
    pattern = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
    m = re.search(pattern, content, re.DOTALL)
    if not m:
        return ""
    text = m.group(1).strip()
    # 清理掉代码块标记
    text = re.sub(r"```[\s\S]*?```", "", text)
    # 压缩空白
    text = re.sub(r"\n{2,}", "\n", text)
    return text[:300]


def extract_title(content: str) -> str:
    """提取 # 标题"""
    m = re.match(r"#\s+(.+)", content)
    return m.group(1).strip() if m else "(untitled)"


def extract_keywords_section(content: str) -> list[str]:
    """提取 ## Search Keywords 段落下的 - 开头的条目"""
    section = extract_section(content, "Search Keywords")
    if not section:
        return []
    keywords = []
    for line in section.split("\n"):
        line = line.strip()
        # 匹配 "- keyword" 或 "- keyword" 格式
        m = re.match(r"[-*]\s+(.+)", line)
        if m:
            kw = m.group(1).strip()
            if kw:
                keywords.append(kw)
        elif line and not line.startswith("#"):
            keywords.append(line)
    return keywords


def extract_tags(content: str) -> list[str]:
    """从 Tags: 行提取标签"""
    m = re.search(r"Tags:\s*(.+)", content)
    if not m:
        return []
    raw = m.group(1)
    return [t.strip() for t in raw.split(",") if t.strip()]


def extract_module(content: str) -> str:
    """从 Module: 行提取模块名"""
    m = re.search(r"Module:\s*(.+)", content)
    return m.group(1).strip() if m else ""


def compute_relevance(
    prompt_tokens: set[str],
    content: str,
    filename_stem: str,
    max_score: float = 0,
) -> float:
    """计算单个 lesson 文件与 prompt 的相关性得分"""
    score = 0.0

    # 1. 文件名匹配 (权重 3)
    name_text = filename_stem.replace("-", " ").replace("_", " ")
    file_tokens = tokenize(name_text)
    name_overlap = prompt_tokens & file_tokens
    score += len(name_overlap) * 3.0

    # 2. Search Keywords 匹配 (权重 3)
    keywords = extract_keywords_section(content)
    if keywords:
        kw_text = " ".join(keywords)
        kw_tokens = tokenize(kw_text)
        kw_overlap = prompt_tokens & kw_tokens
        score += len(kw_overlap) * 3.0

    # 3. Tags 匹配 (权重 2)
    tags = extract_tags(content)
    if tags:
        tag_text = " ".join(tags)
        tag_tokens = tokenize(tag_text)
        tag_overlap = prompt_tokens & tag_tokens
        score += len(tag_overlap) * 2.0

    # 4. Module 匹配 (权重 2)
    module = extract_module(content)
    if module:
        mod_tokens = tokenize(module)
        mod_overlap = prompt_tokens & mod_tokens
        score += len(mod_overlap) * 2.0

    # 5. 正文关键词交集 (权重 0.3，仅英文 token)
    content_lower = content.lower()
    for token in prompt_tokens:
        # 跳过中文单字 — 太容易误匹配
        if re.match(r"^[\u4e00-\u9fff]$", token):
            continue
        if token in content_lower:
            score += 0.3

    return score


def search_lessons(repo_root: str, user_prompt: str, top_n: int = 3) -> list[dict]:
    """搜索相关 lessons，返回按相关性排序的结果"""
    lessons_dir = Path(repo_root) / ".trellis" / "lessons"
    if not lessons_dir.exists():
        return []

    prompt_tokens = tokenize(user_prompt)
    if not prompt_tokens:
        return []

    # 计算所有 lesson 的最大可能得分，用于百分比
    max_possible = 0.0
    all_scored: list[tuple[dict, float]] = []

    for md_file in lessons_dir.rglob("*.md"):
        # Prevent symlink escape
        if not md_file.resolve().is_relative_to(lessons_dir.resolve()):
            continue
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if not content.strip():
            continue

        score = compute_relevance(prompt_tokens, content, md_file.stem)
        # 阈值从 3.0 降至 2.0：短 query 时单关键词匹配也应该返回结果
        if score < 2.0:
            continue

        result = {
            "path": str(md_file.relative_to(repo_root)),
            "score": score,
            "title": extract_title(content),
            "root_cause": extract_section(content, "Root Cause"),
            "reusable_lesson": extract_section(content, "Reusable Lesson"),
            "lesson_points": extract_section(content, "关键修复点"),
        }
        all_scored.append((result, score))
        if score > max_possible:
            max_possible = score

    if not all_scored:
        return []

    # 排序并取 top N
    all_scored.sort(key=lambda x: x[1], reverse=True)
    results = []
    for result, score in all_scored[:top_n]:
        result["relevance"] = round(score / max_possible * 100) if max_possible > 0 else 0
        results.append(result)

    return results


def build_context(results: list[dict]) -> str:
    """构建 additionalContext 文本"""
    if not results:
        return ""

    lines = [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📚 相关历史 Lessons ({len(results)} 条匹配)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for r in results:
        title = r["title"][:80]
        relevance = r["relevance"]
        lines.append(f"▸ {title} (relevance: {relevance}%)")

        # 优先展示 root cause
        root_cause = r.get("root_cause", "")
        if root_cause:
            # 取第一行作为摘要
            first_line = root_cause.split("\n")[0].strip()
            if first_line:
                lines.append(f"  根因: {first_line[:100]}")

        # 展示 reusable lesson
        reusable = r.get("reusable_lesson", "")
        if reusable:
            first_line = reusable.split("\n")[0].strip()
            if first_line:
                lines.append(f"  教训: {first_line[:100]}")

        # 如果没有标准格式，展示 lesson_points
        elif r.get("lesson_points"):
            first_line = r["lesson_points"].split("\n")[0].strip()
            if first_line:
                lines.append(f"  要点: {first_line[:100]}")

        lines.append(f"  文件: {r['path']}")
        lines.append("")

    lines.append("⚠️ 请在实现前阅读这些 lessons 的完整内容")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")

    return "\n".join(lines)


def main():
    try:
        raw = sys.stdin.read(1_000_000)  # limit to 1MB
        if not raw:
            sys.exit(0)
        input_data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    hook_event = input_data.get("hook_event_name", "")
    if hook_event != "UserPromptSubmit":
        sys.exit(0)

    # 获取用户输入
    user_prompt = input_data.get("user_prompt", "")
    # 也尝试从环境变量获取（兼容不同版本）
    if not user_prompt:
        user_prompt = os.environ.get("CLAUDE_USER_INPUT", "")
    if not user_prompt:
        sys.exit(0)

    cwd = input_data.get("cwd", os.getcwd())
    repo_root = find_repo_root(cwd)
    if not repo_root:
        sys.exit(0)

    # 搜索相关 lessons
    results = search_lessons(repo_root, user_prompt, top_n=3)

    if not results:
        sys.exit(0)

    # 构建并输出 additionalContext
    context = build_context(results)
    if context:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            }
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
