import { ChevronDown, ChevronRight, Infinity, RadioTower, Square } from "lucide-react";
import { useMemo, useState } from "react";
import { CollapsibleSection } from "../../components/CollapsibleSection";
import { Keycap } from "../../components/keycap";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { stepIcon, stepTitle } from "../../lib/steps";
import type { ActionStep, LoopStartStep } from "../../lib/types";

type LoopRange = { startIndex: number; endIndex: number; depth: number };
type RowItem = { index: number; depth: number; collapsedSummary?: string };

function estimateStepMs(step: ActionStep): number {
  if (step.type === "wait") return (step.ms + step.random_ms + step.interval_ms + step.randomness_ms) * Math.max(1, step.repeats);
  if (step.type === "loop_end") return 0;
  if (step.type === "loop_start") return (step.interval_ms + step.randomness_ms) * Math.max(1, step.repeats);
  return (step.interval_ms + step.randomness_ms) * Math.max(1, step.repeats);
}

function formatMs(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(ms >= 10000 ? 0 : 1)}s`;
}

function resolveLoops(steps: ActionStep[]): Map<string, LoopRange> {
  const stack: Array<{ loopId: string; index: number; depth: number }> = [];
  const ranges = new Map<string, LoopRange>();
  let depth = 0;
  for (let i = 0; i < steps.length; i += 1) {
    const step = steps[i];
    if (step.type === "loop_start") {
      stack.push({ loopId: step.loop_id, index: i, depth });
      depth += 1;
      continue;
    }
    if (step.type === "loop_end") {
      depth = Math.max(0, depth - 1);
      const open = stack.pop();
      if (!open || open.loopId !== step.loop_id) {
        console.warn("Malformed loop structure detected at index", i);
        continue;
      }
      ranges.set(step.loop_id, { startIndex: open.index, endIndex: i, depth: open.depth });
    }
  }
  return ranges;
}

function buildRows(steps: ActionStep[], ranges: Map<string, LoopRange>): RowItem[] {
  const rows: RowItem[] = [];
  const hidden = new Set<number>();
  for (const step of steps) {
    if (step.type === "loop_start" && step.collapsed) {
      const range = ranges.get(step.loop_id);
      if (range) {
        for (let i = range.startIndex + 1; i <= range.endIndex; i += 1) hidden.add(i);
      }
    }
  }

  let depth = 0;
  for (let i = 0; i < steps.length; i += 1) {
    const step = steps[i];
    if (step.type === "loop_end") depth = Math.max(0, depth - 1);
    const rowDepth = depth;
    if (!hidden.has(i)) {
      let collapsedSummary: string | undefined;
      if (step.type === "loop_start" && step.collapsed) {
        const range = ranges.get(step.loop_id);
        if (range) {
          const children = steps.slice(range.startIndex + 1, range.endIndex);
          const count = children.length;
          const cycle = children.reduce((sum, child) => sum + estimateStepMs(child), 0);
          collapsedSummary = `Loop · ${count} steps · ~${formatMs(cycle)}${step.loop_infinite ? "" : ` · ~${formatMs(cycle * Math.max(1, step.loop_count))}`}`;
        }
      }
      rows.push({ index: i, depth: rowDepth, collapsedSummary });
    }
    if (step.type === "loop_start") depth += 1;
  }
  return rows;
}

export function SequenceBuilder({ steps, loopsCount, loopsInfinite, running, runHotkey, selectedId, onSelect, onLoopsChange, onRunToggle, onStepsChange }: { steps: ActionStep[]; loops: number; loopsCount: number; loopsInfinite: boolean; running: boolean; runHotkey: string; selectedId: string; onSelect: (id: string) => void; onLoopsChange: (count: number, infinite: boolean) => void; onRunToggle: () => void; onStepsChange: (steps: ActionStep[]) => void; }) {
  const [loopDraft, setLoopDraft] = useState(String(loopsCount));
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dropAtVisibleRow, setDropAtVisibleRow] = useState<number | null>(null);

  const ranges = useMemo(() => resolveLoops(steps), [steps]);
  const rows = useMemo(() => buildRows(steps, ranges), [steps, ranges]);

  const moveStep = (fromIndex: number, toVisibleRow: number) => {
    const toIndex = toVisibleRow >= rows.length ? steps.length : rows[toVisibleRow].index;
    const moving = steps[fromIndex];
    if (!moving) return;
    if (moving.type === "loop_start" || moving.type === "loop_end") {
      // Preserve marker pair integrity by blocking marker drags for now.
      return;
    }
    const next = [...steps];
    const [item] = next.splice(fromIndex, 1);
    const insertIndex = fromIndex < toIndex ? toIndex - 1 : toIndex;
    next.splice(insertIndex, 0, item);
    onStepsChange(next);
  };

  const toggleCollapse = (rowStep: LoopStartStep) => {
    onStepsChange(steps.map((step) => (step.id === rowStep.id ? { ...step, collapsed: !rowStep.collapsed } : step)));
  };

  return (
    <CollapsibleSection title="Sequence Builder" icon={<RadioTower size={16} />} actions={<div className="flex items-center gap-2"><label className="flex items-center gap-2 text-xs text-muted-foreground">Loops<div className="relative"><Input className="h-8 w-24 pr-8" type="number" min={1} value={loopsInfinite ? "" : loopDraft} disabled={loopsInfinite} onChange={(event) => setLoopDraft(event.target.value)} onBlur={() => { const parsed = Number(loopDraft); if (Number.isFinite(parsed) && parsed >= 1) { const safe = Math.floor(parsed); onLoopsChange(safe, false); setLoopDraft(String(safe)); } else { setLoopDraft(String(loopsCount)); } }} /><button className={`absolute right-1 top-1/2 -translate-y-1/2 rounded p-1 ${loopsInfinite ? "text-accent" : "text-muted-foreground hover:text-foreground"}`} onClick={() => onLoopsChange(loopsCount, !loopsInfinite)} title="Repeat indefinitely" type="button"><Infinity size={14} /></button></div></label><Button variant={running ? "danger" : "success"} onClick={onRunToggle}>{running ? <Square size={16} /> : <RadioTower size={16} />}{running ? "Stop sequence" : "Run sequence"}<Keycap>{runHotkey}</Keycap></Button></div>}>
      <div className="grid gap-2">
        {rows.map((row, visibleIndex) => {
          const step = steps[row.index];
          return (
            <div key={step.id}>
              <div className={`h-1 rounded ${dropAtVisibleRow === visibleIndex ? "bg-info/70" : "bg-transparent"}`} />
              <button
                draggable={step.type !== "loop_start" && step.type !== "loop_end"}
                onDragStart={() => setDragIndex(row.index)}
                onDragOver={(e) => { e.preventDefault(); setDropAtVisibleRow(visibleIndex); }}
                onDrop={() => {
                  if (dragIndex === null) return;
                  moveStep(dragIndex, visibleIndex);
                  setDragIndex(null);
                  setDropAtVisibleRow(null);
                }}
                className={`flex w-full items-center justify-between rounded-lg border p-3 text-left transition ${step.id === selectedId ? "border-info/45 bg-info/10" : "border-border bg-background/60 hover:bg-surface-strong"} ${step.enabled ? "" : "opacity-45"}`}
                onClick={() => onSelect(step.id)}
                style={{ marginLeft: `${row.depth * 16}px`, width: `calc(100% - ${row.depth * 16}px)` }}
              >
                <div className="flex items-center gap-3">
                  <Badge>{String(row.index + 1).padStart(2, "0")}</Badge>
                  {step.type === "loop_start" ? (
                    <button type="button" className="rounded p-1 text-info hover:bg-background/50" onClick={(e) => { e.stopPropagation(); toggleCollapse(step); }} title={step.collapsed ? "Expand loop" : "Collapse loop"}>
                      {step.collapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                    </button>
                  ) : null}
                  <span className="text-info">{stepIcon(step.type)}</span>
                  <div>
                    <div className="text-sm font-semibold">{row.collapsedSummary ?? stepTitle(step)}</div>
                    <div className="font-mono text-xs text-muted-foreground">repeats {step.repeats} / delay {step.interval_ms}ms</div>
                  </div>
                </div>
                <Badge tone={step.enabled ? "success" : "neutral"}>{step.enabled ? "enabled" : "off"}</Badge>
              </button>
            </div>
          );
        })}
        <div className={`h-1 rounded ${dropAtVisibleRow === rows.length ? "bg-info/70" : "bg-transparent"}`} onDragOver={(e) => { e.preventDefault(); setDropAtVisibleRow(rows.length); }} onDrop={() => { if (dragIndex === null) return; moveStep(dragIndex, rows.length); setDragIndex(null); setDropAtVisibleRow(null); }} />
      </div>
    </CollapsibleSection>
  );
}
