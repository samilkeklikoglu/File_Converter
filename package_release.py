"""Create versioned portable and checksum assets for a GitHub release."""

from __future__ import annotations

import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app_info import APP_NAME, APP_VERSION


PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
LEGAL_FILES = (
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "PRIVACY.md",
    "CHANGELOG.md",
    "README.md",
)


def _sha256(path: Path) -> str:
    """Return the lowercase SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_release(
    project_root: Path = PROJECT_ROOT,
    dist_dir: Path = DIST_DIR,
) -> tuple[Path, Path]:
    """Build the portable ZIP and SHA256SUMS file from verified build outputs."""
    executable = dist_dir / f"{APP_NAME}.exe"
    installer = dist_dir / f"{APP_NAME}-{APP_VERSION}-Setup.exe"
    missing = [path for path in (executable, installer) if not path.is_file()]
    if missing:
        names = ", ".join(path.name for path in missing)
        raise FileNotFoundError(f"Missing release output: {names}")

    portable = dist_dir / f"{APP_NAME}-{APP_VERSION}-Portable.zip"
    with ZipFile(portable, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        archive.write(executable, arcname=f"{APP_NAME}.exe")
        for name in LEGAL_FILES:
            source = project_root / name
            if not source.is_file():
                raise FileNotFoundError(f"Missing release document: {name}")
            archive.write(source, arcname=name)

    checksum_file = dist_dir / "SHA256SUMS.txt"
    assets = (installer, portable)
    checksum_file.write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in assets),
        encoding="utf-8",
        newline="\n",
    )
    return portable, checksum_file


if __name__ == "__main__":
    portable_path, checksums_path = package_release()
    print(f"[+] Portable package: {portable_path}")
    print(f"[+] Checksums: {checksums_path}")
