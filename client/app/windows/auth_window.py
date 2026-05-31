from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
from app.api import api_client
import httpx


class AuthWindow(QWidget):
    auth_success = pyqtSignal(int, str)  # emits (exam_id, student_email)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("cheat-buster — Student Login")
        self.setMinimumSize(420, 320)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(16)

        # Title
        title = QLabel("Student Login")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        # Form
        form = QFormLayout()
        form.setSpacing(10)

        self._email_field = QLineEdit()
        self._email_field.setPlaceholderText("student@university.edu")
        form.addRow("Email:", self._email_field)

        self._group_field = QLineEdit()
        self._group_field.setPlaceholderText("e.g. CS-301")
        form.addRow("Group number:", self._group_field)

        self._exam_id_field = QLineEdit()
        self._exam_id_field.setPlaceholderText("numeric ID")
        form.addRow("Exam ID:", self._exam_id_field)

        self._variant_field = QLineEdit()
        self._variant_field.setPlaceholderText("numeric variant")
        form.addRow("Variant number:", self._variant_field)

        root.addLayout(form)

        # Error label (hidden by default)
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)
        self._error_label.hide()
        root.addWidget(self._error_label)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._start_btn = QPushButton("Start Exam")
        self._start_btn.setMinimumWidth(120)
        self._start_btn.clicked.connect(self._on_start_exam)
        btn_row.addWidget(self._start_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

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
