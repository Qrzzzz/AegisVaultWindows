"""Simple framed content block."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from aegisvault.ui.design import spacing


class Card(QFrame):
    def __init__(self, title: str = "", description: str = "") -> None:
        super().__init__()
        self.setObjectName("Card")
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING)
        self.content_layout.setSpacing(spacing.MD)
        if title:
            label = QLabel(title)
            label.setObjectName("SectionTitle")
            self.content_layout.addWidget(label)
        if description:
            desc = QLabel(description)
            desc.setObjectName("Description")
            desc.setWordWrap(True)
            self.content_layout.addWidget(desc)
