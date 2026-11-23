"""Ask for a project name (new project or rename)."""
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout)


class ProjectDialog(QDialog):
    def __init__(self, name: str = "", existing: list[str] = (), parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rename project" if name else "New project")
        self.setMinimumWidth(340)
        self._existing = {n.casefold() for n in existing if n != name}

        self.edit = QLineEdit(name)
        self.edit.setObjectName("TitleEdit")
        self.edit.setPlaceholderText("Project name")
        self.edit.selectAll()
        self.error = QLabel("")
        self.error.setObjectName("DialogError")
        self.error.hide()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok = buttons.button(QDialogButtonBox.Ok)
        ok.setText("Rename" if name else "Create")
        ok.setObjectName("PrimaryButton")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)
        title = QLabel("Name")
        title.setObjectName("FieldLabel")
        layout.addWidget(title)
        layout.addWidget(self.edit)
        layout.addWidget(self.error)
        layout.addWidget(buttons)

    def name(self) -> str:
        return self.edit.text().strip()

    def accept(self) -> None:
        if not self.name():
            self._fail("Please enter a name.")
        elif self.name().casefold() in self._existing:
            self._fail("A project with this name already exists.")
        else:
            super().accept()

    def _fail(self, message: str) -> None:
        self.error.setText(message)
        self.error.show()
        self.edit.setFocus()
