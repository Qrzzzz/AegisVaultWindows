from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTabWidget

from aegisvault.i18n.translator import Translator
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from aegisvault.ui.main_window import MainWindow


def _window(tmp_path: Path) -> tuple[QApplication, MainWindow, AppSettings]:
    app = QApplication.instance() or QApplication([])
    settings = AppSettings()
    window = MainWindow(settings, SettingsStore(tmp_path / "settings.json"), Translator(settings.language))
    return app, window, settings


def test_main_window_has_only_three_primary_workspaces(tmp_path: Path) -> None:
    app, window, _settings = _window(tmp_path)
    window.show()
    app.processEvents()
    assert isinstance(window.centralWidget(), QTabWidget)
    assert window.tabs.count() == 3
    for index in range(3):
        QTest.mouseClick(window.tabs.tabBar(), Qt.MouseButton.LeftButton, pos=window.tabs.tabBar().tabRect(index).center())
        app.processEvents()
        assert window.tabs.currentIndex() == index

    assert window.settings_action.shortcut().toString() == "Ctrl+,"
    assert window.about_action.shortcut().toString() == "F1"
    assert window.text_page.input.accessibleName()
    assert window.file_page.picker.select_button.accessibleName()
    assert window.base64_page.input.accessibleName()
    window.close()
    app.processEvents()


def test_settings_apply_in_place_without_losing_workspace_state(tmp_path: Path) -> None:
    app, window, settings = _window(tmp_path)
    window.text_page.input.setPlainText("keep this input")
    window.text_page.output.set_text("keep this result")
    window._set_page(1, focus=False)
    page_ids = tuple(id(page) for page in (window.text_page, window.file_page, window.base64_page))

    settings.language = "en-US"
    settings.theme = "light"
    window._settings_saved()
    app.processEvents()

    assert tuple(id(page) for page in (window.text_page, window.file_page, window.base64_page)) == page_ids
    assert window.text_page.input.toPlainText() == "keep this input"
    assert window.text_page.output.text() == "keep this result"
    assert window.tabs.currentIndex() == 1
    assert window.tabs.tabText(0) == "Text"
    assert not window.styleSheet()
    window.close()
    app.processEvents()
