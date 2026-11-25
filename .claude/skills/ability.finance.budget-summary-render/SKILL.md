---
name: ability.finance.budget-summary-render
description: "Build the budget summary Excel workbook."
argument-hint: "[--date DATE]"
---

# Render the workbook

> Write `ability.finance.budget-summary-render/budget-summary-DATE.xlsx` from the organised data. Use as stage 3 of ability.finance.budget-summary-run.

Input: `ability.finance.budget-summary-organise/organised-DATE.json` (read only). Output: `ability.finance.budget-summary-render/` at the repo root. No categorising and no model judgment here.

## Steps
1. Run `python3 .claude/skills/ability.finance.budget-summary-render/scripts/render.py [--date DATE]` from the repo root.
2. Present the workbook path and the summary it prints.

## The workbook
- **filtered**: `date`, `amount`, `description`, every transaction from the start date, then a row `TOTAL (for validation with grouped sheet)` holding the net.
- **grouped**: a `=== SUMMARY ===` block (total transactions with net and start date, total spending as a negative, total credits), then `=== CATEGORIES ===`: each category with `count`, `total_amount`, `earliest_date`, followed by indented `└` sub-items and a blank row. Identical descriptions are merged into one line. `Other` lists its sub-items by earliest date.
- The net on `filtered` equals the sum of the category totals on `grouped`; the sheet is written only after that is re-checked.
- Standard library only (`xlsx_writer.py` writes the file; text is never treated as a formula).

## Fails loudly
Missing organised file, or a reconciliation mismatch. Never edit the workbook by hand.
