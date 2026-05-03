import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./app";
import { defaultSettings } from "./lib/defaults";

const apiMock = vi.hoisted(() => ({
  getSettings: vi.fn(),
  getState: vi.fn(),
  runSequence: vi.fn(),
  stop: vi.fn(),
  emergencyStop: vi.fn(),
  saveSettings: vi.fn(),
  mousePosition: vi.fn(),
  pixel: vi.fn()
}));

vi.mock("./lib/api", () => ({ api: apiMock }));

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.getSettings.mockResolvedValue(defaultSettings);
    apiMock.getState.mockResolvedValue({
      product_name: "Ace Auto Click",
      running: false,
      recording: false,
      status: "Idle",
      last_error: null
    });
    apiMock.runSequence.mockResolvedValue({ state: { product_name: "Ace Auto Click", running: true, recording: false, status: "Running", last_error: null } });
    apiMock.emergencyStop.mockResolvedValue({ state: { product_name: "Ace Auto Click", running: false, recording: false, status: "Emergency stop", last_error: null } });
    apiMock.saveSettings.mockImplementation(async (settings) => settings);
    apiMock.mousePosition.mockResolvedValue({ x: 25, y: 50 });
  });

  it("renders the refined workspace without forbidden shortcut behavior", async () => {
    render(<App />);

    expect(screen.getByText("Ace Auto Click")).toBeInTheDocument();
    expect(screen.getByText("normal")).toBeInTheDocument();
    expect(screen.getByText("advanced")).toBeInTheDocument();
    expect(screen.getByText("Action Library")).toBeInTheDocument();
    expect(screen.getByText("Runtime")).toBeInTheDocument();
    expect(screen.getByText("Emergency stop")).toBeInTheDocument();
    expect(screen.queryByText(/palette/i)).not.toBeInTheDocument();

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(screen.queryByText(/palette/i)).not.toBeInTheDocument();
    await screen.findByText(/Connected to Ace Auto Click/);
  });

  it("opens settings from the emergency keybind segment while idle", async () => {
    render(<App />);

    fireEvent.click(screen.getByLabelText("Edit emergency stop hotkey"));

    expect(await screen.findByText("Keybinds")).toBeInTheDocument();
    expect(screen.getByLabelText(/Emergency stop/i)).toBeInTheDocument();
  });

  it("uses emergency stop when the emergency segment is clicked while running", async () => {
    apiMock.getState.mockResolvedValue({
      product_name: "Ace Auto Click",
      running: true,
      recording: false,
      status: "Running",
      last_error: null
    });
    render(<App />);

    fireEvent.click(await screen.findByLabelText("Trigger emergency stop hotkey"));

    expect(apiMock.emergencyStop).toHaveBeenCalled();
  });

  it("sends the profile loop count when running a sequence", async () => {
    render(<App />);

    const loops = screen.getByLabelText(/Loops/i);
    fireEvent.change(loops, { target: { value: "3" } });
    fireEvent.click(screen.getByText("Run sequence"));

    await waitFor(() => expect(apiMock.runSequence).toHaveBeenCalled());
    expect(apiMock.runSequence.mock.calls[0][1]).toBe(3);
  });

  it("collapses and expands sections", () => {
    render(<App />);

    fireEvent.click(screen.getByText("Action Library"));
    expect(screen.queryByText("Pixel check")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Action Library"));
    expect(screen.getByText("Pixel check")).toBeInTheDocument();
  });
});
