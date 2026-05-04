import type { ReactNode } from "react";
import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { cn } from "../lib/utils";
import { Button } from "./ui/button";

type Props = {
  title: string;
  icon?: ReactNode;
  defaultOpen?: boolean;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  density?: "default" | "compact";
};

export function CollapsibleSection({
  title,
  icon,
  defaultOpen = true,
  actions,
  children,
  className,
  density = "default"
}: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className={cn("rounded-xl border border-border bg-surface/75 shadow-raycast", className)}>
      <div className={cn("flex items-center justify-between gap-2 px-3", density === "compact" ? "min-h-9 py-1.5" : "min-h-11 py-2")}>
        <button
          type="button"
          className="flex min-w-0 flex-1 items-center gap-2 text-left text-sm font-semibold text-foreground"
          onClick={() => setOpen((value) => !value)}
        >
          <span className="text-muted-foreground">{open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}</span>
          {icon ? <span className="text-info">{icon}</span> : null}
          <span className="truncate">{title}</span>
        </button>
        <div className="flex items-center gap-2">{actions}</div>
      </div>
      {open ? <div className={cn("px-3", density === "compact" ? "pb-2" : "pb-3")}>{children}</div> : null}
    </section>
  );
}

export function SectionIconButton(props: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <Button variant="ghost" size="icon" className="h-7 w-7" {...props} />;
}
