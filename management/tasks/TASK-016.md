# TASK-016: Client unit tests

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
Write pytest test suite for the PyQt6 student client. Currently `client/tests/__init__.py` is empty.

Cover:
- `git_watcher.py`: cycle logic — diff detection, commit creation, POST dispatch; mock `git.Repo` and `httpx`
- `api.py`: all API wrapper methods — verify correct URL construction, headers (JWT), request body; mock HTTP responses
- Window state transitions: auth → exam select → dir picker → session (use `pytest-qt` for Qt widget testing)

## Acceptance criteria
- [ ] `pytest client/` passes with no failures
- [ ] `git_watcher` tested with mocked repo: detects changes, skips when no diff, handles network error gracefully
- [ ] `api.py` methods tested against mocked httpx responses (success + 4xx/5xx paths)
- [ ] Qt windows instantiate without crashing under headless test runner

## Notes
Add `pytest`, `pytest-qt`, `pytest-mock` to `client/pyproject.toml` dev deps.
Headless Qt testing may require `QT_QPA_PLATFORM=offscreen` env var in CI.
