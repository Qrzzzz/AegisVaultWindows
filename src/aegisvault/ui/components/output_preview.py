"""Read-only text result with copy, clear, and use-as-input actions."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
)

from aegisvault.ui.pages.common import AdaptiveRow, Section


class OutputPreview(Section):
    content_changed = Signal()
    use_as_input_requested = Signal()
    swap_requested = Signal()

    def __init__(self, copy_label: str, clear_label: str, use_as_input_label: str) -> None:
        super().__init__()
        self._busy = False
        self.setObjectName("OutputPreview")
        self.setProperty("card", True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.editor = QPlainTextEdit()
        self.editor.setTabChangesFocus(True)
        self.editor.setReadOnly(True)
        self.editor.setMinimumHeight(90)
        self.editor.setMaximumHeight(90)
        self.editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.copy_button = QPushButton(copy_label)
        self.clear_button = QPushButton(clear_label)
        self.use_as_input_button = QPushButton(use_as_input_label)
        self.swap_button = self.use_as_input_button
        self.copy_button.clicked.connect(self.copy)
        self.clear_button.clicked.connect(self.clear)
        self.use_as_input_button.clicked.connect(self._use_as_input)
        self.editor.textChanged.connect(self._sync_actions)
        self.clear_button.setProperty("quiet", True)
        self.use_as_input_button.setProperty("quiet", True)
        actions = AdaptiveRow(self.copy_button, self.use_as_input_button, self.clear_button)
        layout = self.outer
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(self.editor)
        layout.addWidget(actions)
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

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._sync_actions()

    def _sync_actions(self) -> None:
        has_text = bool(self.editor.toPlainText())
        self.copy_button.setEnabled(has_text)
        self.clear_button.setEnabled(has_text and not self._busy)
        self.use_as_input_button.setEnabled(has_text and not self._busy)
        self.setVisible(has_text)
        self.content_changed.emit()
