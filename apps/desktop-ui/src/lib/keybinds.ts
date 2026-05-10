const SPECIAL_KEY_LABELS: Record<string, string> = {
  " ": "SPACE",
  space: "SPACE",
  esc: "ESC",
  escape: "ESC",
  enter: "ENTER",
  tab: "TAB",
  backspace: "BACKSPACE",
  delete: "DELETE",
  home: "HOME",
  end: "END",
  page_up: "PAGE UP",
  pageup: "PAGE UP",
  page_down: "PAGE DOWN",
  pagedown: "PAGE DOWN",
  up: "UP",
  down: "DOWN",
  left: "LEFT",
  right: "RIGHT",
  btnm4: "BTNM 4",
  mouse4: "BTNM 4",
  "button.x1": "BTNM 4",
  btnm5: "BTNM 5",
  mouse5: "BTNM 5",
  "button.x2": "BTNM 5"
};

const MODIFIER_LABELS: Record<string, string> = {
  ctrl: "CTRL",
  control: "CTRL",
  alt: "ALT",
  shift: "SHIFT",
  meta: "META",
  cmd: "META"
};

function displayPart(part: string): string | null {
  const normalized = part.trim().toLowerCase().replace(/^key\./, "");
  if (!normalized || normalized === "?" || /[\u0000-\u001f\u007f]/.test(normalized)) return null;
  if (MODIFIER_LABELS[normalized]) return MODIFIER_LABELS[normalized];
  if (SPECIAL_KEY_LABELS[normalized]) return SPECIAL_KEY_LABELS[normalized];
  if (/^f(?:[1-9]|1\d|2[0-4])$/.test(normalized)) return normalized.toUpperCase();
  if (/^[a-z0-9]$/.test(normalized)) return normalized.toUpperCase();
  return null;
}

export function displayKeybind(value?: string | null): string {
  if (!value || !value.trim() || value.trim() === "?") return "Unset";
  const parts = value.split("+").map(displayPart);
  if (parts.length === 0 || parts.some((part) => part === null)) return "Unset";
  return parts.join(" + ");
}
