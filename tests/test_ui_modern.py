"""Acceptance for the approved appearance and navigation changes."""

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest

from aegisvault.ui.pages.settings_page import SettingsDialog
from test_ui_basic_light import _window


def test_appearance_save_preserves_live_pages_and_unsaved_content(tmp_path: Path) -> None:
    app, window = _window(tmp_path)
    try:
        page = window.text_page
        page.input.setPlainText("Unsubmitted text / 尚未提交")
        page.password.edit.setText("synthetic-password")
        page.output.set_text("Retained result")
        identities = [id(window.tabs.widget(index)) for index in range(3)]
        for theme in ("dark", "light", "system"):
            dialog = SettingsDialog(window.i18n, window.settings, window.store, window)
            dialog.settings_saved.connect(window._settings_saved)
            dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData(theme))
            dialog.save()
            QTest.qWait(20)
            assert window.store.load().theme == theme
            assert identities == [id(window.tabs.widget(index)) for index in range(3)]
            assert page.input.toPlainText() == "Unsubmitted text / 尚未提交"
            assert page.password.text() == "synthetic-password"
            assert page.output.text() == "Retained result"
            if theme != "system":
                assert (app.palette().color(QPalette.ColorRole.Window).lightness() < 128) == (theme == "dark")
    finally:
        window.close()


def test_rejected_appearance_save_does_not_restyle_the_window(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app, window = _window(tmp_path)
    try:
        original_color = app.palette().color(QPalette.ColorRole.Window)
        dialog = SettingsDialog(window.i18n, window.settings, window.store, window)
        dialog.settings_saved.connect(window._settings_saved)
        dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData("dark"))

        def fail(_settings: object) -> None:
            raise OSError("Synthetic save failure")

        monkeypatch.setattr(window.store, "save", fail)
        dialog.save()
        assert window.settings.theme == "light"
        assert app.palette().color(QPalette.ColorRole.Window) == original_color
        assert not window.store.path.exists()
        dialog.close()
    finally:
        window.close()


def test_real_focused_mode_button_accepts_arrow_navigation(tmp_path: Path) -> None:
    _app, window = _window(tmp_path)
    try:
        mode = window.text_page.mode
        mode.buttons[0].setFocus()
        QTest.qWait(20)
        QTest.keyClick(mode.buttons[0], Qt.Key.Key_Right)
        assert mode.current == "decrypt"
        assert window.text_page.confirm_password.isHidden()
        assert mode.buttons[1].isChecked()
        assert mode.buttons[1].hasFocus()
    finally:
        window.close()
