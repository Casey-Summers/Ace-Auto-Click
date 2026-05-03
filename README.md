# Ace Auto Click

Ace Auto Click is a dark-first desktop popup application for precise mouse,
keyboard, pixel, and sequence workflows. Tauri owns the application window,
React renders the interface, and Python owns all OS-level automation behind a
local API.

## Architecture

- `app.py` is the root launcher for the desktop app, API debug server, and
  runtime checks.
- `src/ace_auto_click/api` exposes the local typed API boundary.
- `src/ace_auto_click/automation` owns mouse, keyboard, pixel, and recorder
  behavior.
- `src/ace_auto_click/runtime` owns process orchestration.
- `src/ace_auto_click/storage` owns settings and macro persistence.
- `apps/desktop-ui` contains the Tauri/React frontend.
- `DESIGN.md` is the UI pillar and theme source of truth.

## Install Backend

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Install Frontend

```powershell
npm.cmd --prefix apps/desktop-ui install
```

Rust/Cargo are required to build the Tauri desktop shell. During development,
`python app.py desktop` falls back to a native Python WebView popup if Cargo is
not available.

## Run

Run the desktop app in development mode. This opens the Tauri popup application
when Cargo is available, or a native WebView popup fallback when it is not. It
does not use the browser as the app surface:

```powershell
python app.py desktop
```

Run the Python API by itself for backend/debug work:

```powershell
python app.py api
```

Verify imports, settings migration, and API app creation:

```powershell
python app.py check
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
