---
name: ability.finance.budget-summary-parse
description: "Parse the bank statement CSV in data/ into dated transactions."
argument-hint: "[--csv NAME] [--date DATE]"
---

# Parse the statement

> Read the statement CSV from `data/` and write `ability.finance.budget-summary-parse/transactions-DATE.json`. Use as stage 1 of ability.finance.budget-summary-run or when the user asks to parse a statement.

Input: `data/` only (the named file, or the one `*.csv` there). Output: `ability.finance.budget-summary-parse/` at the repo root, created on demand. The statement is never modified.

## Steps
1. Run `python3 .claude/skills/ability.finance.budget-summary-parse/scripts/parse.py [--csv NAME] [--date DATE]` from the repo root.
2. Report the transaction count and date range it prints. Repeat any `WARNING skipped` line in full.

## What it does
Checks that line 7 is the `Date, Amount, Balance, Description` header, then reads line 8 onward: date (`YYYY/MM/DD`), amount (plain number, negative is spending), description (everything after the third comma, whitespace collapsed, commas inside quotes kept). Balance is ignored. Transactions are sorted by date, oldest first. Unparseable lines are listed with their line numbers in `skipped`.

## Fails loudly
No CSV, several CSVs without `--csv`, an unexpected header line, or zero valid transactions. Skipped lines only warn; do not ignore them.
