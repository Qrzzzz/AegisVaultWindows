"""Thread helpers for PySide6 workflows."""

from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from aegisvault.core.models import ProgressEvent


class FunctionWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(object, str)
    progress = Signal(object)
    finished = Signal()

    def __init__(self, fn: Callable[[Callable[[ProgressEvent], None]], Any]) -> None:
        super().__init__()
        self._fn = fn

    @Slot()
    def run(self) -> None:
        try:
            result = self._fn(self.progress.emit)
        except Exception as exc:
            self.failed.emit(exc, traceback.format_exc())
        else:
            self.succeeded.emit(result)
        finally:
            self.finished.emit()


