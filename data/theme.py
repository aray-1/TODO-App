"""Light and dark themes: a calm slate background with an indigo accent.

Widgets read colours from ``theme_manager().theme`` and repaint when
``theme_manager().changed`` fires.
"""
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

from data import settings


@dataclass(frozen=True)
class Theme:
    name: str
    window: QColor        # board background (and the main window behind everything)
    sidebar: QColor       # project pane
    card: QColor          # TODO cards, inputs, menus, dialogs
    border: QColor        # separators and widget outlines
    hover: QColor         # hovered / pressed widget background
    accent: QColor        # primary highlight (indigo)
    accent_soft: QColor   # selected project row, module chips
    text: QColor
    text_muted: QColor
    shadow: QColor        # card drop shadow
    high: QColor          # urgency colours
    medium: QColor
    low: QColor
    overdue: QColor       # deadline chips
    due_soon: QColor

    def urgency(self, level):
        """The colour of an urgency level, or None when no urgency is set."""
        return {"high": self.high, "medium": self.medium, "low": self.low}.get(level)


LIGHT = Theme(
    name="light",
    window=QColor("#F5F6FA"),
    sidebar=QColor("#EBEDF5"),
    card=QColor("#FFFFFF"),
    border=QColor("#D9DCE8"),
    hover=QColor("#E3E6F2"),
    accent=QColor("#5B5FC7"),
    accent_soft=QColor("#E4E5F8"),
    text=QColor("#1F2233"),
    text_muted=QColor("#6B7085"),
    shadow=QColor(31, 34, 51, 38),
    high=QColor("#D64545"),
    medium=QColor("#D99A00"),
    low=QColor("#3A9D5D"),
    overdue=QColor("#D64545"),
    due_soon=QColor("#C98A00"),
)

DARK = Theme(
    name="dark",
    window=QColor("#1B1C22"),
    sidebar=QColor("#24252E"),
    card=QColor("#2B2D38"),
    border=QColor("#3A3C4A"),
    hover=QColor("#34364A"),
    accent=QColor("#8B8FF0"),
    accent_soft=QColor("#383A5C"),
    text=QColor("#E8E9F0"),
    text_muted=QColor("#9A9DB0"),
    shadow=QColor(0, 0, 0, 110),
    high=QColor("#F07171"),
    medium=QColor("#F2C14E"),
    low=QColor("#5CC48A"),
    overdue=QColor("#F07171"),
    due_soon=QColor("#F2C14E"),
)

THEMES = {"light": LIGHT, "dark": DARK}


class ThemeManager(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._theme = THEMES.get(settings.get("theme", "light"), LIGHT)

    @property
    def theme(self) -> Theme:
        return self._theme

    def set_theme(self, name: str) -> None:
        theme = THEMES[name]
        if theme is self._theme:
            return
        self._theme = theme
        settings.put("theme", name)
        self.changed.emit()

    def toggle(self) -> None:
        self.set_theme("dark" if self._theme.name == "light" else "light")


_manager = None


def theme_manager() -> ThemeManager:
    global _manager
    if _manager is None:
        _manager = ThemeManager()
    return _manager
