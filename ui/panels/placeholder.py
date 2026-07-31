"""
ui/panels/placeholder.py — "Yakında" Placeholder Paneli

Word→PDF, PDF Birleştir ve Resim Dönüştür modülleri MVP'nin
ikinci aşamasında gelecek. Bu sırada güzel bir "yapım aşamasında"
ekranı gösteriyoruz.
"""

import qtawesome as qta
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class PlaceholderPanel(QWidget):
    """Henüz geliştirilmemiş modüller için geçici panel."""
    
    def __init__(self, title: str, icon_name: str, description: str, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)
        
        # İkon
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setPixmap(qta.icon(icon_name, color="#3a3a70").pixmap(72, 72))
        
        # Başlık
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 22px; font-weight: 700; color: #5050a0;")
        
        # Açıklama
        desc_label = QLabel(description)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("font-size: 14px; color: #404070;")
        desc_label.setWordWrap(True)
        
        # "Yakında" etiketi
        soon_label = QLabel("🚧  Yakında Geliyor")
        soon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        soon_label.setStyleSheet(
            "font-size: 13px; color: #7c6af7; font-weight: 600; "
            "background: #1a1a35; border-radius: 20px; padding: 8px 20px;"
        )
        
        layout.addStretch()
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addSpacing(12)
        layout.addWidget(soon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
