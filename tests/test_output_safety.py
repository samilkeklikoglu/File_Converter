import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
from pypdf import PdfWriter

from core.image_convert import convert_images
from core.pdf_split import split_pdf_by_pages
from core.pdf_to_image import convert_pdf_to_images
from core.pdf_to_word import convert_pdf_to_word
from core.worker import CancelledException


class OutputSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="fileconverter_safety_")
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_image_batch_failure_removes_outputs_from_current_run(self):
        valid = self.root / "valid.png"
        invalid = self.root / "invalid.png"
        Image.new("RGB", (20, 20), "blue").save(valid)
        invalid.write_bytes(b"not an image")
        output = self.root / "images"

        with self.assertRaises(Exception):
            convert_images([str(valid), str(invalid)], str(output), "JPG")

        self.assertEqual(list(output.glob("*.jpg")), [])

    def test_cancelled_pdf_split_removes_completed_pages(self):
        source = self.root / "source.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.add_blank_page(width=100, height=100)
        with source.open("wb") as handle:
            writer.write(handle)

        checks = 0

        def cancel_after_first_page():
            nonlocal checks
            checks += 1
            return checks >= 3

        output = self.root / "split"
        with self.assertRaises(CancelledException):
            split_pdf_by_pages(
                str(source), str(output), cancel_check=cancel_after_first_page
            )
        self.assertFalse(output.exists())

    def test_pdf_to_word_failure_preserves_existing_output(self):
        source = self.root / "source.pdf"
        source.write_bytes(b"pdf fixture")
        output = self.root / "output.docx"
        output.write_bytes(b"keep existing")

        class FailingConverter:
            def __init__(self, _source):
                pass

            def convert(self, temporary):
                Path(temporary).write_bytes(b"partial")
                raise RuntimeError("conversion stopped")

            def close(self):
                pass

        with (
            patch.dict(
                sys.modules,
                {"pdf2docx": SimpleNamespace(Converter=FailingConverter)},
            ),
            self.assertRaisesRegex(RuntimeError, "conversion stopped"),
        ):
            convert_pdf_to_word(str(source), str(output))

        self.assertEqual(output.read_bytes(), b"keep existing")

    def test_pdf_to_image_validates_format_and_dpi(self):
        source = self.root / "source.pdf"
        source.write_bytes(b"fixture")
        with self.assertRaisesRegex(ValueError, "output format"):
            convert_pdf_to_images(str(source), str(self.root / "out"), "BMP")
        with self.assertRaisesRegex(ValueError, "DPI"):
            convert_pdf_to_images(str(source), str(self.root / "out"), "PNG", 0)


if __name__ == "__main__":
    unittest.main()
