import type { ReactNode } from "react";

export function AppShell({
  header,
  left,
  center,
  right
}: {
  header: ReactNode;
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
}) {
  return (
    <main className="flex min-h-screen flex-col p-5">
      {header}
      <div className="grid flex-1 grid-cols-[280px_minmax(360px,1fr)_320px] gap-4">
        <aside className="flex min-h-0 flex-col gap-3 rounded-xl border border-border bg-surface/40 p-3">{left}</aside>
        <section className="min-h-0">{center}</section>
        <aside className="flex min-h-0 flex-col gap-3 rounded-xl border border-border bg-surface/40 p-3">{right}</aside>
      </div>
    </main>
  );
}
