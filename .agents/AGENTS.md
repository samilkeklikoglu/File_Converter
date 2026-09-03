# FileConverter — AI Context Document

> **Son Güncelleme:** 2026-09-03
> **Versiyon:** v2.0.0
> **Dil:** Python 3.12+
> **Framework:** PySide6 (Qt6)
> **Platform:** Windows (birincil), macOS (kısmi destek)

---

## 1. Proje Özeti

FileConverter, dosya dönüştürme işlemlerini tek bir arayüzde toplayan masaüstü uygulamasıdır.
Kullanıcı dosyaları sürükle-bırak veya dosya seçici ile ekler; uygulama dosya tipini otomatik algılar
ve uygun dönüşüm aksiyonlarını dinamik olarak sunar.

**Desteklenen dönüşümler:**

| Kaynak Tip   | Hedef Tip       | Motor Dosyası             | Bağımlılık    |
|-------------|-----------------|---------------------------|---------------|
| Resim       | PDF             | `core/image_to_pdf.py`    | Pillow        |
| Resim       | JPG/PNG/WEBP    | `core/image_convert.py`   | Pillow        |
| Word (.docx)| PDF             | `core/word_to_pdf.py`     | docx2pdf + MS Word |
| PDF (çoklu) | Tek PDF         | `core/pdf_merge.py`       | pypdf         |
| PDF (tekli) | Ayrı sayfalar   | `core/pdf_split.py`       | pypdf         |
| PDF         | Resim (PNG/JPG) | `core/pdf_to_image.py`    | PyMuPDF (fitz)|
| PDF         | Word (.docx)    | `core/pdf_to_word.py`     | pdf2docx      |

---

## 2. Dizin Yapısı

```
FileConverter/
├── main.py                      # Uygulama giriş noktası + global QSS dark tema
├── build.py                     # PyInstaller build scripti
├── installer.iss                # Inno Setup Windows installer config
├── requirements.txt             # Python bağımlılıkları
├── requirements-build.txt       # Sabitlenmiş PyInstaller bağımlılıkları
├── README.md                    # Kurulum, kullanım, test ve build rehberi
├── LICENSE                      # GNU AGPLv3 proje lisansı
├── THIRD_PARTY_NOTICES.md       # Dağıtılan bağımlılıkların lisans özeti
├── PRIVACY.md                   # Yerel veri işleme gizlilik bildirimi
├── CHANGELOG.md                 # Sürüm değişiklik geçmişi
├── package_release.py           # Portable ZIP ve SHA-256 yayın çıktıları
├── TODO.md                      # Proje roadmap ve görev takibi
├── .gitignore
│
├── assets/
│   ├── fileconverter.png        # Yüksek çözünürlüklü ikon kaynağı
│   └── fileconverter.ico        # Pencere, EXE ve installer ikonu
│
├── core/                        # İş mantığı katmanı (UI bağımsız)
│   ├── __init__.py
│   ├── file_detector.py         # Dosya tipi algılama
│   ├── worker.py                # QThread tabanlı arka plan işçisi
│   ├── image_to_pdf.py          # Resim → PDF dönüşüm motoru
│   ├── image_convert.py         # Resim format dönüşüm motoru (JPG/PNG/WEBP)
│   ├── word_to_pdf.py           # Word → PDF dönüşüm motoru
│   ├── pdf_merge.py             # PDF birleştirme motoru
│   ├── pdf_split.py             # PDF bölme motoru (sayfa + aralık)
│   ├── pdf_to_image.py          # PDF → Resim dönüşüm motoru
│   └── pdf_to_word.py           # PDF → Word dönüşüm motoru
│
├── tests/                       # unittest birim ve regresyon testleri
│
└── ui/                          # Kullanıcı arayüzü katmanı
    ├── __init__.py
    ├── main_window.py           # QMainWindow — tek merkezi widget (SmartPanel) barındırır
    ├── drop_zone.py             # Sürükle-bırak dosya giriş widget'ı
    ├── progress_widget.py       # İlerleme çubuğu + sonuç gösterimi widget'ı
    └── panels/
        ├── __init__.py
        └── smart_panel.py       # Ana akış yöneticisi — scene state machine (~1200 satır)
```

---

## 3. Mimari Genel Bakış

### 3.1 Katmanlı Yapı

```
┌─────────────────────────────────────────────────────┐
│                    main.py                          │
│            (QApplication + QSS Tema)                │
├─────────────────────────────────────────────────────┤
│                 UI Katmanı (ui/)                    │
│  ┌─────────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ MainWindow  │→ │SmartPanel│→ │ProgressWidget │  │
│  │             │  │ (FSM)    │  │               │  │
│  └─────────────┘  └────┬─────┘  └───────────────┘  │
│                        │                            │
│              ┌─────────┤                            │
│              │  DropZone│                            │
│              └──────────┘                           │
├─────────────────────────────────────────────────────┤
│               Core Katmanı (core/)                  │
│  ┌──────────────┐  ┌─────────────────────────────┐  │
│  │file_detector │  │   ConversionWorker (QThread) │  │
│  └──────────────┘  └──────────┬──────────────────┘  │
│                               │                     │
│  ┌──────────┐ ┌──────────┐ ┌──┴───────┐ ┌────────┐ │
│  │image2pdf │ │img_convert│ │pdf_merge │ │pdf2img │ │
│  │word2pdf  │ │pdf_split  │ │pdf2word  │ │        │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
└─────────────────────────────────────────────────────┘
```

### 3.2 Veri Akışı

```
Kullanıcı dosya bırakır/seçer
        │
        ▼
  DropZone.files_dropped (Signal[list[str]])
        │
        ▼
  SmartPanel._on_files_dropped(paths)
        │
        ▼
  file_detector.detect_type(paths) → "image"|"word"|"pdf"|"mixed"|"unsupported"
        │
        ▼
  SmartPanel._set_files(paths)
        ├── _populate_file_list()   → QListWidget güncelle
        ├── _update_detect_band()   → Algılama kartını güncelle
        ├── _update_action_stack()  → İlgili aksiyon panelini göster
        └── stack.setCurrentIndex(SCENE_ACTIONS)

Kullanıcı aksiyon butonuna tıklar
        │
        ▼
  _start_xxx() → ConversionWorker(func, kwargs) oluştur
        │
        ▼
  _launch_worker(worker, op_label, paths)
        ├── worker.progress → progress_widget.set_progress
        ├── worker.status   → progress_widget.set_status
        ├── worker.succeeded → _on_finished → progress_widget.set_finished
        └── worker.error    → _on_error   → progress_widget.set_error + QMessageBox
```

---

## 4. Bileşen Detayları

### 4.1 `main.py` — Uygulama Giriş Noktası

- **Satır sayısı:** 346 (büyük çoğunluğu QSS stildir)
- **İşlevi:** `QApplication` oluşturur, `DARK_THEME` QSS string'ini uygular, `MainWindow`'u başlatır
- **Tema renk paleti:**
  - Ana arka plan: `#08080f` (koyu lacivert-siyah)
  - Accent: `#6c63ff` (mor-mavi gradient)
  - İkincil accent: `#4a90e2` (mavi)
  - Başarı: `#22d3a0` (yeşil)
  - Hata: `#ef4444` / `#f87171` (kırmızı)
  - Metin: `#e8e8f5` (açık)
  - Dim metin: `#9090c0`, `#454580`
- **Önemli objectName'ler (QSS'te kullanılan):**
  - `primaryBtn` — gradient accent buton
  - `successBtn` — yeşil gradient buton
  - `fileList` — dosya listesi
  - `titleLabel`, `subtitleLabel`, `sectionLabel` — yazı tipleri

### 4.2 `core/file_detector.py` — Dosya Tipi Algılama

```python
# Sabitleri
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}
WORD_EXTENSIONS  = {'.docx', '.doc'}
PDF_EXTENSIONS   = {'.pdf'}

# Public API
detect_type(paths: list[str]) → "image" | "word" | "pdf" | "mixed" | "unsupported"
get_type_label(file_type: str, count: int) → str  # Türkçe etiket
```

- Tüm dosyalar aynı tipteyse → o tipin adı
- Birden fazla desteklenen tip varsa → `"mixed"`
- Herhangi biri tanınmıyorsa → hemen `"unsupported"` döner (kısa devre)

### 4.3 `core/worker.py` — ConversionWorker (QThread)

```python
class ConversionWorker(QThread):
    # Sinyaller
    progress  = Signal(int)    # 0–100
    status    = Signal(str)    # Durum metni
    succeeded = Signal(str)    # Başarılı → çıktı dosya yolu
    error     = Signal(str)    # Hata mesajı
    cancelled = Signal()       # Kullanıcı iptal etti
```

**Dönüşüm fonksiyonu kontratı:** Tüm core dönüşüm fonksiyonları şu imzayı takip etmelidir:
```python
def convert_xxx(
    ...,  # fonksiyona özgü parametreler
    progress_callback: Callable[[int], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> str:  # Başarılı ise çıktı yolu döner, hata ise exception fırlatır
```

**İptal mekanizması:** `cancel_check()` True döndüğünde `CancelledException` fırlatılır.
Worker bu exception'ı yakalar ve `cancelled` sinyalini emit eder.

### 4.4 `core/image_to_pdf.py` — Resim → PDF

- Pillow kullanır
- Sayfa boyutları: `A4` (794×1123px @96dpi), `Letter` (816×1056px), `Orijinal`
- RGBA/P modlu resimleri RGB'ye çevirir (beyaz arka plan)
- `_fit_to_page()`: Aspect ratio koruyarak letterbox (beyaz canvas)
- Upscale yapmaz (`scale = min(..., 1.0)`)
- Çıktı: Tek multi-page PDF

### 4.5 `core/image_convert.py` — Resim Format Dönüştürme

- Desteklenen çıktılar: JPG, PNG, WEBP
- Kalite: 1–95 (JPG/WEBP için geçerli, PNG için optimize=True)
- Kaynak=hedef çakışmasında `_converted` eki ekler
- RGBA → RGB dönüşümü (JPEG için zorunlu, beyaz arka plan)

### 4.6 `core/word_to_pdf.py` — Word → PDF

- `docx2pdf` kütüphanesi üzerinden **Microsoft Word** kullanır (COM automation)
- **Platform kısıtı:** Yalnızca `win32` ve `darwin`
- Hata sınıflandırması: Word bulunamadı / PermissionError / genel hata

### 4.7 `core/pdf_merge.py` — PDF Birleştirme

- `pypdf` kütüphanesi (PdfWriter/PdfReader)
- Minimum 2 PDF gerektirir
- Şifreli PDF kontrolü var
- Bozuk PDF kontrolü var (PdfReadError yakalanır)
- İlerleme: %5 başlangıç → %90 dosya okuma → %92 kayıt → %100

### 4.8 `core/pdf_split.py` — PDF Bölme

İki mod:
1. **`split_pdf_by_pages()`** — Her sayfayı ayrı PDF olarak çıkarır
   - Çıktı adları: `{stem}_page_01.pdf`, `_page_02.pdf`, ...
2. **`split_pdf_by_ranges()`** — Kullanıcı aralığına göre böler
   - Girdi: `"1-3, 5, 7-9"` formatında string
   - Çıktı adları: `{stem}_pp_1-3.pdf`, `_pp_5-5.pdf`, ...

**`parse_page_ranges(range_str, total_pages)` helper:**
- 1-indexed, inclusive aralıklar
- Bounds checking ve validation içerir
- Türkçe hata mesajları

### 4.9 `core/pdf_to_image.py` — PDF → Resim

- **PyMuPDF (fitz)** kütüphanesi
- `import pymupdf as fitz` şeklinde import edilir
- DPI ayarlanabilir (varsayılan: 150), zoom = dpi/72
- Çıktı formatları: PNG, JPG
- Çıktı adları: `{stem}_page_01.png`

### 4.10 `core/pdf_to_word.py` — PDF → Word

- **pdf2docx** kütüphanesi (Converter sınıfı)
- Layout analizi ve tablo reconstructionu yapar
- İlerleme: %10 analiz → %30 ayrıştırma → %100

### 4.11 `ui/main_window.py` — Ana Pencere

```python
class MainWindow(QMainWindow):
    # Layout: QMainWindow → central_widget → SmartPanel
    # Pencere boyutu: min(780, 560), default(960, 660)
    # Başlık: "FileConverter — Dosya Dönüştürme Aracı"
    # İkon: qtawesome fa5.clone (#6c63ff)
    # Ekran merkezleme yapılır
```

### 4.12 `ui/drop_zone.py` — Sürükle-Bırak Alanı

```python
class DropZone(QWidget):
    files_dropped = Signal(list)  # list[str]

    # Görsel durumlar:
    _STATES = {
        "normal": {"bg": "#0b0b1a", "border": "#1e1e45"},
        "hover":  {"bg": "#0f0f28", "border": "#6c63ff"},
        "reject": {"bg": "#160808", "border": "#ef4444"},
    }
```

- Sürükle-bırak + tıkla-seç desteği
- Format pill'leri: JPG, PNG, PDF, DOCX, WEBP
- Upload ikonu: `fa5s.cloud-upload-alt`
- objectName: `dropZone`
- Dosya tipi filtrelemesi **yapmaz** — bunu SmartPanel/file_detector halleder

### 4.13 `ui/progress_widget.py` — İlerleme Widget'ı

```python
class ProgressWidget(QWidget):
    clear_requested = Signal()

    # Durumlar: idle → running → done | error
    # Alt bileşenler:
    #   - status_icon (QLabel, 20×20)
    #   - status_label (QLabel)
    #   - progress_bar (QProgressBar, 0-100, h:22)
    #   - open_btn ("Klasörü Aç", objectName=successBtn)
    #   - clear_btn ("Yeni İşlem")
```

- `_open_output_folder()`: Platform-aware (explorer/open/xdg-open)
  - Dosya ise: `explorer /select, <path>` (Windows)
  - Dizin ise: `explorer <path>`
- Kart stili: `progressCard` objectName, koyu arka plan + border-radius

### 4.14 `ui/panels/smart_panel.py` — Ana Akış Yöneticisi (~1200 satır)

Bu dosya uygulamanın kalbidir. Üç scene'li state machine yönetir.

**Scene State Machine:**
```
SCENE_EMPTY (0)     →  Büyük drop zone, dosya bekleniyor
     │ files_dropped
     ▼
SCENE_ACTIONS (1)   →  Dosyalar listelendi, aksiyon seçimi
     │ aksiyon tıklandı
     ▼
SCENE_PROGRESS (2)  →  Dönüşüm çalışıyor/tamamlandı/hata
     │ "Yeni İşlem" tıklandı
     ▼
SCENE_EMPTY (0)     →  Başa dön
```

**Action Stack (SCENE_ACTIONS içindeki iç QStackedWidget):**

| İndeks | Durum         | Gösterilen Widget       |
|--------|---------------|-------------------------|
| 0      | `image`       | PDF'e Dönüştür + Format Dönüştür |
| 1      | `word`        | PDF'e Dönüştür (Word)   |
| 2      | `pdf` (1 adet)| Böl + Görsele Çevir + Word'e Çevir |
| 3      | `pdf` (2+ adet)| Birleştir              |
| 4      | `mixed`       | Uyarı mesajı            |
| 5      | `unsupported` | Hata mesajı             |

**Önemli iç sınıflar:**

```python
class FileListWidget(QListWidget):
    """Hem OS sürükleme (harici dosya) hem dahili drag-drop sıralama destekler"""
    files_dropped = Signal(list)

class FileListItemWidget(QWidget):
    """Her dosya satırı: ikon + ad + boyut + silme butonu"""
    remove_requested = Signal(str)
```

**Dönüşüm başlatma metodları:**

| Metod                      | Core fonksiyonu                         | Ek parametreler            |
|----------------------------|-----------------------------------------|----------------------------|
| `_start_image_to_pdf()`    | `image_to_pdf.convert_images_to_pdf()`  | page_size                  |
| `_start_image_convert()`   | `image_convert.convert_images()`        | output_format, quality     |
| `_start_word_to_pdf()`     | `word_to_pdf.convert_word_to_pdf()`     | —                          |
| `_start_pdf_merge()`       | `pdf_merge.merge_pdfs()`                | output_path (kullanıcı seçer) |
| `_start_pdf_split_all()`   | `pdf_split.split_pdf_by_pages()`        | —                          |
| `_start_pdf_split_ranges()`| `pdf_split.split_pdf_by_ranges()`       | range_str                  |
| `_start_pdf_to_image()`    | `pdf_to_image.convert_pdf_to_images()`  | output_format, dpi=150     |
| `_start_pdf_to_word()`     | `pdf_to_word.convert_pdf_to_word()`     | —                          |

**Çıktı yolları (hardcoded):**

| İşlem             | Varsayılan Çıktı                           |
|-------------------|--------------------------------------------|
| Resim → PDF       | `{kaynak_dizin}/converted_images.pdf`      |
| Format dönüştür   | `{kaynak_dizin}/` (aynı klasör)            |
| Word → PDF        | `{kaynak_dizin}/{stem}.pdf`                |
| PDF birleştir     | Kullanıcı seçer (QFileDialog.getSaveFileName) |
| PDF böl           | `{kaynak_dizin}/split_output/`             |
| PDF → Resim       | `{kaynak_dizin}/pdf_pages/`                |
| PDF → Word        | `{kaynak_dizin}/{stem}.docx`               |

---

## 5. Bağımlılıklar

### 5.1 `requirements.txt` (mevcut)

```
PySide6==6.11.1
Pillow==12.0.0
pypdf==6.14.2
docx2pdf==0.1.8
qtawesome==1.4.2
pymupdf==1.28.2
pdf2docx==0.5.13
```

### 5.2 Build bağımlılıkları

`requirements-build.txt`, doğrulanan PyInstaller ve hook sürümlerini sabitler:

```text
pyinstaller==6.22.2
pyinstaller-hooks-contrib==2026.7
```

### 5.3 Sistem bağımlılıkları

- **Microsoft Word** — `word_to_pdf.py` için gerekli (docx2pdf COM automation)
- Yalnızca Windows ve macOS'ta çalışır

---

## 6. Signal/Slot Bağlantı Haritası

```
DropZone.files_dropped ──────────→ SmartPanel._on_files_dropped
FileListWidget.files_dropped ────→ SmartPanel._add_more_files
mini_drop.files_dropped ─────────→ SmartPanel._add_more_files
FileListItemWidget.remove_requested → SmartPanel._remove_file
ProgressWidget.clear_requested ──→ SmartPanel._reset_to_empty

browse_btn.clicked ──────────────→ SmartPanel._open_file_dialog
add_more_btn.clicked ────────────→ SmartPanel._open_file_dialog_addmore
reset_btn.clicked ───────────────→ SmartPanel._reset_to_empty

img_to_pdf_btn.clicked ──────────→ SmartPanel._start_image_to_pdf
img_convert_fmt_btn.clicked ─────→ SmartPanel._start_image_convert
word_to_pdf_btn.clicked ─────────→ SmartPanel._start_word_to_pdf
pdf_merge_btn.clicked ───────────→ SmartPanel._start_pdf_merge
pdf_split_all_btn.clicked ───────→ SmartPanel._start_pdf_split_all
pdf_split_range_btn.clicked ─────→ SmartPanel._start_pdf_split_ranges
pdf_to_img_btn.clicked ──────────→ SmartPanel._start_pdf_to_image
pdf_to_word_btn.clicked ─────────→ SmartPanel._start_pdf_to_word

img_fmt_combo.currentTextChanged → SmartPanel._on_img_fmt_changed
img_quality_slider.valueChanged  → img_quality_label.setText

ConversionWorker.progress ───────→ ProgressWidget.set_progress
ConversionWorker.status ─────────→ ProgressWidget.set_status
ConversionWorker.succeeded ──────→ SmartPanel._on_finished → ProgressWidget.set_finished
ConversionWorker.error ──────────→ SmartPanel._on_error → ProgressWidget.set_error
QThread.finished ────────────────→ SmartPanel._cleanup_worker
```

---

## 7. QSS Tema Sistemi

Tüm QSS, `main.py` içindeki `DARK_THEME` string'inde tanımlıdır (satır 13–330).
`app.setStyleSheet(DARK_THEME)` ile global olarak uygulanır.

**objectName bazlı stil kuralları:**
- `QPushButton#primaryBtn` — gradient mor-mavi (accent) buton
- `QPushButton#successBtn` — gradient yeşil buton
- `QListWidget#fileList` — dosya listesi (dark bg, rounded)
- `QLabel#titleLabel` — büyük başlık (20px, bold, beyaz)
- `QLabel#subtitleLabel` — alt başlık (12px, dim)
- `QLabel#sectionLabel` — bölüm etiketi (10px, uppercase letter-spacing)

**Widget içi stiller:** `DropZone`, `ProgressWidget`, `SmartPanel` header ve kartlar
kendi `setStyleSheet()` çağrılarını yaparak `objectName`'e bağlı isolation sağlar.
Çocuk widget'lara `background: transparent; border: none;` uygulanır.

---

## 8. Build ve Dağıtım

### 8.1 PyInstaller (`build.py`)

```bash
python build.py
# → python -m PyInstaller --noconsole --onefile ...
# → dist/FileConverter.exe
```

- Build öncesi `dist/` ve `build/` temizlenir
- PATH'teki `pyinstaller.exe` yerine aktif Python yorumlayıcısı kullanılır
- `assets/fileconverter.ico` EXE'ye gömülür ve runtime verisi olarak paketlenir
- `--noconsole`: Console penceresi açılmaz
- `--onefile`: Tek .exe çıktı

### 8.2 Inno Setup (`installer.iss`)

- AppVersion: 2.0
- Dil: Türkçe
- Hedef: `{autopf}\FileConverter`
- LZMA2 sıkıştırma
- Masaüstü kısayolu (opsiyonel)
- Kurulum sonrası otomatik başlatma

---

## 9. Bilinen Sorunlar ve Teknik Borç

1. **`requirements.txt` eksik:** ~~`pymupdf` ve `pdf2docx` paketleri listelenmiyor~~ ✅ Düzeltildi
2. **Sabit çıktı dosya adları:** ~~`converted_images.pdf` gibi sabit isimler üzerine yazma riski taşır~~ ✅ Düzeltildi (Akıllı otomatik isimlendirme `_1, _2` vb.)
3. **Worker iptal mekanizması:** ~~Uzun dönüşümler iptal edilemiyor~~ ✅ Düzeltildi (İptal Et butonu + CancelledException)
4. **DPI ayarı UI'da yok:** ~~`pdf_to_image` sabit 150 DPI kullanıyor~~ ✅ Düzeltildi (72, 150, 300, 600 DPI seçimi eklendi)
5. **Word toplu dönüştürme yok:** ~~Tek seferde yalnızca 1 Word dosyası dönüştürülebilir~~ ✅ Düzeltildi
6. **Çıktı konumu seçimi yok:** ~~Yalnızca PDF merge'de var~~ ✅ Düzeltildi (Her işlem öncesi QFileDialog soruyor)
7. **Logging altyapısı yok:** Hata takibi zorlaşır
8. **Uygulama ikonu:** ✅ PNG kaynak ve 16–256 px ICO oluşturuldu; pencere/build/installer'a bağlandı
9. **Test paketi:** ✅ `tests/` altında 37 birim ve regresyon testi mevcut
10. **Worker sinyal adı:** ✅ Başarı sinyali `succeeded`; temizlik yerleşik `QThread.finished` üzerinden yapılır
11. **Kısmi çıktılar:** ✅ Atomik tekli çıktılar ve başarısız toplu işlem temizliği eklendi
12. **Klasör tarama:** ✅ Büyük klasörler `PathScanWorker` ile UI thread'i dışında taranır
13. **Güvenli kapanış:** ✅ Aktif işlem iptal/temizlik tamamlanmadan pencere kapatılmaz
14. **Kalan borç:** Logging, çok kareli TIFF/WEBP ve `SmartPanel` bileşenlere ayırma

---

## 10. Geliştirme Kuralları

### 10.1 Yeni Dönüşüm Motoru Ekleme

1. `core/` altında yeni modül oluştur (örn: `core/excel_to_pdf.py`)
2. Fonksiyon `progress_callback` ve `status_callback` kabul etmeli
3. Başarıda `str` (çıktı yolu) dönmeli, hatada exception fırlatmalı
4. `core/file_detector.py`'de yeni uzantıları ekle
5. `ui/panels/smart_panel.py`'de:
   - Yeni action widget oluştur (`_build_xxx_actions()`)
   - `action_stack`'e ekle
   - `_update_action_stack()` map'ini güncelle
   - Yeni `_start_xxx()` metodu yaz
6. `ui/drop_zone.py`'deki dosya filtresi string'ine yeni uzantıları ekle

### 10.2 Kod Stili

- Tüm UI metinleri **Türkçe** olarak yazılır
- Docstring'ler ve yorumlar **İngilizce** olarak yazılır
- Bağımlılıklar lazy import edilir (fonksiyon içinde `import`)
- Hata mesajları son kullanıcıya yönelik, açıklayıcı ve Türkçe olmalı
- `frozenset` uzantı kümeleri için kullanılır
- `Path` (pathlib) tüm dosya yolu işlemleri için kullanılır
- Tip annotasyonları: Python 3.12+ union syntax (`X | None`)

### 10.3 QSS Stili Ekleme

- Global stiller `main.py` → `DARK_THEME` string'ine eklenir
- Widget-spesifik stiller ilgili widget'ın `__init__` veya `_build_ui` metodunda `setStyleSheet()` ile uygulanır
- Yeni widget'lara benzersiz `objectName` verilir ve QSS bu ismi hedefler
- Çocuk widget'larda `background: transparent; border: none;` zorunludur (cascading sorunlarını önler)

### 10.4 Thread Güvenliği

- Tüm ağır işlemler `ConversionWorker` (QThread) üzerinde çalışır
- UI güncellemeleri yalnızca Signal/Slot üzerinden yapılır
- Worker'dan doğrudan UI widget'ına erişim **YASAKTIR**
- Worker tamamlandıktan sonra `_cleanup_worker()` ile `deleteLater()` çağrılır

---

## 11. Çalıştırma

```bash
# Bağımlılıkları kur
pip install PySide6 Pillow pypdf docx2pdf qtawesome pymupdf pdf2docx

# Uygulamayı başlat
python main.py

# Testleri çalıştır
python -m unittest discover -s tests -v

# Standalone build (gerekirse önce build bağımlılıklarını kur)
pip install -r requirements-build.txt
python build.py
```
