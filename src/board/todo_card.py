"""One floating TODO card: an urgency stripe, a done checkbox, the title, a line
of notes and chips for the module, urgency, deadline and (in "All") project.

All cards on the board have the same size: the title and the notes get two lines
each and the chips one row. Longer text fades out at the cut (the full text is in
the tooltip); a long module or project name is shortened with "…"."""
from datetime import date

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFontMetrics, QLinearGradient, QPainter, QPainterPath,
                           QPalette, QPen, QTextLayout)
from PySide6.QtWidgets import (QCheckBox, QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
                               QLabel, QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from data.icons import icon
from data.theme import theme_manager
from src.model.store import URGENCY_LABELS, Todo, deadline_state

CARD_WIDTH = 264          # minimum (and preferred) width; the board stretches cards to fill rows
CARD_MAX_WIDTH = 380
RADIUS = 10
STRIPE = 4
INDENT = 25               # notes and chips line up with the title, past the done box
TITLE_LINES = 2
NOTES_LINES = 2
CHIP_HEIGHT = 20
CHIP_SPACING = 6
PAD_TOP, PAD_BOTTOM, SPACING = 10, 12, 6


FADE = 56                 # width of the fade-out at the end of cut-off text


class FadeText(QWidget):
    """Word-wrapped text limited to ``lines`` lines. Text that does not fit is cut
    after the last line, which fades out into the card instead of ending in "…";
    the full text is then the tooltip. Font and colour come from the stylesheet
    (its object name), like a QLabel's."""

    def __init__(self, text: str, lines: int, object_name: str, indent: int = 0,
                 shrink: bool = False, parent=None):
        """``shrink``: take only the height of the lines the text uses (at least one),
        so what follows moves up; otherwise always ``lines`` lines high."""
        super().__init__(parent)
        self.setObjectName(object_name)
        self.full_text = text
        self.lines = lines
        self.shrink = shrink
        self.truncated = False
        self.background = None            # the card's colour (default: theme.card)
        self.strike = False               # strike the text through (a completed TODO)
        self.setContentsMargins(indent, 0, 0, 0)
        self.setMinimumWidth(1)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

    def line_height(self) -> int:
        self.ensurePolished()
        return QFontMetrics(self.font()).lineSpacing()

    def fix_height(self) -> int:
        """Set and return the full height (``lines`` lines); a shrinking text gives
        back what it does not use once it knows its width."""
        height = self.lines * self.line_height()
        self.setFixedHeight(height)
        return height

    def _layout(self, width: float):
        """The laid-out lines (at most ``lines`` + 1, to know whether it is cut)."""
        text = self.full_text.strip().replace("\r\n", "\n").replace("\n", " ")
        layout = QTextLayout(text, self.font())
        layout.beginLayout()
        lines, y = [], 0.0
        while len(lines) <= self.lines:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(width)
            line.setPosition(QPointF(0, y))
            y += QFontMetrics(self.font()).lineSpacing()
            lines.append(line)
        layout.endLayout()
        return layout, lines

    def resizeEvent(self, event):
        super().resizeEvent(event)
        _layout, lines = self._layout(max(1, self.contentsRect().width()))
        self.truncated = len(lines) > self.lines
        self.setToolTip(self.full_text.strip() if self.truncated else "")
        if self.shrink:                       # the width is unchanged, so this settles
            height = max(1, min(len(lines), self.lines)) * self.line_height()
            if height != self.height():
                self.setFixedHeight(height)

    def paintEvent(self, _event):
        rect = self.contentsRect()
        layout, lines = self._layout(max(1, rect.width()))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setPen(self.palette().color(QPalette.WindowText))
        origin = QPointF(rect.left(), rect.top())
        metrics = QFontMetrics(self.font())
        for line in lines[:self.lines]:
            line.draw(painter, origin)
            if self.strike:   # drawn here: the stylesheet re-sets the font, dropping strike-out
                y = origin.y() + line.y() + line.ascent() - metrics.strikeOutPos() + 0.5
                width = min(line.naturalTextWidth(), rect.width())
                painter.save()
                painter.setPen(QPen(self.palette().color(QPalette.WindowText), max(1, metrics.lineWidth())))
                painter.drawLine(QPointF(origin.x(), y), QPointF(origin.x() + width, y))
                painter.restore()
        if len(lines) > self.lines:
            # fade the end of the last visible line into the card's background
            last = lines[self.lines - 1]
            end = rect.left() + min(last.naturalTextWidth(), rect.width())
            top = rect.top() + last.y()
            fade = QRectF(end - FADE, top, FADE + 1, last.height() + 1)
            card = QColor(self.background or theme_manager().theme.card)
            gradient = QLinearGradient(fade.left(), 0, fade.right(), 0)
            clear = QColor(card)
            clear.setAlpha(0)
            gradient.setColorAt(0.0, clear)
            gradient.setColorAt(1.0, card)
            painter.fillRect(fade, gradient)
        painter.end()


def blend(fg: QColor, bg: QColor, alpha: float) -> QColor:
    """``fg`` laid over ``bg`` at ``alpha`` (an opaque colour)."""
    return QColor(round(fg.red() * alpha + bg.red() * (1 - alpha)),
                  round(fg.green() * alpha + bg.green() * (1 - alpha)),
                  round(fg.blue() * alpha + bg.blue() * (1 - alpha)))


def format_deadline(deadline: str, state: str | None, today: date | None = None) -> str:
    today = today or date.today()
    due = date.fromisoformat(deadline)
    if state == "today":
        return "Due today"
    if state == "soon":
        return "Due tomorrow"
    text = f"{due.day} {due:%b}" + (f" {due.year}" if due.year != today.year else "")
    return f"Overdue · {text}" if state == "overdue" else text


def format_completed(completed: str | None, today: date | None = None) -> str:
    """"Completed 23 Nov" from the ISO timestamp (just "Completed" if it is unknown)."""
    if not completed:
        return "Completed"
    today = today or date.today()
    done = date.fromisoformat(completed[:10])
    if done == today:
        return "Completed today"
    return f"Completed {done.day} {done:%b}" + (f" {done.year}" if done.year != today.year else "")


class Chip(QWidget):
    """A small rounded label, optionally with a leading icon."""

    def __init__(self, text: str, fg: QColor, bg: QColor, icon_name: str | None = None,
                 kind: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Chip")
        self.kind = kind
        self.text = text
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"#Chip {{ background: {bg.name()}; border-radius: 9px; }}"
                           f"#Chip QLabel {{ color: {fg.name()}; font-size: 8.5pt; font-weight: 600; }}")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 0, 8, 0)
        layout.setSpacing(4)
        self._extra = 7 + 8                  # horizontal margins (+ the icon, below)
        if icon_name:
            glyph = QLabel()
            glyph.setPixmap(icon(icon_name, fg).pixmap(12, 12))
            layout.addWidget(glyph)
            self._extra += 12 + 4
        self.label = QLabel(text)
        layout.addWidget(self.label)
        self.setFixedHeight(CHIP_HEIGHT)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def full_width(self) -> int:
        """The width the chip needs to show its whole text."""
        self.label.ensurePolished()
        return self._extra + QFontMetrics(self.label.font()).horizontalAdvance(self.text) + 2

    def fit(self, width: int) -> None:
        """Shorten the text with "…" so the chip is at most ``width`` wide."""
        self.label.ensurePolished()
        room = max(12, width - self._extra - 2)
        self.label.setText(QFontMetrics(self.label.font()).elidedText(self.text, Qt.ElideRight, room))
        self.setToolTip(self.text if self.label.text() != self.text else "")


class TodoCard(QFrame):
    toggled = Signal(str)
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, todo: Todo, project_name: str | None = None, today: date | None = None,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("TodoCard")
        self.todo_id = todo.id
        self.todo = todo
        self._hover = False
        theme = theme_manager().theme
        # A completed TODO sits back: tinted towards the board, flat (no shadow), a
        # neutral stripe, a green check, a struck-through title and muted chips.
        self.done = todo.done
        self._background = blend(theme.card, theme.window, 0.6) if todo.done else theme.card
        self._stripe = theme.border if todo.done else (theme.urgency(todo.urgency) or theme.border)
        self.setMinimumWidth(CARD_WIDTH)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

        if not todo.done:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(18)
            shadow.setOffset(0, 2)
            shadow.setColor(theme.shadow)
            self.setGraphicsEffect(shadow)

        # Every card has the same height: a two-line title slot, a one-line notes slot
        # and one row of chips (plus a project row in "All TODOs"). Longer text is
        # shortened with "…" and shown in full in a tooltip.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(STRIPE + 12, PAD_TOP, 8, PAD_BOTTOM)
        outer.setSpacing(SPACING)

        # -- top row: done box, title, hover actions
        top = QHBoxLayout()
        top.setSpacing(8)
        self.done_box = QCheckBox()
        self.done_box.setObjectName("DoneBox")
        self.done_box.setChecked(todo.done)
        self.done_box.setToolTip("Mark as not done" if todo.done else "Mark as done")
        self.done_box.setCursor(Qt.PointingHandCursor)
        self.done_box.clicked.connect(lambda _=False: self.toggled.emit(self.todo_id))
        top.addWidget(self.done_box, 0, Qt.AlignTop)
        self.title = FadeText(" ".join(todo.title.split()), TITLE_LINES, "CardTitle", shrink=True)
        self.title.setProperty("done", todo.done)
        self.title.ensurePolished()               # the stylesheet sets its font
        self.title.strike = todo.done
        self.title.background = self._background
        title_height = self.title.fix_height()
        top.addWidget(self.title, 1, Qt.AlignTop)
        # Edit / delete float over the top-right corner on hover (outside the layout,
        # so the title can use the full width when they are hidden).
        self.actions = QWidget(self)
        self.actions.setObjectName("CardActions")
        self.actions.setAttribute(Qt.WA_StyledBackground, True)
        self.actions.setStyleSheet(f"#CardActions {{ background: {self._background.name()}; border-radius: 6px; }}")
        actions = QHBoxLayout(self.actions)
        actions.setContentsMargins(2, 2, 2, 2)
        actions.setSpacing(0)
        for name, tip, signal in (("edit", "Edit", self.edit_requested),
                                  ("delete", "Delete", self.delete_requested)):
            button = QToolButton()
            button.setObjectName("CardAction")
            button.setIcon(icon(name, theme.text_muted))
            button.setIconSize(QSize(15, 15))
            button.setToolTip(tip)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, s=signal: s.emit(self.todo_id))
            actions.addWidget(button)
        self.actions.adjustSize()
        self.actions.hide()
        outer.addLayout(top)

        # -- notes: two wrapped lines. The slot is kept (empty) when there are no
        # notes, so every card has the same height.
        notes = FadeText(todo.notes, NOTES_LINES, "CardNotes", indent=INDENT)
        notes.background = self._background
        notes_height = notes.fix_height()
        outer.addWidget(notes)
        self.notes = notes if todo.notes.strip() else None
        outer.addStretch(1)

        # -- chips
        self.chips = []
        state = deadline_state(todo, today)
        if todo.done:
            # the deadline and urgency no longer matter: say when it was finished
            self._add_chip(format_completed(todo.completed, today), theme.success, theme, "check",
                           "completed")
        elif todo.deadline:
            if state == "overdue":
                fg = theme.overdue
            elif state in ("today", "soon") and not todo.done:
                fg = theme.due_soon
            else:
                fg = theme.text_muted
            self._add_chip(format_deadline(todo.deadline, state, today), fg, theme, "calendar",
                           f"deadline:{state}")
        if todo.urgency and not todo.done:
            self._add_chip(URGENCY_LABELS[todo.urgency], theme.urgency(todo.urgency), theme,
                           None, f"urgency:{todo.urgency}")
        self.module_chip = None
        if todo.module.strip():
            fg, bg = ((theme.text_muted, theme.hover) if todo.done
                      else (theme.accent, theme.accent_soft))
            self.module_chip = Chip(f"# {todo.module.strip()}", fg, bg, kind="module")
            self.chips.append(self.module_chip)
        # one row of chips, always present (empty when the TODO has none)
        self.chip_row = self._row([c for c in self.chips])
        outer.addWidget(self.chip_row)
        rows = 1
        self.project_chip = None
        if project_name:
            self.project_chip = Chip(project_name, theme.text_muted, theme.hover, "folder",
                                     kind="project")
            self.chips.append(self.project_chip)
            outer.addWidget(self._row([self.project_chip]))
            rows = 2

        height = (PAD_TOP + max(title_height, self.done_box.sizeHint().height()) + SPACING
                  + notes_height + SPACING + rows * CHIP_HEIGHT + (rows - 1) * SPACING
                  + PAD_BOTTOM)
        self.setFixedHeight(height)

    @staticmethod
    def _row(chips) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(INDENT, 0, 0, 0)
        layout.setSpacing(CHIP_SPACING)
        for chip in chips:
            layout.addWidget(chip)
        layout.addStretch(1)
        row.setFixedHeight(CHIP_HEIGHT)
        row.setMinimumWidth(1)
        row.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        return row

    def _add_chip(self, text, fg, theme, icon_name, kind):
        # On the light theme the saturated colours need a darker tone for text.
        text_color = fg.darker(135) if theme.name == "light" and kind.startswith(
            ("urgency:medium", "deadline:today", "deadline:soon")) else fg
        alpha = 0.16 if theme.name == "light" else 0.22
        self.chips.append(Chip(text, text_color, blend(fg, theme.card, alpha), icon_name, kind))

    def chip_kinds(self) -> list[str]:
        return [chip.kind for chip in self.chips]

    def sizeHint(self):
        return QSize(CARD_WIDTH, self.height())

    # -- painting and interaction
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.actions.move(self.width() - self.actions.width() - 6, 6)
        self.actions.raise_()
        self._fit_text()

    def _fit_text(self) -> None:
        """Shorten the module and project chips to the card's width (the title and
        notes cut themselves, see FadeText)."""
        text_width = self.width() - (STRIPE + 12) - 8 - INDENT
        if self.module_chip is not None:
            others = [c for c in self.chips
                      if c.kind.startswith(("deadline", "urgency", "completed"))]
            used = sum(c.sizeHint().width() for c in others) + CHIP_SPACING * len(others)
            self.module_chip.fit(min(self.module_chip.full_width(), text_width - used))
        if self.project_chip is not None:
            self.project_chip.fit(min(self.project_chip.full_width(), text_width))

    def paintEvent(self, _event):
        theme = theme_manager().theme
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, RADIUS, RADIUS)
        painter.fillPath(path, self._background)
        painter.save()
        painter.setClipPath(path)
        painter.fillRect(QRectF(rect.left(), rect.top(), STRIPE, rect.height()), self._stripe)
        painter.restore()
        border = theme.accent if self._hover else theme.border
        painter.setPen(QPen(border, 1))
        painter.drawPath(path)
        painter.end()

    def enterEvent(self, event):
        self._hover = True
        self.actions.show()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.actions.hide()
        self.update()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.edit_requested.emit(self.todo_id)
        super().mouseDoubleClickEvent(event)
