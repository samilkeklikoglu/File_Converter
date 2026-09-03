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
            "pdf2docx kütüphanesi bulunamadı. "
            "Lütfen 'pip install pdf2docx' komutuyla yükleyin."
        )

    source = Path(pdf_path)
    if not source.is_file():
        raise FileNotFoundError(f"Dosya bulunamadı: {source.name}")

    output = Path(output_path)
    if output.suffix.lower() != ".docx":
        raise ValueError("Word çıktısı .docx uzantılı olmalıdır.")
    if source.resolve() == output.resolve():
        raise ValueError("Kaynak PDF ile Word çıktısı aynı dosya olamaz.")

    if status_callback:
        status_callback("PDF analizi yapılıyor...")
    if progress_callback:
        progress_callback(10)

    if cancel_check and cancel_check():
        from core.worker import CancelledException
        raise CancelledException("İşlem iptal edildi.")

    try:
        with atomic_output_path(output) as temporary:
            cv = None
            try:
                cv = Converter(str(source))

                if status_callback:
                    status_callback("Metin ve tablolar ayrıştırılıyor...")
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
                raise CancelledException("İşlem iptal edildi.")

    except Exception as exc:
        from core.worker import CancelledException
        if isinstance(exc, CancelledException):
            raise
        raise RuntimeError(
            f"Dönüşüm başarısız oldu. PDF korumalı veya bozuk olabilir.\n\nTeknik detay: {exc}"
        ) from exc

    if not output.exists():
        raise RuntimeError("Word belgesi oluşturulamadı.")

    if progress_callback:
        progress_callback(100)
    if status_callback:
        status_callback(f"Tamamlandı! → {output.name}")

    return str(output)
