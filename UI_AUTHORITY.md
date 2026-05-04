# Ace Auto Click UI Authority

This file is mandatory reading before UI work. It defines the order of
authority and the checks every UI change must pass.

## Authority Order

1. Latest explicit user request.
2. `UI_AUTHORITY.md`.
3. `DESIGN.md`.
4. Existing shadcn-style primitives in `apps/desktop-ui/src/components/ui`.
5. Current architecture: Tauri desktop, React UI, Python backend API.

## Required Checks

- No command palette, hidden command-first UX, or command-palette keybinds.
- Dark-first Raycast-inspired theme from `DESIGN.md`.
- Regular visible controls and keybind fields only.
- Every widget or section uses the reusable `CollapsibleSection`.
- Safety controls remain visible, semantically red, and never hidden behind settings.
- Settings are in-window, not a separate browser or OS window.
- No one-off component styling outside reusable UI primitives unless the file
  explains why the exception is necessary.
- Event logs are optional and controlled by settings.
- Normal mode is for beginner/simple current-mouse clicking.
- Advanced mode is for custom sequence automation.
