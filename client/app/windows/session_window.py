from datetime import datetime, timezone

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)


class SessionWindow(QWidget):
    finish_exam = pyqtSignal()

    def __init__(self, repo_path: str, interval_seconds: int = 30, parent=None):
        super().__init__(parent)
        self.repo_path = repo_path
        self.interval_seconds = interval_seconds
        self._countdown = interval_seconds
        self._commit_count = 0
        self.setWindowTitle("cheat-buster — Active Session")
        self.setMinimumSize(500, 420)
        self._build_ui()
        self._start_countdown()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(40, 36, 40, 36)

        # ── Title ─────────────────────────────────────────────────────────
        title = QLabel("Active Session")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        layout.addSpacing(6)

        repo_label = QLabel(self.repo_path)
        repo_label.setWordWrap(True)
        repo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        repo_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        layout.addWidget(repo_label)
        layout.addSpacing(24)

        # ── Stats card ────────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)

        self._countdown_label = self._stat_row(
            card_layout, "Next snapshot", f"{self._countdown}s"
        )
        self._last_commit_label = self._stat_row(
            card_layout, "Last commit", "Never"
        )
        self._count_label = self._stat_row(
            card_layout, "Commits sent", "0"
        )

        # Status row with indicator dot
        self._status_label = self._stat_row(
            card_layout, "Status", "\u25cf Active", value_style="color: #16A34A; font-weight: 600;"
        )

        layout.addWidget(card)
        layout.addStretch()

        # ── Finish button ─────────────────────────────────────────────────
        self._finish_btn = QPushButton("Finish Exam")
        self._finish_btn.setProperty("role", "danger")
        self._finish_btn.setMinimumHeight(44)
        self._finish_btn.clicked.connect(self._on_finish_clicked)
        layout.addWidget(self._finish_btn)

    def _stat_row(
        self,
        parent_layout: QVBoxLayout,
        label_text: str,
        value_text: str,
        value_style: str = "",
    ) -> QLabel:
        """Add a labeled stat row to parent_layout; return the value QLabel."""
        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent;")
        row_layout = QVBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(2)

        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 600; background: transparent;")
        row_layout.addWidget(lbl)

        val = QLabel(value_text)
        val_font = QFont()
        val_font.setPointSize(13)
        val.setFont(val_font)
        val.setStyleSheet(f"color: #1E1B4B; background: transparent; {value_style}")
        row_layout.addWidget(val)

        parent_layout.addWidget(row_widget)
        return val

    def _on_finish_clicked(self):
        """Show confirmation dialog before ending session."""
        reply = QMessageBox.question(
            self,
            "Finish Exam",
            "Are you sure you want to finish the exam?\n\nA final snapshot will be sent before closing.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.finish_exam.emit()

    def closeEvent(self, event):
        """Intercept window X button — show same confirmation as Finish Exam."""
        reply = QMessageBox.question(
            self,
            "Finish Exam",
            "Are you sure you want to finish the exam?\n\nA final snapshot will be sent before closing.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.finish_exam.emit()
            event.accept()
        else:
            event.ignore()

    def _start_countdown(self):
        self._timer = QTimer()
        self._timer.setInterval(1000)  # 1 second tick
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        self._countdown -= 1
        if self._countdown <= 0:
            self._countdown = self.interval_seconds
        self._countdown_label.setText(f"{self._countdown}s")

    def on_commit_sent(self, count: int):
        self._commit_count += count
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self._last_commit_label.setText(f"{ts} UTC")
        self._count_label.setText(str(self._commit_count))
        self._status_label.setText("\u25cf Active")
        self._status_label.setStyleSheet("color: #16A34A; font-weight: 600; background: transparent;")
        self._countdown = self.interval_seconds  # reset countdown

    def on_error(self, msg: str):
        self._status_label.setText(f"\u25cf Error — {msg}")
        self._status_label.setStyleSheet("color: #DC2626; font-weight: 600; background: transparent;")
