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
import { ChevronDown, ChevronRight, GripVertical, Infinity, RadioTower, RotateCcw, RotateCw, Square } from "lucide-react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { CollapsibleSection } from "../../components/CollapsibleSection";
import { SplitHotkeyActionButton } from "../../components/SplitHotkeyActionButton";
import { Badge } from "../../components/ui/badge";
import { Input } from "../../components/ui/input";
import { stepIcon } from "../../lib/steps";
import { executionStepStateTone, formatMs, resolveLoops, stepSummary, sumTiming, type RowSummary } from "../../lib/sequence";
import type { ActionStep, ExecutionEvent, LoopStartStep, Rgb } from "../../lib/types";
type RailSegment = { id: string; y1: number; y2: number };
type RowGeometry = { top: number; bottom: number };
type RowItem = { index: number; indentPct: number; collapsedSummary?: RowSummary };
type LoopRange = { startIndex: number; endIndex: number; depth: number };

function computeIndentPct(index: number, ranges: Map<string, LoopRange>): number {
  for (const range of ranges.values()) {
    if (index > range.startIndex && index < range.endIndex) return 10;
  }
  return 0;
}

function buildRows(steps: ActionStep[], ranges: Map<string, LoopRange>): RowItem[] {
  const rows: RowItem[] = [];
  const hidden = new Set<number>();
  for (const step of steps) {
    if (step.type === "loop_start" && step.collapsed) {
      const range = ranges.get(step.loop_id);
      if (range) for (let index = range.startIndex + 1; index <= range.endIndex; index += 1) hidden.add(index);
    }
  }
  for (let index = 0; index < steps.length; index += 1) {
    if (hidden.has(index)) continue;
    const step = steps[index];
    let collapsedSummary: RowSummary | undefined;
    if (step.type === "loop_start" && step.collapsed) {
      const range = ranges.get(step.loop_id);
      if (range) {
        const children = steps.slice(range.startIndex + 1, range.endIndex);
        collapsedSummary = { title: step.loop_infinite ? `Loop infinite - ${children.length} steps` : `Loop ${Math.max(1, step.loop_count, step.repeats)}x - ${children.length} steps`, subtext: "" };
      }
    }
    rows.push({ index, indentPct: computeIndentPct(index, ranges), collapsedSummary });
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

function SortableRow({ row, step, selected, stateTone, flashTone, heldTone, selectedPixelLiveRgb, pixelSamplingAssist, onSelect, onToggleCollapse }: { row: RowItem; step: ActionStep; selected: boolean; stateTone?: "info" | "success" | "warning" | "danger"; flashTone?: "success" | "warning" | null; heldTone?: "danger" | null; selectedPixelLiveRgb?: Rgb | null; pixelSamplingAssist?: boolean; onSelect: () => void; onToggleCollapse: (step: LoopStartStep) => void; }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: step.id });
  const summary = row.collapsedSummary ?? stepSummary(step, selectedPixelLiveRgb, selected);
  return (
    <div ref={setNodeRef} data-step-id={step.id} style={{ transform: CSS.Transform.toString(transform), transition, marginLeft: `${row.indentPct}%`, width: `calc(100% - ${row.indentPct}%)` }} className={isDragging ? "opacity-60" : ""}>
      <div className={`relative flex w-full items-center justify-between rounded-lg border p-3 text-left transition ${heldTone === "danger" ? "border-danger/60 bg-danger/10" : selected ? (stateTone === "success" ? "border-success/55 bg-success/10" : stateTone === "warning" ? "border-warning/55 bg-warning/10" : stateTone === "danger" ? "border-danger/55 bg-danger/10" : "border-info/45 bg-info/10") : "border-border bg-background/60 hover:bg-surface-strong"} ${step.enabled ? "" : "opacity-45"} ${pixelSamplingAssist ? "border-warning/75 bg-warning/10 shadow-[0_0_0_1px_hsl(var(--warning)/0.5)]" : ""} ${flashTone === "success" && !heldTone ? "step-fade-success" : ""} ${flashTone === "warning" && !heldTone ? "step-fade-warning" : ""}`} onClick={onSelect}>
        <div className="flex min-w-0 items-center gap-3">
          <button type="button" className="rounded p-1 text-muted-foreground hover:bg-background/50 hover:text-foreground" title="Drag step" {...attributes} {...listeners}><GripVertical size={14} /></button>
          {step.type === "loop_start"
            ? (
              <button
                type="button"
                className="step-icon inline-flex items-center justify-center rounded-md hover:bg-background/60 [&>svg]:h-[20px] [&>svg]:w-[20px]"
                data-step-type="loop_start"
                onClick={(event) => { event.stopPropagation(); onToggleCollapse(step); }}
                title={step.collapsed ? "Expand loop" : "Collapse loop"}
              >
                <RotateCw size={20} />
              </button>
            )
            : step.type === "loop_end"
              ? <span className="step-icon [&>svg]:h-[20px] [&>svg]:w-[20px]" data-step-type={step.type}><RotateCcw size={20} /></span>
              : <span className="step-icon [&>svg]:h-[20px] [&>svg]:w-[20px]" data-step-type={step.type}>{stepIcon(step.type)}</span>}
          <div className="min-w-0">
            <div className="flex items-center gap-2 truncate text-sm font-semibold">
              <span className="truncate">{summary.title}</span>
              {summary.pixelComparison ? <span className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border border-border" style={{ backgroundColor: summary.pixelComparison.current ? `rgb(${summary.pixelComparison.current.join(",")})` : "transparent" }} /><span className="text-xs">{summary.pixelComparison.matches ? "=" : "!="}</span><span className="h-3 w-3 rounded-sm border border-border" style={{ backgroundColor: `rgb(${summary.pixelComparison.expected.join(",")})` }} /></span> : null}
            </div>
            {summary.subtext ? <div className="truncate font-mono text-xs text-muted-foreground">{summary.subtext}</div> : null}
          </div>
        </div>
        <div className="ml-3 flex shrink-0 items-center gap-1.5">
          {step.type === "loop_start" ? (
            <button
              type="button"
              className="rounded border border-border bg-background/60 p-1 hover:bg-background/80"
              title={step.collapsed ? "Expand loop" : "Collapse loop"}
              onClick={(event) => {
                event.stopPropagation();
                onToggleCollapse(step);
              }}
            >
              {step.collapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
            </button>
          ) : null}
          <Badge>{String(row.index + 1).padStart(2, "0")}</Badge>
        </div>
      </div>
    </div>
  );
}

export function SequenceBuilder({ steps, loopsCount, loopsInfinite, running, runHotkey, selectedId, selectedPixelLiveRgb, samplingPixelStepId, executingStepId, executingStepState, executionEvents, onSelect, onLoopsChange, onRunToggle, onStepsChange, onSamplePixelFromClickStep, onRunHotkeyClick }: { steps: ActionStep[]; loops: number; loopsCount: number; loopsInfinite: boolean; running: boolean; runHotkey: string; selectedId: string; selectedPixelLiveRgb?: Rgb | null; samplingPixelStepId?: string; executingStepId?: string | null; executingStepState?: "running" | "waiting" | "condition_false" | null; executionEvents?: ExecutionEvent[]; onSelect: (id: string) => void; onLoopsChange: (count: number, infinite: boolean) => void; onRunToggle: () => void; onStepsChange: (steps: ActionStep[]) => void; onSamplePixelFromClickStep?: (clickStepId: string) => void; onRunHotkeyClick: () => void; }) {
  const [loopDraft, setLoopDraft] = useState(String(loopsCount));
  const [flashByStepId, setFlashByStepId] = useState<Record<string, "success" | "warning">>({});
  const [heldStateByStepId, setHeldStateByStepId] = useState<Record<string, "danger">>({});
  const [rowGeometry, setRowGeometry] = useState<Map<string, RowGeometry>>(new Map());
  const sensors = useSensors(useSensor(PointerSensor), useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }));
  const ranges = useMemo(() => resolveLoops(steps), [steps]);
  const totalEstimate = useMemo(() => {
    const base = sumTiming(steps).baseMs;
    const loops = loopsInfinite ? 1 : Math.max(1, loopsCount);
    return formatMs(base * loops);
  }, [steps, loopsCount, loopsInfinite]);
  const rows = useMemo(() => buildRows(steps, ranges), [steps, ranges]);
  const rowIds = rows.map((row) => steps[row.index].id);
  const listRef = useRef<HTMLDivElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const flashTimersRef = useRef<Record<string, number>>({});
  const visualRunIdRef = useRef<number | null>(null);

  const scheduleMeasure = () => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      const list = listRef.current;
      if (!list) return;
      const listRect = list.getBoundingClientRect();
      const next = new Map<string, RowGeometry>();
      const nodes = list.querySelectorAll<HTMLElement>("[data-step-id]");
      nodes.forEach((node) => {
        const id = node.dataset.stepId;
        if (!id) return;
        const rect = node.getBoundingClientRect();
        next.set(id, { top: rect.top - listRect.top + list.scrollTop, bottom: rect.bottom - listRect.top + list.scrollTop });
      });
      setRowGeometry(next);
    });
  };

  useLayoutEffect(() => {
    scheduleMeasure();
    const list = listRef.current;
    if (!list) return;
    const onScroll = () => scheduleMeasure();
    list.addEventListener("scroll", onScroll, { passive: true });
    const observer = new ResizeObserver(() => scheduleMeasure());
    observer.observe(list);
    return () => {
      list.removeEventListener("scroll", onScroll);
      observer.disconnect();
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [rows.length, steps]);

  const railSegments: RailSegment[] = useMemo(() => {
    const segments: RailSegment[] = [];
    for (const [loopId, range] of ranges.entries()) {
      const startId = steps[range.startIndex]?.id;
      const endId = steps[range.endIndex]?.id;
      if (!startId || !endId) continue;
      const startGeo = rowGeometry.get(startId);
      const endGeo = rowGeometry.get(endId);
      if (!startGeo || !endGeo) continue;
      const y1 = startGeo.bottom;
      const y2 = endGeo.top;
      if (y2 > y1) segments.push({ id: loopId, y1, y2 });
    }
    return segments;
  }, [ranges, rowGeometry, steps]);

  useEffect(() => {
    if (!running || !listRef.current) return;
    if (!executingStepId) {
      if (typeof listRef.current.scrollTo === "function") {
        listRef.current.scrollTo({ top: 0, behavior: "smooth" });
      } else {
        listRef.current.scrollTop = 0;
      }
      return;
    }
    const row = listRef.current.querySelector(`[data-step-id="${executingStepId}"]`) as HTMLElement | null;
    if (!row) return;
    row.scrollIntoView({ block: "start", behavior: "smooth" });
  }, [running, executingStepId]);

  useEffect(() => {
    if (running) {
      setFlashByStepId({});
      setHeldStateByStepId({});
      Object.values(flashTimersRef.current).forEach((timer) => window.clearTimeout(timer));
      flashTimersRef.current = {};
      return;
    }
    setFlashByStepId({});
    setHeldStateByStepId({});
    visualRunIdRef.current = null;
    Object.values(flashTimersRef.current).forEach((timer) => window.clearTimeout(timer));
    flashTimersRef.current = {};
  }, [running]);

  useEffect(() => {
    return () => {
      Object.values(flashTimersRef.current).forEach((timer) => window.clearTimeout(timer));
    };
  }, []);

  useEffect(() => {
    if (!executionEvents?.length) return;
    const lastEvent = executionEvents[executionEvents.length - 1];
    if (visualRunIdRef.current !== lastEvent.run_id) {
      visualRunIdRef.current = lastEvent.run_id;
      setFlashByStepId({});
      setHeldStateByStepId({});
      Object.values(flashTimersRef.current).forEach((timer) => window.clearTimeout(timer));
      flashTimersRef.current = {};
    }
    const eventRow = listRef.current?.querySelector(`[data-step-id="${lastEvent.step_id}"]`) as HTMLElement | null;
    eventRow?.scrollIntoView?.({ block: "start", behavior: "smooth" });
    for (const event of executionEvents.filter((item) => item.run_id === visualRunIdRef.current)) {
      if (event.phase === "condition_waiting") {
        if (!running) continue;
        setHeldStateByStepId((current) => ({ ...current, [event.step_id]: "danger" }));
        continue;
      }
      if (event.phase === "condition_met") {
        setHeldStateByStepId((current) => {
          const next = { ...current };
          delete next[event.step_id];
          return next;
        });
      }
      const shouldFlash = event.phase === "step_complete" || event.phase === "loop_enter" || event.phase === "loop_exit" || event.phase === "loop_repeat";
      if (!shouldFlash) continue;
      const tone = event.phase === "loop_repeat" || (event.phase === "step_complete" && event.step_type === "wait") ? "warning" : "success";
      setFlashByStepId((current) => ({ ...current, [event.step_id]: tone }));
      if (flashTimersRef.current[event.step_id]) window.clearTimeout(flashTimersRef.current[event.step_id]);
      flashTimersRef.current[event.step_id] = window.setTimeout(() => {
        setFlashByStepId((current) => {
          const next = { ...current };
          delete next[event.step_id];
          return next;
        });
        delete flashTimersRef.current[event.step_id];
      }, 1800);
    }
  }, [executionEvents, running]);

  const onDragEnd = (event: DragEndEvent) => {
    if (!event.over || event.active.id === event.over.id) return;
    const fromIndex = steps.findIndex((step) => step.id === event.active.id);
    const toIndex = steps.findIndex((step) => step.id === event.over?.id);
    if (fromIndex < 0 || toIndex < 0) return;
    onStepsChange(moveBlock(steps, fromIndex, toIndex, ranges));
    scheduleMeasure();
  };

  const toggleCollapse = (rowStep: LoopStartStep) => onStepsChange(steps.map((step) => (step.id === rowStep.id ? { ...step, collapsed: !rowStep.collapsed } : step)));

  return (
    <CollapsibleSection
      className="sequence-builder-shell flex h-full min-h-0 flex-col"
      contentClassName="min-h-0 flex-1"
      title="Sequence Builder"
      actions={<div className="flex items-center gap-2"><SplitHotkeyActionButton tone={running ? "danger" : "success"} icon={running ? <Square size={16} /> : <RadioTower size={16} />} label={running ? "Stop sequence" : "Run sequence"} hotkey={runHotkey} onAction={onRunToggle} onHotkey={running ? onRunToggle : onRunHotkeyClick} /></div>}
    >
      <div className="flex min-h-0 h-full flex-1 flex-col overflow-hidden">
      <div className="mb-2 shrink-0 grid grid-cols-3 items-center gap-2 rounded-md bg-background/40 px-3 py-1.5 text-xs text-muted-foreground">
        <div>Actions: <span className="font-mono">{rows.length}</span></div>
        <div className="text-center">Approx: <span className="font-mono">{totalEstimate}</span></div>
        <div className="flex items-center justify-end gap-2">
          <span>Loops</span>
          <div className="relative">
            <Input className="h-7 w-24 pr-8" type="number" min={1} value={loopsInfinite ? "" : loopDraft} disabled={loopsInfinite} onChange={(event) => { const nextValue = event.target.value; setLoopDraft(nextValue); const parsed = Number(nextValue); if (Number.isFinite(parsed) && parsed >= 1) onLoopsChange(Math.floor(parsed), false); }} onBlur={() => { const parsed = Number(loopDraft); if (Number.isFinite(parsed) && parsed >= 1) { const safe = Math.floor(parsed); onLoopsChange(safe, false); setLoopDraft(String(safe)); } else setLoopDraft(String(loopsCount)); }} />
            <button className={`absolute right-1 top-1/2 -translate-y-1/2 rounded p-1 ${loopsInfinite ? "text-accent" : "text-muted-foreground hover:text-foreground"}`} onClick={() => onLoopsChange(loopsCount, !loopsInfinite)} title="Repeat indefinitely" type="button"><Infinity size={14} /></button>
          </div>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
        <SortableContext items={rowIds} strategy={verticalListSortingStrategy}>
          <div ref={listRef} className="relative h-full min-h-0 overflow-y-auto overflow-x-hidden pr-1">
            <div className="pointer-events-none absolute inset-0 z-0">
              {railSegments.map((segment) => <span key={segment.id} className="absolute w-px" style={{ left: "5%", top: `${segment.y1}px`, height: `${segment.y2 - segment.y1}px`, backgroundColor: "hsl(var(--loop-rail) / 0.75)" }} />)}
            </div>
            <div className="relative z-10 flex flex-col gap-2">
              {rows.map((row) => {
                const step = steps[row.index];
                const pixelSamplingAssist = Boolean(samplingPixelStepId) && (step.type === "click" || step.type === "move");
                const executing = executingStepId === step.id;
                const stateTone = executionStepStateTone(executing, executingStepState);
                return <SortableRow key={step.id} row={row} step={step} selected={executing || step.id === selectedId} stateTone={stateTone} flashTone={flashByStepId[step.id] ?? null} heldTone={heldStateByStepId[step.id] ?? null} selectedPixelLiveRgb={selectedPixelLiveRgb} pixelSamplingAssist={pixelSamplingAssist} onSelect={() => { if (pixelSamplingAssist && onSamplePixelFromClickStep) { void onSamplePixelFromClickStep(step.id); return; } onSelect(step.id); }} onToggleCollapse={toggleCollapse} />;
              })}
            </div>
          </div>
        </SortableContext>
      </DndContext>
      </div>
      </div>
    </CollapsibleSection>
  );
}
