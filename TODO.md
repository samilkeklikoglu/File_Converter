# FileConverter — Proje Durumu

## ✅ Tamamlanan Özellikler

### Core Dönüşüm Motorları
- [x] Resim → PDF dönüştürme (`core/image_to_pdf.py`) — A4, Letter, Orijinal
- [x] Resim format dönüştürme (`core/image_convert.py`) — JPG, PNG, WEBP + kalite ayarı
- [x] Word → PDF dönüştürme (`core/word_to_pdf.py`) — docx2pdf ile
- [x] PDF birleştirme (`core/pdf_merge.py`) — pypdf ile
- [x] PDF bölme (`core/pdf_split.py`) — sayfa bazlı + aralık bazlı
- [x] PDF → Görsel (`core/pdf_to_image.py`) — pymupdf ile, PNG/JPG
- [x] PDF → Word (`core/pdf_to_word.py`) — pdf2docx ile

### UI
- [x] Ana pencere ve dark tema (`main.py`, `ui/main_window.py`)
- [x] Sürükle-bırak alanı (`ui/drop_zone.py`)
- [x] Otomatik dosya tipi algılama (`core/file_detector.py`)
- [x] Akıllı panel — tip bazlı aksiyon gösterimi (`ui/panels/smart_panel.py`)
- [x] İlerleme çubuğu ve durum gösterimi (`ui/progress_widget.py`)
- [x] Dosya listesi — sürükle-bırak sıralama + silme
- [x] Arka plan thread'inde dönüşüm (`core/worker.py`)

### Build & Dağıtım
- [x] PyInstaller build scripti (`build.py`)
- [x] Inno Setup installer scripti (`installer.iss`)

---

## 📋 Yapılacaklar

### Yüksek Öncelik
- [x] `requirements.txt`'e eksik bağımlılıkları ekle (`pymupdf`, `pdf2docx`)
- [x] Uygulama ikonu oluştur (`.ico`) — pencere, build ve installer'a dahil et
- [x] Worker iptal (cancel) mekanizması ekle
- [x] Sabit çıktı dosya adlarını ve PDF merge üzerine yazma riskini düzelt

### Orta Öncelik
- [x] Tüm işlemlere çıktı konumu seçme özelliği ekle
- [x] PDF → Görsel'de DPI ayarını UI'a ekle
- [x] Birden fazla Word dosyasını toplu dönüştürme desteği
- [x] README.md oluştur (kurulum, kullanım, build ve sınırlamalar)
- [x] Birim/regresyon testleri ekle (`tests/`, 35 senaryo)

### Düşük Öncelik
- [x] Klasör sürükle-bırak desteği (içindeki dosyaları otomatik bul)
- [x] Büyük klasörleri arka plan thread'inde tara
- [x] Aktif işlem sırasında güvenli pencere kapatma akışı
- [ ] Logging altyapısı ekle
- [ ] Ayarlar / tercihler paneli (varsayılan çıktı konumu, DPI, kalite)
- [ ] Son kullanılan dosyalar / geçmiş
- [ ] Çoklu dil (i18n) altyapısı

---

## 🔧 Sıradaki Teknik İşler

- [x] Başarı sinyalini `succeeded` yap ve temizliği yerleşik `QThread.finished` sinyaline bağla
- [x] Dönüşüm motorlarında atomik yazma ve iptalde kısmi çıktı temizliği ekle
- [x] PDF → Word converter kaynağını hata durumunda `finally` ile kapat
- [x] Tekrarlanan PDF sayfa aralıklarında çıktı adı çakışmasını engelle
- [x] Resimlerde EXIF yönünü uygula
- [ ] Çok kareli TIFF/WEBP davranışını ele al
- [ ] `SmartPanel` sınıfını daha küçük controller/widget bileşenlerine böl
- [ ] CI üzerinde test ve build doğrulaması ekle

## 🚀 2.0.0 Launch Doğrulaması

- [x] Gerçek Microsoft Word ile DOCX → PDF smoke testi
- [x] Güncel kaynaklardan standalone EXE build ve başlangıç testi
- [x] Inno Setup installer derleme, kurulum, çalıştırma ve kaldırma testi
- [x] Çalışma zamanı bağımlılıklarını doğrulanan sürümlere sabitle

> Son güncelleme: 2026-09-03
