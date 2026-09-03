"""
ui/progress_widget.py — Conversion Progress Widget

Displays real-time progress feedback during a file conversion operation,
including a progress bar, status label, and post-completion action buttons.
"""

import subprocess
import sys
from pathlib import Path

from ui import icons as qta
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal


class ProgressWidget(QWidget):
    """
    Widget for displaying conversion progress and completion state.

    States:
        idle    : Not yet started (default after reset).
        running : Conversion in progress.
        done    : Completed successfully; "Open Folder" button is enabled.
        error   : An error occurred during conversion.

    Signals:
        clear_requested:  Emitted when the user clicks the Clear button.
        cancel_requested: Emitted when the user clicks the Cancel button.
    """

    clear_requested  = Signal()
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._output_path: str | None = None
        self._build_ui()
        self.reset()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Card container
        card = QWidget()
        card.setObjectName("progressCard")
        card.setStyleSheet(
            "QWidget#progressCard {"
            "  background-color: #10192b;"
            "  border: 1px solid #26344d;"
            "  border-radius: 14px;"
            "}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 19, 20, 19)
        card_layout.setSpacing(13)

        # Status row
        status_row = QHBoxLayout()
        status_row.setSpacing(10)

        self.status_icon = QLabel()
        self.status_icon.setFixedSize(22, 22)
        self.status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_icon.setStyleSheet("background: transparent; border: none;")
        self.status_icon.setPixmap(
            qta.icon("fa5s.circle-notch", color="#65738d").pixmap(16, 16)
        )

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(
            "color: #a6b2c7; font-size: 12px; font-weight: 600;"
            "background: transparent; border: none;"
        )

        self.progress_value = QLabel("0%")
        self.progress_value.setFixedWidth(42)
        self.progress_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.progress_value.setStyleSheet(
            "color: #8da5ff; font-size: 12px; font-weight: 700; background: transparent; border: none;"
        )

        status_row.addWidget(self.status_icon)
        status_row.addWidget(self.status_label, stretch=1)
        status_row.addWidget(self.progress_value)
        card_layout.addLayout(status_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(14)
        card_layout.addWidget(self.progress_bar)

        self.output_label = QLabel()
        self.output_label.setWordWrap(True)
        self.output_label.setStyleSheet(
            "color: #8290a8; font-size: 11px; background: transparent; border: none;"
        )
        self.output_label.setVisible(False)
        card_layout.addWidget(self.output_label)

        layout.addWidget(card)

        # Action buttons row (outside card)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.cancel_btn = QPushButton("Cancel operation")
        self.cancel_btn.setIcon(qta.icon("fa5s.stop-circle", color="#ef4444"))
        self.cancel_btn.setStyleSheet(
            "QPushButton { background-color: #25171d; color: #f59898; border: 1px solid #573037;"
            "border-radius: 9px; font-weight: 600; font-size: 12px; padding: 0 18px; }"
            "QPushButton:hover { background-color: #342027; border-color: #f87171; color: #ffc0c0; }"
        )
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._on_cancel)

        self.open_btn = QPushButton("Show output in folder")
        self.open_btn.setObjectName("successBtn")
        self.open_btn.setIcon(qta.icon("fa5s.folder-open", color="#ffffff"))
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_output_folder)

        self.clear_btn = QPushButton("New operation")
        self.clear_btn.setIcon(qta.icon("fa5s.redo", color="#a8b5cb"))
        self.clear_btn.setEnabled(False)
        self.clear_btn.clicked.connect(self._on_clear)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.open_btn, stretch=1)
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)

    # ── Public API ────────────────────────────────────────────────────────────

    def reset(self):
        """Resets the widget to its initial idle state."""
        self._output_path = None
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_value.setText("0%")
        self.output_label.clear()
        self.output_label.setVisible(False)
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet(
            "color: #a6b2c7; font-size: 12px; font-weight: 600;"
            "background: transparent; border: none;"
        )
        self.status_icon.setPixmap(
            qta.icon("fa5s.circle-notch", color="#65738d").pixmap(16, 16)
        )
        self.open_btn.setEnabled(False)
        self.open_btn.setVisible(True)
        self.clear_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)

    def start(self, cancellable: bool = True):
        """Prepare the widget for a running conversion."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_value.setText("0%")
        self.output_label.clear()
        self.output_label.setVisible(False)
        self.open_btn.setEnabled(False)
        self.open_btn.setVisible(False)
        self.clear_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setVisible(cancellable)
        self.set_status("Starting...", color="#7070c0",
                        icon_name="fa5s.circle-notch", icon_color="#6c63ff")

    def start_indeterminate(self, status: str, cancellable: bool = True):
        """Show an activity indicator when total work cannot be calculated."""
        self.start(cancellable=cancellable)
        self.progress_bar.setRange(0, 0)
        self.progress_value.setText("…")
        self.set_status(status, color="#a6b2c7",
                        icon_name="fa5s.search", icon_color="#8da5ff")

    def set_progress(self, value: int):
        """Updates the progress bar value (0–100)."""
        safe_value = max(0, min(100, value))
        if self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(safe_value)
        self.progress_value.setText(f"{safe_value}%")

    def set_status(self, text: str, color: str = "#9090c8",
                   icon_name: str = "fa5s.sync-alt", icon_color: str = "#6c63ff"):
        """Updates the status label text, color, and icon."""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: 600;"
            "background: transparent; border: none;"
        )
        self.status_icon.setPixmap(
            qta.icon(icon_name, color=icon_color).pixmap(16, 16)
        )

    def set_finished(self, output_path: str):
        """
        Marks the conversion as successfully completed.

        Args:
            output_path: Full path to the generated output file or directory.
        """
        self._output_path = output_path
        self.set_progress(100)
        output = Path(output_path)
        self.output_label.setText(f"Output: {output.name}")
        self.output_label.setVisible(True)
        self.set_status("Conversion completed successfully", color="#63ddb9",
                        icon_name="fa5s.check-circle", icon_color="#48d6b0")
        self.cancel_btn.setVisible(False)
        self.open_btn.setVisible(True)
        self.open_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)

    def set_error(self, message: str):
        """Marks the conversion as failed and displays the error message."""
        self.set_status(f"Error: {message}", color="#f87171",
                        icon_name="fa5s.times-circle", icon_color="#f87171")
        self.set_progress(0)
        self.cancel_btn.setVisible(False)
        self.clear_btn.setEnabled(True)

    def set_cancelled(self):
        """Marks the conversion as cancelled by the user."""
        self.set_status("Operation cancelled.", color="#c0a030",
                        icon_name="fa5s.ban", icon_color="#c0a030")
        self.set_progress(0)
        self.cancel_btn.setVisible(False)
        self.clear_btn.setEnabled(True)

    # ── Private Methods ───────────────────────────────────────────────────────

    def _open_output_folder(self):
        if not self._output_path:
            return

        path = Path(self._output_path)

        if path.is_dir():
            folder = path
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(folder)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        else:
            folder = path.parent
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", str(path)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])

    def _on_cancel(self):
        self.cancel_btn.setEnabled(False)
        self.cancel_requested.emit()

    def _on_clear(self):
        self.reset()
        self.clear_requested.emit()
