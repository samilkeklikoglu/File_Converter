import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from ui.drop_zone import extract_local_paths
from ui.main_window import MainWindow, _load_app_icon
from ui.panels.smart_panel import SmartPanel
from ui.progress_widget import ProgressWidget


class UiRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_cancel_button_is_reenabled_for_next_operation(self):
        widget = ProgressWidget()
        widget.start()
        widget._on_cancel()
        self.assertFalse(widget.cancel_btn.isEnabled())

        widget.reset()
        widget.start()
        self.assertTrue(widget.cancel_btn.isEnabled())
        self.assertFalse(widget.cancel_btn.isHidden())
        widget.close()

    def test_non_cancellable_operation_hides_cancel_button(self):
        widget = ProgressWidget()
        widget.start(cancellable=False)
        self.assertTrue(widget.cancel_btn.isHidden())
        widget.close()

    def test_progress_value_is_clamped_and_readable(self):
        widget = ProgressWidget()
        widget.set_progress(140)
        self.assertEqual(widget.progress_bar.value(), 100)
        self.assertEqual(widget.progress_value.text(), "100%")

        widget.set_progress(-5)
        self.assertEqual(widget.progress_bar.value(), 0)
        self.assertEqual(widget.progress_value.text(), "0%")
        widget.close()

    def test_application_icon_loads(self):
        self.assertFalse(_load_app_icon().isNull())

    def test_pdf_to_word_is_launched_as_non_cancellable(self):
        with tempfile.TemporaryDirectory(prefix="fileconverter_pdf_word_ui_") as temp_dir:
            source = Path(temp_dir) / "source.pdf"
            source.write_bytes(b"fixture")
            panel = SmartPanel()
            panel._set_files([str(source)])
            launches = []
            panel._launch_worker = lambda *args, **kwargs: launches.append(kwargs)

            with patch(
                "ui.panels.smart_panel.QFileDialog.getExistingDirectory",
                return_value=temp_dir,
            ):
                panel._start_pdf_to_word()

            self.assertEqual(len(launches), 1)
            self.assertFalse(launches[0]["cancellable"])
            panel.close()

    def test_folder_paths_are_extracted_and_expanded(self):
        with tempfile.TemporaryDirectory(prefix="fileconverter_folder_unit_") as temp_dir:
            root = Path(temp_dir)
            nested = root / "nested"
            nested.mkdir()
            supported = nested / "document.pdf"
            unsupported = nested / "notes.txt"
            supported.write_bytes(b"fixture")
            unsupported.write_bytes(b"fixture")

            urls = [QUrl.fromLocalFile(str(root)), QUrl("https://example.com/a.pdf")]
            self.assertEqual(extract_local_paths(urls), [str(root)])

            panel = SmartPanel()
            self.assertEqual(panel._expand_directories([str(root)]), [str(supported)])
            panel.close()

    def test_file_types_open_the_matching_action_page(self):
        with tempfile.TemporaryDirectory(prefix="fileconverter_ui_actions_") as temp_dir:
            root = Path(temp_dir)
            images = [root / "one.jpg", root / "two.png"]
            pdfs = [root / "one.pdf", root / "two.pdf"]
            for path in images + pdfs:
                path.write_bytes(b"fixture")

            panel = SmartPanel()
            panel._set_files([str(path) for path in images])
            self.assertEqual(panel.action_stack.currentIndex(), 0)
            self.assertEqual(panel.file_count_label.text(), "2 öğe")

            panel._set_files([str(pdfs[0])])
            self.assertEqual(panel.action_stack.currentIndex(), 2)

            panel._set_files([str(path) for path in pdfs])
            self.assertEqual(panel.action_stack.currentIndex(), 3)
            panel.close()

    def test_folder_selection_is_routed_to_background_scan(self):
        with tempfile.TemporaryDirectory(prefix="fileconverter_ui_scan_") as temp_dir:
            panel = SmartPanel()
            with patch.object(panel, "_start_folder_scan") as start_scan:
                panel._queue_paths([temp_dir], append=False)
            start_scan.assert_called_once_with([temp_dir], False)
            panel.close()

    def test_window_close_cancels_active_work_and_defers_exit(self):
        window = MainWindow()
        callbacks = []
        window.smart_panel.has_running_operation = lambda: True
        window.smart_panel.request_shutdown = lambda callback: callbacks.append(callback) or True
        event = QCloseEvent()

        with patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            window.closeEvent(event)

        self.assertFalse(event.isAccepted())
        self.assertFalse(window.isEnabled())
        self.assertEqual(len(callbacks), 1)
        window._force_close = True
        window.close()


if __name__ == "__main__":
    unittest.main()
