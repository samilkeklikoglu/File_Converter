"""
core/image_to_pdf.py — Resim → PDF Dönüşüm Motoru

ÖĞRENME NOTU — Pillow (PIL):
  
  Pillow, Python'ın en yaygın görsel işleme kütüphanesidir.
  
  Temel kavramlar:
    Image.open(path)          → Dosyadan Image nesnesi oluştur
    image.convert("RGB")      → Renk modunu değiştir
                                  RGBA → PNG gibi alfa kanallı resimler PDF'e
                                  kaydedilemez; RGB'ye çevirmek gerekir
    image.save(path, "PDF")   → PDF olarak kaydet
    
  Birden fazla resmi tek PDF'e birleştirme:
    İlk resim: image.save(path, save_all=True, append_images=[...])
    save_all=True    : Tüm kareleri kaydet
    append_images    : İlk resimden sonra eklenecek resimler

  Sayfa boyutu:
    PDF boyutu resmin piksel boyutuna (DPI'ya) bağlıdır.
    Belirli bir kağıt boyutu istiyorsak resmi o boyuta ölçeklendiririz.

Bu fonksiyon UI'dan tamamen bağımsız!
UI bilmez, Qt bilmez. Sadece dosya yolları alır, PDF üretir.
"""

from pathlib import Path
from typing import Callable
from PIL import Image


# Standart kağıt boyutları (piksel, 96 DPI varsayımıyla)
# Gerçek baskı için 300 DPI kullanılır, ama ekran görüntüsü için 96 DPI yeterli
PAPER_SIZES_96DPI = {
    "A4":      (794, 1123),   # 210mm × 297mm @ 96 DPI
    "Letter":  (816, 1056),   # 8.5in × 11in @ 96 DPI
    "Orijinal": None,         # Resmin kendi boyutu korunur
}


def convert_images_to_pdf(
    image_paths: list[str],
    output_path: str,
    page_size: str = "A4",
    progress_callback: Callable[[int], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
) -> str:
    """
    Verilen resim dosyalarını tek bir PDF'e dönüştürür.
    
    Parametreler:
        image_paths      : Dönüştürülecek resim dosyalarının tam yolları
        output_path      : Oluşturulacak PDF'in tam yolu
        page_size        : "A4", "Letter" veya "Orijinal"
        progress_callback: İlerleme güncellemesi için çağrılır (0-100)
        status_callback  : Durum metni için çağrılır
    
    Döndürür:
        str: Oluşturulan PDF'in tam yolu (başarısız olursa exception fırlatır)
    """
    
    if not image_paths:
        raise ValueError("Dönüştürülecek resim dosyası seçilmedi.")
    
    total = len(image_paths)
    target_size = PAPER_SIZES_96DPI.get(page_size)  # None ise orijinal boyut
    
    # ── Adım 1: Resimleri Yükle ve Hazırla ──────────────────────────────────
    processed_images: list[Image.Image] = []
    
    for i, path_str in enumerate(image_paths):
        path = Path(path_str)
        
        # Durum güncellemesi
        if status_callback:
            status_callback(f"Yükleniyor: {path.name}  ({i + 1}/{total})")
        
        # Resmi aç
        img = Image.open(path)
        
        # RGBA veya P (palette) modundaki resimleri RGB'ye dönüştür
        # PDF formatı alfa kanalını (şeffaflık) desteklemez
        if img.mode in ("RGBA", "P", "LA"):
            # Beyaz arka plan üzerine yapıştır (şeffaf piksel → beyaz)
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        
        # ── Adım 2: Boyutlandırma (isteğe bağlı) ────────────────────────────
        if target_size is not None:
            # Oranı koruyarak hedef boyuta sığdır (crop yok, sıkıştırma var)
            img = _fit_to_page(img, target_size)
        
        processed_images.append(img)
        
        # İlerleme: yükleme aşaması %0-50 arası
        if progress_callback:
            progress_callback(int((i + 1) / total * 50))
    
    # ── Adım 3: PDF Olarak Kaydet ────────────────────────────────────────────
    if status_callback:
        status_callback("PDF oluşturuluyor...")
    
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)  # klasör yoksa oluştur
    
    # İlk resim ana sayfadır; diğerleri append_images ile eklenir
    first_img = processed_images[0]
    rest_imgs  = processed_images[1:]  # boş liste olabilir (tek resim)
    
    first_img.save(
        output,
        format="PDF",
        save_all=True,       # çok sayfalı PDF için zorunlu
        append_images=rest_imgs,
        resolution=96.0,     # DPI
    )
    
    # İlerleme: kaydetme aşaması %50-100
    for i, _ in enumerate(processed_images):
        if progress_callback:
            progress_callback(50 + int((i + 1) / total * 50))
    
    if status_callback:
        status_callback(f"Tamamlandı! → {output.name}")
    
    # Belleği temizle
    for img in processed_images:
        img.close()
    
    return str(output)


def _fit_to_page(img: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    """
    Resmi hedef sayfa boyutuna, oranı koruyarak sığdırır.
    
    Resim sayfadan küçükse büyütülmez (kalite kaybı önlenir).
    Resim sayfadan büyükse küçültülür.
    Kalan alan beyaz bırakılır (letterbox efekti).
    
    Parametreler:
        img        : Pillow Image nesnesi
        target_size: (genişlik, yükseklik) piksel
    
    Döndürür:
        Yeni boyutlandırılmış Image nesnesi
    """
    page_w, page_h = target_size
    img_w, img_h = img.size
    
    # Oran koruyarak ölçek hesapla
    scale = min(page_w / img_w, page_h / img_h, 1.0)  # 1.0: büyütme yok
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    
    # Yeniden boyutlandır (LANCZOS: yüksek kaliteli küçültme filtresi)
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Beyaz arka plan sayfaya yerleştir (ortalanmış)
    canvas = Image.new("RGB", (page_w, page_h), (255, 255, 255))
    x_offset = (page_w - new_w) // 2
    y_offset = (page_h - new_h) // 2
    canvas.paste(resized, (x_offset, y_offset))
    
    return canvas
