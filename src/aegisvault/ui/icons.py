"""Small monochrome vector icons; widget rendering stays with Qt."""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

PATHS = {
    "text": '<path d="M6 3h8l4 4v14H6zM14 3v5h4M9 12h6M9 16h6"/>',
    "file": '<path d="M3 6h7l2 2h9v12H3z"/>',
    "base64": '<path d="m8 7-5 5 5 5m8-10 5 5-5 5m-3-13-2 16"/>',
    "settings": '<path d="M4 7h5m4 0h7M4 17h9m4 0h3"/><circle cx="11" cy="7" r="2"/><circle cx="15" cy="17" r="2"/>',
    "more": '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    "eye": '<path d="M2 12s4-6 10-6 10 6 10 6-4 6-10 6-10-6-10-6z"/><circle cx="12" cy="12" r="3"/>',
    "eye-off": '<path d="m3 3 18 18M9 6c7-2 13 6 13 6s-1 2-3 3M6 7c-2 2-4 5-4 5s6 9 14 5"/>',
    "upload": '<path d="M6 3h8l4 4v14H6zM14 3v5h4m-6 10v-7m-3 3 3-3 3 3"/>',
    "local": '<rect x="3" y="4" width="18" height="13" rx="1"/><path d="M8 21h8m-4-4v4"/>',
}


def icon(name: str) -> QIcon:
    color = QApplication.palette().color(QPalette.ColorRole.WindowText).name()
    return _render(name, color)


@lru_cache(maxsize=64)
def _render(name: str, color: str) -> QIcon:
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</svg>'
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    result = QIcon()
    for scale in (1, 2, 3):
        pixmap = QPixmap(24 * scale, 24 * scale)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        pixmap.setDevicePixelRatio(scale)
        result.addPixmap(pixmap)
        disabled = QPixmap(pixmap.size())
        disabled.fill(Qt.GlobalColor.transparent)
        painter = QPainter(disabled)
        painter.setOpacity(0.45)
        # Use physical pixels while composing the disabled high-DPI variant.
        pixmap.setDevicePixelRatio(1)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        disabled.setDevicePixelRatio(scale)
        result.addPixmap(disabled, QIcon.Mode.Disabled)
    return result
