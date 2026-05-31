# TASK-021: Docker Compose deployment setup

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
No containerization or deployment setup exists. Add Docker support for the server so it can be run reproducibly.

Deliverables:
- `server/Dockerfile` — multi-stage build: install deps with uv, copy app, run uvicorn
- `docker-compose.yml` at repo root — server service, volume-mount SQLite db file
- `.dockerignore` — exclude `.venv`, `__pycache__`, `.env`, `*.db`
- Document `docker compose up` workflow in README

Client apps (PyQt6) are desktop apps and don't need containerization.

## Acceptance criteria
- [ ] `docker compose up` starts server on port 8000
- [ ] Server connects to persisted SQLite volume (data survives container restart)
- [ ] `docker compose up` uses `.env` file for config (SECRET_KEY etc)
- [ ] README updated with Docker setup instructions

## Notes
SQLite file should be mounted as a volume at `/app/data/cheat_buster.db`.
Use `python:3.11-slim` base image.
