"""
core/pdf_merge.py — PDF Merge Engine

Merges multiple PDF files into a single document using pypdf.
Works on all platforms without external dependencies beyond the library itself.
"""

from contextlib import ExitStack
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Callable


def merge_pdfs(
    input_paths: list[str],
    output_path: str,
    progress_callback: Callable[[int], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> str:
    """
    Merges a list of PDF files into one output PDF, preserving page order.

    Args:
        input_paths:       Ordered list of full paths to the PDF files to merge.
        output_path:       Full path for the resulting merged PDF.
        progress_callback: Called with an integer (0-100) to report progress.
        status_callback:   Called with a status string for UI feedback.

    Returns:
        Full path of the generated PDF file.

    Raises:
        ValueError:       If fewer than two PDFs are provided.
        FileNotFoundError: If any input file does not exist.
        PermissionError:  If a file is encrypted or cannot be written.
        RuntimeError:     If a file is corrupt or output cannot be created.
    """
    if not input_paths:
        raise ValueError("Select at least one PDF file.")

    if len(input_paths) < 2:
        raise ValueError("Select at least two PDF files to merge.")

    for path_str in input_paths:
        p = Path(path_str)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p.name}")
        if p.suffix.lower() != ".pdf":
            raise ValueError(
                f"'{p.name}' is not a PDF file. "
                "Only files with a .pdf extension are accepted."
            )

    try:
        from pypdf import PdfWriter, PdfReader  # noqa: PLC0415
        from pypdf.errors import PdfReadError  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "The pypdf package is not installed. "
            "Install it with 'pip install pypdf'."
        )

    output = Path(output_path)
    if output.suffix.lower() != ".pdf":
        raise ValueError("The merged output must have a .pdf extension.")

    resolved_output = output.resolve()
    for path_str in input_paths:
        if Path(path_str).resolve() == resolved_output:
            raise ValueError(
                "The output cannot be one of the source PDFs. "
                "Choose a different name or location to protect the source files."
            )

    output.parent.mkdir(parents=True, exist_ok=True)

    writer = PdfWriter()
    total = len(input_paths)

    if status_callback:
        status_callback(f"Starting... ({total} files)")
    if progress_callback:
        progress_callback(5)

    with ExitStack() as source_files:
        for i, path_str in enumerate(input_paths):
            if cancel_check and cancel_check():
                from core.worker import CancelledException
                raise CancelledException("Operation cancelled.")

            p = Path(path_str)
            if status_callback:
                status_callback(f"Processing: {p.name}  ({i + 1}/{total})")

            try:
                source_handle = source_files.enter_context(p.open("rb"))
                reader = PdfReader(source_handle)

                if reader.is_encrypted:
                    raise PermissionError(
                        f"'{p.name}' is an encrypted PDF. "
                        "Encrypted PDFs cannot be merged. "
                        "Remove the password protection first."
                    )

                for page in reader.pages:
                    writer.add_page(page)
            except PdfReadError as exc:
                raise RuntimeError(
                    f"'{p.name}' could not be read. "
                    f"The file may be corrupt or invalid.\n\nTechnical details: {exc}"
                ) from exc
            except PermissionError:
                raise
            except Exception as exc:
                raise RuntimeError(
                    f"An unexpected error occurred while processing '{p.name}':\n{exc}"
                ) from exc

            if progress_callback:
                progress_callback(5 + int((i + 1) / total * 85))

        if status_callback:
            status_callback("Saving PDF...")
        if progress_callback:
            progress_callback(92)

        if cancel_check and cancel_check():
            from core.worker import CancelledException
            raise CancelledException("Operation cancelled.")

        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="wb",
                prefix=f".{output.stem}.",
                suffix=".tmp",
                dir=output.parent,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                writer.write(temporary_file)

            if temporary_path.stat().st_size == 0:
                raise RuntimeError(
                    "The merge completed, but the temporary output file is empty."
                )
            temporary_path.replace(output)
        except PermissionError as exc:
            raise PermissionError(
                f"Cannot write to '{output.name}'. "
                "The file may be open in another application."
            ) from exc
        except Exception as exc:
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(
                f"An unexpected error occurred while saving '{output.name}':\n{exc}"
            ) from exc
        finally:
            if temporary_path and temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    pass

    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError(
            "The merge completed, but the output file was not created."
        )

    if progress_callback:
        progress_callback(100)
    if status_callback:
        status_callback(f"Complete! → {output.name}")

    return str(output)
