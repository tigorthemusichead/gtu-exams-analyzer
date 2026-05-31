# TASK-004: Auth endpoints (JWT, student + teacher)

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Implement authentication endpoints for both roles.

**Student auth** `POST /auth/student`:
- Input: email, group_number, exam_id, variant
- Output: JWT (payload: user_id, exam_id, role="student", exp = now + exam_duration)

**Teacher auth** `POST /auth/teacher`:
- Input: email, password
- Output: JWT (payload: user_id, role="teacher", exp = now + 8h)

JWT middleware: FastAPI dependency that validates token and injects current user into route.

## Acceptance criteria
- [ ] `POST /auth/student` returns valid JWT for known student
- [ ] `POST /auth/teacher` returns valid JWT for correct credentials
- [ ] Invalid credentials return 401
- [ ] JWT dependency rejects expired/malformed tokens
- [ ] Role-based access: student routes reject teacher token and vice versa

## Notes
Blocked by TASK-003. Store teacher credentials hashed (bcrypt via passlib).
