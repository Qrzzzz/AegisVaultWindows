"""Reusable result panel with copy and reveal actions."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QTextEdit

from aegisvault.ui.components.glass_card import GlassCard


class ResultPanel(GlassCard):
    reveal_requested = Signal(object)

    def __init__(self, copy_text: str, reveal_text: str, clear_text: str, placeholder: str = "") -> None:
        super().__init__(object_name="ResultCard")
        self.output_path: Path | None = None
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlaceholderText(placeholder)
        self.text.setMinimumHeight(118)
        self.copy_button = QPushButton(copy_text)
        self.reveal_button = QPushButton(reveal_text)
        self.clear_button = QPushButton(clear_text)
        self.reveal_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_text)
        self.clear_button.clicked.connect(self.clear)
        self.reveal_button.clicked.connect(lambda: self.reveal_requested.emit(self.output_path))
        buttons = QHBoxLayout()
        buttons.addWidget(self.copy_button)
        buttons.addWidget(self.reveal_button)
        buttons.addStretch(1)
        buttons.addWidget(self.clear_button)
        self.content_layout.addWidget(self.text)
        self.content_layout.addLayout(buttons)

    def set_texts(self, copy_text: str, reveal_text: str, clear_text: str) -> None:
        self.copy_button.setText(copy_text)
        self.reveal_button.setText(reveal_text)
        self.clear_button.setText(clear_text)

    def set_result(self, text: str, output_path: Path | None = None) -> None:
        self.text.setPlainText(text)
        self.output_path = output_path
        self.reveal_button.setEnabled(output_path is not None)

    def copy_text(self) -> None:
        content = self.text.toPlainText()
        if content:
            QApplication.clipboard().setText(content)
            original = self.copy_button.text()
            self.copy_button.setText("Copied")
            self.copy_button.setEnabled(False)
            QTimer.singleShot(1200, lambda: self._restore_copy_button(original))

    def clear(self) -> None:
        self.text.clear()
        self.output_path = None
        self.reveal_button.setEnabled(False)

    def _restore_copy_button(self, text: str) -> None:
        self.copy_button.setText(text)
        self.copy_button.setEnabled(True)

