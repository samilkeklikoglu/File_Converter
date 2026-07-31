"""
core/word_to_pdf.py — Word → PDF Dönüşüm Motoru

ÖĞRENME NOTU — docx2pdf:

  docx2pdf, Microsoft Word'ü (COM arayüzü üzerinden) kullanarak
  .docx / .doc dosyalarını PDF'e dönüştürür.

  KISIT: Windows'ta Microsoft Word kurulu olması ZORUNLUDUR.
  macOS'ta LibreOffice veya Word for Mac desteklenir.
  Linux'ta doğrudan çalışmaz (LibreOffice sarmalayıcı gerekir).

  Temel kullanım:
    docx2pdf.convert(input_path, output_path)
      input_path  → .docx dosyasının tam yolu (str veya Path)
      output_path → oluşturulacak PDF'in tam yolu (str veya Path)

  Hata durumları:
    - Word kurulu değilse → genellikle COM hatası veya OSError
    - Dosya bozuksa       → çeşitli Exception türleri
    - Dosya kilitliyse    → PermissionError

Bu fonksiyon UI'dan tamamen bağımsız!
UI bilmez, Qt bilmez. Sadece dosya yolları alır, PDF üretir.
"""

import sys
from pathlib import Path
from typing import Callable


def convert_word_to_pdf(
    input_path: str,
    output_dir: str,
    progress_callback: Callable[[int], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
) -> str:
    """
    Verilen Word dosyasını PDF'e dönüştürür.

    Parametreler:
        input_path       : Dönüştürülecek .docx / .doc dosyasının tam yolu
        output_dir       : PDF'in kaydedileceği klasörün tam yolu
        progress_callback: İlerleme güncellemesi için çağrılır (0-100)
        status_callback  : Durum metni için çağrılır

    Döndürür:
        str: Oluşturulan PDF'in tam yolu (başarısız olursa exception fırlatır)
    """
    # ── Ön Kontroller ────────────────────────────────────────────────────────
    source = Path(input_path)

    if not source.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {source.name}")

    if source.suffix.lower() not in (".docx", ".doc"):
        raise ValueError(
            f"Desteklenmeyen dosya formatı: '{source.suffix}'. "
            "Yalnızca .docx ve .doc dosyaları dönüştürülebilir."
        )

    # ── Çıktı Yolunu Hazırla ─────────────────────────────────────────────────
    output_folder = Path(output_dir)
    output_folder.mkdir(parents=True, exist_ok=True)
    output_path = output_folder / (source.stem + ".pdf")

    # ── İlerleme: Başlangıç ──────────────────────────────────────────────────
    if status_callback:
        status_callback(f"Hazırlanıyor: {source.name}")
    if progress_callback:
        progress_callback(10)

    # ── Platform Uyarısı ─────────────────────────────────────────────────────
    if sys.platform not in ("win32", "darwin"):
        raise EnvironmentError(
            "docx2pdf yalnızca Windows ve macOS'ta çalışır. "
            "Linux'ta Microsoft Word veya LibreOffice kurulu olmalıdır."
        )

    # ── Dönüşüm ──────────────────────────────────────────────────────────────
    try:
        # docx2pdf burada içe aktarılıyor: import hatası daha anlaşılır mesaj verir
        import docx2pdf  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "docx2pdf kütüphanesi bulunamadı. "
            "Lütfen 'pip install docx2pdf' komutuyla yükleyin."
        )

    if status_callback:
        status_callback(f"Dönüştürülüyor: {source.name}")
    if progress_callback:
        progress_callback(30)

    try:
        # docx2pdf.convert() Word COM arayüzünü çağırır (Windows) ya da
        # Word for Mac / LibreOffice'i başlatır (macOS)
        docx2pdf.convert(str(source), str(output_path))

    except Exception as exc:
        error_msg = str(exc)

        # Yaygın hata türlerine göre kullanıcı dostu mesaj üret
        if "Word" in error_msg or "com_error" in error_msg.lower() or "comtypes" in error_msg.lower():
            raise RuntimeError(
                "Microsoft Word bulunamadı veya başlatılamadı.\n"
                "Word → PDF dönüşümü için sisteminizde Microsoft Word kurulu olmalıdır.\n\n"
                f"Teknik detay: {error_msg}"
            ) from exc

        if "PermissionError" in error_msg or "Access is denied" in error_msg:
            raise PermissionError(
                f"'{source.name}' dosyasına erişilemiyor.\n"
                "Dosya başka bir program tarafından açık olabilir (Word gibi). "
                "Lütfen kapatıp tekrar deneyin.\n\n"
                f"Teknik detay: {error_msg}"
            ) from exc

        # Bilinmeyen hata — orijinal mesajı ilet
        raise RuntimeError(
            f"Dönüşüm sırasında beklenmedik bir hata oluştu:\n{error_msg}"
        ) from exc

    # ── Çıktı Doğrulama ──────────────────────────────────────────────────────
    if not output_path.exists():
        raise RuntimeError(
            "Dönüşüm tamamlandı ancak PDF dosyası oluşturulamadı. "
            "Lütfen Microsoft Word'ün düzgün kurulu olduğunu kontrol edin."
        )

    # ── İlerleme: Tamamlandı ─────────────────────────────────────────────────
    if progress_callback:
        progress_callback(100)
    if status_callback:
        status_callback(f"Tamamlandı! → {output_path.name}")

    return str(output_path)
