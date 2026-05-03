import { RadioTower, Square } from "lucide-react";

import { CollapsibleSection } from "../../components/CollapsibleSection";
import { Keycap } from "../../components/keycap";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { stepIcon, stepTitle } from "../../lib/steps";
import type { ActionStep } from "../../lib/types";

export function SequenceBuilder({
  steps,
  loops,
  running,
  runHotkey,
  selectedId,
  onSelect,
  onLoopsChange,
  onRunToggle
}: {
  steps: ActionStep[];
  loops: number;
  running: boolean;
  runHotkey: string;
  selectedId: string;
  onSelect: (id: string) => void;
  onLoopsChange: (loops: number) => void;
  onRunToggle: () => void;
}) {
  return (
    <CollapsibleSection
      title="Sequence Builder"
      icon={<RadioTower size={16} />}
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
      <div className="grid gap-2">
        {steps.map((step, index) => (
          <button
            key={step.id}
            className={`flex items-center justify-between rounded-lg border p-3 text-left transition ${
              step.id === selectedId
                ? "border-info/45 bg-info/10"
                : "border-border bg-background/60 hover:bg-surface-strong"
            }`}
            onClick={() => onSelect(step.id)}
          >
            <div className="flex items-center gap-3">
              <Badge>{String(index + 1).padStart(2, "0")}</Badge>
              <span className="text-info">{stepIcon(step.type)}</span>
              <div>
                <div className="text-sm font-semibold">{stepTitle(step)}</div>
                <div className="font-mono text-xs text-muted-foreground">
                  repeats {step.repeats} / delay {step.interval_ms}ms
                </div>
              </div>
            </div>
            <Badge tone={step.enabled ? "success" : "neutral"}>{step.enabled ? "enabled" : "off"}</Badge>
          </button>
        ))}
      </div>
    </CollapsibleSection>
  );
}
