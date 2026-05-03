import { cn } from "../lib/utils";

export function Keycap({ children, className }: { children: string; className?: string }) {
  return (
    <kbd
      className={cn(
        "inline-flex h-6 min-w-6 items-center justify-center rounded-md bg-gradient-to-b from-[#121212] to-[#0d0d0d] px-1.5 font-mono text-xs text-muted-foreground shadow-key",
        className
      )}
    >
      {children}
    </kbd>
  );
}
