# Ace Auto Click

Ace Auto Click is a dark-first desktop popup application for precise mouse,
keyboard, pixel, and sequence workflows. Tauri owns the native application
window, React renders inside Tauri's desktop WebView, and Python owns all
OS-level automation behind a local API.

## Architecture

- `app.py` is the root launcher for the desktop app, API debug server, and
  runtime checks.
- `src/ace_auto_click/api` exposes the local typed API boundary.
- `src/ace_auto_click/automation` owns mouse, keyboard, pixel, and recorder
  behavior.
- `src/ace_auto_click/runtime` owns process orchestration.
- `src/ace_auto_click/storage` owns settings and macro persistence.
- `apps/desktop-ui` contains the Tauri/React frontend.
- `docs/DESIGN.md` is the UI pillar and theme source of truth.
- `docs/UI_AUTHORITY.md` defines UI authority and implementation rules.

## Install Backend

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

For development and tests, install the dev requirements:

```powershell
python -m pip install -r requirements-dev.txt
```

## Install Frontend

```powershell
npm.cmd --prefix apps/desktop-ui install
```

Rust/Cargo are required to run and build the Tauri desktop shell:

```powershell
winget install Rustlang.Rustup
```

Restart your terminal after installing Rust so `cargo` is available on PATH.

## Run

Run the desktop app in development mode. This opens the Tauri popup
application, not a browser tab:

```powershell
python app.py desktop
```

Run the Python API by itself for backend/debug work:

```powershell
python app.py api
```

Verify imports, settings migration, API app creation, Node/npm availability,
and Cargo availability:

```powershell
python app.py check
```

Run the full dependency doctor. Add `--fix` to install safe project
dependencies and regenerate missing Tauri icons:

```powershell
python app.py doctor
python app.py doctor --fix
python app.py doctor --dev --build-check
```

Vite remains an internal development server for Tauri. Do not use the browser
tab as the user-facing app surface.

## Safety

- `F12` is reserved as the emergency stop hotkey in the API contract.
- PyAutoGUI's screen-corner failsafe remains enabled.
- This tool is intended for personal productivity, accessibility, and testing
  your own apps.

## Tests

```powershell
python -m pytest
npm.cmd --prefix apps/desktop-ui run test
npm.cmd --prefix apps/desktop-ui run build
```

## Dependency Notes

- Python dependencies in `requirements.txt` are runtime backend dependencies.
- Test-only packages live in `requirements-dev.txt`.
- Tauri requires Rust/Cargo because it compiles the native desktop shell.
- Vite is development tooling for Tauri's React UI; it is not supported as the
  user-facing app surface.
- Dependency doctor logs are written to `logs/dependency-doctor`.
