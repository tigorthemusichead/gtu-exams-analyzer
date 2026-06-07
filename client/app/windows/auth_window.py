import os

import httpx
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from app.api import api_client

_LOGO_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "logo.png")
)


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    font = lbl.font()
    font.setPointSize(11)
    font.setBold(True)
    lbl.setFont(font)
    lbl.setStyleSheet("color: #4B5563; margin-bottom: 2px;")
    return lbl


class AuthWindow(QWidget):
    auth_success = pyqtSignal(int, str)  # emits (exam_id, student_email)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("cheat-buster — Student Login")
        self.setMinimumSize(440, 560)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(48, 36, 48, 36)
        root.setSpacing(0)

        # ── Logo ──────────────────────────────────────────────────────────
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(_LOGO_PATH)
        if not pixmap.isNull():
            logo_label.setPixmap(
                pixmap.scaledToHeight(52, Qt.TransformationMode.SmoothTransformation)
            )
        root.addWidget(logo_label)
        root.addSpacing(6)

        app_name = QLabel("cheat-buster")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_name.setStyleSheet("color: #6B7280; font-size: 12px; letter-spacing: 0.5px;")
        root.addWidget(app_name)
        root.addSpacing(28)

        # ── Divider ───────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setObjectName("divider")
        root.addWidget(divider)
        root.addSpacing(22)

        # ── Section title ─────────────────────────────────────────────────
        title = QLabel("Student Login")
        title_font = QFont()
        title_font.setPointSize(17)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)
        root.addSpacing(22)

        # ── Form fields (label-above-input style) ─────────────────────────
        form_layout = QVBoxLayout()
        form_layout.setSpacing(0)

        self._email_field = QLineEdit()
        self._email_field.setPlaceholderText("student@university.edu")
        form_layout.addWidget(_field_label("Email"))
        form_layout.addSpacing(4)
        form_layout.addWidget(self._email_field)
        form_layout.addSpacing(14)

        self._group_field = QLineEdit()
        self._group_field.setPlaceholderText("e.g. 108259")
        form_layout.addWidget(_field_label("Group number"))
        form_layout.addSpacing(4)
        form_layout.addWidget(self._group_field)
        form_layout.addSpacing(14)

        self._exam_id_field = QLineEdit()
        self._exam_id_field.setPlaceholderText("numeric ID")
        form_layout.addWidget(_field_label("Exam ID"))
        form_layout.addSpacing(4)
        form_layout.addWidget(self._exam_id_field)
        form_layout.addSpacing(14)

        self._variant_field = QLineEdit()
        self._variant_field.setPlaceholderText("numeric variant")
        form_layout.addWidget(_field_label("Variant number"))
        form_layout.addSpacing(4)
        form_layout.addWidget(self._variant_field)

        root.addLayout(form_layout)
        root.addSpacing(14)

        # ── Error label ───────────────────────────────────────────────────
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: #DC2626; font-size: 12px;")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)
        self._error_label.hide()
        root.addWidget(self._error_label)

        root.addStretch()
        root.addSpacing(8)

        # ── Submit button ─────────────────────────────────────────────────
        self._start_btn = QPushButton("Start Exam")
        self._start_btn.setMinimumHeight(42)
        self._start_btn.clicked.connect(self._on_start_exam)
        root.addWidget(self._start_btn)

        self.setLayout(root)

    def _on_start_exam(self):
        self._clear_error()

        email = self._email_field.text().strip()
        group = self._group_field.text().strip()
        exam_id_text = self._exam_id_field.text().strip()
        variant_text = self._variant_field.text().strip()

        # Validation
        if not email:
            self._show_error("Email is required.")
            return
        if "@" not in email:
            self._show_error("Email must contain '@'.")
            return
        if not group:
            self._show_error("Group number is required.")
            return
        if not exam_id_text:
            self._show_error("Exam ID is required.")
            return
        if not variant_text:
            self._show_error("Variant number is required.")
            return

        try:
            exam_id = int(exam_id_text)
        except ValueError:
            self._show_error("Exam ID must be a number.")
            return

        try:
            variant = int(variant_text)
        except ValueError:
            self._show_error("Variant number must be a number.")
            return

        # API call
        try:
            response = api_client.post("/auth/student", {
                "email": email,
                "group_number": group,
                "exam_id": exam_id,
                "variant": variant,
            })
        except httpx.ConnectError:
            self._show_error("Cannot connect to server. Make sure the server is running.")
            return
        except httpx.TimeoutException:
            self._show_error("Request timed out. Please try again.")
            return
        except Exception as exc:
            self._show_error(f"Unexpected error: {exc}")
            return

        if response.status_code == 200:
            data = response.json()
            api_client.set_token(data["access_token"])
            self.auth_success.emit(exam_id, email)
        elif response.status_code == 401:
            self._show_error("Invalid credentials. Check your email and exam details.")
        elif response.status_code == 404:
            self._show_error("Exam not found. Check the exam ID and variant.")
        elif response.status_code >= 500:
            self._show_error(f"Server error ({response.status_code}). Please try again later.")
        else:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            self._show_error(f"Error {response.status_code}: {detail}")

    def _show_error(self, msg: str):
        self._error_label.setText(msg)
        self._error_label.show()

    def _clear_error(self):
        self._error_label.hide()
        self._error_label.setText("")
