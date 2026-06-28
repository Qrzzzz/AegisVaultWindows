"""About dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from aegisvault import __license__, __version__
from aegisvault.i18n.translator import Translator


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget, translator: Translator) -> None:
        super().__init__(parent)
        self.i18n = translator
        self.setWindowTitle(self.i18n.t("about.title"))
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        title = QLabel(self.i18n.t("about.title"))
        title.setObjectName("PageTitle")
        body = QLabel(self.i18n.t("about.body"))
        body.setWordWrap(True)
        body.setObjectName("Description")
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(QLabel(self.i18n.t("about.version", version=__version__)))
        layout.addWidget(QLabel(self.i18n.t("about.license", license=__license__)))
        layout.addWidget(QLabel(self.i18n.t("about.repo")))
        layout.addWidget(QLabel(self.i18n.t("about.migration")))
        close = QPushButton("OK")
        close.clicked.connect(self.accept)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self.setStyleSheet(parent.styleSheet())


