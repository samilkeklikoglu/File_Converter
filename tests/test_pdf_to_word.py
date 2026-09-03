import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.pdf_to_word import convert_pdf_to_word


class PdfToWordResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="fileconverter_pdf_word_")
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "source.pdf"
        self.source.write_bytes(b"pdf fixture")
        self.output = self.root / "output.docx"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_closes_converter_after_success(self):
        instances = []

        class FakeConverter:
            def __init__(self, source):
                self.source = source
                self.closed = False
                instances.append(self)

            def convert(self, output):
                Path(output).write_bytes(b"docx fixture")

            def close(self):
                self.closed = True

        with patch.dict(sys.modules, {"pdf2docx": SimpleNamespace(Converter=FakeConverter)}):
            result = convert_pdf_to_word(str(self.source), str(self.output))

        self.assertEqual(Path(result), self.output)
        self.assertTrue(instances[0].closed)

    def test_closes_converter_after_conversion_error(self):
        instances = []

        class FailingConverter:
            def __init__(self, source):
                self.source = source
                self.closed = False
                instances.append(self)

            def convert(self, output):
                raise ValueError("layout failure")

            def close(self):
                self.closed = True

        with (
            patch.dict(
                sys.modules,
                {"pdf2docx": SimpleNamespace(Converter=FailingConverter)},
            ),
            self.assertRaisesRegex(RuntimeError, "layout failure"),
        ):
            convert_pdf_to_word(str(self.source), str(self.output))

        self.assertTrue(instances[0].closed)


if __name__ == "__main__":
    unittest.main()
