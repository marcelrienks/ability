import importlib.util
import tempfile
import unittest
import zipfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("trend", ROOT / ".claude/skills/ability.stocks.trend/scripts/trend.py")
trend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trend)


def pts(*prices):
    labels = ["now"] + [i[0] for i in trend.INCREMENTS]
    return list(zip(labels, prices))


def hist(prices, end=date(2026, 11, 20)):
    n = len(prices)
    return [(end - timedelta(days=n - 1 - i), float(p)) for i, p in enumerate(prices)]


class SignalTest(unittest.TestCase):
    def test_returns_and_drawdown(self):
        h = hist([100, 200, 150])
        self.assertAlmostEqual(trend.drawdown(h), -0.25)
        r = trend.horizon_returns([("now", 150.0), ("1m", 100.0), ("6m", 200.0)])
        self.assertAlmostEqual(r["1m"], 0.5)
        self.assertAlmostEqual(r["6m"], -0.25)

    def test_ma_trend(self):
        self.assertEqual(trend.ma_trend(hist(range(1, 30))), "n/a")
        self.assertEqual(trend.ma_trend(hist(range(1, 300))), "bull")
        self.assertEqual(trend.ma_trend(hist(range(300, 1, -1))), "bear")
        # price dipped below the slow average while the fast one is still above it
        self.assertEqual(trend.ma_trend(hist([100] * 30 + [200] * 9 + [50])), "mixed")

    def test_verdicts(self):
        up = {h: 0.2 for h in trend.SCORED_HORIZONS}
        down = {h: -0.2 for h in trend.SCORED_HORIZONS}
        self.assertEqual(trend.verdict(up, -0.05, "bull"), "GOOD")
        self.assertEqual(trend.verdict(down, -0.5, "bear"), "POOR")
        # long-term fine but now rolling over: early warning
        self.assertEqual(trend.verdict(up, -0.4, "bull"), "WARNING")
        self.assertEqual(trend.verdict(up, -0.4, "mixed"), "WARNING")
        self.assertEqual(trend.verdict({}, -0.1, "n/a"), "N/A")

    def test_netflix_case_long_trend_down(self):
        # short horizons up, long horizons down, deep drawdown: flagged even though recent months are green
        mixed = {"6m": 0.1, "1y": 0.05, "3y": -0.3, "5y": -0.4, "10y": -0.2}
        self.assertEqual(trend.verdict(mixed, -0.5, "mixed"), "WARNING")
        self.assertEqual(trend.verdict(mixed, -0.5, "bear"), "POOR")


class PointsTest(unittest.TestCase):
    def test_last_close_on_or_before_target(self):
        end = date(2026, 11, 20)
        hist = [(end - timedelta(days=i), float(1000 - i)) for i in range(4000, -1, -1)]
        p = dict(trend.price_points(hist))
        self.assertEqual(p["now"], 1000.0)
        self.assertEqual(p["1w"], 993.0)
        self.assertEqual(p["1m"], 1000.0 - (end - date(2026, 10, 20)).days)

    def test_short_history_stops(self):
        end = date(2026, 11, 20)
        hist = [(end - timedelta(days=i), 1.0) for i in range(40, -1, -1)]
        self.assertEqual([l for l, _ in trend.price_points(hist)], ["now", "1d", "1w", "1m"])

    def test_tolerates_provider_range_slightly_short(self):
        end = date(2026, 11, 20)
        hist_ = [(end - timedelta(days=i), 1.0) for i in range(3640, -1, -1)]  # ~9.97y
        self.assertIn("10y", [l for l, _ in trend.price_points(hist_)])

    def test_month_end_clamp(self):
        self.assertEqual(trend.months_back(date(2026, 3, 31), 1), date(2026, 2, 28))


class ExtractTest(unittest.TestCase):
    def test_header_columns_across_sheets(self):
        sheets = {"A": [["Name", "Ticker"], ["x", "abc"], ["y", "XYZ"], ["", ""], ["z", "SKIP"]],
                  "B": [["Symbol", "Qty"], ["XYZ", "5"], ["DEF.JO", "1"]]}
        t, m = trend.extract_tickers(sheets)
        self.assertEqual((t, m), (["ABC", "XYZ", "DEF.JO"], "header"))

    def test_fallback(self):
        t, m = trend.extract_tickers({"A": [["Total", "AAPL", "1,000", "MSFT"]]})
        self.assertEqual((t, m), (["AAPL", "MSFT"], "fallback"))

    def test_xlsx_reader(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "p.xlsx"
            ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
            with zipfile.ZipFile(f, "w") as z:
                z.writestr("xl/workbook.xml", f'<workbook {ns} xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="S1" sheetId="1" r:id="rId1"/></sheets></workbook>')
                z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
                z.writestr("xl/sharedStrings.xml", f'<sst {ns}><si><t>Ticker</t></si><si><t>AAPL</t></si></sst>')
                z.writestr("xl/worksheets/sheet1.xml", f'<worksheet {ns}><sheetData><row r="1"><c r="B1" t="s"><v>0</v></c></row><row r="2"><c r="B2" t="s"><v>1</v></c></row></sheetData></worksheet>')
            self.assertEqual(trend.extract_tickers(trend.read_xlsx(f)), (["AAPL"], "header"))


class ExchangeTest(unittest.TestCase):
    def test_exchange_column(self):
        sheets = {"I": [["Code", "#", "Exchange"], ["etfgld", "1", "JSE"], ["GOOG", "2", "NYSE"], ["", "", ""], ["X", "3", "AMS"]]}
        self.assertEqual(trend.extract_exchanges(sheets), {"ETFGLD": "JSE", "GOOG": "NYSE"})

    def test_no_exchange_column(self):
        self.assertEqual(trend.extract_exchanges({"A": [["Ticker"], ["ABC"]]}), {})

    def test_unlisted_raises(self):
        with self.assertRaises(ValueError):
            trend.fetch_history("BLYDE", "EE")


class AnalyseTest(unittest.TestCase):
    def test_exchange_lookup_and_failures(self):
        end = date(2026, 11, 20)
        h = [(end - timedelta(days=i), float(100 + i)) for i in range(4000, -1, -1)]
        seen = []

        def fake(ticker, exchange):
            seen.append((ticker, exchange))
            if ticker == "BAD":
                raise ValueError("no Google Finance listing")
            return h

        rows, failed = trend.analyse(["ABC", "BAD", "XYZ"], {"ABC": "JSE"}, "AMS", fake)
        self.assertEqual([r["ticker"] for r in rows], ["ABC", "XYZ"])
        self.assertEqual(seen, [("ABC", "JSE"), ("BAD", "AMS"), ("XYZ", "AMS")])
        self.assertEqual(failed[0][0], "BAD")
        self.assertIn(rows[0]["verdict"], trend.VERDICT_ORDER)


if __name__ == "__main__":
    unittest.main()
