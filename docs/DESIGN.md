# Ace Auto Click UI Pillar

Ace Auto Click uses a Raycast-inspired design pillar for a dark-first,
keyboard-centric desktop utility. This file is the source of truth for UI
decisions across the React/Tauri frontend.

## Theme

- Product name: Ace Auto Click
- Default mode: dark
- Future mode: light tokens may exist, but dark remains the primary product
  experience until light mode is explicitly enabled.
- Mood: precise, fast, calm, and utility-focused.
- Layout density: compact enough for repeated workflows, with clear separation
  between active controls, sequence structure, logs, and safety state.

## Color Tokens

- `--background`: `#07080a`, near-black blue.
- `--surface`: `#101111`, primary elevated surface.
- `--surface-strong`: `#1b1c1e`, selected cards, badges, command rows.
- `--border`: `rgba(255,255,255,0.08)`, default containment.
- `--border-strong`: `rgba(255,255,255,0.14)`, focused/selected containment.
- `--text`: `#f9f9f9`, high-emphasis text.
- `--text-muted`: `#cecece`, body/supporting text.
- `--text-subtle`: `#9c9c9d`, metadata and secondary labels.
- `--disabled`: `#6a6b6c`, disabled text and inactive controls.
- `--accent`: `#ff6363`, critical/action accent used sparingly.
- `--info`: `#55b3ff`, focus, selected rows, and active guidance.
- `--success`: `#5fc992`, running/ready confirmations.
- `--warning`: `#ffbc33`, attention states.
- `--danger`: `#ff6363`, destructive controls and emergency stop.

## Typography

- Primary: Inter, with system sans-serif fallback.
- Mono: Geist Mono, ui-monospace fallback.
- Use medium weights for core UI text on dark surfaces.
- Avoid oversized marketing typography; this is a work tool, not a landing page.
- Use mono text for hotkeys, coordinates, RGB values, and event logs.

## Components

- Buttons use dark surfaces, subtle inset highlights, and restrained opacity
  transitions.
- Destructive actions use Raycast red only where the action is genuinely
  destructive or safety-related.
- Cards use dark surfaces with fine borders, not heavy shadows.
- Inputs use `#07080a` backgrounds, 8px radius, muted placeholders, and blue
  focus rings.
- Keyboard shortcuts render as small key caps with gradient depth.
- Command palette is the primary navigation accelerator.
- Status badges use semantic color: blue for info, green for running/success,
  yellow for warning, red for danger/error.

## Layout Rules

- Base spacing unit: 8px.
- Main app frame: sidebar/actions on the left, active sequence/work area in the
  center, runtime/status inspector on the right when space allows.
- Touch/click targets: minimum 32px for compact controls, 40px for primary
  controls.
- Cards and panels use 8px to 12px radius.
- Avoid nested cards; use panels for major work regions and cards for repeated
  items such as sequence steps.

## Do

- Keep accent colors purposeful and semantic.
- Make keyboard and command workflows first-class.
- Keep safety state visible at all times.
- Preserve dense, scannable control surfaces for advanced automation.
- Prepare tokens so light mode can be added later without rewriting components.

## Do Not

- Use bright color as decoration.
- Use pure black for every surface.
- Hide emergency stop or running state behind a modal or secondary page.
- Add marketing hero sections or explanatory onboarding as the primary screen.
- Create one-off component styles outside the shared UI component layer.
