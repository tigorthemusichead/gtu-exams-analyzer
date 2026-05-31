"""Unit tests for app.git_watcher.WatcherWorker._run_cycle logic.

Qt objects are not instantiated here — only the pure cycle logic is tested
by calling _run_cycle with mocked git.Repo and api_client.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


def make_worker(repo_path: str = "/fake/repo"):
    """Create WatcherWorker without starting Qt thread."""
    # Patch PyQt6 signal machinery so no QApplication is needed
    with patch("app.git_watcher.QObject.__init__", return_value=None):
        with patch("app.git_watcher.WatcherWorker.commit_sent", create=True, new_callable=lambda: property(lambda self: None)):
            pass
    from app.git_watcher import WatcherWorker
    worker = WatcherWorker.__new__(WatcherWorker)
    worker.repo_path = repo_path
    worker.interval_seconds = 30
    worker._timer = None
    worker._commit_count = 0
    return worker


class FakeDiff:
    """Minimal git diff object."""
    def __init__(self, b_path="solution.py", diff_text=b"+line1\n+line2\n-old_line\n"):
        self.b_path = b_path
        self.a_path = b_path
        self.diff = diff_text


def test_run_cycle_no_changes(mocker):
    """When no changes, cycle emits 'No changes' and does not commit."""
    from app.git_watcher import WatcherWorker

    mock_repo = MagicMock()
    mock_repo.untracked_files = []
    mock_repo.index.diff.return_value = []
    mock_repo.git.diff.return_value = ""

    mocker.patch("app.git_watcher.git.Repo", return_value=mock_repo)
    emit_status = mocker.patch.object(WatcherWorker, "status_changed", create=True)

    worker = WatcherWorker.__new__(WatcherWorker)
    worker.repo_path = "/fake"
    worker.interval_seconds = 30
    worker._timer = None
    worker._commit_count = 0

    # Patch signals as simple callables
    worker.status_changed = MagicMock()
    worker.error_occurred = MagicMock()
    worker.commit_sent = MagicMock()

    worker._run_cycle()

    # Should not commit anything
    mock_repo.index.commit.assert_not_called()
    worker.status_changed.emit.assert_called_with("No changes")


def test_run_cycle_with_changes_posts_commits(mocker):
    """When changes exist, commits and POSTs to server."""
    from app.git_watcher import WatcherWorker

    fake_commit = MagicMock()
    fake_commit.hexsha = "deadbeef"
    fake_diff = FakeDiff("main.py", b"+def foo():\n+    pass\n-old\n")
    fake_commit.parents = [MagicMock()]
    fake_commit.parents[0].diff.return_value = [fake_diff]

    mock_repo = MagicMock()
    mock_repo.untracked_files = ["new_file.py"]
    mock_repo.index.diff.return_value = []
    mock_repo.index.commit.return_value = fake_commit

    mocker.patch("app.git_watcher.git.Repo", return_value=mock_repo)

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_api = mocker.patch("app.git_watcher.api_client")
    mock_api.post.return_value = mock_response

    worker = WatcherWorker.__new__(WatcherWorker)
    worker.repo_path = "/fake"
    worker.interval_seconds = 30
    worker._timer = None
    worker._commit_count = 0
    worker.status_changed = MagicMock()
    worker.error_occurred = MagicMock()
    worker.commit_sent = MagicMock()

    worker._run_cycle()

    mock_repo.git.add.assert_called_once_with(".")
    mock_repo.index.commit.assert_called_once()
    mock_api.post.assert_called_once()
    call_args = mock_api.post.call_args
    assert call_args[0][0] == "/commits"
    commits_payload = call_args[0][1]["commits"]
    assert len(commits_payload) == 1
    assert commits_payload[0]["commit_id"] == "deadbeef"
    assert commits_payload[0]["lines_added"] == 2
    assert commits_payload[0]["lines_removed"] == 1


def test_run_cycle_network_error_non_fatal(mocker):
    """Network failure during POST is non-fatal — emits error_occurred."""
    from app.git_watcher import WatcherWorker

    fake_commit = MagicMock()
    fake_commit.hexsha = "aabb"
    fake_commit.parents = []
    fake_diff = FakeDiff("f.py", b"+x\n")

    # First commit (no parents) → diff against NULL_TREE
    mocker.patch("app.git_watcher.git.NULL_TREE", create=True, new=None)
    fake_commit.diff.return_value = [fake_diff]

    mock_repo = MagicMock()
    mock_repo.untracked_files = ["f.py"]
    mock_repo.index.diff.return_value = []
    mock_repo.index.commit.return_value = fake_commit

    mocker.patch("app.git_watcher.git.Repo", return_value=mock_repo)

    mock_api = mocker.patch("app.git_watcher.api_client")
    mock_api.post.side_effect = Exception("Connection refused")

    worker = WatcherWorker.__new__(WatcherWorker)
    worker.repo_path = "/fake"
    worker.interval_seconds = 30
    worker._timer = None
    worker._commit_count = 0
    worker.status_changed = MagicMock()
    worker.error_occurred = MagicMock()
    worker.commit_sent = MagicMock()

    # Should not raise
    worker._run_cycle()

    worker.error_occurred.emit.assert_called_once()
    assert "Network error" in worker.error_occurred.emit.call_args[0][0]


def test_run_cycle_server_error_emits_error(mocker):
    """Non-201 server response emits error_occurred."""
    from app.git_watcher import WatcherWorker

    fake_commit = MagicMock()
    fake_commit.hexsha = "cc"
    fake_diff = FakeDiff("g.py", b"+y\n")
    fake_commit.parents = [MagicMock()]
    fake_commit.parents[0].diff.return_value = [fake_diff]

    mock_repo = MagicMock()
    mock_repo.untracked_files = ["g.py"]
    mock_repo.index.diff.return_value = []
    mock_repo.index.commit.return_value = fake_commit

    mocker.patch("app.git_watcher.git.Repo", return_value=mock_repo)

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_api = mocker.patch("app.git_watcher.api_client")
    mock_api.post.return_value = mock_response

    worker = WatcherWorker.__new__(WatcherWorker)
    worker.repo_path = "/fake"
    worker.interval_seconds = 30
    worker._timer = None
    worker._commit_count = 0
    worker.status_changed = MagicMock()
    worker.error_occurred = MagicMock()
    worker.commit_sent = MagicMock()

    worker._run_cycle()

    worker.error_occurred.emit.assert_called_once()
    assert "500" in worker.error_occurred.emit.call_args[0][0]
