# TASK-024: Add server-side auth to web dashboard routes

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
All web HTML routes (`/dashboard`, `/exams/new`, `/exams/{id}`, `/exams/{id}/report`)
have no server-side authentication. Access is protected only by a client-side
localStorage check in `app.js`, which is trivially bypassed (JS disabled, curl, etc.).

Any unauthenticated user can load these pages directly and see exam data.

Affected file:
- `server/app/routers/web.py` — all route handlers

## Acceptance criteria
- [ ] Unauthenticated GET to `/dashboard` redirects to `/login` (not renders the page)
- [ ] Unauthenticated GET to `/exams/new` redirects to `/login`
- [ ] Unauthenticated GET to `/exams/{id}` redirects to `/login`
- [ ] Unauthenticated GET to `/exams/{id}/report` redirects to `/login`
- [ ] Authenticated requests continue to work normally

## Notes
Web routes use session cookies or tokens differently from the API (Bearer header).
Options:
1. Store JWT in a cookie on login, validate cookie in web route deps.
2. Use a separate session mechanism (e.g. `itsdangerous` signed cookie).
3. Add a `require_teacher_cookie` dependency that redirects (302) instead of raising 401.
```

