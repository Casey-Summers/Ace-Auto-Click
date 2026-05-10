import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SequenceBuilder } from "./SequenceBuilder";
import type { ActionStep, ExecutionEvent } from "../../lib/types";

const baseStep = {
  enabled: true,
  repeats: 1,
  interval_ms: 0,
  randomness_ms: 0
};

const steps: ActionStep[] = [
  { ...baseStep, id: "loop-start", type: "loop_start", loop_id: "loop-a", loop_count: 1, loop_infinite: false, collapsed: false },
  { ...baseStep, id: "click-1", type: "click", x: 10, y: 20, button: "left", clicks: 1, random_offset: 0 },
  { ...baseStep, id: "wait-1", type: "wait", ms: 100, random_ms: 0 },
  { ...baseStep, id: "pixel-1", type: "pixel_check", x: 10, y: 20, expected_rgb: [255, 255, 255], tolerance: 10, mode: "wait_until_match" },
  { ...baseStep, id: "loop-end", type: "loop_end", loop_id: "loop-a" }
];

function event(step_id: string, phase: ExecutionEvent["phase"], sequence_no = 1): ExecutionEvent {
  const step = steps.find((item) => item.id === step_id);
  return {
    step_id,
    step_type: step?.type ?? "click",
    phase,
    run_id: 1,
    sequence_no,
    ts_ms: sequence_no
  };
}

function renderBuilder(executionEvents: ExecutionEvent[]) {
  return render(
    <SequenceBuilder
      steps={steps}
      loops={1}
      loopsCount={1}
      loopsInfinite={false}
      running
      runHotkey="F8"
      selectedId=""
      executionEvents={executionEvents}
      onSelect={vi.fn()}
      onLoopsChange={vi.fn()}
      onRunToggle={vi.fn()}
      onStepsChange={vi.fn()}
      onRunHotkeyClick={vi.fn()}
    />
  );
}

function row(container: HTMLElement, stepId: string): HTMLElement {
  const node = container.querySelector(`[data-step-id="${stepId}"] > div`);
  if (!(node instanceof HTMLElement)) throw new Error(`Missing row for ${stepId}`);
  return node;
}

describe("SequenceBuilder execution flashes", () => {
  it("uses a bounded scroll viewport structure for rows", () => {
    const { container } = renderBuilder([]);
    const clipper = container.querySelector(".min-h-0.flex-1.overflow-hidden");
    const scroller = container.querySelector(".overflow-y-auto.overflow-x-hidden");
    expect(clipper).toBeTruthy();
    expect(scroller).toBeTruthy();
  });

  it("renders sanitized keybind row titles", () => {
    render(
      <SequenceBuilder
        steps={[
          { ...baseStep, id: "tap-1", type: "key_tap", key: "btnm4" },
          { ...baseStep, id: "hold-1", type: "key_hold", key: "\x01", hold_ms: 1500 }
        ]}
        loops={1}
        loopsCount={1}
        loopsInfinite={false}
        running={false}
        runHotkey="F8"
        selectedId=""
        executionEvents={[]}
        onSelect={vi.fn()}
        onLoopsChange={vi.fn()}
        onRunToggle={vi.fn()}
        onStepsChange={vi.fn()}
        onRunHotkeyClick={vi.fn()}
      />
    );

    expect(screen.getByText("Tap BTNM 4")).toBeInTheDocument();
    expect(screen.getByText("Hold Unset for 1.5s")).toBeInTheDocument();
  });

  it("success-flashes a row from a step completion event", async () => {
    const { container } = renderBuilder([event("click-1", "step_complete")]);

    await waitFor(() => expect(row(container, "click-1")).toHaveClass("step-fade-success"));
  });

  it("warning-flashes loop end from loop repeat event", async () => {
    const { container } = renderBuilder([event("loop-end", "loop_repeat")]);

    await waitFor(() => expect(row(container, "loop-end")).toHaveClass("step-fade-warning"));
  });

  it("warning-flashes wait rows from completion events", async () => {
    const { container } = renderBuilder([event("wait-1", "step_complete")]);

    await waitFor(() => expect(row(container, "wait-1")).toHaveClass("step-fade-warning"));
  });

  it("holds danger while a pixel condition waits and clears it when met", async () => {
    const { container, rerender } = renderBuilder([event("pixel-1", "condition_waiting")]);

    await waitFor(() => expect(row(container, "pixel-1").className).toContain("border-danger"));

    rerender(
      <SequenceBuilder
        steps={steps}
        loops={1}
        loopsCount={1}
        loopsInfinite={false}
        running
        runHotkey="F8"
        selectedId=""
        executionEvents={[event("pixel-1", "condition_met", 2), event("pixel-1", "step_complete", 3)]}
        onSelect={vi.fn()}
        onLoopsChange={vi.fn()}
        onRunToggle={vi.fn()}
        onStepsChange={vi.fn()}
        onRunHotkeyClick={vi.fn()}
      />
    );

    await waitFor(() => expect(row(container, "pixel-1").className).not.toContain("border-danger"));
    expect(row(container, "pixel-1")).toHaveClass("step-fade-success");
  });
});
