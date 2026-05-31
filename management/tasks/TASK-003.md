# TASK-003: FastAPI project skeleton + dependencies

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Bootstrap `server/` FastAPI app with all required dependencies, app factory, and basic health endpoint.

Dependencies: fastapi, uvicorn, sqlalchemy (async), alembic, pyjwt, passlib, python-dotenv, httpx (for tests).

App structure:
```
server/app/
├── main.py          # FastAPI app factory
├── config.py        # Settings from env
├── database.py      # Async SQLAlchemy engine + session
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic schemas
├── routers/         # Route handlers
└── services/        # Business logic
```

## Acceptance criteria
- [x] `uvicorn app.main:app` starts without errors
- [x] `GET /health` returns `{"status": "ok"}`
- [x] Database session dependency injected and working
- [x] Alembic initialized, initial migration runnable

## Notes
Blocked by TASK-002.
