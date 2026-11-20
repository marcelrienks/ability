# Tests

```bash
python3 -m unittest discover -s tests -v
```

`tests/test_structure.py`:
- folder names match the naming pattern and `name:` in SKILL.md; common folders have no SKILL.md
- flat `ability.<domain>.<function>` only for single-function domains, and single-function domains must be flat
- every domain has a help skill, and every category has a category help skill that uses the shared `help.py`
- orchestrator required at 2+ working skills, description starts `Orchestrator:`, covers every owned skill
- `io: external` matches an `## I/O exception` section; `install` values are valid; external skills declare `install`; orchestrators' owned skills allow the orchestrator's scopes
- documented `.claude/skills/...` paths exist (README and wiki), no `~/.claude/skills` in skills
- `ability_paths.py` identical across domains and refuses paths outside `data/`

`tests/test_deploy.py` deploys into temp dirs for each agent and scope and checks folder layout, frontmatter conversion, path rewriting, dependencies, `install.json` roots, and refusals. Uninstall tests cover selective removal with dependency pruning, foreign folders left alone, refusing to break an orchestrator, output kept unless `--purge-output`, and dry run.

`tests/test_trend.py` covers the stocks trend logic offline: signals and verdicts, price-point selection, ticker extraction (xlsx, header and fallback), exchange lookup and failures.
