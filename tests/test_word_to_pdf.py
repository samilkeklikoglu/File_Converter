import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.word_to_pdf import convert_word_to_pdf


class WordToPdfTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="fileconverter_word_unit_")
        self.root = Path(self.temp_dir.name)
        self.output = self.root / "output"
        self.output.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _source(self, relative_path: str) -> Path:
        source = self.root / relative_path
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"word fixture")
        return source

    def test_batch_conversion_preserves_existing_outputs(self):
        first = self._source("first.docx")
        second = self._source("nested/first.docx")
        existing = self.output / "first.pdf"
        existing.write_bytes(b"keep me")
        calls = []

        def fake_convert(source, output):
            calls.append((source, output))
            Path(output).write_bytes(b"generated pdf")

        progress = []
        statuses = []
        fake_module = SimpleNamespace(convert=fake_convert)
        with (
            patch.dict(sys.modules, {"docx2pdf": fake_module}),
            patch("core.word_to_pdf.sys.platform", "win32"),
        ):
            result = convert_word_to_pdf(
                [str(first), str(second)],
                str(self.output),
                progress_callback=progress.append,
                status_callback=statuses.append,
            )

        self.assertEqual(Path(result), self.output)
        self.assertEqual(existing.read_bytes(), b"keep me")
        self.assertTrue((self.output / "first_1.pdf").exists())
        self.assertTrue((self.output / "first_2.pdf").exists())
        self.assertEqual(len(calls), 2)
        self.assertEqual(progress, [0, 50, 100])
        self.assertEqual(len(statuses), 3)

    def test_validates_inputs_before_conversion(self):
        with self.assertRaisesRegex(ValueError, "seçilmedi"):
            convert_word_to_pdf([], str(self.output))

        unsupported = self._source("notes.txt")
        with self.assertRaisesRegex(ValueError, "Desteklenmeyen"):
            convert_word_to_pdf([str(unsupported)], str(self.output))

        with self.assertRaises(FileNotFoundError):
            convert_word_to_pdf([str(self.root / "missing.docx")], str(self.output))

    def test_translates_permission_errors(self):
        source = self._source("locked.docx")

        def fail_convert(_source, _output):
            raise PermissionError("Access is denied")

        fake_module = SimpleNamespace(convert=fail_convert)
        with (
            patch.dict(sys.modules, {"docx2pdf": fake_module}),
            patch("core.word_to_pdf.sys.platform", "win32"),
            self.assertRaisesRegex(PermissionError, "erişilemiyor"),
        ):
            convert_word_to_pdf([str(source)], str(self.output))


if __name__ == "__main__":
    unittest.main()
