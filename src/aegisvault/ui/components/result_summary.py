"""File task result summary with reveal and clear actions."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout


class ResultSummary(QGroupBox):
    content_changed = Signal()
    reveal_requested = Signal(object)

    def __init__(self, open_label: str, clear_label: str) -> None:
        super().__init__()
        self.setObjectName("ResultSummary")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.output_path: Path | None = None
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.open_button = QPushButton(open_label)
        self.clear_button = QPushButton(clear_label)
        self.open_button.clicked.connect(self._reveal)
        self.clear_button.clicked.connect(self.clear)
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.open_button)
        actions.addWidget(self.clear_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self.label)
        layout.addLayout(actions)
        self.set_texts(open_label, clear_label)
        self.clear()

    def set_texts(self, open_label: str, clear_label: str) -> None:
        self.open_button.setText(open_label)
        self.open_button.setAccessibleName(open_label)
        self.clear_button.setText(clear_label)
        self.clear_button.setAccessibleName(clear_label)

    def set_result(self, text: str, output_path: Path | None = None) -> None:
        self.output_path = output_path
        self.label.setText(text)
        self.setAccessibleName(text)
        self.open_button.setVisible(output_path is not None)
        self.show()
        self.content_changed.emit()

    def clear(self) -> None:
        self.output_path = None
        self.label.clear()
        self.setAccessibleName("")
        self.open_button.hide()
        self.hide()
        self.content_changed.emit()

    def _reveal(self) -> None:
        if self.output_path is not None:
            self.reveal_requested.emit(self.output_path)
