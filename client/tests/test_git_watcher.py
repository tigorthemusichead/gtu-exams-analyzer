"""Unit tests for app.git_watcher.WatcherWorker._run_cycle logic.

Qt objects are not instantiated here — only the pure cycle logic is tested
by calling _run_cycle with mocked dulwich API and api_client.
"""

from unittest.mock import MagicMock


FAKE_SHA = b"deadbeef00000000000000000000000000000000"


def make_worker(repo_path: str = "/fake/repo"):
    """Create WatcherWorker without starting Qt thread."""
    from app.git_watcher import WatcherWorker
    worker = WatcherWorker.__new__(WatcherWorker)
    worker.repo_path = repo_path
    worker.interval_seconds = 30
    worker._timer = None
    worker._commit_count = 0
    worker.status_changed = MagicMock()
    worker.error_occurred = MagicMock()
    worker.commit_sent = MagicMock()
    return worker


def make_status(untracked=None, unstaged=None, staged=None):
    s = MagicMock()
    s.untracked = untracked or []
    s.unstaged = unstaged or []
    s.staged = staged or {"add": [], "modify": [], "delete": []}
    return s


def make_repo_mock(commit_sha=FAKE_SHA, has_parents=True):
    mock_repo = MagicMock()
    mock_commit_obj = MagicMock()
    mock_commit_obj.tree = b"treesha" + b"0" * 33
    mock_parent_obj = MagicMock()
    mock_parent_obj.tree = b"ptreesha" + b"0" * 32
    if has_parents:
        mock_commit_obj.parents = [b"parentsha" + b"0" * 31]
        mock_repo.__getitem__.side_effect = (
            lambda sha: mock_commit_obj if sha == commit_sha else mock_parent_obj
        )
    else:
        mock_commit_obj.parents = []
        mock_repo.__getitem__.return_value = mock_commit_obj
    mock_conf = MagicMock()
    mock_conf.get.side_effect = lambda s, k: b"Student" if k == b"name" else b"s@test.com"
    mock_repo.get_config.return_value = mock_conf
    return mock_repo


def test_run_cycle_no_changes(mocker):
    """When no changes, cycle emits 'No changes' and does not commit."""
    mocker.patch("app.git_watcher.Repo", return_value=MagicMock())
    mocker.patch("app.git_watcher.porcelain.status", return_value=make_status())
    mock_commit = mocker.patch("app.git_watcher.porcelain.commit")

    worker = make_worker()
    worker._run_cycle()

    mock_commit.assert_not_called()
    worker.status_changed.emit.assert_called_with("No changes")


def test_run_cycle_with_changes_posts_commits(mocker):
    """When changes exist, commits and POSTs to server."""
    mock_repo = make_repo_mock()
    mocker.patch("app.git_watcher.Repo", return_value=mock_repo)
    mocker.patch("app.git_watcher.porcelain.status", return_value=make_status(untracked=[b"main.py"]))
    mocker.patch("app.git_watcher.porcelain.add")
    mocker.patch("app.git_watcher.porcelain.commit", return_value=FAKE_SHA)

    fake_change = MagicMock()
    fake_change.old.path = b"main.py"
    fake_change.new.path = b"main.py"
    mocker.patch("app.git_watcher.tree_changes", return_value=[fake_change])
    mocker.patch(
        "app.git_watcher.write_object_diff",
        side_effect=lambda buf, store, old, new: buf.write(b"+def foo():\n+    pass\n-old\n"),
    )

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_api = mocker.patch("app.git_watcher.api_client")
    mock_api.post.return_value = mock_response

    worker = make_worker()
    worker._run_cycle()

    mock_api.post.assert_called_once()
    call_args = mock_api.post.call_args
    assert call_args[0][0] == "/commits"
    commits_payload = call_args[0][1]["commits"]
    assert len(commits_payload) == 1
    assert commits_payload[0]["commit_id"] == FAKE_SHA.decode()
    assert commits_payload[0]["lines_added"] == 2
    assert commits_payload[0]["lines_removed"] == 1


def test_run_cycle_network_error_non_fatal(mocker):
    """Network failure during POST is non-fatal — emits error_occurred."""
    mock_repo = make_repo_mock(has_parents=False)
    mocker.patch("app.git_watcher.Repo", return_value=mock_repo)
    mocker.patch("app.git_watcher.porcelain.status", return_value=make_status(untracked=[b"f.py"]))
    mocker.patch("app.git_watcher.porcelain.add")
    mocker.patch("app.git_watcher.porcelain.commit", return_value=FAKE_SHA)

    fake_change = MagicMock()
    fake_change.old.path = b"f.py"
    fake_change.new.path = b"f.py"
    mocker.patch("app.git_watcher.tree_changes", return_value=[fake_change])
    mocker.patch(
        "app.git_watcher.write_object_diff",
        side_effect=lambda buf, store, old, new: buf.write(b"+x\n"),
    )

    mock_api = mocker.patch("app.git_watcher.api_client")
    mock_api.post.side_effect = Exception("Connection refused")

    worker = make_worker()
    worker._run_cycle()  # Must not raise

    worker.error_occurred.emit.assert_called_once()
    assert "Network error" in worker.error_occurred.emit.call_args[0][0]


def test_run_cycle_server_error_emits_error(mocker):
    """Non-201 server response emits error_occurred."""
    mock_repo = make_repo_mock()
    mocker.patch("app.git_watcher.Repo", return_value=mock_repo)
    mocker.patch("app.git_watcher.porcelain.status", return_value=make_status(untracked=[b"g.py"]))
    mocker.patch("app.git_watcher.porcelain.add")
    mocker.patch("app.git_watcher.porcelain.commit", return_value=FAKE_SHA)

    fake_change = MagicMock()
    fake_change.old.path = b"g.py"
    fake_change.new.path = b"g.py"
    mocker.patch("app.git_watcher.tree_changes", return_value=[fake_change])
    mocker.patch(
        "app.git_watcher.write_object_diff",
        side_effect=lambda buf, store, old, new: buf.write(b"+y\n"),
    )

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_api = mocker.patch("app.git_watcher.api_client")
    mock_api.post.return_value = mock_response

    worker = make_worker()
    worker._run_cycle()

    worker.error_occurred.emit.assert_called_once()
    assert "500" in worker.error_occurred.emit.call_args[0][0]
