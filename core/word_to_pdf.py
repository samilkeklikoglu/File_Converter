"""
core/word_to_pdf.py — Word → PDF Dönüşüm Motoru

Converts .docx / .doc files to PDF using Microsoft Word via the docx2pdf library.
Requires Microsoft Word on Windows or macOS.
"""

import sys
from pathlib import Path
from typing import Callable


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
            f"'{source.name}' dosyasına erişilemiyor. "
            "Dosya başka bir program tarafından açık olabilir. "
            "Lütfen dosyayı kapatıp tekrar deneyin.\n\n"
            f"Teknik detay: {error_msg}"
        ) from exc

    if any(
        token in lowered
        for token in ("word", "com_error", "comtypes", "class not registered")
    ):
        raise RuntimeError(
            "Microsoft Word bulunamadı veya başlatılamadı.\n"
            "Word → PDF dönüşümü için Microsoft Word kurulu olmalıdır.\n\n"
            f"Teknik detay: {error_msg}"
        ) from exc

    raise RuntimeError(
        f"'{source.name}' dönüştürülürken beklenmedik bir hata oluştu:\n{error_msg}"
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
        raise ValueError("Dönüştürülecek Word belgesi seçilmedi.")

    sources = [Path(path) for path in input_paths]
    for source in sources:
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Dosya bulunamadı: {source.name}")
        if source.suffix.lower() not in WORD_EXTENSIONS:
            raise ValueError(
                f"Desteklenmeyen dosya formatı: '{source.suffix}'. "
                "Yalnızca .docx ve .doc dosyaları dönüştürülebilir."
            )

    if sys.platform not in ("win32", "darwin"):
        raise EnvironmentError(
            "Word → PDF dönüşümü yalnızca Microsoft Word kurulu Windows "
            "ve macOS sistemlerinde desteklenir."
        )

    try:
        import docx2pdf  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "docx2pdf kütüphanesi bulunamadı. "
            "Lütfen 'pip install docx2pdf' komutuyla yükleyin."
        )

    output_folder = Path(output_dir)
    output_folder.mkdir(parents=True, exist_ok=True)

    total = len(sources)
    if progress_callback:
        progress_callback(0)

    for index, source in enumerate(sources):
        if cancel_check and cancel_check():
            from core.worker import CancelledException
            raise CancelledException("İşlem iptal edildi.")

        output_path = _get_unique_output_path(output_folder, source)

        if status_callback:
            status_callback(
                f"Dönüştürülüyor: {source.name}  ({index + 1}/{total})"
            )

        try:
            docx2pdf.convert(str(source), str(output_path))
        except Exception as exc:
            _raise_conversion_error(source, exc)

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(
                f"'{source.name}' için dönüşüm tamamlandı ancak PDF "
                "dosyası oluşturulamadı. Microsoft Word kurulumunu kontrol edin."
            )

        if progress_callback:
            progress_callback(int((index + 1) / total * 100))

    if status_callback:
        status_callback(f"Tamamlandı! {total} Word belgesi PDF'e dönüştürüldü.")

    return str(output_folder)
