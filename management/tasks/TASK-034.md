# TASK-034: Bundle client for macOS DMG

status: done
created: 2026-06-07
updated: 2026-06-07

## Description

Bundle the PyQt6 Python client into a macOS `.dmg` installer using PyInstaller + create-dmg.

### Context
- PyQt6 app, Python 3.11+, entry point: `app.main:main`
- Dependencies: PyQt6, httpx, gitpython, python-dotenv
- Resources: `app/resources/logo.png` (loaded via `__file__`-relative path)
- Config via `.env`: `SERVER_URL`, `WATCHER_INTERVAL_SECONDS`
- Build system: hatchling (no existing bundle config)

### Approach
PyInstaller (battle-tested for PyQt6) + `create-dmg` (brew) → signed `.dmg`.

## Steps

### 1. Add PyInstaller dev dependency
Add `pyinstaller` to `pyproject.toml` `[project.optional-dependencies]` dev section.
```
pip install pyinstaller
```

### 2. Decide SERVER_URL config strategy
Bundled app won't ship `.env`. Options:
- **A** — Bake prod `SERVER_URL` into the spec/build env (simple, inflexible)
- **B** — Ship no default; user sets env var before launching (clean, needs docs)
- **C** — Prompt user for `SERVER_URL` on first launch and persist to `~/.cheat-buster.env`

`python-dotenv` already falls back to env vars if `.env` absent — acceptable for B.

Go with option A

### 3. Create PyInstaller .spec file
`client/cheat-buster.spec`:
- Entry point: `app/main.py`
- Include data: `app/resources/logo.png` → `app/resources/`
- Hidden imports for PyQt6 plugins (`PyQt6.QtSvg`, `PyQt6.QtWidgets`, etc.)
- Windowed mode (no terminal)
- Icon: `app/resources/logo.icns` (see step 4)
- One-dir build (better for macOS `.app` signing vs one-file)

### 4. Convert logo.png → logo.icns
macOS `.app` requires `.icns` icon. Use `sips` + `iconutil` (ship with macOS):
```bash
mkdir logo.iconset
sips -z 16 16     app/resources/logo.png --out logo.iconset/icon_16x16.png
sips -z 32 32     app/resources/logo.png --out logo.iconset/icon_16x16@2x.png
sips -z 32 32     app/resources/logo.png --out logo.iconset/icon_32x32.png
sips -z 64 64     app/resources/logo.png --out logo.iconset/icon_32x32@2x.png
sips -z 128 128   app/resources/logo.png --out logo.iconset/icon_128x128.png
sips -z 256 256   app/resources/logo.png --out logo.iconset/icon_128x128@2x.png
sips -z 256 256   app/resources/logo.png --out logo.iconset/icon_256x256.png
sips -z 512 512   app/resources/logo.png --out logo.iconset/icon_256x256@2x.png
sips -z 512 512   app/resources/logo.png --out logo.iconset/icon_512x512.png
sips -z 1024 1024 app/resources/logo.png --out logo.iconset/icon_512x512@2x.png
iconutil -c icns logo.iconset -o app/resources/logo.icns
rm -rf logo.iconset
```

### 5. Build .app with PyInstaller
```bash
cd client
pyinstaller cheat-buster.spec
```
Output: `client/dist/cheat-buster.app`

### 6. Add git availability check to app startup
In `app/main.py`, before creating `QApplication`, check for `git` binary:
```python
import shutil
import sys

def check_git():
    if shutil.which("git") is None:
        # QApplication needed for dialog — create minimal one
        from PyQt6.QtWidgets import QApplication, QMessageBox
        _app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "Git Not Found",
            "Git is required but not installed.\n\n"
            "Install via Terminal:\n"
            "    xcode-select --install\n\n"
            "Or download from: https://git-scm.com",
        )
        sys.exit(1)
```
Call `check_git()` at top of `main()` before anything else. On macOS, `xcode-select --install` covers most users. Clean macOS without CLT will also show OS-level git install prompt on first `git` invocation — double safety net.

### 7. Smoke-test .app
```bash
open client/dist/cheat-buster.app
```
Verify: launches without terminal, all windows work, git watcher runs, API calls succeed.

### 8. Package into .dmg with create-dmg
```bash
brew install create-dmg

create-dmg \
  --volname "Cheat Buster" \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "cheat-buster.app" 150 200 \
  --app-drop-link 450 200 \
  client/dist/Cheat-Buster.dmg \
  client/dist/cheat-buster.app
```

### 9. (Optional) Code signing + notarization
Required for distribution outside internal network (Gatekeeper bypass):
```bash
codesign --deep --force --sign "Developer ID Application: <name>" \
  client/dist/cheat-buster.app
xcrun notarytool submit client/dist/Cheat-Buster.dmg \
  --apple-id <email> --team-id <team> --wait
xcrun stapler staple client/dist/Cheat-Buster.dmg
```
Skip if distributing internally (e.g., via USB or local network).

Here use Ad-hoc Signing

### 10. Add Makefile targets
```makefile
build-mac-app:
	cd client && pyinstaller cheat-buster.spec

build-mac-dmg: build-mac-app
	create-dmg \
	  --volname "Cheat Buster" \
	  --window-size 600 400 \
	  --icon-size 100 \
	  --icon "cheat-buster.app" 150 200 \
	  --app-drop-link 450 200 \
	  client/dist/Cheat-Buster.dmg \
	  client/dist/cheat-buster.app
```

## Acceptance criteria
- [ ] `pyinstaller` added to dev dependencies
- [ ] `app/resources/logo.icns` generated and committed
- [ ] `client/cheat-buster.spec` created and working
- [ ] `client/dist/cheat-buster.app` launches cleanly (no terminal, correct icon)
- [ ] `client/dist/Cheat-Buster.dmg` mounts, drag-to-Applications works
- [ ] Git check added to `main()` — shows error dialog if git absent
- [ ] App connects to server via configured `SERVER_URL`
- [ ] Makefile targets `build-mac-app` and `build-mac-dmg` added

## Notes
- PyInstaller one-dir (not one-file) preferred on macOS — one-file extracts to temp dir on launch, breaks relative paths and slows startup
- Git check uses `shutil.which("git")` — runs before gitpython touches anything, so failure is clean
- `gitpython` may need `GIT_PYTHON_GIT_EXECUTABLE` env var set to `shutil.which("git")` result in bundle to avoid PATH issues
- Test on clean macOS user account (no Python installed) to catch missing deps
