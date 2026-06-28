"""Glass-style card container."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout


class GlassCard(QFrame):
    def __init__(self, *, object_name: str = "Card", margins: tuple[int, int, int, int] = (22, 22, 22, 22)) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(*margins)
        self.content_layout.setSpacing(14)


