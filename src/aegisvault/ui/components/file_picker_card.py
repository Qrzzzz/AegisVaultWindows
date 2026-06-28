"""File selection and metadata preview card."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QFrame, QLabel, QPushButton, QVBoxLayout

from aegisvault.ui.design import spacing


class FilePickerCard(QFrame):
    file_selected = Signal(object)

    def __init__(self, select_label: str, empty_label: str, hint: str) -> None:
        super().__init__()
        self.setObjectName("FilePickerCard")
        self.select_button = QPushButton(select_label)
        self.select_button.clicked.connect(self._browse)
        self.title = QLabel(empty_label)
        self.title.setObjectName("SectionTitle")
        self.hint = QLabel(hint)
        self.hint.setObjectName("Muted")
        self.hint.setWordWrap(True)
        self.meta = QLabel("")
        self.meta.setObjectName("MetaLabel")
        self.meta.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING)
        layout.setSpacing(spacing.SM)
        layout.addWidget(self.title)
        layout.addWidget(self.hint)
        layout.addWidget(self.meta)
        layout.addWidget(self.select_button)

    def set_file(self, path: Path, labels: dict[str, str]) -> None:
        self.title.setText(path.name)
        self.meta.setText("\n".join(f"{key}: {value}" for key, value in labels.items()))

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.select_button.text())
        if path:
            self.file_selected.emit(Path(path))
