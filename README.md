# FileConverter

**Sürüm:** 2.0.0

FileConverter; resim, PDF ve Word belgeleri için sık kullanılan dönüşümleri tek
bir PySide6 masaüstü arayüzünde toplayan bir dosya dönüştürme uygulamasıdır.
Dosyalar seçilebilir veya sürükle-bırak ile eklenebilir; desteklenen klasörler
alt dizinleriyle birlikte taranır.

## Desteklenen dönüşümler

| Kaynak | Hedef / işlem | Açıklama |
|---|---|---|
| JPG, JPEG, PNG, WEBP, BMP, TIFF | PDF | Çoklu resim, A4/Letter/orijinal sayfa boyutu |
| JPG, JPEG, PNG, WEBP, BMP, TIFF | JPG, PNG, WEBP | Toplu format ve kalite dönüşümü |
| DOC, DOCX | PDF | Microsoft Word üzerinden tekli/toplu dönüşüm |
| Birden fazla PDF | PDF | Sıralı birleştirme |
| PDF | PDF | Her sayfayı veya seçilen aralıkları ayırma |
| PDF | PNG, JPG | 72/150/300/600 DPI sayfa render işlemi |
| PDF | DOCX | Metin ve yerleşim odaklı Word dönüşümü |

## Gereksinimler

- Python 3.12 veya üzeri
- Windows ya da kısmi macOS desteği
- Word → PDF için Microsoft Word

PDF → Word işlemi OCR yapmaz. Taranmış belgelerde metinlerin düzenlenebilir hale
gelmesi beklenmemelidir; karmaşık tablolar ve sayfa düzenleri yaklaşık sonuç
verebilir.

## Kurulum ve çalıştırma

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

## Testler

Test paketi ek bağımlılık gerektirmeyen standart `unittest` altyapısını kullanır:

```powershell
python -m unittest discover -s tests -v
```

Testler dosya algılama, PDF sayfa aralıkları, Word toplu dönüşüm davranışı,
atomik çıktı güvenliği, worker yaşam döngüsü, kaynak kapatma, arka planda klasör
tarama ve UI regresyonlarını kapsar. Mevcut paket 35 test içerir.

## Standalone EXE oluşturma

```powershell
python -m pip install -r requirements-build.txt
python build.py
```

Çıktı `dist/FileConverter.exe` konumunda oluşturulur. Build scripti PyInstaller'ı
aktif Python yorumlayıcısı üzerinden çalıştırır; sistem PATH ayarına bağımlı
değildir. PDF → Word bağımlılıkları nedeniyle tek dosyalı EXE yaklaşık 168 MB'tır.

## Windows installer

Önce standalone EXE'yi oluşturun, ardından Inno Setup 6 ile `installer.iss`
dosyasını derleyin. Sonuç `dist/FileConverter-2.0.0-Setup.exe` olarak yazılır.

2.0.0 launch doğrulamasında gerçek EXE başlangıcı, Microsoft Word üzerinden
DOCX → PDF dönüşümü ve installer kurulum/çalıştırma/kaldırma akışı başarıyla
test edilmiştir.

## Bilinen sınırlamalar

- Şifreli PDF dosyaları desteklenmez.
- Çoklu PDF seçildiğinde arayüz yalnızca birleştirme aksiyonunu gösterir.
- PDF → Word işlemi başladıktan sonra güvenli biçimde yarıda kesilemediği için bu
  işlemde iptal butonu gösterilmez.
- Çok sayfalı TIFF ve animasyonlu WEBP dosyalarında yalnızca aktif/ilk kare
  dönüştürülür.
- Çok büyük resim grupları PDF oluşturulurken yüksek bellek kullanabilir.
- Uygulama ve installer henüz ticari kod imzalama sertifikasıyla imzalanmamıştır;
  Windows ilk çalıştırmada SmartScreen uyarısı gösterebilir.

## Proje yapısı

```text
core/                 Dönüşüm motorları ve arka plan worker'ı
ui/                   PySide6 kullanıcı arayüzü
tests/                Kalıcı regresyon ve birim testleri
assets/               PNG kaynak ikon ve çok boyutlu Windows ICO
main.py               Uygulama giriş noktası
build.py              PyInstaller build akışı
installer.iss         Inno Setup yapılandırması
```
