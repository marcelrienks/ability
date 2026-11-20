# Skills

| Domain | Category | Skill | `io` | `install` |
|--------|----------|-------|------|-----------|
| `git` | (flat) | `ability.git.sync` | external | global,project |
| `screen` | (flat) | `ability.screen.read` | external | global |
| `wiki` | `docs` | `ability.wiki.docs-run` (orchestrator), `-init`, `-read`, `-write`, `-simplify`, `-review` | external | project |

`git` and `screen` have a single function each, so they use the flat `ability.<domain>.<function>` form. Run `/ability.help` for args and summaries.

## Wiki docs pipeline

`/ability.wiki.docs-run [overwrite] [review] [auto]` runs, in order, stopping on first failure:

1. `docs-init`: move documentation into `wiki/` and `wiki/raw/`, then build context
2. `docs-read [refresh]`: write `.cel/context.md` with hashes (skips rescan when unchanged)
3. `docs-write [overwrite]`: generate baseline docs, then simplify with `force`
4. `docs-simplify [force]`: consolidate duplicates (asks for confirmation unless `force`)
5. `docs-review [auto]`: fallacy, contradiction, inconsistency review (only with `review`)

All of them work in place on the project in the working directory. Install with `deploy.py --scope project`.
