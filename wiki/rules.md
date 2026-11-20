# Rules

Ruleset for every skill in this repo. Tests in `tests/` enforce the structural parts.

## Naming

```
ability.<domain>.<category>-<function>
```

The folder name is the skill name, and it must equal `name:` in SKILL.md.

| Part | Meaning |
|------|---------|
| `ability` | Product prefix |
| `domain` | System the skills work on |
| `category` | Group of related skills |
| `function` | Verb or role |

### Reserved functions

| Function | Rule |
|----------|------|
| `<category>-help` | Required per category. Prints each skill's args plus a one-line summary. Makes no external calls. Uses shared `ability.help/scripts/help.py`. |
| `*-run` | Orchestrator. Required once a category has 2+ working skills. Description starts `Orchestrator:`. Runs stages in order, passes shared args down, stops on first failure, never bypasses a failed guard. |
| `*-common` | Hidden shared lib or config. Never run directly, no SKILL.md. Never inside an orchestrator. |

### Grouping

- A skill run by an orchestrator carries its name prefix. Orchestrator `<category>-<group>-run` owns `<category>-<group>-<function>` skills plus `<category>-<group>-common`.
- A skill outside any orchestrator keeps the plain `<category>-<function>` name.
- `ability.<domain>.common` holds domain-wide shared code (`scripts/ability_paths.py`).

### Help levels

```
/ability.help                          all
/ability.<domain>.help                 one domain
/ability.<domain>.<category>-help      one category
```

## SKILL.md frontmatter

| Key | Required | Meaning |
|-----|----------|---------|
| `name` | yes | Equals the folder name |
| `description` | yes | First sentence is the help summary. Orchestrators start `Orchestrator:` |
| `argument-hint` | no | Args shown by help, e.g. `"[refresh]"` |
| `io` | no | `data` (default) or `external`. See [io](io.md) |
| `install` | no | Where the skill may be deployed: `project`, `global`, or `global,project`. Absent = repo-only. See [deploy](deploy.md) |

`io: external` skills must also declare `install`: a skill that works outside this repo has to be installable somewhere.

## Other rules

- Reference scripts by repo-relative `.claude/skills/...`, never `~/.claude/skills`. The deploy script rewrites these for the target.
- No secrets in commits. Real `*.ini` files are git-ignored; ship `*.ini.example`.
- Skills are read-only against external systems unless explicitly confirmed.
- Skills run only on explicit user invocation; they never schedule or start runs themselves. Steps inside one invoked run may proceed automatically.

## Adding skills

- **Existing category**: name it `<category>-<function>`. It appears in help automatically.
- **New category**: create `<category>-help` first. Add `*-run` at the second working skill. Shared code goes in a hidden `*-common`.
- **New domain**: add `ability.<domain>.help` and `ability.<domain>.common`, then repeat the category rules.
- Decide where it runs: from the clone only (default), or declare `install` (and `io: external` if it works outside `data/`).
