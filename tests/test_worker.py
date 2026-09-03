import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QSignalSpy

from core.worker import CancelledException, ConversionWorker


class ConversionWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    @staticmethod
    def _wait_for(worker, signal_spy):
        worker.start()
        if not worker.wait(3000):
            worker.requestInterruption()
            worker.wait(1000)
            raise AssertionError("Worker did not finish within 3 seconds")
        QCoreApplication.processEvents()
        if signal_spy.count() == 0:
            raise AssertionError("QThread.finished was not emitted")

    def test_success_uses_separate_succeeded_signal(self):
        def convert(**_kwargs):
            return "output.pdf"

        worker = ConversionWorker(convert, {})
        succeeded = QSignalSpy(worker.succeeded)
        thread_finished = QSignalSpy(worker.finished)
        self._wait_for(worker, thread_finished)

        self.assertEqual(succeeded.count(), 1)
        self.assertEqual(succeeded.at(0), ["output.pdf"])
        self.assertEqual(thread_finished.count(), 1)
        self.assertEqual(thread_finished.at(0), [])

    def test_error_still_reaches_real_thread_finished_signal(self):
        def convert(**_kwargs):
            raise RuntimeError("conversion failed")

        worker = ConversionWorker(convert, {})
        errors = QSignalSpy(worker.error)
        thread_finished = QSignalSpy(worker.finished)
        self._wait_for(worker, thread_finished)

        self.assertEqual(errors.count(), 1)
        self.assertEqual(errors.at(0), ["conversion failed"])
        self.assertEqual(thread_finished.count(), 1)

    def test_cancelled_still_reaches_real_thread_finished_signal(self):
        def convert(**_kwargs):
            raise CancelledException("cancelled")

        worker = ConversionWorker(convert, {})
        cancelled = QSignalSpy(worker.cancelled)
        thread_finished = QSignalSpy(worker.finished)
        self._wait_for(worker, thread_finished)

        self.assertEqual(cancelled.count(), 1)
        self.assertEqual(thread_finished.count(), 1)


if __name__ == "__main__":
    unittest.main()
