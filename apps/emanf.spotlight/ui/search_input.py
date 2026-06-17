from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLineEdit


class SearchInput(QLineEdit):
    query_changed = Signal(str)
    query_submitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("searchInput")
        self.setPlaceholderText("Search apps, files, commands...")
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setFocusPolicy(Qt.StrongFocus)

        self.textChanged.connect(self._on_text_changed)
        self.returnPressed.connect(self._on_return_pressed)

    def _on_text_changed(self, text: str):
        self.query_changed.emit(text)

    def _on_return_pressed(self):
        self.query_submitted.emit(self.text())

    def get_query(self) -> str:
        return self.text().strip()
