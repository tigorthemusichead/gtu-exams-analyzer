# TASK-014: Session end + graceful shutdown

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Handle student ending exam session cleanly.

Behaviors:
1. **Explicit end**: "Finish Exam" button → confirmation dialog → final git commit + POST → clear JWT from memory → return to auth screen
2. **Window close (X button)**: intercept `closeEvent` → same cleanup as explicit end
3. **Unexpected crash / process kill**: git state left as-is (acceptable — server has last-known-good data)

Final commit cycle on session end:
- Force one last `git add . && git commit` even if N seconds haven't elapsed
- Send all pending file changes to server
- Call `POST /session/end` if such endpoint exists (optional)

## Acceptance criteria
- [x] "Finish Exam" button triggers confirmation dialog before ending
- [x] Final commit + POST fires before app closes
- [x] JWT cleared from memory on session end
- [x] App returns to auth screen after explicit end (does not quit entirely)
- [x] Window close (X) intercepted and shows same confirmation dialog
- [x] No crash if server unreachable during shutdown (logs error, proceeds)

## Notes
Blocked by TASK-013.
