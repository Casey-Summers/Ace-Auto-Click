import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  type DragEndEvent,
  useSensor,
  useSensors
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Infinity, RadioTower, Square, SquareMinus, SquarePlus } from "lucide-react";
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
  for (let index = 0; index < steps.length; index += 1) {
    const step = steps[index];
    if (step.type === "loop_start") {
      stack.push({ loopId: step.loop_id, index, depth });
      depth += 1;
      continue;
    }
    if (step.type === "loop_end") {
      depth = Math.max(0, depth - 1);
      const open = stack.pop();
      if (!open || open.loopId !== step.loop_id) {
        console.warn("Malformed loop structure detected at index", index);
        continue;
      }
      ranges.set(step.loop_id, { startIndex: open.index, endIndex: index, depth: open.depth });
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
        for (let index = range.startIndex + 1; index <= range.endIndex; index += 1) hidden.add(index);
      }
    }
  }

  let depth = 0;
  for (let index = 0; index < steps.length; index += 1) {
    const step = steps[index];
    if (step.type === "loop_end") depth = Math.max(0, depth - 1);
    if (!hidden.has(index)) {
      let collapsedSummary: string | undefined;
      if (step.type === "loop_start" && step.collapsed) {
        const range = ranges.get(step.loop_id);
        if (range) {
          const children = steps.slice(range.startIndex + 1, range.endIndex);
          const cycle = children.reduce((sum, child) => sum + estimateStepMs(child), 0);
          collapsedSummary = `Loop - ${children.length} steps - ~${formatMs(cycle)}${step.loop_infinite ? "" : ` - ~${formatMs(cycle * Math.max(1, step.loop_count))}`}`;
        }
      }
      rows.push({ index, depth, collapsedSummary });
    }
    if (step.type === "loop_start") depth += 1;
  }
  return rows;
}

function blockRangeForIndex(index: number, steps: ActionStep[], ranges: Map<string, LoopRange>) {
  const step = steps[index];
  if (!step) return { startIndex: index, endIndex: index };
  if (step.type === "loop_start") return ranges.get(step.loop_id) ?? { startIndex: index, endIndex: index };
  if (step.type === "loop_end") {
    const matched = Array.from(ranges.values()).find((range) => range.endIndex === index);
    return matched ?? { startIndex: index, endIndex: index };
  }
  return { startIndex: index, endIndex: index };
}

function moveBlock(steps: ActionStep[], fromIndex: number, toIndex: number, ranges: Map<string, LoopRange>) {
  const range = blockRangeForIndex(fromIndex, steps, ranges);
  if (toIndex >= range.startIndex && toIndex <= range.endIndex) return steps;
  const block = steps.slice(range.startIndex, range.endIndex + 1);
  const next = [...steps.slice(0, range.startIndex), ...steps.slice(range.endIndex + 1)];
  const insertIndex = toIndex > range.startIndex ? toIndex - block.length + 1 : toIndex;
  next.splice(Math.max(0, insertIndex), 0, ...block);
  return next;
}

function SortableRow({ row, step, selected, onSelect, onToggleCollapse }: { row: RowItem; step: ActionStep; selected: boolean; onSelect: () => void; onToggleCollapse: (step: LoopStartStep) => void; }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: step.id });
  const isLoop = step.type === "loop_start" || step.type === "loop_end";
  return (
    <div ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition, marginLeft: `${row.depth * 16}px`, width: `calc(100% - ${row.depth * 16}px)` }} className={isDragging ? "opacity-60" : ""}>
      <div className={`flex w-full items-center justify-between rounded-lg border p-3 text-left transition ${selected ? "border-info/45 bg-info/10" : "border-border bg-background/60 hover:bg-surface-strong"} ${step.enabled ? "" : "opacity-45"}`} onClick={onSelect}>
        <div className="flex min-w-0 items-center gap-3">
          <button type="button" className="rounded p-1 text-muted-foreground hover:bg-background/50 hover:text-foreground" title="Drag step" {...attributes} {...listeners}>
            <GripVertical size={14} />
          </button>
          <Badge>{String(row.index + 1).padStart(2, "0")}</Badge>
          {step.type === "loop_start" ? (
            <button type="button" className="rounded-md border border-info/30 bg-info/10 p-1 text-info hover:bg-info/15" onClick={(event) => { event.stopPropagation(); onToggleCollapse(step); }} title={step.collapsed ? "Expand loop" : "Collapse loop"}>
              {step.collapsed ? <SquarePlus size={14} /> : <SquareMinus size={14} />}
            </button>
          ) : null}
          {!isLoop ? <span className="text-info">{stepIcon(step.type)}</span> : null}
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold">{row.collapsedSummary ?? stepTitle(step)}</div>
            <div className="font-mono text-xs text-muted-foreground">repeats {step.repeats} / delay {step.interval_ms}ms</div>
          </div>
        </div>
        <Badge tone={step.enabled ? "success" : "neutral"}>{step.enabled ? "Enabled" : "Disabled"}</Badge>
      </div>
    </div>
  );
}

export function SequenceBuilder({ steps, loopsCount, loopsInfinite, running, runHotkey, selectedId, onSelect, onLoopsChange, onRunToggle, onStepsChange }: { steps: ActionStep[]; loops: number; loopsCount: number; loopsInfinite: boolean; running: boolean; runHotkey: string; selectedId: string; onSelect: (id: string) => void; onLoopsChange: (count: number, infinite: boolean) => void; onRunToggle: () => void; onStepsChange: (steps: ActionStep[]) => void; }) {
  const [loopDraft, setLoopDraft] = useState(String(loopsCount));
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );
  const ranges = useMemo(() => resolveLoops(steps), [steps]);
  const rows = useMemo(() => buildRows(steps, ranges), [steps, ranges]);
  const rowIds = rows.map((row) => steps[row.index].id);

  const onDragEnd = (event: DragEndEvent) => {
    if (!event.over || event.active.id === event.over.id) return;
    const fromIndex = steps.findIndex((step) => step.id === event.active.id);
    const toIndex = steps.findIndex((step) => step.id === event.over?.id);
    if (fromIndex < 0 || toIndex < 0) return;
    onStepsChange(moveBlock(steps, fromIndex, toIndex, ranges));
  };

  const toggleCollapse = (rowStep: LoopStartStep) => {
    onStepsChange(steps.map((step) => (step.id === rowStep.id ? { ...step, collapsed: !rowStep.collapsed } : step)));
  };

  return (
    <CollapsibleSection title="Sequence Builder" icon={<RadioTower size={16} />} actions={<div className="flex items-center gap-2"><label className="flex items-center gap-2 text-xs text-muted-foreground">Loops<div className="relative"><Input className="h-8 w-24 pr-8" type="number" min={1} value={loopsInfinite ? "" : loopDraft} disabled={loopsInfinite} onChange={(event) => { const nextValue = event.target.value; setLoopDraft(nextValue); const parsed = Number(nextValue); if (Number.isFinite(parsed) && parsed >= 1) onLoopsChange(Math.floor(parsed), false); }} onBlur={() => { const parsed = Number(loopDraft); if (Number.isFinite(parsed) && parsed >= 1) { const safe = Math.floor(parsed); onLoopsChange(safe, false); setLoopDraft(String(safe)); } else { setLoopDraft(String(loopsCount)); } }} /><button className={`absolute right-1 top-1/2 -translate-y-1/2 rounded p-1 ${loopsInfinite ? "text-accent" : "text-muted-foreground hover:text-foreground"}`} onClick={() => onLoopsChange(loopsCount, !loopsInfinite)} title="Repeat indefinitely" type="button"><Infinity size={14} /></button></div></label><Button variant={running ? "danger" : "success"} onClick={onRunToggle}>{running ? <Square size={16} /> : <RadioTower size={16} />}{running ? "Stop sequence" : "Run sequence"}<Keycap>{runHotkey}</Keycap></Button></div>}>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
        <SortableContext items={rowIds} strategy={verticalListSortingStrategy}>
          <div className="grid gap-2">
            {rows.map((row) => {
              const step = steps[row.index];
              return <SortableRow key={step.id} row={row} step={step} selected={step.id === selectedId} onSelect={() => onSelect(step.id)} onToggleCollapse={toggleCollapse} />;
            })}
          </div>
        </SortableContext>
      </DndContext>
    </CollapsibleSection>
  );
}
