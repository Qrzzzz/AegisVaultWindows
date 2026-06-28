"""Localized error dialog."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from aegisvault.core.exceptions import AppError, OperationCancelled
from aegisvault.i18n.translator import Translator


def show_error(parent: QWidget, translator: Translator, exc: object, diagnostic: str = "") -> None:
    if isinstance(exc, OperationCancelled):
        return
    code = exc.code if isinstance(exc, AppError) else "generic"
    message = translator.t(f"error.{code}")
    if message == f"error.{code}":
        message = translator.t("error.generic")
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(translator.t("error.title"))
    box.setText(message)
    if diagnostic:
        box.setDetailedText(diagnostic)
    box.exec()


