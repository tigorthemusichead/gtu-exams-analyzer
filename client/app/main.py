import os
import shutil
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox, QStackedWidget

from app.api import api_client
from app.git_watcher import GitWatcher
from app.theme import STYLESHEET
from app.windows.auth_window import AuthWindow
from app.windows.dir_picker_window import DirPickerWindow
from app.windows.exam_window import ExamWindow
from app.windows.session_window import SessionWindow

_ICO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "logo.png")


class MainApp(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("cheat-buster")
        self.setMinimumSize(540, 420)
        self._auth_window = AuthWindow()
        self.addWidget(self._auth_window)
        self._auth_window.auth_success.connect(self._on_auth)
        self._repo_path: str | None = None
        self._watcher: GitWatcher | None = None
        self._session_window: SessionWindow | None = None

    def _on_auth(self, exam_id: int, student_email: str):
        exam_win = ExamWindow(exam_id)
        self.addWidget(exam_win)
        self.setCurrentWidget(exam_win)
        exam_win.logout.connect(self._on_logout)
        exam_win.continue_clicked.connect(
            lambda: self._show_dir_picker(exam_id, student_email)
        )

    def _show_dir_picker(self, exam_id: int, student_email: str):
        dir_win = DirPickerWindow(exam_id, student_email)
        self.addWidget(dir_win)
        self.setCurrentWidget(dir_win)
        dir_win.back.connect(lambda: self.setCurrentIndex(self.currentIndex() - 1))
        dir_win.session_ready.connect(self._on_session_ready)

    def _on_session_ready(self, repo_path: str):
        self._repo_path = repo_path
        interval = int(os.getenv("WATCHER_INTERVAL_SECONDS", "30"))

        # Create session window
        session_win = SessionWindow(repo_path, interval_seconds=interval)
        self.addWidget(session_win)
        self.setCurrentWidget(session_win)
        session_win.finish_exam.connect(self._on_finish_exam)
        self._session_window = session_win

        # Start git watcher
        self._watcher = GitWatcher(repo_path, interval_seconds=interval)
        self._watcher.start()
        self._watcher.commit_sent.connect(session_win.on_commit_sent)
        self._watcher.error_occurred.connect(session_win.on_error)

    def _on_finish_exam(self):
        """
        Full graceful shutdown:
        1. Stop the countdown timer in session_window (prevent UI updates during shutdown)
        2. Force final git commit + POST via watcher.flush_and_stop()
        3. Clear JWT from memory
        4. Navigate back to auth screen
        5. Reset watcher reference
        """
        # Stop UI countdown timer
        if self._session_window and hasattr(self._session_window, '_timer'):
            self._session_window._timer.stop()

        # Flush: force final commit + HTTP POST
        if self._watcher:
            try:
                self._watcher.flush_and_stop()
            except Exception:
                pass  # non-fatal if server unreachable
            self._watcher = None

        # Clear auth token
        api_client.clear_token()

        # Reset session state
        self._repo_path = None
        self._session_window = None

        # Return to auth screen
        self.setCurrentWidget(self._auth_window)

    def closeEvent(self, event):
        """Intercept main window close — run graceful shutdown if session active."""
        if self._watcher and self._watcher.is_running:
            reply = QMessageBox.question(
                self,
                "Finish Exam",
                "Exam session is active. Finish exam and quit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_finish_exam()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def _on_logout(self):
        api_client.clear_token()
        self.setCurrentWidget(self._auth_window)


def _check_git():
    git_path = shutil.which("git")
    if git_path is None:
        _app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "Git Not Found",
            "Git is required but not installed.\n\n"
            "Install via Terminal:\n"
            "    xcode-select --install\n\n"
            "Or download from: https://git-scm.com",
        )
        sys.exit(1)
    # Help gitpython find git in bundled app (PATH may differ)
    os.environ.setdefault("GIT_PYTHON_GIT_EXECUTABLE", git_path)


def main():
    _check_git()
    app = QApplication(sys.argv)
    app.setApplicationName("cheat-buster")
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(QIcon(_ICO_PATH))
    window = MainApp()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
