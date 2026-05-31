# TASK-017: Teacher web dashboard (served by FastAPI)

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
Build teacher-facing web UI served directly by the existing FastAPI server. No separate app — FastAPI mounts Jinja2 templates + static files from `server/app/web/`.

**Stack:** Jinja2 templates + vanilla JS + Fetch API. No frontend build step. FastAPI `StaticFiles` mount for CSS/JS assets.

**Server-side additions:**
- Mount `StaticFiles` at `/static` → `server/app/web/static/`
- Mount `Jinja2Templates` from `server/app/web/templates/`
- Add `routers/web.py` with GET routes returning `TemplateResponse`
- Auth: JWT stored in `localStorage`, sent as `Authorization: Bearer` header on all Fetch calls. Login page sets token on success.

**Pages / flows:**

1. `GET /` → redirect to `/login` if no token
2. `GET /login` → email + password form → POST `/auth/login` → store JWT → redirect to `/dashboard`
3. `GET /dashboard` → list teacher's exams, two sections:
   - **Analyzed** (exams where `AnalysisResult` exists)
   - **Pending** (no result yet)
   - Button: "New exam"
4. `GET /exams/new` → form: name, group number, date, duration (minutes) → POST `/exams`
5. `GET /exams/{exam_id}` → exam detail: student list, commit count, "Run Analysis" button → POST `/analysis/{exam_id}/run` → poll for completion → redirect to report
6. `GET /exams/{exam_id}/report` → full report page (see TASK-018 for graph)

**Server changes needed:**
- `routers/web.py` — new router with above GET routes, included in `main.py`
- `dependencies.py` — optional: cookie-based token fallback for HTML pages (or keep header-only and handle in JS)
- `main.py` — mount `StaticFiles`, include web router

## Acceptance criteria
- [ ] `GET /login` renders login page; successful login stores JWT and redirects
- [ ] `GET /dashboard` shows exams split into analyzed / pending sections
- [ ] Teacher can create exam via form
- [ ] "Run Analysis" triggers analysis and shows loading state
- [ ] Report page loads after analysis completes
- [ ] Unauthenticated access to any page redirects to `/login`
- [ ] All API calls use JWT from localStorage

## Notes
No frontend framework or build tool needed. CDN links for minimal CSS (e.g., classless/Pico CSS).
Analysis trigger may be long-running — use polling: JS polls `GET /analysis/{exam_id}/status` every 2s until done.
