# Ace Auto Click

Ace Auto Click is a dark-first desktop automation workspace for precise mouse,
keyboard, pixel, and sequence workflows. The app is being migrated from the
legacy `customtkinter` UI to a Tauri + React + TypeScript frontend backed by the
existing Python automation engine.

## Architecture

- `ace_auto_click_api.py` exposes the local typed API boundary.
- `click_engine.py`, `actions.py`, `pixel_match.py`, and `recorder.py` remain
  the automation backend.
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

Rust/Cargo are required to run or build the Tauri desktop shell.

## Run

Start the Python API:

```powershell
python main.py api
```

Start the React frontend during development:

```powershell
npm.cmd --prefix apps/desktop-ui run dev
```

Run the Tauri shell after installing Rust/Cargo:

```powershell
python main.py desktop
```

## Safety

- `F12` is reserved as the emergency stop hotkey in the API contract.
- PyAutoGUI's screen-corner failsafe remains enabled.
- This tool is intended for personal productivity, accessibility, and testing
  your own apps.
