#!/usr/bin/env python3
"""Portfolio health check.

Reads tickers from an xlsx/csv/tsv export, fetches weekly price history from Google Finance, and
prints one table with a GOOD / WARNING / POOR verdict per stock from three signals:
horizon returns, drawdown from peak, and moving-average trend.

Usage: trend.py FILE [--exchange JSE]
"""
import argparse
import bisect
import calendar
import csv
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

# (label, months back, days back). Exactly one of the two is set.
INCREMENTS = [
    ("1d", 0, 1), ("1w", 0, 7), ("1m", 1, 0), ("6m", 6, 0), ("1y", 12, 0), ("2y", 24, 0),
    ("3y", 36, 0), ("4y", 48, 0), ("5y", 60, 0), ("10y", 120, 0),
]
GF_URL = "https://www.google.com/finance/_/GoogleFinanceUi/data/batchexecute?rpcids=AiCwsd&source-path=/finance/quote/&hl=en&rt=c"
GF_MAX_WINDOW = 8  # Google Finance chart window code: full history, weekly points
# Exchanges tried after the one in the export: exports often label NASDAQ and NYSE Arca names "NYSE".
US_EXCHANGES = ["NASDAQ", "NYSE", "NYSEARCA", "NYSEAMERICAN"]
UNLISTED = {"EE"}  # no Google Finance listing; the sheet values these by hand
CENTS = {"JSE"}  # quoted in cents, the sheet divides by 100
WEEKS_FAST, WEEKS_SLOW = 10, 40  # 50 and 200 trading days, on weekly points
HEADERS = {"ticker", "symbol", "code", "instrument", "share code", "stock", "ticker symbol"}
TICKER_RE = re.compile(r"^[A-Za-z0-9^][A-Za-z0-9.\-=]{0,14}$")
FALLBACK_RE = re.compile(r"^[A-Z]{1,5}([.\-][A-Z]{1,3})?$")
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


# ---------- ticker extraction ----------

def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group()
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_xlsx(path: Path) -> dict[str, list[list[str]]]:
    """Sheet name -> rows of strings. Stdlib only."""
    sheets: dict[str, list[list[str]]] = {}
    with zipfile.ZipFile(path) as z:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in rels}
        rid = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        for sheet in wb.find("m:sheets", NS):
            target = targets[sheet.get(rid)].lstrip("/")
            part = target if target.startswith("xl/") else f"xl/{target}"
            root = ET.fromstring(z.read(part))
            rows: list[list[str]] = []
            for row in root.iter(f"{{{NS['m']}}}row"):
                cells: list[str] = []
                for c in row.findall("m:c", NS):
                    idx = _col_index(c.get("r"))
                    cells.extend([""] * (idx + 1 - len(cells)))
                    t = c.get("t")
                    if t == "inlineStr":
                        val = "".join(x.text or "" for x in c.iter(f"{{{NS['m']}}}t"))
                    else:
                        v = c.find("m:v", NS)
                        val = v.text if v is not None and v.text else ""
                        if t == "s" and val:
                            val = shared[int(val)]
                    cells[idx] = val.strip()
                rows.append(cells)
            sheets[sheet.get("name")] = rows
    return sheets


def read_delimited(path: Path) -> dict[str, list[list[str]]]:
    text = path.read_text(encoding="utf-8-sig")
    dialect = csv.excel_tab if path.suffix.lower() == ".tsv" else csv.Sniffer().sniff(text[:4096], ",;\t")
    return {path.stem: [[c.strip() for c in row] for row in csv.reader(text.splitlines(), dialect)]}


def extract_tickers(sheets: dict[str, list[list[str]]]) -> tuple[list[str], str]:
    """Return (tickers, method). Header columns first, ticker-shaped cells as fallback."""
    found: list[str] = []
    for rows in sheets.values():
        for r, row in enumerate(rows):
            cols = [i for i, c in enumerate(row) if c.lower() in HEADERS]
            for col in cols:
                for below in rows[r + 1:]:
                    if col < len(below) and TICKER_RE.match(below[col]) and not below[col].replace(".", "").isdigit():
                        found.append(below[col].upper())
                    elif col < len(below) and not below[col]:
                        break
    if found:
        return list(dict.fromkeys(found)), "header"
    for rows in sheets.values():
        for row in rows:
            found.extend(c for c in row if FALLBACK_RE.match(c))
    return list(dict.fromkeys(found)), "fallback"


def extract_exchanges(sheets: dict[str, list[list[str]]]) -> dict[str, str]:
    """Ticker -> exchange, from an `Exchange` column in the same header row as the ticker column."""
    out: dict[str, str] = {}
    for rows in sheets.values():
        for r, row in enumerate(rows):
            lower = [c.lower() for c in row]
            ex_cols = [i for i, c in enumerate(lower) if c in ("exchange", "market")]
            for col in (i for i, c in enumerate(lower) if c in HEADERS):
                for below in rows[r + 1:]:
                    if col >= len(below) or not below[col]:
                        break
                    if ex_cols and ex_cols[0] < len(below) and below[ex_cols[0]]:
                        out.setdefault(below[col].upper(), below[ex_cols[0]].upper())
    return out


# ---------- prices ----------

def _gf_weekly(ticker: str, exchange: str) -> list[tuple[date, float]]:
    """Weekly closes for ticker:exchange from Google Finance, [] if it has no such listing."""
    inner = json.dumps([[[None, [ticker, exchange]]], GF_MAX_WINDOW, None, None, None, None, None, 0], separators=(",", ":"))
    freq = json.dumps([[["AiCwsd", inner, None, "generic"]]], separators=(",", ":"))
    req = urllib.request.Request(
        GF_URL, data=urllib.parse.urlencode({"f.req": freq}).encode(),
        headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode()
    line = next(l for l in body.splitlines() if l.startswith('[["wrb.fr"'))
    payload = json.loads(line)[0][2]
    if not payload or payload == "[]":
        return []
    points = json.loads(payload)[0][0][3][0][1]
    return [(date(*p[0][:3]), p[1][0]) for p in points if p[1][0]]


def fetch_history(ticker: str, exchange: str = "") -> list[tuple[date, float]]:
    """Last 10 years of weekly closes. Tries the given exchange, then the US ones."""
    if exchange in UNLISTED:
        raise ValueError(f"unlisted ({exchange}), no Google Finance data")
    symbol = ticker.upper()
    candidates = list(dict.fromkeys(([exchange] if exchange else []) + (US_EXCHANGES if exchange in ("", *US_EXCHANGES) else [])))
    for ex in candidates:
        out = _gf_weekly(symbol, ex)
        if out:
            cutoff = months_back(out[-1][0], 120) - timedelta(days=14)
            scale = 100 if ex in CENTS else 1
            return [(d, c / scale) for d, c in out if d >= cutoff]
    raise ValueError(f"no Google Finance listing (tried {', '.join(candidates) or 'none'})")


def months_back(d: date, months: int) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 - months, 12)
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def price_points(history: list[tuple[date, float]]) -> list[tuple[str, float]]:
    """[(label, price)] for 'now' and each increment the history covers, newest first."""
    dates = [d for d, _ in history]
    now_date, now_price = history[-1]
    points = [("now", now_price)]
    for label, months, days in INCREMENTS:
        target = months_back(now_date, months) if months else now_date - timedelta(days=days)
        i = bisect.bisect_right(dates, target) - 1
        if i < 0:
            if (dates[0] - target).days > 14:  # history genuinely too short
                break
            i = 0  # the provider's range starts a few days short of the exact target
        points.append((label, history[i][1]))
    return points


# ---------- signals ----------

HORIZONS = ["1m", "6m", "1y", "3y", "5y", "10y"]
SCORED_HORIZONS = ["6m", "1y", "3y", "5y", "10y"]  # 1m is shown but too noisy to score
VERDICT_ORDER = {"POOR": 0, "WARNING": 1, "GOOD": 2, "N/A": 3}
COLORS = {"POOR": "31", "WARNING": "33", "GOOD": "32"}


def horizon_returns(points: list[tuple[str, float]]) -> dict[str, float]:
    now = points[0][1]
    return {label: now / price - 1 for label, price in points[1:] if label in HORIZONS and price}


def drawdown(history: list[tuple[date, float]]) -> float:
    """Fraction below the highest close in the history (0 = at peak, -0.4 = 40% below)."""
    return history[-1][1] / max(p for _, p in history) - 1


def ma_trend(history: list[tuple[date, float]], fast: int = WEEKS_FAST, slow: int = WEEKS_SLOW) -> str:
    """bull: price and fast MA above slow MA. bear: price and fast MA below. else mixed. n/a if < slow closes.

    Defaults are the 50/200-day pair expressed in weekly closes.
    """
    closes = [p for _, p in history]
    if len(closes) < slow:
        return "n/a"
    ma50, ma200, price = sum(closes[-fast:]) / fast, sum(closes[-slow:]) / slow, closes[-1]
    if price > ma200 and ma50 > ma200:
        return "bull"
    if price < ma200 and ma50 < ma200:
        return "bear"
    return "mixed"


def verdict(returns: dict[str, float], dd: float, ma: str) -> str:
    """Each signal scores -1/0/+1 (unavailable = 0). Sum >= 2 GOOD, <= -2 POOR, else WARNING."""
    scored = [returns[h] for h in SCORED_HORIZONS if h in returns]
    if not scored:
        return "N/A"
    up = sum(r > 0 for r in scored) / len(scored)
    s_ret = 1 if up >= 2 / 3 else -1 if up <= 1 / 3 else 0
    s_dd = 1 if dd > -0.15 else -1 if dd < -0.30 else 0
    s_ma = {"bull": 1, "bear": -1}.get(ma, 0)
    total = s_ret + s_dd + s_ma
    return "GOOD" if total >= 2 else "POOR" if total <= -2 else "WARNING"


# ---------- output ----------

def pct(x: float | None) -> str:
    return "-" if x is None else f"{x * 100:+.0f}%"


def render(rows: list[dict], color: bool = False) -> str:
    cols = [("Ticker", "ticker"), ("Last", "last")] + [(h, h) for h in HORIZONS] + [
        ("From peak", "peak"), ("MA trend", "ma"), ("Verdict", "verdict")]
    widths = [max(len(h), *(len(str(r[k])) for r in rows)) if rows else len(h) for h, k in cols]

    def line(vals, paint=False):
        cells = []
        for (_, key), v, w in zip(cols, vals, widths):
            text = str(v).ljust(w)
            if paint and color and key == "verdict" and v in COLORS:
                text = f"\033[{COLORS[v]}m{text}\033[0m"
            cells.append(text)
        return "  ".join(cells).rstrip()

    out = [line([h for h, _ in cols]), line(["-" * w for w in widths])]
    out += [line([r[k] for _, k in cols], paint=True) for r in rows]
    return "\n".join(out)


def analyse(tickers: list[str], exchanges: dict[str, str], default_exchange: str = "",
            fetch=fetch_history) -> tuple[list[dict], list[tuple[str, str]]]:
    rows, failed = [], []
    for t in tickers:
        try:
            history = fetch(t, exchanges.get(t, default_exchange))
        except (urllib.error.URLError, ValueError, KeyError, IndexError, TypeError, StopIteration) as err:
            failed.append((t, str(err)))
            continue
        points = price_points(history)
        returns = horizon_returns(points)
        dd, ma = drawdown(history), ma_trend(history)
        rows.append({"ticker": t, "last": f"{points[0][1]:.2f}",
                     **{h: pct(returns.get(h)) for h in HORIZONS},
                     "peak": pct(dd), "ma": ma, "verdict": verdict(returns, dd, ma), "dd": dd})
    rows.sort(key=lambda r: (VERDICT_ORDER[r["verdict"]], r["dd"], r["ticker"]))
    return rows, failed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--exchange", default="", help="exchange for tickers the file gives none for, e.g. JSE")
    args = ap.parse_args()
    path = Path(args.file)
    if not path.is_file():
        print(f"file not found: {path}", file=sys.stderr)
        return 1
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        sheets = read_xlsx(path)
    elif ext in (".csv", ".tsv"):
        sheets = read_delimited(path)
    else:
        print(f"unsupported file type: {ext}", file=sys.stderr)
        return 1
    tickers, method = extract_tickers(sheets)
    if not tickers:
        print("no tickers found", file=sys.stderr)
        return 1
    if method == "fallback":
        print("note: no ticker/symbol header found, using ticker-shaped cells. Check the list.", file=sys.stderr)
    print(f"{len(tickers)} tickers from {path.name} ({len(sheets)} sheet(s))\n")
    rows, failed = analyse(tickers, extract_exchanges(sheets), args.exchange.upper())
    print(render(rows, color=sys.stdout.isatty()))
    for symbol, err in failed:
        print(f"failed: {symbol}: {err}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
