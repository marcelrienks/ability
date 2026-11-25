# ability.finance.budget-summary-common

Hidden shared lib for the `budget-summary` group. Never run directly. Used by `ability.finance.budget-summary-parse`, `-organise`, `-render`, orchestrated by `ability.finance.budget-summary-run`. Nothing here talks to the network.

- `scripts/budget_common.py`: CSV parsing, salary detection, filtering, three-tier categorising, grouped rows, reconciliation guards, stage-file helpers.
- `scripts/xlsx_writer.py`: minimal `.xlsx` writer (standard library only).
- `config/category-mappings.json`: merchant keywords per category, pattern groups, category order, settings. **The file to edit** to change categories. Contains personal merchant names.
- `references/business-rules.md`: the rules and file contracts. Wins over any budget `SKILL.md`.

Tests: `python3 -m unittest tests.test_budget` (or the full suite, see `wiki/tests.md`). Synthetic data only, writes only to a temp folder, never reads `data/`.
