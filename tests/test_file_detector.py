import tempfile
import unittest
from pathlib import Path

from core.file_detector import detect_type, expand_supported_paths, get_type_label


class FileDetectorTests(unittest.TestCase):
    def test_detects_supported_types_case_insensitively(self):
        cases = [
            (["photo.JPG", "scan.png"], "image"),
            (["report.DOCX", "legacy.doc"], "word"),
            (["one.PDF", "two.pdf"], "pdf"),
        ]
        for paths, expected in cases:
            with self.subTest(paths=paths):
                self.assertEqual(detect_type(paths), expected)

    def test_detects_mixed_and_unsupported_inputs(self):
        self.assertEqual(detect_type(["one.pdf", "photo.png"]), "mixed")
        self.assertEqual(detect_type(["one.pdf", "notes.txt"]), "unsupported")
        self.assertEqual(detect_type([]), "unsupported")

    def test_returns_localized_label(self):
        self.assertEqual(get_type_label("image", 3), "3 image files detected")
        self.assertEqual(get_type_label("pdf", 1), "1 PDF file detected")

    def test_folder_expansion_is_filtered_deduplicated_and_sorted(self):
        with tempfile.TemporaryDirectory(prefix="fileconverter_scan_") as temp_dir:
            root = Path(temp_dir)
            (root / "B.pdf").write_bytes(b"fixture")
            (root / "a.png").write_bytes(b"fixture")
            (root / "notes.txt").write_bytes(b"fixture")

            expanded = expand_supported_paths([str(root), str(root / "a.png")])
            self.assertEqual(
                [Path(path).name for path in expanded],
                ["a.png", "B.pdf"],
            )


if __name__ == "__main__":
    unittest.main()
