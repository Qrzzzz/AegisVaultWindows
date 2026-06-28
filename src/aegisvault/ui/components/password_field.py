"""Password input with visibility toggle and strength hint."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QProgressBar, QToolButton, QVBoxLayout, QWidget


class PasswordField(QWidget):
    def __init__(self, label: str, placeholder: str, show_text: str, hide_text: str) -> None:
        super().__init__()
        self.show_text = show_text
        self.hide_text = hide_text
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(label)
        self.label.setObjectName("Muted")
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setPlaceholderText(placeholder)
        self.toggle = QToolButton()
        self.toggle.setText(show_text)
        self.toggle.clicked.connect(self._toggle)
        row.addWidget(self.label)
        row.addWidget(self.edit, 1)
        row.addWidget(self.toggle)
        self.strength = QProgressBar()
        self.strength.setObjectName("StrengthBar")
        self.strength.setRange(0, 100)
        self.strength.setValue(0)
        self.hint = QLabel("")
        self.hint.setObjectName("Muted")
        self.edit.textChanged.connect(self._update_strength)
        outer.addLayout(row)
        outer.addWidget(self.strength)
        outer.addWidget(self.hint)

    def text(self) -> str:
        return self.edit.text()

    def set_texts(self, label: str, placeholder: str, show_text: str, hide_text: str) -> None:
        self.label.setText(label)
        self.edit.setPlaceholderText(placeholder)
        self.show_text = show_text
        self.hide_text = hide_text
        self.toggle.setText(hide_text if self.edit.echoMode() == QLineEdit.EchoMode.Normal else show_text)

    def _toggle(self) -> None:
        visible = self.edit.echoMode() == QLineEdit.EchoMode.Normal
        self.edit.setEchoMode(QLineEdit.EchoMode.Password if visible else QLineEdit.EchoMode.Normal)
        self.toggle.setText(self.show_text if visible else self.hide_text)

    def _update_strength(self, value: str) -> None:
        score = min(100, len(value) * 5)
        categories = [any(ch.islower() for ch in value), any(ch.isupper() for ch in value), any(ch.isdigit() for ch in value), any(not ch.isalnum() for ch in value)]
        score += sum(categories) * 10
        if len(value) >= 16:
            score += 10
        self.strength.setValue(min(100, score))
        self.hint.setText("")


