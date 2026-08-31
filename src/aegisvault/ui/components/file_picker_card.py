"""Accessible file picker with direct drag-and-drop support."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFileDialog, QFrame, QLabel, QPushButton, QVBoxLayout

from aegisvault.ui.design import spacing


class FilePickerCard(QFrame):
    file_selected = Signal(object)

    def __init__(self, select_label: str, empty_label: str, hint: str) -> None:
        super().__init__()
        self.setObjectName("FilePickerCard")
        self.setAcceptDrops(True)
        self._enabled_for_input = True
        self._empty_label = empty_label
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
        layout.setContentsMargins(
            spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING
        )
        layout.setSpacing(spacing.SM)
        layout.addWidget(self.title)
        layout.addWidget(self.hint)
        layout.addWidget(self.meta)
        layout.addWidget(self.select_button)
        self.set_texts(select_label, empty_label, hint)

    def set_texts(self, select_label: str, empty_label: str, hint: str) -> None:
        showing_empty = not self.meta.text()
        self._empty_label = empty_label
        self.select_button.setText(select_label)
        self.select_button.setAccessibleName(select_label)
        self.hint.setText(hint)
        if showing_empty:
            self.title.setText(empty_label)
        self.setAccessibleName(hint)

    def set_file(self, path: Path, labels: dict[str, str]) -> None:
        self.title.setText(path.name)
        self.title.setAccessibleName(path.name)
        self.meta.setText("\n".join(f"{key}: {value}" for key, value in labels.items()))

    def clear(self) -> None:
        self.title.setText(self._empty_label)
        self.meta.clear()

    def set_input_enabled(self, enabled: bool) -> None:
        self._enabled_for_input = enabled
        self.select_button.setEnabled(enabled)
        self.setAcceptDrops(enabled)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._enabled_for_input and any(Path(url.toLocalFile()).is_file() for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        if not self._enabled_for_input:
            event.ignore()
            return
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_file():
                self.file_selected.emit(path)
                event.acceptProposedAction()
                return
        event.ignore()

    def _browse(self) -> None:
        if not self._enabled_for_input:
            return
        path, _ = QFileDialog.getOpenFileName(self, self.select_button.text())
        if path:
            self.file_selected.emit(Path(path))
