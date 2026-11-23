"""Icons loaded from data/icons/*.svg.

Line icons draw with ``currentColor``; ``icon()`` substitutes the current
theme's text colour (or a given colour) and caches the result. The full-colour
window icon comes from ``app_icon()``.
"""
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from data.theme import theme_manager

ICON_DIR = Path(__file__).resolve().parent / "icons"
SIZES = (16, 20, 24, 32, 48)
WINDOW_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
DISABLED_OPACITY = 0.55

_cache = {}


def svg_text(name: str, color) -> str:
    """The SVG source of ``name`` drawn in ``color`` (QColor), or "" if unknown."""
    path = ICON_DIR / f"{name}.svg"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").replace("currentColor", color.name())


def _pixmap(svg: str, size: int, opacity: float = 1.0) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setOpacity(opacity)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(painter)
    painter.end()
    return pixmap


def app_icon(name: str = "app") -> QIcon:
    """A full-colour window icon (data/icons/<name>.svg) at the usual sizes."""
    key = ("window", name)
    if key not in _cache:
        path = ICON_DIR / f"{name}.svg"
        result = QIcon()
        if path.is_file():
            svg = path.read_text(encoding="utf-8")
            for size in WINDOW_SIZES:
                result.addPixmap(_pixmap(svg, size))
        _cache[key] = result
    return _cache[key]


def icon(name: str, color=None) -> QIcon:
    """The icon ``name`` in ``color`` (default: the current theme's text colour);
    an empty QIcon if unknown."""
    theme = theme_manager().theme
    color = color or theme.text
    key = (name, color.name(), theme.name)
    if key not in _cache:
        normal = svg_text(name, color)
        result = QIcon()
        if normal:
            disabled = svg_text(name, theme.text_muted)
            for size in SIZES:
                result.addPixmap(_pixmap(normal, size), QIcon.Normal)
                result.addPixmap(_pixmap(disabled, size, DISABLED_OPACITY), QIcon.Disabled)
        _cache[key] = result
    return _cache[key]
