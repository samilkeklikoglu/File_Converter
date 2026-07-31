"""
main.py — Uygulamanın giriş noktası

ÖĞRENME NOTU:
  Her PySide6 uygulaması şu üç adımla başlar:
  1. QApplication oluştur  → Qt'nin kendisi (event loop, sistem kaynakları)
  2. Bir pencere (QWidget/QMainWindow) oluştur ve göster
  3. app.exec() ile event loop'u başlat → kullanıcı eylemi bekle
  
  Event loop: "Kullanıcı bir şey yaparsa (tıklama, tuş, vb.) beni çağır,
               yoksa bekle" döngüsüdür. app.exec() bunu yönetir.
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow


# ── Global Qt Style Sheet (QSS) ──────────────────────────────────────────────
# QSS, CSS'e çok benzer. Koyu tema renklerimizi burada tanımlıyoruz.
# Widget adı (QPushButton), sınıf (.success) veya durum (:hover) seçilebilir.
DARK_THEME = """
/* ── Genel Uygulama Renkleri ── */
QMainWindow, QWidget {
    background-color: #0f0f1a;
    color: #e0e0f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

/* ── Sol Kenar Çubuğu ── */
QListWidget {
    background-color: #13131f;
    border: none;
    border-right: 1px solid #2a2a40;
    outline: none;
}
QListWidget::item {
    padding: 14px 20px;
    border-radius: 8px;
    margin: 3px 8px;
    color: #9090b0;
}
QListWidget::item:hover {
    background-color: #1e1e30;
    color: #c0c0e0;
}
QListWidget::item:selected {
    background-color: #1a1a35;
    color: #ffffff;
    border-left: 3px solid #7c6af7;
}

/* ── Butonlar ── */
QPushButton {
    background-color: #2a2a45;
    color: #c8c8e8;
    border: 1px solid #3a3a55;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #35356a;
    border-color: #7c6af7;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #7c6af7;
}
QPushButton:disabled {
    background-color: #1a1a28;
    color: #404060;
    border-color: #252535;
}

/* Birincil aksiyon butonu (dönüştür, birleştir, vb.) */
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #7c6af7, stop:1 #5b9cf7);
    border: none;
    color: #ffffff;
    font-size: 14px;
    padding: 12px 30px;
    border-radius: 10px;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #9080ff, stop:1 #70aaff);
}
QPushButton#primaryBtn:disabled {
    background: #2a2a40;
    color: #555570;
}

/* Başarı butonu (klasörü aç) */
QPushButton#successBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #2ecc71, stop:1 #27ae60);
    border: none;
    color: #ffffff;
    font-size: 13px;
    padding: 10px 24px;
    border-radius: 8px;
}
QPushButton#successBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #3de882, stop:1 #32cc73);
}

/* ── Progress Bar ── */
QProgressBar {
    background-color: #1e1e30;
    border: 1px solid #2a2a45;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    height: 16px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #7c6af7, stop:1 #5b9cf7);
    border-radius: 6px;
}

/* ── Liste Kutuları (dosya listesi) ── */
QListWidget#fileList {
    background-color: #13131f;
    border: 1px solid #2a2a40;
    border-radius: 8px;
    padding: 4px;
}
QListWidget#fileList::item {
    padding: 8px 12px;
    margin: 2px 4px;
    border-radius: 5px;
    color: #c0c0e0;
    border: none;
}
QListWidget#fileList::item:hover {
    background-color: #1e1e35;
}
QListWidget#fileList::item:selected {
    background-color: #252545;
    color: #ffffff;
    border: none;
    border-left: none;
}

/* ── Açılır Menüler ── */
QComboBox {
    background-color: #1e1e30;
    border: 1px solid #3a3a55;
    border-radius: 6px;
    padding: 6px 12px;
    color: #c8c8e8;
    min-width: 120px;
}
QComboBox:hover {
    border-color: #7c6af7;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #1e1e30;
    border: 1px solid #3a3a55;
    selection-background-color: #35356a;
}

/* ── Kaydırma Çubukları ── */
QScrollBar:vertical {
    background: #13131f;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #3a3a60;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* ── Etiketler ── */
QLabel#titleLabel {
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
}
QLabel#subtitleLabel {
    font-size: 12px;
    color: #6060a0;
}
QLabel#sectionLabel {
    font-size: 11px;
    font-weight: 600;
    color: #7c6af7;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* ── Ayırıcı çizgi ── */
QFrame[frameShape="4"],  /* HLine */
QFrame[frameShape="5"] { /* VLine */
    color: #2a2a40;
    background-color: #2a2a40;
}
"""


def main():
    # sys.argv: komut satırı argümanlarını Qt'ye iletir (gerekli ama burada boş)
    app = QApplication(sys.argv)
    app.setApplicationName("FileConverter")
    app.setApplicationDisplayName("FileConverter")
    
    # Tüm uygulamaya global stil uygula
    app.setStyleSheet(DARK_THEME)
    
    # Ana pencereyi oluştur ve göster
    window = MainWindow()
    window.show()
    
    # Event loop'u başlat; kullanıcı pencereyi kapatınca 0 döner
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
