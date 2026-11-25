# Deployment

Skills run directly from a clone of this repo (`.claude/skills/` is picked up by Claude Code when it is the working directory). Skills built to run elsewhere are installed with `scripts/deploy.py`, either **per project** or **globally**, in the convention of the target AI agent.

## Declaring where a skill may go

`install:` in SKILL.md frontmatter:

| Value | Meaning |
|-------|---------|
| (absent) | Repo-only. Never deployed |
| `project` | Installable into a project, for skills run from another project (e.g. wiki skills) |
| `global` | Installable into the user's global skills (e.g. screenshot reading) |
| `global,project` | Either |

A skill must declare the requested scope to be deployed, even when named with `--skill`; otherwise deploy refuses with an error. Current declarations are in the `install` column of [skills](skills.md), the single source of truth. `python3 scripts/deploy.py --scope global --agent claude --dry-run` lists what a global deploy would install.

## Usage

```bash
python3 scripts/deploy.py --agent claude  --scope project --project ~/work/myapp
python3 scripts/deploy.py --agent copilot --scope global
python3 scripts/deploy.py --agent agents  --scope global --skill ability.screen.read
python3 scripts/deploy.py --agent claude  --scope global --uninstall
python3 scripts/deploy.py --agent claude  --scope project --project ~/work/myapp --uninstall --skill ability.wiki.docs-run
```

| Flag | Meaning |
|------|---------|
| `--agent` | `claude`, `copilot`, `agents` (required) |
| `--scope` | `project` or `global` (required). `project` also needs `--project DIR` |
| `--skill NAME` | Deploy (or with `--uninstall`, remove) only this skill (repeatable). Default: every eligible skill when deploying, every installed one when uninstalling |
| `--home DIR` | Home for global scope (default: your home; e.g. a Windows home from WSL) |
| `--clean` | Remove all `ability.*` from the target before deploying |
| `--uninstall` | Remove installed skills and stop. All of them, or only the `--skill` ones (see below) |
| `--purge-output` | With `--uninstall`: also delete the removed skills' output folders |
| `--dry-run` | Print the plan only |

A skill that doesn't declare the requested scope is refused with an error. `--home` applies to global scope only. `--clean` removes only `ability.*` skill folders in the target (never output folders, never other skills) and is ignored with `--uninstall`.

### Global install, specific skills

```bash
# one skill for one agent (its dependencies come along)
python3 scripts/deploy.py --agent claude --scope global --skill ability.screen.read
# several skills, another agent
python3 scripts/deploy.py --agent copilot --scope global --skill ability.git.sync --skill ability.stocks.trend
# every global-eligible skill, all three agents
for a in claude copilot agents; do python3 scripts/deploy.py --agent $a --scope global; done
```

Deploys are additive: installing one skill leaves other installed `ability.*` skills alone, and only replaces the folders it deploys. Use `--clean` for an exact set.

Global and project installs are separate folders, so both can exist for the same agent. Which one the agent uses when both are present is the agent's own precedence rule, not this repo's.

## Agent conventions

| Agent | Project folder | Global folder | Frontmatter kept |
|-------|----------------|---------------|------------------|
| `claude` | `<project>/.claude/skills/` | `~/.claude/skills/` | `name`, `description`, `argument-hint` |
| `copilot` | `<project>/.github/skills/` | `~/.copilot/skills/` | `name`, `description` |
| `agents` | `<project>/.agents/skills/` | `~/.agents/skills/` | `name`, `description` |

Repo-only keys (`io`, `install`) are always stripped. Agents without an argument-hint key get the usage appended to the description (`Usage: /<name> [args]`). ### Adding an agent

1. Add an entry to `AGENTS` in `scripts/deploy.py`: `project` folder, `global` folder, `keys` (frontmatter keys it understands) and `usage_in_description` (true if it has no argument-hint key).
2. Add a case to `tests/test_deploy.py`.
3. Add a row to the table above.
The `--agent` choices are generated from `AGENTS`.

## What a deploy does

1. Picks the skills (declared eligible, or `--skill`).
2. Adds dependencies: `ability.help`, the domain help and `*.common`, the category help (domains with categories only), and for an orchestrator every skill it owns. A dependency that doesn't allow the scope is an error.
3. Copies each folder (replacing any existing copy) and converts SKILL.md frontmatter.
4. Rewrites docs: `.claude/skills/` becomes the target's skills folder (project: relative, e.g. `.github/skills/`; global: `~/.copilot/skills/`), and `<repo root>` becomes `<project root>` or `~/.ability`.
5. Writes `install.json` into each `*.common` folder so `ability_paths.py` finds its root. Skill outputs then land in `<project>/<skill-name>/` or `~/.ability/<skill-name>/`.

## Uninstalling

`--uninstall` takes the same `--agent`, `--scope`, `--project` and `--home` as a deploy, so it hits the same folder.

- **No `--skill`**: removes every `ability.*` folder in the target.
- **With `--skill`**: removes those skills plus any dependency (help, common, `ability.help`) that no remaining installed skill still needs. A skill that isn't installed is an error.
- **Never breaks what's left**: if a remaining skill still needs a skill you asked to remove (e.g. removing `ability.wiki.docs-init` while `ability.wiki.docs-run` is installed), it stops and tells you which skill to remove too.
- **Only `ability.*` folders** are touched; other skills in the folder stay.
- **Output is kept** (`<project>/<skill-name>/`, `~/.ability/<skill-name>/`) because it is your data. `--purge-output` deletes the removed skills' output folders, and `~/.ability` itself once empty.
- `--dry-run` prints what would be removed.

Deployed skills are self-contained copies. Re-run deploy after changing a skill in the repo. Help in a deployed install lists only the deployed skills.

Run project-scope skills with the project as the working directory, since script paths are project-relative.
