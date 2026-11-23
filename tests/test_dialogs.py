"""The TODO and project dialogs."""
from PySide6.QtCore import QDate

from src.dialogs.project_dialog import ProjectDialog
from src.dialogs.todo_dialog import TodoDialog
from src.model.store import Todo


def test_title_is_required(qtbot, store):
    p = store.add_project("Alpha")
    dialog = TodoDialog(store, p.id)
    qtbot.addWidget(dialog)
    dialog.accept()
    assert dialog.error.text() == "Please enter a title."
    assert store.todos == []


def test_new_todo_defaults_to_no_urgency_or_deadline(qtbot, store):
    p = store.add_project("Alpha")
    dialog = TodoDialog(store, p.id)
    qtbot.addWidget(dialog)
    dialog.title.setText("  Write docs ")
    dialog.accept()
    t = store.todos[0]
    assert (t.project_id, t.title, t.urgency, t.deadline, t.module) == (p.id, "Write docs", None, None, "")


def test_edit_round_trip(qtbot, store):
    a, b = store.add_project("Alpha"), store.add_project("Beta")
    store.add_todo(Todo(a.id, "other", module="parser"))
    t = store.add_todo(Todo(a.id, "Fix ADC", urgency="high", deadline="2026-12-01"))
    dialog = TodoDialog(store, todo=t)
    qtbot.addWidget(dialog)
    assert dialog.urgency() == "high"
    assert dialog.has_deadline.isChecked()
    assert dialog.deadline.date() == QDate(2026, 12, 1)
    assert dialog._completer.model().stringList() == ["parser"]
    dialog.urgency_buttons[None].setChecked(True)
    dialog.has_deadline.setChecked(False)
    dialog.module.setText("adc")
    dialog.project.setCurrentIndex(dialog.project.findData(b.id))
    dialog.accept()
    t = store.todo(t.id)
    assert (t.project_id, t.urgency, t.deadline, t.module) == (b.id, None, None, "adc")


def test_quick_deadline(qtbot, store):
    p = store.add_project("Alpha")
    dialog = TodoDialog(store, p.id)
    qtbot.addWidget(dialog)
    assert not dialog.has_deadline.isChecked()
    dialog.set_deadline_in(1)
    assert dialog.values()["deadline"] == QDate.currentDate().addDays(1).toString("yyyy-MM-dd")


def test_project_dialog_validation(qtbot):
    dialog = ProjectDialog(existing=["Alpha"])
    qtbot.addWidget(dialog)
    dialog.accept()
    assert dialog.error.text() == "Please enter a name."
    dialog.edit.setText("alpha")
    dialog.accept()
    assert "already exists" in dialog.error.text()
    rename = ProjectDialog("Alpha", ["Alpha"])
    qtbot.addWidget(rename)
    rename.accept()                                   # keeping its own name is fine
    assert rename.result() == ProjectDialog.Accepted
