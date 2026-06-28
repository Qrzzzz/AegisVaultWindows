"""Progress card for file tasks."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QPushButton, QVBoxLayout

from aegisvault.core.models import ProgressEvent
from aegisvault.ui.design import spacing
from aegisvault.ui.pages.common import format_size


class TaskProgress(QFrame):
    def __init__(self, cancel_label: str) -> None:
        super().__init__()
        self.setObjectName("TaskProgress")
        self.stage = QLabel("Ready")
        self.stage.setObjectName("SectionTitle")
        self.detail = QLabel("")
        self.detail.setObjectName("Muted")
        self.detail.setWordWrap(True)
        self.bar = QProgressBar()
        self.cancel_button = QPushButton(cancel_label)
        self.cancel_button.setObjectName("Danger")
        self.cancel_button.setEnabled(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING)
        layout.setSpacing(spacing.SM)
        layout.addWidget(self.stage)
        layout.addWidget(self.detail)
        layout.addWidget(self.bar)
        layout.addWidget(self.cancel_button)

    def set_running(self, running: bool) -> None:
        self.cancel_button.setEnabled(running)

    def set_event(self, event: ProgressEvent) -> None:
        self.bar.setValue(round(event.percent * 100))
        processed = ""
        if event.total_bytes is not None and event.processed_bytes is not None:
            processed = f" - {format_size(event.processed_bytes)} / {format_size(event.total_bytes)}"
        self.stage.setText(f"{event.stage} {round(event.percent * 100)}%")
        self.detail.setText(f"{event.detail}{processed}")

    def reset(self) -> None:
        self.bar.setValue(0)
        self.stage.setText("Ready")
        self.detail.clear()
