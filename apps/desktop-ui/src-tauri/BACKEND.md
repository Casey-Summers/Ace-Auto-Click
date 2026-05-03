# Python Backend Runtime

Ace Auto Click is designed to run as a Tauri desktop popup. During development,
the root launcher starts the Python API first and then opens the Tauri window:

```powershell
python app.py desktop
```

For packaged builds, the Python API should be bundled as a sidecar executable
that exposes `http://127.0.0.1:8765`. The React frontend already targets that
local API by default through `src/lib/api.ts`.

The backend process must be started before the window becomes interactive and
terminated when the Tauri application exits.

During development, `python app.py desktop` prefers Tauri when Cargo is on PATH.
If Cargo is unavailable, it starts the same Python API and Vite frontend inside a
native Python WebView window so the app still runs outside the browser.
