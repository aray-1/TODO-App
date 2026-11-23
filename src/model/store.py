"""Projects and TODOs, kept in one JSON file and saved on every change.

``Store`` owns the data; the views listen to ``projects_changed`` and
``todos_changed``. The free functions (``filter_todos``, ``sort_todos``,
``deadline_state``) are pure so they can be tested without any widgets.
"""
import json
import os
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QObject, Signal

URGENCIES = ("high", "medium", "low")          # most urgent first; None = not set
URGENCY_LABELS = {"high": "High", "medium": "Medium", "low": "Low"}
FILE_VERSION = 1


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id() -> str:
    return uuid.uuid4().hex


@dataclass
class Project:
    name: str
    id: str = field(default_factory=_new_id)
    created: str = field(default_factory=_now)


@dataclass
class Todo:
    project_id: str
    title: str
    notes: str = ""
    module: str = ""
    urgency: str | None = None          # "high" | "medium" | "low" | None
    deadline: str | None = None         # ISO date "YYYY-MM-DD" | None
    done: bool = False
    id: str = field(default_factory=_new_id)
    created: str = field(default_factory=_now)
    completed: str | None = None


def _from_dict(cls, raw: dict):
    """Build a dataclass from a dict, ignoring unknown keys (newer files)."""
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in raw.items() if k in names})


# -- pure helpers -------------------------------------------------------------------
def deadline_state(todo: Todo, today: date | None = None) -> str | None:
    """"overdue", "today", "soon" (tomorrow), "later", or None without a deadline.
    A completed TODO is never overdue."""
    if not todo.deadline:
        return None
    today = today or date.today()
    due = date.fromisoformat(todo.deadline)
    if due < today:
        return "later" if todo.done else "overdue"
    if due == today:
        return "today"
    if due == today + timedelta(days=1):
        return "soon"
    return "later"


def _urgency_rank(todo: Todo) -> int:
    return URGENCIES.index(todo.urgency) if todo.urgency in URGENCIES else len(URGENCIES)


def sort_todos(todos, key: str = "deadline"):
    """Open TODOs first, then by ``key``:
    "deadline": earliest first, undated last, ties by urgency;
    "urgency": High > Medium > Low > none, ties by deadline;
    "created": newest first."""
    far = date.max.isoformat()
    if key == "urgency":
        order = lambda t: (t.done, _urgency_rank(t), t.deadline or far, t.created)  # noqa: E731
    elif key == "created":
        return sorted(sorted(todos, key=lambda t: t.created, reverse=True), key=lambda t: t.done)
    else:
        order = lambda t: (t.done, t.deadline or far, _urgency_rank(t), t.created)  # noqa: E731
    return sorted(todos, key=order)


def filter_todos(todos, text: str = "", urgency: str = "all", show_done: bool = False):
    """``urgency``: "all", one of URGENCIES, or "none" for TODOs without one."""
    needle = text.strip().casefold()
    result = []
    for t in todos:
        if t.done and not show_done:
            continue
        if urgency == "none" and t.urgency is not None:
            continue
        if urgency in URGENCIES and t.urgency != urgency:
            continue
        if needle and needle not in f"{t.title}\n{t.notes}\n{t.module}".casefold():
            continue
        result.append(t)
    return result


# -- the store ---------------------------------------------------------------------
class Store(QObject):
    projects_changed = Signal()
    todos_changed = Signal()

    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.projects: list[Project] = []
        self.todos: list[Todo] = []
        self.recovered_from: Path | None = None   # set when an unreadable file was moved aside
        self._load()

    # -- persistence
    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            projects = [_from_dict(Project, p) for p in raw.get("projects", [])]
            todos = [_from_dict(Todo, t) for t in raw.get("todos", [])]
        except (OSError, ValueError, TypeError, AttributeError):
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = self.path.with_name(f"{self.path.stem}.corrupt-{stamp}{self.path.suffix}")
            os.replace(self.path, backup)
            self.recovered_from = backup
            return
        self.projects, self.todos = projects, todos

    def save(self) -> None:
        data = {"version": FILE_VERSION,
                "projects": [asdict(p) for p in self.projects],
                "todos": [asdict(t) for t in self.todos]}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    # -- projects
    def project(self, project_id: str) -> Project | None:
        return next((p for p in self.projects if p.id == project_id), None)

    def add_project(self, name: str) -> Project:
        project = Project(name=name.strip())
        self.projects.append(project)
        self.save()
        self.projects_changed.emit()
        return project

    def rename_project(self, project_id: str, name: str) -> None:
        project = self.project(project_id)
        if project and name.strip() and name.strip() != project.name:
            project.name = name.strip()
            self.save()
            self.projects_changed.emit()
            self.todos_changed.emit()      # the "All" view shows project names on cards

    def delete_project(self, project_id: str) -> None:
        """Delete a project and all of its TODOs."""
        self.projects = [p for p in self.projects if p.id != project_id]
        self.todos = [t for t in self.todos if t.project_id != project_id]
        self.save()
        self.projects_changed.emit()
        self.todos_changed.emit()

    # -- todos
    def todo(self, todo_id: str) -> Todo | None:
        return next((t for t in self.todos if t.id == todo_id), None)

    def todos_of(self, project_id: str | None):
        """The TODOs of one project, or of every project when ``project_id`` is None."""
        if project_id is None:
            return list(self.todos)
        return [t for t in self.todos if t.project_id == project_id]

    def add_todo(self, todo: Todo) -> Todo:
        self.todos.append(todo)
        self._todos_saved()
        return todo

    def update_todo(self, todo_id: str, **changes) -> None:
        todo = self.todo(todo_id)
        if todo is None:
            return
        for key, value in changes.items():
            setattr(todo, key, value)
        if "done" in changes:
            todo.completed = _now() if todo.done else None
        self._todos_saved()

    def toggle_done(self, todo_id: str) -> None:
        todo = self.todo(todo_id)
        if todo is not None:
            self.update_todo(todo_id, done=not todo.done)

    def delete_todo(self, todo_id: str) -> None:
        self.todos = [t for t in self.todos if t.id != todo_id]
        self._todos_saved()

    def _todos_saved(self) -> None:
        self.save()
        self.todos_changed.emit()
        self.projects_changed.emit()       # open counts in the project pane

    # -- queries
    def modules(self, project_id: str | None) -> list[str]:
        """The distinct module names used in a project (all projects for None)."""
        names = {t.module.strip() for t in self.todos_of(project_id) if t.module.strip()}
        return sorted(names, key=str.casefold)

    def open_count(self, project_id: str | None) -> int:
        return sum(1 for t in self.todos_of(project_id) if not t.done)
