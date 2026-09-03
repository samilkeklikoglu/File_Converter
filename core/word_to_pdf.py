"""
core/word_to_pdf.py — Word to PDF Conversion Engine

Converts .docx / .doc files to PDF using Microsoft Word via the docx2pdf library.
Requires Microsoft Word on Windows or macOS.
"""

import sys
from pathlib import Path
from typing import Callable

from core.output_utils import atomic_output_path, cleanup_created_files


WORD_EXTENSIONS: frozenset[str] = frozenset({".docx", ".doc"})


def _get_unique_output_path(output_folder: Path, source: Path) -> Path:
    """Build a PDF output path without overwriting an existing file."""
    candidate = output_folder / f"{source.stem}.pdf"
    counter = 1
    while candidate.exists():
        candidate = output_folder / f"{source.stem}_{counter}.pdf"
        counter += 1
    return candidate


def _raise_conversion_error(source: Path, exc: Exception) -> None:
    """Translate common Word/COM failures into user-facing exceptions."""
    error_msg = str(exc)
    lowered = error_msg.lower()

    if (
        isinstance(exc, PermissionError)
        or "access is denied" in lowered
        or "permission denied" in lowered
    ):
        raise PermissionError(
            f"Cannot access '{source.name}'. "
            "The file may be open in another application. "
            "Close it and try again.\n\n"
            f"Technical details: {error_msg}"
        ) from exc

    if any(
        token in lowered
        for token in ("word", "com_error", "comtypes", "class not registered")
    ):
        raise RuntimeError(
            "Microsoft Word could not be found or started.\n"
            "Microsoft Word must be installed for Word to PDF conversion.\n\n"
            f"Technical details: {error_msg}"
        ) from exc

    raise RuntimeError(
        f"An unexpected error occurred while converting '{source.name}':\n{error_msg}"
    ) from exc


def convert_word_to_pdf(
    input_paths: list[str],
    output_dir: str,
    progress_callback: Callable[[int], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> str:
    """
    Converts a list of Word documents to PDF.

    Args:
        input_paths:       List of full paths to the .docx / .doc files.
        output_dir:        Directory where the resulting PDFs will be saved.
        progress_callback: Called with an integer (0-100) to report progress.
        status_callback:   Called with a status string for UI feedback.

    Returns:
        Full path of the generated output directory.

    Raises:
        FileNotFoundError: If any input file does not exist.
        ValueError:        If any file extension is not supported.
        EnvironmentError:  If the platform is not supported.
        RuntimeError:      If conversion fails.
    """
    if not input_paths:
        raise ValueError("No Word documents were selected for conversion.")

    sources = [Path(path) for path in input_paths]
    for source in sources:
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"File not found: {source.name}")
        if source.suffix.lower() not in WORD_EXTENSIONS:
            raise ValueError(
                f"Unsupported file format: '{source.suffix}'. "
                "Only .docx and .doc files can be converted."
            )

    if sys.platform not in ("win32", "darwin"):
        raise EnvironmentError(
            "Word to PDF conversion is supported only on Windows and macOS "
            "systems with Microsoft Word installed."
        )

    try:
        import docx2pdf  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "The docx2pdf package is not installed. "
            "Install it with 'pip install docx2pdf'."
        )

    output_folder = Path(output_dir)
    output_folder.mkdir(parents=True, exist_ok=True)

    total = len(sources)
    created_files: list[Path] = []
    if progress_callback:
        progress_callback(0)

    try:
        for index, source in enumerate(sources):
            if cancel_check and cancel_check():
                from core.worker import CancelledException
                raise CancelledException("Operation cancelled.")

            output_path = _get_unique_output_path(output_folder, source)

            if status_callback:
                status_callback(
                    f"Converting: {source.name}  ({index + 1}/{total})"
                )

            try:
                with atomic_output_path(output_path) as temporary:
                    docx2pdf.convert(str(source), str(temporary))
                    if cancel_check and cancel_check():
                        from core.worker import CancelledException
                        raise CancelledException("Operation cancelled.")
            except Exception as exc:
                from core.worker import CancelledException
                if isinstance(exc, CancelledException):
                    raise
                _raise_conversion_error(source, exc)

            created_files.append(output_path)
            if progress_callback:
                progress_callback(int((index + 1) / total * 100))
    except Exception:
        cleanup_created_files(created_files)
        raise

    if status_callback:
        status_callback(f"Complete! {total} Word documents converted to PDF.")

    return str(output_folder)
