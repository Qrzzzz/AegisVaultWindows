"""Settings dialog with dangerous options in a collapsed advanced section."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QToolButton,
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


class SettingsDialog(QDialog):
    settings_saved = Signal()
    recent_cleared = Signal()
    error = Signal(object, str)

    def __init__(
        self,
        translator: Translator,
        settings: AppSettings,
        store: SettingsStore,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsDialog")
        self.i18n = translator
        self.settings = settings
        self.store = store
        self._recent_files = list(settings.recent_files)
        self._recent_was_cleared = False
        self.setModal(True)
        self.resize(680, 720)
        self.setMinimumSize(580, 600)

        self.alert = InlineAlert()
        self.general_card = self._build_general_card()
        self.output_card = self._build_output_card()
        self.recent_card = self._build_recent_card()
        self.advanced_toggle = QToolButton()
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advanced_toggle.setChecked(self.settings.show_advanced_options)
        self.advanced_toggle.toggled.connect(self._toggle_advanced)
        self.advanced_panel = self._build_advanced_panel()
        self.advanced_panel.setVisible(self.advanced_toggle.isChecked())

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.save)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(spacing.XL, spacing.XL, spacing.XL, spacing.XL)
        layout.setSpacing(spacing.MD)
        layout.addWidget(self.general_card)
        layout.addWidget(self.output_card)
        layout.addWidget(self.recent_card)
        layout.addWidget(self.advanced_toggle)
        layout.addWidget(self.advanced_panel)
        layout.addWidget(self.alert)
        layout.addStretch(1)
        layout.addWidget(self.buttons)
        self.retranslate_ui()

    def _build_general_card(self) -> Card:
        card = Card()
        self.language_combo = QComboBox()
        self.language_combo.addItem("", "zh-CN")
        self.language_combo.addItem("", "en-US")
        self.language_combo.setCurrentIndex(0 if self.settings.language == "zh-CN" else 1)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("", "dark")
        self.theme_combo.addItem("", "light")
        self.theme_combo.addItem("", "system")
        self.theme_combo.setCurrentIndex({"dark": 0, "light": 1, "system": 2}.get(self.settings.theme, 0))
        self.language_row = FormRow("", self.language_combo)
        self.theme_row = FormRow("", self.theme_combo)
        card.content_layout.addWidget(self.language_row)
        card.content_layout.addWidget(self.theme_row)
        return card

    def _build_output_card(self) -> Card:
        card = Card()
        self.output_dir = QLineEdit(self.settings.default_output_dir)
        self.browse_button = QPushButton()
        self.browse_button.clicked.connect(self._browse_output_dir)
        output_row = QWidget()
        output_layout = QHBoxLayout(output_row)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(spacing.SM)
        output_layout.addWidget(self.output_dir, 1)
        output_layout.addWidget(self.browse_button)
        self.output_dir_row = FormRow("", output_row)
        card.content_layout.addWidget(self.output_dir_row)
        return card

    def _build_recent_card(self) -> Card:
        card = Card()
        self.remember = QCheckBox()
        self.remember.setChecked(self.settings.remember_recent_files)
        self.recent_list = QListWidget()
        self.recent_list.setAccessibleName(self.i18n.t("settings.recent_files"))
        self.clear_recent_button = QPushButton()
        self.clear_recent_button.clicked.connect(self._clear_recent)
        card.content_layout.addWidget(self.remember)
        card.content_layout.addWidget(self.recent_list)
        card.content_layout.addWidget(ActionBar(self.clear_recent_button))
        self._refresh_recent()
        return card

    def _build_advanced_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("AdvancedPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING, spacing.CARD_PADDING
        )
        layout.setSpacing(spacing.MD)
        self.overwrite = QCheckBox()
        self.overwrite.setChecked(self.settings.overwrite_outputs)
        self.overwrite_note = QFrame()
        overwrite_note_layout = QVBoxLayout(self.overwrite_note)
        overwrite_note_layout.setContentsMargins(0, 0, 0, 0)
        self.overwrite_warning = QLabel()
        self.overwrite_warning.setObjectName("WarningText")
        self.overwrite_warning.setWordWrap(True)
        overwrite_note_layout.addWidget(self.overwrite_warning)
        self.ak = QCheckBox()
        self.ak.setChecked(self.settings.allow_ak_compatibility)
        self.ak_warning = QLabel()
        self.ak_warning.setObjectName("WarningText")
        self.ak_warning.setWordWrap(True)
        layout.addWidget(self.overwrite)
        layout.addWidget(self.overwrite_note)
        layout.addWidget(self.ak)
        layout.addWidget(self.ak_warning)
        return panel

    def retranslate_ui(self) -> None:
        self.setWindowTitle(self.i18n.t("settings.title"))
        self.setAccessibleName(self.i18n.t("settings.title"))
        self.general_card.set_title(self.i18n.t("settings.general"))
        self.output_card.set_title(self.i18n.t("settings.output"))
        self.recent_card.set_title(self.i18n.t("settings.recent_files"))
        self.language_combo.setItemText(0, self.i18n.t("settings.language.zh"))
        self.language_combo.setItemText(1, self.i18n.t("settings.language.en"))
        self.theme_combo.setItemText(0, self.i18n.t("settings.theme.dark"))
        self.theme_combo.setItemText(1, self.i18n.t("settings.theme.light"))
        self.theme_combo.setItemText(2, self.i18n.t("settings.theme.system"))
        self.language_row.set_label(self.i18n.t("settings.language"))
        self.theme_row.set_label(self.i18n.t("settings.theme"))
        self.output_dir_row.set_label(self.i18n.t("field.output_dir"))
        self.output_dir.setAccessibleName(self.i18n.t("field.output_dir"))
        self.output_dir.setPlaceholderText(self.i18n.t("settings.output_same_folder"))
        self.browse_button.setText(self.i18n.t("action.browse"))
        self.browse_button.setAccessibleName(self.i18n.t("action.browse"))
        self.remember.setText(self.i18n.t("settings.recent"))
        self.clear_recent_button.setText(self.i18n.t("settings.clear_recent"))
        self.clear_recent_button.setAccessibleName(self.i18n.t("settings.clear_recent"))
        self.advanced_toggle.setText(self.i18n.t("settings.advanced"))
        self.advanced_toggle.setAccessibleName(self.i18n.t("settings.advanced"))
        self.overwrite.setText(self.i18n.t("settings.overwrite"))
        self.overwrite_warning.setText(self.i18n.t("settings.overwrite.note"))
        self.ak.setText(self.i18n.t("settings.ak"))
        self.ak_warning.setText(self.i18n.t("settings.ak.note"))
        save = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        save.setText(self.i18n.t("action.save"))
        cancel.setText(self.i18n.t("action.cancel"))
        save.setAccessibleName(save.text())
        cancel.setAccessibleName(cancel.text())
        self._refresh_recent()
        self._toggle_advanced(self.advanced_toggle.isChecked())

    def save(self) -> None:
        self.alert.clear()
        output_dir = self.output_dir.text().strip()
        if output_dir and not Path(output_dir).expanduser().is_dir():
            exc = FileIOError("Output directory does not exist.", code="file.output_dir_invalid")
            self.alert.show_error(self.i18n, exc)
            self.alert.setFocus(Qt.FocusReason.OtherFocusReason)
            self.error.emit(exc, "")
            return
        self.settings.language = str(self.language_combo.currentData())
        self.settings.theme = str(self.theme_combo.currentData())
        self.settings.default_output_dir = output_dir
        self.settings.overwrite_outputs = self.overwrite.isChecked()
        self.settings.remember_recent_files = self.remember.isChecked()
        self.settings.show_advanced_options = self.advanced_toggle.isChecked()
        self.settings.allow_ak_compatibility = self.ak.isChecked()
        self.settings.recent_files = list(self._recent_files)
        self.store.save(self.settings)
        if self._recent_was_cleared:
            self.recent_cleared.emit()
        self.settings_saved.emit()
        self.accept()

    def _toggle_advanced(self, expanded: bool) -> None:
        self.advanced_toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.advanced_panel.setVisible(expanded)

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, self.i18n.t("field.output_dir"))
        if path:
            self.output_dir.setText(path)

    def _clear_recent(self) -> None:
        self._recent_files = []
        self._recent_was_cleared = True
        self._refresh_recent()

    def _refresh_recent(self) -> None:
        self.recent_list.clear()
        if not self._recent_files:
            self.recent_list.addItem(self.i18n.t("settings.no_recent"))
            return
        for item in self._recent_files:
            self.recent_list.addItem(item)


# Transitional import compatibility for integrations that imported the old page.
SettingsPage = SettingsDialog
