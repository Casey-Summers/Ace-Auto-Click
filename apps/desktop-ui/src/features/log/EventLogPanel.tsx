import { CollapsibleSection } from "../../components/CollapsibleSection";

export function EventLogPanel({ log }: { log: string[] }) {
  return (
    <CollapsibleSection title="Event Log" defaultOpen>
      <div className="grid max-h-48 gap-2 overflow-auto font-mono text-xs text-muted-foreground">
        {log.slice(0, 12).map((entry, index) => (
          <div key={`${entry}-${index}`} className="rounded-md bg-background/70 p-2">
            {entry}
          </div>
        ))}
      </div>
    </CollapsibleSection>
  );
}
