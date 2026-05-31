from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
import git  # gitpython


class DirPickerWindow(QWidget):
    """Screen where student selects working directory and confirms git init."""

    session_ready = pyqtSignal(str)  # emits repo_path when ready
    back = pyqtSignal()              # go back to exam confirmation

    def __init__(self, exam_id: int, student_email: str, parent=None):
        super().__init__(parent)
        self.exam_id = exam_id
        self.student_email = student_email
        self._selected_path: str | None = None
        self.setWindowTitle("cheat-buster — Select Working Directory")
        self.setMinimumSize(540, 280)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(16)

        # Title
        title = QLabel("Select your working directory")
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        # Subtitle
        subtitle = QLabel("Your code will be tracked here during the exam")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #555;")
        root.addWidget(subtitle)

        root.addStretch()

        # Path row: read-only line edit + Browse button
        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        self._path_display = QLineEdit()
        self._path_display.setReadOnly(True)
        self._path_display.setPlaceholderText("No directory selected…")
        path_row.addWidget(self._path_display, stretch=1)

        browse_btn = QPushButton("Browse…")
        browse_btn.setMinimumWidth(90)
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(browse_btn)

        root.addLayout(path_row)

        root.addStretch()

        # Action buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._back_btn = QPushButton("Back")
        self._back_btn.setMinimumWidth(90)
        self._back_btn.clicked.connect(self.back.emit)
        btn_row.addWidget(self._back_btn)

        btn_row.addStretch()

        self._confirm_btn = QPushButton("Confirm")
        self._confirm_btn.setMinimumWidth(120)
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(self._confirm_btn)

        root.addLayout(btn_row)

        self.setLayout(root)

    def _on_browse(self):
        """Open native directory picker."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Working Directory", ""
        )
        if path:
            self._selected_path = path
            self._path_display.setText(path)
            self._confirm_btn.setEnabled(True)

    def _on_confirm(self):
        """
        1. Check if .git exists in selected path.
        2. If not: call git.Repo.init(self._selected_path)
        3. Set git user.name = student_email (use email as name for simplicity)
           Set git user.email = student_email
           via repo.config_writer()
        4. Emit session_ready(path)
        """
        if not self._selected_path:
            return
        try:
            try:
                repo = git.Repo(self._selected_path)
                # Existing repo — reuse
            except git.InvalidGitRepositoryError:
                repo = git.Repo.init(self._selected_path)

            # Set git identity from student auth
            with repo.config_writer() as cfg:
                cfg.set_value("user", "name", self.student_email)
                cfg.set_value("user", "email", self.student_email)

            self.session_ready.emit(self._selected_path)
        except Exception as e:
            QMessageBox.critical(self, "Git Error", str(e))
