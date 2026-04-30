#!/usr/bin/env node
/**
 * Auto-Approve Hook for Claude Code
 *
 * PermissionRequest — when a permission dialog appears:
 *   - If .claude-approve marker exists in project → auto-allow
 *   - If no marker → defer to normal flow (ask user)
 *
 * Also supports PreToolUse for tools that don't show dialogs.
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
 * Find project root by walking up from startDir.
 */
function findProjectRoot(startDir) {
  let dir = startDir || process.cwd();
  for (let i = 0; i < 8; i++) {
    const approve = path.join(dir, '.claude-approve');
    if (fs.existsSync(approve)) return dir;
    const git = path.join(dir, '.git');
    if (fs.existsSync(git)) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

/**
 * Check if project has auto-approve marker.
 */
function isApproved(projectRoot) {
  if (!projectRoot) return false;
  const marker = path.join(projectRoot, '.claude-approve');
  return fs.existsSync(marker);
}

/**
 * Tools that require permission in Claude Code.
 */
const PERMISSION_TOOLS = new Set([
  'Bash',
  'Edit',
  'Write',
  'Read',
  'Glob',
  'Grep',
  'Agent',
  'WebFetch',
  'WebSearch',
]);

/**
 * Dangerous patterns that should NEVER be auto-approved.
 */
const DANGEROUS_PATTERNS = [
  /rm\s+(-rf|-r\s+-f|-f\s+-r)\s+([\/~]|\/)/,
  /:\s*>?\s*\/dev\/null/,
  /\|\s*(sh|bash|zsh|fish)\s*$/,
  /eval\s+\$/,
  /\$\(.*\)\s*\|\s*(sh|bash)/,
  /curl.*\|\s*(sh|bash)/,
  /wget.*\|\s*(sh|bash)/,
  /chmod\s+777/,
  /git\s+push\s+.*--force/,
  /dd\s+if=/,
  />\s*\/etc\//,
  />\s*~\/\.ssh\//,
];

function isDangerous(command) {
  for (const pattern of DANGEROUS_PATTERNS) {
    if (pattern.test(command)) return true;
  }
  return false;
}

/**
 * Handle PermissionRequest event.
 * This fires when a permission dialog is about to be shown.
 * Return allow/deny to control the dialog.
 */
function handlePermissionRequest(input) {
  const cwd = input.cwd || process.cwd();
  if (!path.isAbsolute(cwd)) return;

  const projectRoot = findProjectRoot(cwd);
  if (!isApproved(projectRoot)) return;

  const toolName = input.tool_name || '';
  const toolInput = input.tool_input || {};
  const command = toolInput.command || '';

  // Never auto-approve dangerous commands
  if (isDangerous(command)) {
    sendDeny('Dangerous command detected. Manual review required.');
    return;
  }

  // Check if tool is in our approval list
  if (!PERMISSION_TOOLS.has(toolName)) return;

  // Auto-approve!
  sendAllow(projectRoot);
}

function handlePreToolUse(input) {
  const cwd = input.cwd || process.cwd();
  if (!path.isAbsolute(cwd)) return;

  const projectRoot = findProjectRoot(cwd);
  if (!isApproved(projectRoot)) return;

  const toolName = input.tool_name || '';
  const toolInput = input.tool_input || {};
  const command = toolInput.command || '';

  // Never auto-approve dangerous commands
  if (isDangerous(command)) return;

  // Only auto-approve Edit/Write/Patch for now (most common)
  if (toolName !== 'Edit' && toolName !== 'Write' && toolName !== 'Patch') return;

  // Auto-approve file modifications
  sendAllowDecision(projectRoot);
}

function getRelativePath(targetPath) {
  const home = require('os').homedir();
  if (targetPath && targetPath.startsWith(home)) {
    return targetPath.replace(home, '~');
  }
  return targetPath || 'unknown';
}

function sendAllow(projectRoot) {
  console.log(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PermissionRequest',
        decision: {
          behavior: 'allow',
        },
      },
    }),
  );
}

function sendAllowDecision(projectRoot) {
  console.log(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'allow',
        permissionDecisionReason: 'Auto-approved via .claude-approve marker',
      },
    }),
  );
}

function sendDeny(reason) {
  console.log(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PermissionRequest',
        decision: {
          behavior: 'deny',
          message: reason,
          interrupt: true,
        },
      },
    }),
  );
}

function main() {
  try {
    const input = readInput();
    const eventName = input.hook_event_name || '';

    if (eventName === 'PermissionRequest') {
      handlePermissionRequest(input);
    } else if (eventName === 'PreToolUse') {
      handlePreToolUse(input);
    }
  } catch (err) {
    if (process.env.AUTO_APPROVE_DEBUG) {
      console.error('Auto-approve hook error:', (err.message || '').slice(0, 200));
    }
  }
}

main();
