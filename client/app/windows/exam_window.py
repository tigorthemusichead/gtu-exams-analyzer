import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

_LOGO_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "logo.png")
)


class ExamWindow(QWidget):
    continue_clicked = pyqtSignal()
    logout = pyqtSignal()

    def __init__(self, exam_id: int, parent=None):
        super().__init__(parent)
        self.exam_id = exam_id
        self.setWindowTitle("GTU exam monitoring — Exam Confirmed")
        self.setMinimumSize(460, 360)
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

        app_name = QLabel("GTU exam monitoring")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_name.setStyleSheet("color: #6B7280; font-size: 12px; letter-spacing: 0.5px;")
        root.addWidget(app_name)
        root.addSpacing(28)

        # ── Divider ───────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setObjectName("divider")
        root.addWidget(divider)
        root.addSpacing(28)

        # ── Title ─────────────────────────────────────────────────────────
        title = QLabel("Exam Confirmed")
        title_font = QFont()
        title_font.setPointSize(17)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)
        root.addSpacing(20)

        # ── Exam ID card ──────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(4)

        card_title = QLabel("Exam ID")
        card_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_title.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;")
        card_layout.addWidget(card_title)

        exam_id_lbl = QLabel(str(self.exam_id))
        id_font = QFont()
        id_font.setPointSize(28)
        id_font.setBold(True)
        exam_id_lbl.setFont(id_font)
        exam_id_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        exam_id_lbl.setStyleSheet("color: #7C3AED;")
        card_layout.addWidget(exam_id_lbl)

        root.addWidget(card)
        root.addStretch()

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._logout_btn = QPushButton("Logout")
        self._logout_btn.setProperty("role", "secondary")
        self._logout_btn.setMinimumHeight(40)
        self._logout_btn.setMinimumWidth(110)
        self._logout_btn.clicked.connect(self.logout.emit)
        btn_row.addWidget(self._logout_btn)

        btn_row.addStretch()

        self._continue_btn = QPushButton("Continue")
        self._continue_btn.setMinimumHeight(40)
        self._continue_btn.setMinimumWidth(140)
        self._continue_btn.clicked.connect(self.continue_clicked.emit)
        btn_row.addWidget(self._continue_btn)

        root.addLayout(btn_row)

        self.setLayout(root)
