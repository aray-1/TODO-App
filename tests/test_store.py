"""The data model: projects, TODOs, persistence and the pure helpers."""
import json
from datetime import timedelta

from conftest import TODAY
from src.model.store import Store, Todo, deadline_state, filter_todos, sort_todos


def _iso(days: int) -> str:
    return (TODAY + timedelta(days=days)).isoformat()


def test_only_a_title_is_needed(store):
    p = store.add_project("Alpha")
    t = store.add_todo(Todo(project_id=p.id, title="Write docs"))
    assert (t.module, t.urgency, t.deadline, t.done) == ("", None, None, False)


def test_round_trip_through_the_file(store, tmp_path):
    p = store.add_project("Alpha")
    store.add_todo(Todo(project_id=p.id, title="Fix ADC", module="adc", urgency="high",
                        deadline="2026-12-01", notes="Check the clock"))
    reloaded = Store(tmp_path / "todos.json")
    assert [x.name for x in reloaded.projects] == ["Alpha"]
    t = reloaded.todos[0]
    assert (t.title, t.module, t.urgency, t.deadline, t.notes) == (
        "Fix ADC", "adc", "high", "2026-12-01", "Check the clock")
    assert json.loads((tmp_path / "todos.json").read_text(encoding="utf-8"))["version"] == 1
    assert not (tmp_path / "todos.json.tmp").exists()


def test_rename_and_delete_project_cascades(store):
    a, b = store.add_project("Alpha"), store.add_project("Beta")
    store.add_todo(Todo(project_id=a.id, title="one"))
    store.add_todo(Todo(project_id=b.id, title="two"))
    store.rename_project(a.id, "  Alpha 2 ")
    assert store.project(a.id).name == "Alpha 2"
    store.delete_project(a.id)
    assert [p.name for p in store.projects] == ["Beta"]
    assert [t.title for t in store.todos] == ["two"]


def test_toggle_done_sets_completed_and_counts(store):
    p = store.add_project("Alpha")
    t = store.add_todo(Todo(project_id=p.id, title="one"))
    store.add_todo(Todo(project_id=p.id, title="two"))
    assert store.open_count(p.id) == 2
    store.toggle_done(t.id)
    assert store.todo(t.id).done and store.todo(t.id).completed
    assert store.open_count(p.id) == 1 and store.open_count(None) == 1
    store.toggle_done(t.id)
    assert store.todo(t.id).completed is None


def test_modules_are_distinct_per_project(store):
    a, b = store.add_project("Alpha"), store.add_project("Beta")
    for module in ("parser", "UI", "parser", ""):
        store.add_todo(Todo(project_id=a.id, title="x", module=module))
    store.add_todo(Todo(project_id=b.id, title="y", module="driver"))
    assert store.modules(a.id) == ["parser", "UI"]
    assert store.modules(None) == ["driver", "parser", "UI"]


def test_unreadable_file_is_kept_aside(tmp_path):
    path = tmp_path / "todos.json"
    path.write_text("{ not json", encoding="utf-8")
    s = Store(path)
    assert s.projects == [] and s.todos == []
    assert s.recovered_from is not None and s.recovered_from.read_text(encoding="utf-8") == "{ not json"
    assert not path.exists()


def test_deadline_states():
    def state(days, done=False):
        return deadline_state(Todo("p", "t", deadline=_iso(days), done=done), TODAY)
    assert state(-1) == "overdue"
    assert state(-1, done=True) == "later"
    assert state(0) == "today"
    assert state(1) == "soon"
    assert state(5) == "later"
    assert deadline_state(Todo("p", "t"), TODAY) is None


def test_sort_by_deadline_then_urgency_undated_last():
    todos = [Todo("p", "undated-high", urgency="high"),
             Todo("p", "later-none", deadline=_iso(5)),
             Todo("p", "later-high", deadline=_iso(5), urgency="high"),
             Todo("p", "soon", deadline=_iso(1)),
             Todo("p", "done-early", deadline=_iso(-3), done=True)]
    assert [t.title for t in sort_todos(todos, "deadline")] == [
        "soon", "later-high", "later-none", "undated-high", "done-early"]


def test_sort_by_urgency_none_last():
    todos = [Todo("p", "none"), Todo("p", "low", urgency="low"),
             Todo("p", "high", urgency="high"), Todo("p", "medium", urgency="medium")]
    assert [t.title for t in sort_todos(todos, "urgency")] == ["high", "medium", "low", "none"]


def test_filters():
    todos = [Todo("p", "Fix ADC", module="adc", urgency="high"),
             Todo("p", "Write docs", notes="mention the ADC"),
             Todo("p", "Old", urgency="low", done=True)]
    titles = lambda **kw: [t.title for t in filter_todos(todos, **kw)]  # noqa: E731
    assert titles() == ["Fix ADC", "Write docs"]
    assert titles(show_done=True) == ["Fix ADC", "Write docs", "Old"]
    assert titles(text="adc") == ["Fix ADC", "Write docs"]
    assert titles(urgency="high") == ["Fix ADC"]
    assert titles(urgency="none") == ["Write docs"]
    assert titles(urgency="low", show_done=True) == ["Old"]
