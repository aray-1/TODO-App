"""Persistent user settings (theme, last selected project, window geometry).

Values are stored as JSON strings through QSettings so that types survive the
round trip. Set the environment variable TODOAPP_SETTINGS_FILE to redirect the
store to an INI file (used by the tests).
"""
import json
import os

from PySide6.QtCore import QSettings

ORGANISATION = "TodoApp"
APPLICATION = "TodoApp"


def _store() -> QSettings:
    path = os.environ.get("TODOAPP_SETTINGS_FILE")
    if path:
        return QSettings(path, QSettings.IniFormat)
    return QSettings(ORGANISATION, APPLICATION)


def get(key: str, default=None):
    raw = _store().value(key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def put(key: str, value) -> None:
    _store().setValue(key, json.dumps(value))
