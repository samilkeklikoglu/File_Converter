"""
ui/drop_zone.py — Drag-and-Drop File Input Widget

Accepts any file type via drag-and-drop or click-to-browse.
Type detection and filtering are handled by the parent panel (SmartPanel / file_detector).
"""

from ui import icons as qta
from pathlib import Path
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QHBoxLayout, QFileDialog
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QDragLeaveEvent, QMouseEvent


def extract_local_paths(urls) -> list[str]:
    """Return existing local file and directory paths from dropped URLs."""
    paths: list[str] = []
    for url in urls:
        local_path = url.toLocalFile()
        if not local_path:
            continue
        path = Path(local_path)
        if path.is_file() or path.is_dir():
            paths.append(str(path))
    return paths


class DropZone(QWidget):
    """
    A drag-and-drop target widget that accepts files of any type.

    File type validation is delegated to the parent panel; this widget
    only handles the drop event and emits the resulting file paths.

    Signals:
        files_dropped(list[str]): Emitted with the list of dropped file paths.
    """

    files_dropped = Signal(list)

    _BASE_STYLE = (
        "background-color: {bg};"
        "border: 2px dashed {border};"
        "border-radius: 16px;"
    )

    _STATES = {
        "normal": {"bg": "#10192b", "border": "#34425e"},
        "hover":  {"bg": "#14213a", "border": "#6f91ff"},
        "reject": {"bg": "#24151c", "border": "#f87171"},
    }

    # Transparent style applied once to all child labels so parent
    # stylesheet changes never cascade into them.
    _CHILD_TRANSPARENT = (
        "background: transparent; border: none;"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(260)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to select files or folders")
        self._build_ui()
        self._apply_state("normal")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(9)
        layout.setContentsMargins(40, 34, 40, 34)

        # Icon container — has its own objectName so the parent
        # stylesheet never touches it.
        self.icon_container = QWidget()
        self.icon_container.setObjectName("dropZoneIconContainer")
        self.icon_container.setFixedSize(72, 72)
        self.icon_container.setStyleSheet(
            "QWidget#dropZoneIconContainer {"
            "  background-color: #1b2a49;"
            "  border-radius: 22px;"
            "  border: 1px solid #3b5483;"
            "}"
        )
        icon_inner = QVBoxLayout(self.icon_container)
        icon_inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_inner.setContentsMargins(0, 0, 0, 0)

        self.icon_label = QLabel()
        self.icon_label.setObjectName("dropZoneIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet(self._CHILD_TRANSPARENT)
        self.icon_label.setPixmap(
            qta.icon("fa5s.file-import", color="#8ca5ff").pixmap(30, 30)
        )
        icon_inner.addWidget(self.icon_label)

        # Text content
        self.main_label = QLabel("Drop your files here")
        self.main_label.setObjectName("dropZoneMainLabel")
        self.main_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_label.setStyleSheet(
            "font-size: 19px; font-weight: 700; color: #f4f7ff;"
            "background: transparent; border: none;"
        )

        self.sub_label = QLabel("Click this area to browse, or drop a folder")
        self.sub_label.setObjectName("dropZoneSubLabel")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet(
            "font-size: 12px; color: #94a3bb; background: transparent; border: none;"
        )

        # Format pills row
        pills_row = QHBoxLayout()
        pills_row.setSpacing(6)
        pills_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for i, (fmt, color) in enumerate([
            ("JPG", "#9db1d4"), ("PNG", "#9db1d4"), ("PDF", "#ff9b9b"),
            ("DOCX", "#8eb7ff"), ("WEBP", "#9db1d4"),
        ]):
            pill = QLabel(fmt)
            pill.setObjectName(f"dropZonePill_{i}")
            pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pill.setFixedHeight(22)
            pill.setStyleSheet(
                f"color: {color}; background-color: transparent;"
                f"border: 1px solid #34425e; border-radius: 6px;"
                f"padding: 3px 9px; font-size: 10px; font-weight: 700;"
                f"letter-spacing: 0.5px;"
            )
            pills_row.addWidget(pill)

        layout.addWidget(self.icon_container, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(8)
        layout.addWidget(self.main_label)
        layout.addWidget(self.sub_label)
        layout.addSpacing(10)
        layout.addLayout(pills_row)

    # ── Click-to-Browse ───────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        """Opens a file dialog when the drop zone is clicked."""
        if event.button() == Qt.MouseButton.LeftButton:
            paths, _ = QFileDialog.getOpenFileNames(
                self,
            "Select Files",
                "",
            "Supported Files (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif "
                "*.docx *.doc *.pdf);;"
            "All Files (*.*)"
            )
            if paths:
                self.files_dropped.emit(paths)
        super().mousePressEvent(event)

    # ── Drag-and-Drop Events ──────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if extract_local_paths(urls):
                event.acceptProposedAction()
                self._set_hover_style()
            else:
                event.ignore()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if (
            event.mimeData().hasUrls()
            and extract_local_paths(event.mimeData().urls())
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self._set_normal_style()

    def dropEvent(self, event: QDropEvent):
        self._set_normal_style()

        urls = event.mimeData().urls()
        paths = extract_local_paths(urls)

        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _apply_state(self, state: str):
        """Apply a visual state without touching child widget styles."""
        colors = self._STATES[state]
        self.setStyleSheet(
            f"QWidget#dropZone {{ {self._BASE_STYLE.format(**colors)} }}"
        )

    def _set_normal_style(self):
        self._apply_state("normal")

    def _set_hover_style(self):
        self._apply_state("hover")

    def _set_reject_style(self):
        self._apply_state("reject")
