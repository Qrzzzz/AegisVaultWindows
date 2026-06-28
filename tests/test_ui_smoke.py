from __future__ import annotations

import os

from PySide6.QtWidgets import QApplication

from aegisvault.bootstrap import bootstrap
from aegisvault.ui.main_window import MainWindow


def test_main_window_constructs_and_switches_pages() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    store, settings, translator = bootstrap()
    window = MainWindow(settings, store, translator)
    assert window.shell.stack.count() == 4
    for index in range(4):
        window._set_page(index)
        assert window.shell.stack.currentIndex() == index
    window.text_page.mode.set_current("decrypt")
    assert window.text_page.confirm_password.isHidden()
    window.text_page.mode.set_current("encrypt")
    assert not window.text_page.confirm_password.isHidden()
    window.close()
    app.processEvents()
