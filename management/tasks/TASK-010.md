# TASK-010: PyQt6 student client skeleton

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Bootstrap `client/` PyQt6 application with app factory, main window, and basic navigation structure.

Dependencies: PyQt6, httpx, gitpython, python-dotenv.

App structure:
```
client/app/
├── main.py           # QApplication entry point
├── config.py         # Server URL from .env
├── api.py            # HTTP client (httpx) for backend calls
├── git_watcher.py    # Git operations + periodic timer
├── windows/
│   ├── auth_window.py
│   ├── exam_window.py   # Directory picker + active session view
│   └── ...
└── widgets/          # Reusable Qt widgets
```

## Acceptance criteria
- [x] `python -m app.main` launches window without errors on macOS, Windows, Linux
- [x] Main window with placeholder navigation between screens
- [x] `config.py` reads `SERVER_URL` from `.env`
- [x] `api.py` has base `httpx.Client` with auth token injection

## Notes
Blocked by TASK-002.
