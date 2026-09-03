import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build


class BuildScriptTests(unittest.TestCase):
    def test_uses_current_python_to_run_pyinstaller(self):
        with tempfile.TemporaryDirectory(prefix="fileconverter_build_unit_") as temp_dir:
            dist_dir = Path(temp_dir) / "dist"
            dist_dir.mkdir()

            def fake_check_call(command, cwd):
                self.assertEqual(command[:3], [build.sys.executable, "-m", "PyInstaller"])
                self.assertEqual(cwd, build.PROJECT_ROOT)
                icon_path = build.PROJECT_ROOT / "assets" / "fileconverter.ico"
                self.assertIn(f"--icon={icon_path}", command)
                self.assertIn(
                    f"--add-data={icon_path}{build.os.pathsep}assets",
                    command,
                )
                self.assertIn(
                    f"--additional-hooks-dir={build.HOOKS_DIR}",
                    command,
                )
                for module in build.PYINSTALLER_EXCLUDES:
                    self.assertIn(f"--exclude-module={module}", command)
                self.assertTrue((build.HOOKS_DIR / "hook-cv2.py").is_file())
                self.assertTrue((build.HOOKS_DIR / "hook-qtawesome.py").is_file())
                self.assertTrue(
                    (build.HOOKS_DIR / "hook-PySide6.QtGui.py").is_file()
                )
                (dist_dir / "FileConverter.exe").write_bytes(b"executable")

            with (
                patch.object(build, "DIST_DIR", dist_dir),
                patch.object(build, "_ensure_pyinstaller"),
                patch.object(build, "_clean_previous_builds"),
                patch.object(build.subprocess, "check_call", side_effect=fake_check_call),
            ):
                result = build.build_app()

            self.assertEqual(result, dist_dir / "FileConverter.exe")

    def test_reports_missing_executable(self):
        with tempfile.TemporaryDirectory(prefix="fileconverter_build_unit_") as temp_dir:
            dist_dir = Path(temp_dir) / "dist"
            dist_dir.mkdir()
            with (
                patch.object(build, "DIST_DIR", dist_dir),
                patch.object(build, "_ensure_pyinstaller"),
                patch.object(build, "_clean_previous_builds"),
                patch.object(build.subprocess, "check_call"),
                self.assertRaisesRegex(RuntimeError, "was not created"),
            ):
                build.build_app()


if __name__ == "__main__":
    unittest.main()
