#!/usr/bin/env node
/**
 * Harness Knowledge Base Hook for Claude Code
 *
 * PreToolUse — detects when working in any project with a .harness
 *               directory and reminds the agent to check it before tasks.
 *             — if .harness doesn't exist, initializes one automatically.
 */

const fs = require('fs');
const path = require('path');

function readInput() {
  try {
    const data = fs.readFileSync(0, 'utf-8');
    return JSON.parse(data);
  } catch {
    return {};
  }
}

/**
 * Find .harness directory by walking up from startDir.
 * Returns the path to .harness/ or null if not found.
 */
function findHarnessDir(startDir) {
  let dir = startDir || process.cwd();
  for (let i = 0; i < 8; i++) {
    const candidate = path.join(dir, '.harness');
    if (fs.existsSync(candidate)) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

/**
 * Find project root (parent of .harness or cwd fallback).
 */
function findProjectRoot(startDir) {
  let dir = startDir || process.cwd();
  for (let i = 0; i < 8; i++) {
    const candidate = path.join(dir, '.harness');
    if (fs.existsSync(candidate)) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

function getRelativePath(targetPath) {
  const home = process.env.HOME || '/Users/nizhihao';
  if (targetPath.startsWith(home)) {
    return targetPath.replace(home, '~');
  }
  return targetPath;
}

const README_TEMPLATE = `# .harness Knowledge Base

This directory stores lessons learned from development work in this project.

Its purpose is to help the AI avoid repeated mistakes, improve implementation quality, and check past issues before starting new tasks.

## What to do before starting a task

Before implementing any task, the AI must:

1. Read \`.harness/INDEX.md\`
2. Look for relevant past lessons by:
   - feature
   - module
   - technology
   - symptom
   - error type
   - tags
3. Output a short historical experience check
4. List the risks and mistakes to avoid in the current task

## What to do after fixing a bug

After a bug is successfully fixed, the AI must create or update a lesson document in \`.harness/lessons/\`.

The lesson should include:

- issue title
- symptom
- root cause
- solution
- prevention
- related files or modules
- tags
- search keywords

The AI must also update \`.harness/INDEX.md\`.

## Goal

The goal of this knowledge base is to make past mistakes searchable and reusable, so future tasks can avoid similar problems earlier in development.
`;

const INDEX_TEMPLATE = `# .harness Index

> Auto-generated on first initialization. Update this file whenever you add new lessons.

## Overview

| Stat | Value |
|------|-------|
| Lessons (total) | 0 |
| Last updated | {DATE} |

## By Module

<!-- Auto-updated by hook. Format: - [module]: N lessons -->

## By Tag

<!-- Auto-updated by hook. Format: - [tag]: N lessons -->

## Recent Lessons

<!-- Auto-updated by hook. List 10 most recent lessons -->

---

_This index is auto-managed. Edit this file to add module/tag descriptions._
`;

const BUG_LESSON_TEMPLATE = `---
title: "【Bug】<issue-slug>"
status: draft
date: {DATE}
tags:
  - untagged
modules:
  - unspecified
---

## Issue Title

<Clear, descriptive title>

## Symptom

<What was observed - error message, incorrect behavior, etc.>

## Root Cause

<Why it happened - the actual bug>

## Solution

<How it was fixed>

## Prevention

<How to avoid this in the future>

## Related Files / Modules

<List affected files>

## Reusable Lesson

<What general principle can be extracted?>

## Search Keywords

<terms that would help find this lesson later>
`;

const TASK_PRECHECK_TEMPLATE = `# Task Precheck

> Fill this in before starting any implementation task.

## Task Overview

**Task:** <What are you implementing?>
**Module:** <Which module does this affect?>
**Type:** <feature / bugfix / refactor / docs>

---

## Historical Lessons (from .harness)

**Related lessons found:** <N>

<!-- List relevant lesson titles and their key takeaways -->

---

## Risks & Constraints

<!-- What could go wrong? What has caused problems in similar tasks before? -->

---

## Implementation Plan

1. <step 1>
2. <step 2>
3. <step 3>

---

## Edge Cases to Consider

<!-- Null, empty, loading, error states, boundary conditions -->

---

## Verification Plan

<!-- How will you verify the solution works? -->
`;

/**
 * Initialize .harness directory structure for a project.
 */
function initializeHarness(projectRoot) {
  const dirs = [
    '.harness/lessons/backend',
    '.harness/lessons/frontend',
    '.harness/lessons/database',
    '.harness/lessons/infrastructure',
    '.harness/tags',
    '.harness/templates',
  ];

  const files = [
    { name: '.harness/README.md', content: README_TEMPLATE },
    {
      name: '.harness/INDEX.md',
      content: INDEX_TEMPLATE.replace('{DATE}', new Date().toISOString().split('T')[0]),
    },
    {
      name: '.harness/templates/bug-lesson-template.md',
      content: BUG_LESSON_TEMPLATE.replace('{DATE}', new Date().toISOString().split('T')[0]),
    },
    {
      name: '.harness/templates/task-precheck-template.md',
      content: TASK_PRECHECK_TEMPLATE,
    },
  ];

  const created = [];
  const errors = [];

  for (const dir of dirs) {
    const fullPath = path.join(projectRoot, dir);
    try {
      fs.mkdirSync(fullPath, { recursive: true });
      created.push(dir);
    } catch (err) {
      errors.push(`mkdir ${dir}: ${err.message}`);
    }
  }

  for (const file of files) {
    const fullPath = path.join(projectRoot, file.name);
    try {
      if (!fs.existsSync(fullPath)) {
        fs.writeFileSync(fullPath, file.content, 'utf-8');
        created.push(file.name);
      }
    } catch (err) {
      errors.push(`write ${file.name}: ${err.message}`);
    }
  }

  return { created, errors };
}

function buildReminder(harnessPath, projectName) {
  const rel = getRelativePath(harnessPath);
  const lines = [
    '',
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
    `📚 Harness 知识库提醒`,
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
    `项目: ${projectName}`,
    '',
    '在开始实现任务前，请确保已：',
    `1. 读取 .harness/INDEX.md（主导航）`,
    `2. 读取相关 tags 文件`,
    `3. 按模板输出 Task Precheck（历史经验 × 当前风险）`,
    '',
    `知识库: ${rel}`,
    '提示：修 Bug 后必须按模板写 lesson 并更新 INDEX。',
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
    '',
  ];
  return lines.join('\n');
}

function buildInitMessage(projectRoot, result) {
  const rel = getRelativePath(projectRoot);
  const lines = [
    '',
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
    `📚 .harness 知识库已初始化`,
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
    `项目: ${rel}`,
    `创建了 ${result.created.length} 个文件/目录`,
    '',
    '已创建：',
    ...result.created.map((p) => `  + ${p}`),
    '',
    '接下来：',
    '1. 读取 .harness/INDEX.md 了解项目结构',
    '2. 读取 .harness/templates/task-precheck-template.md',
    '3. 开始工作时输出 Task Precheck',
    '4. 修 Bug 后写 lesson 沉淀经验',
    '',
    '⚠️ 知识库会越用越智能，请养成沉淀习惯',
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
    '',
  ];
  return lines.join('\n');
}

function handlePreToolUse(input) {
  const cwd = input.cwd || process.cwd();
  if (!path.isAbsolute(cwd)) return;

  const harnessPath = findHarnessDir(cwd);
  const projectRoot = findProjectRoot(cwd);
  const projectName = projectRoot ? path.basename(projectRoot) : path.basename(cwd);

  const toolName = input.tool_name || '';
  const EDIT_TOOLS = new Set(['Edit', 'Write', 'Patch']);
  if (!EDIT_TOOLS.has(toolName)) return;

  const sessionKey = 'HARNESS_HOOK_DONE';
  if (process.env[sessionKey]) return;

  let message = '';

  if (!harnessPath) {
    // Initialize .harness for this project
    if (projectRoot) {
      process.env[sessionKey] = '1';
      const result = initializeHarness(projectRoot);
      message = buildInitMessage(projectRoot, result);
      sendHookResponse('PreToolUse', message);
    }
  } else {
    // Already has .harness, remind to use it
    process.env[sessionKey] = '1';
    message = buildReminder(harnessPath, projectName);
    sendHookResponse('PreToolUse', message);
  }
}

function sendHookResponse(hookEventName, message) {
  console.log(
    JSON.stringify({
      hookSpecificOutput: { hookEventName, additionalContext: message },
    }),
  );
}

function main() {
  try {
    const input = readInput();
    const handler = handlers[input.hook_event_name || ''];
    if (handler) handler(input);
  } catch (err) {
    if (process.env.HARNESS_DEBUG) {
      console.error('Harness hook error:', err.message || ''.slice(0, 200));
    }
  }
}

const handlers = {
  PreToolUse: handlePreToolUse,
};

main();
