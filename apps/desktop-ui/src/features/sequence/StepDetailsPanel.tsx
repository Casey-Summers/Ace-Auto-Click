import { Crosshair } from "lucide-react";

import { CollapsibleSection } from "../../components/CollapsibleSection";
import { Button } from "../../components/ui/button";
import { Input, Select } from "../../components/ui/input";
import type { ActionStep, NormalProfileSettings } from "../../lib/types";

export function NormalDetailsPanel({
  normal,
  onChange
}: {
  normal: NormalProfileSettings;
  onChange: (patch: Partial<NormalProfileSettings>) => void;
}) {
  return (
    <CollapsibleSection title="Normal Profile" icon={<Crosshair size={16} />}>
      <div className="grid gap-3">
        <label className="flex items-center justify-between rounded-lg bg-background/70 p-2 text-sm">
          Click at current mouse
          <input type="checkbox" checked={normal.use_current_mouse} onChange={(event) => onChange({ use_current_mouse: event.target.checked })} />
        </label>
        <Select value={normal.button} onChange={(event) => onChange({ button: event.target.value as "left" | "right" | "middle" })}>
          <option value="left">left</option>
          <option value="right">right</option>
          <option value="middle">middle</option>
        </Select>
        <Input type="number" value={normal.interval_ms} onChange={(event) => onChange({ interval_ms: Number(event.target.value) })} />
        <Input type="number" value={normal.interval_random_ms} onChange={(event) => onChange({ interval_random_ms: Number(event.target.value) })} />
        <Input type="number" value={normal.position_random_px} onChange={(event) => onChange({ position_random_px: Number(event.target.value) })} />
        <Input type="number" value={normal.clicks_per_cycle} onChange={(event) => onChange({ clicks_per_cycle: Number(event.target.value) })} />
        <label className="flex items-center justify-between rounded-lg bg-background/70 p-2 text-sm">
          Double click
          <input type="checkbox" checked={normal.double_click} onChange={(event) => onChange({ double_click: event.target.checked })} />
        </label>
      </div>
    </CollapsibleSection>
  );
}

export function StepDetailsPanel({
  step,
  onChange,
  onSamplePixel
}: {
  step?: ActionStep;
  onChange: (patch: Partial<ActionStep>) => void;
  onSamplePixel: () => void;
}) {
  if (!step) {
    return (
      <CollapsibleSection title="Selected Step" defaultOpen>
        <p className="text-sm text-muted-foreground">Select a step to edit details.</p>
      </CollapsibleSection>
    );
  }

  return (
    <CollapsibleSection title="Selected Step" icon={<Crosshair size={16} />}>
      <div className="grid gap-3">
        <Input type="number" value={step.repeats} onChange={(event) => onChange({ repeats: Number(event.target.value) })} />
        <Input type="number" value={step.interval_ms} onChange={(event) => onChange({ interval_ms: Number(event.target.value) })} />
        <Input type="number" value={step.randomness_ms} onChange={(event) => onChange({ randomness_ms: Number(event.target.value) })} />

        {step.type === "click" ? (
          <>
            <div className="grid grid-cols-2 gap-2">
              <Input type="number" value={step.x} onChange={(event) => onChange({ x: Number(event.target.value) })} />
              <Input type="number" value={step.y} onChange={(event) => onChange({ y: Number(event.target.value) })} />
            </div>
            <Select value={step.button} onChange={(event) => onChange({ button: event.target.value as "left" | "right" | "middle" })}>
              <option value="left">left</option>
              <option value="right">right</option>
              <option value="middle">middle</option>
            </Select>
            <Input type="number" value={step.clicks} onChange={(event) => onChange({ clicks: Number(event.target.value) })} />
            <Input type="number" value={step.random_offset} onChange={(event) => onChange({ random_offset: Number(event.target.value) })} />
          </>
        ) : null}

        {step.type === "wait" ? (
          <>
            <Input type="number" value={step.ms} onChange={(event) => onChange({ ms: Number(event.target.value) })} />
            <Input type="number" value={step.random_ms} onChange={(event) => onChange({ random_ms: Number(event.target.value) })} />
          </>
        ) : null}

        {step.type === "pixel_check" ? (
          <>
            <div className="flex items-center gap-2">
              <div
                className="h-8 w-12 rounded-md border border-border"
                style={{ backgroundColor: `rgb(${step.expected_rgb.join(",")})` }}
              />
              <span className="font-mono text-xs text-muted-foreground">{step.expected_rgb.join(", ")}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Input type="number" value={step.x} onChange={(event) => onChange({ x: Number(event.target.value) })} />
              <Input type="number" value={step.y} onChange={(event) => onChange({ y: Number(event.target.value) })} />
            </div>
            <Input type="number" value={step.tolerance} onChange={(event) => onChange({ tolerance: Number(event.target.value) })} />
            <Select value={step.mode} onChange={(event) => onChange({ mode: event.target.value as "wait_until_match" | "stop_if_mismatch" | "skip_if_mismatch" })}>
              <option value="wait_until_match">wait until match</option>
              <option value="stop_if_mismatch">stop if mismatch</option>
              <option value="skip_if_mismatch">skip if mismatch</option>
            </Select>
            <Button onClick={onSamplePixel}>Sample pixel</Button>
          </>
        ) : null}

        {step.type === "key_tap" ? (
          <Input value={step.key} onChange={(event) => onChange({ key: event.target.value })} />
        ) : null}
      </div>
    </CollapsibleSection>
  );
}
