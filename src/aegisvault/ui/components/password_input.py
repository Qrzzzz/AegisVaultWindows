"""Password input with accessible show/hide control and live relabeling."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from aegisvault.ui.icons import icon


class PasswordInput(QWidget):
    def __init__(self, label: str, placeholder: str, show_label: str, hide_label: str) -> None:
        super().__init__()
        self.show_label = show_label
        self.hide_label = hide_label
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setPlaceholderText(placeholder)
        self.edit.setAccessibleName(label)
        self.toggle = QPushButton()
        self.toggle.setIconSize(QSize(18, 18))
        self.toggle.setFixedWidth(36)
        self.toggle.setAccessibleName(show_label)
        self.toggle.clicked.connect(self._toggle)
        self.label = QLabel(label)
        self.label.setBuddy(self.edit)
        self.field = QWidget()
        self.field.setObjectName("PasswordRow")
        self.field.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        row = QHBoxLayout(self.field)
        row.setContentsMargins(0, 0, 2, 0)
        row.setSpacing(0)
        row.addWidget(self.edit, 1)
        row.addWidget(self.toggle)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(9)
        layout.addWidget(self.label)
        layout.addWidget(self.field)
        self._update_toggle()

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
        self._update_toggle()

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802
        super().setEnabled(enabled)
        self.edit.setEnabled(enabled)
        self.toggle.setEnabled(enabled)

    def _toggle(self) -> None:
        visible = self.edit.echoMode() == QLineEdit.EchoMode.Normal
        self.edit.setEchoMode(QLineEdit.EchoMode.Password if visible else QLineEdit.EchoMode.Normal)
        self._update_toggle()

    def _update_toggle(self) -> None:
        visible = self.edit.echoMode() == QLineEdit.EchoMode.Normal
        text = self.hide_label if visible else self.show_label
        self.toggle.setAccessibleName(f"{text} {self.label.text()}")
        self.toggle.setToolTip(text)
        self.toggle.setIcon(icon("eye-off" if visible else "eye"))

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange and hasattr(self, "toggle"):
            self._update_toggle()


class PasswordPair(QWidget):
    """Stack at narrow widths or large font sizes without shrinking labels."""

    def __init__(self, password: PasswordInput, confirmation: PasswordInput, hint: QLabel) -> None:
        super().__init__()
        self.password = password
        self.confirmation = confirmation
        self.row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.row.setSpacing(18)
        self.row.addWidget(password, 1)
        self.row.addWidget(confirmation, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(9)
        layout.addLayout(self.row)
        layout.addWidget(hint)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        threshold = max(470, self.fontMetrics().horizontalAdvance("Confirm password") * 3)
        self.row.setDirection(QBoxLayout.Direction.TopToBottom if self.width() < threshold else QBoxLayout.Direction.LeftToRight)
