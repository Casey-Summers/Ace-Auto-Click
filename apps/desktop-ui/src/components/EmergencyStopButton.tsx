import { AlertTriangle } from "lucide-react";

import { Keycap } from "./keycap";

export function EmergencyStopButton({
  hotkey,
  running,
  onStop,
  onKeybindClick
}: {
  hotkey: string;
  running: boolean;
  onStop: () => void;
  onKeybindClick: () => void;
}) {
  const keyAction = running ? onStop : onKeybindClick;
  return (
    <div className="inline-flex overflow-hidden rounded-lg border border-danger/30 bg-danger/10 text-danger shadow-raycast">
      <button
        type="button"
        className="flex h-10 items-center gap-2 px-3 text-sm font-semibold transition hover:bg-danger/15"
        onClick={onStop}
      >
        <AlertTriangle size={16} />
        Emergency stop
      </button>
      <button
        type="button"
        className="border-l border-danger/25 px-2 transition hover:bg-danger/15"
        onClick={keyAction}
        aria-label={running ? "Trigger emergency stop hotkey" : "Edit emergency stop hotkey"}
      >
        <Keycap className="text-danger">{hotkey}</Keycap>
      </button>
    </div>
  );
}
