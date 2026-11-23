"""Filesystem locations for the application.

* **bundled** assets (the icons) sit next to the code and are read-only.
* the **per-user data** directory holds ``todos.json`` and the recoloured-icon
  cache. ``user_data_dir`` returns it (created on first use).

Set ``TODOAPP_DATA_DIR`` to redirect the per-user directory (the tests do this
so they never touch a real profile).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def user_data_dir() -> Path:
    """The writable per-user data directory, created if it does not exist."""
    override = os.environ.get("TODOAPP_DATA_DIR")
    path = Path(override) if override else _platform_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_subdir(name: str) -> Path:
    """A named sub-directory of the per-user data directory, created if missing."""
    path = user_data_dir() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _platform_data_dir() -> Path:
    """The OS's per-user application-data location for this app."""
    try:
        from PySide6.QtCore import QStandardPaths
        location = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        if location:
            return Path(location)
    except Exception:                       # Qt missing or no application object yet
        pass
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "TodoApp"
    return Path.home() / ".todo_app"
