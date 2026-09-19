import unittest
from totals import aggregate


class TotalsTests(unittest.TestCase):
    def test_exact_sum(self):
        self.assertEqual(aggregate([("x", "0.1"), ("x", "0.2")]), {"rows": 2, "invalid_rows": 0, "totals": {"x": "0.30"}})

    def test_round_once(self):
        self.assertEqual(aggregate([("x", "0.005"), ("x", "0.005")])["totals"], {"x": "0.01"})

    def test_half_up_and_negative(self):
        self.assertEqual(aggregate([("x", "1.005"), ("y", "-1.005")])["totals"], {"x": "1.01", "y": "-1.01"})

    def test_invalid(self):
        self.assertEqual(aggregate([None, ("x", "abc"), ("x", "NaN"), ("x", "Infinity"), ("x", "-Infinity"), ("x", "0")]), {"rows": 1, "invalid_rows": 5, "totals": {"x": "0.00"}})

    def test_case(self):
        self.assertEqual(aggregate([("x", "1"), ("X", "2")])["totals"], {"x": "1.00", "X": "2.00"})

    def test_empty(self):
        self.assertEqual(aggregate([]), {"rows": 0, "invalid_rows": 0, "totals": {}})
