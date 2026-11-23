"""Sliding switch that changes between the light and dark theme (from Circuit Design Assistant)."""
from PySide6.QtCore import QEasingCurve, QPointF, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton

from data.icons import icon
from data.theme import theme_manager


class ThemeToggle(QAbstractButton):
    """A track with a round knob: left with a sun in the light theme, right with a
    moon in the dark theme. Clicking it (or Space when focused) slides the knob
    across and switches the theme."""

    TRACK_W, TRACK_H = 40, 18       # the switch itself
    PAD = 3                         # room around the track for its border and focus ring, so
                                    # nothing is cut at the widget's edge at any display scale
    MARGIN = 0                      # no extra space: the header lays it out
    WIDTH = PAD + TRACK_W + PAD     # 46
    HEIGHT = PAD + TRACK_H + PAD    # 24

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ThemeToggle")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self.setFixedSize(self.WIDTH + self.MARGIN, self.HEIGHT)
        self._pos = 0.0             # knob position: 0 = left (light), 1 = right (dark)
        self._keyboard_focus = False  # draw the focus ring only when reached with Tab
        self._anim = QVariantAnimation(self, duration=160,
                                       easingCurve=QEasingCurve(QEasingCurve.InOutCubic))
        self._anim.valueChanged.connect(self._move)
        self.clicked.connect(lambda _checked=False: theme_manager().toggle())
        theme_manager().changed.connect(self._sync)
        self._sync(animate=False)

    def sizeHint(self):
        return QSize(self.WIDTH + self.MARGIN, self.HEIGHT)

    def _move(self, value) -> None:
        self._pos = float(value)
        self.update()

    def _sync(self, animate=True) -> None:
        dark = theme_manager().theme.name == "dark"
        self.blockSignals(True)
        self.setChecked(dark)
        self.blockSignals(False)
        self.setToolTip("Switch to the light theme" if dark else "Switch to the dark theme")
        self.setAccessibleName("Dark theme" if dark else "Light theme")
        target = 1.0 if dark else 0.0
        self._anim.stop()
        if animate and self.isVisible():
            self._anim.setStartValue(self._pos)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._move(target)

    def paintEvent(self, _event):
        theme = theme_manager().theme
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track = QRectF(self.PAD, self.PAD, self.TRACK_W, self.TRACK_H)
        radius = track.height() / 2
        # The track tints towards the accent as the knob moves to the dark side.
        off, on = theme.border, theme.accent      # border: a step darker than the menu bar
        t = self._pos
        fill = QColor(round(off.red() + (on.red() - off.red()) * t),
                      round(off.green() + (on.green() - off.green()) * t),
                      round(off.blue() + (on.blue() - off.blue()) * t))
        if self.underMouse():
            fill = fill.lighter(108) if theme.name == "dark" else fill.darker(104)
        painter.setPen(QPen(fill.darker(112), 1))
        painter.setBrush(fill)
        painter.drawRoundedRect(track, radius, radius)
        if self.hasFocus() and self._keyboard_focus:
            painter.setPen(QPen(theme.accent, 1.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(track.adjusted(-2, -2, 2, 2), radius + 2, radius + 2)
        knob_d = track.height() - 4
        x = track.left() + 2 + (track.width() - 4 - knob_d) * self._pos
        knob = QRectF(x, track.top() + 2, knob_d, knob_d)
        painter.setPen(QPen(theme.border, 1))
        painter.setBrush(theme.card)
        painter.drawEllipse(knob)
        glyph = icon("moon" if self._pos >= 0.5 else "sun")
        glyph.paint(painter, knob.adjusted(3, 3, -3, -3).toRect(), Qt.AlignCenter)
        painter.end()

    def focusInEvent(self, event):
        self._keyboard_focus = event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._keyboard_focus = False
        super().focusOutEvent(event)

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def hitButton(self, pos) -> bool:
        return QRectF(0, 0, self.WIDTH, self.HEIGHT).contains(QPointF(pos))
