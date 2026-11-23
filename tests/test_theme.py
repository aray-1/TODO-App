"""Themes, the stylesheet and the main window."""
from data import settings
from data.qss import build_qss, contrast
from data.theme import DARK, LIGHT, theme_manager
from src.main_window import MainWindow
from src.model.store import Store


def test_toggle_persists():
    theme_manager().toggle()
    assert theme_manager().theme is DARK
    assert settings.get("theme") == "dark"
    theme_manager().toggle()
    assert theme_manager().theme is LIGHT


def test_stylesheet_builds_for_both_themes():
    for theme in (LIGHT, DARK):
        qss = build_qss(theme)
        assert theme.accent.name() in qss and "{" in qss


def test_text_is_readable_on_both_themes():
    for theme in (LIGHT, DARK):
        assert contrast(theme.text, theme.card) >= 7
        assert contrast(theme.text, theme.window) >= 7
        assert contrast(theme.text_muted, theme.card) >= 4.5


def test_main_window_restores_last_project(qtbot, tmp_path):
    store = Store(tmp_path / "todos.json")
    p = store.add_project("Alpha")
    settings.put("last_project", p.id)
    window = MainWindow(store)
    qtbot.addWidget(window)
    assert window.pane.current_project() == p.id
    assert window.board.title.text() == "Alpha"
    theme_manager().toggle()                          # restyles without errors
    assert theme_manager().theme is DARK
