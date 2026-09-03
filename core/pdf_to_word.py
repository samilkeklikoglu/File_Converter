"""
core/pdf_to_word.py — PDF → Word Conversion Engine

Converts a PDF file into an editable Word document (.docx).
Uses pdf2docx for layout analysis and reconstruction.
"""

from pathlib import Path
from typing import Callable

from core.output_utils import atomic_output_path


def convert_pdf_to_word(
    pdf_path: str,
    output_path: str,
    progress_callback: Callable[[int], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> str:
    """
    Converts a PDF document to an editable .docx file.

    Args:
        pdf_path:          Full path to the source PDF file.
        output_path:       Full path where the resulting .docx will be saved.
        progress_callback: Called with an integer (0-100) to report progress.
        status_callback:   Called with a status string for UI feedback.

    Returns:
        Full path of the generated .docx file.

    Raises:
        FileNotFoundError: If the input PDF does not exist.
        RuntimeError:      If the conversion fails.
    """
    try:
        from pdf2docx import Converter  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "The pdf2docx package is not installed. "
            "Install it with 'pip install pdf2docx'."
        )

    source = Path(pdf_path)
    if not source.is_file():
        raise FileNotFoundError(f"File not found: {source.name}")

    output = Path(output_path)
    if output.suffix.lower() != ".docx":
        raise ValueError("The Word output must have a .docx extension.")
    if source.resolve() == output.resolve():
        raise ValueError("The source PDF and Word output cannot be the same file.")

    if status_callback:
        status_callback("Analyzing PDF...")
    if progress_callback:
        progress_callback(10)

    if cancel_check and cancel_check():
        from core.worker import CancelledException
        raise CancelledException("Operation cancelled.")

    try:
        with atomic_output_path(output) as temporary:
            cv = None
            try:
                cv = Converter(str(source))

                if status_callback:
                    status_callback("Extracting text and tables...")
                if progress_callback:
                    progress_callback(30)

                cv.convert(str(temporary))
            finally:
                if cv is not None:
                    try:
                        cv.close()
                    except Exception:
                        pass

            if cancel_check and cancel_check():
                from core.worker import CancelledException
                raise CancelledException("Operation cancelled.")

    except Exception as exc:
        from core.worker import CancelledException
        if isinstance(exc, CancelledException):
            raise
        raise RuntimeError(
            f"Conversion failed. The PDF may be protected or corrupt.\n\nTechnical details: {exc}"
        ) from exc

    if not output.exists():
        raise RuntimeError("The Word document could not be created.")

    if progress_callback:
        progress_callback(100)
    if status_callback:
        status_callback(f"Complete! → {output.name}")

    return str(output)
