"""Application stylesheet generated from a ``data.theme.Theme``.

Apply with ``app.setStyleSheet(build_qss(theme_manager().theme))`` and again
whenever ``theme_manager().changed`` fires.
"""
from data.icons import svg_text
from data.paths import user_subdir


def _luminance(color) -> float:
    def channel(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(color.red()) + 0.7152 * channel(color.green()) + 0.0722 * channel(color.blue())


def contrast(a, b) -> float:
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def on_color(background, candidates):
    """The candidate colour with the highest contrast against ``background``."""
    return max(candidates, key=lambda c: contrast(background, c))


def _icon_url(name: str, color) -> str:
    """A QSS url() for ``name`` recoloured to ``color`` (stylesheet images cannot
    be recoloured, so a copy is written to the per-user icon cache)."""
    path = user_subdir("icon_cache") / f"{name}_{color.name()[1:]}.svg"
    if not path.exists():
        path.write_text(svg_text(name, color), encoding="utf-8")
    return f'url("{path.as_posix()}")'


def build_qss(theme) -> str:
    t = theme
    on_accent = on_color(t.accent, (t.card, t.text, t.window))
    v = {
        "window": t.window.name(), "sidebar": t.sidebar.name(), "card": t.card.name(),
        "border": t.border.name(), "hover": t.hover.name(), "accent": t.accent.name(),
        "accent_soft": t.accent_soft.name(), "text": t.text.name(), "muted": t.text_muted.name(),
        "on_accent": on_accent.name(), "accent_hover": (t.accent.lighter(110) if t.name == "dark"
                                                       else t.accent.darker(110)).name(),
        "check": _icon_url("check", on_accent),
        "down": _icon_url("chevron_down", t.text), "up": _icon_url("chevron_up", t.text),
        "down_off": _icon_url("chevron_down", t.text_muted),
        "up_off": _icon_url("chevron_up", t.text_muted),
    }
    return _TEMPLATE.format(**v)


_TEMPLATE = """
QWidget {{ color: {text}; selection-background-color: {accent}; selection-color: {on_accent}; }}
QWidget:disabled {{ color: {muted}; }}
QMainWindow, #Board {{ background: {window}; }}
QDialog {{ background: {card}; }}
QLabel {{ background: transparent; }}
#Muted {{ color: {muted}; }}
#DialogError {{ color: {accent}; font-weight: bold; }}
#FieldLabel {{ color: {muted}; font-weight: 600; }}

/* ---- project pane ---- */
#ProjectPane {{ background: {sidebar}; border-right: 1px solid {border}; }}
#PaneTitle {{ color: {muted}; font-size: 8.5pt; font-weight: bold; letter-spacing: 1px; padding: 0 6px; }}
QListWidget#ProjectList {{ background: transparent; border: none; outline: 0; }}
QListWidget#ProjectList::item {{ border-radius: 6px; padding: 0; margin: 1px 0; }}
QListWidget#ProjectList::item:hover {{ background: {hover}; }}
QListWidget#ProjectList::item:selected {{ background: {accent_soft}; color: {text}; }}
#ProjectRow QLabel {{ background: transparent; }}
#ProjectName {{ font-size: 10pt; }}
#ProjectName[current="true"] {{ font-weight: bold; }}
#CountBadge {{ color: {muted}; font-size: 8.5pt; padding: 0 2px; }}

/* ---- board ---- */
#BoardHeader {{ background: {window}; border-bottom: 1px solid {border}; }}
#BoardTitle {{ font-size: 16pt; font-weight: 600; }}
#BoardSubtitle {{ color: {muted}; }}
#EmptyTitle {{ font-size: 13pt; font-weight: 600; }}
#EmptyText {{ color: {muted}; }}

/* ---- cards ---- */
#CardTitle {{ font-size: 10.5pt; font-weight: 600; }}
#CardTitle[done="true"] {{ color: {muted}; }}
#CardNotes {{ color: {muted}; }}
QToolButton#CardAction {{ background: transparent; border: none; border-radius: 4px; padding: 3px; }}
QToolButton#CardAction:hover {{ background: {hover}; }}

/* ---- buttons ---- */
QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 3px; }}
QToolButton:hover {{ background: {hover}; }}
QToolButton:pressed {{ background: {hover}; border-color: {border}; }}
QPushButton {{
    background: {card}; border: 1px solid {border}; border-radius: 6px;
    padding: 5px 14px; min-width: 56px;
}}
QPushButton:hover {{ background: {hover}; }}
QPushButton:pressed {{ background: {hover}; border-color: {accent}; }}
QPushButton:focus {{ border-color: {accent}; }}
QPushButton:disabled {{ background: {window}; color: {muted}; border-color: {border}; }}
QPushButton#PrimaryButton {{
    background: {accent}; color: {on_accent}; border: 1px solid {accent}; font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{ background: {accent_hover}; border-color: {accent_hover}; }}
QPushButton#PrimaryButton:disabled {{ background: {border}; border-color: {border}; color: {muted}; }}
QPushButton#NewProjectButton {{
    background: transparent; border: 1px dashed {border}; text-align: left; padding: 6px 10px;
}}
QPushButton#NewProjectButton:hover {{ background: {hover}; border-color: {accent}; }}
QPushButton#QuickDate {{ min-width: 0; padding: 3px 10px; border-radius: 11px; }}
QPushButton#Segment {{ min-width: 0; padding: 4px 12px; border-radius: 0; margin: 0; }}
QPushButton#Segment[first="true"] {{ border-top-left-radius: 6px; border-bottom-left-radius: 6px; }}
QPushButton#Segment[last="true"] {{ border-top-right-radius: 6px; border-bottom-right-radius: 6px; }}
QPushButton#Segment:checked {{ background: {accent_soft}; border-color: {accent}; font-weight: 600; }}

/* ---- inputs ---- */
QLineEdit, QAbstractSpinBox, QComboBox {{
    background: {card}; border: 1px solid {border}; border-radius: 6px;
    padding: 4px 8px; min-height: 18px;
}}
QLineEdit:focus, QAbstractSpinBox:focus, QComboBox:focus, QComboBox:on {{ border-color: {accent}; }}
QLineEdit:disabled, QAbstractSpinBox:disabled, QComboBox:disabled {{ background: {window}; color: {muted}; }}
QLineEdit#SearchBar {{ border-radius: 15px; padding: 4px 12px; }}
QLineEdit#TitleEdit {{ font-size: 11pt; padding: 6px 8px; }}

QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
    subcontrol-origin: border; width: 18px; border: none; border-left: 1px solid {border}; background: transparent;
}}
QAbstractSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: 6px; }}
QAbstractSpinBox::down-button {{ subcontrol-position: bottom right; border-bottom-right-radius: 6px; }}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{ background: {hover}; }}
QAbstractSpinBox::up-arrow {{ image: {up}; width: 9px; height: 9px; }}
QAbstractSpinBox::down-arrow {{ image: {down}; width: 9px; height: 9px; }}
QAbstractSpinBox::up-arrow:disabled, QAbstractSpinBox::up-arrow:off {{ image: {up_off}; }}
QAbstractSpinBox::down-arrow:disabled, QAbstractSpinBox::down-arrow:off {{ image: {down_off}; }}
QDateEdit {{ padding-right: 24px; }}
QDateEdit::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 22px; border: none; }}
QDateEdit::down-arrow {{ image: {down}; width: 11px; height: 11px; }}
QDateEdit::down-arrow:disabled {{ image: {down_off}; }}

QComboBox {{ padding-right: 24px; }}
QComboBox:hover {{ border-color: {accent}; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 22px; border: none; }}
QComboBox::down-arrow {{ image: {down}; width: 11px; height: 11px; }}
QComboBox::down-arrow:disabled {{ image: {down_off}; }}
QComboBox QAbstractItemView {{
    background: {card}; border: 1px solid {border}; padding: 2px; outline: 0;
    selection-background-color: {hover}; selection-color: {text};
}}

QCheckBox {{ background: transparent; spacing: 6px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px; border: 1.5px solid {muted}; border-radius: 4px; background: {card};
}}
QCheckBox::indicator:hover {{ border-color: {accent}; }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; image: {check}; }}
QCheckBox::indicator:disabled {{ background: {window}; border-color: {border}; }}
QCheckBox#DoneBox::indicator {{ width: 17px; height: 17px; border-radius: 9px; }}

QPlainTextEdit, QTextEdit {{ background: {card}; border: 1px solid {border}; border-radius: 6px; padding: 2px; }}
QPlainTextEdit:focus, QTextEdit:focus {{ border-color: {accent}; }}

/* ---- calendar popup ---- */
QCalendarWidget QWidget {{ alternate-background-color: {window}; }}
QCalendarWidget QToolButton {{ color: {text}; padding: 4px 8px; }}
QCalendarWidget QMenu {{ background: {card}; }}
QCalendarWidget QAbstractItemView:enabled {{
    background: {card}; color: {text}; selection-background-color: {accent}; selection-color: {on_accent};
}}
QCalendarWidget QAbstractItemView:disabled {{ color: {muted}; }}
#qt_calendar_navigationbar {{ background: {sidebar}; }}

/* ---- menus ---- */
QMenu {{ background: {card}; border: 1px solid {border}; padding: 4px; }}
QMenu::item {{ background: transparent; padding: 5px 24px 5px 12px; border-radius: 4px; }}
QMenu::item:selected {{ background: {hover}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 4px 6px; }}

/* ---- scrolling and splitting ---- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget#qt_scrollarea_viewport, QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle {{ background: {border}; border-radius: 3px; margin: 2px; }}
QScrollBar::handle:vertical {{ min-height: 24px; }}
QScrollBar::handle:horizontal {{ min-width: 24px; }}
QScrollBar::handle:hover, QScrollBar::handle:pressed {{ background: {muted}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; background: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QAbstractScrollArea::corner {{ background: transparent; }}
QSplitter::handle {{ background: {border}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:hover {{ background: {accent}; }}

QToolTip {{ background: {card}; color: {text}; border: 1px solid {border}; padding: 4px 6px; }}
"""
