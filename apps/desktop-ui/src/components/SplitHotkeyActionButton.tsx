import type { ReactNode } from "react";
import { Keycap } from "./keycap";

export function SplitHotkeyActionButton({
  tone,
  icon,
  label,
  hotkey,
  onAction,
  onHotkey
}: {
  tone: "danger" | "success";
  icon: ReactNode;
  label: string;
  hotkey: string;
  onAction: () => void;
  onHotkey: () => void;
}) {
  const toneClass = tone === "danger"
    ? "border-danger/30 bg-danger/10 text-danger"
    : "border-success/30 bg-success/10 text-success";
  const separatorClass = tone === "danger" ? "border-danger/30" : "border-success/30";
  return (
    <div className={`inline-flex overflow-hidden rounded-lg border shadow-raycast ${toneClass}`}>
      <button type="button" className={`flex h-10 items-center gap-2 px-3 text-sm font-semibold transition ${tone === "danger" ? "hover:bg-danger/20 active:bg-danger/25" : "hover:bg-success/20 active:bg-success/25"}`} onClick={onAction}>
        {icon}
        {label}
      </button>
      <button type="button" className={`border-l px-2 transition ${separatorClass} ${tone === "danger" ? "hover:bg-danger/16 active:bg-danger/22" : "hover:bg-success/16 active:bg-success/22"}`} onClick={onHotkey}>
        <Keycap className="text-current">{hotkey}</Keycap>
      </button>
    </div>
  );
}
