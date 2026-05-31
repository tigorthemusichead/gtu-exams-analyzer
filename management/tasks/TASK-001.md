# TASK-001: Design database schema (SQLite)

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Design full SQLite schema for cheat-buster system.

Entities from project spec:
- Users (students + teachers, role-based)
- Exams (created by teacher: name, group, date)
- Exam sessions (student participates in exam, variant)
- Commits (per-file snapshots sent from student client: commit_id, student_id, timestamp, exercise_id, lines_added, lines_removed, file_name)
- Analysis results (per-exam, per-student normality metrics)
- Similarity pairs (student A ↔ student B, metric M, per-exam)

Consider:
- JWT auth: server needs to validate student/teacher identity — store hashed passwords for teachers, email-only for students
- Exam duration types (1h / 2h) affect JWT TTL — store exam_type or duration_minutes on exam
- Commit data is append-only, high volume — index on (exam_id, student_id, timestamp)
- Analysis is triggered post-exam, results cached — separate tables for analysis output

## Acceptance criteria
- [x] ERD or schema SQL covering all entities
- [x] Foreign keys and indexes defined
- [x] Migration file (SQLite `CREATE TABLE` statements)
- [x] Short rationale for non-obvious design choices

## Deliverable
`db/migrations/001_initial_schema.sql`

## Design rationale

**`users` single table for both roles** — role column + CHECK constraint. Avoids join for auth. `password_hash` nullable: NULL = student (email-only), bcrypt string = teacher.

**`exams.duration_minutes`** — server reads this after teacher creates exam; JWT exp = `issued_at + duration_minutes * 60`. Supports any duration, not just 60/120.

**`exam_sessions.ended_at NULL`** — active session detection without extra status enum. Server sets it when student ends session or JWT expires.

**`commits` append-only** — no UPDATE path. `UNIQUE(commit_id, student_id, file_name)` idempotent: client can retry on network error without duplication. `exam_id` added server-side from JWT claims (not trusted from client). Composite index `(exam_id, student_id, timestamp)` covers primary analysis scan.

**`analysis_results` UNIQUE(exam_id, student_id)** — `INSERT OR REPLACE` lets teacher re-run analysis and overwrite stale cache without manual delete.

**`similarity_pairs` CHECK(student_a_id < student_b_id)** — canonical ordering eliminates duplicate (A,B)/(B,A) rows. Halves storage; all queries use `WHERE student_a_id = X OR student_b_id = X`.

**`details` / `suspicious_flags` as JSON TEXT** — avoids schema churn as metric set evolves. SQLite `json_extract()` available for filtering if needed later.

**`PRAGMA journal_mode = WAL`** — in migration file so it activates on first open. Improves concurrent read throughput during high-volume commit ingestion.

## Notes
