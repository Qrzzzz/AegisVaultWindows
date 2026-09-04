"""Password input with accessible show/hide control and live relabeling."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget


class PasswordInput(QWidget):
    def __init__(self, label: str, placeholder: str, show_label: str, hide_label: str) -> None:
        super().__init__()
        self.show_label = show_label
        self.hide_label = hide_label
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setPlaceholderText(placeholder)
        self.edit.setAccessibleName(label)
        self.toggle = QPushButton(show_label)
        self.toggle.setAccessibleName(show_label)
        self.toggle.clicked.connect(self._toggle)
        self.label = QLabel(label)
        self.label.setBuddy(self.edit)
        self.row = layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.toggle)

    def add_to_form(self, form: QFormLayout) -> None:
        """Let the shared form align labels without imposing a fixed width."""
        self.row.removeWidget(self.label)
        form.addRow(self.label, self)

    def text(self) -> str:
        return self.edit.text()

    def clear(self) -> None:
        self.edit.clear()

    def set_texts(self, label: str, placeholder: str, show_label: str, hide_label: str) -> None:
        self.show_label = show_label
        self.hide_label = hide_label
        self.label.setText(label)
        self.edit.setAccessibleName(label)
        self.edit.setPlaceholderText(placeholder)
        visible = self.edit.echoMode() == QLineEdit.EchoMode.Normal
        self.toggle.setText(hide_label if visible else show_label)
        self.toggle.setAccessibleName(self.toggle.text())

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802
        super().setEnabled(enabled)
        self.edit.setEnabled(enabled)
        self.toggle.setEnabled(enabled)

    def _toggle(self) -> None:
        visible = self.edit.echoMode() == QLineEdit.EchoMode.Normal
        self.edit.setEchoMode(QLineEdit.EchoMode.Password if visible else QLineEdit.EchoMode.Normal)
        self.toggle.setText(self.show_label if visible else self.hide_label)
        self.toggle.setAccessibleName(self.toggle.text())
