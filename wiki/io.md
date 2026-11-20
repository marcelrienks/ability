# I/O contract

## Default

- **Input**: read only from `data/` at the root. Anything outside is refused. Sensitive input files are git-ignored.
- **Output**: write only to `<root>/<skill-name>/`. Created on demand, git-ignored. Never write to another skill's folder. May read an earlier stage's folder, never edit it.
- **Pipeline style**: each stage writes its own artifact, the next stage reads it. Upstream data stays untouched.
- **Paths**: resolve via `ability.<domain>.common/scripts/ability_paths.py` (CLI: `root`, `input`, `output`, `upstream`, `config`).
- **Not data** (outside the rule): skill settings (`<skill>/config/`) and credentials (`config.ini` at root, git-ignored).

`<root>` is the repo root in a clone. For a deployed skill it is the project directory (project scope) or `~/.ability` (global scope); the deploy script records it in `install.json` inside each `*.common` folder.

## Per-skill exception: `io: external`

Some skills exist to work on something outside `data/` (a project's own `wiki/`, the OS screenshot folder, a git repository). They opt out of the default individually:

1. `io: external` in the SKILL.md frontmatter.
2. An `## I/O exception` section stating exactly what the skill reads and writes.
3. An `install` declaration (see [deploy](deploy.md)).

Tests fail if the declaration and the section disagree. Undeclared skills follow the default.

| Skill | Reads | Writes |
|-------|-------|--------|
| `ability.screen.read` | OS screenshot folders / clipboard | staged copy in its own output folder |
| `ability.git.sync` | the git repo in the working directory | git history and remote (after confirmation); sync log in its output folder |
| `ability.wiki.docs-*` | the project's `README.md`, `wiki/`, codebase | `wiki/`, `wiki/raw/`, `.cel/context.md` in place |
