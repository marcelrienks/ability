---
name: ability.finance.budget-summary-run
description: "Orchestrator: Generate the monthly budget summary workbook from a credit card CSV."
argument-hint: "[--csv NAME]"
---

# Monthly budget summary (orchestrator)

> Turn a credit card statement CSV into the monthly budget summary Excel workbook: transactions from the latest salary deposit forward, categorised and totalled. Use when the user runs /ability.finance.budget-summary-run or asks for a "budget summary", "monthly budget", "process my credit card statement" or "organise my statement". Orchestrates ability.finance.budget-summary-parse, -organise and -render. Shared code: ability.finance.budget-summary-common.

Orchestrator for the budget-summary group. Owns `ability.finance.budget-summary-parse`, `ability.finance.budget-summary-organise`, `ability.finance.budget-summary-render` and the hidden `ability.finance.budget-summary-common`. Default I/O contract: `data/` in, `<repo root>/<skill-name>/` out.

Produces `ability.finance.budget-summary-render/budget-summary-DATE.xlsx` with two sheets, `filtered` (every transaction from the salary date, with a validation total) and `grouped` (summary plus categories). Scripts do all the work; no model judgment is needed to produce the workbook.

## Inputs
- Optional `--csv NAME`: a file in `data/`. Without it, `data/` must hold exactly one `*.csv`; zero or several stops the run.
- The statement is an FNB Private Credit Card export (format: `ability.finance.budget-summary-common/references/business-rules.md`).
- Categories: `.claude/skills/ability.finance.budget-summary-common/config/category-mappings.json`.

## Rules (read first)
1. **Local only.** Nothing is uploaded, emailed or shared. The statement is personal financial data: never paste transactions into chat beyond what the user asks to see, and never copy `data/*.csv` anywhere.
2. **Stop on failure.** If a stage exits non-zero, show its message and the stage, and ask. Never work around a guard (bad header, reconciliation failure, invalid config).
3. **Never hand-edit** the JSON or the workbook. Fix the cause (config, CSV) and rerun.
4. All rules live in `.claude/skills/ability.finance.budget-summary-common/references/business-rules.md`. If this file and that one disagree, that one wins.
5. Any working directory under the repo root works. Inputs are read only from `data/`; each stage writes only to its own folder at the repo root. DATE is today, `YYYY-MM-DD`; pass the same `--date` to every stage if a run crosses midnight.

## Stages

| # | Skill | Args | Guard artifact |
|---|-------|------|----------------|
| 1 | `ability.finance.budget-summary-parse` | `--csv` if given | `transactions-DATE.json` |
| 2 | `ability.finance.budget-summary-organise` | none | `organised-DATE.json` |
| 3 | `ability.finance.budget-summary-render` | none | `budget-summary-DATE.xlsx` |

## Steps
1. **Parse**: follow `ability.finance.budget-summary-parse` (pass `--csv` when given).
2. **Organise**: follow `ability.finance.budget-summary-organise`.
3. **Render**: follow `ability.finance.budget-summary-render`.
4. **Present** the workbook path and the summary lines `render.py` printed (start date and salary, transaction count, categories, spending, credits, net). Repeat every WARNING from the stages (skipped lines, salary fallback, category not in `categoryOrder`).
5. **Suggest mappings (optional)**: from `ability.finance.budget-summary-organise/organised-DATE.json`, list the `Other` sub-items whose label starts with `Individual:` and spend most. If any look like a recurring merchant, propose a keyword and category for `config/category-mappings.json`. Edit the config only after the user agrees, then rerun the stages.

## Outputs
`ability.finance.budget-summary-render/budget-summary-DATE.xlsx`, `ability.finance.budget-summary-organise/organised-DATE.json`, `ability.finance.budget-summary-parse/transactions-DATE.json`. Running again on the same date overwrites that date's files.

## Troubleshooting
| Symptom | Cause / fix |
| --- | --- |
| "no CSV file in .../data" | Put the statement export in `data/`. |
| "several CSV files in data/" | Pass `--csv NAME`, or remove the extras. |
| "line 7 is not the 'Date, Amount, Balance, Description' header" | Not an FNB credit card export, or the layout changed. Do not edit the CSV to fit; update the parser rules first. |
| "WARNING skipped N line(s)" | Rows with a bad date (must be `YYYY/MM/DD`) or amount (plain number, no `R`). Fix the export; the report is incomplete until they parse. |
| "no salary-sized credit in the previous month" | Salary missing or below `minimumSalaryAmount`. The run used the fallback shown. Check the threshold in the config. |
| "reconciliation failed" | A bug or a hand-edited stage file. Delete the stage folders for today and rerun. |
| "category config invalid" | Fix `category-mappings.json` as the message says. |
