import unittest
from summary import summarize


class SummaryTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(summarize("category,amount\nfood,2.50\nfood,1.25\n"), {"rows": 2, "invalid_rows": 0, "totals": {"food": "3.75"}})

    def test_exact_decimal(self):
        self.assertEqual(summarize("category,amount\nx,0.1\nx,0.2\n")["totals"], {"x": "0.30"})

    def test_round_after_sum(self):
        self.assertEqual(summarize("category,amount\nx,0.005\nx,0.005\n")["totals"], {"x": "0.01"})

    def test_half_up(self):
        self.assertEqual(summarize("category,amount\nx,1.005\ny,-1.005\n")["totals"], {"x": "1.01", "y": "-1.01"})

    def test_quoted_comma(self):
        self.assertEqual(summarize('category,amount\n"food, drink",2\n')["totals"], {"food, drink": "2.00"})

    def test_bom_crlf(self):
        self.assertEqual(summarize("\ufeffcategory,amount\r\nx,1\r\n")["rows"], 1)

    def test_invalid_records(self):
        self.assertEqual(summarize("category,amount\nx,NaN\nx,Infinity\nx,-Infinity\nx,abc\nx,\n,1\nx\nx,1,extra\nx,3\n"), {"rows": 1, "invalid_rows": 8, "totals": {"x": "3.00"}})

    def test_trim_and_case(self):
        self.assertEqual(summarize("category,amount\n x , 2 \nX,3\n")["totals"], {"x": "2.00", "X": "3.00"})

    def test_negative_zero(self):
        self.assertEqual(summarize("category,amount\nx,-2\nx,0\nx,1\n"), {"rows": 3, "invalid_rows": 0, "totals": {"x": "-1.00"}})

    def test_extra_columns(self):
        self.assertEqual(summarize("category,amount,note\nx,1,ok\n")["rows"], 1)

    def test_header_only(self):
        self.assertEqual(summarize("category,amount\n\n"), {"rows": 0, "invalid_rows": 0, "totals": {}})

    def test_bad_headers(self):
        for text in ("", "category\nx\n", "amount\n1\n", "category,amount,amount\nx,1,2\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                summarize(text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
