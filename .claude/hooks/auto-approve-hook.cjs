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
  // rm variants (including encoding bypasses)
  /rm\s+(-rf|-r\s+-f|-f\s+-r|-fR|-Rf|--recursive\s+--force|--force\s+--recursive)\s+([\/~]|\*\s*$|\.\s*$|\.\/)/,
  /rm\s+-r\s+([\/~]|\.\s*$)/, // rm -r without -f on absolute/relative paths
  /\$'[^']*\\(x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|[0-7]{3})/, // $'\x72' / $'r' / $'\162' encoding bypass
  /\$\{[!#][a-zA-Z_]*\}/, // indirect/reference variables: ${!var}, ${#var}
  /\$\{(BASH_COMMAND|SHELLOPTS|BASH_SUBSHELL|IFS|FUNCNAME|OLDPWD)\b[^}]*\}/, // dangerous shell variables
  /:\s*>?\s*\/dev\/null/,
  // pipe to shell
  /\|\s*(\/?(usr\/)?bin\/)?(sh|bash|zsh|fish)\b(\s+-c|\s+--)?/,
  /eval\s+\$/,
  /\$\(.*\)\s*\|\s*(sh|bash)/,
  /curl.*\|\s*(sh|bash)/,
  /wget.*\|\s*(sh|bash)/,
  /chmod\s+777/,
  /git\s+push\s+.*(?<!-with-lease)(?<!-if-includes)\s--force(?:\s|$)/,
  /dd\s+if=/,
  // redirect to sensitive paths
  />\s*\/etc\//,
  />\s*~\/\.ssh\//,
  // backtick command substitution with special chars
  /`[^`]*[\s|;&$><][^`]*`/,
  // $() subshell with dangerous commands (handles nested parens via .* greedy)
  /\$\(.*\b(rm|dd|mkfs|chmod|chown|mv|cat|sh|bash)\b/,
  // interpreter -e/-c flag (code execution)
  /\b(node|python|python3|perl|ruby)\s+(-e|-c)\s/,
  /base64\s+-d\s*\|.*\b(sh|bash)/,
  // heredoc — single-char and longer delimiters
  /<<\s*['"]?[A-Za-z_]{1,}/,
  // privilege escalation
  /\bsudo\s+.*\b(rm|dd|mkfs|chmod|chown)\b/,
  /\bxargs\s+.*(sh|bash|rm|chmod|chown)\b/,
  /\bfind\b.*-exec\s+/,
  /\bawk\s+.*\b(system|exec)\s*\(/,
  // source / dot operator executing scripts (allows quoted paths)
  /(?:^|&&|\|\||;|`)\s*(?:source|\.)\s+["']?[~/\$][^\s;|&"']*/, // source / dot operator
  /(?:^|&&|\|\||;|`)\s*exec\s+/, // exec replacing process
  /\btee\s+.*(~\/\.|\/etc\/|\/\.ssh\/)/, // tee writing to sensitive paths
];

/**
 * Sensitive file paths that should never be written via Edit/Write/Patch.
 */
const SENSITIVE_PATHS = [
  /\/\.ssh\//,
  /\/id_(rsa|ed25519|ecdsa|dsa)$/,
  /\/\.bashrc$/,
  /\/\.zshrc$/,
  /\/\.profile$/,
  /\/\.bash_profile$/,
  /\/\.gitconfig$/,
  /^\/etc\//,
  /\/\.gnupg\//,
  /\/\.config\/gh\/hosts\.yml$/,
  /\/\.env$/,
  /\/\.env\./,
  /\/credentials$/,
  /\/secrets?\//,
  /\/\.aws\//,
  /\/\.npmrc$/,
];

function isSensitivePath(filePath) {
  if (!filePath) return false;
  const expanded = filePath.replace(/^~/, process.env.HOME || '');
  const resolved = path.resolve(expanded);
  for (const pattern of SENSITIVE_PATHS) {
    if (pattern.test(resolved)) return true;
  }
  return false;
}

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
    auditLog(projectRoot, { event: 'deny', tool: toolName, reason: 'dangerous_command', cmd: command.slice(0, 200) });
    sendDeny('Dangerous command detected. Manual review required.');
    return;
  }

  // Check if tool is in our approval list
  if (!PERMISSION_TOOLS.has(toolName)) return;

  // Auto-approve!
  auditLog(projectRoot, { event: 'allow', tool: toolName, via: 'PermissionRequest' });
  sendAllow();
}

function handlePreToolUse(input) {
  const cwd = input.cwd || process.cwd();
  if (!path.isAbsolute(cwd)) return;

  const projectRoot = findProjectRoot(cwd);
  if (!isApproved(projectRoot)) return;

  const toolName = input.tool_name || '';
  const toolInput = input.tool_input || {};
  const command = toolInput.command || '';

  // Never auto-approve dangerous commands (applies to all tools, especially Bash)
  // Note: Bash danger checks also run in handlePermissionRequest (which covers the Bash tool specifically)
  if (isDangerous(command)) {
    auditLog(projectRoot, { event: 'deny', tool: toolName, reason: 'dangerous_command', cmd: command.slice(0, 200) });
    return;
  }

  // Only auto-approve Edit/Write/Patch file modifications
  if (toolName !== 'Edit' && toolName !== 'Write' && toolName !== 'Patch') return;

  const filePath = toolInput.file_path || toolInput.path || '';
  if (isSensitivePath(filePath)) {
    auditLog(projectRoot, { event: 'deny', tool: toolName, reason: 'sensitive_path', path: filePath.slice(0, 200) });
    return;
  }

  // Auto-approve safe file modifications
  auditLog(projectRoot, { event: 'allow', tool: toolName, file: filePath.slice(0, 200), via: 'PreToolUse' });
  sendAllowDecision();
}

function sendAllow() {
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

function sendAllowDecision() {
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

/**
 * Append audit entry to .claude/auto-approve-audit.jsonl
 */
function auditLog(projectRoot, entry) {
  if (!projectRoot) return;
  try {
    const logFile = path.join(projectRoot, '.claude', 'auto-approve-audit.jsonl');
    const logDir = path.dirname(logFile);
    if (!fs.existsSync(logDir)) return;
    // Rotate if over 5MB
    try {
      const stat = fs.statSync(logFile);
      if (stat.size > 5_000_000) {
        fs.renameSync(logFile, logFile + '.1');
      }
    } catch { /* file may not exist yet */ }
    const line = JSON.stringify({
      ts: new Date().toISOString(),
      ...entry,
    }) + '\n';
    fs.appendFileSync(logFile, line, { flag: 'a' });
  } catch { /* audit logging is best-effort */ }
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
