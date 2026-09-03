import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from package_release import LEGAL_FILES, package_release


class ReleasePackageTests(unittest.TestCase):
    def test_portable_archive_contains_binary_and_legal_documents(self):
        with tempfile.TemporaryDirectory(prefix="fileconverter_release_") as temp_dir:
            root = Path(temp_dir)
            dist = root / "dist"
            dist.mkdir()
            (dist / "FileConverter.exe").write_bytes(b"portable")
            (dist / "FileConverter-2.0.0-Setup.exe").write_bytes(b"installer")
            for name in LEGAL_FILES:
                (root / name).write_text(name, encoding="utf-8")

            portable, checksums = package_release(root, dist)

            with ZipFile(portable) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {"FileConverter.exe", *LEGAL_FILES},
                )
            checksum_text = checksums.read_text(encoding="utf-8")
            self.assertIn("FileConverter-2.0.0-Setup.exe", checksum_text)
            self.assertIn("FileConverter-2.0.0-Portable.zip", checksum_text)


if __name__ == "__main__":
    unittest.main()
