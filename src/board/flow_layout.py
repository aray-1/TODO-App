"""A layout that places widgets left to right and wraps them onto new rows,
like words in a paragraph (a port of Qt's Flow Layout example)."""
from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout


class FlowLayout(QLayout):
    """With ``column_width=(minimum, maximum)`` every item gets the same width,
    stretched so that as many columns as fit fill the row (a card grid)."""

    def __init__(self, parent=None, spacing: int = 12, column_width=None):
        super().__init__(parent)
        self._items = []
        self._spacing = spacing
        self._columns = column_width

    # -- QLayout interface
    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, apply=True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    # -- helpers
    def clear(self) -> None:
        """Remove and delete every widget in the layout."""
        while self._items:
            item = self._items.pop()
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _do_layout(self, rect: QRect, apply: bool) -> int:
        m: QMargins = self.contentsMargins()
        area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, row_height = area.x(), area.y(), 0
        uniform = None
        if self._columns:
            low, high = self._columns
            columns = max(1, (area.width() + self._spacing) // (low + self._spacing))
            uniform = min(high, max(low, (area.width() - (columns - 1) * self._spacing) // columns))
        for item in self._items:
            if item.widget() is not None and item.widget().isHidden():
                continue
            hint = item.sizeHint()
            if uniform is not None:
                hint.setWidth(uniform)
            if item.hasHeightForWidth():
                hint.setHeight(item.heightForWidth(hint.width()))
            next_x = x + hint.width() + self._spacing
            if next_x - self._spacing > area.right() + 1 and row_height > 0:
                x = area.x()
                y += row_height + self._spacing
                next_x = x + hint.width() + self._spacing
                row_height = 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            row_height = max(row_height, hint.height())
        return y + row_height - rect.y() + m.bottom()
