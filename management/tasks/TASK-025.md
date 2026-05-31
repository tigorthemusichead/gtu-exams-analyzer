# TASK-025: Move report.css <link> from scripts block to base template head block

status: done
created: 2026-05-27
updated: 2026-05-27

## Description
`report.html:71` places `<link rel="stylesheet" href="/static/css/report.css">` inside
`{% block scripts %}`, which renders at the bottom of `<body>`. Stylesheets loaded here
cause a flash of unstyled content (FOUC) — the page renders without report styles until
the parser reaches the bottom of the document.

Affected file:
- `server/app/web/templates/report.html:71`
- `server/app/web/templates/base.html` — needs a `{% block head %}` block if not present

## Acceptance criteria
- [ ] `report.css` is loaded in `<head>`, not at the bottom of `<body>`
- [ ] No FOUC on the report page
- [ ] Other pages unaffected

## Notes
Add `{% block head %}{% endblock %}` inside `<head>` in `base.html`. Override it in
`report.html` to inject the stylesheet. Remove the `<link>` from `{% block scripts %}`.
```

