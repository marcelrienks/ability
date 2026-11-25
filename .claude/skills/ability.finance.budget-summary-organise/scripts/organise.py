#!/usr/bin/env python3
"""organise.py: stage 2. Salary start, filter, categorise, group, reconcile. Writes organised-DATE.json.

Usage: organise.py [--date DATE]
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
    ap.add_argument("--date", default=bc.today())
    a = ap.parse_args()
    try:
        cfg = bc.load_config()
        txs = bc.read_stage(bc.PARSE, "transactions", a.date)["transactions"]
        salary = bc.find_salary(txs, cfg["settings"]["minimumSalaryAmount"])
        filtered = bc.filter_from(txs, salary["date"])
        grouped, warnings = bc.build_grouped(bc.categorise(filtered, cfg), cfg)
        bc.reconcile(filtered, grouped)
        summary = bc.summarise(filtered)
        out = bc.write_json(bc.ORGANISE, f"organised-{a.date}.json", {
            "date": a.date,
            "salary": {k: salary[k] for k in ("date", "amount", "description", "basis")},
            "summary": summary,
            "warnings": warnings,
            "filtered": filtered,
            "grouped": grouped,
        })
    except bc.BudgetError as e:
        sys.exit(f"organise failed: {e}")
    print(f"start: {salary['date']} R{salary['amount']:.2f} ({salary['basis']})")
    print(f"{summary['transactions']} transactions in {len(grouped)} categories, reconciled")
    for w in warnings:
        print("WARNING " + w)
    if salary["basis"] != "previous-month":
        print(f"WARNING no salary-sized credit in the previous month; used {salary['basis']}")
    print(f"wrote {out.relative_to(bc.paths.repo_root())}")


main()
