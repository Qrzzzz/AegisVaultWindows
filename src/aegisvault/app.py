"""Qt application entrypoint."""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from aegisvault.bootstrap import bootstrap
from aegisvault.ui.main_window import MainWindow


def run() -> int:
    store, settings, translator = bootstrap()
    app = QApplication(sys.argv)
    app.setApplicationName("AegisVault")
    app.setOrganizationName("AegisVault")
    window = MainWindow(settings, store, translator)
    if os.environ.get("AEGISVAULT_HEADLESS_SMOKE") == "1":
        window.close()
        app.quit()
        return 0
    window.show()
    return app.exec()
