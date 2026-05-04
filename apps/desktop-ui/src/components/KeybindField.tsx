import { useEffect, useRef, useState } from "react";

import { cn } from "../lib/utils";
import { Keycap } from "./keycap";

type Props = {
  label: string;
  value: string;
  disabled?: boolean;
  reserved?: string[];
  onChange: (value: string) => void;
};

const keyNames: Record<string, string> = {
  " ": "Space",
  Escape: "Escape",
  Esc: "Escape",
  Control: "Ctrl",
  Alt: "Alt",
  Shift: "Shift",
  Meta: "Meta"
};

function normalizeKey(event: KeyboardEvent): string | null {
  if (event.key === "Escape") return "Escape";
  const key = keyNames[event.key] ?? (event.key.length === 1 ? event.key.toUpperCase() : event.key);
  if (["Ctrl", "Alt", "Shift", "Meta"].includes(key)) return null;
  const modifiers = [
    event.ctrlKey ? "Ctrl" : null,
    event.altKey ? "Alt" : null,
    event.shiftKey && key.length !== 1 ? "Shift" : null,
    event.metaKey ? "Meta" : null
  ].filter(Boolean);
  return [...modifiers, key].join("+");
}

export function KeybindField({ label, value, disabled, reserved = [], onChange }: Props) {
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!listening) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      event.preventDefault();
      event.stopPropagation();
      const next = normalizeKey(event);
      if (next === "Escape") {
        setListening(false);
        setError("");
        return;
      }
      if (!next) return;
      if (reserved.map((item) => item.toLowerCase()).includes(next.toLowerCase())) {
        setError(`${next} is already assigned.`);
        return;
      }
      onChange(next);
      setError("");
      setListening(false);
      buttonRef.current?.focus();
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [listening, onChange, reserved]);

  return (
    <div className="grid gap-1 text-xs text-muted-foreground">
      <span id={`${label.replace(/\s+/g, "-").toLowerCase()}-keybind-label`}>{label}</span>
      <button
        ref={buttonRef}
        type="button"
        aria-labelledby={`${label.replace(/\s+/g, "-").toLowerCase()}-keybind-label`}
        disabled={disabled}
        className={cn(
          "flex h-10 items-center justify-between rounded-lg border border-input bg-background px-3 text-left text-sm text-foreground outline-none transition focus:border-info/50 focus:ring-2 focus:ring-info/15 disabled:opacity-45",
          listening ? "border-info/60 bg-info/10 text-info ring-2 ring-info/20" : ""
        )}
        onClick={() => {
          if (!disabled) {
            setListening(true);
            setError("");
          }
        }}
      >
        <span>{listening ? "Press a key..." : "Click to change"}</span>
        <Keycap>{value}</Keycap>
      </button>
      {error ? <span className="text-danger">{error}</span> : null}
    </div>
  );
}
