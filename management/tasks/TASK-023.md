# TASK-023: Fix dashboard showing all teachers' exams instead of own exams only

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
`web.py:39` runs `select(Exam)` with no teacher filter. Any authenticated teacher
sees every exam in the database, including those created by other teachers.

The API `list_exams` endpoint (`exams.py:86`) correctly filters by `teacher_id`.
The web dashboard must do the same.

Affected file:
- `server/app/routers/web.py:39` — `result = await db.execute(select(Exam))`

## Acceptance criteria
- [ ] Dashboard only shows exams belonging to the logged-in teacher
- [ ] Filter uses teacher identity from the session token (or equivalent auth mechanism)
- [ ] A second teacher account sees only their own exams, not the first teacher's

## Notes
The web routes currently have no server-side auth at all (see TASK-024). Resolving
TASK-024 first (adding `require_teacher` to web routes) will make the teacher ID
available here, enabling the filter.
```

