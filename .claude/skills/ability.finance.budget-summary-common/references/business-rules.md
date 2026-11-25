# Budget summary: business rules

Wins over any `SKILL.md`. Ported from the original Simplicity project (`docs/prd.md` is the spec; `run-workflow.js` diverged from it, see "Decisions").

## 1. Input
FNB Private Credit Card CSV in `data/`.

```
Lines 1-6   statement info (name, account, balance)   ignored
Line 7      Date, Amount, Balance, Description        must match, or the run fails
Line 8+     YYYY/MM/DD, -453.32, 0, DESCRIPTION
```

- Amounts: negative is spending, positive is a credit. Plain numbers only (`-237.64`, not `R237,64` or `(237.64)`).
- Dates: `YYYY/MM/DD` only.
- Balance is ignored. Description is everything after the third comma, whitespace collapsed, commas inside double quotes kept.
- A non-blank line that does not parse is skipped, listed in `skipped` and warned. Zero valid transactions fails.
- Transactions are sorted by date ascending. The sort is stable, so same-day rows keep file order.

## 2. Folders and files
| Stage | Folder | File |
| --- | --- | --- |
| parse | `ability.finance.budget-summary-parse/` | `transactions-DATE.json` (`source`, `skipped`, `transactions`) |
| organise | `ability.finance.budget-summary-organise/` | `organised-DATE.json` (`salary`, `summary`, `warnings`, `filtered`, `grouped`) |
| render | `ability.finance.budget-summary-render/` | `budget-summary-DATE.xlsx` |

## 3. Start of the period (salary)
1. Latest transaction date L. The previous month is the calendar month before L's month.
2. Candidates: credits of at least `settings.minimumSalaryAmount` dated in that previous month. Take the latest (last in sorted order).
3. None: take the latest credit of at least the minimum anywhere (`basis: latest-anywhere`, warned).
4. None: take the earliest transaction (`basis: earliest-transaction`, warned).
5. Keep every transaction dated on or after the start date, debits and credits.

## 4. Categorising
First match wins, never double counted. Matching is substring, case-insensitive by default.
1. **Credit**: every amount above zero. Reserved name, cannot be a tier 1 category.
2. **Tier 1**: `tier1Categories`, categories checked in config order, keywords in list order.
3. **Tier 2**: `tier2Patterns` (`contains` only), first pattern wins, grouped under `groupName`.
4. **Tier 3**: anything else, one item per transaction, labelled `Individual: <description>`.

`Other` is built last: tier-1 `Other` keyword matches (one `Individual:` item each), then tier-2 groups, then tier-3 items, sorted by earliest date. Sub-items of other categories merge identical descriptions (case-insensitive) into one line with count, total and earliest date.

Main category order: `categoryOrder` (skipping `Other`), then any category with transactions that is missing from `categoryOrder` (warned), then `Other`.

## 5. Totals and guards
- Money is summed in whole cents. Total spending is the sum of negative amounts and is shown negative; total credits the sum of positive amounts; net is their sum.
- **Reconciliation** (organise and again at render): grouped counts equal the filtered count, grouped totals equal the filtered net, sub-items equal their categories. A mismatch fails the run.
- Config problems fail the run: wrong types, `firstMatchWins` not true, tier 2 `matchType` other than `contains`, `Credit` used as a tier 1 category.

## 6. Settings (`config/category-mappings.json`)
`minimumSalaryAmount` (default 10000), `caseInsensitive` (true), `firstMatchWins` (must be true). `preserveDescriptionFormatting` is accepted and ignored: descriptions are always whitespace-collapsed.

## 7. Decisions (differences from the original project)
The original had two logics. This port follows the spec and fixes what the runner got wrong:
- **Salary rule**: previous-month window with fallbacks (spec), not "latest large credit anywhere" (runner).
- **Credit**: positive amounts are `Credit` (spec). The runner sent a salary through tier 2/other matching (the `1bb` pattern) and left `Credit` out.
- **Nothing is dropped**: the runner wrote only categories in `categoryOrder`, so tier 2 groups and `Credit` vanished from the grouped sheet and its totals did not match the filtered total. Reconciliation now guarantees they do.
- **Order**: `categoryOrder` is honoured. The spec's engine re-sorted by earliest date, which made the setting meaningless.
- **Text cells**: `=== SUMMARY ===` has no leading apostrophe (that was a Google Sheets workaround); a zero count or amount shows as 0, not blank.
- **Description spacing** is collapsed (spec), the runner kept the bank's padding.
- **Header check** on line 7 is new; the original skipped 7 lines blindly.
- **Config** is validated, not silently replaced by built-in defaults.
- Excel is written without ExcelJS or Node.
