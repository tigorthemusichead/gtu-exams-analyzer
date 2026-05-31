# TASK-015: Server unit tests

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
Write pytest test suite for the FastAPI server. Currently `server/tests/__init__.py` is empty — no tests exist.

Cover:
- `auth_service`: register, login, JWT generation/validation
- `routers/auth`: POST /auth/register, POST /auth/login (student + teacher paths)
- `routers/exams`: CRUD — create, list, get (teacher-only guards)
- `routers/commits`: POST ingestion, duplicate handling, auth guard
- `routers/analysis`: trigger analysis, fetch report, 404 on missing exam
- `services/analysis_individual`: burst detection, late_start, inactivity_gap, score formula
- `services/analysis_group`: cosine, structural (Jaccard), sequential scores, edge threshold, combine weights

Use `httpx.AsyncClient` + `pytest-asyncio` for router tests with in-memory SQLite.
Pure service functions (analysis_individual, analysis_group) use unit tests with crafted `CommitRecord` lists.

## Acceptance criteria
- [ ] `pytest server/` passes with no failures
- [ ] Coverage ≥ 80% on `app/services/` and `app/routers/`
- [ ] Edge cases covered: empty commit list, single student, all-identical commits
- [ ] Auth guards tested: 401 on missing token, 403 on wrong role

## Notes
Add `pytest`, `pytest-asyncio`, `httpx` to `server/pyproject.toml` dev deps if not present.
