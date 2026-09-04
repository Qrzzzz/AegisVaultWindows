"""Native settings form with a genuinely collapsed advanced section."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
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
from aegisvault.ui.components.inline_alert import InlineAlert
from aegisvault.ui.light import ensure_light_appearance
from aegisvault.ui.pages.common import scroll_page


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
        ensure_light_appearance()
        self.i18n = translator
        self.settings = settings
        self.store = store
        self._recent_files = list(settings.recent_files)
        self._recent_was_cleared = False
        self.setModal(True)
        self.resize(620, 500)
        self.setMinimumSize(480, 380)

        self.language_combo = QComboBox()
        self.language_combo.addItem("", "zh-CN")
        self.language_combo.addItem("", "en-US")
        self.language_combo.setCurrentIndex(0 if settings.language == "zh-CN" else 1)
        self.language_label = QLabel()
        self.language_label.setBuddy(self.language_combo)
        self.output_dir = QLineEdit(settings.default_output_dir)
        self.output_label = QLabel()
        self.output_label.setBuddy(self.output_dir)
        self.browse_button = QPushButton()
        self.browse_button.clicked.connect(self._browse_output_dir)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_dir, 1)
        output_row.addWidget(self.browse_button)
        form = QFormLayout()
        form.addRow(self.language_label, self.language_combo)
        form.addRow(self.output_label, output_row)

        self.remember = QCheckBox()
        self.remember.setChecked(settings.remember_recent_files)
        self.recent_label = QLabel()
        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(60)
        self.recent_list.setMaximumHeight(120)
        self.clear_recent_button = QPushButton()
        self.clear_recent_button.clicked.connect(self._clear_recent)

        self.advanced_toggle = QToolButton()
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advanced_toggle.setChecked(settings.show_advanced_options)
        self.advanced_toggle.toggled.connect(self._toggle_advanced)
        self.advanced_panel = QWidget()
        advanced = QVBoxLayout(self.advanced_panel)
        advanced.setContentsMargins(0, 0, 0, 0)
        self.overwrite = QCheckBox()
        self.overwrite.setChecked(settings.overwrite_outputs)
        self.overwrite_warning = QLabel()
        self.overwrite_warning.setWordWrap(True)
        for widget in (self.overwrite, self.overwrite_warning):
            advanced.addWidget(widget)

        self.alert = InlineAlert()
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.save)
        self.buttons.rejected.connect(self.reject)
        scroll, content = scroll_page()
        content.addLayout(form)
        content.addWidget(self.remember)
        content.addWidget(self.recent_label)
        content.addWidget(self.recent_list)
        content.addWidget(self.clear_recent_button, alignment=Qt.AlignmentFlag.AlignLeft)
        content.addWidget(self.advanced_toggle, alignment=Qt.AlignmentFlag.AlignLeft)
        content.addWidget(self.advanced_panel)
        content.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll, 1)
        layout.addWidget(self.alert)
        layout.addWidget(self.buttons)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(self.i18n.t("settings.title"))
        self.setAccessibleName(self.windowTitle())
        self.language_combo.setItemText(0, self.i18n.t("settings.language.zh"))
        self.language_combo.setItemText(1, self.i18n.t("settings.language.en"))
        self.language_label.setText(self.i18n.t("settings.language"))
        self.language_combo.setAccessibleName(self.language_label.text())
        self.output_label.setText(self.i18n.t("field.output_dir"))
        self.output_dir.setAccessibleName(self.output_label.text())
        self.output_dir.setPlaceholderText(self.i18n.t("settings.output_same_folder"))
        self.browse_button.setText(self.i18n.t("action.browse"))
        self.remember.setText(self.i18n.t("settings.recent"))
        self.recent_label.setText(self.i18n.t("settings.recent_files"))
        self.recent_list.setAccessibleName(self.recent_label.text())
        self.clear_recent_button.setText(self.i18n.t("settings.clear_recent"))
        self.advanced_toggle.setText(self.i18n.t("settings.advanced"))
        self.overwrite.setText(self.i18n.t("settings.overwrite"))
        self.overwrite_warning.setText(self.i18n.t("settings.overwrite.note"))
        for button in (self.browse_button, self.clear_recent_button, self.advanced_toggle, self.overwrite):
            button.setAccessibleName(button.text())
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
        candidate = AppSettings(
            language=str(self.language_combo.currentData()),
            theme="light",
            default_output_dir=output_dir,
            overwrite_outputs=self.overwrite.isChecked(),
            remember_recent_files=self.remember.isChecked(),
            show_advanced_options=self.advanced_toggle.isChecked(),
            recent_files=list(self._recent_files),
        )
        try:
            self.store.save(candidate)
        except Exception as exc:
            self.alert.show_error(self.i18n, exc)
            self.alert.setFocus(Qt.FocusReason.OtherFocusReason)
            self.error.emit(exc, "")
            return

        self.settings.language = candidate.language
        self.settings.theme = candidate.theme
        self.settings.default_output_dir = candidate.default_output_dir
        self.settings.overwrite_outputs = candidate.overwrite_outputs
        self.settings.remember_recent_files = candidate.remember_recent_files
        self.settings.show_advanced_options = candidate.show_advanced_options
        self.settings.recent_files = list(candidate.recent_files)
        if self._recent_was_cleared:
            self.recent_cleared.emit()
        self.settings_saved.emit()
        self.accept()

    def _toggle_advanced(self, expanded: bool) -> None:
        self.advanced_toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.advanced_panel.setVisible(expanded)

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, self.i18n.t("field.output_dir"), options=QFileDialog.Option.DontUseNativeDialog
        )
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
        self.recent_list.addItems(self._recent_files)
