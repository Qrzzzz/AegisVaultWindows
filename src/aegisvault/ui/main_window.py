"""Main application window and page navigation."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import QMainWindow, QMessageBox

from aegisvault.i18n.translator import Translator
from aegisvault.services.crypto_service import CryptoService
from aegisvault.services.file_io import reveal_file
from aegisvault.services.recent_files import RecentFilesService
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from aegisvault.ui.components.app_shell import AppShell, Sidebar
from aegisvault.ui.dialogs.about_dialog import AboutDialog
from aegisvault.ui.dialogs.error_dialog import show_error
from aegisvault.ui.pages.base64_page import Base64Page
from aegisvault.ui.pages.file_page import FilePage
from aegisvault.ui.pages.settings_page import SettingsPage
from aegisvault.ui.pages.text_page import TextPage
from aegisvault.ui.platform_effects import apply_windows_backdrop
from aegisvault.ui.styles import app_stylesheet
from aegisvault.utils.paths import resource_path

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Application shell that hosts task-specific workspaces."""

    PAGE_META = {
        0: ("text.title", "text.description"),
        1: ("file.title", "file.description"),
        2: ("base64.title", "base64.description"),
        3: ("settings.title", "settings.description"),
    }

    def __init__(self, settings: AppSettings, store: SettingsStore, translator: Translator) -> None:
        super().__init__()
        self.settings = settings
        self.store = store
        self.i18n = translator
        self.service = CryptoService(settings)
        self.recent = RecentFilesService(settings, store)
        self.text_page: TextPage
        self.file_page: FilePage
        self.base64_page: Base64Page
        self.settings_page: SettingsPage

        icon_path = resource_path("app_icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setWindowTitle(self.i18n.t("app.title"))
        self.setAcceptDrops(True)
        self.setMinimumSize(1040, 700)
        self.resize(1200, 800)
        self._build_ui()
        self._apply_theme()
        QTimer.singleShot(0, lambda: apply_windows_backdrop(int(self.winId()), dark=self.settings.theme != "light"))

    def _build_ui(self) -> None:
        sidebar = Sidebar(
            self.i18n.t("app.title"),
            self.i18n.t("app.subtitle"),
            [
                (self.i18n.t("nav.text"), 0),
                (self.i18n.t("nav.file"), 1),
                (self.i18n.t("nav.base64"), 2),
                (self.i18n.t("nav.settings"), 3),
            ],
            self.i18n.t("nav.about"),
        )
        sidebar.page_selected.connect(self._set_page)
        sidebar.about_requested.connect(self._show_about)
        self.shell = AppShell(sidebar)
        self.setCentralWidget(self.shell)
        self._build_pages()
        self._set_page(0)

    def _build_pages(self) -> None:
        self.text_page = TextPage(self.i18n, self.settings, self.service)
        self.file_page = FilePage(self.i18n, self.settings, self.service)
        self.base64_page = Base64Page(self.i18n, self.settings, self.service)
        self.settings_page = SettingsPage(self.i18n, self.settings, self.store)
        for page in (self.text_page, self.file_page, self.base64_page):
            page.error.connect(self._log_error)
            page.status_message.connect(self.shell.status.show_message)
        self.file_page.file_selected.connect(self._remember_file)
        self.base64_page.file_selected.connect(self._remember_file)
        self.file_page.reveal_requested.connect(self._reveal_file)
        self.base64_page.reveal_requested.connect(self._reveal_file)
        self.settings_page.error.connect(self._log_error)
        self.settings_page.settings_saved.connect(self._settings_saved)
        self.settings_page.recent_cleared.connect(lambda: self.shell.status.show_message(self.i18n.t("settings.recent_cleared"), 3000))
        for workspace in (self.text_page, self.file_page, self.base64_page, self.settings_page):
            self.shell.stack.addWidget(workspace)

    def _set_page(self, index: int) -> None:
        self.shell.stack.setCurrentIndex(index)
        self.shell.sidebar.set_current(index)
        title_key, desc_key = self.PAGE_META[index]
        self.shell.header.set_page(self.i18n.t(title_key), self.i18n.t(desc_key))

    def _settings_saved(self) -> None:
        current = self.shell.stack.currentIndex()
        self.i18n.set_language(self.settings.language)
        self.service = CryptoService(self.settings)
        self._apply_theme()
        self._build_ui()
        self._set_page(current)
        self.shell.status.show_message(self.i18n.t("settings.saved"), 3000)

    def _remember_file(self, path: object) -> None:
        if isinstance(path, Path):
            self.recent.add(path)

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
        LOGGER.error("UI error: %s", exc, exc_info=True)
        if diagnostic:
            LOGGER.debug("Diagnostic detail:\n%s", diagnostic)

    def _show_error(self, exc: object, diagnostic: str = "") -> None:
        LOGGER.error("UI error: %s", exc, exc_info=True)
        show_error(self, self.i18n, exc, diagnostic)

    def _apply_theme(self) -> None:
        theme = "dark" if self.settings.theme == "system" else self.settings.theme
        self.setStyleSheet(app_stylesheet(theme))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        data = event.mimeData()
        if data.hasUrls():
            for url in data.urls():
                path = Path(url.toLocalFile())
                if path.is_file():
                    self.file_page.set_file(path)
                    self._set_page(1)
                    self.shell.status.show_message(self.i18n.t("drag.file_detected"), 3000)
                    return
        if data.hasText():
            self.text_page.input.setPlainText(data.text())
            self._set_page(0)
            self.shell.status.show_message(self.i18n.t("drag.text_detected"), 3000)

    def closeEvent(self, event: QCloseEvent) -> None:
        running_pages = [page for page in (self.text_page, self.file_page, self.base64_page) if page.has_running_task()]
        if running_pages:
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
                if hasattr(page, "cancel"):
                    page.cancel()
        event.accept()
