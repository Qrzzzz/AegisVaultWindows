# ruff: noqa: E402, I001

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtGui import QFontDatabase, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from aegisvault.i18n.translator import Translator
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from aegisvault.ui.main_window import MainWindow

BASELINE_DIR = ROOT / "docs" / "screenshots"
PAGE_NAMES = ("text", "file", "base64")


def render_workspace(path: Path, page_index: int, *, language: str = "zh-CN") -> QImage:
    app = QApplication.instance() or QApplication([])
    for font_path in (
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/msyhbd.ttc"),
    ):
        if font_path.is_file():
            QFontDatabase.addApplicationFont(str(font_path))
    with tempfile.TemporaryDirectory(prefix="aegisvault-ui-") as temp_dir:
        temp = Path(temp_dir)
        settings = AppSettings(language=language, theme="dark")
        window = MainWindow(settings, SettingsStore(temp / "settings.json"), Translator(language))
        window.resize(1080, 900)
        window.text_page.input.setPlainText("AegisVault 的加密操作只在本机执行。\nCtrl+Enter 运行当前选择的操作。")
        sample = temp / "design-review.txt"
        sample.write_text("visual regression sample", encoding="utf-8")
        window.file_page.set_file(sample)
        display_path = Path("C:/Users/User/Documents/design-review.txt")
        window.file_page.picker.set_file(
            display_path,
            {
                window.i18n.t("file.path_label"): str(display_path),
                window.i18n.t("file.size_label"): "24 B",
                window.i18n.t("file.type_label"): ".txt",
            },
        )
        window.file_page.output_dir.setText("C:/Users/User/Documents")
        window.file_page.output_preview.setText(
            window.i18n.t(
                "file.output_preview",
                path="C:/Users/User/Documents/design-review.txt.agv",
            )
        )
        window.file_page.password.edit.setText("sample password")
        window.file_page.confirm_password.edit.setText("sample password")
        window.base64_page.input.setPlainText("AegisVault")
        window._set_page(page_index, focus=False)
        window.show()
        app.processEvents()
        QTest.qWait(60)
        image = window.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
        path.parent.mkdir(parents=True, exist_ok=True)
        assert image.save(str(path), "PNG")
        window.close()
        app.processEvents()
        return image


def _sample_difference(left: QImage, right: QImage) -> float:
    assert left.size() == right.size()
    difference = 0
    samples = 0
    for y in range(0, left.height(), 16):
        for x in range(0, left.width(), 16):
            a = left.pixelColor(x, y)
            b = right.pixelColor(x, y)
            difference += abs(a.red() - b.red()) + abs(a.green() - b.green()) + abs(a.blue() - b.blue())
            samples += 1
    return difference / max(1, samples * 255 * 3)


def test_offscreen_workspace_screenshots_match_structural_baselines(tmp_path: Path) -> None:
    for index, name in enumerate(PAGE_NAMES):
        rendered = render_workspace(tmp_path / f"{name}.png", index)
        baseline_path = BASELINE_DIR / f"minimal-{name}-zh-CN.png"
        baseline = QImage(str(baseline_path)).convertToFormat(QImage.Format.Format_RGB32)
        assert not baseline.isNull(), f"Missing UI baseline: {baseline_path}"
        assert rendered.size() == baseline.size() == rendered.size()
        assert rendered.width() >= 900
        assert rendered.height() >= 680
        assert _sample_difference(rendered, baseline) < 0.18


def _update_baselines() -> None:
    for index, name in enumerate(PAGE_NAMES):
        target = BASELINE_DIR / f"minimal-{name}-zh-CN.png"
        render_workspace(target, index)
        print(target)


if __name__ == "__main__":
    if "--update" not in sys.argv:
        raise SystemExit("Pass --update to regenerate UI screenshot baselines.")
    _update_baselines()
