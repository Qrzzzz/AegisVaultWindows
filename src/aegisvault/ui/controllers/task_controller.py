"""Single-task controller with cancellation-aware state transitions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from aegisvault.core.exceptions import OperationCancelled
from aegisvault.core.models import CancelToken, ProgressCallback, TaskState
from aegisvault.ui.workers import FunctionWorker

TaskCallable = Callable[[ProgressCallback, CancelToken], Any]


class TaskController(QObject):
    """Run one background task at a time and expose stable UI states."""

    state_changed = Signal(object)
    progress_changed = Signal(object)
    succeeded = Signal(object)
    failed = Signal(object, str)
    cancelled = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.state = TaskState.IDLE
        self._thread: QThread | None = None
        self._token: CancelToken | None = None

    @property
    def busy(self) -> bool:
        return self.state in {TaskState.RUNNING, TaskState.CANCELLING}

    def run(self, task: TaskCallable) -> bool:
        if self.busy:
            return False
        self._token = CancelToken()
        self._set_state(TaskState.RUNNING)
        thread = QThread(self)
        worker = FunctionWorker(lambda progress: task(progress, self._token or CancelToken()))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self.progress_changed.emit)
        worker.succeeded.connect(self._on_success)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_thread)
        self._thread = thread
        thread.start()
        return True

    def cancel(self) -> None:
        if self.state == TaskState.RUNNING and self._token:
            self._set_state(TaskState.CANCELLING)
            self._token.cancel()

    def can_close(self) -> bool:
        return not self.busy

    def _on_success(self, result: object) -> None:
        self._set_state(TaskState.DONE)
        self.succeeded.emit(result)

    def _on_failed(self, exc: object, diagnostic: str) -> None:
        if isinstance(exc, OperationCancelled):
            self._set_state(TaskState.CANCELLED)
            self.cancelled.emit()
            return
        self._set_state(TaskState.FAILED)
        self.failed.emit(exc, diagnostic)

    def _clear_thread(self) -> None:
        self._thread = None
        self._token = None

    def _set_state(self, state: TaskState) -> None:
        self.state = state
        self.state_changed.emit(state)


