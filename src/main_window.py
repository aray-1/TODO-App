"""The application window: project pane on the left, the TODO board on the right."""
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QSplitter

from data import settings
from data.icons import app_icon
from data.paths import user_data_dir
from data.qss import build_qss
from data.theme import theme_manager
from src.board.todo_board import TodoBoard
from src.dialogs.project_dialog import ProjectDialog
from src.dialogs.todo_dialog import TodoDialog
from src.model.store import Store
from src.sidebar.project_pane import ProjectPane

APP_NAME = "TODO App"
DATA_FILE = "todos.json"


class MainWindow(QMainWindow):
    def __init__(self, store: Store | None = None):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon("app"))
        self.store = store or Store(user_data_dir() / DATA_FILE, self)

        self.pane = ProjectPane(self.store)
        self.board = TodoBoard(self.store)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.pane)
        self.splitter.addWidget(self.board)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([250, 1050])
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(1)
        self.pane.setMinimumWidth(190)
        self.setCentralWidget(self.splitter)
        self.resize(1300, 820)

        self.pane.project_selected.connect(self._on_project_selected)
        self.pane.new_project_requested.connect(self.new_project)
        self.pane.rename_requested.connect(self.rename_project)
        self.pane.delete_requested.connect(self.delete_project)
        self.board.new_todo_requested.connect(self.new_todo)
        self.board.new_project_requested.connect(self.new_project)
        self.board.edit_requested.connect(self.edit_todo)
        self.board.delete_requested.connect(self.delete_todo)
        QShortcut(QKeySequence("Ctrl+N"), self, self.new_todo)
        QShortcut(QKeySequence("Ctrl+Shift+N"), self, self.new_project)
        QShortcut(QKeySequence("Ctrl+F"), self, self.board.search.setFocus)

        theme_manager().changed.connect(self._apply_theme)
        self._apply_theme()
        self.pane.select(settings.get("last_project"))
        self.board.set_project(self.pane.current_project())

        geometry = settings.get("geometry")
        if geometry:
            self.restoreGeometry(QByteArray.fromBase64(geometry.encode("ascii")))
        if self.store.recovered_from is not None:
            QMessageBox.warning(
                self, APP_NAME,
                "The saved TODOs could not be read, so the app started empty.\n\n"
                f"The unreadable file was kept as:\n{self.store.recovered_from}")

    # -- projects
    def _on_project_selected(self, project_id) -> None:
        settings.put("last_project", project_id)
        self.board.set_project(project_id)

    def new_project(self) -> None:
        dialog = ProjectDialog(existing=[p.name for p in self.store.projects], parent=self)
        if dialog.exec():
            project = self.store.add_project(dialog.name())
            self.pane.select(project.id)

    def rename_project(self, project_id: str) -> None:
        project = self.store.project(project_id)
        if project is None:
            return
        dialog = ProjectDialog(project.name, [p.name for p in self.store.projects], self)
        if dialog.exec():
            self.store.rename_project(project_id, dialog.name())

    def delete_project(self, project_id: str) -> None:
        project = self.store.project(project_id)
        if project is None:
            return
        count = len(self.store.todos_of(project_id))
        detail = f" and its {count} TODO{'s' if count != 1 else ''}" if count else ""
        answer = QMessageBox.question(
            self, "Delete project", f"Delete “{project.name}”{detail}? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if answer == QMessageBox.Yes:
            self.store.delete_project(project_id)

    # -- todos
    def new_todo(self) -> None:
        if not self.store.projects:
            self.new_project()
            if not self.store.projects:
                return
        project_id = self.pane.current_project() or self.store.projects[0].id
        TodoDialog(self.store, project_id, parent=self).exec()

    def edit_todo(self, todo_id: str) -> None:
        todo = self.store.todo(todo_id)
        if todo is not None:
            TodoDialog(self.store, todo=todo, parent=self).exec()

    def delete_todo(self, todo_id: str) -> None:
        todo = self.store.todo(todo_id)
        if todo is None:
            return
        answer = QMessageBox.question(self, "Delete TODO", f"Delete “{todo.title}”?",
                                      QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if answer == QMessageBox.Yes:
            self.store.delete_todo(todo_id)

    # -- window
    def _apply_theme(self) -> None:
        QApplication.instance().setStyleSheet(build_qss(theme_manager().theme))

    def closeEvent(self, event):
        settings.put("geometry", bytes(self.saveGeometry().toBase64()).decode("ascii"))
        super().closeEvent(event)
