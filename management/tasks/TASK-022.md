# TASK-022: Fix route conflict blocking /exams/new and /exams/{id} HTML pages

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
API exams router is mounted before the web router in `main.py`. Starlette matches
`GET /exams/{exam_id}` loosely — the string "new" and all numeric IDs are captured
by the API route. The `require_teacher` dependency (Bearer token) fires before path
coercion, returning 401 to browser requests that carry no Bearer header.

Result: `/exams/new` and every `/exams/{id}` HTML detail page returns
`{"detail":"Not authenticated"}` instead of the HTML template.

Affected files:
- `server/app/routers/exams.py:93` — `@router.get("/{exam_id}", ...)`
- `server/app/main.py:23-28` — router registration order

## Acceptance criteria
- [ ] Navigating to `/exams/new` while logged in renders the New Exam HTML form
- [ ] Navigating to `/exams/1` while logged in renders the Exam Detail HTML page
- [ ] `GET /exams/{id}` API endpoint still works with Bearer token (e.g. from student client)
- [ ] Use `@router.get("/{exam_id:int}", ...)` in `exams.py` so Starlette rejects non-integer segments at match stage
- [ ] Verify web router is consulted for non-integer paths like "new"

## Notes
Simplest fix: change `exams.py:93` to `/{exam_id:int}`. This makes Starlette's int
converter reject "new" at path-matching stage, falling through to the web router.
For numeric IDs, both routers still define `GET /exams/{id}` — web router must be
registered before API router, OR API routes prefixed with `/api/`.
```

