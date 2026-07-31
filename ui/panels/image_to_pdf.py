"""
ui/panels/image_to_pdf.py — Resim → PDF Panel

ÖĞRENME NOTU — Widget Kompozisyonu:
  Bu panel, daha önce yazdığımız bileşenleri bir araya getirir:
    DropZone         → dosya alma
    QListWidget      → eklenen dosyaları listele
    QComboBox        → ayarlar (sayfa boyutu)
    ConversionWorker → arka planda dönüştür
    ProgressWidget   → ilerlemeyi göster
  
  Bir PySide6 panel genellikle şu sorumlulukları üstlenir:
    1. Alt widget'ları düzenle (layout)
    2. Sinyalleri birbirine bağla (connect)
    3. İş mantığını tetikle (worker başlat)
    4. Kullanıcıya durum göster (progress, hata)
"""

import os
from pathlib import Path
import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QComboBox, QMessageBox, QFileDialog,
    QSizePolicy,
)
from PySide6.QtCore import Qt

from ui.drop_zone import DropZone
from ui.progress_widget import ProgressWidget
from core.worker import ConversionWorker
from core import image_to_pdf as converter


class ImageToPdfPanel(QWidget):
    """
    Resim → PDF dönüşüm paneli.
    Sürükle-bırak ile JPG/PNG/WEBP dosyaları alır, tek PDF'e dönüştürür.
    """
    
    ACCEPTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ConversionWorker | None = None  # aktif thread referansı
        self._build_ui()
        self._connect_signals()
    
    def _build_ui(self):
        """Tüm widget'ları oluştur ve layout'a yerleştir."""
        
        # Ana dikey layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(16)
        
        # ── Başlık ───────────────────────────────────────────────────────────
        header_layout = QHBoxLayout()
        
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon("fa5s.file-image", color="#7c6af7").pixmap(32, 32))
        
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Resim → PDF")
        title.setObjectName("titleLabel")
        subtitle = QLabel("JPG, PNG, WEBP ve diğer resim formatlarını tek PDF'e dönüştürün")
        subtitle.setObjectName("subtitleLabel")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        
        header_layout.addWidget(icon_label)
        header_layout.addSpacing(10)
        header_layout.addLayout(title_col)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # ── Sürükle-Bırak Alanı ──────────────────────────────────────────────
        self.drop_zone = DropZone(accepted_extensions=self.ACCEPTED_EXTENSIONS)
        main_layout.addWidget(self.drop_zone)
        
        # ── Dosya Listesi Başlığı + Butonlar ─────────────────────────────────
        list_header = QHBoxLayout()
        
        files_label = QLabel("Eklenmiş Dosyalar")
        files_label.setObjectName("sectionLabel")
        
        self.add_btn = QPushButton("  Dosya Ekle")
        self.add_btn.setIcon(qta.icon("fa5s.plus", color="#9090c0"))
        self.add_btn.setFixedHeight(30)
        
        self.remove_btn = QPushButton("  Seçili Kaldır")
        self.remove_btn.setIcon(qta.icon("fa5s.minus", color="#9090c0"))
        self.remove_btn.setFixedHeight(30)
        self.remove_btn.setEnabled(False)
        
        self.clear_list_btn = QPushButton("  Tümünü Temizle")
        self.clear_list_btn.setIcon(qta.icon("fa5s.times", color="#9090c0"))
        self.clear_list_btn.setFixedHeight(30)
        self.clear_list_btn.setEnabled(False)
        
        list_header.addWidget(files_label)
        list_header.addStretch()
        list_header.addWidget(self.add_btn)
        list_header.addWidget(self.remove_btn)
        list_header.addWidget(self.clear_list_btn)
        main_layout.addLayout(list_header)
        
        # ── Dosya Listesi ─────────────────────────────────────────────────────
        # QListWidget: seçilebilir, sıralanabilir öğe listesi
        self.file_list = QListWidget()
        self.file_list.setObjectName("fileList")
        self.file_list.setMinimumHeight(140)
        self.file_list.setMaximumHeight(220)
        # Çoklu seçime izin ver (Ctrl+tıklama)
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        # Boş mesaj (placeholder)
        self.file_list.addItem("— Henüz dosya eklenmedi —")
        self.file_list.item(0).setForeground(Qt.GlobalColor.darkGray)
        self.file_list.item(0).setFlags(Qt.ItemFlag.NoItemFlags)  # seçilemez
        main_layout.addWidget(self.file_list)
        
        # ── Ayarlar ──────────────────────────────────────────────────────────
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(16)
        
        # Sayfa boyutu seçici
        page_label = QLabel("Sayfa Boyutu:")
        page_label.setStyleSheet("color: #8080b0;")
        
        self.page_size_combo = QComboBox()
        for size_name in converter.PAPER_SIZES_96DPI.keys():
            self.page_size_combo.addItem(size_name)
        # Varsayılan: A4
        self.page_size_combo.setCurrentText("A4")
        
        # Dosya adı bilgisi
        self.file_count_label = QLabel("0 dosya seçildi")
        self.file_count_label.setStyleSheet("color: #5050a0; font-size: 12px;")
        
        settings_layout.addWidget(page_label)
        settings_layout.addWidget(self.page_size_combo)
        settings_layout.addStretch()
        settings_layout.addWidget(self.file_count_label)
        main_layout.addLayout(settings_layout)
        
        # ── Dönüştür Butonu ───────────────────────────────────────────────────
        self.convert_btn = QPushButton("  PDF Oluştur")
        self.convert_btn.setObjectName("primaryBtn")
        self.convert_btn.setIcon(qta.icon("fa5s.magic", color="#ffffff"))
        self.convert_btn.setEnabled(False)
        self.convert_btn.setFixedHeight(48)
        main_layout.addWidget(self.convert_btn)
        
        # ── İlerleme Widget'ı ─────────────────────────────────────────────────
        self.progress_widget = ProgressWidget()
        main_layout.addWidget(self.progress_widget)
        
        # Alt boşluk
        main_layout.addStretch()
    
    def _connect_signals(self):
        """Tüm sinyal → slot bağlantılarını kur."""
        
        # Drop zone → dosya ekle
        self.drop_zone.files_dropped.connect(self._add_files)
        
        # Liste butonları
        self.add_btn.clicked.connect(self._open_file_dialog)
        self.remove_btn.clicked.connect(self._remove_selected)
        self.clear_list_btn.clicked.connect(self._clear_file_list)
        
        # Liste seçimi değişince "Kaldır" butonu aktif olsun
        self.file_list.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Dönüştür
        self.convert_btn.clicked.connect(self._start_conversion)
        
        # Progress widget "Temizle" butonu
        self.progress_widget.clear_requested.connect(self._clear_file_list)
    
    # ── Dosya Yönetimi ────────────────────────────────────────────────────────
    
    def _open_file_dialog(self):
        """Standart dosya seçme dialogunu aç."""
        
        # QFileDialog.getOpenFileNames: Birden fazla dosya seçebilir
        # Döndürür: (dosya_listesi, seçili_filtre)
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Resim Dosyaları Seç",
            "",  # başlangıç klasörü (boş = son kullanılan)
            "Resim Dosyaları (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif)"
        )
        if paths:
            self._add_files(paths)
    
    def _add_files(self, paths: list[str]):
        """
        Dosyaları listeye ekle. Tekrar eklemeyi önle.
        
        Mevcut dosyaları takip etmek için set kullanıyoruz (O(1) arama).
        """
        # Eğer liste "henüz dosya yok" placeholder'ı içeriyorsa temizle
        if self._is_empty_placeholder():
            self.file_list.clear()
        
        # Mevcut yolları topla (tekrar eklemeyi önlemek için)
        existing = {
            self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.file_list.count())
        }
        
        added = 0
        for path_str in paths:
            path = Path(path_str)
            
            # Uzantı kontrolü (drop_zone zaten filtreler, ama dialog için de kontrol et)
            if path.suffix.lower() not in self.ACCEPTED_EXTENSIONS:
                continue
            
            # Tekrar ekleme kontrolü
            if path_str in existing:
                continue
            
            # Liste öğesi oluştur
            item = QListWidgetItem()
            item.setText(f"  {path.name}")
            item.setToolTip(path_str)  # tam yol tooltip'te
            item.setIcon(qta.icon("fa5s.image", color="#7070c0"))
            
            # Tam yolu UserRole'a sakla (görünmez veri)
            # UserRole: Qt'nin özel veri saklama mekanizması
            item.setData(Qt.ItemDataRole.UserRole, path_str)
            
            self.file_list.addItem(item)
            added += 1
        
        if added > 0:
            self._update_ui_state()
    
    def _remove_selected(self):
        """Seçili dosyaları listeden kaldır."""
        # takeItem ile kaldırma: listeyi tersten dolaş (index kayması önlemi)
        selected_rows = [self.file_list.row(item) for item in self.file_list.selectedItems()]
        for row in sorted(selected_rows, reverse=True):
            self.file_list.takeItem(row)
        
        if self.file_list.count() == 0:
            self._show_placeholder()
        
        self._update_ui_state()
    
    def _clear_file_list(self):
        """Tüm dosyaları listeden kaldır."""
        self.file_list.clear()
        self._show_placeholder()
        self._update_ui_state()
    
    def _show_placeholder(self):
        """Boş liste mesajını göster."""
        self.file_list.addItem("— Henüz dosya eklenmedi —")
        self.file_list.item(0).setForeground(Qt.GlobalColor.darkGray)
        self.file_list.item(0).setFlags(Qt.ItemFlag.NoItemFlags)
    
    def _is_empty_placeholder(self) -> bool:
        """Liste sadece placeholder mı içeriyor?"""
        return (
            self.file_list.count() == 1 and
            not self.file_list.item(0).flags() & Qt.ItemFlag.ItemIsEnabled
        )
    
    def _get_file_paths(self) -> list[str]:
        """Listedeki tüm geçerli dosya yollarını döndür."""
        paths = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:  # placeholder'ın UserRole'u None
                paths.append(path)
        return paths
    
    def _on_selection_changed(self):
        """Liste seçimi değişince buton durumlarını güncelle."""
        has_selection = bool(self.file_list.selectedItems())
        self.remove_btn.setEnabled(has_selection)
    
    def _update_ui_state(self):
        """Dosya sayısına göre buton ve etiket durumlarını güncelle."""
        paths = self._get_file_paths()
        count = len(paths)
        
        self.convert_btn.setEnabled(count > 0)
        self.clear_list_btn.setEnabled(count > 0)
        
        if count == 0:
            self.file_count_label.setText("0 dosya seçildi")
        elif count == 1:
            self.file_count_label.setText("1 dosya seçildi")
        else:
            self.file_count_label.setText(f"{count} dosya seçildi")
    
    # ── Dönüşüm ──────────────────────────────────────────────────────────────
    
    def _start_conversion(self):
        """
        Dönüşümü başlat.
        
        Adımlar:
          1. Dosya yollarını topla
          2. Çıktı yolunu belirle
          3. ConversionWorker oluştur ve sinyalleri bağla
          4. Worker'ı başlat (ayrı thread'de çalışır)
          5. UI'yı "çalışıyor" moduna al
        """
        paths = self._get_file_paths()
        if not paths:
            return
        
        # ── Çıktı Yolu ───────────────────────────────────────────────────────
        # Kaynak dosyayla aynı klasör, "converted_" öneki
        source_dir = Path(paths[0]).parent
        output_name = "converted_images.pdf"
        output_path = str(source_dir / output_name)
        
        # ── Worker Oluştur ────────────────────────────────────────────────────
        page_size = self.page_size_combo.currentText()
        
        self._worker = ConversionWorker(
            func=converter.convert_images_to_pdf,
            kwargs={
                'image_paths': paths,
                'output_path': output_path,
                'page_size':   page_size,
                # progress_callback ve status_callback worker tarafından eklenir
            }
        )
        
        # ── Sinyalleri Bağla ─────────────────────────────────────────────────
        # Worker sinyalleri → UI metodları (ana thread'de güvenli)
        self._worker.progress.connect(self.progress_widget.set_progress)
        self._worker.status.connect(self.progress_widget.set_status)
        self._worker.finished.connect(self._on_conversion_finished)
        self._worker.error.connect(self._on_conversion_error)
        # Thread bitince referansı temizle (bellek sızıntısı önlemi)
        self._worker.finished.connect(lambda _: self._cleanup_worker())
        self._worker.error.connect(lambda _: self._cleanup_worker())
        
        # ── UI'yı Kilitle (işlem süresince) ───────────────────────────────────
        self.convert_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self.clear_list_btn.setEnabled(False)
        self.progress_widget.start()
        
        # ── Thread'i Başlat ────────────────────────────────────────────────────
        # Bu satırdan sonra QThread.run() ayrı bir thread'de çalışmaya başlar
        # Ana thread bloklanmaz → UI yanıt vermeye devam eder
        self._worker.start()
    
    def _on_conversion_finished(self, output_path: str):
        """İşlem başarıyla bitti."""
        self.progress_widget.set_finished(output_path)
        self._unlock_ui()
    
    def _on_conversion_error(self, message: str):
        """İşlem sırasında hata oluştu."""
        self.progress_widget.set_error(message)
        self._unlock_ui()
        
        # Kullanıcıya ek hata dialogu göster
        QMessageBox.warning(
            self,
            "Dönüşüm Hatası",
            f"İşlem sırasında bir sorun oluştu:\n\n{message}\n\n"
            "Lütfen dosyaların bozuk olmadığını kontrol edin.",
        )
    
    def _unlock_ui(self):
        """İşlem bitince UI elemanlarını tekrar aktif et."""
        paths = self._get_file_paths()
        self.convert_btn.setEnabled(len(paths) > 0)
        self.add_btn.setEnabled(True)
        self.clear_list_btn.setEnabled(len(paths) > 0)
    
    def _cleanup_worker(self):
        """Thread referansını temizle."""
        if self._worker:
            self._worker.deleteLater()  # Qt bellek yönetimi
            self._worker = None
