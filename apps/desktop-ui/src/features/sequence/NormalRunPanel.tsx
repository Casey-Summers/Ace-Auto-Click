import { RadioTower, Square } from "lucide-react";

import { CollapsibleSection } from "../../components/CollapsibleSection";
import { Keycap } from "../../components/keycap";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import type { NormalProfileSettings } from "../../lib/types";

export function NormalRunPanel({
  normal,
  loops,
  running,
  runHotkey,
  onLoopsChange,
  onRunToggle
}: {
  normal: NormalProfileSettings;
  loops: number;
  running: boolean;
  runHotkey: string;
  onLoopsChange: (loops: number) => void;
  onRunToggle: () => void;
}) {
  return (
    <CollapsibleSection
      title="Normal Mode"
      actions={
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            Loops
            <Input className="h-8 w-20" type="number" min={0} value={loops} onChange={(event) => onLoopsChange(Number(event.target.value))} />
          </label>
          <Button variant={running ? "danger" : "success"} onClick={onRunToggle}>
            {running ? <Square size={16} /> : <RadioTower size={16} />}
            {running ? "Stop sequence" : "Run sequence"}
            <Keycap>{runHotkey}</Keycap>
          </Button>
        </div>
      }
    >
      <div className="grid gap-3 rounded-lg border border-border bg-background/60 p-4">
        <div>
          <h2 className="text-base font-semibold">Click at current mouse position</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Runs a simple profile for quick repeated clicking without building a custom sequence.
          </p>
        </div>
        <div className="grid grid-cols-4 gap-2 text-sm">
          <div className="rounded-lg bg-surface-strong p-3">
            <div className="text-xs text-muted-foreground">Button</div>
            <div className="font-mono">{normal.button}</div>
          </div>
          <div className="rounded-lg bg-surface-strong p-3">
            <div className="text-xs text-muted-foreground">Pre-delay</div>
            <div className="font-mono">{normal.interval_ms}ms</div>
          </div>
          <div className="rounded-lg bg-surface-strong p-3">
            <div className="text-xs text-muted-foreground">Randomness</div>
            <div className="font-mono">{normal.position_random_px}px</div>
          </div>
          <div className="rounded-lg bg-surface-strong p-3">
            <div className="text-xs text-muted-foreground">Clicks</div>
            <div className="font-mono">{normal.double_click ? 2 : normal.clicks_per_cycle}</div>
          </div>
        </div>
      </div>
    </CollapsibleSection>
  );
}
