# TASK-013: Periodic git watcher + HTTP POST

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Core background worker that periodically snapshots changes and sends them to server.

Cycle (every N seconds, configurable, default 30):
1. `git diff --stat HEAD` → detect changed files
2. If changes exist:
   a. `git add .`
   b. `git commit -m "auto: <timestamp>"`
   c. For each changed file: parse lines_added, lines_removed from diff
   d. `POST /commits` with payload per file
3. If no changes: skip (no empty commits)

Implementation:
- Use `QTimer` in PyQt6 for non-blocking periodic execution on main thread, or `QThread` for background
- Use `gitpython` for all git operations
- Use `httpx` for HTTP POST

Active session view shows:
- Timer countdown to next snapshot
- Last commit timestamp
- Running count of commits sent
- Connection status indicator

## Acceptance criteria
- [x] Timer fires every N seconds without blocking UI
- [x] Empty working tree skips commit cycle (no empty commits created)
- [x] Each changed file generates one POST request per cycle
- [x] Network failure logged and retried next cycle (non-fatal)
- [x] lines_added / lines_removed correctly parsed from git diff output
- [x] Commit messages include timestamp

## Notes
Blocked by TASK-012. N configurable via `.env` or UI setting.
