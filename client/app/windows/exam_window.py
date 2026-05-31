from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


class ExamWindow(QWidget):
    continue_clicked = pyqtSignal()
    logout = pyqtSignal()

    def __init__(self, exam_id: int, parent=None):
        super().__init__(parent)
        self.exam_id = exam_id
        self.setWindowTitle("cheat-buster — Exam Confirmed")
        self.setMinimumSize(500, 350)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(20)

        # Title
        title = QLabel("Exam Started")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        # Exam ID display
        exam_label = QLabel(f"Exam ID: {self.exam_id}")
        exam_font = QFont()
        exam_font.setPointSize(13)
        exam_label.setFont(exam_font)
        exam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(exam_label)

        root.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        self._logout_btn = QPushButton("Logout")
        self._logout_btn.setMinimumWidth(100)
        self._logout_btn.clicked.connect(self.logout.emit)
        btn_row.addWidget(self._logout_btn)

        btn_row.addStretch()

        self._continue_btn = QPushButton("Continue to directory selection")
        self._continue_btn.setMinimumWidth(220)
        self._continue_btn.clicked.connect(self.continue_clicked.emit)
        btn_row.addWidget(self._continue_btn)

        root.addLayout(btn_row)

        self.setLayout(root)
