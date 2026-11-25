#!/usr/bin/env python3
"""render.py: stage 3. Build budget-summary-DATE.xlsx (sheets: filtered, grouped) from organised-DATE.json.
No categorising happens here. Usage: render.py [--date DATE]
"""
import argparse
import importlib.util
import sys
from pathlib import Path

_here = Path(__file__).resolve().parents[2] / "ability.finance.budget-summary-common" / "scripts"
_spec = importlib.util.spec_from_file_location("budget_common", _here / "budget_common.py")
bc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bc)

sys.path.insert(0, str(_here))
import xlsx_writer  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=bc.today())
    a = ap.parse_args()
    try:
        org = bc.read_stage(bc.ORGANISE, "organised", a.date)
        txs, grouped, summary = org["filtered"], org["grouped"], org["summary"]
        bc.reconcile(txs, grouped)  # the file may be stale or edited: check again before writing
        frows, grows = bc.filtered_rows(txs), bc.grouped_rows(summary, grouped)
        out = bc.paths.output_dir(bc.RENDER) / f"budget-summary-{a.date}.xlsx"
        xlsx_writer.write_workbook(out, [
            ("filtered", [("date", 12), ("amount", 12), ("description", 40)], frows),
            ("grouped", [("category", 30), ("count", 10), ("total_amount", 15), ("earliest_date", 12)], grows),
        ])
    except bc.BudgetError as e:
        sys.exit(f"render failed: {e}")
    print(f"wrote {out.relative_to(bc.paths.repo_root())}  (filtered {len(frows)} rows, grouped {len(grows)} rows)")
    print(f"Start (salary): {org['salary']['date']} R{org['salary']['amount']:.2f}")
    print(f"Transactions:   {summary['transactions']}  ({summary['date_start']} to {summary['date_end']})")
    print(f"Categories:     {len(grouped)}")
    print(f"Spending:       R{summary['spending']:.2f}")
    print(f"Credits:        R{summary['credits']:.2f}")
    print(f"Net:            R{summary['net']:.2f}")


main()
