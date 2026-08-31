"""Read-only text result with copy, clear, and use-as-input actions."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout

from aegisvault.ui.design import spacing


class OutputPreview(QFrame):
    use_as_input_requested = Signal()
    swap_requested = Signal()

    def __init__(self, copy_label: str, clear_label: str, use_as_input_label: str) -> None:
        super().__init__()
        self.setObjectName("OutputPreview")
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.copy_button = QPushButton(copy_label)
        self.clear_button = QPushButton(clear_label)
        self.use_as_input_button = QPushButton(use_as_input_label)
        self.swap_button = self.use_as_input_button
        self.copy_button.clicked.connect(self.copy)
        self.clear_button.clicked.connect(self.clear)
        self.use_as_input_button.clicked.connect(self._use_as_input)
        self.editor.textChanged.connect(self._sync_actions)
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.copy_button)
        actions.addWidget(self.clear_button)
        actions.addWidget(self.use_as_input_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING
        )
        layout.setSpacing(spacing.SM)
        layout.addWidget(self.editor)
        layout.addLayout(actions)
        self.set_texts(copy_label, clear_label, use_as_input_label)
        self._sync_actions()

    def set_texts(self, copy_label: str, clear_label: str, use_as_input_label: str, placeholder: str = "") -> None:
        self.copy_button.setText(copy_label)
        self.copy_button.setAccessibleName(copy_label)
        self.clear_button.setText(clear_label)
        self.clear_button.setAccessibleName(clear_label)
        self.use_as_input_button.setText(use_as_input_label)
        self.use_as_input_button.setAccessibleName(use_as_input_label)
        self.editor.setPlaceholderText(placeholder)

    def set_accessible_name(self, text: str) -> None:
        self.editor.setAccessibleName(text)

    def set_text(self, text: str) -> None:
        self.editor.setPlainText(text)

    def text(self) -> str:
        return self.editor.toPlainText()

    def clear(self) -> None:
        self.editor.clear()

    def copy(self) -> None:
        QApplication.clipboard().setText(self.editor.toPlainText())

    def _use_as_input(self) -> None:
        self.use_as_input_requested.emit()
        self.swap_requested.emit()

    def _sync_actions(self) -> None:
        has_text = bool(self.editor.toPlainText())
        self.copy_button.setEnabled(has_text)
        self.clear_button.setEnabled(has_text)
        self.use_as_input_button.setEnabled(has_text)
