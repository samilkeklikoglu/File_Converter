"""
ui/panels/word_to_pdf.py — Word → PDF Panel

ÖĞRENME NOTU — Tek Dosya Dönüşümü:

  Resim → PDF panelinden temel fark:
    - Birden fazla dosya yerine TEK bir .docx / .doc dosyası kabul edilir
    - Dosya listesi yerine tek dosyayı gösteren basit bir bilgi etiketi kullanılır
    - Sayfa boyutu ayarı yoktur (Word belgesinin kendi sayfa düzeni korunur)
    - drop_zone filtresi yalnızca .docx ve .doc uzantılarını kabul eder

  Mimari olarak image_to_pdf paneli ile birebir aynı yapıdadır:
    DropZone         → dosya alma
    ConversionWorker → arka planda dönüştür
    ProgressWidget   → ilerlemeyi göster
"""

import os
from pathlib import Path
import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QFileDialog,
)
from PySide6.QtCore import Qt

from ui.drop_zone import DropZone
from ui.progress_widget import ProgressWidget
from core.worker import ConversionWorker
from core import word_to_pdf as converter


class WordToPdfPanel(QWidget):
    """
    Word → PDF dönüşüm paneli.
    Sürükle-bırak ile .docx / .doc dosyası alır, PDF'e dönüştürür.
    """

    ACCEPTED_EXTENSIONS = {'.docx', '.doc'}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ConversionWorker | None = None  # aktif thread referansı
        self._current_file: str | None = None          # seçili dosya yolu
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        """Tüm widget'ları oluştur ve layout'a yerleştir."""

        # Ana dikey layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(16)

        # ── Başlık ───────────────────────────────────────────────────────────
        header_layout = QHBoxLayout()

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon("fa5s.file-word", color="#7c6af7").pixmap(32, 32))

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Word → PDF")
        title.setObjectName("titleLabel")
        subtitle = QLabel("DOCX ve DOC belgelerini PDF formatına dönüştürün")
        subtitle.setObjectName("subtitleLabel")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        header_layout.addWidget(icon_label)
        header_layout.addSpacing(10)
        header_layout.addLayout(title_col)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # ── Platform Uyarı Bandı ──────────────────────────────────────────────
        # docx2pdf Windows'ta Microsoft Word gerektirir; bunu kullanıcıya göster
        import sys as _sys
        if _sys.platform == "win32":
            warn_text = "ℹ  Bu özellik Microsoft Word'ün kurulu olmasını gerektirir."
            warn_color = "#1e1e35"
            warn_text_color = "#8080c0"
        else:
            warn_text = "⚠  docx2pdf yalnızca Windows ve macOS'ta çalışır. Linux desteklenmez."
            warn_color = "#2a1a1a"
            warn_text_color = "#c07070"

        warn_label = QLabel(warn_text)
        warn_label.setStyleSheet(
            f"background: {warn_color}; color: {warn_text_color}; "
            "font-size: 12px; padding: 8px 14px; border-radius: 6px;"
        )
        warn_label.setWordWrap(True)
        main_layout.addWidget(warn_label)

        # ── Sürükle-Bırak Alanı ──────────────────────────────────────────────
        self.drop_zone = DropZone(accepted_extensions=self.ACCEPTED_EXTENSIONS)
        main_layout.addWidget(self.drop_zone)

        # ── Seçili Dosya Başlığı + Butonlar ──────────────────────────────────
        file_header = QHBoxLayout()

        file_section_label = QLabel("Seçili Dosya")
        file_section_label.setObjectName("sectionLabel")

        self.add_btn = QPushButton("  Dosya Seç")
        self.add_btn.setIcon(qta.icon("fa5s.folder-open", color="#9090c0"))
        self.add_btn.setFixedHeight(30)

        self.clear_btn = QPushButton("  Temizle")
        self.clear_btn.setIcon(qta.icon("fa5s.times", color="#9090c0"))
        self.clear_btn.setFixedHeight(30)
        self.clear_btn.setEnabled(False)

        file_header.addWidget(file_section_label)
        file_header.addStretch()
        file_header.addWidget(self.add_btn)
        file_header.addWidget(self.clear_btn)
        main_layout.addLayout(file_header)

        # ── Seçili Dosya Listesi (tek öğe gösterir) ───────────────────────────
        # QListWidget kullanılıyor (image_to_pdf ile tutarlı görünüm için)
        self.file_list = QListWidget()
        self.file_list.setObjectName("fileList")
        self.file_list.setMinimumHeight(80)
        self.file_list.setMaximumHeight(100)
        self.file_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._show_placeholder()
        main_layout.addWidget(self.file_list)

        # ── Çıktı Bilgisi ─────────────────────────────────────────────────────
        self.output_info_label = QLabel("PDF, kaynak dosyayla aynı klasöre kaydedilecek.")
        self.output_info_label.setStyleSheet("color: #5050a0; font-size: 12px;")
        main_layout.addWidget(self.output_info_label)

        # ── Dönüştür Butonu ───────────────────────────────────────────────────
        self.convert_btn = QPushButton("  PDF Oluştur")
        self.convert_btn.setObjectName("primaryBtn")
        self.convert_btn.setIcon(qta.icon("fa5s.file-export", color="#ffffff"))
        self.convert_btn.setEnabled(False)
        self.convert_btn.setFixedHeight(48)
        main_layout.addWidget(self.convert_btn)

        # ── İlerleme Widget'ı ─────────────────────────────────────────────────
        self.progress_widget = ProgressWidget()
        main_layout.addWidget(self.progress_widget)

        # Alt boşluk
        main_layout.addStretch()

    def _connect_signals(self):
        """Tüm sinyal → slot bağlantılarını kur."""

        # Drop zone → dosya seç
        self.drop_zone.files_dropped.connect(self._on_files_dropped)

        # Butonlar
        self.add_btn.clicked.connect(self._open_file_dialog)
        self.clear_btn.clicked.connect(self._clear_file)

        # Dönüştür
        self.convert_btn.clicked.connect(self._start_conversion)

        # Progress widget "Temizle" butonu
        self.progress_widget.clear_requested.connect(self._clear_file)

    # ── Dosya Yönetimi ────────────────────────────────────────────────────────

    def _open_file_dialog(self):
        """Standart dosya seçme dialogunu aç (tek dosya)."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Word Belgesi Seç",
            "",
            "Word Belgeleri (*.docx *.doc)"
        )
        if path:
            self._set_file(path)

    def _on_files_dropped(self, paths: list[str]):
        """Drop zone'dan düşen dosyaları işle — yalnızca ilk geçerli dosyayı al."""
        for path_str in paths:
            p = Path(path_str)
            if p.suffix.lower() in self.ACCEPTED_EXTENSIONS:
                self._set_file(path_str)
                return  # İlk geçerli dosyayla yetiniyoruz

    def _set_file(self, path_str: str):
        """Seçilen dosyayı panele yükle."""
        path = Path(path_str)

        # Uzantı kontrolü
        if path.suffix.lower() not in self.ACCEPTED_EXTENSIONS:
            QMessageBox.warning(
                self,
                "Desteklenmeyen Dosya",
                f"'{path.name}' dosyası desteklenmiyor.\n"
                "Yalnızca .docx ve .doc dosyaları kabul edilir."
            )
            return

        self._current_file = path_str

        # Listeyi güncelle
        self.file_list.clear()
        item = QListWidgetItem()
        item.setText(f"  {path.name}")
        item.setToolTip(path_str)  # tam yol tooltip'te
        item.setIcon(qta.icon("fa5s.file-word", color="#7c6af7"))
        item.setData(Qt.ItemDataRole.UserRole, path_str)
        self.file_list.addItem(item)

        # Çıktı bilgisini güncelle
        output_path = path.parent / (path.stem + ".pdf")
        self.output_info_label.setText(f"PDF kaydedilecek: {output_path}")

        self._update_ui_state()

    def _clear_file(self):
        """Seçili dosyayı temizle."""
        self._current_file = None
        self.file_list.clear()
        self._show_placeholder()
        self.output_info_label.setText("PDF, kaynak dosyayla aynı klasöre kaydedilecek.")
        self._update_ui_state()

    def _show_placeholder(self):
        """Boş liste mesajını göster."""
        self.file_list.addItem("— Henüz dosya seçilmedi —")
        self.file_list.item(0).setForeground(Qt.GlobalColor.darkGray)
        self.file_list.item(0).setFlags(Qt.ItemFlag.NoItemFlags)

    def _update_ui_state(self):
        """Dosya durumuna göre buton durumlarını güncelle."""
        has_file = self._current_file is not None
        self.convert_btn.setEnabled(has_file)
        self.clear_btn.setEnabled(has_file)

    # ── Dönüşüm ──────────────────────────────────────────────────────────────

    def _start_conversion(self):
        """
        Dönüşümü başlat.

        Adımlar:
          1. Kaynak dosya ve çıktı klasörünü belirle
          2. ConversionWorker oluştur ve sinyalleri bağla
          3. Worker'ı başlat (ayrı thread'de çalışır)
          4. UI'yı \"çalışıyor\" moduna al
        """
        if not self._current_file:
            return

        source = Path(self._current_file)

        # ── Çıktı Klasörü ─────────────────────────────────────────────────────
        # Kaynak dosyayla aynı klasör
        output_dir = str(source.parent)

        # ── Worker Oluştur ────────────────────────────────────────────────────
        self._worker = ConversionWorker(
            func=converter.convert_word_to_pdf,
            kwargs={
                'input_path': self._current_file,
                'output_dir': output_dir,
                # progress_callback ve status_callback worker tarafından eklenir
            }
        )

        # ── Sinyalleri Bağla ─────────────────────────────────────────────────
        self._worker.progress.connect(self.progress_widget.set_progress)
        self._worker.status.connect(self.progress_widget.set_status)
        self._worker.finished.connect(self._on_conversion_finished)
        self._worker.error.connect(self._on_conversion_error)
        # Thread bitince referansı temizle (bellek sızıntısı önlemi)
        self._worker.finished.connect(lambda _: self._cleanup_worker())
        self._worker.error.connect(lambda _: self._cleanup_worker())

        # ── UI'yı Kilitle (işlem süresince) ───────────────────────────────────
        self.convert_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.progress_widget.start()

        # ── Thread'i Başlat ────────────────────────────────────────────────────
        self._worker.start()

    def _on_conversion_finished(self, output_path: str):
        """İşlem başarıyla bitti."""
        self.progress_widget.set_finished(output_path)
        self._unlock_ui()

    def _on_conversion_error(self, message: str):
        """İşlem sırasında hata oluştu."""
        self.progress_widget.set_error(message)
        self._unlock_ui()

        # Kullanıcıya ek hata dialogu göster
        QMessageBox.warning(
            self,
            "Dönüşüm Hatası",
            f"İşlem sırasında bir sorun oluştu:\n\n{message}\n\n"
            "Microsoft Word'ün kurulu ve dosyanın açık olmadığını kontrol edin.",
        )

    def _unlock_ui(self):
        """İşlem bitince UI elemanlarını tekrar aktif et."""
        has_file = self._current_file is not None
        self.convert_btn.setEnabled(has_file)
        self.add_btn.setEnabled(True)
        self.clear_btn.setEnabled(has_file)

    def _cleanup_worker(self):
        """Thread referansını temizle."""
        if self._worker:
            self._worker.deleteLater()  # Qt bellek yönetimi
            self._worker = None
