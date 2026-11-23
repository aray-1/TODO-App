"""The main area: a header with the project name and the view controls, and the
TODO cards floating in a grid that reflows with the width."""
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout,
                               QWidget)

from data import settings
from data.icons import icon
from data.qss import on_color
from data.theme import theme_manager
from src.board.flow_layout import FlowLayout
from src.board.todo_card import CARD_MAX_WIDTH, CARD_WIDTH, TodoCard
from src.model.store import Store, filter_todos, sort_todos
from src.widgets.theme_toggle import ThemeToggle

URGENCY_FILTERS = (("All urgencies", "all"), ("High", "high"), ("Medium", "medium"),
                   ("Low", "low"), ("No urgency", "none"))
SORTS = (("Sort: Deadline", "deadline"), ("Sort: Urgency", "urgency"), ("Sort: Newest", "created"))


class TodoBoard(QWidget):
    new_todo_requested = Signal()
    new_project_requested = Signal()
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, store: Store, parent=None):
        super().__init__(parent)
        self.setObjectName("Board")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.store = store
        self.project_id = None
        self.today = None                     # tests pin "today"; None = the real date
        self.cards: list[TodoCard] = []

        # -- header
        header = QFrame()
        header.setObjectName("BoardHeader")
        self.title = QLabel()
        self.title.setObjectName("BoardTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("BoardSubtitle")
        self.theme_toggle = ThemeToggle()

        self.search = QLineEdit()
        self.search.setObjectName("SearchBar")
        self.search.setPlaceholderText("Search title, notes, module")
        self.search.setClearButtonEnabled(True)
        self._search_icon = QAction(self.search)
        self.search.addAction(self._search_icon, QLineEdit.LeadingPosition)
        self.urgency = QComboBox()
        for text, value in URGENCY_FILTERS:
            self.urgency.addItem(text, value)
        self.sort = QComboBox()
        for text, value in SORTS:
            self.sort.addItem(text, value)
        self.sort.setCurrentIndex(max(0, self.sort.findData(settings.get("sort", "deadline"))))
        self.show_done = QCheckBox("Show completed")
        self.show_done.setChecked(bool(settings.get("show_done", False)))
        self.new_button = QPushButton("  New TODO")
        self.new_button.setObjectName("PrimaryButton")
        self.new_button.setCursor(Qt.PointingHandCursor)
        self.new_button.setToolTip("New TODO (Ctrl+N)")
        self.new_button.clicked.connect(self.new_todo_requested)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        top = QHBoxLayout()
        top.setSpacing(14)
        top.addLayout(titles, 1)
        top.addWidget(self.new_button, 0, Qt.AlignVCenter)
        top.addWidget(self.theme_toggle, 0, Qt.AlignVCenter)
        # The view controls wrap onto a second row when the window is narrow.
        controls = QWidget()
        flow = FlowLayout(controls, spacing=8)
        flow.setContentsMargins(0, 0, 0, 0)
        self.search.setFixedWidth(260)
        for widget in (self.search, self.urgency, self.sort, self.show_done):
            widget.setFixedHeight(30)
            flow.addWidget(widget)
        policy = controls.sizePolicy()
        policy.setHeightForWidth(True)
        controls.setSizePolicy(policy)
        head = QVBoxLayout(header)
        head.setContentsMargins(24, 16, 24, 14)
        head.setSpacing(12)
        head.addLayout(top)
        head.addWidget(controls)

        # -- cards, or an empty state
        self.grid_host = QWidget()
        self.flow = FlowLayout(self.grid_host, spacing=14, column_width=(CARD_WIDTH, CARD_MAX_WIDTH))
        self.flow.setContentsMargins(24, 20, 24, 24)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.grid_host)

        self.empty = QWidget()
        self.empty_title = QLabel()
        self.empty_title.setObjectName("EmptyTitle")
        self.empty_text = QLabel()
        self.empty_text.setObjectName("EmptyText")
        self.empty_button = QPushButton()
        self.empty_button.setObjectName("PrimaryButton")
        self.empty_button.setCursor(Qt.PointingHandCursor)
        self.empty_button.clicked.connect(self._empty_action)
        empty = QVBoxLayout(self.empty)
        empty.addStretch(2)
        for widget in (self.empty_title, self.empty_text):
            widget.setAlignment(Qt.AlignCenter)
            empty.addWidget(widget)
        empty.addSpacing(10)
        empty.addWidget(self.empty_button, 0, Qt.AlignHCenter)
        empty.addStretch(3)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.scroll)
        self.stack.addWidget(self.empty)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addWidget(self.stack, 1)

        # Typing in the search box refreshes after a short pause, not per key.
        self._search_timer = QTimer(self, singleShot=True, interval=150)
        self._search_timer.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda _t: self._search_timer.start())
        self.urgency.currentIndexChanged.connect(self.refresh)
        self.sort.currentIndexChanged.connect(self._sort_changed)
        self.show_done.toggled.connect(self._show_done_changed)
        store.todos_changed.connect(self.refresh)
        store.projects_changed.connect(self._update_header)
        theme_manager().changed.connect(self._apply_theme)
        self._apply_theme()

    # -- public
    def set_project(self, project_id) -> None:
        self.project_id = project_id
        self.refresh()

    def refresh(self) -> None:
        """Rebuild the cards for the current project and filters."""
        self._update_header()
        todos = filter_todos(self.store.todos_of(self.project_id), self.search.text(),
                             self.urgency.currentData(), self.show_done.isChecked())
        todos = sort_todos(todos, self.sort.currentData())
        self.flow.clear()
        self.cards = []
        names = {p.id: p.name for p in self.store.projects}
        for todo in todos:
            card = TodoCard(todo, names.get(todo.project_id) if self.project_id is None else None,
                            self.today)
            card.toggled.connect(self.store.toggle_done)
            card.edit_requested.connect(self.edit_requested)
            card.delete_requested.connect(self.delete_requested)
            self.flow.addWidget(card)
            self.cards.append(card)
        self._update_empty_state(bool(todos))

    # -- internals
    def _update_header(self) -> None:
        project = self.store.project(self.project_id) if self.project_id else None
        if self.project_id is not None and project is None:
            self.project_id = None
        self.title.setText(project.name if project else "All TODOs")
        todos = self.store.todos_of(self.project_id)
        open_count = sum(1 for t in todos if not t.done)
        done_count = len(todos) - open_count
        self.subtitle.setText(f"{open_count} open · {done_count} completed")
        self.new_button.setEnabled(bool(self.store.projects))

    def _update_empty_state(self, has_cards: bool) -> None:
        if has_cards:
            self.stack.setCurrentWidget(self.scroll)
            return
        self._empty_kind = "todo"
        if not self.store.projects:
            self._empty_kind = "project"
            self.empty_title.setText("No projects yet")
            self.empty_text.setText("Create a project to start collecting TODOs.")
            self.empty_button.setText("  New project")
        elif self.store.todos_of(self.project_id) and (self.search.text().strip()
                                                       or self.urgency.currentData() != "all"
                                                       or not self.show_done.isChecked()):
            self.empty_title.setText("Nothing to show")
            self.empty_text.setText("No TODOs match the search or filters.")
            self.empty_button.setText("  New TODO")
        else:
            self.empty_title.setText("No TODOs here")
            self.empty_text.setText("Add the first one — only a title is needed.")
            self.empty_button.setText("  New TODO")
        self.stack.setCurrentWidget(self.empty)

    def _empty_action(self) -> None:
        if self._empty_kind == "project":
            self.new_project_requested.emit()
        else:
            self.new_todo_requested.emit()

    def _sort_changed(self) -> None:
        settings.put("sort", self.sort.currentData())
        self.refresh()

    def _show_done_changed(self, checked: bool) -> None:
        settings.put("show_done", checked)
        self.refresh()

    def _apply_theme(self) -> None:
        theme = theme_manager().theme
        self.new_button.setIcon(icon("plus", on_color(theme.accent, (theme.card, theme.text, theme.window))))
        self.new_button.setIconSize(QSize(14, 14))
        self.empty_button.setIcon(self.new_button.icon())
        self._search_icon.setIcon(icon("search", theme.text_muted))
        self.refresh()                        # cards paint chips and shadows in theme colours
