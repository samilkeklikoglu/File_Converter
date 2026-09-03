import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from app_info import APP_NAME, APP_VERSION
from package_release import LEGAL_FILES, package_release


class ReleasePackageTests(unittest.TestCase):
    def test_portable_archive_contains_binary_and_legal_documents(self):
        with tempfile.TemporaryDirectory(prefix="fileconverter_release_") as temp_dir:
            root = Path(temp_dir)
            dist = root / "dist"
            dist.mkdir()
            (dist / f"{APP_NAME}.exe").write_bytes(b"portable")
            installer_name = f"{APP_NAME}-{APP_VERSION}-Setup.exe"
            portable_name = f"{APP_NAME}-{APP_VERSION}-Portable.zip"
            (dist / installer_name).write_bytes(b"installer")
            for name in LEGAL_FILES:
                (root / name).write_text(name, encoding="utf-8")

            portable, checksums = package_release(root, dist)

            with ZipFile(portable) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {f"{APP_NAME}.exe", *LEGAL_FILES},
                )
            checksum_text = checksums.read_text(encoding="utf-8")
            self.assertIn(installer_name, checksum_text)
            self.assertIn(portable_name, checksum_text)


if __name__ == "__main__":
    unittest.main()
