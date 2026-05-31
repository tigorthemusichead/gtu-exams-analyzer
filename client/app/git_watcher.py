"""
Background git watcher. Uses QTimer to periodically:
1. Check for uncommitted changes (git diff --stat HEAD or check untracked)
2. If changes exist: git add . && git commit -m "auto: <timestamp>"
3. For each changed file: POST /commits with lines_added/lines_removed
4. If no changes: skip (no empty commits)

Uses QThread + QObject worker pattern for non-blocking operation.
"""
import logging
from datetime import datetime, timezone
from typing import Callable

import git
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from app.api import api_client

logger = logging.getLogger(__name__)


class WatcherWorker(QObject):
    """Worker that runs inside a QThread."""

    commit_sent = pyqtSignal(int)       # emits count of files POSTed
    error_occurred = pyqtSignal(str)    # non-fatal error message
    status_changed = pyqtSignal(str)    # status text for UI

    def __init__(self, repo_path: str, interval_seconds: int = 30):
        super().__init__()
        self.repo_path = repo_path
        self.interval_seconds = interval_seconds
        self._timer: QTimer | None = None
        self._commit_count: int = 0

    def start_timer(self):
        """Called in the worker thread context."""
        self._timer = QTimer()
        self._timer.setInterval(self.interval_seconds * 1000)
        self._timer.timeout.connect(self._run_cycle)
        self._timer.start()
        self.status_changed.emit("Watcher started")
        logger.info("Git watcher started, interval=%ds", self.interval_seconds)

    def stop_timer(self):
        if self._timer:
            self._timer.stop()

    def run_cycle_now(self):
        """Force an immediate cycle (used for final flush on session end)."""
        self._run_cycle()

    def _run_cycle(self):
        try:
            repo = git.Repo(self.repo_path)

            # Check for changes: untracked files or modified files
            has_changes = (
                bool(repo.untracked_files)
                or bool(repo.index.diff(None))
                or bool(repo.index.diff("HEAD"))
            )

            if not has_changes:
                # Also check if there's anything to stage that differs from HEAD
                try:
                    diff_stat = repo.git.diff("HEAD", "--stat")
                    has_changes = bool(diff_stat.strip())
                except git.GitCommandError:
                    # No commits yet — check for untracked
                    has_changes = bool(repo.untracked_files)

            if not has_changes:
                self.status_changed.emit("No changes")
                return

            # Stage all changes
            repo.git.add(".")

            # Commit
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            commit_msg = f"auto: {timestamp}"

            try:
                commit = repo.index.commit(commit_msg)
            except Exception as e:
                # Nothing to commit after add (edge case)
                self.status_changed.emit("No changes to commit")
                return

            # Parse diff for lines added/removed per file
            try:
                parent = commit.parents[0] if commit.parents else None
                if parent:
                    diffs = parent.diff(commit, create_patch=True)
                else:
                    # First commit — diff against empty tree
                    diffs = commit.diff(git.NULL_TREE, create_patch=True)
            except Exception:
                diffs = []

            payloads = []
            for diff in diffs:
                lines_added = 0
                lines_removed = 0
                diff_text = None
                if diff.diff:
                    diff_text = (
                        diff.diff.decode("utf-8", errors="replace")
                        if isinstance(diff.diff, bytes)
                        else diff.diff
                    )
                    for line in diff_text.splitlines():
                        if line.startswith("+") and not line.startswith("+++"):
                            lines_added += 1
                        elif line.startswith("-") and not line.startswith("---"):
                            lines_removed += 1

                file_name = diff.b_path or diff.a_path or "unknown"
                payloads.append(
                    {
                        "commit_id": commit.hexsha,
                        "timestamp": timestamp,
                        "exercise_id": "default",
                        "file_name": file_name,
                        "lines_added": lines_added,
                        "lines_removed": lines_removed,
                        "diff": diff_text,
                    }
                )

            if payloads:
                try:
                    resp = api_client.post("/commits", {"commits": payloads})
                    if resp.status_code == 201:
                        self._commit_count += len(payloads)
                        self.commit_sent.emit(len(payloads))
                        self.status_changed.emit(
                            f"Sent {len(payloads)} file(s) at {timestamp}"
                        )
                    else:
                        self.error_occurred.emit(f"Server error {resp.status_code}")
                except Exception as e:
                    # Network failure — non-fatal, will retry next cycle
                    self.error_occurred.emit(f"Network error: {e}")
                    logger.warning("POST /commits failed: %s", e)

        except Exception as e:
            self.error_occurred.emit(f"Watcher error: {e}")
            logger.error("Watcher cycle error: %s", e)


class GitWatcher:
    """
    Manages a WatcherWorker running in a QThread.
    Usage:
        watcher = GitWatcher(repo_path="/path/to/repo", interval_seconds=30)
        watcher.commit_sent.connect(my_slot)
        watcher.start()
        # ...
        watcher.flush_and_stop()
    """

    def __init__(self, repo_path: str, interval_seconds: int = 30):
        self.repo_path = repo_path
        self.interval_seconds = interval_seconds
        self.is_running = False
        self._thread: QThread | None = None
        self._worker: WatcherWorker | None = None

    @property
    def commit_sent(self):
        return self._worker.commit_sent if self._worker else None

    @property
    def error_occurred(self):
        return self._worker.error_occurred if self._worker else None

    @property
    def status_changed(self):
        return self._worker.status_changed if self._worker else None

    def start(self):
        if self.is_running:
            return
        self._thread = QThread()
        self._worker = WatcherWorker(self.repo_path, self.interval_seconds)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start_timer)
        self._thread.start()
        self.is_running = True

    def flush_and_stop(self):
        """Force one final cycle then stop."""
        if self._worker:
            self._worker.run_cycle_now()
        self.stop()

    def stop(self):
        if not self.is_running:
            return
        if self._worker:
            self._worker.stop_timer()
        if self._thread:
            self._thread.quit()
            self._thread.wait(3000)
        self.is_running = False
