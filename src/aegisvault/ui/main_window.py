"""Single-window AegisVault shell and workspace navigation."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTabWidget

from aegisvault.core.exceptions import FileIOError
from aegisvault.i18n.translator import Translator
from aegisvault.services.crypto_service import CryptoService
from aegisvault.services.file_io import reveal_file
from aegisvault.services.recent_files import RecentFilesService
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from aegisvault.ui.dialogs.about_dialog import AboutDialog
from aegisvault.ui.dialogs.error_dialog import show_error
from aegisvault.ui.light import ensure_light_appearance
from aegisvault.ui.pages.base64_page import Base64Page
from aegisvault.ui.pages.file_page import FilePage
from aegisvault.ui.pages.settings_page import SettingsDialog
from aegisvault.ui.pages.text_page import TextPage
from aegisvault.utils.paths import resource_path

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Compact shell hosting the three user workspaces."""

    def __init__(self, settings: AppSettings, store: SettingsStore, translator: Translator) -> None:
        super().__init__()
        ensure_light_appearance()
        self.settings = settings
        self.store = store
        self.i18n = translator
        self.service = CryptoService(settings)
        self.recent = RecentFilesService(settings, store)
        self.settings_dialog: SettingsDialog | None = None
        self._shortcuts: list[QShortcut] = []

        icon_path = resource_path("app_icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setAcceptDrops(True)
        self.setMinimumSize(600, 440)
        self.resize(900, 680)
        self._build_ui()
        self._build_menu()
        self._install_shortcuts()
        self.retranslate_ui()
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.styleHints().colorSchemeChanged.connect(self._keep_light)

    def _build_ui(self) -> None:
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.statusBar().setSizeGripEnabled(False)
        self._build_pages()
        self.tabs.currentChanged.connect(self._focus_page)
        self._set_page(0, focus=False)

    def _build_pages(self) -> None:
        self.text_page = TextPage(self.i18n, self.settings, self.service)
        self.file_page = FilePage(self.i18n, self.settings, self.service)
        self.base64_page = Base64Page(self.i18n, self.settings, self.service)
        for page in (self.text_page, self.file_page, self.base64_page):
            page.error.connect(self._log_error)
            page.status_message.connect(self.statusBar().showMessage)
            self.tabs.addTab(page, "")
        self.text_page.settings_requested.connect(self._show_settings)
        self.file_page.file_selected.connect(self._remember_file)
        self.base64_page.file_selected.connect(self._remember_file)
        self.file_page.reveal_requested.connect(self._reveal_file)
        self.base64_page.reveal_requested.connect(self._reveal_file)

    def _build_menu(self) -> None:
        self.app_menu = self.menuBar().addMenu("")
        self.settings_action = QAction(self)
        self.settings_action.setShortcut(QKeySequence("Ctrl+,"))
        self.settings_action.triggered.connect(self._show_settings)
        self.app_menu.addAction(self.settings_action)
        self.recent_menu = self.app_menu.addMenu("")
        self.app_menu.addSeparator()
        self.exit_action = QAction(self)
        self.exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self.exit_action.triggered.connect(self.close)
        self.app_menu.addAction(self.exit_action)
        self.help_menu = self.menuBar().addMenu("")
        self.about_action = QAction(self)
        self.about_action.setShortcut(QKeySequence("F1"))
        self.about_action.triggered.connect(self._show_about)
        self.help_menu.addAction(self.about_action)

    def _install_shortcuts(self) -> None:
        for sequence, index in (("Ctrl+1", 0), ("Ctrl+2", 1), ("Ctrl+3", 2)):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(lambda selected=index: self._set_page(selected))
            self._shortcuts.append(shortcut)

    def _set_page(self, index: int, *, focus: bool = True) -> None:
        if index not in range(3):
            return
        self.tabs.setCurrentIndex(index)
        if focus:
            self._focus_page(index)

    def _focus_page(self, index: int) -> None:
        page = self.tabs.widget(index)
        if hasattr(page, "focus_initial"):
            QTimer.singleShot(0, page.focus_initial)

    def retranslate_ui(self) -> None:
        self.setWindowTitle(self.i18n.t("app.title"))
        for index, key in enumerate(("nav.text", "nav.file", "nav.base64")):
            self.tabs.setTabText(index, self.i18n.t(key))
        self.tabs.setAccessibleName(self.i18n.t("access.workspaces"))
        self.text_page.retranslate_ui()
        self.file_page.retranslate_ui()
        self.base64_page.retranslate_ui()
        self.app_menu.setTitle(self.i18n.t("menu.app"))
        self.settings_action.setText(self.i18n.t("nav.settings"))
        self.recent_menu.setTitle(self.i18n.t("settings.recent_files"))
        self.exit_action.setText(self.i18n.t("action.exit"))
        self.help_menu.setTitle(self.i18n.t("menu.help"))
        self.about_action.setText(self.i18n.t("nav.about"))
        self._refresh_recent_menu()

    def _show_settings(self) -> None:
        if self._has_running_tasks():
            self.statusBar().showMessage(self.i18n.t("settings.blocked_while_running"), 4000)
            return
        dialog = SettingsDialog(self.i18n, self.settings, self.store, self)
        dialog.error.connect(self._log_error)
        dialog.settings_saved.connect(self._settings_saved)
        dialog.recent_cleared.connect(self._recent_cleared)
        self.settings_dialog = dialog
        dialog.exec()
        self.settings_dialog = None

    def _settings_saved(self) -> None:
        self.i18n.set_language(self.settings.language)
        self.service = CryptoService(self.settings)
        for page in (self.text_page, self.file_page, self.base64_page):
            page.set_service(self.service)
        ensure_light_appearance()
        self.retranslate_ui()
        self.statusBar().showMessage(self.i18n.t("settings.saved"), 3000)

    def _recent_cleared(self) -> None:
        self._refresh_recent_menu()
        self.statusBar().showMessage(self.i18n.t("settings.recent_cleared"), 3000)

    def _remember_file(self, path: object) -> None:
        if isinstance(path, Path):
            self.recent.add(path)
            self._refresh_recent_menu()

    def _refresh_recent_menu(self) -> None:
        self.recent_menu.clear()
        if not self.settings.recent_files:
            empty = self.recent_menu.addAction(self.i18n.t("settings.no_recent"))
            empty.setEnabled(False)
            return
        for value in self.settings.recent_files:
            action = self.recent_menu.addAction(value)
            action.setToolTip(value)
            action.triggered.connect(lambda _checked=False, path=value: self._open_recent(path))

    def _open_recent(self, value: str) -> None:
        path = Path(value)
        if not path.is_file():
            self._show_error(FileIOError("Recent file is unavailable.", code="file.not_found"), "")
            return
        if self.file_page.set_file(path):
            self._set_page(1)
            self.statusBar().showMessage(self.i18n.t("file.recent_opened"), 3000)

    def _reveal_file(self, path: object) -> None:
        if not isinstance(path, Path):
            return
        try:
            reveal_file(path)
        except Exception as exc:
            self._show_error(exc, "")

    def _show_about(self) -> None:
        AboutDialog(self, self.i18n).exec()

    def _log_error(self, exc: object, diagnostic: str = "") -> None:
        LOGGER.error("UI error: %s", exc)
        if diagnostic:
            LOGGER.debug("Diagnostic detail:\n%s", diagnostic)

    def _show_error(self, exc: object, diagnostic: str = "") -> None:
        self._log_error(exc, diagnostic)
        show_error(self, self.i18n, exc, diagnostic)

    def _keep_light(self, _scheme: object) -> None:
        QTimer.singleShot(0, ensure_light_appearance)

    def _has_running_tasks(self) -> bool:
        return any(page.has_running_task() for page in (self.text_page, self.file_page, self.base64_page))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._has_running_tasks():
            event.ignore()
            return
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        if self._has_running_tasks():
            event.ignore()
            self.statusBar().showMessage(self.i18n.t("drag.blocked_running"), 4000)
            return
        data = event.mimeData()
        if data.hasUrls():
            for url in data.urls():
                path = Path(url.toLocalFile())
                if not path.is_file():
                    continue
                if self.tabs.currentIndex() == 2 and self.base64_page.kind.current == "file":
                    accepted = self.base64_page.set_file(path)
                    target = 2
                else:
                    accepted = self.file_page.set_file(path)
                    target = 1
                if accepted:
                    self._set_page(target)
                    self.statusBar().showMessage(self.i18n.t("drag.file_detected"), 3000)
                    event.acceptProposedAction()
                return
        if data.hasText():
            self.text_page.input.setPlainText(data.text())
            self._set_page(0)
            self.statusBar().showMessage(self.i18n.t("drag.text_detected"), 3000)
            event.acceptProposedAction()
            return
        event.ignore()

    def closeEvent(self, event: QCloseEvent) -> None:
        running_pages = [page for page in (self.text_page, self.file_page, self.base64_page) if page.has_running_task()]
        if not running_pages:
            event.accept()
            return
        answer = QMessageBox.question(
            self,
            self.i18n.t("close.running_title"),
            self.i18n.t("close.running_message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            event.ignore()
            return
        for page in running_pages:
            page.cancel()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            stopped = True
            for page in running_pages:
                stopped = page.wait_for_task() and stopped
        finally:
            QApplication.restoreOverrideCursor()
        if not stopped:
            self.statusBar().showMessage(self.i18n.t("close.waiting"), 5000)
            event.ignore()
            return
        event.accept()
