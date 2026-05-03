import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./app";

vi.mock("./lib/api", () => ({
  api: {
    getSettings: vi.fn().mockRejectedValue(new Error("offline")),
    getState: vi.fn().mockRejectedValue(new Error("offline")),
    runSimple: vi.fn(),
    runSequence: vi.fn(),
    stop: vi.fn(),
    emergencyStop: vi.fn(),
    saveSettings: vi.fn(),
    mousePosition: vi.fn(),
    pixel: vi.fn()
  }
}));

describe("App", () => {
  it("renders the Ace Auto Click workspace", () => {
    render(<App />);

    expect(screen.getByText("Ace Auto Click")).toBeInTheDocument();
    expect(screen.getByText("Action Library")).toBeInTheDocument();
    expect(screen.getByText("Sequence Builder")).toBeInTheDocument();
    expect(screen.getByText("Emergency stop")).toBeInTheDocument();
    expect(screen.getByText("Click left at 500, 500")).toBeInTheDocument();
  });

  it("shows a disconnected state when the backend is unavailable", async () => {
    render(<App />);

    expect(await screen.findByText(/API unavailable: offline/)).toBeInTheDocument();
  });
});
