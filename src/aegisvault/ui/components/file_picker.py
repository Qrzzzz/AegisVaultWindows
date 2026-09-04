"""A path row with browse, concise metadata and guarded file drops."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class FilePicker(QWidget):
    file_selected = Signal(object)

    def __init__(self, select_label: str, empty_label: str, hint: str) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self._enabled_for_input = True
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.select_button = QPushButton()
        self.select_button.clicked.connect(self._browse)
        self.meta = QLabel()
        self.meta.setTextFormat(Qt.TextFormat.PlainText)
        self.meta.setWordWrap(True)
        self.meta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        row = QHBoxLayout()
        row.addWidget(self.path_edit, 1)
        row.addWidget(self.select_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self.hint)
        layout.addWidget(self.meta)
        self.set_texts(select_label, empty_label, hint)
        self.clear()

    def set_texts(self, select_label: str, empty_label: str, hint: str) -> None:
        self.select_button.setText(select_label)
        self.select_button.setAccessibleName(select_label)
        self.path_edit.setPlaceholderText(empty_label)
        self.path_edit.setAccessibleName(hint)
        self.hint.setText(hint)

    def set_file(self, path: Path, labels: dict[str, str]) -> None:
        self.path_edit.setText(str(path))
        self.path_edit.setCursorPosition(0)
        # The full path is already selectable above; don't repeat it in metadata.
        self.meta.setText(" · ".join(f"{key}: {value}" for key, value in labels.items() if value != str(path)))
        self.meta.setVisible(bool(self.meta.text()))
        self.hint.hide()

    def clear(self) -> None:
        self.path_edit.clear()
        self.meta.clear()
        self.meta.hide()
        self.hint.show()

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
        path, _ = QFileDialog.getOpenFileName(
            self, self.select_button.text(), options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            self.file_selected.emit(Path(path))
