import type { AppMode } from "../lib/types";
import { cn } from "../lib/utils";

export function ModeToggle({
  value,
  onChange
}: {
  value: AppMode;
  onChange: (mode: AppMode) => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-border bg-background/80 p-1">
      {(["normal", "advanced"] as AppMode[]).map((mode) => (
        <button
          key={mode}
          type="button"
          className={cn(
            "h-7 rounded-md px-3 text-xs font-semibold capitalize transition",
            value === mode
              ? "bg-surface-strong text-foreground shadow-raycast"
              : "text-muted-foreground hover:text-foreground"
          )}
          onClick={() => onChange(mode)}
        >
          {mode}
        </button>
      ))}
    </div>
  );
}
