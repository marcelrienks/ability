# ability

Repository of AI skills and related scripts.

Skills are written for Claude Code but follow one strict, uniform pattern so they convert easily to other AI agents' skill conventions. They run directly from a clone of this repo, or are installed per project or globally for Claude, Copilot or other agents with `scripts/deploy.py`.

In short: naming convention + orchestrator/stage pipeline + `data/`-in / skill-folder-out data contract (with declared per-skill exceptions) + declared install scope, all enforced by tests.

## Quick start

```bash
# run from the clone: open Claude Code here, then
/ability.help

# install into another project, or globally
python3 scripts/deploy.py --agent claude --scope project --project ~/work/myapp
python3 scripts/deploy.py --agent copilot --scope global

# tests
python3 -m unittest discover -s tests -v
```

## Layout

```
.claude/skills/<skill-name>/   SKILL.md (+ scripts/, config/); hidden *-common has no SKILL.md
data/                          default input (git-ignored except .gitkeep)
<skill-name>/                  default output per skill, created on demand (git-ignored)
scripts/deploy.py              install skills for claude / copilot / agents, project or global
tests/                         structure and deploy tests
wiki/                          the ruleset and expectations
```

## Wiki

- [rules](wiki/rules.md): naming, orchestrators, help, frontmatter, adding skills
- [io](wiki/io.md): `data/` in / skill folder out, and the `io: external` exception
- [deploy](wiki/deploy.md): `install:` declaration, project vs. global, agent conventions
- [skills](wiki/skills.md): current skills and the wiki pipeline
- [tests](wiki/tests.md): what the tests enforce
