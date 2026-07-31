"""
ui/progress_widget.py — İlerleme Çubuğu ve Durum Widget'ı

Bu widget, dönüşüm sırasında kullanıcıya bilgi verir:
  - QProgressBar: Yüzde gösterir
  - QLabel (durum): "İşleniyor: foto.jpg (2/5)" gibi metin
  - QPushButton (klasörü aç): İşlem bitince aktif olur
  - QPushButton (temizle): Yeni işlem için sıfırla
"""

import os
import subprocess
import sys
from pathlib import Path
import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal


class ProgressWidget(QWidget):
    """
    Dönüşüm ilerleme durumunu gösteren widget.
    
    Durumlar:
      - idle    : Henüz başlanmadı (gizli veya pasif)
      - running : İşlem devam ediyor
      - done    : Tamamlandı, "Klasörü Aç" butonu aktif
      - error   : Hata oluştu
    """
    
    # Kullanıcı "Temizle" butonuna basınca panelin dosya listesini sıfırlaması için
    clear_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._output_path: str | None = None  # Çıktı dosyasının yolu
        self._build_ui()
        self.reset()  # Başlangıç durumu
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)
        
        # ── Ayırıcı çizgi ───────────────────────────────────────────────────
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)
        
        # ── Durum Metni ──────────────────────────────────────────────────────
        self.status_label = QLabel("Hazır")
        self.status_label.setStyleSheet("color: #6060a0; font-size: 12px;")
        layout.addWidget(self.status_label)
        
        # ── İlerleme Çubuğu ──────────────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(18)
        layout.addWidget(self.progress_bar)
        
        # ── Alt Butonlar ─────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        # "Klasörü Aç" butonu — işlem bitmeden devre dışı
        self.open_btn = QPushButton("  Klasörü Aç")
        self.open_btn.setObjectName("successBtn")
        self.open_btn.setIcon(qta.icon("fa5s.folder-open", color="#ffffff"))
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_output_folder)
        
        # "Temizle" butonu
        self.clear_btn = QPushButton("  Temizle")
        self.clear_btn.setIcon(qta.icon("fa5s.trash-alt", color="#9090b0"))
        self.clear_btn.setEnabled(False)
        self.clear_btn.clicked.connect(self._on_clear)
        
        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    # ── Genel Kullanım API'si (dışarıdan çağrılacak metodlar) ────────────────
    
    def reset(self):
        """Widget'ı başlangıç durumuna getirir."""
        self._output_path = None
        self.progress_bar.setValue(0)
        self.status_label.setText("Hazır")
        self.status_label.setStyleSheet("color: #6060a0; font-size: 12px;")
        self.open_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
    
    def start(self):
        """Dönüşüm başladığında çağrılır."""
        self.progress_bar.setValue(0)
        self.open_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.set_status("Başlatılıyor...", color="#a0a0d0")
    
    def set_progress(self, value: int):
        """
        İlerleme yüzdesini günceller (0-100).
        Bu metot, QThread'den sinyal aracılığıyla çağrılacak.
        """
        self.progress_bar.setValue(value)
    
    def set_status(self, text: str, color: str = "#a0a0d0"):
        """Durum metnini günceller."""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px;")
    
    def set_finished(self, output_path: str):
        """
        Dönüşüm başarıyla tamamlandı.
        output_path: Oluşturulan dosyanın tam yolu
        """
        self._output_path = output_path
        self.progress_bar.setValue(100)
        self.set_status("✓  Dönüşüm tamamlandı!", color="#2ecc71")
        self.open_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
    
    def set_error(self, message: str):
        """Hata durumunda çağrılır."""
        self.set_status(f"✗  Hata: {message}", color="#e74c3c")
        self.progress_bar.setValue(0)
        self.clear_btn.setEnabled(True)
    
    # ── Özel Metodlar ────────────────────────────────────────────────────────
    
    def _open_output_folder(self):
        """
        Çıktı dosyasının bulunduğu klasörü işletim sistemi dosya yöneticisinde açar.
        
        Platform farkı:
          Windows : explorer /select,"dosya.pdf"  → dosyayı seçili gösterir
          macOS   : open -R dosya.pdf
          Linux   : xdg-open klasör/
        """
        if not self._output_path:
            return
        
        path = Path(self._output_path)
        folder = path.parent
        
        if sys.platform == "win32":
            # /select, ile dosyayı seçili göster
            subprocess.Popen(["explorer", "/select,", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])
    
    def _on_clear(self):
        """Temizle butonuna basıldı — sıfırla ve üst panele bildir."""
        self.reset()
        self.clear_requested.emit()
