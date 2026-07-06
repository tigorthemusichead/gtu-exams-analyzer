import io
import logging
import os
from datetime import datetime, timezone

from dulwich import porcelain
from dulwich.diff_tree import tree_changes
from dulwich.patch import write_object_diff
from dulwich.repo import Repo
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from app.api import api_client

logger = logging.getLogger(__name__)


class WatcherWorker(QObject):

    commit_sent = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    status_changed = pyqtSignal(str)

    def __init__(self, repo_path: str, interval_seconds: int = 30):
        super().__init__()
        self.repo_path = repo_path
        self.interval_seconds = interval_seconds
        self._timer: QTimer | None = None
        self._commit_count: int = 0

    def start_timer(self):

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
        self._run_cycle()

    def _run_cycle(self):
        try:
            repo = Repo(self.repo_path)
            status = porcelain.status(repo)

            has_changes = bool(
                status.staged["add"]
                or status.staged["modify"]
                or status.staged["delete"]
                or status.unstaged
                or status.untracked
            )

            if not has_changes:
                self.status_changed.emit("No changes")
                return


            all_paths = list(status.untracked) + list(status.unstaged)
            if all_paths:
                porcelain.add(repo, paths=all_paths)


            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            commit_msg = f"auto: {timestamp}"

            try:
                conf = repo.get_config()
                name = conf.get((b"user",), b"name").decode()
                email = conf.get((b"user",), b"email").decode()
                identity = f"{name} <{email}>".encode()
                commit_sha = porcelain.commit(
                    repo,
                    message=commit_msg.encode(),
                    author=identity,
                    committer=identity,
                )
            except Exception:
                self.status_changed.emit("No changes to commit")
                return

            commit_id = commit_sha.decode() if isinstance(commit_sha, bytes) else commit_sha
            commit_obj = repo[commit_sha]
            parent_tree_id = repo[commit_obj.parents[0]].tree if commit_obj.parents else None

            try:
                changes = list(tree_changes(repo.object_store, parent_tree_id, commit_obj.tree))
            except Exception:
                changes = []

            payloads = []
            for change in changes:
                buf = io.BytesIO()
                try:
                    write_object_diff(buf, repo.object_store, change.old, change.new)
                except Exception:
                    pass
                diff_bytes = buf.getvalue()

                lines_added = 0
                lines_removed = 0
                diff_text = None
                if diff_bytes:
                    diff_text = diff_bytes.decode("utf-8", errors="replace")
                    for line in diff_text.splitlines():
                        if line.startswith("+") and not line.startswith("+++"):
                            lines_added += 1
                        elif line.startswith("-") and not line.startswith("---"):
                            lines_removed += 1

                raw_path = change.new.path if change.new.path else change.old.path
                file_name = raw_path.decode() if isinstance(raw_path, bytes) else (raw_path or "unknown")

                payloads.append(
                    {
                        "commit_id": commit_id,
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
                    self.error_occurred.emit(f"Network error: {e}")
                    logger.warning("POST /commits failed: %s", e)

        except Exception as e:
            self.error_occurred.emit(f"Watcher error: {e}")
            logger.error("Watcher cycle error: %s", e)


class GitWatcher:

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
