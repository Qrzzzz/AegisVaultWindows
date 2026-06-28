"""Main application window and page navigation."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from aegisvault.i18n.translator import Translator
from aegisvault.services.crypto_service import CryptoService
from aegisvault.services.file_io import reveal_file
from aegisvault.services.recent_files import RecentFilesService
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
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
    """Thin shell that hosts independently implemented workspaces."""

    def __init__(self, settings: AppSettings, store: SettingsStore, translator: Translator) -> None:
        super().__init__()
        self.settings = settings
        self.store = store
        self.i18n = translator
        self.service = CryptoService(settings)
        self.recent = RecentFilesService(settings, store)
        self.stack = QStackedWidget()
        self.nav_group = QButtonGroup(self)
        self.nav_buttons: dict[int, QPushButton] = {}
        self.text_page: TextPage
        self.file_page: FilePage
        self.base64_page: Base64Page
        self.settings_page: SettingsPage

        icon_path = resource_path("app_icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setWindowTitle(self.i18n.t("app.title"))
        self.setAcceptDrops(True)
        self.setMinimumSize(1000, 660)
        self.resize(1180, 780)
        self._build_ui()
        self._apply_theme()
        QTimer.singleShot(0, lambda: apply_windows_backdrop(int(self.winId()), dark=self.settings.theme != "light"))

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())
        self.stack = QStackedWidget()
        self.stack.setContentsMargins(0, 0, 0, 0)
        self._build_pages()
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(238)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(10)
        brand = QLabel(self.i18n.t("app.title"))
        brand.setObjectName("Brand")
        subtitle = QLabel(self.i18n.t("app.subtitle"))
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addSpacing(18)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = {}
        for text, index in [
            (self.i18n.t("nav.text"), 0),
            (self.i18n.t("nav.file"), 1),
            (self.i18n.t("nav.base64"), 2),
            (self.i18n.t("nav.settings"), 3),
        ]:
            button = QPushButton(text)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, i=index: self._set_page(i))
            self.nav_group.addButton(button, index)
            self.nav_buttons[index] = button
            layout.addWidget(button)
        self.nav_buttons[0].setChecked(True)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        about = QPushButton(self.i18n.t("nav.about"))
        about.clicked.connect(self._show_about)
        layout.addWidget(about)
        return sidebar

    def _build_pages(self) -> None:
        self.text_page = TextPage(self.i18n, self.settings, self.service)
        self.file_page = FilePage(self.i18n, self.settings, self.service)
        self.base64_page = Base64Page(self.i18n, self.settings, self.service)
        self.settings_page = SettingsPage(self.i18n, self.settings, self.store)
        for page in (self.text_page, self.file_page, self.base64_page):
            page.error.connect(self._show_error)
            page.status_message.connect(self.statusBar().showMessage)
        self.file_page.file_selected.connect(self._remember_file)
        self.base64_page.file_selected.connect(self._remember_file)
        self.file_page.reveal_requested.connect(self._reveal_file)
        self.base64_page.reveal_requested.connect(self._reveal_file)
        self.settings_page.error.connect(self._show_error)
        self.settings_page.settings_saved.connect(self._settings_saved)
        self.settings_page.recent_cleared.connect(lambda: self.statusBar().showMessage(self.i18n.t("settings.recent_cleared"), 3000))
        for workspace in (self.text_page, self.file_page, self.base64_page, self.settings_page):
            self.stack.addWidget(workspace)

    def _set_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        button = self.nav_buttons.get(index)
        if button:
            button.setChecked(True)

    def _settings_saved(self) -> None:
        current = self.stack.currentIndex()
        self.i18n.set_language(self.settings.language)
        self.service = CryptoService(self.settings)
        self._apply_theme()
        self._build_ui()
        self._set_page(current)
        self.statusBar().showMessage(self.i18n.t("settings.saved"), 3000)

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
                    self.statusBar().showMessage(self.i18n.t("drag.file_detected"), 3000)
                    return
        if data.hasText():
            self.text_page.input.setPlainText(data.text())
            self._set_page(0)
            self.statusBar().showMessage(self.i18n.t("drag.text_detected"), 3000)

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


