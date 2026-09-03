"""
ui/main_window.py — Main Application Window

Hosts the SmartPanel as the sole central widget.
The panel manages its own internal scene transitions (empty → actions → progress).
"""

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow, QMessageBox, QWidget, QVBoxLayout
from PySide6.QtGui import QCloseEvent, QIcon

import qtawesome as qta
from ui.panels.smart_panel import SmartPanel


def _load_app_icon() -> QIcon:
    """Load the bundled app icon, with a QtAwesome fallback for source runs."""
    bundle_root = Path(
        getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])
    )
    icon_path = bundle_root / "assets" / "fileconverter.ico"
    if icon_path.is_file():
        return QIcon(str(icon_path))
    return qta.icon("fa5.clone", color="#6c63ff")


class MainWindow(QMainWindow):
    """
    The application's top-level window.

    Layout:
        QMainWindow
          └── central_widget (QWidget)
                └── SmartPanel  (fills the entire content area)
    """

    def __init__(self):
        super().__init__()
        self._force_close = False
        self._setup_window()
        self._build_ui()

    def _setup_window(self):
        self.setWindowTitle("FileConverter — Smart File Converter")
        self.setWindowIcon(_load_app_icon())
        self.setMinimumSize(940, 640)
        self.resize(1120, 760)

        screen = self.screen().availableGeometry()
        x = (screen.width()  - self.width())  // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.smart_panel = SmartPanel()
        layout.addWidget(self.smart_panel)

    def closeEvent(self, event: QCloseEvent):
        """Keep the process alive until active conversion cleanup has finished."""
        if self._force_close or not self.smart_panel.has_running_operation():
            event.accept()
            return

        answer = QMessageBox.question(
            self,
            "Conversion in progress",
            "Cancel the current operation and close the application?\n\n"
            "Temporary files created by this operation will be removed safely.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            event.ignore()
            return

        self.setEnabled(False)
        self.setWindowTitle("FileConverter — Stopping safely...")
        if self.smart_panel.request_shutdown(self._finish_deferred_close):
            event.ignore()
        else:
            event.accept()

    def _finish_deferred_close(self):
        """Close on the UI event loop after the worker has fully stopped."""
        self._force_close = True
        QTimer.singleShot(0, self.close)
