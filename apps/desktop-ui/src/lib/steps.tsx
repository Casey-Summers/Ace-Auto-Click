import { Crosshair, Keyboard, MousePointerClick, Timer } from "lucide-react";

import type { ActionStep } from "./types";

export function stepIcon(type: ActionStep["type"]) {
  if (type === "click") return <MousePointerClick size={16} />;
  if (type === "wait") return <Timer size={16} />;
  if (type === "pixel_check") return <Crosshair size={16} />;
  return <Keyboard size={16} />;
}

export function stepTitle(step: ActionStep) {
  if (step.type === "click") return `Click ${step.button} at ${step.x}, ${step.y}`;
  if (step.type === "wait") return `Wait ${step.ms}ms`;
  if (step.type === "pixel_check") return `Pixel ${step.x}, ${step.y}`;
  return `Tap ${step.key}`;
}

export function createStep(type: ActionStep["type"]): ActionStep {
  const id = `step-${type}-${Date.now()}`;
  const base = { id, enabled: true, repeats: 1, interval_ms: 100, randomness_ms: 0 };
  if (type === "click") {
    return { ...base, type, x: 0, y: 0, button: "left", clicks: 1, random_offset: 0 };
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
  return { ...base, type, key: "space" };
}
