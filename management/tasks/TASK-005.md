# TASK-005: Exam management endpoints

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Teacher-only endpoints for creating and listing exams.

**Create exam** `POST /exams`:
- Input: name, group_number, date, duration_minutes
- Output: created exam with id

**List exams** `GET /exams`:
- Returns exams created by authenticated teacher
- Includes flag: `has_report` (bool)

**Get exam** `GET /exams/{exam_id}`:
- Returns exam details + participant count

## Acceptance criteria
- [ ] Teacher can create exam, receives exam_id
- [ ] `GET /exams` returns only exams belonging to that teacher
- [ ] `has_report` flag correctly reflects whether report exists
- [ ] Student token returns 403 on all exam management routes
- [ ] Exam model persisted to DB via SQLAlchemy

## Notes
Blocked by TASK-004.
