"""Application entry point for FileConverter."""

import sys

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow

APP_VERSION = "2.0.0"


# Component-specific layout stays with each widget; shared controls live here.
DARK_THEME = """
QMainWindow, QWidget {
    background-color: #0b1020;
    color: #eef2ff;
    font-family: "Segoe UI Variable", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}
QLabel, QStackedWidget {
    background-color: transparent;
    border: none;
}
QToolTip {
    background-color: #1b253b; color: #f8fafc; border: 1px solid #34415d;
    border-radius: 6px; padding: 6px 9px;
}
QPushButton {
    min-height: 38px; padding: 0 16px; border: 1px solid #2a3650;
    border-radius: 9px; background-color: #162036; color: #d7deed;
    font-size: 12px; font-weight: 600;
}
QPushButton:hover { background-color: #1c2943; border-color: #526483; color: #ffffff; }
QPushButton:pressed { background-color: #111a2d; }
QPushButton:focus { border-color: #7092ff; }
QPushButton:disabled { background-color: #11182a; border-color: #1c263a; color: #56627a; }
QPushButton#primaryBtn {
    min-height: 42px; padding: 0 20px; border: 1px solid #7792ff;
    border-radius: 10px; background-color: #5b7cfa; color: #ffffff;
    font-size: 13px; font-weight: 700;
}
QPushButton#primaryBtn:hover { background-color: #6b8aff; border-color: #9aadff; }
QPushButton#primaryBtn:pressed { background-color: #4b69df; }
QPushButton#primaryBtn:disabled { background-color: #263354; border-color: #33415f; color: #72809a; }
QPushButton#successBtn {
    min-height: 42px; border: 1px solid #2dd4a8; border-radius: 10px;
    background-color: #159a7b; color: #ffffff; font-size: 13px; font-weight: 700;
}
QPushButton#successBtn:hover { background-color: #18ad8a; border-color: #5ee8c2; }
QProgressBar {
    min-height: 14px; max-height: 14px; border: none; border-radius: 7px;
    background-color: #202a40; color: transparent; text-align: center;
}
QProgressBar::chunk { border-radius: 7px; background-color: #5b7cfa; }
QListWidget#fileList {
    padding: 5px; border: 1px solid #26334c; border-radius: 11px;
    background-color: #0f1729; outline: none;
}
QListWidget#fileList::item { margin: 3px; border: 1px solid transparent; border-radius: 8px; }
QListWidget#fileList::item:hover { background-color: #172238; border-color: #283852; }
QListWidget#fileList::item:selected { background-color: #1c2b49; border-color: #3f5f9a; }
QComboBox, QLineEdit {
    min-height: 38px; padding: 0 11px; border: 1px solid #2a3650;
    border-radius: 8px; background-color: #0f1729; color: #e2e8f0;
    selection-background-color: #4f6ed7;
}
QComboBox:hover, QLineEdit:hover { border-color: #526483; }
QComboBox:focus, QLineEdit:focus { border-color: #7092ff; background-color: #111c31; }
QLineEdit::placeholder { color: #64728c; }
QComboBox::drop-down { width: 26px; border: none; }
QComboBox::down-arrow {
    width: 0; height: 0; margin-right: 8px; border-left: 4px solid transparent;
    border-right: 4px solid transparent; border-top: 5px solid #91a0ba;
}
QComboBox QAbstractItemView {
    padding: 4px; border: 1px solid #34415d; border-radius: 8px;
    background-color: #131d31; color: #e2e8f0;
    selection-background-color: #294273; selection-color: #ffffff; outline: none;
}
QLabel#titleLabel { color: #f8fafc; font-size: 20px; font-weight: 700; }
QLabel#subtitleLabel { color: #93a0b8; font-size: 12px; }
QLabel#sectionLabel { color: #9aa8c0; font-size: 11px; font-weight: 700; }
QLabel#eyebrowLabel { color: #7f9cff; font-size: 11px; font-weight: 700; }
QSlider::groove:horizontal { height: 4px; border-radius: 2px; background-color: #28344b; }
QSlider::sub-page:horizontal { border-radius: 2px; background-color: #5b7cfa; }
QSlider::handle:horizontal {
    width: 16px; height: 16px; margin: -6px 0; border: 2px solid #b6c4ff;
    border-radius: 8px; background-color: #5b7cfa;
}
QScrollBar:vertical { width: 8px; margin: 3px 1px; border: none; background: transparent; }
QScrollBar::handle:vertical { min-height: 28px; border-radius: 4px; background-color: #34415b; }
QScrollBar::handle:vertical:hover { background-color: #526483; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QMessageBox { background-color: #111a2c; }
QMessageBox QLabel { min-width: 320px; color: #e2e8f0; }
"""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FileConverter")
    app.setApplicationDisplayName("FileConverter")
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0b1020"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#eef2ff"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#0f1729"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#162036"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#eef2ff"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#162036"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#eef2ff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#5b7cfa"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
