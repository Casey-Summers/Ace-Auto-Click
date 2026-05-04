import { Info } from "lucide-react";
import type { ReactNode } from "react";
import { CollapsibleSection } from "../../components/CollapsibleSection";
import { Button } from "../../components/ui/button";
import { Input, Select } from "../../components/ui/input";
import type { ActionStep, NormalProfileSettings } from "../../lib/types";

function FieldRow({ title, info, children }: { title: string; info: string; children: ReactNode }) {
  return (
    <div className="grid gap-1.5">
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <span>{title}</span>
        <span className="inline-flex h-4 w-4 items-center justify-center rounded text-muted-foreground/90" title={info} aria-label={info}>
          <Info size={12} />
        </span>
      </div>
      {children}
    </div>
  );
}

export function NormalDetailsPanel({ normal, onChange }: { normal: NormalProfileSettings; onChange: (patch: Partial<NormalProfileSettings>) => void; }) {
  return (
    <CollapsibleSection title="Normal Profile">
      <div className="grid gap-4">
        <FieldRow title="Use Current Mouse" info="Use current cursor location for clicks.">
          <label className="flex items-center justify-between rounded-lg bg-background/70 p-2 text-sm">Follow cursor<input type="checkbox" checked={normal.use_current_mouse} onChange={(event) => onChange({ use_current_mouse: event.target.checked })} /></label>
        </FieldRow>
        <FieldRow title="Mouse Button" info="Mouse button used by the click action.">
          <Select value={normal.button} onChange={(event) => onChange({ button: event.target.value as "left" | "right" | "middle" })}><option value="left">left</option><option value="right">right</option><option value="middle">middle</option></Select>
        </FieldRow>
        <FieldRow title="Base Delay (ms)" info="Base delay between clicks."><Input type="number" value={normal.interval_ms} onChange={(event) => onChange({ interval_ms: Number(event.target.value) })} /></FieldRow>
        <FieldRow title="Random Delay (ms)" info="Additional random delay added each cycle."><Input type="number" value={normal.interval_random_ms} onChange={(event) => onChange({ interval_random_ms: Number(event.target.value) })} /></FieldRow>
        <FieldRow title="Position Randomness (px)" info="Random offset applied to click position."><Input type="number" value={normal.position_random_px} onChange={(event) => onChange({ position_random_px: Number(event.target.value) })} /></FieldRow>
        <FieldRow title="Clicks Per Cycle" info="Number of clicks each cycle."><Input type="number" value={normal.clicks_per_cycle} onChange={(event) => onChange({ clicks_per_cycle: Number(event.target.value) })} /></FieldRow>
        <FieldRow title="Double Click" info="Send two clicks per cycle.">
          <label className="flex items-center justify-between rounded-lg bg-background/70 p-2 text-sm">Enable<input type="checkbox" checked={normal.double_click} onChange={(event) => onChange({ double_click: event.target.checked })} /></label>
        </FieldRow>
      </div>
    </CollapsibleSection>
  );
}

export function StepDetailsPanel({ step, onChange, onSamplePixel }: { step?: ActionStep; onChange: (patch: Partial<ActionStep>) => void; onSamplePixel: () => void; }) {
  if (!step) return <CollapsibleSection title="Selected Step" defaultOpen><p className="text-sm text-muted-foreground">Select a step to edit details.</p></CollapsibleSection>;
  return (
    <CollapsibleSection title="Selected Step">
      <div className="grid gap-4">
        <FieldRow title="Step Status" info="Disabled steps stay in sequence but are skipped while running.">
          <div className="grid grid-cols-2 gap-2">
            <Button variant={step.enabled ? "success" : "ghost"} onClick={() => onChange({ enabled: true })}>Enabled</Button>
            <Button variant={!step.enabled ? "danger" : "ghost"} onClick={() => onChange({ enabled: false })}>Disabled</Button>
          </div>
        </FieldRow>

        <FieldRow title="Repeat Count" info="Number of times this step repeats before the next step."><Input type="number" value={step.repeats} onChange={(event) => onChange({ repeats: Number(event.target.value) })} /></FieldRow>
        <FieldRow title="Base Delay (ms)" info="Delay after each execution of this step."><Input type="number" value={step.interval_ms} onChange={(event) => onChange({ interval_ms: Number(event.target.value) })} /></FieldRow>
        <FieldRow title="Random Delay (ms)" info="Random delay added after each execution."><Input type="number" value={step.randomness_ms} onChange={(event) => onChange({ randomness_ms: Number(event.target.value) })} /></FieldRow>

        {step.type === "click" ? <><FieldRow title="Mouse X" info="Horizontal screen coordinate."><Input type="number" value={step.x} onChange={(event) => onChange({ x: Number(event.target.value) })} /></FieldRow><FieldRow title="Mouse Y" info="Vertical screen coordinate."><Input type="number" value={step.y} onChange={(event) => onChange({ y: Number(event.target.value) })} /></FieldRow><FieldRow title="Button" info="Mouse button to click."><Select value={step.button} onChange={(event) => onChange({ button: event.target.value as "left" | "right" | "middle" })}><option value="left">left</option><option value="right">right</option><option value="middle">middle</option></Select></FieldRow><FieldRow title="Clicks" info="Number of click presses per step run."><Input type="number" value={step.clicks} onChange={(event) => onChange({ clicks: Number(event.target.value) })} /></FieldRow><FieldRow title="Position Randomness (px)" info="Random offset around target point."><Input type="number" value={step.random_offset} onChange={(event) => onChange({ random_offset: Number(event.target.value) })} /></FieldRow></> : null}

        {step.type === "wait" ? <><FieldRow title="Wait Duration (ms)" info="Primary wait duration for this step."><Input type="number" value={step.ms} onChange={(event) => onChange({ ms: Number(event.target.value) })} /></FieldRow><FieldRow title="Random Wait (ms)" info="Additional random wait duration."><Input type="number" value={step.random_ms} onChange={(event) => onChange({ random_ms: Number(event.target.value) })} /></FieldRow></> : null}

        {step.type === "pixel_check" ? <><FieldRow title="Expected Color" info="Expected RGB value at the target pixel."><div className="flex items-center gap-2"><div className="h-8 w-12 rounded-md border border-border" style={{ backgroundColor: `rgb(${step.expected_rgb.join(",")})` }} /><span className="font-mono text-xs text-muted-foreground">{step.expected_rgb.join(", ")}</span></div></FieldRow><FieldRow title="Pixel X" info="Horizontal coordinate for sampling."><Input type="number" value={step.x} onChange={(event) => onChange({ x: Number(event.target.value) })} /></FieldRow><FieldRow title="Pixel Y" info="Vertical coordinate for sampling."><Input type="number" value={step.y} onChange={(event) => onChange({ y: Number(event.target.value) })} /></FieldRow><FieldRow title="Tolerance" info="Allowed RGB distance from expected color."><Input type="number" value={step.tolerance} onChange={(event) => onChange({ tolerance: Number(event.target.value) })} /></FieldRow><FieldRow title="Mismatch Mode" info="Action to take when color does not match."><Select value={step.mode} onChange={(event) => onChange({ mode: event.target.value as "wait_until_match" | "stop_if_mismatch" | "skip_if_mismatch" })}><option value="wait_until_match">wait until match</option><option value="stop_if_mismatch">stop if mismatch</option><option value="skip_if_mismatch">skip if mismatch</option></Select></FieldRow><FieldRow title="Sample Pixel" info="Read current RGB value from selected coordinates."><Button onClick={onSamplePixel}>Sample pixel</Button></FieldRow></> : null}

        {step.type === "key_tap" ? <FieldRow title="Key" info="Keyboard key to tap."><Input value={step.key} onChange={(event) => onChange({ key: event.target.value })} /></FieldRow> : null}

        {step.type === "loop_start" ? <><FieldRow title="Loop Count" info="Number of loop iterations when not infinite."><Input type="number" value={step.loop_count} disabled={step.loop_infinite} onChange={(event) => onChange({ loop_count: Math.max(1, Number(event.target.value) || 1) })} /></FieldRow><FieldRow title="Infinite Loop" info="Run loop body indefinitely until stopped."><label className="flex items-center justify-between rounded-lg bg-background/70 p-2 text-sm">Enable<input type="checkbox" checked={step.loop_infinite} onChange={(event) => onChange({ loop_infinite: event.target.checked })} /></label></FieldRow></> : null}
      </div>
    </CollapsibleSection>
  );
}
