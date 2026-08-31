"""Simple framed content block."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from aegisvault.ui.design import spacing


class Card(QFrame):
    def __init__(self, title: str = "", description: str = "") -> None:
        super().__init__()
        self.setObjectName("Card")
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(
            spacing.CARD_PADDING,
            spacing.CARD_PADDING,
            spacing.CARD_PADDING,
            spacing.CARD_PADDING,
        )
        self.content_layout.setSpacing(spacing.MD)
        self.title_label = QLabel()
        self.title_label.setObjectName("SectionTitle")
        self.description_label = QLabel()
        self.description_label.setObjectName("Description")
        self.description_label.setWordWrap(True)
        self.content_layout.addWidget(self.title_label)
        self.content_layout.addWidget(self.description_label)
        self.set_title(title)
        self.set_description(description)

    def set_title(self, text: str) -> None:
        self.title_label.setText(text)
        self.title_label.setVisible(bool(text))
        self.title_label.setAccessibleName(text)

    def set_description(self, text: str) -> None:
        self.description_label.setText(text)
        self.description_label.setVisible(bool(text))
