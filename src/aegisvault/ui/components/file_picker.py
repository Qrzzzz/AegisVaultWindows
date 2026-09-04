"""A path row with browse, concise metadata and guarded file drops."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from aegisvault.ui.icons import icon


class FilePicker(QWidget):
    file_selected = Signal(object)

    def __init__(self, select_label: str, empty_label: str, hint: str) -> None:
        super().__init__()
        self.setObjectName("FilePicker")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAcceptDrops(True)
        self._enabled_for_input = True
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setProperty("outputPath", True)
        self.select_button = QPushButton()
        self.select_button.clicked.connect(self._browse)
        self.meta = QLabel()
        self.meta.setProperty("muted", True)
        self.meta.setTextFormat(Qt.TextFormat.PlainText)
        self.meta.setWordWrap(True)
        self.meta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.symbol = QLabel()
        self.symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.symbol.setPixmap(icon("upload").pixmap(30, 30))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(self.symbol)
        layout.addWidget(self.hint)
        layout.addWidget(self.path_edit)
        layout.addWidget(self.meta)
        layout.addWidget(self.select_button, alignment=Qt.AlignmentFlag.AlignHCenter)
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
        self.path_edit.setToolTip(str(path))
        self.path_edit.setCursorPosition(len(str(path)))
        # The full path is already selectable above; don't repeat it in metadata.
        self.meta.setText(" · ".join(f"{key}: {value}" for key, value in labels.items() if value != str(path)))
        self.meta.setVisible(bool(self.meta.text()))
        self.path_edit.show()
        self.symbol.hide()
        self.hint.hide()

    def clear(self) -> None:
        self.path_edit.clear()
        self.path_edit.setToolTip("")
        self.path_edit.hide()
        self.symbol.show()
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
        path, _ = QFileDialog.getOpenFileName(self, self.select_button.text())
        if path:
            self.file_selected.emit(Path(path))

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange and hasattr(self, "symbol"):
            self.symbol.setPixmap(icon("upload").pixmap(30, 30))
