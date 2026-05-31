# TASK-006: Commit data ingestion endpoint

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Student-facing endpoint that receives periodic commit snapshots from the client app.

**Ingest commit** `POST /commits`:
- Auth: student JWT required
- Input (JSON body):
  ```json
  {
    "commit_id": "string",
    "timestamp": "ISO8601",
    "exercise_id": "string",
    "file_name": "string",
    "lines_added": 0,
    "lines_removed": 0,
    "diff": "string (optional, raw git diff text)"
  }
  ```
- `student_id` extracted from JWT, not from body
- Output: 201 Created

Persist each record to `commits` table.

## Acceptance criteria
- [x] Valid student JWT + valid body → 201, record stored in DB
- [x] Missing/invalid JWT → 401
- [x] `student_id` always taken from token, never from request body
- [x] Bulk insert supported (array body) for batching multiple file changes per commit cycle
- [x] Duplicate `commit_id` + `file_name` handled gracefully (upsert or ignore)

## Notes
Blocked by TASK-004. Diff text storage is optional for MVP — can be enabled via config flag.
