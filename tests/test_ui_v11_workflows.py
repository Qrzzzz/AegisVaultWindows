"""Native form regressions; also run with QT_QPA_PLATFORM=windows."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QMessageBox,
    QScrollArea,
    QStyle,
    QStyleOptionComboBox,
    QWidget,
)

from aegisvault.core.models import TaskState
from aegisvault.i18n.translator import Translator
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from aegisvault.ui.main_window import MainWindow
from aegisvault.ui.pages.settings_page import SettingsDialog


@pytest.fixture
def window(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[MainWindow]:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    settings = AppSettings(language="en-US")
    win = MainWindow(settings, SettingsStore(tmp_path / "settings.json"), Translator(settings.language))
    win.show()
    win.activateWindow()
    QTest.qWait(30)
    try:
        yield win
    finally:
        for page in (win.text_page, win.file_page, win.base64_page):
            page.cancel()
            assert page.wait_for_task()
        win.close()
        app.processEvents()


def wait_for(predicate: object) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        QTest.qWait(10)
        if predicate():
            return
    raise AssertionError("Qt task did not reach its expected state")


def run(page: object) -> None:
    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    wait_for(lambda: not page.controller.busy)


def inside(widget: QWidget, parent: QWidget) -> bool:
    return parent.rect().contains(QRect(widget.mapTo(parent, QPoint()), widget.size()))


@pytest.mark.parametrize("language", ["en-US", "zh-CN"])
def test_result_actions_follow_operation_and_form_tabs_preserve_text(window: MainWindow, language: str) -> None:
    window.settings.language = language
    window._settings_saved()
    page = window.text_page
    page.input.setPlainText("中文\nform input")
    page.input.setFocus()
    QTest.keyClick(page.input, Qt.Key.Key_Tab)
    assert page.password.edit.hasFocus()
    assert page.input.toPlainText() == "中文\nform input"
    page.password.edit.setText("synthetic-password")
    page.confirm_password.edit.setText("synthetic-password")
    run(page)
    assert page.controller.state == TaskState.DONE
    assert page.output.text().startswith("AGV1.")
    for size in ((900, 680), (600, 440)):
        window.resize(*size)
        QTest.qWait(20)
        assert inside(page.run_button, window)
        assert page.result_scroll.mapTo(window, QPoint()).y() > page.run_button.mapTo(window, QPoint()).y()
        for button in (page.output.copy_button, page.output.clear_button, page.output.use_as_input_button):
            page.result_scroll.ensureWidgetVisible(button)
            QTest.qWait(10)
            assert inside(button, page.result_scroll.viewport())
        for scroll in page.findChildren(QScrollArea):
            assert scroll.horizontalScrollBar().maximum() == 0
    QTest.mouseClick(page.output.use_as_input_button, Qt.MouseButton.LeftButton)
    run(page)
    assert page.output.text() == "中文\nform input"
    page.password.edit.setText("wrong")
    run(page)
    assert page.alert.isVisible()
    assert page.output.text() == "中文\nform input"


def test_file_roundtrip_native_paths_and_language_retains_result(window: MainWindow, tmp_path: Path) -> None:
    folder = tmp_path / ("中文路径" * 12)
    folder.mkdir()
    source = folder / ("长文件名" * 10 + ".txt")
    source.write_bytes("仅测试 / Synthetic\n".encode() * 300)
    window._set_page(1)
    page = window.file_page
    page.set_file(source)
    page.password.edit.setText("synthetic-password")
    page.confirm_password.edit.setText("synthetic-password")
    run(page)
    encrypted = page.result.output_path
    assert encrypted is not None and encrypted.is_file()
    assert source.read_bytes().startswith("仅测试".encode())
    assert page.picker.path_edit.toolTip() == str(source)
    assert page.output_preview.isReadOnly()
    assert page.output_preview.toolTip() == page.output_preview.text()
    page.set_file(encrypted)
    page.mode.set_current("decrypt")
    run(page)
    decoded = page.result.output_path
    assert decoded is not None and decoded != source
    assert decoded.read_bytes() == source.read_bytes()
    page_ids = (id(window.text_page), id(page), id(window.base64_page))
    dialog = SettingsDialog(window.i18n, window.settings, window.store, window)
    dialog.settings_saved.connect(window._settings_saved)
    dialog.language_combo.setCurrentIndex(0)
    dialog.overwrite.setChecked(True)
    dialog.show()
    QTest.mouseClick(dialog.buttons.button(QDialogButtonBox.StandardButton.Save), Qt.MouseButton.LeftButton)
    assert window.store.load().language == "zh-CN"
    assert page_ids == (id(window.text_page), id(page), id(window.base64_page))
    assert page.result.output_path == decoded
    assert window.i18n.t("result.success") in page.result.label.text()
    assert page.overwrite_warning.isVisible()
    window._set_page(2)
    window.base64_page.kind.set_current("file")
    assert window.base64_page.overwrite_warning.isVisible()
    for index, target in ((1, page), (2, window.base64_page)):
        window._set_page(index)
        window.resize(600, 440)
        QTest.qWait(20)
        assert inside(target.run_button, window)
        for scroll in target.findChildren(QScrollArea):
            assert scroll.horizontalScrollBar().maximum() == 0


def test_mode_labels_fit_after_language_changes(window: MainWindow) -> None:
    window.resize(600, 440)
    for language in ("zh-CN", "en-US", "zh-CN"):
        window.settings.language = language
        window._settings_saved()
        for index, page in enumerate((window.text_page, window.file_page, window.base64_page)):
            window._set_page(index)
            for combo in ([page.kind, page.mode] if index == 2 else [page.mode]):
                for selected in range(combo.count()):
                    combo.setCurrentIndex(selected)
                    QTest.qWait(10)
                    option = QStyleOptionComboBox()
                    combo.initStyleOption(option)
                    field = combo.style().subControlRect(
                        QStyle.ComplexControl.CC_ComboBox, option, QStyle.SubControl.SC_ComboBoxEditField, combo
                    )
                    assert field.width() >= combo.fontMetrics().horizontalAdvance(combo.currentText())


@pytest.mark.parametrize("kind", ["crypto", "base64"])
@pytest.mark.parametrize("close", [False, True])
def test_real_file_cancel_and_close_cleanup(
    window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, close: bool
) -> None:
    """Pause only progress delivery; the real service/atomic writer still runs."""
    source = tmp_path / "cancel-fixture.bin"
    source.write_bytes(b"synthetic" * 1024 * 1024)
    page = window.file_page if kind == "crypto" else window.base64_page
    window._set_page(1 if kind == "crypto" else 2)
    if kind == "crypto":
        page.password.edit.setText("synthetic-password")
        page.confirm_password.edit.setText("synthetic-password")
    else:
        page.kind.set_current("file")
    page.set_file(source)
    method_name = "encrypt_file" if kind == "crypto" else "base64_encode_file"
    original = getattr(page.service, method_name)

    def controlled(*args: object, **kwargs: object) -> object:
        progress, token = kwargs["progress"], kwargs["cancel_token"]

        def report(event: object) -> None:
            progress(event)
            if event.processed_bytes:
                deadline = time.monotonic() + 8
                while not token.cancelled and time.monotonic() < deadline:
                    time.sleep(0.005)

        kwargs["progress"] = report
        return original(*args, **kwargs)

    monkeypatch.setattr(page.service, method_name, controlled)
    before = set(tmp_path.rglob("*"))
    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    wait_for(lambda: page.progress.bar.maximum() == 100 and page.progress.bar.value() > 2)
    assert page.controller.busy and not page.run_button.isEnabled()
    assert not page.picker.select_button.isEnabled()
    assert not page.result.clear_button.isEnabled()
    assert not page.set_file(source)
    if close:
        monkeypatch.setattr(QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Yes)
        assert window.close()
    else:
        QTest.mouseClick(page.progress.cancel_button, Qt.MouseButton.LeftButton)
    wait_for(lambda: not page.controller.busy)
    assert page.controller.state == TaskState.CANCELLED
    assert all(not thread.isRunning() for thread in page.controller._retired_threads)
    assert set(tmp_path.rglob("*")) == before
