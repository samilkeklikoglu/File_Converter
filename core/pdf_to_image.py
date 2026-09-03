"""
core/pdf_to_image.py — PDF → Image Conversion Engine

Converts pages of a PDF document into individual image files (PNG or JPG).
Uses PyMuPDF (fitz) for rendering.
"""

from pathlib import Path
from typing import Callable

from core.output_utils import atomic_output_path, cleanup_created_files


def convert_pdf_to_images(
    pdf_path: str,
    output_dir: str,
    output_format: str = "PNG",
    dpi: int = 150,
    progress_callback: Callable[[int], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> str:
    """
    Converts each page of a PDF file to a separate image file.

    Args:
        pdf_path:          Full path to the source PDF.
        output_dir:        Directory where images will be saved.
        output_format:     Target format, either "PNG" or "JPG" (JPEG).
        dpi:               DPI resolution for rendering (higher means better quality).
        progress_callback: Called with an integer (0-100) to report progress.
        status_callback:   Called with a status string for UI feedback.

    Returns:
        Path of the output directory containing the images.

    Raises:
        FileNotFoundError: If the input PDF does not exist.
        RuntimeError:      If the PDF cannot be opened or is encrypted.
    """
    try:
        import pymupdf as fitz  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "pymupdf kütüphanesi bulunamadı. "
            "Lütfen 'pip install pymupdf' komutuyla yükleyin."
        )

    source = Path(pdf_path)
    if not source.is_file():
        raise FileNotFoundError(f"Dosya bulunamadı: {source.name}")

    fmt_key = output_format.upper()
    if fmt_key not in {"PNG", "JPG", "JPEG"}:
        raise ValueError("Çıktı formatı PNG veya JPG olmalıdır.")
    if not isinstance(dpi, int) or isinstance(dpi, bool) or not 36 <= dpi <= 1200:
        raise ValueError("DPI değeri 36 ile 1200 arasında bir tam sayı olmalıdır.")

    output_folder = Path(output_dir)
    folder_existed = output_folder.exists()
    output_folder.mkdir(parents=True, exist_ok=True)
    created_files: list[Path] = []
    doc = None

    try:
        doc = fitz.open(source)
    except Exception as exc:
        raise RuntimeError(
            f"PDF dosyası açılamadı. Dosya bozuk olabilir.\n\nTeknik detay: {exc}"
        ) from exc

    try:
        if doc.is_encrypted:
            raise RuntimeError(
                f"'{source.name}' şifreli bir PDF dosyasıdır. "
                "Şifreli PDF'ler resme dönüştürülemez."
            )

        total_pages = len(doc)
        if total_pages == 0:
            raise RuntimeError("PDF dosyası boş.")

        fmt = "JPEG" if fmt_key in {"JPG", "JPEG"} else "PNG"
        ext = ".jpg" if fmt == "JPEG" else ".png"
        pad = len(str(total_pages))
        output_paths = [
            output_folder / f"{source.stem}_page_{str(page).zfill(pad)}{ext}"
            for page in range(1, total_pages + 1)
        ]
        existing = next((path for path in output_paths if path.exists()), None)
        if existing:
            raise FileExistsError(
                f"'{existing.name}' zaten mevcut. Lütfen boş bir çıktı klasörü seçin."
            )

        if status_callback:
            status_callback(f"Sayfalar işleniyor... (Toplam {total_pages} sayfa)")
        if progress_callback:
            progress_callback(5)

        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        for i, page in enumerate(doc):
            if cancel_check and cancel_check():
                from core.worker import CancelledException
                raise CancelledException("İşlem iptal edildi.")

            page_num = i + 1
            out_path = output_paths[i]
            if status_callback:
                status_callback(f"Dönüştürülüyor: Sayfa {page_num}/{total_pages}")

            pix = page.get_pixmap(matrix=mat)
            with atomic_output_path(out_path) as temporary:
                pix.save(str(temporary))
                if cancel_check and cancel_check():
                    from core.worker import CancelledException
                    raise CancelledException("İşlem iptal edildi.")
            created_files.append(out_path)

            if progress_callback:
                progress_callback(5 + int(page_num / total_pages * 90))

        if progress_callback:
            progress_callback(100)
        if status_callback:
            status_callback(f"Tamamlandı! {total_pages} sayfa resim olarak kaydedildi.")
    except Exception:
        cleanup_created_files(created_files)
        if not folder_existed:
            try:
                output_folder.rmdir()
            except OSError:
                pass
        raise
    finally:
        if doc is not None:
            doc.close()

    return str(output_folder)
