import { displayKeybind } from "./keybinds";
import type { ActionStep, LoopStartStep, Rgb, RuntimeState } from "./types";

export type LoopRange = { startIndex: number; endIndex: number; depth: number };
export type Timing = { baseMs: number; randomMs: number };
export type RowSummary = { title: string; subtext: string; pixelComparison?: { current: Rgb | null; expected: Rgb; matches: boolean } };

export function formatMs(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(ms >= 10000 ? 0 : 1)}s`;
}

export function loopDisplayCount(step: LoopStartStep): number {
  return Math.max(1, step.loop_count, step.repeats);
}

export function stepTitle(step: ActionStep): string {
  if (step.type === "click") return `Click ${step.button} at ${step.x}, ${step.y}`;
  if (step.type === "move") return `${step.movement_mode === "smooth" ? "Smooth move" : "Move"} to ${step.x}, ${step.y}`;
  if (step.type === "drag") return `Drag ${step.direction} ${step.length_px}px`;
  if (step.type === "wait") return `Wait ${step.ms}ms`;
  if (step.type === "pixel_check") return `Pixel Match ${step.x}, ${step.y}`;
  if (step.type === "key_hold") return `Hold ${displayKeybind(step.key)} for ${step.hold_ms}ms`;
  if (step.type === "loop_start") return step.loop_infinite ? "Loop start (infinite)" : `Loop start (${step.loop_count}x)`;
  if (step.type === "loop_end") return "Loop end";
  return `Tap ${displayKeybind(step.key)}`;
}

export function stepSummary(step: ActionStep, selectedPixelLiveRgb?: Rgb | null, selected = false): RowSummary {
  if (step.type === "click") {
    const parts: string[] = [];
    if (step.repeats !== 1) parts.push(`repeats ${step.repeats}`);
    if (step.interval_ms !== 100 || step.randomness_ms !== 0) parts.push(`pre-delay ${formatMs(step.interval_ms)}${step.randomness_ms > 0 ? ` +- ${formatMs(step.randomness_ms)}` : ""}`);
    if (step.clicks !== 1) parts.push(`clicks ${step.clicks}`);
    if (step.random_offset > 0) parts.push(`position +- ${step.random_offset}px`);
    return { title: `Click ${step.button.charAt(0).toUpperCase()}${step.button.slice(1)} at ${step.x}, ${step.y}`, subtext: parts.join(" / ") };
  }
  if (step.type === "move") {
    const parts: string[] = [];
    if (step.repeats !== 1) parts.push(`repeats ${step.repeats}`);
    if (step.interval_ms !== 100 || step.randomness_ms !== 0) parts.push(`pre-delay ${formatMs(step.interval_ms)}${step.randomness_ms > 0 ? ` +- ${formatMs(step.randomness_ms)}` : ""}`);
    if (step.movement_mode === "smooth") {
      parts.push(step.movement_duration_ms > 0 ? `smooth ${formatMs(step.movement_duration_ms)}` : "smooth auto");
      if (step.movement_smoothness !== 70) parts.push(`smoothness ${step.movement_smoothness}`);
      if (step.path_randomness !== 20) parts.push(`path random ${step.path_randomness}`);
    } else if (step.random_offset > 0) {
      parts.push(`position +- ${step.random_offset}px`);
    }
    return { title: `${step.movement_mode === "smooth" ? "Smooth move" : "Move"} to ${step.x}, ${step.y}`, subtext: parts.join(" / ") };
  }
  if (step.type === "drag") {
    const parts: string[] = [];
    if (step.repeats !== 1) parts.push(`repeats ${step.repeats}`);
    if (step.speed !== 500) parts.push(`speed ${step.speed}px/s`);
    if (step.interval_ms !== 100 || step.randomness_ms !== 0) parts.push(`pre-delay ${formatMs(step.interval_ms)}${step.randomness_ms > 0 ? ` +- ${formatMs(step.randomness_ms)}` : ""}`);
    if (step.random_offset > 0) parts.push(`position +- ${step.random_offset}px`);
    return { title: `Drag ${step.direction} ${step.length_px}px`, subtext: parts.join(" / ") };
  }
  if (step.type === "wait") {
    const parts: string[] = [];
    if (step.repeats !== 1) parts.push(`repeats ${step.repeats}`);
    if (step.interval_ms !== 100 || step.randomness_ms !== 0) parts.push(`pre-delay ${formatMs(step.interval_ms)}${step.randomness_ms > 0 ? ` +- ${formatMs(step.randomness_ms)}` : ""}`);
    if (step.random_ms !== 0) parts.push(`wait jitter +- ${formatMs(step.random_ms)}`);
    return { title: `Wait ${formatMs(step.ms)}${step.random_ms > 0 ? ` +- ${formatMs(step.random_ms)}` : ""}`, subtext: parts.join(" / ") };
  }
  if (step.type === "pixel_check") {
    const matches = selected && selectedPixelLiveRgb ? Math.max(...selectedPixelLiveRgb.map((value, index) => Math.abs(value - step.expected_rgb[index]))) <= step.tolerance : false;
    const parts: string[] = [];
    if (step.repeats !== 1) parts.push(`repeats ${step.repeats}`);
    if (step.interval_ms !== 100 || step.randomness_ms !== 0) parts.push(`pre-delay ${formatMs(step.interval_ms)}${step.randomness_ms > 0 ? ` +- ${formatMs(step.randomness_ms)}` : ""}`);
    if (step.mode !== "wait_until_match") parts.push(step.mode.replace(/_/g, " "));
    if (step.tolerance !== 10) parts.push(`tol ${step.tolerance}`);
    return { title: "Pixel Match", subtext: parts.join(" / "), pixelComparison: { current: selected && selectedPixelLiveRgb ? selectedPixelLiveRgb : null, expected: step.expected_rgb, matches } };
  }
  if (step.type === "key_tap") {
    const parts: string[] = [];
    if (step.repeats !== 1) parts.push(`repeats ${step.repeats}`);
    if (step.interval_ms !== 100 || step.randomness_ms !== 0) parts.push(`pre-delay ${formatMs(step.interval_ms)}${step.randomness_ms > 0 ? ` +- ${formatMs(step.randomness_ms)}` : ""}`);
    return { title: `Tap ${displayKeybind(step.key)}`, subtext: parts.join(" / ") };
  }
  if (step.type === "key_hold") {
    const parts: string[] = [];
    if (step.repeats !== 1) parts.push(`repeats ${step.repeats}`);
    if (step.interval_ms !== 100 || step.randomness_ms !== 0) parts.push(`pre-delay ${formatMs(step.interval_ms)}${step.randomness_ms > 0 ? ` +- ${formatMs(step.randomness_ms)}` : ""}`);
    return { title: `Hold ${displayKeybind(step.key)} for ${formatMs(step.hold_ms)}`, subtext: parts.join(" / ") };
  }
  if (step.type === "loop_start") return { title: step.loop_infinite ? "Loop Start infinite" : `Loop Start x${loopDisplayCount(step)}`, subtext: "" };
  return { title: "Loop End", subtext: "" };
}

export function estimateStepTiming(step: ActionStep): Timing {
  const repeats = Math.max(1, step.repeats);
  if (step.type === "wait") return { baseMs: (step.ms + step.interval_ms) * repeats, randomMs: (step.random_ms + step.randomness_ms) * repeats };
  if (step.type === "loop_end") return { baseMs: 0, randomMs: 0 };
  return { baseMs: step.interval_ms * repeats, randomMs: step.randomness_ms * repeats };
}

export function sumTiming(steps: ActionStep[]): Timing {
  return steps.reduce((sum, step) => {
    const timing = estimateStepTiming(step);
    return { baseMs: sum.baseMs + timing.baseMs, randomMs: sum.randomMs + timing.randomMs };
  }, { baseMs: 0, randomMs: 0 });
}

export function resolveLoops(steps: ActionStep[]): Map<string, LoopRange> {
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
      if (!open || open.loopId !== step.loop_id) continue;
      ranges.set(step.loop_id, { startIndex: open.index, endIndex: index, depth: open.depth });
    }
  }
  return ranges;
}

export function executionStepStateTone(executing: boolean, executingStepState?: RuntimeState["current_step_state"] | null) {
  return !executing ? "info" : executingStepState === "condition_false" ? "danger" : executingStepState === "waiting" ? "warning" : "success";
}
