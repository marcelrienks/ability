# Skills

| Domain | Category | Skill | `io` | `install` |
|--------|----------|-------|------|-----------|
| `git` | (flat) | `ability.git.sync` | external | global,project |
| `screen` | (flat) | `ability.screen.read` | external | global |
| `stocks` | (flat) | `ability.stocks.trend` | default (`data/` in) | global,project |
| `wiki` | `docs` | `ability.wiki.docs-run` (orchestrator), `-init`, `-read`, `-write`, `-simplify`, `-review` | external | project |

`git`, `screen` and `stocks` have a single function each, so they use the flat `ability.<domain>.<function>` form. Run `/ability.help` for args and summaries.

## Wiki docs pipeline

`/ability.wiki.docs-run [overwrite] [review] [auto]` runs, in order, stopping on first failure:

1. `docs-init`: move documentation into `wiki/` and `wiki/raw/`, then build context
2. `docs-read [refresh]`: write `.cel/context.md` with hashes (skips rescan when unchanged)
3. `docs-write [overwrite]`: generate baseline docs, then simplify with `force`
4. `docs-simplify [force]`: consolidate duplicates (asks for confirmation unless `force`)
5. `docs-review [auto]`: fallacy, contradiction, inconsistency review (only with `review`)

All of them work in place on the project in the working directory. Install with `deploy.py --scope project`.

## Stocks trend

`/ability.stocks.trend [file] [exchange=JSE]` reads tickers from a portfolio export in `data/` (all sheets, header columns `Ticker`/`Symbol`/`Code`...), fetches 10 years of weekly history from Google Finance (`EXCHANGE:CODE` from the export's Exchange column, as the spreadsheet's GOOGLEFINANCE formulas do; unlisted `EE` rows are skipped), and prints a screen-only table rating each stock GOOD, WARNING or POOR. Signals: returns over 1m to 10y, drawdown from peak, 50/200-day moving-average trend. Meant to expose stocks that are in profit but trending down long term. Network access is read-only, no credentials.
