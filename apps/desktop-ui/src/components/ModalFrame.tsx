import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

import { Button } from "./ui/button";

export function ModalFrame({
  title,
  description,
  children,
  widthClass = "w-[min(720px,calc(100vw-48px))]",
  zClass = "z-50",
  onClose
}: {
  title: string;
  description?: string;
  children: ReactNode;
  widthClass?: string;
  zClass?: string;
  onClose: () => void;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    panelRef.current?.querySelector<HTMLElement>("button:not([disabled])")?.focus();
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          "button:not([disabled]), input:not([disabled]), select:not([disabled])"
        )
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className={`fixed inset-0 ${zClass} grid place-items-center bg-background/75 p-6 backdrop-blur-sm`}>
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`${widthClass} overflow-hidden rounded-xl border border-border bg-surface shadow-raycast`}
      >
        <header className="flex min-h-14 items-center justify-between border-b border-border px-5">
          <div>
            <h2 className="text-base font-semibold">{title}</h2>
            {description ? <p className="text-xs text-muted-foreground">{description}</p> : null}
          </div>
          <Button size="icon" variant="ghost" onClick={onClose} aria-label={`Close ${title}`}>
            <X size={18} />
          </Button>
        </header>
        {children}
      </div>
    </div>
  );
}
