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
const crypto = require('crypto');

function readInput() {
  try {
    const data = fs.readFileSync(0, 'utf-8');
    if (data.length > 1_000_000) return {}; // reject oversized input
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
 * Generate the expected approve token for a given project root.
 * Users must put this exact string in their .claude-approve file.
 */
function generateApproveToken(projectRoot) {
  const normalized = path.resolve(projectRoot);
  return 'approve-' + crypto.createHash('sha256').update(normalized).digest('hex').slice(0, 16);
}

/**
 * Check if project has auto-approve marker with valid content.
 */
function isApproved(projectRoot) {
  if (!projectRoot) return false;
  const marker = path.join(projectRoot, '.claude-approve');
  if (!fs.existsSync(marker)) return false;
  try {
    const content = fs.readFileSync(marker, 'utf-8').trim();
    if (!content) return false; // empty file not accepted
    // Accept if content matches expected token (SHA256 of project root path)
    const expected = generateApproveToken(projectRoot);
    return content === expected;
  } catch {
    return false;
  }
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
  /rm\s+(-rf|-r\s+-f|-f\s+-r|-fR|-Rf|--recursive\s+--force|--force\s+--recursive)\s+([\/~]|\*\s*$|\.\s*$)/,
  /:\s*>?\s*\/dev\/null/,
  /\|\s*(\/?(usr\/)?bin\/)?(sh|bash|zsh|fish)\b(\s+-c|\s+--)?/,
  /eval\s+\$/,
  /\$\(.*\)\s*\|\s*(sh|bash)/,
  /curl.*\|\s*(sh|bash)/,
  /wget.*\|\s*(sh|bash)/,
  /chmod\s+777/,
  /git\s+push\s+.*--force/,
  /dd\s+if=/,
  />\s*\/etc\//,
  />\s*~\/\.ssh\//,
  /`[^`]*[\s|;&$><][^`]*`/,
  /\$\([^)]*\b(rm|dd|mkfs|chmod|chown|mv|cat)\b/,
  /\b(node|python|python3|perl|ruby)\s+(-e|-c)\s/,
  /base64\s+-d\s*\|.*\b(sh|bash)/,
  /<<\s*['"]?[A-Z_]{2,}/,
  /\bsudo\s+.*\b(rm|dd|mkfs|chmod|chown)\b/,
  /\bxargs\s+.*(sh|bash|rm|chmod|chown)\b/,
  /\bfind\b.*-exec\s+/,
  /\bawk\s+.*\b(system|exec)\s*\(/,
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
