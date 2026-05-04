import * as React from "react";

import { cn } from "../../lib/utils";

type Tone = "neutral" | "info" | "success" | "warning" | "danger";

const tones: Record<Tone, string> = {
  neutral: "bg-surface-strong text-muted-foreground ring-white/10",
  info: "bg-info/15 text-info ring-info/25",
  success: "bg-success/15 text-success ring-success/25",
  warning: "bg-warning/15 text-warning ring-warning/25",
  danger: "bg-danger/15 text-danger ring-danger/25"
};

export function Badge({
  tone = "neutral",
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center rounded-md px-2 font-mono text-xs font-medium ring-1",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}
