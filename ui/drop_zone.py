"""
ui/drop_zone.py — Sürükle-Bırak Alanı

ÖĞRENME NOTU — Drag & Drop:
  Qt'de sürükle-bırak, event (olay) override etmekle çalışır.
  
  Sürükleme döngüsü:
  1. dragEnterEvent  → kullanıcı widget'ın üzerine geldi (kabul et/reddet)
  2. dragMoveEvent   → widget üzerinde hareket ediyor (genellikle aynı karar)
  3. dropEvent       → kullanıcı bıraktı → dosya yollarını çıkar
  4. dragLeaveEvent  → kullanıcı widget'tan çıktı (iptal)
  
  MIME Data: Sürüklenen veri, MIME türleriyle taşınır.
  Dosya sürükleme → 'text/uri-list' MIME türü → QUrl listesi
  
  QUrl.toLocalFile() → "C:/Users/.../foto.jpg" gibi yerel yola çevirir.
"""

import qtawesome as qta
from pathlib import Path
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QDragLeaveEvent


class DropZone(QWidget):
    """
    Sürükle-bırak alanı widget'ı.
    
    Parametreler:
        accepted_extensions: Kabul edilen uzantılar kümesi, örn: {'.jpg', '.png'}
                             None verilirse tüm dosyalar kabul edilir.
    
    Sinyaller:
        files_dropped(list[str]): Bırakılan dosyaların tam yolları
    """
    
    files_dropped = Signal(list)  # list[str] — dosya yolları
    
    # Renk sabitleri (QSS'ye taşımak yerine burada tutuyoruz, çünkü
    # programatik olarak değiştiriyoruz)
    _STYLE_NORMAL = """
        QWidget#dropZone {
            background-color: #13131f;
            border: 2px dashed #3a3a60;
            border-radius: 14px;
        }
    """
    _STYLE_HOVER = """
        QWidget#dropZone {
            background-color: #1a1a35;
            border: 2px dashed #7c6af7;
            border-radius: 14px;
        }
    """
    _STYLE_REJECT = """
        QWidget#dropZone {
            background-color: #1f1010;
            border: 2px dashed #c0392b;
            border-radius: 14px;
        }
    """
    
    def __init__(self, accepted_extensions: set[str] | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.accepted_extensions = accepted_extensions  # örn: {'.jpg', '.png', '.jpeg'}
        
        # Qt'ye bu widget'ın sürüklemeyi kabul ettiğini söyle
        self.setAcceptDrops(True)
        self.setMinimumHeight(180)
        
        self._build_ui()
        self._set_normal_style()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        
        # İkon (qtawesome ile)
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_pixmap = qta.icon("fa5s.cloud-upload-alt", color="#5a5a90").pixmap(52, 52)
        self.icon_label.setPixmap(icon_pixmap)
        
        # Ana metin
        self.main_label = QLabel("Dosyaları buraya sürükleyin")
        self.main_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #8080c0;")
        
        # Alt metin (uzantılar)
        ext_text = "veya tıklayarak seçin"
        if self.accepted_extensions:
            exts = "  ".join(e.upper().lstrip('.') for e in sorted(self.accepted_extensions))
            ext_text = f"Desteklenen: {exts}"
        
        self.sub_label = QLabel(ext_text)
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet("font-size: 12px; color: #505080;")
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.main_label)
        layout.addWidget(self.sub_label)
    
    # ── Sürükle-Bırak Event'leri ──────────────────────────────────────────────
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """
        Kullanıcı bir şeyi bu widget'ın üzerine sürükledi.
        
        event.mimeData(): Sürüklenen verinin içeriği
        hasUrls(): Dosya/klasör sürükleniyorsa True döner
        
        Eğer kabul edersek: event.acceptProposedAction()
        Reddedersek: event.ignore() → Qt başka widget'a sorar
        """
        if event.mimeData().hasUrls():
            # Sürüklenen dosyaların uzantılarını kontrol et
            urls = event.mimeData().urls()
            if self._has_valid_files(urls):
                event.acceptProposedAction()
                self._set_hover_style()
            else:
                event.acceptProposedAction()  # yine de kabul, ama kırmızı göster
                self._set_reject_style()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event: QDragMoveEvent):
        """
        Kullanıcı widget üzerinde hareket ediyor.
        dragEnterEvent ile aynı kararı veriyoruz.
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dragLeaveEvent(self, event: QDragLeaveEvent):
        """Kullanıcı widget'tan çıktı, normal stile dön."""
        self._set_normal_style()
    
    def dropEvent(self, event: QDropEvent):
        """
        Kullanıcı dosyaları bıraktı — asıl iş burada!
        
        event.mimeData().urls() → QUrl listesi
        url.toLocalFile()       → "C:/Users/.../foto.jpg" gibi yerel yol
        """
        self._set_normal_style()
        
        urls = event.mimeData().urls()
        
        # Geçerli dosya yollarını topla
        valid_paths = []
        for url in urls:
            local_path = url.toLocalFile()
            path = Path(local_path)
            
            # Klasör değil, dosya olmalı
            if not path.is_file():
                continue
            
            # Uzantı filtresi uygulanıyorsa kontrol et
            if self.accepted_extensions:
                if path.suffix.lower() not in self.accepted_extensions:
                    continue
            
            valid_paths.append(str(path))
        
        if valid_paths:
            # Sinyali yayıyoruz → bizi dinleyen panel dosyaları alacak
            self.files_dropped.emit(valid_paths)
            event.acceptProposedAction()
    
    # ── Yardımcı Metodlar ─────────────────────────────────────────────────────
    
    def _has_valid_files(self, urls) -> bool:
        """Sürüklenen dosyaların en az biri kabul edilen türde mi?"""
        if not self.accepted_extensions:
            return True  # filtre yoksa hepsini kabul et
        
        for url in urls:
            path = Path(url.toLocalFile())
            if path.suffix.lower() in self.accepted_extensions:
                return True
        return False
    
    def _set_normal_style(self):
        self.setStyleSheet(self._STYLE_NORMAL)
    
    def _set_hover_style(self):
        self.setStyleSheet(self._STYLE_HOVER)
    
    def _set_reject_style(self):
        self.setStyleSheet(self._STYLE_REJECT)
