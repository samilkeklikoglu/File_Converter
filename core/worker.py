"""
core/worker.py — QThread-Based Background Worker

Runs any conversion function in a background thread to keep the UI responsive.
Communicates progress and results back to the main thread via Qt signals.
"""

from PySide6.QtCore import QThread, Signal


class CancelledException(Exception):
    """Raised by conversion functions when a cancel_check callback returns True."""
    pass


class ConversionWorker(QThread):
    """
    Generic background worker that executes a conversion function in a separate thread.

    The conversion function is passed via `func` at construction time, making this
    worker reusable for image-to-PDF, word-to-PDF, PDF merging, or any future converter.

    All converter functions must follow this contract:
        - Accept `progress_callback: Callable[[int], None]` keyword argument.
        - Accept `status_callback: Callable[[str], None]` keyword argument.
        - Accept `cancel_check: Callable[[], bool]` keyword argument.
        - Return the full output file path (str) on success.
        - Raise CancelledException when cancel_check() returns True.
        - Raise an exception on failure (never return silently).

    Signals:
        progress  (int): Progress percentage, 0–100.
        status    (str): Human-readable status message.
        succeeded (str): Emitted on success with the output file path.
        error     (str): Emitted on failure with the error message.
        cancelled ():    Emitted when the operation is cancelled by the user.

    Args:
        func:   The conversion function to execute.
        kwargs: Keyword arguments forwarded to `func` (excluding callbacks).
    """

    progress  = Signal(int)
    status    = Signal(str)
    succeeded = Signal(str)
    error     = Signal(str)
    cancelled = Signal()

    def __init__(self, func, kwargs: dict, parent=None):
        super().__init__(parent)
        self._func = func
        self._kwargs = kwargs
        self._cancelled = False

    def cancel(self):
        """Request cancellation. Thread-safe — can be called from the main thread."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        """Returns True if cancellation has been requested."""
        return self._cancelled

    def run(self):
        try:
            self._kwargs['progress_callback'] = lambda v: self.progress.emit(v)
            self._kwargs['status_callback']   = lambda s: self.status.emit(s)
            self._kwargs['cancel_check']      = self.is_cancelled

            output_path = self._func(**self._kwargs)

            if self._cancelled:
                self.cancelled.emit()
            else:
                self.succeeded.emit(output_path)

        except CancelledException:
            self.cancelled.emit()

        except Exception as exc:
            if self._cancelled:
                self.cancelled.emit()
            else:
                self.error.emit(str(exc))


class PathScanWorker(QThread):
    """Expand dropped folders without blocking the UI thread."""

    completed = Signal(list)
    error = Signal(str)
    cancelled = Signal()

    def __init__(self, paths: list[str], parent=None):
        super().__init__(parent)
        self._paths = list(paths)
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def run(self):
        from core.file_detector import expand_supported_paths

        try:
            paths = expand_supported_paths(self._paths, self.is_cancelled)
            if self._cancelled:
                self.cancelled.emit()
            else:
                self.completed.emit(paths)
        except CancelledException:
            self.cancelled.emit()
        except Exception as exc:
            self.error.emit(str(exc))
