import os

import git  # gitpython
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)


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
        self.setMinimumSize(540, 300)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(48, 40, 48, 36)
        root.setSpacing(0)

        # ── Title ─────────────────────────────────────────────────────────
        title = QLabel("Select working directory")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)
        root.addSpacing(8)

        subtitle = QLabel("Your code will be tracked here during the exam")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #6B7280; font-size: 12px;")
        root.addWidget(subtitle)
        root.addSpacing(32)

        # ── Directory picker card ─────────────────────────────────────────
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        path_label = QLabel("Directory")
        path_label.setStyleSheet("color: #4B5563; font-size: 11px; font-weight: 600;")
        card_layout.addWidget(path_label)

        path_row = QHBoxLayout()
        path_row.setSpacing(10)

        self._path_display = QLineEdit()
        self._path_display.setReadOnly(True)
        self._path_display.setPlaceholderText("No directory selected…")
        path_row.addWidget(self._path_display, stretch=1)

        browse_btn = QPushButton("Browse…")
        browse_btn.setProperty("role", "secondary")
        browse_btn.setMinimumWidth(90)
        browse_btn.setMinimumHeight(38)
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(browse_btn)

        card_layout.addLayout(path_row)
        root.addWidget(card)
        root.addStretch()

        # ── Action buttons ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._back_btn = QPushButton("Back")
        self._back_btn.setProperty("role", "secondary")
        self._back_btn.setMinimumHeight(40)
        self._back_btn.setMinimumWidth(100)
        self._back_btn.clicked.connect(self.back.emit)
        btn_row.addWidget(self._back_btn)

        btn_row.addStretch()

        self._confirm_btn = QPushButton("Confirm")
        self._confirm_btn.setMinimumHeight(40)
        self._confirm_btn.setMinimumWidth(130)
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
