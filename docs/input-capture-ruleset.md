# Input Capture Ruleset

This ruleset defines required behavior for all action capture buttons and session-based capture flows.

## 1) Pending Stage Is Mandatory
- Pressing a capture button must always enter a visible pending/waiting state.
- During pending, no value may be committed until a **new** user input occurs.

## 2) Ignore Activation Input
- Capture must ignore the interaction used to activate capture (mouse click / key press).
- Implement with an arming delay and/or equivalent event-gating so capture accepts only post-activation input.

## 3) Reusable Capture Framework
- All captures must use the shared capture-session lifecycle:
  1. start session
  2. set pending state
  3. poll status
  4. resolve complete/cancel/fail/timeout
  5. clear pending state and session id
- New capture types must extend this framework, not implement bespoke one-off flows.

## 4) Reusable Capture Button UI
- Use shared capture row/button rendering for all action capture controls.
- Waiting and idle labels must be consistent across capture types.

## 5) Key Capture Semantics
- Record first valid key input only.
- Modifiers are optional but supported (e.g. `ctrl+shift+a`).
- Stop capture immediately after the first valid chord or key.

## 6) Settings Panel Ordering
- Interactable capture controls must appear at the top of the right-hand Action Settings panel by default.
- Non-interactive fields and generic timing fields appear below capture controls.

## 7) Cancellation and Safety
- `Esc` must cancel active capture sessions.
- Session state must be cleaned up on completion, cancellation, error, and context invalidation.

