from __future__ import annotations

import os
import time
from pathlib import Path
from threading import Event

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QPoint, QPointF, QRect, Qt, QUrl
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QMessageBox, QScrollArea, QWidget

from aegisvault.core.exceptions import ValidationError
from aegisvault.core.models import ProgressEvent, TextDecryptResult
from aegisvault.i18n.translator import Translator
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from aegisvault.ui import main_window as main_window_module
from aegisvault.ui.dialogs.about_dialog import AboutDialog
from aegisvault.ui.dialogs.error_dialog import show_error
from aegisvault.ui.main_window import MainWindow
from aegisvault.ui.pages.settings_page import SettingsDialog
from test_ui_visual import qa_application


def _window(tmp_path: Path, language: str = "en-US") -> tuple[QApplication, MainWindow]:
    app = qa_application()
    settings = AppSettings(language=language)
    window = MainWindow(settings, SettingsStore(tmp_path / "settings.json"), Translator(language))
    window.show()
    window.activateWindow()
    app.processEvents()
    return app, window


def _wait(app: QApplication, predicate: object) -> None:
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        app.processEvents()
        if callable(predicate) and predicate():
            return
        QTest.qWait(5)
    raise AssertionError("Qt did not reach the expected state")


def _inside(widget: QWidget, ancestor: QWidget) -> bool:
    return ancestor.rect().contains(QRect(widget.mapTo(ancestor, QPoint()), widget.size()))


@pytest.mark.parametrize("old_theme", ["dark", "system", "light"])
def test_old_theme_migration_preserves_other_preferences(tmp_path: Path, old_theme: str) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    old = AppSettings(
        theme=old_theme,
        language="en-US",
        default_output_dir=str(tmp_path),
        overwrite_outputs=True,
        remember_recent_files=False,
        show_advanced_options=True,
        recent_files=["C:/Samples/old.txt"],
    )
    store.save(old)
    loaded = store.load()
    assert loaded.theme == "light"
    assert loaded.to_dict() == {**old.to_dict(), "theme": "light"}
    store.save(loaded)
    assert store.load() == loaded


@pytest.mark.parametrize("old_theme", ["dark", "system"])
def test_all_dialogs_are_light_without_qss_or_theme_selector(
    tmp_path: Path, old_theme: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = qa_application()
    dark = QPalette(app.palette())
    dark.setColor(QPalette.ColorRole.Window, QColor("#202020"))
    dark.setColor(QPalette.ColorRole.Base, QColor("#151515"))
    app.setPalette(dark)
    settings = AppSettings(theme=old_theme)
    window = MainWindow(settings, SettingsStore(tmp_path / "settings.json"), Translator("en-US"))
    window.show()
    dialogs = [
        SettingsDialog(window.i18n, settings, window.store),
        AboutDialog(window, window.i18n),
    ]
    assert not hasattr(dialogs[0], "theme_combo")
    assert len(dialogs[0].findChildren(QComboBox)) == 1
    for dialog in dialogs:
        dialog.show()
    app.processEvents()
    for widget in [window, *dialogs]:
        assert widget.palette().color(QPalette.ColorRole.Window).lightness() > 180
        assert not widget.styleSheet()
    # Simulate a later platform notification while these windows are open.
    app.setPalette(dark)
    app.styleHints().colorSchemeChanged.emit(Qt.ColorScheme.Dark)
    _wait(app, lambda: window.palette().color(QPalette.ColorRole.Window).lightness() > 180)
    for widget in dialogs:
        assert widget.palette().color(QPalette.ColorRole.Window).lightness() > 180
        widget.close()

    seen: list[bool] = []

    def inspect_error(box: QMessageBox) -> int:
        seen.append(box.palette().color(QPalette.ColorRole.Window).lightness() > 180)
        assert not box.styleSheet()
        return 0

    monkeypatch.setattr(QMessageBox, "exec", inspect_error)
    show_error(window, window.i18n, ValidationError("fixture", code="validation.password_mismatch"))
    assert seen == [True]
    window.close()


def test_idle_running_result_error_and_cancel_visibility(tmp_path: Path) -> None:
    app, window = _window(tmp_path)
    for page in (window.text_page, window.file_page, window.base64_page):
        assert page.progress.isHidden()
        assert page.alert.isHidden()
    assert window.text_page.output.isHidden()
    assert window.base64_page.output.isHidden()
    assert window.file_page.result.isHidden()
    assert window.base64_page.result.isHidden()
    assert window.file_page.output_preview.isHidden()

    page = window.text_page
    started, finish = Event(), Event()

    def task(progress: object, _token: object) -> TextDecryptResult:
        started.set()
        progress(ProgressEvent(0.5, "decrypting", processed_bytes=5, total_bytes=10))
        while not finish.is_set():
            time.sleep(0.002)
        return TextDecryptResult("retained result", "AGV1")

    try:
        assert page.controller.run(task)
        _wait(app, started.is_set)
        assert page.progress.isVisible()
        assert page.progress.cancel_button.isEnabled()
        assert not page.run_button.isEnabled()
        assert page.input.isReadOnly()
        finish.set()
        _wait(app, lambda: not page.controller.busy)
        assert page.progress.isHidden()
        assert page.output.isVisible()
        assert page.run_button.isEnabled()
        assert page.output.text() == "retained result"
        assert page.output.copy_button.isVisible()

        # Validation failure must not erase the completed result.
        page.password.edit.setText("one")
        page.confirm_password.edit.setText("two")
        QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
        assert page.alert.isVisible()
        assert page.output.text() == "retained result"

        finish.clear()
        started.clear()
        page.alert.clear()
        assert page.controller.run(task)
        _wait(app, started.is_set)
        QTest.mouseClick(page.progress.cancel_button, Qt.MouseButton.LeftButton)
        assert not page.progress.cancel_button.isEnabled()
        assert not page.controller.cancel()
        finish.set()
        _wait(app, lambda: not page.controller.busy)
        assert page.progress.isHidden()
        assert page.output.text() == "retained result"
        QTest.mouseClick(page.output.clear_button, Qt.MouseButton.LeftButton)
        assert page.output.isHidden()
    finally:
        finish.set()
        page.wait_for_task()
        window.close()


@pytest.mark.parametrize("language", ["zh-CN", "en-US"])
@pytest.mark.parametrize("size", [(900, 680), (640, 480), (600, 440)])
def test_key_controls_reachable_at_normal_and_small_sizes(tmp_path: Path, language: str, size: tuple[int, int]) -> None:
    app, window = _window(tmp_path, language)
    window.resize(*size)
    for index, page in enumerate((window.text_page, window.file_page, window.base64_page)):
        window._set_page(index)
        app.processEvents()
        scroll = page.findChild(QScrollArea)
        assert scroll is not None
        assert scroll.horizontalScrollBar().maximum() == 0
        assert _inside(page.mode, scroll.viewport())
        assert _inside(page.run_button, window)
        assert _inside(page.clear_button, window)
        inputs = [page.picker.select_button] if index == 1 else [page.input]
        if index < 2:
            inputs += [page.password.edit, page.confirm_password.edit]
        assert all(_inside(widget, scroll.viewport()) for widget in inputs)
        assert page.font().pointSizeF() == app.font().pointSizeF()
    window._set_page(0)
    window.text_page.mode.set_current("decrypt")
    window.text_page.output.set_text("result")
    app.processEvents()
    scroll = window.text_page.findChild(QScrollArea)
    if size == (900, 680):
        assert scroll.verticalScrollBar().maximum() == 0
    for button in (
        window.text_page.output.copy_button,
        window.text_page.output.clear_button,
        window.text_page.output.use_as_input_button,
    ):
        scroll.ensureWidgetVisible(button)
        app.processEvents()
        assert _inside(button, scroll.viewport())
    assert _inside(window.text_page.run_button, window)
    window.close()


def test_modes_settings_and_tabs_preserve_inputs_and_results(tmp_path: Path) -> None:
    app, window = _window(tmp_path)
    source = tmp_path / "fixture.txt"
    source.write_text("fixture", encoding="utf-8")
    window.text_page.input.setPlainText("keep text")
    window.text_page.output.set_text("keep output")
    window.text_page.password.edit.setText("fixture-password")
    window.file_page.set_file(source)
    window.file_page.result.set_result("retained file result", source)
    base64 = window.base64_page
    base64.input.setPlainText("keep Base64")
    base64.output.set_text("a2VlcA==")
    base64.kind.set_current("file")
    base64.set_file(source)
    base64.result.set_result("retained Base64 file result", source)
    base64.kind.set_current("text")
    assert base64.result.isHidden()
    assert base64.output.text() == "a2VlcA=="
    base64.kind.set_current("file")
    assert not base64.result.isHidden()
    assert base64.output.isHidden()
    window._set_page(2)
    identities = tuple(id(page) for page in (window.text_page, window.file_page, base64))
    dialog = SettingsDialog(window.i18n, window.settings, window.store, window)
    dialog.language_combo.setCurrentIndex(0)
    dialog.settings_saved.connect(window._settings_saved)
    dialog.save()
    app.processEvents()
    assert window.tabs.currentIndex() == 2
    assert identities == tuple(id(page) for page in (window.text_page, window.file_page, base64))
    assert window.text_page.input.toPlainText() == "keep text"
    assert window.text_page.output.text() == "keep output"
    assert window.text_page.password.text() == "fixture-password"
    assert window.file_page.selected_file == source
    assert window.file_page.result.output_path == source
    assert base64.selected_file == source
    assert base64.input.toPlainText() == "keep Base64"
    assert base64.output.text() == "a2VlcA=="
    assert base64.result.output_path == source
    assert base64.kind.current == "file"
    assert window.tabs.tabText(0) == "文本"
    assert window.store.load().theme == "light"
    window.close()


def test_keyboard_shortcuts_and_native_mode_selection(tmp_path: Path) -> None:
    app, window = _window(tmp_path)
    QTest.qWait(20)
    QTest.keyClick(window, Qt.Key.Key_3, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    assert window.tabs.currentIndex() == 2
    assert window.base64_page.input.hasFocus()
    page = window.base64_page
    page.input.setPlainText("keyboard")
    QTest.keyClick(page.input, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    _wait(app, lambda: not page.controller.busy)
    assert page.output.text() == "a2V5Ym9hcmQ="
    page.mode.setFocus()
    QTest.keyClick(page.mode, Qt.Key.Key_Down)
    assert page.mode.current == "decode"
    assert page.relaxed_decode.isVisible()
    QTest.keyClick(window, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    assert window.text_page.input.hasFocus()
    toggle = window.text_page.password.toggle
    QTest.mouseClick(toggle, Qt.MouseButton.LeftButton)
    assert toggle.text() == "Hide"
    assert toggle.accessibleName() == "Hide"
    QTest.mouseClick(toggle, Qt.MouseButton.LeftButton)
    assert toggle.text() == "Show"
    window.close()


def test_base64_file_drop_roundtrip_preview_recent_and_reveal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app, window = _window(tmp_path)
    source = tmp_path / "sample.bin"
    source.write_bytes(bytes(range(256)))
    page = window.base64_page
    page.kind.set_current("file")
    window._set_page(2)
    app.processEvents()
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(source))])
    drag = QDragEnterEvent(
        QPoint(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    )
    drop = QDropEvent(
        QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    )
    QApplication.sendEvent(page.picker, drag)
    QApplication.sendEvent(page.picker, drop)
    assert drag.isAccepted() and drop.isAccepted()
    assert page.selected_file == source
    assert str(source) in page.picker.path_edit.text()
    assert page.output_preview.isVisible()
    assert ".b64" in page.output_preview.text()
    assert window.settings.recent_files[0] == str(source.resolve())
    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    _wait(app, lambda: not page.controller.busy)
    encoded = page.result.output_path
    assert encoded is not None and encoded.is_file()
    revealed: list[Path] = []
    monkeypatch.setattr(main_window_module, "reveal_file", revealed.append)
    QTest.mouseClick(page.result.open_button, Qt.MouseButton.LeftButton)
    assert revealed == [encoded]
    page.set_file(encoded)
    assert page.result.output_path == encoded  # selecting input doesn't discard the previous result
    page.mode.set_current("decode")
    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    _wait(app, lambda: not page.controller.busy)
    decoded = page.result.output_path
    assert decoded is not None
    assert decoded.read_bytes() == source.read_bytes()
    window.recent_menu.actions()[0].trigger()
    app.processEvents()
    assert window.tabs.currentIndex() == 1
    assert window.file_page.selected_file == encoded
    window.close()


def test_picker_rejects_drop_while_its_real_worker_is_busy(tmp_path: Path) -> None:
    app, window = _window(tmp_path)
    first, second = tmp_path / "first.txt", tmp_path / "second.txt"
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")
    page = window.file_page
    page.set_file(first)
    started, finish = Event(), Event()

    def task(_progress: object, _token: object) -> None:
        started.set()
        while not finish.is_set():
            time.sleep(0.002)

    try:
        page.controller.run(task)
        _wait(app, started.is_set)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(second))])
        event = QDropEvent(
            QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
        )
        page.picker.dropEvent(event)
        assert not event.isAccepted()
        assert page.selected_file == first
        assert not page.picker.select_button.isEnabled()
        page.cancel()
        finish.set()
        _wait(app, lambda: not page.controller.busy)
        assert page.picker.select_button.isEnabled()
    finally:
        finish.set()
        page.wait_for_task()
        window.close()
