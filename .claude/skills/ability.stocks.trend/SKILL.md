---
name: ability.stocks.trend
description: "Read a portfolio export (xlsx or csv) from data/, find its stock tickers, and print a table rating each stock GOOD, WARNING or POOR from long-term returns, drawdown from peak and moving-average trend."
install: global,project
argument-hint: "[file] [exchange=JSE]"
---

# Stocks Trend (portfolio health)

Extracts tickers from a portfolio export, fetches 10 years of price history from Google Finance (the same GOOGLEFINANCE source the portfolio spreadsheet uses), and rates each stock. The point: a stock you are in profit on can still be trending down over years. The verdict surfaces that. Output is a table on screen only.

## Method

Three signals, each scored -1 / 0 / +1 (unavailable = 0):

| Signal | Shown as | +1 | 0 | -1 |
|--------|----------|----|---|----|
| Horizon returns: `now` vs 1m, 6m, 1y, 3y, 5y, 10y ago (1m is shown but not scored, too noisy) | `1m` ... `10y` columns | 2/3 or more of the scored horizons up | between | 1/3 or fewer up |
| Drawdown from peak (highest close in the history) | `From peak` | less than 15% below | 15 to 30% below | more than 30% below |
| Moving averages (50/200 trading days, as 10/40 weekly closes) | `MA trend` | `bull`: price and 50d above 200d | `mixed` | `bear`: price and 50d below 200d |

Verdict = sum of the three: **2 or more GOOD**, **-2 or less POOR**, anything else **WARNING**. WARNING covers mixed signals and early warnings, such as good long-term returns but a deep drawdown or a rolled-over moving average.

Sorted POOR, WARNING, GOOD, then deepest drawdown first. The Verdict is coloured when printed to a terminal. A horizon the stock has no history for shows `-`.

## I/O

Default contract: the export is read from `data/`, output goes to `<repo root>/ability.stocks.trend/` (not used for the table, which prints to screen only).

Network: reads weekly price history from the public Google Finance chart endpoint. Read-only, no credentials. Each ticker is looked up as `EXCHANGE:CODE` using the export's `Exchange` column, as the spreadsheet does. Tickers whose exchange is `NYSE` are retried on NASDAQ, NYSE Arca and NYSE American, since the sheet looks US tickers up bare. JSE prices are cents and are divided by 100 to match the sheet. Exchange `EE` (unlisted, valued by hand in the sheet) is skipped and reported as failed.

## Workflow

1. **Locate the file.** If the user gave `file`, use it. Otherwise list `data/` and use the only `.xlsx`/`.csv`/`.tsv` there, or ask which one if several (prefer the `.xlsx` when it and a `.csv` export of it are both there).
   ```bash
   python3 .claude/skills/ability.stocks.common/scripts/ability_paths.py input
   ```
2. **Run:**
   ```bash
   python3 .claude/skills/ability.stocks.trend/scripts/trend.py FILE [--exchange JSE]
   ```
   - All sheets are scanned. Columns headed `Ticker`, `Symbol`, `Code`, `Instrument`, `Share Code` or `Stock` are used. If no such header exists anywhere, ticker-shaped cells are used as a fallback (the script says so).
   - `exchange` is used for tickers the file gives no exchange for (JSE, for example). Not needed when the file has an `Exchange` column.
3. **Print the table verbatim**, then summarise in one or two lines: the longest uptrends and downtrends, and any tickers that failed to load.

## Output

```
Ticker  Last    1m   6m    1y    3y    5y    10y   From peak  MA trend  Verdict
NFLX    920.10  +4%  +10%  -12%  -35%  -40%  -20%  -48%       mixed     WARNING
ABC     123.40  +2%  +17%  +30%  +84%  +118% +210% -3%        bull      GOOD
XYZ     55.10   -6%  -22%  -43%  -30%  -40%  -55%  -61%       bear      POOR
```

## Notes

- Returns are price only (no dividends) and exclude your cost basis. The export is only used to find tickers.
- Thresholds are constants in `scripts/trend.py` (`verdict`).
- Not investment advice. Signals describe past price only.
