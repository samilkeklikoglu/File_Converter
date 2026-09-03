import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter

from core.pdf_merge import merge_pdfs


class PdfMergeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="fileconverter_merge_unit_")
        self.root = Path(self.temp_dir.name)
        self.first = self.root / "first.pdf"
        self.second = self.root / "second.pdf"
        self._make_pdf(self.first, 1)
        self._make_pdf(self.second, 2)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def _make_pdf(path: Path, pages: int) -> None:
        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(width=200, height=300)
        with path.open("wb") as handle:
            writer.write(handle)

    def test_merges_pages(self):
        output = self.root / "merged.pdf"
        merge_pdfs([str(self.first), str(self.second)], str(output))
        self.assertEqual(len(PdfReader(str(output)).pages), 3)

    def test_rejects_input_file_as_output(self):
        original = self.first.read_bytes()
        with self.assertRaisesRegex(ValueError, "source PDFs"):
            merge_pdfs([str(self.first), str(self.second)], str(self.first))
        self.assertEqual(self.first.read_bytes(), original)

    def test_failed_atomic_write_preserves_existing_output(self):
        output = self.root / "protected.pdf"
        output.write_bytes(b"keep existing output")

        with (
            patch.object(PdfWriter, "write", side_effect=OSError("disk failure")),
            self.assertRaisesRegex(RuntimeError, "disk failure"),
        ):
            merge_pdfs([str(self.first), str(self.second)], str(output))

        self.assertEqual(output.read_bytes(), b"keep existing output")
        self.assertEqual(list(self.root.glob(".protected.*.tmp")), [])

    def test_requires_pdf_output_extension(self):
        with self.assertRaisesRegex(ValueError, r"\.pdf"):
            merge_pdfs(
                [str(self.first), str(self.second)],
                str(self.root / "merged.txt"),
            )


if __name__ == "__main__":
    unittest.main()
