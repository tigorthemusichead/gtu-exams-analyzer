# TASK-011: Auth + exam selection UI

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Student-facing authentication and exam selection screens.

**Auth screen**:
- Fields: university email, group number, exam ID (or dropdown if exams fetched from server), variant number
- "Start Exam" button → calls `POST /auth/student`, stores JWT in memory
- Error display for invalid credentials / server unreachable

**Exam selection** (can be combined with auth or separate step):
- After auth, show selected exam details for confirmation
- "Confirm & Continue" → navigate to directory picker (TASK-012)

## Acceptance criteria
- [ ] All required fields present and validated (non-empty, email format)
- [ ] Successful auth stores JWT and transitions to next screen
- [ ] Auth failure shows human-readable error message
- [ ] No JWT stored to disk (memory only)

## Notes
Blocked by TASK-010. Requires server TASK-004 to be running for end-to-end test.
