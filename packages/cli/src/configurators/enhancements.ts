/**
 * Enhancement configurator for GitNexus, Superpowers, and gstack integrations.
 *
 * These are NOT separate AI platforms — they are enhancements layered on top
 * of the base Claude Code configuration. When enabled via --gitnexus,
 * --superpowers, --gstack, or --all flags, this configurator copies additional
 * templates and updates config.yaml.
 */
import { execSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { writeFile, ensureDir } from "../utils/file-writer.js";
import { DIR_NAMES } from "../constants/paths.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export interface Enhancements {
  gitnexus: boolean;
  superpowers: boolean;
  gstack: boolean;
}

// =============================================================================
// Dependency Detection & Auto-Installation
// =============================================================================

const HOME = os.homedir();

/**
 * Run a shell command, returning true on success.
 */
function run(cmd: string, opts?: { cwd?: string }): boolean {
  try {
    execSync(cmd, { stdio: "pipe", timeout: 120_000, ...opts });
    return true;
  } catch {
    return false;
  }
}

/**
 * Check if Superpowers plugin is installed.
 */
function isSuperpowersInstalled(): boolean {
  // Check plugin cache
  const cacheDir = path.join(
    HOME,
    ".claude",
    "plugins",
    "cache",
    "claude-plugins-official",
    "superpowers",
  );
  if (fs.existsSync(cacheDir)) return true;

  // Check installed_plugins.json
  const installedPath = path.join(
    HOME,
    ".claude",
    "plugins",
    "installed_plugins.json",
  );
  if (fs.existsSync(installedPath)) {
    try {
      const data = JSON.parse(fs.readFileSync(installedPath, "utf-8"));
      return Object.keys(data).some((k) => k.includes("superpowers"));
    } catch {
      // ignore parse errors
    }
  }
  return false;
}

/**
 * Check if gstack skills are installed.
 */
function isGstackInstalled(): boolean {
  const skillDir = path.join(HOME, ".claude", "skills", "gstack");
  return (
    fs.existsSync(path.join(skillDir, "SKILL.md")) ||
    fs.existsSync(path.join(skillDir, "package.json"))
  );
}

/**
 * Check if GitNexus index exists for the project.
 */
function isGitnexusIndexed(cwd: string): boolean {
  return fs.existsSync(path.join(cwd, ".gitnexus", "meta.json"));
}

/**
 * Check if GitNexus MCP server is registered in ~/.claude.json.
 */
function isGitnexusMcpRegistered(): boolean {
  const claudeJsonPath = path.join(HOME, ".claude.json");
  if (!fs.existsSync(claudeJsonPath)) return false;
  try {
    const data = JSON.parse(fs.readFileSync(claudeJsonPath, "utf-8"));
    return !!data.mcpServers?.gitnexus;
  } catch {
    return false;
  }
}

/**
 * Register GitNexus MCP server in ~/.claude.json via `npx gitnexus setup`.
 */
function registerGitnexusMcp(): boolean {
  console.log("  Registering GitNexus MCP server...");
  const ok = run("npx gitnexus setup --host claude");
  if (ok) {
    console.log("  ✓ GitNexus MCP registered");
  } else {
    console.log(
      "  ⚠ Could not register GitNexus MCP. Run manually: npx gitnexus setup --host claude",
    );
  }
  return ok;
}

/**
 * Auto-install Superpowers plugin via Claude Code CLI.
 */
function installSuperpowers(): boolean {
  console.log("  Installing Superpowers plugin...");
  const ok = run("claude plugin install superpowers@claude-plugins-official");
  if (ok) {
    console.log("  ✓ Superpowers plugin installed");
  } else {
    console.log(
      "  ⚠ Could not auto-install Superpowers. Install manually: claude plugin install superpowers@claude-plugins-official",
    );
  }
  return ok;
}

/**
 * Auto-install gstack skills via git clone + setup.
 */
function installGstack(): boolean {
  const targetDir = path.join(HOME, ".claude", "skills", "gstack");

  // Already exists but incomplete? Skip.
  if (fs.existsSync(targetDir)) {
    console.log(
      "  ⚠ gstack directory exists but incomplete. Try: cd ~/.claude/skills/gstack && ./setup --host claude",
    );
    return false;
  }

  console.log("  Cloning gstack...");
  if (!run(`git clone https://github.com/garrytan/gstack.git "${targetDir}"`)) {
    console.log("  ⚠ Could not clone gstack. Install manually:");
    console.log(
      "    git clone https://github.com/garrytan/gstack.git ~/.claude/skills/gstack",
    );
    console.log("    cd ~/.claude/skills/gstack && ./setup --host claude");
    return false;
  }

  console.log("  Running gstack setup...");
  if (!run("./setup --host claude", { cwd: targetDir })) {
    console.log(
      "  ⚠ gstack setup failed. You may need bun installed. Run manually:",
    );
    console.log("    cd ~/.claude/skills/gstack && ./setup --host claude");
    return false;
  }

  console.log("  ✓ gstack skills installed");
  return true;
}

/**
 * Auto-index project with GitNexus.
 */
function indexGitnexus(cwd: string): boolean {
  console.log(
    "  Indexing project with GitNexus (first run may take a moment)...",
  );
  const ok = run("npx gitnexus analyze", { cwd });
  if (ok) {
    console.log("  ✓ GitNexus index created");
  } else {
    console.log(
      "  ⚠ GitNexus indexing failed. Run manually: npx gitnexus analyze",
    );
  }
  return ok;
}

/**
 * Check and install all required dependencies before configuring enhancements.
 */
function ensureDependencies(cwd: string, enhancements: Enhancements): void {
  console.log("");
  console.log("🔍 Checking dependencies...");

  if (enhancements.superpowers && !isSuperpowersInstalled()) {
    console.log("  ⚠ Superpowers plugin not found.");
    installSuperpowers();
  } else if (enhancements.superpowers) {
    console.log("  ✓ Superpowers plugin found");
  }

  if (enhancements.gstack && !isGstackInstalled()) {
    console.log("  ⚠ gstack skills not found.");
    installGstack();
  } else if (enhancements.gstack) {
    console.log("  ✓ gstack skills found");
  }

  if (enhancements.gitnexus) {
    // Check MCP registration
    if (!isGitnexusMcpRegistered()) {
      registerGitnexusMcp();
    } else {
      console.log("  ✓ GitNexus MCP registered");
    }

    // Check project index
    if (!isGitnexusIndexed(cwd)) {
      indexGitnexus(cwd);
    } else {
      console.log("  ✓ GitNexus index found");
    }
  }

  // Warn about consensus-debate env vars
  if (enhancements.gitnexus) {
    const hasApiKey = !!process.env.CONSENSUS_DEBATE_API_KEY;
    const hasEndpoint = !!process.env.CONSENSUS_DEBATE_ENDPOINT;
    if (!hasApiKey || !hasEndpoint) {
      console.log(
        "  ⚠ consensus-debate env vars not set (CONSENSUS_DEBATE_API_KEY, CONSENSUS_DEBATE_ENDPOINT).",
      );
      console.log(
        "    Multi-model review will use empty placeholders. Set these in your shell or ~/.claude/settings.json env section.",
      );
    } else {
      console.log("  ✓ consensus-debate env vars found");
    }
  }

  console.log("");
}

// =============================================================================
// Enhancement Configuration
// =============================================================================

/**
 * Configure enhancement integrations for the current project.
 * Checks dependencies first, then copies templates and updates config.yaml.
 */
export async function configureEnhancements(
  cwd: string,
  enhancements: Enhancements,
): Promise<void> {
  // Check and auto-install dependencies before configuring
  ensureDependencies(cwd, enhancements);

  if (enhancements.gitnexus) {
    await configureGitnexus(cwd);
    await configureConsensusDebate(cwd);
  }
  if (enhancements.superpowers) {
    await configureSuperpowers(cwd);
  }
  if (enhancements.gstack) {
    await configureGstack(cwd);
  }
  updateConfigYaml(cwd, enhancements);
}

/**
 * Configure GitNexus integration:
 * - Copy gitnexus hooks to .claude/hooks/
 * - Copy enhanced agents to .claude/agents/
 * - Overwrite settings.json with full version (includes global hooks)
 * - Overwrite AGENTS.md with full version (includes workflow + routing table)
 */
async function configureGitnexus(cwd: string): Promise<void> {
  const claudeHooksDir = path.join(cwd, ".claude", "hooks");
  const claudeAgentsDir = path.join(cwd, ".claude", "agents");

  ensureDir(claudeHooksDir);
  ensureDir(claudeAgentsDir);

  // Copy gitnexus hooks (includes global hooks: gitnexus-hook.cjs, auto-approve-hook.cjs, harness-hook.cjs)
  const hooksSource = getEnhancementsDir("gitnexus", "hooks");
  if (fs.existsSync(hooksSource)) {
    for (const file of fs.readdirSync(hooksSource)) {
      const src = path.join(hooksSource, file);
      const dest = path.join(claudeHooksDir, file);
      const content = fs.readFileSync(src, "utf-8");
      await writeFile(dest, content, { executable: file.endsWith(".py") });
    }
  }

  // Copy enhanced agents (overwrite base versions)
  const agentsSource = getEnhancementsDir("gitnexus", "agents");
  if (fs.existsSync(agentsSource)) {
    for (const file of fs.readdirSync(agentsSource)) {
      const src = path.join(agentsSource, file);
      const dest = path.join(claudeAgentsDir, file);
      const content = fs.readFileSync(src, "utf-8");
      await writeFile(dest, content);
    }
  }

  // Overwrite settings.json with full version (includes global hooks registration)
  const fullSettingsSource = getEnhancementsDir("gitnexus", "settings.json");
  if (fs.existsSync(fullSettingsSource)) {
    const dest = path.join(cwd, ".claude", "settings.json");
    const content = fs.readFileSync(fullSettingsSource, "utf-8");
    await writeFile(dest, content);
  }

  // Overwrite AGENTS.md with full version (includes 7-stage workflow + routing table)
  const fullAgentsSource = getEnhancementsDir("gitnexus", "agents.md");
  if (fs.existsSync(fullAgentsSource)) {
    const dest = path.join(cwd, "AGENTS.md");
    const content = fs.readFileSync(fullAgentsSource, "utf-8");
    await writeFile(dest, content);
  }

  // Create .claude-approve marker for auto-approve hook
  const approveMarker = path.join(cwd, ".claude-approve");
  if (!fs.existsSync(approveMarker)) {
    await writeFile(approveMarker, "");
    console.log("  ✓ Created .claude-approve marker (auto-approve enabled)");
  }

  console.log("  ✓ GitNexus integration configured");
}

/**
 * Configure consensus-debate skill:
 * - Copy scripts (run_debate.py, review_wrapper.py) to .claude/skills/consensus-debate/scripts/
 * - Generate models.json template with environment variable placeholders
 */
async function configureConsensusDebate(cwd: string): Promise<void> {
  const scriptsDir = path.join(
    cwd,
    ".claude",
    "skills",
    "consensus-debate",
    "scripts",
  );
  ensureDir(scriptsDir);

  const scriptsSource = getEnhancementsDir("consensus-debate", "scripts");
  if (fs.existsSync(scriptsSource)) {
    for (const file of fs.readdirSync(scriptsSource)) {
      // Skip models.json — we generate it from environment variables
      if (file === "models.json") continue;
      const src = path.join(scriptsSource, file);
      const dest = path.join(scriptsDir, file);
      const content = fs.readFileSync(src, "utf-8");
      await writeFile(dest, content, { executable: file.endsWith(".py") });
    }
  }

  // Generate models.json with environment variable placeholders
  // Users must set CONSENSUS_DEBATE_API_KEY and CONSENSUS_DEBATE_ENDPOINT
  // in their ~/.claude/settings.json env section or shell environment
  const modelsJson = generateModelsJsonTemplate();
  await writeFile(path.join(scriptsDir, "models.json"), modelsJson);

  // Copy SKILL.md if it exists
  const skillSource = getEnhancementsDir("consensus-debate", "skills");
  if (fs.existsSync(skillSource)) {
    const skillDest = path.join(cwd, ".claude", "skills", "consensus-debate");
    ensureDir(skillDest);
    for (const file of fs.readdirSync(skillSource)) {
      const src = path.join(skillSource, file);
      const dest = path.join(skillDest, file);
      const content = fs.readFileSync(src, "utf-8");
      await writeFile(dest, content);
    }
  }

  console.log("  ✓ consensus-debate skill configured");
  console.log(
    "    ⚠ Set CONSENSUS_DEBATE_API_KEY and CONSENSUS_DEBATE_ENDPOINT in environment to enable multi-model review",
  );
}

/**
 * Generate models.json template with env var placeholders.
 * Values are read from environment at runtime by run_debate.py.
 */
function generateModelsJsonTemplate(): string {
  // Check if env vars are set — if so, use them; otherwise use placeholders
  const apiKey = process.env.CONSENSUS_DEBATE_API_KEY ?? "";
  const endpoint = process.env.CONSENSUS_DEBATE_ENDPOINT ?? "";
  const judgeModel =
    process.env.CONSENSUS_DEBATE_JUDGE_MODEL ?? "your-judge-model";
  const participantModel =
    process.env.CONSENSUS_DEBATE_PARTICIPANT_MODEL ?? "your-participant-model";
  const participantModel2 =
    process.env.CONSENSUS_DEBATE_PARTICIPANT_MODEL_2 ?? participantModel;

  return JSON.stringify(
    [
      {
        name: "judge",
        endpoint,
        api_key: apiKey,
        model: judgeModel,
        role: "judge",
        protocol: "openai",
      },
      {
        name: "participant-1",
        endpoint,
        api_key: apiKey,
        model: participantModel,
        role: "participant",
        protocol: "openai",
      },
      {
        name: "participant-2",
        endpoint,
        api_key: apiKey,
        model: participantModel2,
        role: "participant",
        protocol: "openai",
      },
    ],
    null,
    2,
  );
}

/**
 * Configure Superpowers command aliases.
 * Creates lightweight .md files in .claude/commands/trellis/ that route to
 * the already-installed Superpowers Claude Code plugin skills.
 */
async function configureSuperpowers(cwd: string): Promise<void> {
  const commandsDir = path.join(cwd, ".claude", "commands", "trellis");
  ensureDir(commandsDir);

  const commandsSource = getEnhancementsDir(
    "superpowers",
    "commands",
    "trellis",
  );
  if (fs.existsSync(commandsSource)) {
    for (const file of fs.readdirSync(commandsSource)) {
      const src = path.join(commandsSource, file);
      const dest = path.join(commandsDir, file);
      const content = fs.readFileSync(src, "utf-8");
      await writeFile(dest, content);
    }
  }

  console.log("  ✓ Superpowers command aliases configured");
}

/**
 * Configure gstack command aliases.
 * Creates lightweight .md files in .claude/commands/trellis/ that route to
 * the already-installed gstack skills at ~/.claude/skills/gstack/.
 */
async function configureGstack(cwd: string): Promise<void> {
  const commandsDir = path.join(cwd, ".claude", "commands", "trellis");
  ensureDir(commandsDir);

  const commandsSource = getEnhancementsDir("gstack", "commands", "trellis");
  if (fs.existsSync(commandsSource)) {
    for (const file of fs.readdirSync(commandsSource)) {
      const src = path.join(commandsSource, file);
      const dest = path.join(commandsDir, file);
      const content = fs.readFileSync(src, "utf-8");
      await writeFile(dest, content);
    }
  }

  console.log("  ✓ gstack command aliases configured");
}

/**
 * Update .trellis/config.yaml with enhancement settings.
 * Non-destructive: only adds sections, doesn't remove user customizations.
 */
function updateConfigYaml(cwd: string, enhancements: Enhancements): void {
  const configPath = path.join(cwd, DIR_NAMES.WORKFLOW, "config.yaml");

  let content = "";
  try {
    content = fs.readFileSync(configPath, "utf-8");
  } catch {
    return; // No config file yet
  }

  const additions: string[] = [];

  // GitNexus section
  if (enhancements.gitnexus && !content.includes("gitnexus:")) {
    additions.push(`
#-------------------------------------------------------------------------------
# GitNexus Knowledge Graph Integration
#-------------------------------------------------------------------------------
gitnexus:
  enabled: true
  auto_index: true           # Auto-check index status on session start
  impact_before_edit: true   # Run impact analysis before file edits
`);
  }

  // Skills section
  if (
    (enhancements.superpowers || enhancements.gstack) &&
    !content.includes("skills:")
  ) {
    const superpowersEnabled = enhancements.superpowers ? "true" : "false";
    const gstackEnabled = enhancements.gstack ? "true" : "false";
    additions.push(`
#-------------------------------------------------------------------------------
# Skills Routing (Superpowers & gstack)
#-------------------------------------------------------------------------------
skills:
  superpowers:
    enabled: ${superpowersEnabled}
    # Superpowers is a Claude Code plugin. Command aliases in
    # .claude/commands/trellis/ route to superpowers skills.
  gstack:
    enabled: ${gstackEnabled}
    # gstack is installed as Claude Code skills at ~/.claude/skills/gstack/.
    # Command aliases in .claude/commands/trellis/ route to gstack skills.
`);
  }

  if (additions.length > 0) {
    content += additions.join("\n");
    fs.writeFileSync(configPath, content, "utf-8");
  }
}

/**
 * Get the path to enhancement template files.
 * Template files are in src/templates/enhancements/{group}/{...subpath}
 */
function getEnhancementsDir(group: string, ...subpath: string[]): string {
  // In development: src/templates/enhancements/
  // In production (dist): dist/templates/enhancements/
  const candidates = [
    path.resolve(
      __dirname,
      "..",
      "templates",
      "enhancements",
      group,
      ...subpath,
    ),
    path.resolve(
      __dirname,
      "..",
      "..",
      "src",
      "templates",
      "enhancements",
      group,
      ...subpath,
    ),
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  // Return first candidate even if it doesn't exist (will be handled gracefully)
  return candidates[0];
}
