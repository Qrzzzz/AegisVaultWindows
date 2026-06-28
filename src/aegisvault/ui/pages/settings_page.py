"""Settings workspace."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QWidget,
)

from aegisvault.i18n.translator import Translator
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from aegisvault.ui.components.glass_card import GlassCard
from aegisvault.ui.pages.common import muted, page_header, scroll_page


class SettingsPage(QWidget):
    settings_saved = Signal()
    recent_cleared = Signal()
    error = Signal(object, str)

    def __init__(self, translator: Translator, settings: AppSettings, store: SettingsStore) -> None:
        super().__init__()
        self.i18n = translator
        self.settings = settings
        self.store = store
        scroll, layout = scroll_page()
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        layout.addWidget(page_header(self.i18n.t("settings.title"), self.i18n.t("settings.description")))
        card = GlassCard()
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)
        self.language_combo = QComboBox()
        self.language_combo.addItem("涓枃", "zh-CN")
        self.language_combo.addItem("English", "en-US")
        self.language_combo.setCurrentIndex(0 if self.settings.language == "zh-CN" else 1)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(self.i18n.t("settings.theme.dark"), "dark")
        self.theme_combo.addItem(self.i18n.t("settings.theme.light"), "light")
        self.theme_combo.addItem(self.i18n.t("settings.theme.system"), "system")
        self.theme_combo.setCurrentIndex({"dark": 0, "light": 1, "system": 2}.get(self.settings.theme, 0))
        self.output_dir = QLineEdit(self.settings.default_output_dir)
        browse = QPushButton(self.i18n.t("action.browse"))
        browse.clicked.connect(self._browse_output_dir)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_dir, 1)
        output_row.addWidget(browse)
        self.overwrite = QCheckBox(self.i18n.t("settings.overwrite"))
        self.overwrite.setChecked(self.settings.overwrite_outputs)
        self.remember = QCheckBox(self.i18n.t("settings.recent"))
        self.remember.setChecked(self.settings.remember_recent_files)
        self.advanced = QCheckBox(self.i18n.t("settings.advanced"))
        self.advanced.setChecked(self.settings.show_advanced_options)
        self.ak = QCheckBox(self.i18n.t("settings.ak"))
        self.ak.setChecked(self.settings.allow_ak_compatibility)
        ak_note = QLabel(self.i18n.t("settings.ak.note"))
        ak_note.setObjectName("Muted")
        ak_note.setWordWrap(True)
        self.recent_list = QListWidget()
        self._refresh_recent()
        clear_recent = QPushButton(self.i18n.t("settings.clear_recent"))
        clear_recent.clicked.connect(self._clear_recent)
        save = QPushButton(self.i18n.t("action.save"))
        save.setObjectName("Primary")
        save.clicked.connect(self.save)
        grid.addWidget(muted(self.i18n.t("settings.language")), 0, 0)
        grid.addWidget(self.language_combo, 0, 1)
        grid.addWidget(muted(self.i18n.t("settings.theme")), 1, 0)
        grid.addWidget(self.theme_combo, 1, 1)
        grid.addWidget(muted(self.i18n.t("field.output_dir")), 2, 0)
        grid.addLayout(output_row, 2, 1)
        grid.addWidget(self.overwrite, 3, 1)
        grid.addWidget(self.remember, 4, 1)
        grid.addWidget(self.advanced, 5, 1)
        grid.addWidget(self.ak, 6, 1)
        grid.addWidget(ak_note, 7, 1)
        grid.addWidget(muted(self.i18n.t("settings.recent_files")), 8, 0)
        grid.addWidget(self.recent_list, 8, 1)
        grid.addWidget(clear_recent, 9, 1)
        grid.addWidget(save, 10, 1)
        card.content_layout.addLayout(grid)
        layout.addWidget(card)
        layout.addStretch(1)

    def save(self) -> None:
        output_dir = self.output_dir.text().strip()
        if output_dir and not Path(output_dir).expanduser().is_dir():
            from aegisvault.core.exceptions import FileIOError

            self.error.emit(FileIOError("Output directory does not exist.", code="file.output_dir_invalid"), "")
            return
        self.settings.language = str(self.language_combo.currentData())
        self.settings.theme = str(self.theme_combo.currentData())
        self.settings.default_output_dir = output_dir
        self.settings.overwrite_outputs = self.overwrite.isChecked()
        self.settings.remember_recent_files = self.remember.isChecked()
        self.settings.show_advanced_options = self.advanced.isChecked()
        self.settings.allow_ak_compatibility = self.ak.isChecked()
        self.store.save(self.settings)
        self.settings_saved.emit()

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, self.i18n.t("field.output_dir"))
        if path:
            self.output_dir.setText(path)

    def _clear_recent(self) -> None:
        self.settings.recent_files = []
        self.store.save(self.settings)
        self._refresh_recent()
        self.recent_cleared.emit()

    def _refresh_recent(self) -> None:
        self.recent_list.clear()
        if not self.settings.recent_files:
            self.recent_list.addItem(self.i18n.t("settings.no_recent"))
            return
        for item in self.settings.recent_files:
            self.recent_list.addItem(item)

