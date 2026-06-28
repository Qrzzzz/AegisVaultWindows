"""Output text area with copy, clear and swap controls."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout

from aegisvault.ui.design import spacing


class OutputPreview(QFrame):
    swap_requested = Signal()

    def __init__(self, copy_label: str, clear_label: str, swap_label: str = "Swap") -> None:
        super().__init__()
        self.setObjectName("OutputPreview")
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.copy_button = QPushButton(copy_label)
        self.clear_button = QPushButton(clear_label)
        self.swap_button = QPushButton(swap_label)
        self.copy_button.clicked.connect(self.copy)
        self.clear_button.clicked.connect(self.clear)
        self.swap_button.clicked.connect(self.swap_requested.emit)
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.copy_button)
        actions.addWidget(self.clear_button)
        actions.addWidget(self.swap_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING)
        layout.setSpacing(spacing.SM)
        layout.addWidget(self.editor)
        layout.addLayout(actions)

    def set_text(self, text: str) -> None:
        self.editor.setPlainText(text)

    def text(self) -> str:
        return self.editor.toPlainText()

    def clear(self) -> None:
        self.editor.clear()

    def copy(self) -> None:
        QApplication.clipboard().setText(self.editor.toPlainText())
