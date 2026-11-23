# TODO App

A small desktop app for keeping TODOs per project. Projects are listed in a left
sidebar, and each project's TODOs float as cards in a grid that reflows with the
window. A TODO needs only a title; it can also name the module it concerns, an
urgency (High/Medium/Low) and a deadline. Overdue and due-soon deadlines are
highlighted. You can search, filter by urgency, sort by deadline, urgency or date
added, and show or hide completed TODOs. The app has light and dark themes and
saves everything automatically to a local JSON file.

Built with Python 3.10 and PySide6; tested with pytest and pytest-qt.

## Download

Windows installers are attached to the [Releases](../../releases) page.

## Run from source

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

Run the tests with `.venv\Scripts\python -m pytest -q`.

## Shortcuts

| Keys | Action |
|---|---|
| Ctrl+N | New TODO |
| Ctrl+Shift+N | New project |
| Ctrl+F | Search |
| Ctrl+Enter | Save (in the TODO dialog) |

## Where the data lives

`%APPDATA%\TodoApp\TodoApp\todos.json`, saved on every change. If the file cannot
be read, it is kept as `todos.corrupt-<time>.json` and the app starts empty.

## License

MIT — see [LICENSE](LICENSE).
