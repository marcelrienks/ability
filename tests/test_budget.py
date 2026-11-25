"""Tests for the budget-summary skills. Run:
python3 -m unittest discover -s tests -v
Synthetic data only. Writes only to a temp folder (ABILITY_BASE_DIR); never reads data/.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

SKILLS = Path(__file__).resolve().parent.parent / ".claude" / "skills"
COMMON = SKILLS / "ability.finance.budget-summary-common" / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, COMMON / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bc = load("budget_common")
xw = load("xlsx_writer")

HEAD = """ACCOUNT TRANSACTION HISTORY

Name:, Test, User
Account:, 123******456, [Private Credit Card]
Balance:, 100.00, N/A

Date, Amount, Balance, Description
"""
ROWS = """2026/09/10, 25000.00, 0, OLD SALARY EMPLOYER
2026/09/28, 30000.00, 0, SALARY EMPLOYER
2026/09/29, -100.50, 0, WOOLWORTHS SOMERSET MA   Somerset Wes ZA
2026/09/30, -50.00, 0, WOOLWORTHS SOMERSET MA   Somerset Wes ZA
2026/10/01, -300.00, 0, SHELL ULTRA CITY
2026/10/02, -75.25, 0, PAYFAST*Some Shop   Cape Town ZA
2026/10/03, -10.00, 0, PAYFAST*Other Shop   Cape Town ZA
2026/10/04, -20.00, 0, "MYSTERY, SHOP"   ZA
2026/10/05, -8.00, 0, TAKEALO MEATS
2026/10/06, -9.99, 0, NETFLIX.COM
"""
CSV = HEAD + ROWS


class Parsing(unittest.TestCase):
    def test_parses_and_cleans(self):
        txs, skipped = bc.parse_transactions(CSV)
        self.assertEqual(len(txs), 10)
        self.assertEqual(skipped, [])
        self.assertEqual(txs[2]["description"], "WOOLWORTHS SOMERSET MA Somerset Wes ZA")
        self.assertEqual(txs[7]["description"], "MYSTERY, SHOP ZA")  # quoted comma kept
        self.assertEqual([t["date"] for t in txs], sorted(t["date"] for t in txs))

    def test_bad_lines_skipped_and_reported(self):
        txs, skipped = bc.parse_transactions(CSV + "2026-10-07, -1.00, 0, BAD DATE\n2026/10/08, R5, 0, BAD AMOUNT\n2026/13/45, -1, 0, NO SUCH DATE\n")
        self.assertEqual(len(txs), 10)
        self.assertEqual([s["line"] for s in skipped], [18, 19, 20])

    def test_wrong_layout_fails(self):
        with self.assertRaises(bc.BudgetError):
            bc.parse_transactions(CSV.replace("Date, Amount, Balance, Description", "Posted, Value, Memo, Text"))
        with self.assertRaises(bc.BudgetError):
            bc.parse_transactions(HEAD)

    def test_find_csv_rules(self):
        with tempfile.TemporaryDirectory() as t:
            os.environ["ABILITY_BASE_DIR"] = t
            try:
                (Path(t) / "data").mkdir()
                with self.assertRaises(bc.BudgetError):
                    bc.find_csv(None)
                (Path(t) / "data" / "a.csv").write_text(CSV)
                self.assertEqual(bc.find_csv(None).name, "a.csv")
                (Path(t) / "data" / "b.csv").write_text(CSV)
                with self.assertRaises(bc.BudgetError):
                    bc.find_csv(None)
                self.assertEqual(bc.find_csv("b.csv").name, "b.csv")
                with self.assertRaises(Exception):
                    bc.find_csv("../outside.csv")
            finally:
                del os.environ["ABILITY_BASE_DIR"]


class Salary(unittest.TestCase):
    def tx(self, *pairs):
        return [{"date": d, "amount": a, "description": "x"} for d, a in pairs]

    def test_previous_month_latest(self):
        s = bc.find_salary(self.tx(("2026/09/10", 25000.0), ("2026/09/28", 30000.0), ("2026/10/06", -5.0)), 10000)
        self.assertEqual((s["date"], s["basis"]), ("2026/09/28", "previous-month"))

    def test_current_month_salary_is_not_the_start_when_previous_exists(self):
        s = bc.find_salary(self.tx(("2026/09/28", 30000.0), ("2026/10/25", 31000.0)), 10000)
        self.assertEqual(s["date"], "2026/09/28")

    def test_fallbacks(self):
        s = bc.find_salary(self.tx(("2026/07/28", 30000.0), ("2026/10/06", -5.0)), 10000)
        self.assertEqual((s["date"], s["basis"]), ("2026/07/28", "latest-anywhere"))
        s = bc.find_salary(self.tx(("2026/10/01", -5.0), ("2026/10/06", 100.0)), 10000)
        self.assertEqual((s["date"], s["basis"]), ("2026/10/01", "earliest-transaction"))

    def test_january_rolls_to_december(self):
        s = bc.find_salary(self.tx(("2025/12/27", 30000.0), ("2026/01/05", -5.0)), 10000)
        self.assertEqual(s["date"], "2025/12/27")


class Categorising(unittest.TestCase):
    def setUp(self):
        self.cfg = bc.load_config()
        txs, _ = bc.parse_transactions(CSV)
        salary = bc.find_salary(txs, self.cfg["settings"]["minimumSalaryAmount"])
        self.filtered = bc.filter_from(txs, salary["date"])
        self.grouped, self.warnings = bc.build_grouped(bc.categorise(self.filtered, self.cfg), self.cfg)
        self.by = {c["category"]: c for c in self.grouped}

    def test_filter_starts_at_salary(self):
        self.assertEqual(self.filtered[0]["description"], "SALARY EMPLOYER")
        self.assertEqual(len(self.filtered), 9)

    def test_tiers(self):
        self.assertEqual(self.by["Credit"]["cents"], 3000000)
        g = self.by["Groceries"]
        self.assertEqual((g["count"], g["cents"]), (2, -15050))
        self.assertEqual(len(g["children"]), 1)  # identical descriptions merged
        labels = [k["label"] for k in self.by["Other"]["children"]]
        self.assertIn("PAYFAST Transactions", labels)
        self.assertIn("Individual: MYSTERY, SHOP ZA", labels)
        self.assertIn("Individual: TAKEALO MEATS", labels)  # tier 1 Other keyword
        payfast = next(k for k in self.by["Other"]["children"] if k["label"] == "PAYFAST Transactions")
        self.assertEqual((payfast["count"], payfast["cents"]), (2, -8525))

    def test_order_and_other_last(self):
        names = [c["category"] for c in self.grouped]
        self.assertEqual(names[-1], "Other")
        order = [c for c in self.cfg["categoryOrder"] if c in names and c != "Other"]
        self.assertEqual(names[:-1], order)

    def test_reconciles_and_detects_breakage(self):
        bc.reconcile(self.filtered, self.grouped)
        broken = json.loads(json.dumps(self.grouped))
        broken[0]["cents"] += 1
        with self.assertRaises(bc.BudgetError):
            bc.reconcile(self.filtered, broken)
        with self.assertRaises(bc.BudgetError):
            bc.reconcile(self.filtered[:-1], self.grouped)

    def test_category_missing_from_order_is_kept_and_warned(self):
        cfg = json.loads(json.dumps(self.cfg))
        cfg["categoryOrder"] = [c for c in cfg["categoryOrder"] if c != "Fuel"]
        grouped, warnings = bc.build_grouped(bc.categorise(self.filtered, cfg), cfg)
        bc.reconcile(self.filtered, grouped)
        self.assertTrue(any("Fuel" in w for w in warnings))

    def test_summary_signs(self):
        s = bc.summarise(self.filtered)
        self.assertEqual(s["credits"], 30000.0)
        self.assertLess(s["spending"], 0)
        self.assertEqual(s["net"], round(s["credits"] + s["spending"], 2))

    def test_rows(self):
        rows = bc.filtered_rows(self.filtered)
        self.assertEqual(rows[-1][2], "TOTAL (for validation with grouped sheet)")
        self.assertEqual(rows[-1][1], bc.summarise(self.filtered)["net"])
        g = bc.grouped_rows(bc.summarise(self.filtered), self.grouped)
        self.assertEqual(g[0][0], "=== SUMMARY ===")
        self.assertTrue(any(str(r[0]).startswith("  └ ") for r in g))


class Config(unittest.TestCase):
    def test_invalid_configs_fail(self):
        good = json.loads(bc.CONFIG_PATH.read_text())
        for mutate in (lambda c: c.pop("tier1Categories"), lambda c: c["settings"].update(firstMatchWins=False),
                       lambda c: c["settings"].update(minimumSalaryAmount="10000"),
                       lambda c: c["tier1Categories"].update(Credit=["x"]),
                       lambda c: c["tier2Patterns"].append({"pattern": "a", "groupName": "A", "matchType": "regex"})):
            cfg = json.loads(json.dumps(good))
            mutate(cfg)
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                json.dump(cfg, f)
            try:
                with self.assertRaises(bc.BudgetError):
                    bc.load_config(Path(f.name))
            finally:
                os.unlink(f.name)


class Workbook(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.xlsx"
            xw.write_workbook(p, [("a", [("h1", 10), ("h2", 10)], [["=== T ===", 1.5], ["a & <b>", None], [None, 2]])])
            z = zipfile.ZipFile(p)
            self.assertIsNone(z.testzip())
            for n in z.namelist():
                ET.fromstring(z.read(n))  # all parts are well-formed XML
            sheet = z.read("xl/worksheets/sheet1.xml").decode()
            self.assertIn("=== T ===", sheet)
            self.assertIn("a &amp; &lt;b&gt;", sheet)
            self.assertNotIn("<f>", sheet)


class EndToEnd(unittest.TestCase):
    def test_three_stages(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "data").mkdir()
            (Path(t) / "data" / "statement.csv").write_text(CSV)
            env = dict(os.environ, ABILITY_BASE_DIR=t)
            for stage in ("parse", "organise", "render"):
                script = SKILLS / f"ability.finance.budget-summary-{stage}" / "scripts" / f"{stage}.py"
                r = subprocess.run([sys.executable, "-I", str(script), "--date", "2026-11-25"], capture_output=True, text=True, env=env)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = Path(t) / "ability.finance.budget-summary-render" / "budget-summary-2026-11-25.xlsx"
            self.assertTrue(out.is_file())
            self.assertIn("Net:", r.stdout)
            # a stale/edited organised file is caught at render
            org = Path(t) / "ability.finance.budget-summary-organise" / "organised-2026-11-25.json"
            data = json.loads(org.read_text())
            data["grouped"][0]["cents"] += 100
            org.write_text(json.dumps(data))
            script = SKILLS / "ability.finance.budget-summary-render" / "scripts" / "render.py"
            r = subprocess.run([sys.executable, "-I", str(script), "--date", "2026-11-25"], capture_output=True, text=True, env=env)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("reconciliation failed", r.stderr)


if __name__ == "__main__":
    unittest.main()
