"""The left pane: "All TODOs", then the projects, each with its open-TODO count."""
from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListView, QListWidget, QListWidgetItem, QMenu,
                               QPushButton, QVBoxLayout, QWidget)

from data.icons import icon
from data.theme import theme_manager
from src.model.store import Store

ALL = None                      # the "All TODOs" entry's project id
ROW_HEIGHT = 36


class DashedButton(QPushButton):
    """A flat button with a dashed rounded outline. The outline is painted here,
    half a pixel inside the widget, rather than by the stylesheet: a stylesheet
    dashed border sits on the widget's edge and is cut off at display scales such
    as 125 % or 150 %. The stylesheet draws only the background and the text."""

    RADIUS = 6

    def paintEvent(self, event):
        super().paintEvent(event)
        theme = theme_manager().theme
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # the outline keeps its colour on hover; the stylesheet shades the background
        pen = QPen(theme.border, 1, Qt.CustomDashLine)
        pen.setDashPattern([4, 3])
        pen.setCosmetic(True)
        painter.setPen(pen)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
                            self.RADIUS, self.RADIUS)
        painter.drawPath(path)
        painter.end()


class ProjectRow(QWidget):
    def __init__(self, icon_name: str, name: str, count: int, parent=None):
        super().__init__(parent)
        self.setObjectName("ProjectRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(9)
        glyph = QLabel()
        glyph.setPixmap(icon(icon_name, theme_manager().theme.text_muted).pixmap(16, 16))
        layout.addWidget(glyph)
        self.name = QLabel(name)
        self.name.setObjectName("ProjectName")
        layout.addWidget(self.name, 1)
        self.count = QLabel(str(count) if count else "")
        self.count.setObjectName("CountBadge")
        layout.addWidget(self.count)

    def set_current(self, current: bool) -> None:
        self.name.setProperty("current", current)
        self.name.style().unpolish(self.name)
        self.name.style().polish(self.name)


class ProjectPane(QWidget):
    project_selected = Signal(object)        # project id, or None for "All TODOs"
    new_project_requested = Signal()
    rename_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, store: Store, parent=None):
        super().__init__(parent)
        self.setObjectName("ProjectPane")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.store = store
        self._current = ALL

        title = QLabel("PROJECTS")
        title.setObjectName("PaneTitle")
        self.list = QListWidget()
        self.list.setObjectName("ProjectList")
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setResizeMode(QListView.Adjust)     # rows follow the pane's width
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        self.list.currentItemChanged.connect(self._on_current)
        self.list.itemDoubleClicked.connect(self._on_double_click)

        self.new_button = DashedButton("  New project")
        self.new_button.setObjectName("NewProjectButton")
        self.new_button.setCursor(Qt.PointingHandCursor)
        self.new_button.setToolTip("New project (Ctrl+Shift+N)")
        self.new_button.clicked.connect(self.new_project_requested)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 12)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(self.list, 1)
        layout.addWidget(self.new_button)

        store.projects_changed.connect(self.refresh)
        theme_manager().changed.connect(self.refresh)
        self.refresh()

    # -- state
    def current_project(self):
        return self._current

    def select(self, project_id) -> None:
        for row in range(self.list.count()):
            if self.list.item(row).data(Qt.UserRole) == project_id:
                self.list.setCurrentRow(row)
                return
        self.list.setCurrentRow(0)            # unknown id: fall back to "All TODOs"

    def refresh(self) -> None:
        """Rebuild the rows (names and counts), keeping the selection."""
        current = self._current
        if current is not ALL and self.store.project(current) is None:
            current = ALL                     # the project was deleted: select() reports ALL
        self.new_button.setIcon(icon("plus"))
        self.list.blockSignals(True)
        self.list.clear()
        self._add_row(ALL, "grid", "All TODOs", self.store.open_count(None))
        for project in self.store.projects:
            self._add_row(project.id, "folder", project.name, self.store.open_count(project.id))
        self.list.blockSignals(False)
        self.select(current)

    def _add_row(self, project_id, icon_name, name, count) -> None:
        item = QListWidgetItem()
        item.setData(Qt.UserRole, project_id)
        item.setSizeHint(QSize(0, ROW_HEIGHT))
        item.setToolTip(name)
        self.list.addItem(item)
        self.list.setItemWidget(item, ProjectRow(icon_name, name, count))

    def _on_current(self, item, _previous=None) -> None:
        project_id = item.data(Qt.UserRole) if item else ALL
        for row in range(self.list.count()):
            widget = self.list.itemWidget(self.list.item(row))
            widget.set_current(self.list.item(row) is item)
        if project_id != self._current:
            self._current = project_id
            self.project_selected.emit(project_id)

    def _on_double_click(self, item) -> None:
        project_id = item.data(Qt.UserRole)
        if project_id is not ALL:
            self.rename_requested.emit(project_id)

    def _context_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None or item.data(Qt.UserRole) is ALL:
            return
        project_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        menu.addAction(icon("edit"), "Rename…", lambda: self.rename_requested.emit(project_id))
        menu.addAction(icon("delete"), "Delete…", lambda: self.delete_requested.emit(project_id))
        menu.exec(self.list.viewport().mapToGlobal(pos))
