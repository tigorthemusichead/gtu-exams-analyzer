# TASK-002: Set up monorepo structure

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Initialize monorepo layout with two packages: `server/` (FastAPI) and `client/` (PyQt6). Add root-level tooling config.

Expected layout:
```
cheat-buster/
├── server/
│   ├── pyproject.toml
│   ├── app/
│   │   └── __init__.py
│   └── ...
├── client/
│   ├── pyproject.toml
│   ├── app/
│   │   └── __init__.py
│   └── ...
├── docs/
├── management/
└── README.md
```

## Acceptance criteria
- [ ] `server/` and `client/` directories created with minimal pyproject.toml each
- [ ] Root README.md documents how to run each package
- [ ] `.gitignore` covers Python, PyQt6, venv artifacts

## Notes
Both packages use Python. Use separate virtual envs or uv workspaces.
