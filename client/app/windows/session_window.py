from datetime import datetime, timezone

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget


class SessionWindow(QWidget):
    finish_exam = pyqtSignal()

    def __init__(self, repo_path: str, interval_seconds: int = 30, parent=None):
        super().__init__(parent)
        self.repo_path = repo_path
        self.interval_seconds = interval_seconds
        self._countdown = interval_seconds
        self._commit_count = 0
        self.setWindowTitle("cheat-buster — Active Session")
        self.setMinimumSize(500, 380)
        self._build_ui()
        self._start_countdown()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 32, 32, 32)

        self._title_label = QLabel("Active Session")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self._title_label.font()
        font.setPointSize(18)
        font.setBold(True)
        self._title_label.setFont(font)
        layout.addWidget(self._title_label)

        self._repo_label = QLabel(f"Repository: {self.repo_path}")
        self._repo_label.setWordWrap(True)
        self._repo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._repo_label)

        layout.addSpacing(8)

        self._countdown_label = QLabel(
            f"Next snapshot in: {self._countdown}s"
        )
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._countdown_label)

        self._last_commit_label = QLabel("Last commit: Never")
        self._last_commit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._last_commit_label)

        self._count_label = QLabel("Commits sent: 0")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._count_label)

        self._status_label = QLabel("Status: Active")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        layout.addStretch()

        self._finish_btn = QPushButton("Finish Exam")
        self._finish_btn.setMinimumHeight(40)
        self._finish_btn.clicked.connect(self._on_finish_clicked)
        layout.addWidget(self._finish_btn)

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
        self._countdown_label.setText(f"Next snapshot in: {self._countdown}s")

    def on_commit_sent(self, count: int):
        self._commit_count += count
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self._last_commit_label.setText(f"Last commit: {ts} UTC")
        self._count_label.setText(f"Commits sent: {self._commit_count}")
        self._status_label.setText("Status: Active")
        self._countdown = self.interval_seconds  # reset countdown

    def on_error(self, msg: str):
        self._status_label.setText(f"Status: Error — {msg}")
