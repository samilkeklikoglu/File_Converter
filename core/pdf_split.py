"""
core/pdf_split.py — PDF Splitting Engine

Splits a PDF file either by extracting each page individually
or by splitting into custom page ranges (e.g. "1-3, 5, 7-9").
Uses pypdf — no external dependencies required.
"""

from pathlib import Path
from typing import Callable

from core.output_utils import atomic_output_path, cleanup_created_files


def _ensure_outputs_available(paths: list[Path]) -> None:
    """Reject an operation that would overwrite an existing split output."""
    existing = next((path for path in paths if path.exists()), None)
    if existing:
        raise FileExistsError(
            f"'{existing.name}' zaten mevcut. Kaynak dosyaları korumak için "
            "boş bir çıktı klasörü seçin."
        )


def _write_pdf_atomic(writer, output: Path, cancel_check) -> None:
    """Write one PDF through a sibling temporary file."""
    with atomic_output_path(output) as temporary:
        with temporary.open("wb") as handle:
            writer.write(handle)
        if cancel_check and cancel_check():
            from core.worker import CancelledException
            raise CancelledException("İşlem iptal edildi.")


def parse_page_ranges(range_str: str, total_pages: int) -> list[tuple[int, int]]:
    """
    Parses a page range string into a list of (start, end) tuples (1-indexed, inclusive).

    Examples:
        "1-3, 5, 7-9" → [(1, 3), (5, 5), (7, 9)]
        "2"           → [(2, 2)]
        "1-5"         → [(1, 5)]

    Args:
        range_str:    User-supplied range string.
        total_pages:  Total number of pages in the PDF (for bounds checking).

    Returns:
        List of (start, end) tuples, 1-indexed.

    Raises:
        ValueError: If the input is malformed or out of range.
    """
    ranges: list[tuple[int, int]] = []
    seen_ranges: set[tuple[int, int]] = set()

    for part in range_str.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            halves = part.split("-", 1)
            try:
                start = int(halves[0].strip())
                end   = int(halves[1].strip())
            except ValueError:
                raise ValueError(f"Geçersiz aralık: '{part}'")

            if start < 1 or end < 1:
                raise ValueError(f"Sayfa numaraları 1'den küçük olamaz: '{part}'")
            if start > end:
                raise ValueError(f"Başlangıç sayfa bitiş sayfasından büyük olamaz: '{part}'")
            if end > total_pages:
                raise ValueError(
                    f"Sayfa {end} mevcut değil. PDF toplam {total_pages} sayfadan oluşuyor."
                )
            parsed_range = (start, end)
        else:
            try:
                page = int(part)
            except ValueError:
                raise ValueError(f"Geçersiz sayfa numarası: '{part}'")

            if page < 1 or page > total_pages:
                raise ValueError(
                    f"Sayfa {page} mevcut değil. PDF toplam {total_pages} sayfadan oluşuyor."
                )
            parsed_range = (page, page)

        if parsed_range in seen_ranges:
            start, end = parsed_range
            label = str(start) if start == end else f"{start}-{end}"
            raise ValueError(f"Tekrarlanan sayfa aralığı: '{label}'")

        seen_ranges.add(parsed_range)
        ranges.append(parsed_range)

    if not ranges:
        raise ValueError("En az bir sayfa aralığı girilmelidir.")

    return ranges


def split_pdf_by_pages(
    input_path: str,
    output_dir: str,
    progress_callback: Callable[[int], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> str:
    """
    Extracts each page of a PDF into a separate file.

    Output files are named: <stem>_page_01.pdf, <stem>_page_02.pdf, ...

    Args:
        input_path:        Full path to the source PDF.
        output_dir:        Directory where the split PDFs will be saved.
        progress_callback: Called with an integer (0-100) to report progress.
        status_callback:   Called with a status string for UI feedback.

    Returns:
        Path of the output directory.

    Raises:
        FileNotFoundError: If the input file does not exist.
        RuntimeError:      If the PDF is encrypted or cannot be read.
    """
    try:
        from pypdf import PdfWriter, PdfReader  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "pypdf kütüphanesi bulunamadı. "
            "Lütfen 'pip install pypdf' komutuyla yükleyin."
        )

    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {source.name}")

    output_folder = Path(output_dir)
    folder_existed = output_folder.exists()
    output_folder.mkdir(parents=True, exist_ok=True)
    created_files: list[Path] = []

    try:
        with source.open("rb") as source_handle:
            reader = PdfReader(source_handle)

            if reader.is_encrypted:
                raise RuntimeError(
                    f"'{source.name}' şifreli bir PDF dosyasıdır. "
                    "Şifreli PDF'ler işlenemez."
                )

            total = len(reader.pages)
            if total == 0:
                raise RuntimeError("PDF dosyası boş veya okunamıyor.")

            stem = source.stem
            pad = len(str(total))
            output_paths = [
                output_folder / f"{stem}_page_{str(page).zfill(pad)}.pdf"
                for page in range(1, total + 1)
            ]
            _ensure_outputs_available(output_paths)

            if status_callback:
                status_callback(f"Bölünüyor: {source.name}  ({total} sayfa)")
            if progress_callback:
                progress_callback(5)

            for i, page in enumerate(reader.pages):
                if cancel_check and cancel_check():
                    from core.worker import CancelledException
                    raise CancelledException("İşlem iptal edildi.")

                page_num = i + 1
                out_path = output_paths[i]
                writer = PdfWriter()
                writer.add_page(page)
                _write_pdf_atomic(writer, out_path, cancel_check)
                created_files.append(out_path)

                if status_callback:
                    status_callback(f"Kaydediliyor: {out_path.name}  ({page_num}/{total})")
                if progress_callback:
                    progress_callback(5 + int(page_num / total * 90))

        if progress_callback:
            progress_callback(100)
        if status_callback:
            status_callback(f"Tamamlandı! {total} sayfa ayrı PDF olarak kaydedildi.")
    except Exception:
        cleanup_created_files(created_files)
        if not folder_existed:
            try:
                output_folder.rmdir()
            except OSError:
                pass
        raise

    return str(output_folder)


def split_pdf_by_ranges(
    input_path: str,
    output_dir: str,
    range_str: str,
    progress_callback: Callable[[int], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> str:
    """
    Splits a PDF into multiple files according to custom page ranges.

    Each range produces one output file named: <stem>_pp_<start>-<end>.pdf

    Args:
        input_path:        Full path to the source PDF.
        output_dir:        Directory where the split PDFs will be saved.
        range_str:         Page range string, e.g. "1-3, 5, 7-9".
        progress_callback: Called with an integer (0-100) to report progress.
        status_callback:   Called with a status string for UI feedback.

    Returns:
        Path of the output directory.

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError:        If range_str is malformed or out of bounds.
        RuntimeError:      If the PDF is encrypted or cannot be read.
    """
    try:
        from pypdf import PdfWriter, PdfReader  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "pypdf kütüphanesi bulunamadı. "
            "Lütfen 'pip install pypdf' komutuyla yükleyin."
        )

    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {source.name}")

    output_folder = Path(output_dir)
    folder_existed = output_folder.exists()
    output_folder.mkdir(parents=True, exist_ok=True)
    created_files: list[Path] = []

    try:
        with source.open("rb") as source_handle:
            reader = PdfReader(source_handle)

            if reader.is_encrypted:
                raise RuntimeError(
                    f"'{source.name}' şifreli bir PDF dosyasıdır. "
                    "Şifreli PDF'ler işlenemez."
                )

            total_pages = len(reader.pages)
            if total_pages == 0:
                raise RuntimeError("PDF dosyası boş veya okunamıyor.")

            ranges = parse_page_ranges(range_str, total_pages)
            output_paths = [
                output_folder / f"{source.stem}_pp_{start}-{end}.pdf"
                for start, end in ranges
            ]
            _ensure_outputs_available(output_paths)

            if status_callback:
                status_callback(f"Bölünüyor: {source.name}  ({len(ranges)} bölüm)")
            if progress_callback:
                progress_callback(5)

            for idx, (start, end) in enumerate(ranges):
                if cancel_check and cancel_check():
                    from core.worker import CancelledException
                    raise CancelledException("İşlem iptal edildi.")

                writer = PdfWriter()
                for page_num in range(start - 1, end):
                    writer.add_page(reader.pages[page_num])

                out_path = output_paths[idx]
                _write_pdf_atomic(writer, out_path, cancel_check)
                created_files.append(out_path)

                if status_callback:
                    status_callback(f"Kaydediliyor: {out_path.name}")
                if progress_callback:
                    progress_callback(5 + int((idx + 1) / len(ranges) * 90))

        if progress_callback:
            progress_callback(100)
        if status_callback:
            status_callback(f"Tamamlandı! {len(ranges)} bölüm kaydedildi.")
    except Exception:
        cleanup_created_files(created_files)
        if not folder_existed:
            try:
                output_folder.rmdir()
            except OSError:
                pass
        raise

    return str(output_folder)
