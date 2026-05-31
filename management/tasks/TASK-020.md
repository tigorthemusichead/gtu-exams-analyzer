# TASK-020: Alembic migration wiring

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
Alembic is installed and `alembic.ini` + `alembic/` directory exist in `server/`, but migrations are not wired to the actual ORM models. The DB is currently created via `SQLAlchemy metadata.create_all()` directly.

Tasks:
1. Set `target_metadata = Base.metadata` in `alembic/env.py`
2. Run `alembic revision --autogenerate -m "initial_schema"` to generate migration from current models
3. Verify migration matches `db/migrations/001_initial_schema.sql`
4. Replace `metadata.create_all()` call in app startup with `alembic upgrade head` (or keep create_all for dev, add note)
5. Document migration workflow in README

## Acceptance criteria
- [ ] `alembic upgrade head` creates a working database
- [ ] `alembic revision --autogenerate` detects no drift after migration applied
- [ ] Existing `seed.py` works after migration
- [ ] README documents `alembic upgrade head` as setup step

## Notes
SQLite has limited ALTER TABLE support — Alembic needs `render_as_batch=True` in env.py for future schema changes.
