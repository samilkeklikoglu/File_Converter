"""
core/pdf_merge.py — PDF Birleştirme Motoru

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
        raise ValueError("En az bir PDF dosyası seçmelisiniz.")

    if len(input_paths) < 2:
        raise ValueError("PDF birleştirmek için en az 2 dosya seçmelisiniz.")

    for path_str in input_paths:
        p = Path(path_str)
        if not p.exists():
            raise FileNotFoundError(f"Dosya bulunamadı: {p.name}")
        if p.suffix.lower() != ".pdf":
            raise ValueError(
                f"'{p.name}' bir PDF dosyası değil. "
                "Yalnızca .pdf uzantılı dosyalar kabul edilir."
            )

    try:
        from pypdf import PdfWriter, PdfReader  # noqa: PLC0415
        from pypdf.errors import PdfReadError  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "pypdf kütüphanesi bulunamadı. "
            "Lütfen 'pip install pypdf' komutuyla yükleyin."
        )

    output = Path(output_path)
    if output.suffix.lower() != ".pdf":
        raise ValueError("Birleştirme çıktısı .pdf uzantılı olmalıdır.")

    resolved_output = output.resolve()
    for path_str in input_paths:
        if Path(path_str).resolve() == resolved_output:
            raise ValueError(
                "Çıktı dosyası kaynak PDF'lerden biriyle aynı olamaz. "
                "Kaynak dosyaların korunması için farklı bir ad veya konum seçin."
            )

    output.parent.mkdir(parents=True, exist_ok=True)

    writer = PdfWriter()
    total = len(input_paths)

    if status_callback:
        status_callback(f"Başlatılıyor... ({total} dosya)")
    if progress_callback:
        progress_callback(5)

    with ExitStack() as source_files:
        for i, path_str in enumerate(input_paths):
            if cancel_check and cancel_check():
                from core.worker import CancelledException
                raise CancelledException("İşlem iptal edildi.")

            p = Path(path_str)
            if status_callback:
                status_callback(f"İşleniyor: {p.name}  ({i + 1}/{total})")

            try:
                source_handle = source_files.enter_context(p.open("rb"))
                reader = PdfReader(source_handle)

                if reader.is_encrypted:
                    raise PermissionError(
                        f"'{p.name}' şifreli bir PDF dosyasıdır. "
                        "Şifreli PDF'ler birleştirilemez. "
                        "Lütfen önce şifreyi kaldırın."
                    )

                for page in reader.pages:
                    writer.add_page(page)
            except PdfReadError as exc:
                raise RuntimeError(
                    f"'{p.name}' dosyası okunamadı. "
                    f"Dosya bozuk veya geçerli bir PDF değil.\n\nTeknik detay: {exc}"
                ) from exc
            except PermissionError:
                raise
            except Exception as exc:
                raise RuntimeError(
                    f"'{p.name}' işlenirken beklenmedik hata oluştu:\n{exc}"
                ) from exc

            if progress_callback:
                progress_callback(5 + int((i + 1) / total * 85))

        if status_callback:
            status_callback("PDF kaydediliyor...")
        if progress_callback:
            progress_callback(92)

        if cancel_check and cancel_check():
            from core.worker import CancelledException
            raise CancelledException("İşlem iptal edildi.")

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
                    "Birleştirme tamamlandı ancak geçici çıktı dosyası boş oluşturuldu."
                )
            temporary_path.replace(output)
        except PermissionError as exc:
            raise PermissionError(
                f"'{output.name}' dosyasına yazılamıyor. "
                "Dosya başka bir program tarafından açık olabilir."
            ) from exc
        except Exception as exc:
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(
                f"'{output.name}' kaydedilirken beklenmedik hata oluştu:\n{exc}"
            ) from exc
        finally:
            if temporary_path and temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    pass

    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError(
            "Birleştirme tamamlandı ancak çıktı dosyası oluşturulamadı."
        )

    if progress_callback:
        progress_callback(100)
    if status_callback:
        status_callback(f"Tamamlandı! → {output.name}")

    return str(output)
