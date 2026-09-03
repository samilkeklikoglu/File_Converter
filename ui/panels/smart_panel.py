"""
ui/panels/smart_panel.py — Single-Flow Conversion Panel

Detects dropped file types automatically and presents the appropriate
conversion actions dynamically.

Scenes:
    SCENE_EMPTY    → Large centered drop zone; waiting for input.
    SCENE_ACTIONS  → Files detected; action buttons displayed.
    SCENE_PROGRESS → Conversion running, completed, or failed.
"""

import sys
from pathlib import Path

import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QComboBox, QFrame, QStackedWidget, QSizePolicy, QLineEdit, QSlider,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QDragEnterEvent, QDragMoveEvent, QDropEvent

from ui.drop_zone import DropZone, extract_local_paths
from ui.progress_widget import ProgressWidget
from core.worker import ConversionWorker, PathScanWorker
from core import image_to_pdf as img_converter
from core import word_to_pdf as word_converter
from core import pdf_merge as pdf_converter
from core import pdf_split as pdf_splitter
from core import image_convert as img_converter_fmt
from core import pdf_to_image as pdf_to_image_converter
from core import pdf_to_word as pdf_to_word_converter
from core.file_detector import detect_type, expand_supported_paths, get_type_label

SCENE_EMPTY    = 0
SCENE_ACTIONS  = 1
SCENE_PROGRESS = 2


class FileListWidget(QListWidget):
    """
    Custom QListWidget that accepts OS file drops (external)
    while preserving standard internal drag and drop moves.
    """
    files_dropped = Signal(list)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if (
            event.mimeData().hasUrls()
            and extract_local_paths(event.mimeData().urls())
        ):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent):
        if (
            event.mimeData().hasUrls()
            and extract_local_paths(event.mimeData().urls())
        ):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            paths = extract_local_paths(event.mimeData().urls())
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
        else:
            super().dropEvent(event)


class FileListItemWidget(QWidget):
    """
    Custom widget displayed inside the FileListWidget.
    Displays file type icon, name, formatted size, and a deletion button.
    """
    remove_requested = Signal(str)

    def __init__(self, path: str, file_type: str, parent=None):
        super().__init__(parent)
        self.path = path
        # Prevent global QWidget background from making this opaque
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setStyleSheet("background: transparent;")
        self._build_ui(file_type)

    def _build_ui(self, file_type: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 10, 8)
        layout.setSpacing(10)

        # Icon
        icon_map = {
            'image': ('fa5s.image', '#8da5ff'),
            'word':  ('fa5s.file-word', '#79adff'),
            'pdf':   ('fa5s.file-pdf', '#ff9696'),
        }
        icon_name, icon_color = icon_map.get(file_type, ('fa5s.file', '#9090c0'))

        icon_lbl = QLabel()
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        icon_lbl.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(16, 16))

        # Name
        p = Path(self.path)
        name_lbl = QLabel(p.name)
        name_lbl.setStyleSheet("color: #e7edf8; font-size: 12px; font-weight: 600; background: transparent; border: none;")
        name_lbl.setToolTip(str(p))

        # Size
        try:
            size_bytes = p.stat().st_size
            if size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        except Exception:
            size_str = ""

        size_lbl = QLabel(size_str)
        size_lbl.setStyleSheet("color: #75839c; font-size: 11px; background: transparent; border: none;")

        # Delete Button
        self.del_btn = QPushButton()
        self.del_btn.setFixedSize(26, 26)
        self.del_btn.setIcon(qta.icon("fa5s.times", color="#8b98ae"))
        self.del_btn.setToolTip(f"{p.name} dosyasını listeden kaldır")
        self.del_btn.setStyleSheet(
            "QPushButton { min-height: 0; padding: 0; background: transparent; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #382027; }"
        )
        self.del_btn.clicked.connect(lambda: self.remove_requested.emit(self.path))

        layout.addWidget(icon_lbl)
        layout.addWidget(name_lbl, stretch=1)
        layout.addWidget(size_lbl)
        layout.addWidget(self.del_btn)


class SmartPanel(QWidget):
    """
    Single-flow conversion panel.

    Flow:
        1. User drops or selects files.
        2. file_detector.detect_type() identifies the file type.
        3. Appropriate action buttons are displayed.
        4. User triggers an action → ConversionWorker starts.
        5. ProgressWidget reports progress.
        6. "Clear" returns to SCENE_EMPTY.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ConversionWorker | None = None
        self._scan_worker: PathScanWorker | None = None
        self._scan_append = False
        self._current_paths: list[str] = []
        self._pdf_output_path: str | None = None

        self._build_ui()
        self._connect_signals()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        self.stack = QStackedWidget()
        root.addWidget(self.stack, stretch=1)

        self.stack.addWidget(self._build_empty_scene())    # 0 — SCENE_EMPTY
        self.stack.addWidget(self._build_actions_scene())  # 1 — SCENE_ACTIONS
        self.stack.addWidget(self._build_progress_scene()) # 2 — SCENE_PROGRESS

        self.stack.setCurrentIndex(SCENE_EMPTY)

    def _build_header(self) -> QWidget:
        outer = QWidget()
        outer.setObjectName("appHeader")
        outer.setFixedHeight(88)
        outer.setStyleSheet(
            "QWidget#appHeader { background-color: #0d1425; border-bottom: 1px solid #202c43; }"
        )
        layout = QHBoxLayout(outer)
        layout.setContentsMargins(32, 0, 32, 0)
        layout.setSpacing(14)

        icon_badge = QWidget()
        icon_badge.setObjectName("brandBadge")
        icon_badge.setFixedSize(46, 46)
        icon_badge.setStyleSheet(
            "QWidget#brandBadge { background-color: #5b7cfa; border: 1px solid #8da5ff;"
            "border-radius: 13px; }"
        )
        badge_layout = QVBoxLayout(icon_badge)
        badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_icon = QLabel()
        badge_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_icon.setStyleSheet("background: transparent; border: none;")
        badge_icon.setPixmap(
            qta.icon("fa5s.exchange-alt", color="#ffffff").pixmap(21, 21)
        )
        badge_layout.addWidget(badge_icon)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        title = QLabel("FileConverter")
        title.setObjectName("titleLabel")
        sub = QLabel("Dosyalarınız için hızlı ve güvenli dönüşüm merkezi")
        sub.setObjectName("subtitleLabel")

        title_col.addWidget(title)
        title_col.addWidget(sub)

        layout.addWidget(icon_badge)
        layout.addLayout(title_col)
        layout.addStretch()

        privacy = QWidget()
        privacy.setObjectName("privacyBadge")
        privacy.setStyleSheet(
            "QWidget#privacyBadge { background-color: #10231f; border: 1px solid #245047;"
            "border-radius: 10px; }"
        )
        privacy_layout = QHBoxLayout(privacy)
        privacy_layout.setContentsMargins(12, 7, 12, 7)
        privacy_layout.setSpacing(8)
        privacy_icon = QLabel()
        privacy_icon.setStyleSheet("background: transparent; border: none;")
        privacy_icon.setPixmap(qta.icon("fa5s.shield-alt", color="#48d6b0").pixmap(14, 14))
        privacy_text = QLabel("Dosyalar cihazınızda işlenir")
        privacy_text.setStyleSheet(
            "background: transparent; border: none; color: #9fe8d5; font-size: 11px; font-weight: 600;"
        )
        privacy_layout.addWidget(privacy_icon)
        privacy_layout.addWidget(privacy_text)
        layout.addWidget(privacy)

        return outer

    # ── Scene 0: Empty / Waiting ───────────────────────────────────────────────

    def _build_empty_scene(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(44, 30, 44, 26)
        layout.setSpacing(16)

        intro = QVBoxLayout()
        intro.setSpacing(6)
        eyebrow = QLabel("1  ·  DOSYALARINIZI EKLEYİN")
        eyebrow.setObjectName("eyebrowLabel")
        heading = QLabel("Ne dönüştürmek istiyorsunuz?")
        heading.setObjectName("titleLabel")
        heading.setStyleSheet("font-size: 26px; font-weight: 700; color: #f8fafc;")
        description = QLabel(
            "Dosya türünü otomatik tanırız ve yalnızca kullanılabilir dönüşüm seçeneklerini gösteririz."
        )
        description.setObjectName("subtitleLabel")
        description.setWordWrap(True)
        intro.addWidget(eyebrow)
        intro.addWidget(heading)
        intro.addWidget(description)
        layout.addLayout(intro)

        self.drop_zone = DropZone()
        self.drop_zone.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.drop_zone)

        browse_btn = QPushButton("Bilgisayardan dosya seç")
        browse_btn.setObjectName("primaryBtn")
        browse_btn.setIcon(qta.icon("fa5s.folder-open", color="#ffffff"))
        browse_btn.setFixedWidth(220)
        browse_btn.setToolTip("Bir veya birden fazla dosya seçin")
        browse_btn.clicked.connect(self._open_file_dialog)

        btn_wrapper = QHBoxLayout()
        btn_wrapper.addStretch()
        btn_wrapper.addWidget(browse_btn)
        btn_wrapper.addStretch()
        layout.addLayout(btn_wrapper)

        support = QLabel(
            "PDF birleştirme ve bölme   •   Resim ↔ PDF   •   PDF → Word   •   Word → PDF"
        )
        support.setAlignment(Qt.AlignmentFlag.AlignCenter)
        support.setStyleSheet("color: #73819a; font-size: 11px;")
        layout.addWidget(support)

        return page

    def _build_actions_scene(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 24, 36, 28)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        step_label = QLabel("2  ·  İŞLEMİ SEÇİN")
        step_label.setObjectName("eyebrowLabel")
        self.reset_btn = QPushButton("Başa dön")
        self.reset_btn.setIcon(qta.icon("fa5s.arrow-left", color="#a8b5cb"))
        self.reset_btn.setFixedWidth(112)
        self.reset_btn.setToolTip("Seçili dosyaları temizleyip başlangıca dön")
        self.reset_btn.clicked.connect(self._reset_to_empty)
        top_row.addWidget(step_label)
        top_row.addStretch()
        top_row.addWidget(self.reset_btn)
        layout.addLayout(top_row)

        detect_card = QWidget()
        detect_card.setObjectName("detectCard")
        detect_card.setStyleSheet(
            "QWidget#detectCard { background-color: #121d31; border: 1px solid #2a3a57;"
            "border-radius: 12px; }"
        )
        detect_card_layout = QHBoxLayout(detect_card)
        detect_card_layout.setContentsMargins(16, 13, 16, 13)
        detect_card_layout.setSpacing(13)

        self.detect_icon = QLabel()
        self.detect_icon.setFixedSize(38, 38)
        self.detect_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detect_icon.setStyleSheet("background: transparent; border: none;")

        detect_text_col = QVBoxLayout()
        detect_text_col.setSpacing(2)
        self.detect_title = QLabel()
        self.detect_title.setStyleSheet(
            "color: #f1f5f9; font-size: 14px; font-weight: 700; background: transparent; border: none;"
        )

        self.detect_sub = QLabel()
        self.detect_sub.setStyleSheet(
            "color: #8f9db5; font-size: 11px; background: transparent; border: none;"
        )
        self.detect_sub.setWordWrap(True)
        detect_text_col.addWidget(self.detect_title)
        detect_text_col.addWidget(self.detect_sub)

        detect_card_layout.addWidget(self.detect_icon)
        detect_card_layout.addLayout(detect_text_col, stretch=1)
        layout.addWidget(detect_card)

        workspace = QHBoxLayout()
        workspace.setSpacing(14)

        files_panel = QWidget()
        files_panel.setObjectName("workspacePanel")
        files_panel.setStyleSheet(
            "QWidget#workspacePanel { background-color: #10192b; border: 1px solid #26344d;"
            "border-radius: 14px; }"
        )
        files_layout = QVBoxLayout(files_panel)
        files_layout.setContentsMargins(16, 16, 16, 16)
        files_layout.setSpacing(11)

        list_header = QHBoxLayout()
        files_lbl = QLabel("Seçilen dosyalar")
        files_lbl.setObjectName("sectionLabel")
        self.file_count_label = QLabel()
        self.file_count_label.setStyleSheet("color: #72809a; font-size: 11px;")
        self.add_more_btn = QPushButton("Dosya ekle")
        self.add_more_btn.setIcon(qta.icon("fa5s.plus", color="#b7c5de"))
        self.add_more_btn.setFixedWidth(112)
        self.add_more_btn.setToolTip("Listeye aynı türde başka dosyalar ekleyin")
        self.add_more_btn.clicked.connect(self._open_file_dialog_addmore)
        list_header.addWidget(files_lbl)
        list_header.addWidget(self.file_count_label)
        list_header.addStretch()
        list_header.addWidget(self.add_more_btn)
        files_layout.addLayout(list_header)

        self.file_list = FileListWidget()
        self.file_list.setObjectName("fileList")
        self.file_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        self.file_list.setDragEnabled(True)
        self.file_list.setAcceptDrops(True)
        self.file_list.setDropIndicatorShown(True)
        self.file_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.file_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.file_list.setToolTip("Birleştirme sırasını değiştirmek için dosyaları sürükleyin")
        files_layout.addWidget(self.file_list, stretch=1)

        order_hint = QLabel("PDF birleştirirken listedeki sıra kullanılır.")
        order_hint.setStyleSheet("color: #67758d; font-size: 10px;")
        order_hint.setWordWrap(True)
        files_layout.addWidget(order_hint)

        action_panel = QWidget()
        action_panel.setObjectName("actionPanel")
        action_panel.setStyleSheet(
            "QWidget#actionPanel { background-color: #10192b; border: 1px solid #26344d;"
            "border-radius: 14px; }"
        )
        action_layout = QVBoxLayout(action_panel)
        action_layout.setContentsMargins(18, 16, 18, 16)
        action_layout.setSpacing(10)

        action_lbl = QLabel("Uygun dönüşümler")
        action_lbl.setObjectName("sectionLabel")
        action_description = QLabel("Bir işlem seçin; çıktı konumunu başlamadan önce soracağız.")
        action_description.setWordWrap(True)
        action_description.setStyleSheet("color: #7e8ca5; font-size: 11px;")
        action_layout.addWidget(action_lbl)
        action_layout.addWidget(action_description)

        self.action_stack = QStackedWidget()
        self.action_stack.setMinimumHeight(310)
        action_layout.addWidget(self.action_stack, stretch=1)

        self.action_stack.addWidget(self._build_image_actions())   # 0 → image
        self.action_stack.addWidget(self._build_word_actions())    # 1 → word
        self.action_stack.addWidget(self._build_pdf_single())      # 2 → pdf (single)
        self.action_stack.addWidget(self._build_pdf_multi())       # 3 → pdf (multi)
        self.action_stack.addWidget(self._build_mixed_warning())   # 4 → mixed
        self.action_stack.addWidget(self._build_unsupported())     # 5 → unsupported

        workspace.addWidget(files_panel, stretch=4)
        workspace.addWidget(action_panel, stretch=6)
        layout.addLayout(workspace, stretch=1)

        return page

    def _make_action_card(
        self, title: str, description: str, icon_name: str, icon_color: str = "#8da5ff"
    ) -> tuple[QWidget, QVBoxLayout]:
        """Create a consistent action card and return its content layout."""
        card = QWidget()
        card.setObjectName("conversionCard")
        card.setStyleSheet(
            "QWidget#conversionCard { background-color: #131e32; border: 1px solid #293a56;"
            "border-radius: 11px; }"
        )
        content = QVBoxLayout(card)
        content.setContentsMargins(14, 13, 14, 14)
        content.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)
        icon = QLabel()
        icon.setFixedSize(30, 30)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            "background-color: #1b2a46; border: 1px solid #344d78; border-radius: 8px;"
        )
        icon.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(14, 14))
        text = QVBoxLayout()
        text.setSpacing(1)
        title_label = QLabel(title)
        title_label.setStyleSheet(
            "background: transparent; border: none; color: #edf2ff; font-size: 12px; font-weight: 700;"
        )
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setStyleSheet(
            "background: transparent; border: none; color: #7f8da6; font-size: 10px;"
        )
        text.addWidget(title_label)
        text.addWidget(description_label)
        header.addWidget(icon)
        header.addLayout(text, stretch=1)
        content.addLayout(header)
        return card, content


    def _build_image_actions(self) -> QWidget:
        w = QWidget()
        w.setObjectName("actionPage")
        w.setStyleSheet("QWidget#actionPage { background: transparent; border: none; }")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        pdf_card, pdf_layout = self._make_action_card(
            "Tek PDF oluştur", "Resimleri seçtiğiniz sırayla tek belgede birleştirir.", "fa5s.file-pdf", "#ff9696"
        )
        pdf_row = QHBoxLayout()
        pdf_row.setSpacing(8)
        page_lbl = QLabel("Sayfa boyutu")
        page_lbl.setStyleSheet("color: #9aa8c0; font-size: 11px; font-weight: 600;")

        self.img_page_combo = QComboBox()
        for size in img_converter.PAPER_SIZES_96DPI.keys():
            self.img_page_combo.addItem(size)
        self.img_page_combo.setCurrentText("A4")
        self.img_page_combo.setToolTip("PDF sayfalarının boyutu")

        self.img_to_pdf_btn = QPushButton("PDF oluştur")
        self.img_to_pdf_btn.setObjectName("primaryBtn")
        self.img_to_pdf_btn.setIcon(qta.icon("fa5s.file-pdf", color="#ffffff"))
        self.img_to_pdf_btn.clicked.connect(self._start_image_to_pdf)

        pdf_row.addWidget(page_lbl)
        pdf_row.addWidget(self.img_page_combo)
        pdf_row.addWidget(self.img_to_pdf_btn, stretch=1)
        pdf_layout.addLayout(pdf_row)
        layout.addWidget(pdf_card)

        format_card, format_layout = self._make_action_card(
            "Resim formatını değiştir", "JPG, PNG veya WEBP çıktısı üretir.", "fa5s.images"
        )
        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(8)

        self.img_fmt_combo = QComboBox()
        for fmt in ["JPG", "PNG", "WEBP"]:
            self.img_fmt_combo.addItem(fmt)
        self.img_fmt_combo.currentTextChanged.connect(self._on_img_fmt_changed)

        quality_lbl = QLabel("Kalite")
        quality_lbl.setStyleSheet("color: #9aa8c0; font-size: 11px; font-weight: 600;")

        self.img_quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.img_quality_slider.setMinimum(1)
        self.img_quality_slider.setMaximum(95)
        self.img_quality_slider.setValue(85)
        self.img_quality_slider.setMinimumWidth(70)
        self.img_quality_slider.setFixedHeight(20)

        self.img_quality_label = QLabel("85")
        self.img_quality_label.setStyleSheet("color: #b8c5da; font-size: 11px; font-weight: 700;")
        self.img_quality_label.setFixedWidth(24)
        self.img_quality_slider.valueChanged.connect(
            lambda v: self.img_quality_label.setText(str(v))
        )

        self.img_convert_fmt_btn = QPushButton("Dönüştür")
        self.img_convert_fmt_btn.setIcon(qta.icon("fa5s.exchange-alt", color="#b8c5da"))
        self.img_convert_fmt_btn.clicked.connect(self._start_image_convert)

        fmt_row.addWidget(self.img_fmt_combo)
        fmt_row.addWidget(quality_lbl)
        fmt_row.addWidget(self.img_quality_slider, stretch=1)
        fmt_row.addWidget(self.img_quality_label)
        fmt_row.addWidget(self.img_convert_fmt_btn)
        format_layout.addLayout(fmt_row)
        layout.addWidget(format_card)
        layout.addStretch()

        return w

    def _build_word_actions(self) -> QWidget:
        w = QWidget()
        w.setObjectName("actionPage")
        w.setStyleSheet("QWidget#actionPage { background: transparent; border: none; }")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        if sys.platform == "win32":
            warn_text = "Bu işlem için bilgisayarınızda Microsoft Word kurulu olmalıdır."
            warn_bg = "#132137"
            warn_fg = "#a9b8d1"
            warn_border = "#2c4265"
        else:
            warn_text = "Word → PDF dönüşümü yalnızca Windows ve macOS'ta kullanılabilir."
            warn_bg = "#28191a"
            warn_fg = "#f1a7a7"
            warn_border = "#573032"

        warn = QLabel(warn_text)
        warn.setWordWrap(True)
        warn.setStyleSheet(
            f"background:{warn_bg}; color:{warn_fg}; "
            f"border: 1px solid {warn_border};"
            "font-size:11px; padding:10px 12px; border-radius:8px; font-weight: 500;"
        )

        card, card_layout = self._make_action_card(
            "PDF belgesi oluştur", "Her Word dosyası ayrı bir PDF olarak kaydedilir.",
            "fa5s.file-pdf", "#ff9696"
        )
        card_layout.addWidget(warn)
        self.word_to_pdf_btn = QPushButton("PDF'e dönüştür")
        self.word_to_pdf_btn.setObjectName("primaryBtn")
        self.word_to_pdf_btn.setIcon(qta.icon("fa5s.file-pdf", color="#ffffff"))
        self.word_to_pdf_btn.clicked.connect(self._start_word_to_pdf)
        card_layout.addWidget(self.word_to_pdf_btn)
        layout.addWidget(card)
        layout.addStretch()

        return w

    def _build_pdf_single(self) -> QWidget:
        w = QWidget()
        w.setObjectName("actionPage")
        w.setStyleSheet("QWidget#actionPage { background: transparent; border: none; }")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(9)

        split_card, split_layout = self._make_action_card(
            "PDF'i böl", "Tüm sayfaları veya belirli aralıkları ayrı PDF'ler olarak çıkarır.",
            "fa5s.cut", "#f3c96b"
        )
        split_row = QHBoxLayout()
        split_row.setSpacing(8)

        self.pdf_split_all_btn = QPushButton("Her sayfayı ayır")
        self.pdf_split_all_btn.setIcon(qta.icon("fa5s.copy", color="#b8c5da"))
        self.pdf_split_all_btn.clicked.connect(self._start_pdf_split_all)

        self.pdf_range_input = QLineEdit()
        self.pdf_range_input.setPlaceholderText("Örn. 1-3, 5, 8-10")
        self.pdf_range_input.setToolTip("Virgülle ayırarak birden fazla sayfa veya aralık girebilirsiniz")

        self.pdf_split_range_btn = QPushButton("Aralığı ayır")
        self.pdf_split_range_btn.setIcon(qta.icon("fa5s.cut", color="#b8c5da"))
        self.pdf_split_range_btn.setFixedWidth(118)
        self.pdf_split_range_btn.clicked.connect(self._start_pdf_split_ranges)

        split_row.addWidget(self.pdf_split_all_btn)
        split_row.addWidget(self.pdf_range_input, stretch=1)
        split_row.addWidget(self.pdf_split_range_btn)
        split_layout.addLayout(split_row)
        layout.addWidget(split_card)

        image_card, image_layout = self._make_action_card(
            "Sayfaları görsele çevir", "Her PDF sayfasını ayrı bir PNG veya JPG dosyası olarak kaydeder.",
            "fa5s.images", "#8da5ff"
        )
        img_row = QHBoxLayout()
        img_row.setSpacing(8)

        self.pdf_img_fmt_combo = QComboBox()
        self.pdf_img_fmt_combo.addItems(["PNG", "JPG"])
        self.pdf_img_fmt_combo.setFixedWidth(76)

        self.pdf_img_dpi_combo = QComboBox()
        self.pdf_img_dpi_combo.addItems(["72 DPI", "150 DPI", "300 DPI", "600 DPI"])
        self.pdf_img_dpi_combo.setCurrentText("150 DPI")
        self.pdf_img_dpi_combo.setFixedWidth(96)
        self.pdf_img_dpi_combo.setToolTip("Daha yüksek DPI daha kaliteli ve daha büyük dosya üretir")

        self.pdf_to_img_btn = QPushButton("Görselleri oluştur")
        self.pdf_to_img_btn.setObjectName("primaryBtn")
        self.pdf_to_img_btn.setIcon(qta.icon("fa5s.images", color="#ffffff"))
        self.pdf_to_img_btn.clicked.connect(self._start_pdf_to_image)

        img_row.addWidget(self.pdf_img_fmt_combo)
        img_row.addWidget(self.pdf_img_dpi_combo)
        img_row.addWidget(self.pdf_to_img_btn, stretch=1)
        image_layout.addLayout(img_row)
        layout.addWidget(image_card)

        word_card, word_layout = self._make_action_card(
            "Düzenlenebilir Word belgesi oluştur", "Metin ve tabloları mümkün olduğunca DOCX düzenine aktarır.",
            "fa5s.file-word", "#79adff"
        )
        self.pdf_to_word_btn = QPushButton("Word belgesi oluştur (.docx)")
        self.pdf_to_word_btn.setIcon(qta.icon("fa5s.file-word", color="#ffffff"))
        self.pdf_to_word_btn.clicked.connect(self._start_pdf_to_word)
        word_layout.addWidget(self.pdf_to_word_btn)
        layout.addWidget(word_card)
        layout.addStretch()

        return w

    def _build_pdf_multi(self) -> QWidget:
        w = QWidget()
        w.setObjectName("actionPage")
        w.setStyleSheet("QWidget#actionPage { background: transparent; border: none; }")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        card, card_layout = self._make_action_card(
            "PDF dosyalarını birleştir",
            "Dosyalar soldaki sıraya göre tek bir PDF içinde birleştirilir.",
            "fa5s.object-group", "#ff9696"
        )
        row = QHBoxLayout()
        row.setSpacing(8)

        self.pdf_output_label = QLabel("Henüz çıktı dosyası seçilmedi")
        self.pdf_output_label.setStyleSheet(
            "color: #8391aa; font-size: 11px; border: 1px solid #2a3650;"
            "background: #0f1729; padding: 10px 12px; border-radius: 8px;"
        )
        self.pdf_output_label.setWordWrap(True)

        choose_btn = QPushButton("Çıktı seç")
        choose_btn.setIcon(qta.icon("fa5s.folder-open", color="#b8c5da"))
        choose_btn.setFixedWidth(120)
        choose_btn.clicked.connect(self._choose_pdf_output)

        self.pdf_merge_btn = QPushButton("PDF'leri birleştir")
        self.pdf_merge_btn.setObjectName("primaryBtn")
        self.pdf_merge_btn.setIcon(qta.icon("fa5s.object-group", color="#ffffff"))
        self.pdf_merge_btn.setEnabled(False)
        self.pdf_merge_btn.clicked.connect(self._start_pdf_merge)

        card_layout.addWidget(self.pdf_output_label)
        row.addWidget(choose_btn)
        row.addWidget(self.pdf_merge_btn, stretch=1)
        card_layout.addLayout(row)
        layout.addWidget(card)
        layout.addStretch()

        return w

    def _build_mixed_warning(self) -> QWidget:
        w = QWidget()
        w.setObjectName("actionPage")
        w.setStyleSheet("QWidget#actionPage { background: transparent; border: none; }")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        warn = QLabel(
            "⚠️  Aynı tipte dosyalar seçin\n"
            "Resimler, Word belgeleri ve PDF'leri ayrı ayrı ekleyip dönüştürebilirsiniz."
        )
        warn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warn.setWordWrap(True)
        warn.setStyleSheet(
            "background: #150e00; color: #907020; font-size: 12px; "
            "padding: 16px 22px; border-radius: 10px; border: 1px solid #2a2000;"
        )
        layout.addWidget(warn)

        return w

    def _build_unsupported(self) -> QWidget:
        w = QWidget()
        w.setObjectName("actionPage")
        w.setStyleSheet("QWidget#actionPage { background: transparent; border: none; }")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        warn = QLabel(
            "✗  Desteklenmeyen dosya formatı\n"
            "Kabul edilenler: JPG · PNG · WEBP · BMP · TIFF · DOCX · DOC · PDF"
        )
        warn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warn.setWordWrap(True)
        warn.setStyleSheet(
            "background: #120606; color: #904040; font-size: 12px; "
            "padding: 16px 22px; border-radius: 10px; border: 1px solid #280e0e;"
        )
        layout.addWidget(warn)

        return w

    # ── Scene 2: Progress ─────────────────────────────────────────────────────

    def _build_progress_scene(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(80, 34, 80, 34)
        layout.setSpacing(14)

        step_label = QLabel("3  ·  DÖNÜŞÜM DURUMU")
        step_label.setObjectName("eyebrowLabel")
        layout.addWidget(step_label)

        heading = QLabel("Dosyanız hazırlanıyor")
        heading.setObjectName("titleLabel")
        heading.setStyleSheet("font-size: 25px; font-weight: 700; color: #f8fafc;")
        layout.addWidget(heading)

        description = QLabel("Bu pencereyi açık tutun. İşlem tamamlandığında çıktı klasörünü doğrudan açabilirsiniz.")
        description.setObjectName("subtitleLabel")
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addSpacing(8)

        op_card = QWidget()
        op_card.setObjectName("opCard")
        op_card.setStyleSheet(
            "QWidget#opCard { background-color: #121d31; border: 1px solid #2a3a57;"
            "border-radius: 14px; }"
        )
        op_card_layout = QHBoxLayout(op_card)
        op_card_layout.setContentsMargins(18, 16, 18, 16)
        op_card_layout.setSpacing(14)

        self.progress_op_icon = QLabel()
        self.progress_op_icon.setFixedSize(40, 40)
        self.progress_op_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_op_icon.setStyleSheet(
            "background-color: #1b2a49; border-radius: 12px; border: 1px solid #3b5483;"
        )
        self.progress_op_icon.setPixmap(
            qta.icon("fa5s.sync-alt", color="#8da5ff").pixmap(19, 19)
        )

        op_text = QVBoxLayout()
        op_text.setSpacing(2)

        self.progress_op_label = QLabel()
        self.progress_op_label.setObjectName("titleLabel")
        fnt = QFont()
        fnt.setPointSize(13)
        fnt.setBold(True)
        self.progress_op_label.setFont(fnt)
        self.progress_op_label.setStyleSheet("background: transparent; border: none; color: #edf2ff;")

        self.progress_file_label = QLabel()
        self.progress_file_label.setStyleSheet(
            "color: #8190aa; font-size: 11px; background: transparent; border: none;"
        )

        op_text.addWidget(self.progress_op_label)
        op_text.addWidget(self.progress_file_label)

        op_card_layout.addWidget(self.progress_op_icon)
        op_card_layout.addLayout(op_text, stretch=1)
        layout.addWidget(op_card)

        self.progress_widget = ProgressWidget()
        layout.addWidget(self.progress_widget)

        layout.addStretch()

        return page


    # ── Signal Connections ────────────────────────────────────────────────────

    def _connect_signals(self):
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        self.progress_widget.clear_requested.connect(self._reset_to_empty)
        self.progress_widget.cancel_requested.connect(self._cancel_worker)
        self.file_list.files_dropped.connect(self._add_more_files)

    # ── File Management ───────────────────────────────────────────────────────

    def _expand_directories(self, paths: list[str]) -> list[str]:
        """Synchronous helper retained for unit tests and direct file lists."""
        return expand_supported_paths(paths)

    def _on_files_dropped(self, paths: list[str]):
        self._queue_paths(paths, append=False)

    def _open_file_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Dosya Seç",
            "",
            "Desteklenen Dosyalar (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif "
            "*.docx *.doc *.pdf);;"
            "Tüm Dosyalar (*.*)"
        )
        if paths:
            self._set_files(paths)

    def _open_file_dialog_addmore(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Dosya Ekle",
            "",
            "Desteklenen Dosyalar (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif "
            "*.docx *.doc *.pdf);;"
            "Tüm Dosyalar (*.*)"
        )
        if paths:
            self._add_more_files(paths)

    def _add_more_files(self, new_paths: list[str]):
        self._queue_paths(new_paths, append=True)

    def _queue_paths(self, paths: list[str], append: bool):
        """Process files immediately and scan folders on a background thread."""
        if any(Path(path).is_dir() for path in paths):
            self._start_folder_scan(paths, append)
            return
        self._apply_scanned_paths(expand_supported_paths(paths), append)

    def _start_folder_scan(self, paths: list[str], append: bool):
        if self._scan_worker and self._scan_worker.isRunning():
            QMessageBox.information(
                self, "Tarama devam ediyor", "Mevcut klasör taramasının tamamlanmasını bekleyin."
            )
            return

        self._scan_append = append
        self.progress_op_label.setText("Klasör taranıyor")
        self.progress_file_label.setText(
            f"{len(paths)} konumda desteklenen dosyalar aranıyor"
        )
        self.progress_widget.start_indeterminate("Dosyalar bulunuyor...", cancellable=True)
        self.stack.setCurrentIndex(SCENE_PROGRESS)

        worker = PathScanWorker(paths, self)
        self._scan_worker = worker
        worker.completed.connect(self._on_folder_scan_completed)
        worker.error.connect(self._on_folder_scan_error)
        worker.cancelled.connect(self._on_folder_scan_cancelled)
        worker.finished.connect(self._cleanup_scan_worker)
        worker.start()

    def _on_folder_scan_completed(self, paths: list[str]):
        if not paths:
            self.progress_widget.set_error("Klasörde desteklenen dosya bulunamadı.")
            return
        self._apply_scanned_paths(paths, self._scan_append)

    def _on_folder_scan_error(self, message: str):
        self.progress_widget.set_error(f"Klasör taranamadı: {message}")

    def _on_folder_scan_cancelled(self):
        if self._scan_append and self._current_paths:
            self.stack.setCurrentIndex(SCENE_ACTIONS)
            self.progress_widget.reset()
        else:
            self.progress_widget.set_cancelled()

    def _cleanup_scan_worker(self):
        if self._scan_worker:
            self._scan_worker.deleteLater()
            self._scan_worker = None

    def _apply_scanned_paths(self, expanded: list[str], append: bool):
        if not expanded:
            return
        if not append:
            self._set_files(expanded)
            return

        combined = list(self._current_paths)
        existing_set = set(self._current_paths)
        for p in expanded:
            if p not in existing_set:
                combined.append(p)
                existing_set.add(p)
        self._set_files(combined)

    def _set_files(self, paths: list[str]):
        """Applies a new file set: detects type and updates all scenes."""
        if not paths:
            return

        file_type = detect_type(paths)
        self._current_paths = paths

        self._populate_file_list(paths, file_type)
        self._update_detect_band(file_type, paths)
        self._update_action_stack(file_type, len(paths))
        self.stack.setCurrentIndex(SCENE_ACTIONS)

    def _populate_file_list(self, paths: list[str], file_type: str):
        self.file_list.clear()

        for path_str in paths:
            item = QListWidgetItem(self.file_list)
            item.setSizeHint(QSize(0, 56))

            widget = FileListItemWidget(path_str, file_type)
            widget.remove_requested.connect(self._remove_file)

            item.setData(Qt.ItemDataRole.UserRole, path_str)
            self.file_list.addItem(item)
            self.file_list.setItemWidget(item, widget)

    def _remove_file(self, path: str):
        if path in self._current_paths:
            self._current_paths.remove(path)

        if not self._current_paths:
            self._reset_to_empty()
        else:
            self._set_files(list(self._current_paths))

    def _update_detect_band(self, file_type: str, paths: list[str]):
        count = len(paths)
        label_text = get_type_label(file_type, count)

        icon_map = {
            'image':       ('fa5s.images',               '#8da5ff'),
            'word':        ('fa5s.file-word',            '#79adff'),
            'pdf':         ('fa5s.file-pdf',             '#ff9696'),
            'mixed':       ('fa5s.exclamation-triangle', '#f3c96b'),
            'unsupported': ('fa5s.times-circle',         '#f87171'),
        }
        icon_name, color = icon_map.get(file_type, ('fa5s.file', '#7070a0'))
        self.detect_icon.setPixmap(
            qta.icon(icon_name, color=color).pixmap(32, 32)
        )
        self.detect_title.setText(label_text.capitalize())
        self.detect_sub.setText(
            f"{'  '.join(Path(p).name for p in paths[:3])}"
            + (" ..." if count > 3 else "")
        )
        self.file_count_label.setText(f"{count} öğe")

    def _update_action_stack(self, file_type: str, count: int):
        page_map = {
            'image':       0,
            'word':        1,
            'pdf':         2 if count == 1 else 3,
            'mixed':       4,
            'unsupported': 5,
        }
        self.action_stack.setCurrentIndex(page_map.get(file_type, 5))

        can_add = file_type in ('image', 'pdf')
        self.add_more_btn.setEnabled(can_add)
        self.add_more_btn.setVisible(can_add)

    def _reset_to_empty(self):
        self._current_paths = []
        self._pdf_output_path = None
        self.file_list.clear()
        self.pdf_output_label.setText("Henüz çıktı dosyası seçilmedi")
        self.pdf_output_label.setStyleSheet(
            "color: #8391aa; font-size: 11px; border: 1px solid #2a3650;"
            "background: #0f1729; padding: 10px 12px; border-radius: 8px;"
        )
        self.pdf_merge_btn.setEnabled(False)
        self.progress_widget.reset()
        if self._worker:
            self._cleanup_worker()
        self.stack.setCurrentIndex(SCENE_EMPTY)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_unique_path(self, base_path: Path) -> Path:
        """Eğer dosya veya klasör zaten varsa, sonuna _1, _2 gibi ekler koyarak benzersiz bir yol üretir."""
        if not base_path.exists():
            return base_path

        stem = base_path.stem
        ext = base_path.suffix
        directory = base_path.parent

        counter = 1
        while True:
            new_path = directory / f"{stem}_{counter}{ext}"
            if not new_path.exists():
                return new_path
            counter += 1

    # ── PDF Merge Helper ──────────────────────────────────────────────────────

    def _choose_pdf_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Birleştirilmiş PDF'i Kaydet",
            "birlestirilmis.pdf",
            "PDF Dosyası (*.pdf)"
        )
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self._pdf_output_path = path
            short = Path(path).name
            self.pdf_output_label.setText(f"Hazır: {short}")
            self.pdf_output_label.setStyleSheet(
                "color: #9fe8d5; font-size: 11px; border: 1px solid #245047;"
                "background: #10231f; padding: 10px 12px; border-radius: 8px;"
            )
            self.pdf_merge_btn.setEnabled(True)

    # ── Conversion Launchers ──────────────────────────────────────────────────

    def _on_img_fmt_changed(self, fmt: str):
        enabled = fmt in ("JPG", "WEBP")
        self.img_quality_slider.setEnabled(enabled)
        self.img_quality_label.setEnabled(enabled)

    def _update_paths_from_list(self):
        paths = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                paths.append(path)
        self._current_paths = paths

    def _start_pdf_split_all(self):
        self._update_paths_from_list()
        paths = self._current_paths
        if not paths:
            return
        pdf_path = paths[0]

        selected_dir = QFileDialog.getExistingDirectory(self, "Çıktı Klasörünü Seç", str(Path(pdf_path).parent))
        if not selected_dir:
            return
        output_dir = str(self._get_unique_path(Path(selected_dir) / "split_output"))

        worker = ConversionWorker(
            func=pdf_splitter.split_pdf_by_pages,
            kwargs={'input_path': pdf_path, 'output_dir': output_dir},
        )
        self._launch_worker(worker, op_label="PDF Bölme", paths=[pdf_path])

    def _start_pdf_split_ranges(self):
        self._update_paths_from_list()
        paths = self._current_paths
        if not paths:
            return
        range_str = self.pdf_range_input.text().strip()
        if not range_str:
            QMessageBox.warning(self, "Aralık Girilmedi", "Lütfen bir sayfa aralığı girin.\nÖrnek: 1-3, 5, 7-9")
            return
        pdf_path = paths[0]

        selected_dir = QFileDialog.getExistingDirectory(self, "Çıktı Klasörünü Seç", str(Path(pdf_path).parent))
        if not selected_dir:
            return
        output_dir = str(self._get_unique_path(Path(selected_dir) / "split_output"))

        worker = ConversionWorker(
            func=pdf_splitter.split_pdf_by_ranges,
            kwargs={
                'input_path': pdf_path,
                'output_dir': output_dir,
                'range_str':  range_str,
            },
        )
        self._launch_worker(worker, op_label="PDF Bölme (Aralık)", paths=[pdf_path])

    def _start_pdf_to_image(self):
        self._update_paths_from_list()
        paths = self._current_paths
        if not paths:
            return
        pdf_path = paths[0]

        selected_dir = QFileDialog.getExistingDirectory(self, "Çıktı Klasörünü Seç", str(Path(pdf_path).parent))
        if not selected_dir:
            return
        output_dir = str(self._get_unique_path(Path(selected_dir) / "pdf_pages"))

        fmt = self.pdf_img_fmt_combo.currentText()

        try:
            dpi_str = self.pdf_img_dpi_combo.currentText().split()[0]
            dpi = int(dpi_str)
        except (ValueError, IndexError):
            dpi = 150

        worker = ConversionWorker(
            func=pdf_to_image_converter.convert_pdf_to_images,
            kwargs={
                'pdf_path':      pdf_path,
                'output_dir':    output_dir,
                'output_format': fmt,
                'dpi':           dpi,
            },
        )
        self._launch_worker(worker, op_label=f"PDF → Görsel ({fmt}, {dpi} DPI)", paths=[pdf_path])

    def _start_pdf_to_word(self):
        self._update_paths_from_list()
        paths = self._current_paths
        if not paths:
            return
        pdf_path = paths[0]

        selected_dir = QFileDialog.getExistingDirectory(self, "Çıktı Klasörünü Seç", str(Path(pdf_path).parent))
        if not selected_dir:
            return
        output_path = str(self._get_unique_path(Path(selected_dir) / (Path(pdf_path).stem + ".docx")))

        worker = ConversionWorker(
            func=pdf_to_word_converter.convert_pdf_to_word,
            kwargs={
                'pdf_path':    pdf_path,
                'output_path': output_path,
            },
        )
        self._launch_worker(
            worker,
            op_label="PDF → Word Dönüşümü",
            paths=[pdf_path],
            cancellable=False,
        )

    def _start_image_convert(self):
        self._update_paths_from_list()
        paths = self._current_paths
        if not paths:
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Çıktı Klasörünü Seç", str(Path(paths[0]).parent))
        if not output_dir:
            return

        fmt     = self.img_fmt_combo.currentText()
        quality = self.img_quality_slider.value()
        worker = ConversionWorker(
            func=img_converter_fmt.convert_images,
            kwargs={
                'image_paths':   paths,
                'output_dir':    output_dir,
                'output_format': fmt,
                'quality':       quality,
            },
        )
        self._launch_worker(worker, op_label=f"Format Dönüştürme → {fmt}", paths=paths)

    def _start_image_to_pdf(self):
        self._update_paths_from_list()
        paths = self._current_paths
        if not paths:
            return

        source_dir = Path(paths[0]).parent
        selected_dir = QFileDialog.getExistingDirectory(self, "Çıktı Klasörünü Seç", str(source_dir))
        if not selected_dir:
            return

        output_path = str(self._get_unique_path(Path(selected_dir) / "converted_images.pdf"))
        page_size = self.img_page_combo.currentText()

        worker = ConversionWorker(
            func=img_converter.convert_images_to_pdf,
            kwargs={
                'image_paths': paths,
                'output_path': output_path,
                'page_size':   page_size,
            }
        )
        self._launch_worker(worker, op_label="Resim → PDF Dönüşümü", paths=paths)

    def _start_word_to_pdf(self):
        self._update_paths_from_list()
        paths = self._current_paths
        if not paths:
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Çıktı Klasörünü Seç", str(Path(paths[0]).parent))
        if not output_dir:
            return

        worker = ConversionWorker(
            func=word_converter.convert_word_to_pdf,
            kwargs={
                'input_paths': paths,
                'output_dir': output_dir,
            }
        )
        self._launch_worker(worker, op_label="Word → PDF Dönüşümü", paths=paths)

    def _start_pdf_merge(self):
        self._update_paths_from_list()
        paths = self._current_paths
        if len(paths) < 2:
            QMessageBox.warning(self, "Yetersiz Dosya", "En az 2 PDF dosyası gerekli.")
            return

        if not self._pdf_output_path:
            QMessageBox.warning(self, "Kayıt Konumu", "Lütfen kayıt konumu seçin.")
            return

        worker = ConversionWorker(
            func=pdf_converter.merge_pdfs,
            kwargs={
                'input_paths': paths,
                'output_path': self._pdf_output_path,
            }
        )
        self._launch_worker(worker, op_label="PDF Birleştirme", paths=paths)

    def _launch_worker(
        self,
        worker: ConversionWorker,
        op_label: str,
        paths: list[str],
        cancellable: bool = True,
    ):
        """Configures, connects, and starts a ConversionWorker."""
        self._worker = worker

        count = len(paths)
        self.progress_op_label.setText(op_label)
        self.progress_file_label.setText(
            f"{count} dosya işlenecek — "
            f"{', '.join(Path(p).name for p in paths[:2])}"
            + (" ..." if count > 2 else "")
        )
        self.progress_widget.start(cancellable=cancellable)
        self.stack.setCurrentIndex(SCENE_PROGRESS)

        worker.progress.connect(self.progress_widget.set_progress)
        worker.status.connect(self.progress_widget.set_status)
        worker.succeeded.connect(self._on_finished)
        worker.error.connect(self._on_error)
        worker.cancelled.connect(self._on_cancelled)
        worker.finished.connect(self._cleanup_worker)

        worker.start()

    # ── Worker Result Handlers ────────────────────────────────────────────────

    def _on_finished(self, output_path: str):
        self.progress_widget.set_finished(output_path)

    def _on_error(self, message: str):
        self.progress_widget.set_error(message)
        QMessageBox.warning(
            self,
            "Dönüşüm Hatası",
            f"İşlem sırasında bir sorun oluştu:\n\n{message}\n\n"
            "Dosyaların bozuk olmadığını kontrol edin.",
        )

    def _on_cancelled(self):
        """Called when the worker is cancelled by the user."""
        self.progress_widget.set_cancelled()

    def _cancel_worker(self):
        """Requests cancellation of the currently running worker."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
        elif self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()

    def has_running_operation(self) -> bool:
        """Return whether a conversion is currently active."""
        return bool(
            (self._worker and self._worker.isRunning())
            or (self._scan_worker and self._scan_worker.isRunning())
        )

    def request_shutdown(self, finished_callback) -> bool:
        """Cancel active work and invoke callback after the thread has stopped."""
        worker = self._worker if self._worker and self._worker.isRunning() else self._scan_worker
        if not worker or not worker.isRunning():
            return False
        worker.finished.connect(finished_callback)
        worker.cancel()
        return True

    def _cleanup_worker(self):
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
