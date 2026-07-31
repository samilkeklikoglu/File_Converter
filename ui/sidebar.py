"""
ui/sidebar.py — Sol kenar çubuğu

ÖĞRENME NOTU — Sinyal & Slot:
  Qt'de widget'lar birbirleriyle "sinyal → slot" mekanizmasıyla konuşur.
  
  - Sinyal (Signal): Bir olay gerçekleştiğinde yayılan mesaj
    Örnek: kullanıcı bir öğeye tıkladığında currentRowChanged(int) sinyali yayılır
  
  - Slot: Sinyali "dinleyen" ve yanıt veren metot
    Herhangi bir Python fonksiyonu/metodu slot olabilir
  
  Bağlantı: widget.sinyal.connect(slot_fonksiyon)
  
  Bu dosyada: Sidebar'da seçim değişince → MainWindow'daki panel değişir.
"""

import qtawesome as qta
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class Sidebar(QWidget):
    """
    Sol kenar çubuğu widget'ı.
    
    Kullanıcı bir kategoriye tıkladığında `category_changed` sinyali yayılır.
    MainWindow bu sinyali dinleyerek sağ paneli değiştirir.
    
    Signal tanımı: Signal(int) → int, hangi indeksin seçildiğini taşır.
    """
    
    # Sınıf düzeyinde sinyal tanımı — her Sidebar örneği bu sinyale sahip olur
    category_changed = Signal(int)
    
    # Kenar çubuğundaki kategoriler: (başlık, qtawesome ikon adı, açıklama)
    CATEGORIES = [
        ("Resim → PDF",      "fa5s.file-image",    "JPG/PNG → PDF"),
        ("Word → PDF",       "fa5s.file-word",     "DOCX → PDF"),
        ("PDF Birleştir",    "fa5s.object-group",  "Birden fazla PDF'i birleştir"),
        ("Resim Dönüştür",   "fa5s.exchange-alt",  "JPG ↔ PNG ↔ WEBP"),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self._build_ui()
    
    def _build_ui(self):
        """Widget'ın iç yapısını oluşturur."""
        
        # QVBoxLayout: widget'ları dikey (üst→alt) sıralar
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # ── Uygulama Logo Alanı ──────────────────────────────────────────────
        logo_widget = QWidget()
        logo_widget.setFixedHeight(70)
        logo_widget.setStyleSheet("background-color: #0d0d18; border-bottom: 1px solid #2a2a40;")
        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setContentsMargins(20, 0, 0, 0)
        
        app_name = QLabel("FileConverter")
        app_name.setObjectName("titleLabel")  # QSS'deki #titleLabel stilini uygular
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        app_name.setFont(font)
        
        tagline = QLabel("Dosya Dönüştürme Aracı")
        tagline.setObjectName("subtitleLabel")
        
        logo_layout.addWidget(app_name)
        logo_layout.addWidget(tagline)
        layout.addWidget(logo_widget)
        
        # ── Bölüm Başlığı ───────────────────────────────────────────────────
        section_label = QLabel("  İŞLEMLER")
        section_label.setObjectName("sectionLabel")
        section_label.setContentsMargins(20, 16, 0, 8)
        layout.addWidget(section_label)
        
        # ── Kategori Listesi ─────────────────────────────────────────────────
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        # Tıklamada focus çerçevesi görünmesin
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        for title, icon_name, desc in self.CATEGORIES:
            item = QListWidgetItem()
            # qtawesome.icon(): Font Awesome ikonunu QIcon'a dönüştürür
            item.setIcon(qta.icon(icon_name, color="#9090c0"))
            item.setText(f"  {title}")
            item.setToolTip(desc)  # üzerine gelince açıklama göster
            self.list_widget.addItem(item)
        
        # İlk kategori varsayılan seçili
        self.list_widget.setCurrentRow(0)
        
        # Sinyal bağlantısı: seçim değişince _on_selection_changed çağrılır
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        
        layout.addWidget(self.list_widget)
        
        # Alt boşluk (esnek)
        layout.addStretch()
        
        # ── Alt Versiyon Bilgisi ─────────────────────────────────────────────
        version_label = QLabel("v1.0.0 — MVP")
        version_label.setObjectName("subtitleLabel")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setContentsMargins(0, 0, 0, 12)
        layout.addWidget(version_label)
    
    def _on_selection_changed(self, row: int):
        """
        Liste seçimi değişince çağrılır.
        Bu metot bir "slot": sinyal tarafından tetiklenir.
        
        `row`: seçilen satırın 0-tabanlı indeksi
        """
        # Kendi sinyalimizi yayıyoruz → MainWindow dinleyecek
        self.category_changed.emit(row)
