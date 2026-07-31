"""
core/worker.py — QThread Tabanlı Arka Plan İşçisi

ÖĞRENME NOTU — Neden QThread?

  UI thread'i (ana thread): Tüm widget çizimi ve kullanıcı etkileşimi burada.
  Eğer bu thread uzun süre meşgul olursa → pencere donar, yanıt vermez.
  
  Çözüm: Ağır işi ayrı bir thread'de yap.
  Qt'de bunun doğru yolu: QThread subclass'ı.
  
  Thread Güvenliği — ÇOK ÖNEMLİ:
    Farklı thread'lerden aynı widget'a erişmek tehlikeli!
    Doğru yol: QThread'den sinyal(Signal) yay, ana thread'de slot ile yakala.
    Sinyal-slot mekanizması thread'ler arası güvenli iletişimi otomatik sağlar.
  
  Yanlış (tehlikeli):
    # worker thread içinde:
    self.progress_bar.setValue(50)  ← Widget'a direkt erişim! YANLIŞ
  
  Doğru:
    # worker thread:
    self.progress.emit(50)           ← Sinyal yay
    # ana thread'deki slot:
    def on_progress(val): self.progress_bar.setValue(val)  ← Widget burada güvenli
"""

from PySide6.QtCore import QThread, Signal


class ConversionWorker(QThread):
    """
    Arka planda herhangi bir dosya dönüşümü yapan generic işçi thread'i.

    Hangi dönüşüm fonksiyonu çalıştırılacağı `func` parametresiyle belirlenir;
    bu sayede worker image_to_pdf, word_to_pdf veya gelecekteki herhangi bir
    dönüştürücüyle kullanılabilir.

    Kullanım (Resim → PDF):
        worker = ConversionWorker(
            func=core.image_to_pdf.convert_images_to_pdf,
            kwargs={'image_paths': [...], 'output_path': '...', 'page_size': 'A4'}
        )

    Kullanım (Word → PDF):
        worker = ConversionWorker(
            func=core.word_to_pdf.convert_word_to_pdf,
            kwargs={'input_path': '...', 'output_dir': '...'}
        )

    Tüm dönüştürücü fonksiyonlar şu sözleşmeye uymalıdır:
        - `progress_callback: Callable[[int], None]` parametresini kabul etmeli
        - `status_callback: Callable[[str], None]` parametresini kabul etmeli
        - Başarı durumunda çıktı dosyasının tam yolunu (str) döndürmeli
        - Hata durumunda exception fırlatmalı (return değil)

    Sinyaller:
        progress (int) : 0-100 arası ilerleme yüzdesi
        status   (str) : Anlık durum metni
        finished (str) : Başarı — çıktı dosyasının tam yolu
        error    (str) : Hata — kullanıcıya gösterilecek mesaj

    Parametreler:
        func    : Çalıştırılacak dönüşüm fonksiyonu
        kwargs  : O fonksiyona geçirilecek anahtar-kelime argümanlar
    """
    
    # ── Sinyaller ────────────────────────────────────────────────────────────
    # Bu sinyaller farklı türde veri taşır:
    
    progress = Signal(int)   # 0-100 arası ilerleme yüzdesi
    status   = Signal(str)   # "İşleniyor: foto.jpg (2/5)" gibi durum metni
    finished = Signal(str)   # Başarı: çıktı dosyasının tam yolu
    error    = Signal(str)   # Hata: kullanıcıya gösterilecek mesaj
    
    def __init__(self, func, kwargs: dict, parent=None):
        super().__init__(parent)
        self._func = func      # Çalıştırılacak fonksiyon
        self._kwargs = kwargs  # Fonksiyon argümanları
    
    def run(self):
        """
        QThread.start() çağrılınca ayrı thread'de bu metot çalışır.
        
        Progress callback'i kwargs içine ekliyoruz:
        Dönüşüm fonksiyonu bu callback'leri çağırdıkça sinyaller yayılır.
        """
        try:
            # Callback fonksiyonları sinyale bağla
            # Dönüşüm fonksiyonu bu callback'leri çağırarak bize bilgi verir
            self._kwargs['progress_callback'] = lambda v: self.progress.emit(v)
            self._kwargs['status_callback']   = lambda s: self.status.emit(s)
            
            # Asıl dönüşüm fonksiyonunu çalıştır
            output_path = self._func(**self._kwargs)
            
            # Başarı sinyali yay (ana thread yakalar)
            self.finished.emit(output_path)
            
        except Exception as exc:
            # Hatayı yakala, kullanıcıya anlaşılır mesaj gönder
            # Uygulama ÇÖKMEZ — sadece hata sinyali yayılır
            self.error.emit(str(exc))
