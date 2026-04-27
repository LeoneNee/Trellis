/**
 * Enhancement configurator for GitNexus, Superpowers, and gstack integrations.
 *
 * These are NOT separate AI platforms — they are enhancements layered on top
 * of the base Claude Code configuration. When enabled via --gitnexus,
 * --superpowers, --gstack, or --all flags, this configurator copies additional
 * templates and updates config.yaml.
 */
import fs from "node:fs";
import path from "node:path";
import { writeFile, ensureDir } from "../utils/file-writer.js";
import { DIR_NAMES } from "../constants/paths.js";

export interface Enhancements {
  gitnexus: boolean;
  superpowers: boolean;
  gstack: boolean;
}

/**
 * Configure enhancement integrations for the current project.
 * Copies templates and updates config.yaml based on which enhancements are enabled.
 */
export async function configureEnhancements(
  cwd: string,
  enhancements: Enhancements,
): Promise<void> {
  if (enhancements.gitnexus) {
    await configureGitnexus(cwd);
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
 */
async function configureGitnexus(cwd: string): Promise<void> {
  const claudeHooksDir = path.join(cwd, ".claude", "hooks");
  const claudeAgentsDir = path.join(cwd, ".claude", "agents");

  ensureDir(claudeHooksDir);
  ensureDir(claudeAgentsDir);

  // Copy gitnexus hooks
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

  console.log("  ✓ GitNexus integration configured");
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
