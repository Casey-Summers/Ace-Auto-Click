import type { ReactNode } from "react";

export function AppShell({
  header,
  left,
  centerTop,
  center,
  right
}: {
  header: ReactNode;
  left: ReactNode;
  centerTop?: ReactNode;
  center: ReactNode;
  right: ReactNode;
}) {
  return (
    <main className="flex h-screen min-h-[720px] flex-col overflow-hidden p-5">
      {header}
      <div className="grid min-h-0 flex-1 grid-cols-[280px_minmax(360px,1fr)_320px] gap-4">
        <aside className="flex min-h-0 flex-col gap-3 overflow-hidden rounded-xl border border-border bg-surface/40 p-3">{left}</aside>
        <section className="flex min-h-0 flex-col gap-3 p-0">
          {centerTop}
          <div className="min-h-0 flex-1">{center}</div>
        </section>
        <aside className="flex min-h-0 flex-col gap-3 overflow-hidden rounded-xl border border-border bg-surface/40 p-3">{right}</aside>
      </div>
    </main>
  );
}
