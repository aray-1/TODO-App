"""Create or edit a TODO. Only the title is required."""
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QCompleter, QDateEdit,
                               QDialog, QDialogButtonBox, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

from src.model.store import URGENCY_LABELS, Store, Todo

URGENCY_CHOICES = (None, "low", "medium", "high")     # left to right in the segmented control


def _label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("FieldLabel")
    return label


class TodoDialog(QDialog):
    """``todo`` None creates a new TODO in ``project_id`` (preselected)."""

    def __init__(self, store: Store, project_id: str | None = None, todo: Todo | None = None,
                 parent=None):
        super().__init__(parent)
        self.store = store
        self.todo = todo
        self.setWindowTitle("Edit TODO" if todo else "New TODO")
        self.setMinimumWidth(560)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        row = 0

        self.project = QComboBox()
        for p in store.projects:
            self.project.addItem(p.name, p.id)
        chosen = todo.project_id if todo else project_id
        index = self.project.findData(chosen)
        self.project.setCurrentIndex(index if index >= 0 else 0)
        grid.addWidget(_label("Project"), row, 0)
        grid.addWidget(self.project, row, 1)
        row += 1

        self.title = QLineEdit(todo.title if todo else "")
        self.title.setObjectName("TitleEdit")
        self.title.setPlaceholderText("What needs to be done?")
        grid.addWidget(_label("Title"), row, 0)
        grid.addWidget(self.title, row, 1)
        row += 1

        self.module = QLineEdit(todo.module if todo else "")
        self.module.setPlaceholderText("Optional — e.g. parser, UI, ADC driver")
        self._completer = QCompleter([], self.module)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self.module.setCompleter(self._completer)
        self.project.currentIndexChanged.connect(self._refresh_modules)
        self._refresh_modules()
        grid.addWidget(_label("Module"), row, 0)
        grid.addWidget(self.module, row, 1)
        row += 1

        # urgency: a segmented control None / Low / Medium / High
        segments = QWidget()
        seg_layout = QHBoxLayout(segments)
        seg_layout.setContentsMargins(0, 0, 0, 0)
        seg_layout.setSpacing(0)
        self.urgency_group = QButtonGroup(self)
        self.urgency_group.setExclusive(True)
        self.urgency_buttons = {}
        for i, level in enumerate(URGENCY_CHOICES):
            button = QPushButton(URGENCY_LABELS.get(level, "None"))
            button.setObjectName("Segment")
            button.setCheckable(True)
            button.setProperty("first", i == 0)
            button.setProperty("last", i == len(URGENCY_CHOICES) - 1)
            button.setCursor(Qt.PointingHandCursor)
            self.urgency_group.addButton(button)
            self.urgency_buttons[level] = button
            seg_layout.addWidget(button)
        seg_layout.addStretch(1)
        self.urgency_buttons[todo.urgency if todo else None].setChecked(True)
        grid.addWidget(_label("Urgency"), row, 0)
        grid.addWidget(segments, row, 1)
        row += 1

        # deadline: a check box, a date with a calendar, quick picks
        deadline_row = QWidget()
        dl = QHBoxLayout(deadline_row)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(6)
        self.has_deadline = QCheckBox()
        self.has_deadline.setToolTip("Set a deadline")
        self.deadline = QDateEdit()
        self.deadline.setCalendarPopup(True)
        self.deadline.setDisplayFormat("ddd d MMM yyyy")
        self.deadline.setMinimumWidth(150)
        if todo and todo.deadline:
            self.has_deadline.setChecked(True)
            self.deadline.setDate(QDate.fromString(todo.deadline, Qt.ISODate))
        else:
            self.deadline.setDate(QDate.currentDate().addDays(7))
        self.has_deadline.toggled.connect(self.deadline.setEnabled)
        self.deadline.setEnabled(self.has_deadline.isChecked())
        dl.addWidget(self.has_deadline)
        dl.addWidget(self.deadline)
        for text, days in (("Today", 0), ("Tomorrow", 1), ("Next week", 7)):
            quick = QPushButton(text)
            quick.setObjectName("QuickDate")
            quick.setCursor(Qt.PointingHandCursor)
            quick.clicked.connect(lambda _=False, d=days: self.set_deadline_in(d))
            dl.addWidget(quick)
        dl.addStretch(1)
        grid.addWidget(_label("Deadline"), row, 0)
        grid.addWidget(deadline_row, row, 1)
        row += 1

        self.notes = QPlainTextEdit(todo.notes if todo else "")
        self.notes.setPlaceholderText("Notes (optional)")
        self.notes.setFixedHeight(96)
        self.notes.setTabChangesFocus(True)
        grid.addWidget(_label("Notes"), row, 0, Qt.AlignTop)
        grid.addWidget(self.notes, row, 1)
        grid.setColumnStretch(1, 1)

        self.error = QLabel("")
        self.error.setObjectName("DialogError")
        self.error.hide()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save = buttons.button(QDialogButtonBox.Save)
        save.setText("Save" if todo else "Add TODO")
        save.setObjectName("PrimaryButton")
        save.setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        QShortcut(QKeySequence("Ctrl+Return"), self, self.accept)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(12)
        layout.addLayout(grid)
        layout.addWidget(self.error)
        layout.addWidget(buttons)
        self.title.setFocus()

    def _refresh_modules(self) -> None:
        self._completer.model().setStringList(self.store.modules(self.project.currentData()))

    def set_deadline_in(self, days: int) -> None:
        self.has_deadline.setChecked(True)
        self.deadline.setDate(QDate.currentDate().addDays(days))

    def urgency(self) -> str | None:
        for level, button in self.urgency_buttons.items():
            if button.isChecked():
                return level
        return None

    def values(self) -> dict:
        """The TODO fields entered in the dialog."""
        return {
            "project_id": self.project.currentData(),
            "title": self.title.text().strip(),
            "module": self.module.text().strip(),
            "urgency": self.urgency(),
            "deadline": (self.deadline.date().toString(Qt.ISODate)
                         if self.has_deadline.isChecked() else None),
            "notes": self.notes.toPlainText().strip(),
        }

    def accept(self) -> None:
        values = self.values()
        if not values["title"]:
            self._fail("Please enter a title.", self.title)
            return
        if values["project_id"] is None:
            self._fail("Create a project first.", self.project)
            return
        if self.todo is None:
            self.store.add_todo(Todo(**values))
        else:
            self.store.update_todo(self.todo.id, **values)
        super().accept()

    def _fail(self, message: str, widget) -> None:
        self.error.setText(message)
        self.error.show()
        widget.setFocus()
