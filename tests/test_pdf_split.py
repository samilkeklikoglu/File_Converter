import unittest

from core.pdf_split import parse_page_ranges


class ParsePageRangesTests(unittest.TestCase):
    def test_parses_pages_and_ranges(self):
        self.assertEqual(
            parse_page_ranges("1-3, 5, 7-9", 9),
            [(1, 3), (5, 5), (7, 9)],
        )

    def test_rejects_invalid_ranges(self):
        for value in ("", "0", "10", "4-2", "1-a", "1--2"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_page_ranges(value, 9)

    def test_allows_whitespace(self):
        self.assertEqual(parse_page_ranges(" 1 - 2 , 4 ", 4), [(1, 2), (4, 4)])

    def test_rejects_equivalent_duplicate_ranges(self):
        for value in ("1, 1", "1, 1-1", "1-3, 1-3"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "Duplicate"):
                    parse_page_ranges(value, 5)


if __name__ == "__main__":
    unittest.main()
