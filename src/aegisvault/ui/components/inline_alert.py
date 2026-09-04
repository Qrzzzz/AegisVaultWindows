"""Inline, keyboard-reachable error and warning banner."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from aegisvault.core.exceptions import AppError
from aegisvault.i18n.translator import Translator


class InlineAlert(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("InlineAlert")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel()
        self.label.setObjectName("InlineAlertText")
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.label)
        self.hide()

    def show_message(self, message: str) -> None:
        self.label.setText(message)
        self.setAccessibleName(message)
        self.show()

    def show_error(self, translator: Translator, exc: object) -> None:
        code = exc.code if isinstance(exc, AppError) else "generic"
        message = translator.t(f"error.{code}")
        if message == f"error.{code}":
            message = translator.t("error.generic")
        self.show_message(message)

    def clear(self) -> None:
        self.label.clear()
        self.setAccessibleName("")
        self.hide()
