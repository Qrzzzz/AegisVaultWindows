"""About dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from aegisvault import __license__, __version__
from aegisvault.i18n.translator import Translator
from aegisvault.ui.light import ensure_light_appearance


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget, translator: Translator) -> None:
        super().__init__(parent)
        ensure_light_appearance()
        self.i18n = translator
        self.setWindowTitle(self.i18n.t("about.title"))
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        body = QLabel(self.i18n.t("about.body"))
        body.setWordWrap(True)
        body.setAccessibleName(self.i18n.t("about.title"))
        layout.addWidget(body)
        layout.addWidget(QLabel(self.i18n.t("about.version", version=__version__)))
        layout.addWidget(QLabel(self.i18n.t("about.license", license=__license__)))
        layout.addWidget(QLabel(self.i18n.t("about.repo")))
        layout.addWidget(QLabel(self.i18n.t("about.migration")))
        close = QPushButton(self.i18n.t("action.close"))
        close.setAccessibleName(self.i18n.t("action.close"))
        close.clicked.connect(self.accept)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
