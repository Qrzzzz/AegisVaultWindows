"""Inline progress and cancellation control for background tasks."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from aegisvault.core.models import ProgressEvent, TaskState
from aegisvault.i18n.translator import Translator
from aegisvault.ui.pages.common import format_size


class TaskProgress(QFrame):
    def __init__(self, translator: Translator) -> None:
        super().__init__()
        self.i18n = translator
        self._event: ProgressEvent | None = None
        self.setObjectName("TaskProgress")
        self.stage = QLabel()
        self.stage.setObjectName("SectionTitle")
        self.detail = QLabel("")
        self.detail.setObjectName("Muted")
        self.detail.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setAccessibleName(self.i18n.t("access.task_progress"))
        self.bar.setRange(0, 100)
        self.cancel_button = QPushButton()
        self.cancel_button.setObjectName("Danger")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stage)
        layout.addWidget(self.detail)
        row = QHBoxLayout()
        row.addWidget(self.bar, 1)
        row.addWidget(self.cancel_button)
        layout.addLayout(row)
        self.retranslate_ui()
        self.reset()

    def retranslate_ui(self) -> None:
        self.bar.setAccessibleName(self.i18n.t("access.task_progress"))
        self.cancel_button.setText(self.i18n.t("action.cancel"))
        self.cancel_button.setAccessibleName(self.i18n.t("action.cancel"))
        if self._event is not None:
            self.set_event(self._event)
        elif self.isVisible():
            self.stage.setText(self.i18n.t("status.running"))

    def set_running(self, running: bool, *, cancelling: bool = False) -> None:
        if running:
            self.show()
            self.cancel_button.setEnabled(not cancelling)
            if self._event is None:
                self.bar.setRange(0, 0)
                self.stage.setText(self.i18n.t("status.cancelling" if cancelling else "status.running"))
                self.detail.clear()
                self.detail.hide()
        else:
            self.cancel_button.setEnabled(False)

    def set_state(self, state: TaskState) -> None:
        if state == TaskState.RUNNING:
            self.set_running(True)
        elif state == TaskState.CANCELLING:
            self.set_running(True, cancelling=True)
            self.stage.setText(self.i18n.t("status.cancelling"))
        else:
            self.set_running(False)

    def set_event(self, event: ProgressEvent) -> None:
        self._event = event
        self.show()
        self.bar.setRange(0, 100)
        percent = round(event.percent * 100)
        stage = self.i18n.t(f"status.{event.stage}")
        self.stage.setText(self.i18n.t("progress.stage", stage=stage, percent=percent))
        detail = event.detail
        if event.total_bytes is not None and event.processed_bytes is not None:
            sizes = self.i18n.t(
                "progress.bytes",
                processed=format_size(event.processed_bytes),
                total=format_size(event.total_bytes),
            )
            detail = f"{detail} · {sizes}" if detail else sizes
        self.detail.setText(detail)
        self.detail.setVisible(bool(detail))
        self.bar.setValue(percent)

    def reset(self) -> None:
        self._event = None
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.stage.setText(self.i18n.t("status.ready"))
        self.detail.clear()
        self.cancel_button.setEnabled(False)
        self.hide()
