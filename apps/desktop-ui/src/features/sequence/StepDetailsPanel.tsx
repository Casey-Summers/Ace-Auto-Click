import { Copy, Info, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
import { CaptureButton } from "../../components/CaptureButton";
import { CollapsibleSection } from "../../components/CollapsibleSection";
import { Keycap } from "../../components/keycap";
import { Button } from "../../components/ui/button";
import { Input, Select } from "../../components/ui/input";
import { displayKeybind } from "../../lib/keybinds";
import { formatMs, stepTitle } from "../../lib/sequence";
import type { ActionStep, NormalProfileSettings, Point, Rgb } from "../../lib/types";

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

function ActionDetailsSection({ active, rightContent, children }: { active: boolean; rightContent?: ReactNode; children: ReactNode }) {
  if (!active) return null;
  return (
    <section className="grid gap-2 rounded-lg border border-info/20 bg-info/5 p-2.5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">Action Details</h3>
        {rightContent}
      </div>
      {children}
    </section>
  );
}

function CursorPreview({ cursor, target }: { cursor: Point | null; target: Point }) {
  const markerX = cursor ? Math.max(8, Math.min(92, (cursor.x % 1000) / 10)) : 50;
  const markerY = cursor ? Math.max(10, Math.min(90, (cursor.y % 700) / 7)) : 50;
  const targetX = Math.max(8, Math.min(92, (target.x % 1000) / 10));
  const targetY = Math.max(10, Math.min(90, (target.y % 700) / 7));

  return (
    <div className="grid gap-3">
      <div className="relative h-32 overflow-hidden rounded-lg border border-border bg-background/80">
        <div className="absolute inset-0 bg-[linear-gradient(hsl(var(--border))_1px,transparent_1px),linear-gradient(90deg,hsl(var(--border))_1px,transparent_1px)] bg-[size:20px_20px] opacity-35" />
        <div
          className="absolute h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-accent bg-accent/20"
          style={{ left: `${targetX}%`, top: `${targetY}%` }}
          title="Current saved target"
        />
        <div
          className="absolute h-6 w-6 -translate-x-1/2 -translate-y-1/2 rounded-full border border-info bg-info/20 shadow-[0_0_18px_hsl(var(--info)/0.35)]"
          style={{ left: `${markerX}%`, top: `${markerY}%` }}
          title="Live cursor"
        >
          <span className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-info" />
          <span className="absolute left-0 top-1/2 h-px w-full -translate-y-1/2 bg-info" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-md bg-background/70 p-2">
          <div className="text-muted-foreground">Cursor</div>
          <div className="font-mono">{cursor ? `${cursor.x}, ${cursor.y}` : "Locating..."}</div>
        </div>
        <div className="rounded-md bg-background/70 p-2">
          <div className="text-muted-foreground">Saved Target</div>
          <div className="font-mono">{target.x}, {target.y}</div>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">Click anywhere to capture. Esc cancels.</p>
    </div>
  );
}

function PixelMatchPreview({ live, expected }: { live: Rgb | null; expected: Rgb }) {
  return (
    <div className="grid gap-2">
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-md bg-background/70 p-2 min-w-0">
          <div className="text-xs text-muted-foreground">Current</div>
          <div className="mt-1 h-12 rounded border border-border" style={{ backgroundColor: live ? `rgb(${live.join(",")})` : "transparent" }} />
          <div className="mt-1 font-mono text-xs min-h-[2.4em] break-words">{live ? `RGB ${live.join(", ")}` : "RGB n/a"}</div>
        </div>
        <div className="rounded-md bg-background/70 p-2 min-w-0">
          <div className="text-xs text-muted-foreground">Expected</div>
          <div className="mt-1 h-12 rounded border border-border" style={{ backgroundColor: `rgb(${expected.join(",")})` }} />
          <div className="mt-1 font-mono text-xs min-h-[2.4em] break-words">{`RGB ${expected.join(", ")}`}</div>
        </div>
      </div>
    </div>
  );
}

function CoordinatePreview({ x, y, offset }: { x: number; y: number; offset: number }) {
  return <p className="text-xs text-muted-foreground">Target: <span className="font-mono">{x}, {y}</span>{offset > 0 ? ` with +- ${offset}px randomness` : ""}.</p>;
}

function TimingPreview({ baseMs, randomMs, repeats }: { baseMs: number; randomMs: number; repeats: number }) {
  const total = Math.max(0, baseMs) * Math.max(1, repeats);
  const jitter = Math.max(0, randomMs) * Math.max(1, repeats);
  return <p className="text-xs text-muted-foreground">Timing: <span className="font-mono">{formatMs(total)}</span>{jitter > 0 ? <> + up to <span className="font-mono">{formatMs(jitter)}</span> random</> : null} per step cycle.</p>;
}

function toggleDragButton(buttons: Array<"left" | "right" | "middle">, button: "left" | "right" | "middle") {
  const next = buttons.includes(button) ? buttons.filter((item) => item !== button) : [...buttons, button];
  return next.length > 0 ? next : [button];
}

function CaptureActionRow({ title, info, waiting, idleLabel, waitingLabel, pendingHint, value, valuePreview, ariaLabel, onCapture }: { title: string; info: string; waiting?: boolean; idleLabel: string; waitingLabel?: string; pendingHint?: string; value?: string; valuePreview?: ReactNode; ariaLabel?: string; onCapture: () => void }) {
  return (
    <FieldRow title={title} info={info}>
      <CaptureButton
        idleText={idleLabel}
        pendingText={waitingLabel}
        pendingHint={pendingHint}
        waiting={waiting}
        disabled={Boolean(waiting)}
        value={value}
        valuePreview={valuePreview}
        ariaLabel={ariaLabel}
        onCapture={onCapture}
      />
    </FieldRow>
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
        <FieldRow title="Base Delay (ms)" info="Safety delay applied before each click."><Input type="number" value={normal.interval_ms} onChange={(event) => onChange({ interval_ms: Number(event.target.value) })} /></FieldRow>
        <FieldRow title="Random Delay (ms)" info="Additional random safety delay applied before each click."><Input type="number" value={normal.interval_random_ms} onChange={(event) => onChange({ interval_random_ms: Number(event.target.value) })} /></FieldRow>
        <FieldRow title="Position Randomness (px)" info="Random offset applied to click position."><Input type="number" value={normal.position_random_px} onChange={(event) => onChange({ position_random_px: Number(event.target.value) })} /></FieldRow>
        <FieldRow title="Clicks Per Cycle" info="Number of clicks each cycle."><Input type="number" value={normal.clicks_per_cycle} onChange={(event) => onChange({ clicks_per_cycle: Number(event.target.value) })} /></FieldRow>
        <FieldRow title="Double Click" info="Send two clicks per cycle.">
          <label className="flex items-center justify-between rounded-lg bg-background/70 p-2 text-sm">Enable<input type="checkbox" checked={normal.double_click} onChange={(event) => onChange({ double_click: event.target.checked })} /></label>
        </FieldRow>
      </div>
    </CollapsibleSection>
  );
}

export function StepDetailsPanel({ step, pickCursorPosition, pickingClickPosition, pickingKey, pixelLiveRgb, samplingPixel, onChange, onSamplePixel, onPickClickPosition, onPickKey, onDuplicate, onDelete }: { step?: ActionStep; pickCursorPosition?: Point | null; pickingClickPosition?: boolean; pickingKey?: boolean; pixelLiveRgb?: Rgb | null; samplingPixel?: boolean; onChange: (patch: Partial<ActionStep>) => void; onSamplePixel: () => void; onPickClickPosition: () => void; onPickKey: () => void; onDuplicate: () => void; onDelete: () => void; }) {
  if (!step) return <CollapsibleSection title="Action Settings" defaultOpen><p className="text-sm text-muted-foreground">Select an action to edit settings, or add one from Action Library.</p></CollapsibleSection>;
  const isLoopMarker = step.type === "loop_start" || step.type === "loop_end";
  const keybindDisplay = step.type === "key_tap" || step.type === "key_hold" ? displayKeybind(step.key) : "";
  return (
    <CollapsibleSection title="Action Settings" className="flex min-h-0 flex-1 flex-col overflow-hidden" contentClassName="min-h-0 flex-1 overflow-hidden">
      <div className="flex max-h-full min-h-0 flex-col gap-4">
        <div className="action-settings-scroll grid min-h-0 flex-1 gap-4 overflow-y-auto px-1 pr-3">
          <FieldRow title="Step Status" info="Disabled steps stay in sequence but are skipped while running.">
            <div className="grid grid-cols-[2fr_2fr_1fr_1fr] gap-2">
              <Button className="w-full" variant={step.enabled ? "success" : "ghost"} onClick={() => onChange({ enabled: true })}>Enabled</Button>
              <Button className="w-full" variant={!step.enabled ? "danger" : "ghost"} onClick={() => onChange({ enabled: false })}>Disabled</Button>
              <Button className="w-full" variant="ghost" size="icon" title="Duplicate action" aria-label="Duplicate action" onClick={onDuplicate}><Copy size={18} /></Button>
              <Button className="w-full" variant="danger" size="icon" title="Delete action" aria-label="Delete action" onClick={onDelete}><Trash2 size={18} /></Button>
            </div>
          </FieldRow>

          {step.type === "click" || step.type === "move" || step.type === "drag" ? (
            <CaptureActionRow
              title="Position Picker"
              info="Waits for the next click and records its exact screen location for this action."
              waiting={pickingClickPosition}
              idleLabel={step.type === "click" ? "Pick Click Position" : step.type === "move" ? "Pick Move Position" : "Pick Drag Start"}
              onCapture={onPickClickPosition}
            />
          ) : null}
          {step.type === "key_hold" || step.type === "key_tap" ? (
            <CaptureActionRow
              title="Keybind Picker"
              info="Waits for the next keyboard key or supported mouse side button and records the first keybind input."
              waiting={pickingKey}
              idleLabel="Change keybind"
              waitingLabel="Press key or side button..."
              pendingHint="Esc cancels"
              value={keybindDisplay}
              valuePreview={<Keycap>{keybindDisplay}</Keycap>}
              onCapture={onPickKey}
            />
          ) : null}

          {step.type === "pixel_check" ? <><CaptureActionRow title="Pixel Sampler" info="Arms pixel sampling; next click captures current color at that location." waiting={samplingPixel} idleLabel="Sample Pixel" onCapture={onSamplePixel} /><FieldRow title="Mismatch Mode" info="Action to take when color does not match."><Select value={step.mode} onChange={(event) => onChange({ mode: event.target.value as "wait_until_match" | "stop_if_mismatch" | "skip_if_mismatch" })}><option value="wait_until_match">wait until match</option><option value="stop_if_mismatch">stop if mismatch</option><option value="skip_if_mismatch">skip if mismatch</option></Select></FieldRow></> : null}

          {!isLoopMarker ? <FieldRow title="Repeat Count" info="Number of times this step repeats before the next step."><Input type="number" value={step.repeats} onChange={(event) => onChange({ repeats: Number(event.target.value) })} /></FieldRow> : null}
          {!isLoopMarker ? <FieldRow title="Base Delay (ms)" info="Safety delay applied before this step runs."><Input type="number" value={step.interval_ms} onChange={(event) => onChange({ interval_ms: Number(event.target.value) })} /></FieldRow> : null}
          {!isLoopMarker ? <FieldRow title="Random Delay (ms)" info="Additional random safety delay applied before this step runs."><Input type="number" value={step.randomness_ms} onChange={(event) => onChange({ randomness_ms: Number(event.target.value) })} /></FieldRow> : null}

          {step.type === "click" ? <><FieldRow title="Mouse X" info="Horizontal screen coordinate."><Input type="number" value={step.x} onChange={(event) => onChange({ x: Number(event.target.value) })} /></FieldRow><FieldRow title="Mouse Y" info="Vertical screen coordinate."><Input type="number" value={step.y} onChange={(event) => onChange({ y: Number(event.target.value) })} /></FieldRow><FieldRow title="Button" info="Mouse button to click."><Select value={step.button} onChange={(event) => onChange({ button: event.target.value as "left" | "right" | "middle" })}><option value="left">left</option><option value="right">right</option><option value="middle">middle</option></Select></FieldRow><FieldRow title="Clicks" info="Number of click presses per step run."><Input type="number" value={step.clicks} onChange={(event) => onChange({ clicks: Number(event.target.value) })} /></FieldRow><FieldRow title="Position Randomness (px)" info="Random offset around target point."><Input type="number" value={step.random_offset} onChange={(event) => onChange({ random_offset: Number(event.target.value) })} /></FieldRow><CoordinatePreview x={step.x} y={step.y} offset={step.random_offset} /></> : null}

          {step.type === "move" ? <><FieldRow title="Mouse X" info="Horizontal screen coordinate."><Input type="number" value={step.x} onChange={(event) => onChange({ x: Number(event.target.value) })} /></FieldRow><FieldRow title="Mouse Y" info="Vertical screen coordinate."><Input type="number" value={step.y} onChange={(event) => onChange({ y: Number(event.target.value) })} /></FieldRow><FieldRow title="Position Randomness (px)" info="Random offset around target point."><Input type="number" value={step.random_offset} onChange={(event) => onChange({ random_offset: Number(event.target.value) })} /></FieldRow><CoordinatePreview x={step.x} y={step.y} offset={step.random_offset} /></> : null}

          {step.type === "drag" ? <><FieldRow title="Held Buttons" info="Mouse buttons held while dragging."><div className="grid grid-cols-3 gap-2">{(["left", "right", "middle"] as const).map((button) => <label key={button} className="flex items-center justify-between rounded-lg bg-background/70 p-2 text-sm">{button}<input type="checkbox" checked={step.buttons.includes(button)} onChange={() => onChange({ buttons: toggleDragButton(step.buttons, button) })} /></label>)}</div></FieldRow><FieldRow title="Direction" info="Drag direction from the start point."><Select value={step.direction} onChange={(event) => onChange({ direction: event.target.value as "right" | "left" | "up" | "down" })}><option value="right">right</option><option value="left">left</option><option value="up">up</option><option value="down">down</option></Select></FieldRow><FieldRow title="Length (px)" info="How far to drag."><Input type="number" value={step.length_px} onChange={(event) => onChange({ length_px: Number(event.target.value) })} /></FieldRow><FieldRow title="Speed (px/s)" info="Drag movement speed in pixels per second."><Input type="number" min={50} max={5000} value={step.speed} onChange={(event) => onChange({ speed: Number(event.target.value) })} /></FieldRow><FieldRow title="Mouse X" info="Horizontal screen coordinate where the drag begins."><Input type="number" value={step.x} onChange={(event) => onChange({ x: Number(event.target.value) })} /></FieldRow><FieldRow title="Mouse Y" info="Vertical screen coordinate where the drag begins."><Input type="number" value={step.y} onChange={(event) => onChange({ y: Number(event.target.value) })} /></FieldRow><FieldRow title="Position Randomness (px)" info="Random offset around the drag start point."><Input type="number" value={step.random_offset} onChange={(event) => onChange({ random_offset: Number(event.target.value) })} /></FieldRow><CoordinatePreview x={step.x} y={step.y} offset={step.random_offset} /></> : null}

          {step.type === "wait" ? <><FieldRow title="Wait Duration (ms)" info="Primary wait duration for this step."><Input type="number" value={step.ms} onChange={(event) => onChange({ ms: Number(event.target.value) })} /></FieldRow><FieldRow title="Random Wait (ms)" info="Additional random wait duration."><Input type="number" value={step.random_ms} onChange={(event) => onChange({ random_ms: Number(event.target.value) })} /></FieldRow><TimingPreview baseMs={step.interval_ms} randomMs={step.randomness_ms} repeats={step.repeats} /></> : null}

          {step.type === "pixel_check" ? <FieldRow title="Tolerance" info="Allowed RGB distance from expected color."><Input type="number" value={step.tolerance} onChange={(event) => onChange({ tolerance: Number(event.target.value) })} /></FieldRow> : null}

          {step.type === "key_hold" ? <FieldRow title="Hold Duration (ms)" info="How long to keep the key pressed before release."><Input type="number" value={step.hold_ms} onChange={(event) => onChange({ hold_ms: Number(event.target.value) })} /></FieldRow> : null}

          {step.type === "loop_start" ? <><FieldRow title="Loop Count" info="Number of loop iterations when not infinite."><Input type="number" value={step.loop_count} disabled={step.loop_infinite} onChange={(event) => onChange({ loop_count: Math.max(1, Number(event.target.value) || 1) })} /></FieldRow><FieldRow title="Infinite Loop" info="Run loop body indefinitely until stopped."><label className="flex items-center justify-between rounded-lg bg-background/70 p-2 text-sm">Enable<input type="checkbox" checked={step.loop_infinite} onChange={(event) => onChange({ loop_infinite: event.target.checked })} /></label></FieldRow><p className="text-xs text-muted-foreground">Loop summary: {stepTitle(step)}</p></> : null}
        </div>

        <ActionDetailsSection
          active={Boolean(((step.type === "click" || step.type === "move" || step.type === "drag") && pickingClickPosition) || step.type === "pixel_check")}
          rightContent={step.type === "pixel_check" ? (() => {
            const delta = pixelLiveRgb ? Math.max(...pixelLiveRgb.map((value, index) => Math.abs(value - step.expected_rgb[index]))) : null;
            const withinTolerance = delta !== null && delta <= step.tolerance;
            const status = pixelLiveRgb === null ? "Outside Tolerance" : withinTolerance ? "Within Tolerance" : "Outside Tolerance";
            const statusTone = status === "Within Tolerance" ? "border-success/70 bg-success/15 text-success" : "border-warning/70 bg-warning/15 text-warning";
            return <div className={`rounded border px-2 py-1 text-xs font-semibold ${statusTone}`}>{status}</div>;
          })() : undefined}
        >
          {step.type === "click" || step.type === "move" || step.type === "drag" ? <CursorPreview cursor={pickCursorPosition ?? null} target={{ x: step.x, y: step.y }} /> : null}
          {step.type === "pixel_check" ? <PixelMatchPreview live={pixelLiveRgb ?? null} expected={step.expected_rgb} /> : null}
        </ActionDetailsSection>
      </div>
    </CollapsibleSection>
  );
}
