"""The board, the cards and the project pane."""
from datetime import timedelta

import pytest

from conftest import TODAY
from src.board.todo_board import TodoBoard
from src.board.todo_card import TodoCard, format_deadline
from src.model.store import Todo
from src.sidebar.project_pane import ProjectPane


@pytest.fixture
def board(qtbot, store):
    b = TodoBoard(store)
    b.today = TODAY
    qtbot.addWidget(b)
    b.resize(1000, 700)
    b.show()
    return b


def _titles(board):
    return [card.todo.title for card in board.cards]


def test_empty_states(board, store):
    assert board.stack.currentWidget() is board.empty
    assert board.empty_title.text() == "No projects yet"
    assert not board.new_button.isEnabled()
    p = store.add_project("Alpha")
    board.set_project(p.id)
    assert board.empty_title.text() == "No TODOs here"
    assert board.new_button.isEnabled()


def test_cards_per_project_and_all(board, store):
    a, b = store.add_project("Alpha"), store.add_project("Beta")
    store.add_todo(Todo(a.id, "one"))
    store.add_todo(Todo(b.id, "two"))
    board.set_project(a.id)
    assert _titles(board) == ["one"]
    assert board.title.text() == "Alpha"
    assert "project" not in board.cards[0].chip_kinds()
    board.set_project(None)
    assert sorted(_titles(board)) == ["one", "two"]
    assert board.title.text() == "All TODOs"
    assert all("project" in card.chip_kinds() for card in board.cards)


def test_board_follows_store_changes_and_filters(board, store, qtbot):
    p = store.add_project("Alpha")
    board.set_project(p.id)
    t = store.add_todo(Todo(p.id, "Fix ADC", urgency="high"))
    store.add_todo(Todo(p.id, "Write docs"))
    assert len(board.cards) == 2
    board.urgency.setCurrentIndex(board.urgency.findData("none"))
    assert _titles(board) == ["Write docs"]
    board.urgency.setCurrentIndex(0)
    store.toggle_done(t.id)
    assert _titles(board) == ["Write docs"]
    board.show_done.setChecked(True)
    assert _titles(board) == ["Write docs", "Fix ADC"]          # done ones last
    board.search.setText("adc")
    qtbot.waitUntil(lambda: _titles(board) == ["Fix ADC"])
    board.search.setText("zzz")
    qtbot.waitUntil(lambda: board.stack.currentWidget() is board.empty)
    assert board.empty_title.text() == "Nothing to show"


def test_card_without_optional_fields_has_no_chips(qtbot):
    card = TodoCard(Todo("p", "Just a title"), today=TODAY)
    qtbot.addWidget(card)
    assert card.chip_kinds() == []
    assert card.notes is None


def test_card_chips(qtbot):
    overdue = TodoCard(Todo("p", "t", module="adc", urgency="medium",
                            deadline=(TODAY - timedelta(days=2)).isoformat()), today=TODAY)
    qtbot.addWidget(overdue)
    assert overdue.chip_kinds() == ["deadline:overdue", "urgency:medium", "module"]
    soon = TodoCard(Todo("p", "t", deadline=(TODAY + timedelta(days=1)).isoformat()), today=TODAY)
    qtbot.addWidget(soon)
    assert soon.chip_kinds() == ["deadline:soon"]


def test_cards_have_the_same_size(qtbot, board, store):
    p = store.add_project("Alpha")
    long_title = "A very long title that goes on and on " * 4
    store.add_todo(Todo(p.id, "Short"))
    store.add_todo(Todo(p.id, long_title, notes="line one\nline two\nline three", module="m" * 80,
                        urgency="medium", deadline=(TODAY - timedelta(days=3)).isoformat()))
    store.add_todo(Todo(p.id, "Mid", module="parser", urgency="low"))
    for project_id in (p.id, None):                   # with and without the project row
        board.set_project(project_id)
        qtbot.waitUntil(lambda: all(c.isVisible() and c.width() > 0 for c in board.cards))
        assert len({(c.width(), c.height()) for c in board.cards}) == 1
    long_card = next(c for c in board.cards if c.todo.title == long_title)
    assert long_card.title.truncated and long_card.title.toolTip() == " ".join(long_title.split())
    short_card = next(c for c in board.cards if c.todo.title == "Short")
    assert not short_card.title.truncated and short_card.title.toolTip() == ""
    assert long_card.module_chip.label.text().endswith("…")
    assert long_card.notes.truncated                  # three lines of notes, two shown
    chip_right = long_card.module_chip.geometry().right()
    assert chip_right <= long_card.chip_row.width()


def test_done_card_looks_completed(qtbot):
    from data.theme import theme_manager
    theme = theme_manager().theme
    todo = Todo("p", "Shipped", module="adc", urgency="high",
                deadline=(TODAY - timedelta(days=5)).isoformat(), done=True,
                completed=f"{TODAY.isoformat()}T10:00:00")
    done = TodoCard(todo, today=TODAY)
    open_card = TodoCard(Todo("p", "Open", urgency="high"), today=TODAY)
    for card in (done, open_card):
        qtbot.addWidget(card)
        card.show()                                   # the stylesheet re-polishes on show
    # the deadline and urgency give way to when it was finished; no "Overdue"
    assert done.chip_kinds() == ["completed", "module"]
    assert done.chips[0].text == "Completed today"
    assert done.graphicsEffect() is None and open_card.graphicsEffect() is not None
    assert done._background != theme.card and open_card._background == theme.card
    assert done._stripe == theme.border and open_card._stripe == theme.high
    assert done.title.strike and not open_card.title.strike
    assert done.height() == open_card.height()


def test_format_completed():
    from src.board.todo_card import format_completed
    assert format_completed(None, TODAY) == "Completed"
    assert format_completed("2026-11-20T09:30:00", TODAY) == "Completed 20 Nov"
    assert format_completed("2025-12-31T09:30:00", TODAY) == "Completed 31 Dec 2025"


def test_format_deadline():
    assert format_deadline("2026-11-23", "today", TODAY) == "Due today"
    assert format_deadline("2026-11-24", "soon", TODAY) == "Due tomorrow"
    assert format_deadline("2026-11-20", "overdue", TODAY) == "Overdue · 20 Nov"
    assert format_deadline("2027-01-05", "later", TODAY) == "5 Jan 2027"


def test_card_signals(qtbot, board, store):
    p = store.add_project("Alpha")
    board.set_project(p.id)
    t = store.add_todo(Todo(p.id, "one"))
    card = board.cards[0]
    with qtbot.waitSignal(board.edit_requested) as edit:
        card.edit_requested.emit(card.todo_id)
    assert edit.args == [t.id]
    card.done_box.click()
    assert store.todo(t.id).done


def test_project_pane_counts_and_selection(qtbot, store):
    a = store.add_project("Alpha")
    store.add_todo(Todo(a.id, "one"))
    pane = ProjectPane(store)
    qtbot.addWidget(pane)
    assert pane.list.count() == 2
    with qtbot.waitSignal(pane.project_selected) as sel:
        pane.select(a.id)
    assert sel.args == [a.id]
    row = pane.list.itemWidget(pane.list.item(1))
    assert (row.name.text(), row.count.text()) == ("Alpha", "1")
    with qtbot.waitSignal(pane.project_selected) as sel:
        store.delete_project(a.id)
    assert sel.args == [None] and pane.list.count() == 1


def test_cards_reflow_with_width(qtbot, board, store):
    p = store.add_project("Alpha")
    for i in range(6):
        store.add_todo(Todo(p.id, f"todo {i}"))
    board.set_project(p.id)

    def rows():
        return len({card.y() for card in board.cards})
    board.resize(1300, 700)
    qtbot.waitUntil(lambda: rows() == 2)              # 4 cards fit in a row at 1300 px
    board.resize(620, 700)
    qtbot.waitUntil(lambda: rows() == 3)              # 2 cards per row
    assert board.grid_host.height() > board.cards[-1].geometry().bottom()
