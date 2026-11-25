#!/usr/bin/env python3
"""parse.py: stage 1. Read the statement CSV from data/ and write transactions-DATE.json.

Usage: parse.py [--csv NAME] [--date DATE]
"""
import argparse
import importlib.util
import sys
from pathlib import Path

_here = Path(__file__).resolve().parents[2] / "ability.finance.budget-summary-common" / "scripts"
_spec = importlib.util.spec_from_file_location("budget_common", _here / "budget_common.py")
bc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--date", default=bc.today())
    a = ap.parse_args()
    try:
        src = bc.find_csv(a.csv)
        txs, skipped = bc.parse_transactions(src.read_text(encoding="utf-8-sig"))
        out = bc.write_json(bc.PARSE, f"transactions-{a.date}.json",
                            {"source": src.name, "date": a.date, "skipped": skipped, "transactions": txs})
    except bc.BudgetError as e:
        sys.exit(f"parse failed: {e}")
    print(f"parsed {len(txs)} transactions from {src.name}: {txs[0]['date']} to {txs[-1]['date']}")
    if skipped:
        print(f"WARNING skipped {len(skipped)} line(s): " + ", ".join(f"{s['line']} ({s['reason']})" for s in skipped))
    print(f"wrote {out.relative_to(bc.paths.repo_root())}")


main()
