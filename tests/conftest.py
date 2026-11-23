"""Shared fixtures. The environment is prepared before anything imports PySide6."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

os.environ["QT_QPA_PLATFORM"] = "offscreen"
if Path(r"C:\Windows\Fonts").is_dir():
    os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
(ROOT / ".scratch").mkdir(exist_ok=True)
os.environ.setdefault("PYTEST_DEBUG_TEMPROOT", str(ROOT / ".scratch"))
if "TODOAPP_TEST_SETTINGS_DIR" not in os.environ:
    os.environ["TODOAPP_TEST_SETTINGS_DIR"] = tempfile.mkdtemp(prefix="pytest_settings_",
                                                               dir=ROOT / ".scratch")
_SETTINGS_DIR = Path(os.environ["TODOAPP_TEST_SETTINGS_DIR"])
os.environ["TODOAPP_SETTINGS_FILE"] = str(_SETTINGS_DIR / "settings.ini")
os.environ.setdefault("TODOAPP_DATA_DIR", str(_SETTINGS_DIR / "data"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import shutil  # noqa: E402
from datetime import date  # noqa: E402

import pytest  # noqa: E402
from PySide6.QtCore import QCoreApplication, QEvent  # noqa: E402

from src.model.store import Store  # noqa: E402

TODAY = date(2026, 11, 23)


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_SETTINGS_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def _app_and_theme(qapp):
    """Every test runs with a QApplication, fresh settings and the light theme."""
    from data import settings
    from data.theme import theme_manager
    settings._store().clear()
    theme_manager().set_theme("light")
    yield qapp
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    theme_manager().set_theme("light")
    qapp.setStyleSheet("")


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "todos.json")
    yield s
    s.deleteLater()
