# TASK-012: Directory picker + git init

status: done
created: 2026-05-11
updated: 2026-05-11

## Description
Screen where student selects working directory. App initializes git repo in that directory.

Behavior:
1. Show native directory picker (`QFileDialog.getExistingDirectory`)
2. Selected path displayed in UI
3. On confirm: check if `.git` exists — if not, run `git init` via `gitpython`
4. Set git user.name and user.email from student auth data (so commits are attributed)
5. Store repo path in app state, navigate to active session view

## Acceptance criteria
- [ ] Native directory picker opens on button click
- [ ] `git init` runs if no existing repo detected
- [ ] Existing git repo in directory is reused without re-init
- [ ] Git user identity set to student email + name
- [ ] Selected path shown in UI before confirmation

## Notes
Blocked by TASK-011.
