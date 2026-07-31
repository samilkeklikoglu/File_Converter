"""
ui/main_window.py — Ana Uygulama Penceresi

ÖĞRENME NOTU — QMainWindow vs QWidget:
  
  QWidget: Temel widget sınıfı, her şey bunun alt sınıfı
  QMainWindow: Menü çubuğu, araç çubuğu, durum çubuğu, merkezi widget
               alanı gibi "pencere" özellikleri olan özel QWidget
  
  setCentralWidget(): QMainWindow'un merkezi içerik alanını belirler.
  Biz oraya QSplitter koyacağız.
  
ÖĞRENME NOTU — QSplitter:
  İki (veya daha fazla) widget'ı yan yana yerleştirir ve aralarındaki
  sınırı kullanıcının sürükleyerek ayarlamasına olanak tanır.
  
  Qt.Orientation.Horizontal → yan yana
  Qt.Orientation.Vertical   → alt alta
  
ÖĞRENME NOTU — QStackedWidget:
  Birden fazla widget'ı "üst üste" tutar; bir anda yalnızca biri görünür.
  setCurrentIndex(n) ile görünen widget değiştirilir.
  Bu, sol menü → sağ panel geçişlerinde idealdir.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.sidebar import Sidebar
from ui.panels.image_to_pdf import ImageToPdfPanel
from ui.panels.word_to_pdf import WordToPdfPanel
from ui.panels.placeholder import PlaceholderPanel


class MainWindow(QMainWindow):
    """
    Uygulamanın ana penceresi.
    
    Yapı:
      QMainWindow
        └── central_widget (QWidget)
              └── QSplitter (yatay)
                    ├── Sidebar          (sol, sabit genişlik)
                    └── QStackedWidget   (sağ, esnek)
                          ├── [0] ImageToPdfPanel
                          ├── [1] WordToPdfPanel
                          ├── [2] PdfMergePanel    (placeholder)
                          └── [3] ImageConvertPanel(placeholder)
    """
    
    def __init__(self):
        super().__init__()
        self._setup_window()
        self._build_ui()
        self._connect_signals()
    
    def _setup_window(self):
        """Pencere özelliklerini ayarla."""
        self.setWindowTitle("FileConverter — Dosya Dönüştürme Aracı")
        self.setMinimumSize(900, 620)
        self.resize(1100, 700)
        
        # Pencereyi ekranın ortasına konumlandır
        screen = self.screen().availableGeometry()
        x = (screen.width()  - self.width())  // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def _build_ui(self):
        """Ana layout ve widget'ları oluştur."""
        
        # ── Merkezi Widget ────────────────────────────────────────────────────
        # QMainWindow doğrudan layout alamaz; önce bir QWidget lazım
        central = QWidget()
        self.setCentralWidget(central)
        
        # Kenarlıksız yatay layout
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ── Sol Kenar Çubuğu ─────────────────────────────────────────────────
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)
        
        # ── Dikey Ayırıcı ────────────────────────────────────────────────────
        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setFrameShadow(QFrame.Shadow.Plain)
        vline.setStyleSheet("color: #2a2a40;")
        main_layout.addWidget(vline)
        
        # ── Sağ İçerik Alanı (QStackedWidget) ───────────────────────────────
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, stretch=1)  # stretch=1: kalan alanı kapla
        
        # Panel 0: Resim → PDF (tam çalışır)
        self.stack.addWidget(ImageToPdfPanel())
        
        # Panel 1: Word → PDF (tam çalışır)
        self.stack.addWidget(WordToPdfPanel())
        
        # Panel 2: PDF Birleştir (placeholder)
        self.stack.addWidget(PlaceholderPanel(
            title="PDF Birleştirme",
            icon_name="fa5s.object-group",
            description="Birden fazla PDF dosyasını tek bir belgede birleştirin.\npypdf kütüphanesi kullanılacak.",
        ))
        
        # Panel 3: Resim Format Dönüştür (placeholder)
        self.stack.addWidget(PlaceholderPanel(
            title="Resim Format Dönüşümü",
            icon_name="fa5s.exchange-alt",
            description="JPG, PNG ve WEBP formatları arasında toplu dönüşüm yapın.\nPillow kütüphanesi kullanılacak.",
        ))
        
        # Başlangıçta ilk panel görünür
        self.stack.setCurrentIndex(0)
    
    def _connect_signals(self):
        """Sidebar seçimi → panel değişikliği bağlantısı."""
        
        # Sidebar'ın category_changed sinyali (int) →
        # QStackedWidget'ın setCurrentIndex slotuna (int) bağla
        # Tek satır — bu kadar! İki widget birbirini tanımak zorunda değil.
        self.sidebar.category_changed.connect(self.stack.setCurrentIndex)
