import type { ReactNode } from "react";
import { Keycap } from "./keycap";

export function SplitHotkeyActionButton({
  tone,
  icon,
  label,
  hotkey,
  onAction,
  onHotkey,
  disabled = false
}: {
  tone: "danger" | "success";
  icon: ReactNode;
  label: string;
  hotkey: string;
  onAction: () => void;
  onHotkey: () => void;
  disabled?: boolean;
}) {
  const toneClass = tone === "danger"
    ? "border-danger/30 bg-danger/10 text-danger"
    : "border-success/30 bg-success/10 text-success";
  const separatorClass = tone === "danger" ? "border-danger/30" : "border-success/30";
  return (
    <div className={`inline-flex overflow-hidden rounded-lg border shadow-raycast ${toneClass}`}>
      <button type="button" className={`flex h-10 items-center gap-2 px-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-45 ${tone === "danger" ? "hover:bg-danger/20 active:bg-danger/25" : "hover:bg-success/20 active:bg-success/25"}`} onClick={onAction} disabled={disabled}>
        {icon}
        {label}
      </button>
      <button type="button" className={`border-l px-2 transition disabled:cursor-not-allowed disabled:opacity-45 ${separatorClass} ${tone === "danger" ? "hover:bg-danger/16 active:bg-danger/22" : "hover:bg-success/16 active:bg-success/22"}`} onClick={onHotkey} disabled={disabled}>
        <Keycap className="text-current">{hotkey}</Keycap>
      </button>
    </div>
  );
}
