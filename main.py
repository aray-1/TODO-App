"""TODO App: start the application.

Usage: python main.py
"""
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from data import settings
from data.icons import app_icon
from src.main_window import APP_NAME, MainWindow

APP_USER_MODEL_ID = "TodoApp.App"


def _own_taskbar_entry() -> None:
    """On Windows, show the application's icon on the taskbar (not Python's)."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except (AttributeError, OSError):
            pass


def main() -> int:
    _own_taskbar_entry()
    app = QApplication(sys.argv)
    if sys.platform == "win32":
        app.setFont(QFont("Segoe UI", 9))
    app.setWindowIcon(app_icon("app"))
    app.setOrganizationName(settings.ORGANISATION)
    app.setApplicationName(settings.APPLICATION)
    app.setApplicationDisplayName("")   # the window title already carries the name
    window = MainWindow()
    window.setObjectName(APP_NAME)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
