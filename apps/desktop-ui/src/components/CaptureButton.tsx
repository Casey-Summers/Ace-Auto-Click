import type { ReactNode } from "react";

import { cn } from "../lib/utils";
import { Button } from "./ui/button";

type CaptureButtonProps = {
  idleText: string;
  pendingText?: string;
  pendingHint?: string;
  waiting?: boolean;
  disabled?: boolean;
  value?: string;
  valuePreview?: ReactNode;
  ariaLabel?: string;
  onCapture: () => void;
};

export function CaptureButton({
  idleText,
  pendingText = "Waiting for input",
  pendingHint,
  waiting,
  disabled,
  value,
  valuePreview,
  ariaLabel,
  onCapture
}: CaptureButtonProps) {
  const rightContent = waiting && pendingHint
    ? <span className="shrink-0 rounded border border-info/40 bg-info/10 px-2 py-0.5 text-xs font-semibold text-info">{pendingHint}</span>
    : valuePreview;

  return (
    <Button
      variant={waiting ? "success" : "default"}
      className={cn(
        "w-full justify-between overflow-hidden text-left",
        waiting ? "border-info/60 bg-info/10 text-info ring-2 ring-info/20 shadow-[inset_0_0_0_1px_hsl(var(--info)/0.25)]" : ""
      )}
      onClick={onCapture}
      disabled={disabled}
      aria-label={ariaLabel ?? `${waiting ? pendingText : idleText}${value ? `, current ${value}` : ""}`}
      aria-busy={waiting || undefined}
    >
      <span className="min-w-0 truncate">{waiting ? pendingText : idleText}</span>
      {rightContent ? <span className="ml-2 flex shrink-0 items-center">{rightContent}</span> : null}
    </Button>
  );
}
