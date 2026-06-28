"""File selection card with output preview metadata."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QGridLayout, QLabel, QPushButton, QWidget

from aegisvault.ui.components.glass_card import GlassCard


class FileDropZone(GlassCard):
    file_selected = Signal(object)

    def __init__(self, select_text: str, empty_text: str, hint_text: str) -> None:
        super().__init__(object_name="DropZone")
        self.selected_path: Path | None = None
        self.empty_text = empty_text
        self.hint_text = hint_text
        self.title = QLabel(empty_text)
        self.title.setObjectName("PageTitle")
        self.hint = QLabel(hint_text)
        self.hint.setObjectName("Description")
        self.hint.setWordWrap(True)
        self.select_button = QPushButton(select_text)
        self.select_button.clicked.connect(self._browse)
        self.grid_holder = QWidget()
        self.grid = QGridLayout(self.grid_holder)
        self.grid.setContentsMargins(0, 4, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(6)
        self.rows: dict[str, QLabel] = {}
        self.content_layout.addWidget(self.title)
        self.content_layout.addWidget(self.hint)
        self.content_layout.addWidget(self.select_button)
        self.content_layout.addWidget(self.grid_holder)

    def set_texts(self, select_text: str, empty_text: str, hint_text: str) -> None:
        self.empty_text = empty_text
        self.hint_text = hint_text
        self.select_button.setText(select_text)
        if not self.selected_path:
            self.title.setText(empty_text)
            self.hint.setText(hint_text)

    def set_file(self, path: Path, labels: dict[str, str]) -> None:
        self.selected_path = path
        self.title.setText(labels.get("name", path.name))
        self.hint.setText(labels.get("path", str(path)))
        self.hint.setToolTip(str(path))
        self._clear_rows()
        for row, (key, value) in enumerate(labels.items()):
            if key in {"name", "path"}:
                continue
            left = QLabel(key)
            left.setObjectName("Muted")
            right = QLabel(value)
            right.setObjectName("Muted")
            right.setWordWrap(True)
            self.grid.addWidget(left, row, 0)
            self.grid.addWidget(right, row, 1)

    def clear(self) -> None:
        self.selected_path = None
        self.title.setText(self.empty_text)
        self.hint.setText(self.hint_text)
        self.hint.setToolTip("")
        self._clear_rows()

    def _browse(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(self, self.select_button.text())
        if path:
            self.file_selected.emit(Path(path))

    def _clear_rows(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget:
                widget.deleteLater()


