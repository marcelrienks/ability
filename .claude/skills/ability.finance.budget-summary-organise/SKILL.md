---
name: ability.finance.budget-summary-organise
description: "Find the salary start, filter from it and categorise the transactions."
argument-hint: "[--date DATE]"
---

# Organise transactions

> Find the salary deposit that starts the budget period, keep transactions from it forward, categorise them in three tiers, reconcile, and write `ability.finance.budget-summary-organise/organised-DATE.json`. Use as stage 2 of ability.finance.budget-summary-run.

Input: `ability.finance.budget-summary-parse/transactions-DATE.json` (read only) and the category config. Output: `ability.finance.budget-summary-organise/` at the repo root.

## Steps
1. Run `python3 .claude/skills/ability.finance.budget-summary-organise/scripts/organise.py [--date DATE]` from the repo root (same `--date` as parse).
2. Report the start date and amount, the transaction and category counts, and every WARNING.

## What it does
1. **Start date.** Latest credit of at least `minimumSalaryAmount` inside the month before the latest transaction's month. Fallbacks: latest such credit anywhere, then the earliest transaction. The basis used is recorded.
2. **Filter** to transactions on or after the start date (debits and credits).
3. **Categorise**, first match wins: every positive amount is `Credit`; tier 1 keyword categories in config order; tier 2 pattern groups; tier 3 individual transactions. Tier 2, tier 3 and tier-1 `Other` items become sub-items of `Other`.
4. **Reconcile**: the grouped counts and totals must equal the filtered ones.

Full rules: `.claude/skills/ability.finance.budget-summary-common/references/business-rules.md`. Category and salary settings: `.claude/skills/ability.finance.budget-summary-common/config/category-mappings.json`.

## Fails loudly
Missing parse output, an invalid config, or a reconciliation mismatch. Never continue with partial output.
