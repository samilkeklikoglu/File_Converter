"""Build FileConverter as a standalone Windows executable with PyInstaller."""

import os
from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
ENTRY_POINT = PROJECT_ROOT / "main.py"
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_REQUIREMENTS = PROJECT_ROOT / "requirements-build.txt"
APP_NAME = "FileConverter"


def _ensure_pyinstaller() -> None:
    """Install the pinned build dependencies when PyInstaller is unavailable."""
    try:
        import PyInstaller  # noqa: F401, PLC0415
    except ImportError:
        print("[*] PyInstaller not found; installing build dependencies...")
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                str(BUILD_REQUIREMENTS),
            ],
            cwd=PROJECT_ROOT,
        )
    else:
        print("[+] PyInstaller is ready.")


def _clean_previous_builds() -> None:
    """Remove generated build directories within the project root."""
    print("[*] Cleaning previous build outputs...")
    for directory in (BUILD_DIR, DIST_DIR):
        if directory.exists():
            shutil.rmtree(directory)


def build_app() -> Path:
    """Create and return the path of the standalone executable."""
    print("=== FileConverter Standalone Build ===")
    _ensure_pyinstaller()
    _clean_previous_builds()

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--noconsole",
        "--onefile",
        f"--name={APP_NAME}",
        f"--workpath={BUILD_DIR}",
        f"--distpath={DIST_DIR}",
        f"--specpath={BUILD_DIR}",
    ]

    icon_path = PROJECT_ROOT / "assets" / "fileconverter.ico"
    if icon_path.exists():
        command.append(f"--icon={icon_path}")
        command.append(f"--add-data={icon_path}{os.pathsep}assets")
    else:
        print("[!] assets/fileconverter.ico not found; using the default icon.")

    command.append(str(ENTRY_POINT))
    print(f"[*] Running: {sys.executable} -m PyInstaller ...")
    subprocess.check_call(command, cwd=PROJECT_ROOT)

    executable = DIST_DIR / f"{APP_NAME}.exe"
    if not executable.is_file() or executable.stat().st_size == 0:
        raise RuntimeError("The build completed, but FileConverter.exe was not created.")

    print("\n==============================================")
    print("[+] BUILD SUCCEEDED")
    print(f"[+] Output: {executable}")
    print("==============================================")
    return executable


if __name__ == "__main__":
    try:
        build_app()
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"[-] Build failed: {exc}")
        raise SystemExit(1) from exc
