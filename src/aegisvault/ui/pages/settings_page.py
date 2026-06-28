"""Settings workspace."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from aegisvault.core.exceptions import FileIOError
from aegisvault.i18n.translator import Translator
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from aegisvault.ui.components.action_bar import ActionBar
from aegisvault.ui.components.card import Card
from aegisvault.ui.components.form_row import FormRow
from aegisvault.ui.components.inline_alert import InlineAlert
from aegisvault.ui.design import spacing
from aegisvault.ui.pages.common import muted, scroll_page


class SettingsPage(QWidget):
    settings_saved = Signal()
    recent_cleared = Signal()
    error = Signal(object, str)

    def __init__(self, translator: Translator, settings: AppSettings, store: SettingsStore) -> None:
        super().__init__()
        self.i18n = translator
        self.settings = settings
        self.store = store
        self.alert = InlineAlert()

        scroll, layout = scroll_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        layout.addWidget(self._build_general_card())
        layout.addWidget(self._build_output_card())
        layout.addWidget(self._build_compat_card())
        layout.addWidget(self._build_recent_card())
        layout.addWidget(self.alert)
        save = QPushButton(self.i18n.t("action.save"))
        save.setObjectName("Primary")
        save.clicked.connect(self.save)
        layout.addWidget(ActionBar(save))
        layout.addStretch(1)

    def _build_general_card(self) -> Card:
        card = Card("General")
        self.language_combo = QComboBox()
        self.language_combo.addItem("Chinese", "zh-CN")
        self.language_combo.addItem("English", "en-US")
        self.language_combo.setCurrentIndex(0 if self.settings.language == "zh-CN" else 1)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(self.i18n.t("settings.theme.dark"), "dark")
        self.theme_combo.addItem(self.i18n.t("settings.theme.light"), "light")
        self.theme_combo.addItem(self.i18n.t("settings.theme.system"), "system")
        self.theme_combo.setCurrentIndex({"dark": 0, "light": 1, "system": 2}.get(self.settings.theme, 0))
        card.content_layout.addWidget(FormRow(self.i18n.t("settings.language"), self.language_combo))
        card.content_layout.addWidget(FormRow(self.i18n.t("settings.theme"), self.theme_combo))
        return card

    def _build_output_card(self) -> Card:
        card = Card("Output")
        self.output_dir = QLineEdit(self.settings.default_output_dir)
        browse = QPushButton(self.i18n.t("action.browse"))
        browse.clicked.connect(self._browse_output_dir)
        output_row = QWidget()
        output_layout = QHBoxLayout(output_row)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(spacing.SM)
        output_layout.addWidget(self.output_dir, 1)
        output_layout.addWidget(browse)
        self.overwrite = QCheckBox(self.i18n.t("settings.overwrite"))
        self.overwrite.setChecked(self.settings.overwrite_outputs)
        card.content_layout.addWidget(FormRow(self.i18n.t("field.output_dir"), output_row))
        card.content_layout.addWidget(self.overwrite)
        return card

    def _build_compat_card(self) -> Card:
        card = Card("Legacy recovery and compatibility")
        self.advanced = QCheckBox(self.i18n.t("settings.advanced"))
        self.advanced.setChecked(self.settings.show_advanced_options)
        self.ak = QCheckBox(self.i18n.t("settings.ak"))
        self.ak.setChecked(self.settings.allow_ak_compatibility)
        card.content_layout.addWidget(self.advanced)
        card.content_layout.addWidget(self.ak)
        card.content_layout.addWidget(muted(self.i18n.t("settings.ak.note")))
        return card

    def _build_recent_card(self) -> Card:
        card = Card(self.i18n.t("settings.recent_files"))
        self.remember = QCheckBox(self.i18n.t("settings.recent"))
        self.remember.setChecked(self.settings.remember_recent_files)
        self.recent_list = QListWidget()
        self._refresh_recent()
        clear_recent = QPushButton(self.i18n.t("settings.clear_recent"))
        clear_recent.clicked.connect(self._clear_recent)
        card.content_layout.addWidget(self.remember)
        card.content_layout.addWidget(self.recent_list)
        card.content_layout.addWidget(ActionBar(clear_recent))
        return card

    def save(self) -> None:
        self.alert.clear()
        output_dir = self.output_dir.text().strip()
        if output_dir and not Path(output_dir).expanduser().is_dir():
            exc = FileIOError("Output directory does not exist.", code="file.output_dir_invalid")
            self.alert.show_error(self.i18n, exc)
            self.error.emit(exc, "")
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
