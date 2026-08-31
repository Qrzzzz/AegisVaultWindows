"""Single-task controller with stale-callback isolation and safe shutdown."""

from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal, Slot

from aegisvault.core.exceptions import OperationCancelled
from aegisvault.core.models import CancelToken, ProgressCallback, TaskState

TaskCallable = Callable[[ProgressCallback, CancelToken], Any]
TaskOutcome = tuple[str, object, str]


class _TaskThread(QThread):
    """QThread whose result is read only after run() has returned."""

    progress = Signal(object)

    def __init__(self, task: TaskCallable, token: CancelToken, parent: QObject) -> None:
        super().__init__(parent)
        self._task = task
        self._token = token
        self.outcome: TaskOutcome | None = None

    def run(self) -> None:
        try:
            result = self._task(self.progress.emit, self._token)
        except Exception as exc:
            self.outcome = ("failure", exc, traceback.format_exc())
        else:
            self.outcome = ("success", result, "")
        finally:
            self._task = lambda _progress, _token: None

    def take_outcome(self) -> TaskOutcome | None:
        outcome = self.outcome
        self.outcome = None
        return outcome


class TaskController(QObject):
    """Run one task at a time and publish terminal state after its thread stops."""

    state_changed = Signal(object)
    progress_changed = Signal(object)
    succeeded = Signal(object)
    failed = Signal(object, str)
    cancelled = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.state = TaskState.IDLE
        self._thread: _TaskThread | None = None
        self._retired_threads: list[_TaskThread] = []
        self._token: CancelToken | None = None
        self._sequence = 0
        self._active_task_id: int | None = None

    @property
    def busy(self) -> bool:
        """Whether a worker thread still owns the active operation."""

        return self._active_task_id is not None

    @property
    def active_task_id(self) -> int | None:
        return self._active_task_id

    def run(self, task: TaskCallable) -> bool:
        if self.busy:
            return False

        self._sequence += 1
        task_id = self._sequence
        token = CancelToken()
        thread = _TaskThread(task, token, self)
        thread.setProperty("aegis_task_id", task_id)
        thread.progress.connect(self._on_thread_progress)
        thread.finished.connect(self._on_thread_finished)

        self._thread = thread
        self._token = token
        self._active_task_id = task_id
        self._set_state(TaskState.RUNNING)
        thread.start()
        return True

    def cancel(self) -> bool:
        """Request cancellation once; repeated requests are harmless."""

        if self.state != TaskState.RUNNING or self._token is None:
            return False
        self._set_state(TaskState.CANCELLING)
        self._token.cancel()
        return True

    def can_close(self) -> bool:
        return not self.busy

    def wait_for_finished(self, timeout_ms: int = 30_000) -> bool:
        """Wait for the active worker to reach a stopped-thread terminal state."""

        thread = self._thread
        task_id = self._active_task_id
        if thread is None or task_id is None:
            return True
        if QThread.currentThread() is thread:
            return False
        if not thread.wait(max(0, timeout_ms)):
            return False
        # closeEvent blocks the GUI loop, so finalize synchronously after the
        # thread has stopped. A queued duplicate is rejected by the task id.
        self._finish_task(task_id, thread)
        QCoreApplication.processEvents()
        return True

    @Slot(object)
    def _on_thread_progress(self, event: object) -> None:
        sender = self.sender()
        if not isinstance(sender, _TaskThread):
            return
        task_id = sender.property("aegis_task_id")
        if isinstance(task_id, int) and task_id == self._active_task_id:
            self.progress_changed.emit(event)

    @Slot()
    def _on_thread_finished(self) -> None:
        sender = self.sender()
        if not isinstance(sender, _TaskThread):
            return
        task_id = sender.property("aegis_task_id")
        if isinstance(task_id, int):
            self._finish_task(task_id, sender)

    def _finish_task(self, task_id: int, thread: _TaskThread) -> None:
        if task_id != self._active_task_id or thread is not self._thread:
            return
        outcome = thread.take_outcome()
        cancellation_requested = bool(self._token and self._token.cancelled)
        self._thread = None
        self._token = None
        self._active_task_id = None
        # Keep stopped QThread wrappers parented until the controller is
        # destroyed. This avoids deferred-delete races on PySide/Windows.
        self._retired_threads.append(thread)

        if outcome is None:
            exc = RuntimeError("Worker stopped without reporting an outcome.")
            self._set_state(TaskState.FAILED)
            self.failed.emit(exc, "")
            return
        kind, payload, diagnostic = outcome
        if kind == "success" and cancellation_requested:
            self._set_state(TaskState.CANCELLED)
            self.cancelled.emit()
        elif kind == "success":
            self._set_state(TaskState.DONE)
            self.succeeded.emit(payload)
        elif isinstance(payload, OperationCancelled):
            self._set_state(TaskState.CANCELLED)
            self.cancelled.emit()
        else:
            self._set_state(TaskState.FAILED)
            self.failed.emit(payload, diagnostic)

    def _set_state(self, state: TaskState) -> None:
        self.state = state
        self.state_changed.emit(state)
