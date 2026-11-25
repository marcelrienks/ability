#!/usr/bin/env python3
"""budget_common.py: shared logic for the ability.finance.budget-summary-* skills.

Everything that must be exact lives here: CSV parsing, salary detection, filtering, three-tier categorising,
grouped rows and the reconciliation guards. Rules: references/business-rules.md (wins over any SKILL.md).
Standard library only. Inputs from data/, outputs to <repo root>/<skill-name>/ via ability_paths.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / "ability.finance.common" / "scripts"))
import ability_paths as paths  # noqa: E402

_repo_root = paths.repo_root


def _root() -> Path:
    """Repo root. ABILITY_BASE_DIR relocates it to a temp folder (tests only)."""
    return Path(os.environ["ABILITY_BASE_DIR"]) if os.environ.get("ABILITY_BASE_DIR") else _repo_root()


paths.repo_root = _root

COMMON = "ability.finance.budget-summary-common"
PARSE = "ability.finance.budget-summary-parse"
ORGANISE = "ability.finance.budget-summary-organise"
RENDER = "ability.finance.budget-summary-render"
CONFIG_PATH = SKILLS / COMMON / "config" / "category-mappings.json"

HEADER_LINES = 7  # lines 1-7: statement info and the column header row; data starts on line 8
DATE_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$")
OTHER, CREDIT = "Other", "Credit"


class BudgetError(Exception):
    """A guard failed. The run stops; never work around it."""


def today() -> str:
    return date.today().isoformat()


def cents(x: float) -> int:
    return round(x * 100)


def money(c: int) -> float:
    return round(c / 100, 2)


def to_date(s: str) -> date:
    return datetime.strptime(s, "%Y/%m/%d").date()


# ---------------------------------------------------------------- config

def load_config(path: Path = CONFIG_PATH) -> dict:
    """Load and validate category-mappings.json. A malformed or incomplete config fails the run:
    silently defaulting merchants would produce a plausible but wrong report."""
    try:
        cfg = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise BudgetError(f"category config unreadable ({path}): {e}")
    errs = []
    t1 = cfg.get("tier1Categories")
    if not isinstance(t1, dict) or not all(isinstance(v, list) and all(isinstance(k, str) and k for k in v) for v in t1.values()):
        errs.append("tier1Categories must map category -> list of non-empty keywords")
    elif CREDIT in t1:
        errs.append(f"{CREDIT} is reserved (all positive amounts)")
    t2 = cfg.get("tier2Patterns")
    if not isinstance(t2, list) or not all(isinstance(p, dict) and p.get("pattern") and p.get("groupName") for p in t2):
        errs.append("tier2Patterns must be a list of {pattern, groupName, matchType}")
    elif any(p.get("matchType", "contains") != "contains" for p in t2):
        errs.append("tier2Patterns: only matchType 'contains' is supported")
    if not isinstance(cfg.get("categoryOrder"), list):
        errs.append("categoryOrder must be a list")
    s = cfg.get("settings")
    if not isinstance(s, dict):
        errs.append("settings must be an object")
    else:
        if not isinstance(s.get("minimumSalaryAmount"), (int, float)) or isinstance(s.get("minimumSalaryAmount"), bool) or s["minimumSalaryAmount"] <= 0:
            errs.append("settings.minimumSalaryAmount must be a positive number")
        if not isinstance(s.get("caseInsensitive"), bool):
            errs.append("settings.caseInsensitive must be true or false")
        if s.get("firstMatchWins") is not True:
            errs.append("settings.firstMatchWins must be true (false would double count transactions)")
    if errs:
        raise BudgetError("category config invalid: " + "; ".join(errs))
    return cfg


# ---------------------------------------------------------------- input

def find_csv(arg: str | None) -> Path:
    """The statement to read: the named file in data/, or the one and only *.csv in data/."""
    if arg:
        p = paths.input_path(arg)
        if not p.is_file():
            raise BudgetError(f"{arg} not found in data/")
        return p
    root = paths.data_dir()
    found = sorted(p for p in root.glob("*.csv") if p.is_file()) if root.exists() else []
    if not found:
        raise BudgetError(f"no CSV file in {root}. Put the statement export in data/.")
    if len(found) > 1:
        raise BudgetError("several CSV files in data/ (" + ", ".join(p.name for p in found) + "). Name one with --csv, or remove the extras.")
    return found[0]


def parse_csv_line(line: str) -> list[str]:
    """Split on commas outside double quotes."""
    out, cur, quoted = [], [], False
    for ch in line:
        if ch == '"':
            quoted = not quoted
        elif ch == "," and not quoted:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out


def parse_transactions(text: str) -> tuple[list[dict], list[dict]]:
    """Return (transactions sorted by date ascending, stable; skipped lines).

    Guard: line 7 must be the Date, Amount, Balance, Description header, so a different bank export or a
    shifted layout fails instead of silently dropping or misreading rows."""
    lines = text.strip().split("\n")
    if len(lines) <= HEADER_LINES:
        raise BudgetError("CSV has no transaction lines (expected 7 header lines, then data)")
    head = [c.strip().lower() for c in parse_csv_line(lines[HEADER_LINES - 1])]
    if head[:4] != ["date", "amount", "balance", "description"]:
        raise BudgetError(f"line {HEADER_LINES} is not the 'Date, Amount, Balance, Description' header (got {lines[HEADER_LINES-1].strip()[:60]!r}). Unsupported statement layout.")
    txs, skipped = [], []
    for i, line in enumerate(lines[HEADER_LINES:], start=HEADER_LINES + 1):
        if not line.strip():
            continue
        parts = parse_csv_line(line)
        reason = None
        if len(parts) < 4:
            reason = "fewer than 4 columns"
        else:
            d, a = parts[0].strip(), parts[1].strip()
            try:
                amount = float(a)
            except ValueError:
                amount = None
            if not DATE_RE.match(d):
                reason = "date is not YYYY/MM/DD"
            else:
                try:
                    to_date(d)
                except ValueError:
                    reason = "date does not exist"
            if reason is None and (amount is None or amount != amount):
                reason = "amount is not a number"
        if reason:
            skipped.append({"line": i, "reason": reason})
            continue
        desc = re.sub(r"\s+", " ", ",".join(parts[3:])).strip()
        txs.append({"date": d, "amount": amount, "description": desc})
    if not txs:
        raise BudgetError("no valid transactions parsed")
    txs.sort(key=lambda t: t["date"])  # YYYY/MM/DD sorts chronologically; stable
    return txs, skipped


# ---------------------------------------------------------------- salary and filter

def find_salary(txs: list[dict], minimum: float) -> dict:
    """Starting point (see business-rules.md section 3).

    1. latest credit >= minimum inside the month before the month of the latest transaction;
    2. else latest credit >= minimum anywhere;
    3. else the earliest transaction. Returns the transaction plus `basis`."""
    latest = to_date(max(t["date"] for t in txs))
    first_of_this = latest.replace(day=1)
    prev_end = first_of_this.fromordinal(first_of_this.toordinal() - 1)
    prev_start = prev_end.replace(day=1)
    big = [t for t in txs if t["amount"] >= minimum]
    in_prev = [t for t in big if prev_start <= to_date(t["date"]) <= prev_end]
    if in_prev:
        return {**in_prev[-1], "basis": "previous-month"}
    if big:
        return {**big[-1], "basis": "latest-anywhere"}
    return {**txs[0], "basis": "earliest-transaction"}


def filter_from(txs: list[dict], start: str) -> list[dict]:
    return [t for t in txs if t["date"] >= start]


# ---------------------------------------------------------------- categorise

def _match(desc: str, needle: str, ci: bool) -> bool:
    return (needle.lower() in desc.lower()) if ci else (needle in desc)


def categorise(txs: list[dict], cfg: dict) -> dict:
    """Three tiers, first match wins, no double counting (business-rules.md section 4).

    Credit: every positive amount. Tier 1: keyword categories in config order. Tier 2: pattern groups.
    Tier 3: everything else, individually. Tier 2 and 3 (and tier 1 'Other') are sub-items of Other."""
    ci = cfg["settings"]["caseInsensitive"]
    main: dict[str, list] = {k: [] for k in cfg["tier1Categories"]}
    main[CREDIT] = []
    tier2: dict[str, list] = {}
    tier3: list[dict] = []
    for t in txs:
        if t["amount"] > 0:
            main[CREDIT].append(t)
            continue
        hit = next((c for c, kws in cfg["tier1Categories"].items() if any(_match(t["description"], k, ci) for k in kws)), None)
        if hit:
            main[hit].append(t)
            continue
        grp = next((p["groupName"] for p in cfg["tier2Patterns"] if _match(t["description"], p["pattern"], ci)), None)
        if grp:
            tier2.setdefault(grp, []).append(t)
        else:
            tier3.append(t)
    return {"main": main, "tier2": tier2, "tier3": tier3}


def _item(label, items):
    return {"label": label, "count": len(items), "cents": sum(cents(t["amount"]) for t in items),
            "earliest": min(t["date"] for t in items)}


def _by_earliest(items):
    return sorted(items, key=lambda i: i["earliest"])  # stable


def _similar(items):
    """Group identical descriptions (case-insensitive): one line per description."""
    groups: dict[str, list] = {}
    for t in items:
        groups.setdefault(t["description"].lower(), []).append(t)
    return _by_earliest(_item(g[0]["description"], g) for g in groups.values())


def build_grouped(cat: dict, cfg: dict) -> tuple[list[dict], list[str]]:
    """Return (categories, warnings). Order: categoryOrder first, other categories next (warned),
    'Other' last. Each category: {category, count, cents, earliest, children[{label,count,cents,earliest}]}."""
    out, warnings = [], []
    main = cat["main"]
    order = [c for c in cfg["categoryOrder"] if c != OTHER and c in main]
    extra = _by_earliest([{"category": c, "earliest": min(t["date"] for t in main[c])}
                          for c in main if c not in order and c != OTHER and main[c]])
    for c in order + [e["category"] for e in extra]:
        items = main[c]
        if not items:
            continue
        if c not in cfg["categoryOrder"]:
            warnings.append(f"category {c} is not in categoryOrder; listed before Other")
        out.append({"category": c, "count": len(items), "cents": sum(cents(t["amount"]) for t in items),
                    "earliest": min(t["date"] for t in items), "children": _similar(items)})
    kids = [_item(f"Individual: {t['description']}", [t]) for t in main.get(OTHER, [])]
    kids += [_item(g, items) for g, items in cat["tier2"].items()]
    kids += [_item(f"Individual: {t['description']}", [t]) for t in cat["tier3"]]
    if kids:
        kids = _by_earliest(kids)
        out.append({"category": OTHER, "count": sum(k["count"] for k in kids), "cents": sum(k["cents"] for k in kids),
                    "earliest": kids[0]["earliest"], "children": kids})
    return out, warnings


def summarise(txs: list[dict]) -> dict:
    spend = sum(cents(t["amount"]) for t in txs if t["amount"] < 0)
    cred = sum(cents(t["amount"]) for t in txs if t["amount"] > 0)
    dates = [t["date"] for t in txs]
    return {"transactions": len(txs), "date_start": min(dates), "date_end": max(dates),
            "spending": money(spend), "credits": money(cred), "net": money(spend + cred)}


def reconcile(txs: list[dict], grouped: list[dict]) -> None:
    """Guard: the grouped sheet must account for every transaction and every cent of the filtered sheet."""
    net = sum(cents(t["amount"]) for t in txs)
    g_net = sum(c["cents"] for c in grouped)
    g_cnt = sum(c["count"] for c in grouped)
    kid_net = sum(k["cents"] for c in grouped for k in c["children"])
    kid_cnt = sum(k["count"] for c in grouped for k in c["children"])
    problems = []
    if g_cnt != len(txs):
        problems.append(f"grouped counts {g_cnt} transactions, filtered has {len(txs)}")
    if g_net != net:
        problems.append(f"grouped totals R{money(g_net):.2f}, filtered totals R{money(net):.2f}")
    if kid_cnt != g_cnt or kid_net != g_net:
        problems.append("sub-items do not add up to their categories")
    if problems:
        raise BudgetError("reconciliation failed: " + "; ".join(problems))


# ---------------------------------------------------------------- sheet rows

def filtered_rows(txs: list[dict]) -> list[list]:
    rows = [[t["date"], round(t["amount"], 2), t["description"]] for t in txs]
    rows.append(["", money(sum(cents(t["amount"]) for t in txs)), "TOTAL (for validation with grouped sheet)"])
    return rows


def grouped_rows(summary: dict, grouped: list[dict]) -> list[list]:
    rows = [["=== SUMMARY ===", None, None, None],
            ["Total Transactions", summary["transactions"], summary["net"], summary["date_start"]],
            ["Total Spending", None, summary["spending"], None],
            ["Total Credits", None, summary["credits"], None],
            [None] * 4,
            ["=== CATEGORIES ===", None, None, None]]
    for c in grouped:
        rows.append([c["category"], c["count"], money(c["cents"]), c["earliest"]])
        for k in c["children"]:
            rows.append([f"  └ {k['label']}", k["count"], money(k["cents"]), k["earliest"]])
        rows.append([None] * 4)
    return rows


# ---------------------------------------------------------------- stage files

def read_stage(skill: str, prefix: str, date_str: str) -> dict:
    p = paths.upstream_dir(skill) / f"{prefix}-{date_str}.json"
    if not p.is_file():
        raise BudgetError(f"{p.name} not found in {skill}/. Run that stage first (same --date).")
    return json.loads(p.read_text())


def write_json(skill: str, name: str, data: dict) -> Path:
    p = paths.output_dir(skill) / name
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return p
