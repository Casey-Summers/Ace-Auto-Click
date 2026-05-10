import { ChevronDown, ChevronUp, Crosshair, Grab, Keyboard, MousePointer, MousePointerClick, Timer } from "lucide-react";

import type { ActionStep } from "./types";

export function stepIcon(type: ActionStep["type"]) {
  if (type === "click") return <MousePointerClick size={16} />;
  if (type === "move") return <MousePointer size={16} />;
  if (type === "drag") return <Grab size={16} />;
  if (type === "wait") return <Timer size={16} />;
  if (type === "pixel_check") return <Crosshair size={16} />;
  if (type === "key_hold") return <Keyboard size={16} />;
  if (type === "loop_start") return <ChevronDown size={16} />;
  if (type === "loop_end") return <ChevronUp size={16} />;
  return <Keyboard size={16} />;
}

export function stepTitle(step: ActionStep) {
  if (step.type === "click") return `Click ${step.button} at ${step.x}, ${step.y}`;
  if (step.type === "move") return `Move to ${step.x}, ${step.y}`;
  if (step.type === "drag") return `Drag ${step.direction} ${step.length_px}px`;
  if (step.type === "wait") return `Wait ${step.ms}ms`;
  if (step.type === "pixel_check") return `Pixel Match ${step.x}, ${step.y}`;
  if (step.type === "key_hold") return `Hold ${step.key} for ${step.hold_ms}ms`;
  if (step.type === "loop_start") return step.loop_infinite ? "Loop start (infinite)" : `Loop start (${step.loop_count}x)`;
  if (step.type === "loop_end") return "Loop end";
  return `Tap ${step.key}`;
}

export function createStep(type: ActionStep["type"]): ActionStep {
  const id = `step-${type}-${Date.now()}`;
  const base = { id, enabled: true, repeats: 1, interval_ms: 100, randomness_ms: 0 };
  if (type === "loop_start") {
    return { ...base, type, loop_id: `loop-${Date.now()}`, loop_count: 1, loop_infinite: false, collapsed: false };
  }
  if (type === "loop_end") {
    return { ...base, type, loop_id: `loop-${Date.now()}` };
  }
  if (type === "click") {
    return { ...base, type, x: 0, y: 0, button: "left", clicks: 1, random_offset: 0 };
  }
  if (type === "move") {
    return { ...base, type, x: 0, y: 0, random_offset: 0 };
  }
  if (type === "drag") {
    return { ...base, type, x: 0, y: 0, buttons: ["left", "right"], direction: "right", length_px: 100, speed: 500, acceleration: 1.6, random_offset: 0 };
  }
  if (type === "wait") {
    return { ...base, type, ms: 1000, random_ms: 0 };
  }
  if (type === "pixel_check") {
    return {
      ...base,
      type,
      x: 0,
      y: 0,
      expected_rgb: [255, 255, 255],
      tolerance: 10,
      mode: "wait_until_match"
    };
  }
  if (type === "key_hold") {
    return { ...base, type, key: "space", hold_ms: 300 };
  }
  return { ...base, type, key: "space" };
}
