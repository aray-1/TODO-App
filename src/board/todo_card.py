"""One floating TODO card: an urgency stripe, a done checkbox, the title, a line
of notes and chips for the module, urgency, deadline and (in "All") project."""
from datetime import date

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QCheckBox, QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
                               QLabel, QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from data.icons import icon
from data.theme import theme_manager
from src.board.flow_layout import FlowLayout
from src.model.store import URGENCY_LABELS, Todo, deadline_state

CARD_WIDTH = 264          # minimum (and preferred) width; the board stretches cards to fill rows
CARD_MAX_WIDTH = 380
RADIUS = 10
STRIPE = 4
INDENT = 25               # notes and chips line up with the title, past the done box


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
        layout.setContentsMargins(7, 2, 8, 2)
        layout.setSpacing(4)
        if icon_name:
            glyph = QLabel()
            glyph.setPixmap(icon(icon_name, fg).pixmap(12, 12))
            layout.addWidget(glyph)
        label = QLabel(text)
        layout.addWidget(label)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


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
        self._stripe = theme.urgency(todo.urgency) or theme.border
        self.setMinimumWidth(CARD_WIDTH)
        policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setCursor(Qt.PointingHandCursor)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 2)
        shadow.setColor(theme.shadow)
        self.setGraphicsEffect(shadow)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(STRIPE + 12, 10, 8, 12)
        outer.setSpacing(6)

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
        self.title = QLabel(todo.title)
        self.title.setObjectName("CardTitle")
        self.title.setWordWrap(True)
        self.title.setProperty("done", todo.done)
        if todo.done:
            font = self.title.font()
            font.setStrikeOut(True)
            self.title.setFont(font)
        self.title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top.addWidget(self.title, 1)
        # Edit / delete float over the top-right corner on hover (outside the layout,
        # so the title can use the full width when they are hidden).
        self.actions = QWidget(self)
        self.actions.setObjectName("CardActions")
        self.actions.setAttribute(Qt.WA_StyledBackground, True)
        self.actions.setStyleSheet(f"#CardActions {{ background: {theme.card.name()}; border-radius: 6px; }}")
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

        # -- notes (first line, elided to the card's width in resizeEvent)
        self._first_note = todo.notes.strip().splitlines()[0] if todo.notes.strip() else ""
        if self._first_note:
            self.notes = QLabel(self._first_note)
            self.notes.setObjectName("CardNotes")
            self.notes.setToolTip(todo.notes.strip())
            self.notes.setContentsMargins(INDENT, 0, 0, 0)
            self.notes.setMinimumWidth(1)
            self.notes.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            outer.addWidget(self.notes)
        else:
            self.notes = None

        # -- chips
        self.chips = []
        state = deadline_state(todo, today)
        if todo.deadline:
            if state == "overdue":
                fg = theme.overdue
            elif state in ("today", "soon") and not todo.done:
                fg = theme.due_soon
            else:
                fg = theme.text_muted
            self._add_chip(format_deadline(todo.deadline, state, today), fg, theme, "calendar",
                           f"deadline:{state}")
        if todo.urgency:
            self._add_chip(URGENCY_LABELS[todo.urgency], theme.urgency(todo.urgency), theme,
                           None, f"urgency:{todo.urgency}")
        if todo.module.strip():
            self.chips.append(Chip(f"# {todo.module.strip()}", theme.accent, theme.accent_soft,
                                   kind="module"))
        if project_name:
            self.chips.append(Chip(project_name, theme.text_muted, theme.hover, "folder",
                                   kind="project"))
        if self.chips:
            holder = QWidget()
            flow = FlowLayout(holder, spacing=6)
            flow.setContentsMargins(INDENT, 2, 0, 0)
            for chip in self.chips:
                flow.addWidget(chip)
            policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            policy.setHeightForWidth(True)
            holder.setSizePolicy(policy)
            outer.addWidget(holder)

    def _add_chip(self, text, fg, theme, icon_name, kind):
        # On the light theme the saturated colours need a darker tone for text.
        text_color = fg.darker(135) if theme.name == "light" and kind.startswith(
            ("urgency:medium", "deadline:today", "deadline:soon")) else fg
        alpha = 0.16 if theme.name == "light" else 0.22
        self.chips.append(Chip(text, text_color, blend(fg, theme.card, alpha), icon_name, kind))

    def chip_kinds(self) -> list[str]:
        return [chip.kind for chip in self.chips]

    def heightForWidth(self, width):
        return self.layout().heightForWidth(width)

    def sizeHint(self):
        return QSize(CARD_WIDTH, self.layout().heightForWidth(CARD_WIDTH))

    # -- painting and interaction
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.actions.move(self.width() - self.actions.width() - 6, 6)
        self.actions.raise_()
        if self.notes is not None:
            width = self.notes.width() - INDENT
            self.notes.setText(QFontMetrics(self.notes.font()).elidedText(
                self._first_note, Qt.ElideRight, max(20, width)))

    def paintEvent(self, _event):
        theme = theme_manager().theme
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, RADIUS, RADIUS)
        painter.fillPath(path, theme.card)
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
