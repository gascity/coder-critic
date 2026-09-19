import unittest
from records import parse_records


class RecordsTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(parse_records("category,amount\nx,1\n"), [("x", "1")])

    def test_quoting_and_bom(self):
        self.assertEqual(parse_records('\ufeffcategory,amount,note\r\n" x,y ", 2 ,ok\r\n'), [("x,y", "2")])

    def test_invalid_rows_and_empty_lines(self):
        self.assertEqual(parse_records("category,amount\n\nx\nx,1,extra\n,2\nx,\nx,abc\n"), [None, None, None, None, ("x", "abc")])

    def test_headers(self):
        for text in ("", "category\nx\n", "category,amount,amount\nx,1,2\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_records(text)

    def test_malformed_quoting(self):
        with self.assertRaises(ValueError):
            parse_records('category,amount\n"unclosed,1\n')

    def test_header_only(self):
        self.assertEqual(parse_records("category,amount\n"), [])
