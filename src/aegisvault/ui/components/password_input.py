"""Password input with a show/hide toggle."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from aegisvault.ui.components.form_row import FormRow
from aegisvault.ui.design import spacing


class PasswordInput(QWidget):
    def __init__(self, label: str, placeholder: str, show_label: str, hide_label: str) -> None:
        super().__init__()
        self.show_label = show_label
        self.hide_label = hide_label
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setPlaceholderText(placeholder)
        self.toggle = QPushButton(show_label)
        self.toggle.clicked.connect(self._toggle)
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(spacing.SM)
        row_layout.addWidget(self.edit, 1)
        row_layout.addWidget(self.toggle)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(FormRow(label, row))

    def text(self) -> str:
        return self.edit.text()

    def clear(self) -> None:
        self.edit.clear()

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802
        super().setEnabled(enabled)
        self.edit.setEnabled(enabled)
        self.toggle.setEnabled(enabled)

    def _toggle(self) -> None:
        visible = self.edit.echoMode() == QLineEdit.EchoMode.Normal
        self.edit.setEchoMode(QLineEdit.EchoMode.Password if visible else QLineEdit.EchoMode.Normal)
        self.toggle.setText(self.show_label if visible else self.hide_label)
