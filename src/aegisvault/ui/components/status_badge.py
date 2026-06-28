"""Small semantic status badge."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel

from aegisvault.core.models import TaskState


class StatusBadge(QLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.setObjectName("StatusBadge")
        self.set_state(TaskState.IDLE, text or "Ready")

    def set_state(self, state: TaskState, text: str) -> None:
        self.setText(text)
        self.setProperty("state", state.value)
        self.style().unpolish(self)
        self.style().polish(self)


