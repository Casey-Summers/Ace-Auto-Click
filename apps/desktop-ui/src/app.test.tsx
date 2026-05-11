import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./app";
import { defaultSettings } from "./lib/defaults";
import { normalizeSettings } from "./lib/settings";
import { createStep } from "./lib/steps";

const apiMock = vi.hoisted(() => ({
  getSettings: vi.fn(),
  getState: vi.fn(),
  executionEvents: vi.fn(),
  runToggle: vi.fn(),
  stop: vi.fn(),
  emergencyStop: vi.fn(),
  saveSettings: vi.fn(),
  listProfiles: vi.fn(),
  profileStatus: vi.fn(),
  saveProfile: vi.fn(),
  loadProfile: vi.fn(),
  openProfilesFolder: vi.fn(),
  mousePosition: vi.fn(),
  pickClickPosition: vi.fn(),
  startMouseClickCapture: vi.fn(),
  startKeyPressCapture: vi.fn(),
  inputCaptureStatus: vi.fn(),
  cancelInputCapture: vi.fn(),
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
    apiMock.runToggle.mockResolvedValue({ state: { product_name: "Ace Auto Click", running: true, recording: false, status: "Running", last_error: null } });
    apiMock.executionEvents.mockResolvedValue([]);
    apiMock.emergencyStop.mockResolvedValue({ state: { product_name: "Ace Auto Click", running: false, recording: false, status: "Emergency stop", last_error: null } });
    apiMock.saveSettings.mockImplementation(async (settings) => settings);
    apiMock.listProfiles.mockResolvedValue([]);
    apiMock.profileStatus.mockResolvedValue({ path: "profiles", available: true, file_count: 0 });
    apiMock.saveProfile.mockResolvedValue({ file_name: "Default-Profile.aceprofile.json", profile_name: "Default Profile", modified_at: "2026-05-04T00:00:00Z", size: 100 });
    apiMock.loadProfile.mockResolvedValue(defaultSettings);
    apiMock.openProfilesFolder.mockResolvedValue({ message: "Profiles folder opened." });
    apiMock.mousePosition.mockResolvedValue({ x: 25, y: 50 });
    apiMock.pickClickPosition.mockResolvedValue({ x: 77, y: 88 });
    apiMock.startMouseClickCapture.mockResolvedValue({ id: "capture-1", status: "pending", result: null, error: null });
    apiMock.startKeyPressCapture.mockResolvedValue({ id: "capture-key-1", status: "pending", result: null, error: null });
    apiMock.inputCaptureStatus.mockResolvedValue({ id: "capture-1", status: "complete", result: { kind: "mouse_click", x: 77, y: 88, button: "Button.left" }, error: null });
    apiMock.cancelInputCapture.mockResolvedValue({ id: "capture-1", status: "cancelled", result: null, error: "Input capture cancelled." });
  });

  it("renders the refined workspace without forbidden shortcut behavior", async () => {
    render(<App />);

    expect(screen.getByText("Ace Auto Click")).toBeInTheDocument();
    expect(screen.getByText("normal")).toBeInTheDocument();
    expect(screen.getByText("advanced")).toBeInTheDocument();
    expect(screen.getByText("Action Library")).toBeInTheDocument();
    expect(screen.getByText("Keybind Tap")).toBeInTheDocument();
    expect(screen.getByText("Keybind Hold")).toBeInTheDocument();
    expect(screen.getByText("Action Settings")).toBeInTheDocument();
    expect(screen.queryByText("Selected Step")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Profile name")).toBeInTheDocument();
    expect(screen.queryByText("Runtime")).not.toBeInTheDocument();
    expect(screen.getByText("Emergency stop")).toBeInTheDocument();
    expect(screen.queryByText(/palette/i)).not.toBeInTheDocument();

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(screen.queryByText(/palette/i)).not.toBeInTheDocument();
    await screen.findByText(/Connected to Ace Auto Click/);
  });

  it("opens settings from the emergency keybind segment while idle", async () => {
    render(<App />);

    fireEvent.click(screen.getByText("Emergency stop"));

    expect(apiMock.emergencyStop).toHaveBeenCalled();
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

    fireEvent.click(await screen.findByText("Emergency stop"));

    expect(apiMock.emergencyStop).toHaveBeenCalled();
  });

  it("toggles run through the backend without rebuilding the payload locally", async () => {
    render(<App />);

    fireEvent.click(screen.getByText("Run sequence"));

    await waitFor(() => expect(apiMock.runToggle).toHaveBeenCalled());
  });

  it("captures a new keybind reactively", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /^Settings$/i }));
    fireEvent.click(await screen.findByRole("button", { name: "Keybinds" }));
    fireEvent.click(screen.getAllByText("Click to change")[0]);
    expect(screen.getByText("Press a key...")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "F9" });
    await waitFor(() => expect(screen.getAllByText("F9").length).toBeGreaterThan(0));
  });

  it("saves the active profile through the Profile Manager", async () => {
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /^Save$/i }));
    expect(await screen.findByRole("dialog", { name: "Save profile" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Confirm Save/i }));

    await waitFor(() => expect(apiMock.saveProfile).toHaveBeenCalled());
    expect(apiMock.listProfiles).toHaveBeenCalled();
  });

  it("keeps settings and runtime usable when profile endpoints are unavailable", async () => {
    apiMock.listProfiles.mockRejectedValue(new Error('{"detail":"Not Found"}'));
    apiMock.profileStatus.mockRejectedValue(new Error('{"detail":"Not Found"}'));

    render(<App />);

    expect(await screen.findByText(/Connected to Ace Auto Click/)).toBeInTheDocument();
    expect(await screen.findByText("Profile API unavailable. Restart the app backend.")).toBeInTheDocument();
  });

  it("collapses and expands sections", () => {
    render(<App />);

    fireEvent.click(screen.getByText("Action Library"));
    expect(screen.queryByText("Pixel Match")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Action Library"));
    expect(screen.getByText("Pixel Match")).toBeInTheDocument();
  });

  it("updates a click action from the position picker", async () => {
    render(<App />);
    await screen.findByText(/Connected to Ace Auto Click/);

    fireEvent.click(screen.getByRole("button", { name: "Pick Click Position" }));

    await waitFor(() => expect(apiMock.startMouseClickCapture).toHaveBeenCalled());
    await waitFor(() => expect(apiMock.inputCaptureStatus).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByDisplayValue("77")).toBeInTheDocument());
    expect(screen.getByDisplayValue("88")).toBeInTheDocument();
  });

  it("shows action details and live cursor coordinates while picking", async () => {
    apiMock.mousePosition.mockResolvedValue({ x: 11, y: 22 });
    apiMock.startMouseClickCapture.mockImplementation(() => new Promise(() => undefined));

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Pick Click Position" }));

    await waitFor(() => expect(apiMock.mousePosition).toHaveBeenCalled());
  });

  it("keeps action details hidden when no action detail is active", () => {
    render(<App />);

    expect(screen.queryByText("Action Details")).not.toBeInTheDocument();
  });

  it("previews pixel match from saved coordinates instead of cursor position", async () => {
    apiMock.mousePosition.mockResolvedValue({ x: 999, y: 888 });
    apiMock.pixel.mockResolvedValue({ x: 10, y: 20, rgb: [12, 34, 56] });
    apiMock.getSettings.mockResolvedValue({
      ...defaultSettings,
      profiles: [{
        ...defaultSettings.profiles[0],
        steps: [{
          id: "step-click-1",
          type: "pixel_check",
          enabled: true,
          repeats: 1,
          interval_ms: 100,
          randomness_ms: 0,
          x: 10,
          y: 20,
          expected_rgb: [255, 255, 255],
          tolerance: 10,
          mode: "wait_until_match"
        }]
      }]
    });

    render(<App />);

    await waitFor(() => expect(apiMock.pixel).toHaveBeenCalledWith(10, 20));
    expect(apiMock.pixel).not.toHaveBeenCalledWith(999, 888);
    expect(await screen.findByText("RGB 12, 34, 56")).toBeInTheDocument();
  });

  it("edits pixel match coordinates directly", async () => {
    apiMock.pixel.mockResolvedValue({ x: 10, y: 20, rgb: [12, 34, 56] });
    apiMock.getSettings.mockResolvedValue({
      ...defaultSettings,
      profiles: [{
        ...defaultSettings.profiles[0],
        steps: [{
          id: "step-click-1",
          type: "pixel_check",
          enabled: true,
          repeats: 1,
          interval_ms: 100,
          randomness_ms: 0,
          x: 10,
          y: 20,
          expected_rgb: [255, 255, 255],
          tolerance: 10,
          mode: "wait_until_match"
        }]
      }]
    });

    render(<App />);
    await screen.findByText("Pixel X");

    fireEvent.change(screen.getByLabelText("Pixel X"), { target: { value: "123" } });
    fireEvent.change(screen.getByLabelText("Pixel Y"), { target: { value: "456" } });

    expect(screen.getByDisplayValue("123")).toBeInTheDocument();
    expect(screen.getByDisplayValue("456")).toBeInTheDocument();
  });

  it("keeps pixel match preview fixed to sampled coordinates after the mouse moves", async () => {
    apiMock.mousePosition.mockResolvedValue({ x: 999, y: 888 });
    apiMock.startMouseClickCapture.mockResolvedValue({ id: "capture-1", status: "pending", result: null, error: null });
    apiMock.inputCaptureStatus.mockResolvedValue({ id: "capture-1", status: "complete", result: { kind: "mouse_click", x: 77, y: 88, button: "Button.left" }, error: null });
    apiMock.pixel.mockImplementation(async (x: number, y: number) => {
      if (x === 77 && y === 88) return { x, y, rgb: [77, 88, 99] };
      if (x === 10 && y === 20) return { x, y, rgb: [10, 20, 30] };
      return { x, y, rgb: [1, 2, 3] };
    });
    apiMock.getSettings.mockResolvedValue({
      ...defaultSettings,
      profiles: [{
        ...defaultSettings.profiles[0],
        steps: [{
          id: "step-click-1",
          type: "pixel_check",
          enabled: true,
          repeats: 1,
          interval_ms: 100,
          randomness_ms: 0,
          x: 10,
          y: 20,
          expected_rgb: [255, 255, 255],
          tolerance: 10,
          mode: "wait_until_match"
        }]
      }]
    });

    render(<App />);
    await waitFor(() => expect(apiMock.pixel).toHaveBeenCalledWith(10, 20));
    fireEvent.click(await screen.findByRole("button", { name: "Sample Pixel" }));

    await waitFor(() => expect(screen.getByLabelText("Pixel X")).toHaveValue(77));
    expect(screen.getByLabelText("Pixel Y")).toHaveValue(88);
    await waitFor(() => expect(apiMock.pixel).toHaveBeenCalledWith(77, 88));
    expect(apiMock.pixel).not.toHaveBeenCalledWith(999, 888);
    expect(await screen.findAllByText("RGB 77, 88, 99")).not.toHaveLength(0);
  });

  it("does not contain cursor-derived pixel match preview reads", () => {
    const activeController = readFileSync("src/hooks/useAppController.ts", "utf8");
    const acecaseController = readFileSync("src/hooks/useAppController-Acecase.ts", "utf8");
    const cursorDerivedPreviewPattern = /selectedStep\?\.type === "pixel_check"[\s\S]{0,160}api\.pixel\(position\.x, position\.y\)/;

    expect(activeController).not.toMatch(cursorDerivedPreviewPattern);
    expect(acecaseController).not.toMatch(cursorDerivedPreviewPattern);
    expect(activeController).not.toContain("api.pixel(position.x, position.y)");
    expect(acecaseController).not.toContain("api.pixel(position.x, position.y)");
  });

  it("clears picker state after a cancelled position picker", async () => {
    apiMock.startMouseClickCapture.mockResolvedValue({ id: "capture-1", status: "pending", result: null, error: null });
    apiMock.inputCaptureStatus.mockResolvedValue({ id: "capture-1", status: "cancelled", result: null, error: "Input capture cancelled." });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Pick Click Position" }));

    await waitFor(() => expect(screen.getByRole("button", { name: "Pick Click Position" })).toBeEnabled());
    expect(await screen.findByText("Position picker cancelled.")).toBeInTheDocument();
  });

  it("cancels a position picker with Escape", async () => {
    apiMock.startMouseClickCapture.mockResolvedValue({ id: "capture-1", status: "pending", result: null, error: null });
    apiMock.inputCaptureStatus.mockImplementation(async (id: string) => ({ id, status: "pending", result: null, error: null }));

    render(<App />);
    await screen.findByText(/Connected to Ace Auto Click/);
    fireEvent.click(screen.getByRole("button", { name: "Pick Click Position" }));

    expect(await screen.findByText("Esc cancels")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Waiting for input" })).toBeDisabled();
    fireEvent.keyDown(window, { key: "Escape" });

    await waitFor(() => expect(apiMock.cancelInputCapture).toHaveBeenCalledWith("capture-1"));
    expect(await screen.findByText("Position picker cancelled.")).toBeInTheDocument();
  });

  it("shows current keybind inside the capture button for keybind actions", async () => {
    render(<App />);
    await screen.findByText(/Connected to Ace Auto Click/);
    fireEvent.click(screen.getByRole("button", { name: /Keybind Tap/i }));
    expect(screen.getByRole("button", { name: /Change keybind, current SPACE/i })).toBeInTheDocument();
    expect(screen.getByText("SPACE")).toBeInTheDocument();
    expect(screen.queryByText(/Capture Key Input/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Key preview:/i)).not.toBeInTheDocument();
  });

  it("keeps keybind hold preview inside the capture button", async () => {
    render(<App />);
    await screen.findByText(/Connected to Ace Auto Click/);
    fireEvent.click(screen.getByRole("button", { name: /Keybind Hold/i }));
    expect(screen.getByRole("button", { name: /Change keybind, current SPACE/i })).toBeInTheDocument();
    expect(screen.queryByText(/Key preview:/i)).not.toBeInTheDocument();
  });

  it("shows pending state while action key capture waits and updates after completion", async () => {
    apiMock.startKeyPressCapture.mockResolvedValue({ id: "capture-key-1", status: "pending", result: null, error: null });
    apiMock.inputCaptureStatus
      .mockResolvedValueOnce({ id: "capture-key-1", status: "pending", result: null, error: null })
      .mockResolvedValue({ id: "capture-key-1", status: "complete", result: { kind: "key_press", key: "ctrl+a" }, error: null });

    render(<App />);
    await screen.findByText(/Connected to Ace Auto Click/);
    fireEvent.click(screen.getByRole("button", { name: /Keybind Tap/i }));
    fireEvent.click(screen.getByRole("button", { name: /Change keybind, current SPACE/i }));

    expect(await screen.findByText("Press key or side button...")).toBeInTheDocument();
    expect(screen.getByText("Click again to cancel")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: /Change keybind, current CTRL \+ A/i })).toBeInTheDocument());
    expect(screen.getByText("CTRL + A")).toBeInTheDocument();
  });

  it("captures Escape as a keybind without cancelling as a position picker", async () => {
    apiMock.startKeyPressCapture.mockResolvedValue({ id: "capture-key-1", status: "pending", result: null, error: null });
    apiMock.inputCaptureStatus.mockResolvedValue({ id: "capture-key-1", status: "complete", result: { kind: "key_press", key: "esc" }, error: null });

    render(<App />);
    await screen.findByText(/Connected to Ace Auto Click/);
    fireEvent.click(screen.getByRole("button", { name: /Keybind Tap/i }));
    fireEvent.click(screen.getByRole("button", { name: /Change keybind, current SPACE/i }));
    fireEvent.keyDown(window, { key: "Escape" });

    await waitFor(() => expect(screen.getByRole("button", { name: /Change keybind, current ESC/i })).toBeInTheDocument());
    expect(screen.getByText("Captured keybind ESC.")).toBeInTheDocument();
    expect(screen.queryByText("Position picker cancelled.")).not.toBeInTheDocument();
  });

  it("cancels a pending keybind capture by clicking the button again", async () => {
    apiMock.startKeyPressCapture.mockResolvedValue({ id: "capture-key-1", status: "pending", result: null, error: null });
    apiMock.inputCaptureStatus.mockImplementation(async (id: string) => ({ id, status: "pending", result: null, error: null }));

    render(<App />);
    await screen.findByText(/Connected to Ace Auto Click/);
    fireEvent.click(screen.getByRole("button", { name: /Keybind Tap/i }));
    fireEvent.click(screen.getByRole("button", { name: /Change keybind, current SPACE/i }));

    const pendingButton = await screen.findByRole("button", { name: /Press key or side button/i });
    expect(pendingButton).toBeEnabled();
    fireEvent.click(pendingButton);

    await waitFor(() => expect(apiMock.cancelInputCapture).toHaveBeenCalledWith("capture-key-1"));
    expect(await screen.findByText("Keybind capture cancelled.")).toBeInTheDocument();
    expect(screen.queryByText("Position picker cancelled.")).not.toBeInTheDocument();
  });

  it("displays captured side mouse buttons as keybind labels", async () => {
    apiMock.startKeyPressCapture.mockResolvedValue({ id: "capture-key-1", status: "pending", result: null, error: null });
    apiMock.inputCaptureStatus.mockResolvedValue({ id: "capture-key-1", status: "complete", result: { kind: "key_press", key: "btnm4" }, error: null });

    render(<App />);
    await screen.findByText(/Connected to Ace Auto Click/);
    fireEvent.click(screen.getByRole("button", { name: /Keybind Tap/i }));
    fireEvent.click(screen.getByRole("button", { name: /Change keybind, current SPACE/i }));

    await waitFor(() => expect(screen.getByRole("button", { name: /Change keybind, current BTNM 4/i })).toBeInTheDocument());
    expect(screen.getByText("BTNM 4")).toBeInTheDocument();
  });

  it("suppresses ctrl+a default behavior while key capture is pending", async () => {
    apiMock.startKeyPressCapture.mockResolvedValue({ id: "capture-key-1", status: "pending", result: null, error: null });
    apiMock.inputCaptureStatus.mockImplementation(async (id: string) => ({ id, status: "pending", result: null, error: null }));
    render(<App />);
    await screen.findByText(/Connected to Ace Auto Click/);
    fireEvent.click(screen.getByRole("button", { name: /Keybind Tap/i }));
    fireEvent.click(screen.getByRole("button", { name: /Change keybind, current SPACE/i }));
    expect(await screen.findByText("Press key or side button...")).toBeInTheDocument();
    const event = new KeyboardEvent("keydown", { key: "a", ctrlKey: true, cancelable: true });
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: /Press key or side button/i }));
    await waitFor(() => expect(apiMock.cancelInputCapture).toHaveBeenCalledWith("capture-key-1"));
  });

  it("creates move steps with instant transition defaults", () => {
    const step = createStep("move");

    expect(step.type).toBe("move");
    if (step.type !== "move") return;
    expect(step.movement_mode).toBe("instant");
    expect(step.movement_duration_ms).toBe(0);
    expect(step.movement_smoothness).toBe(70);
    expect(step.path_randomness).toBe(20);
    expect(step.arc_direction).toBe("auto");
    expect(step.natural_randomness).toBe(35);
    expect(step.natural_overshoot_chance).toBe(30);
    expect(step.natural_overshoot_px).toBe(14);
    expect(step.natural_overshoot_severity).toBe(45);
    expect(step.natural_period_min_px).toBe(18);
    expect(step.natural_period_max_px).toBe(48);
    expect(step.natural_amplitude_min_px).toBe(2);
    expect(step.natural_amplitude_max_px).toBe(9);
    expect(step.natural_peak_reversal_chance).toBe(28);
  });

  it("normalizes saved move steps with missing smooth transition fields", () => {
    const settings = normalizeSettings({
      ...defaultSettings,
      profiles: [{
        ...defaultSettings.profiles[0],
        steps: [{
          id: "move-1",
          type: "move",
          enabled: true,
          repeats: 1,
          interval_ms: 100,
          randomness_ms: 0,
          x: 10,
          y: 20,
          random_offset: 0
        } as never]
      }]
    });
    const step = settings.profiles[0].steps[0];

    expect(step.type).toBe("move");
    if (step.type !== "move") return;
    expect(step.movement_mode).toBe("instant");
    expect(step.movement_duration_ms).toBe(0);
    expect(step.movement_smoothness).toBe(70);
    expect(step.path_randomness).toBe(20);
    expect(step.arc_direction).toBe("auto");
    expect(step.natural_randomness).toBe(35);
    expect(step.natural_overshoot_chance).toBe(30);
    expect(step.natural_overshoot_px).toBe(14);
    expect(step.natural_overshoot_severity).toBe(45);
    expect(step.natural_period_min_px).toBe(18);
    expect(step.natural_period_max_px).toBe(48);
    expect(step.natural_amplitude_min_px).toBe(2);
    expect(step.natural_amplitude_max_px).toBe(9);
    expect(step.natural_peak_reversal_chance).toBe(28);
  });

  it("edits smooth move transition controls", async () => {
    apiMock.getSettings.mockResolvedValue({
      ...defaultSettings,
      profiles: [{
        ...defaultSettings.profiles[0],
        steps: [{
          id: "move-1",
          type: "move",
          enabled: true,
          repeats: 1,
          interval_ms: 100,
          randomness_ms: 0,
          x: 10,
          y: 20,
          random_offset: 0,
          movement_mode: "instant",
          movement_duration_ms: 0,
          movement_smoothness: 70,
          path_randomness: 20,
          arc_direction: "auto",
          natural_randomness: 35,
          natural_overshoot_chance: 30,
          natural_overshoot_px: 14,
          natural_overshoot_severity: 45,
          natural_period_min_px: 18,
          natural_period_max_px: 48,
          natural_amplitude_min_px: 2,
          natural_amplitude_max_px: 9,
          natural_peak_reversal_chance: 28
        }]
      }]
    });

    render(<App />);
    fireEvent.click(await screen.findByText("Move to 10, 20"));
    await screen.findByText("Move Transition");
    expect(screen.queryByText("Move Duration (ms)")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Move Transition"), { target: { value: "smooth" } });
    expect(screen.getByText("Move Duration (ms)")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Move Duration"), { target: { value: "450" } });
    fireEvent.change(screen.getByLabelText("Move Smoothness"), { target: { value: "90" } });
    fireEvent.change(screen.getByLabelText("Move Path Randomness"), { target: { value: "35" } });
    fireEvent.change(screen.getByLabelText("Move Arc Direction"), { target: { value: "left" } });

    expect(screen.getByDisplayValue("450")).toBeInTheDocument();
    expect(screen.getByText(/Target:/)).toHaveTextContent("10, 20 exactly");
    expect(screen.getByText(/Smooth move to 10, 20/i)).toBeInTheDocument();
  });

  it("edits natural move transition controls", async () => {
    apiMock.getSettings.mockResolvedValue({
      ...defaultSettings,
      profiles: [{
        ...defaultSettings.profiles[0],
        steps: [{
          id: "move-2",
          type: "move",
          enabled: true,
          repeats: 1,
          interval_ms: 100,
          randomness_ms: 0,
          x: 30,
          y: 40,
          random_offset: 0,
          movement_mode: "instant",
          movement_duration_ms: 0,
          movement_smoothness: 70,
          path_randomness: 20,
          arc_direction: "auto",
          natural_randomness: 35,
          natural_overshoot_chance: 30,
          natural_overshoot_px: 14
        }]
      }]
    });

    render(<App />);
    fireEvent.click(await screen.findByText("Move to 30, 40"));
    fireEvent.change(screen.getByLabelText("Move Transition"), { target: { value: "natural" } });
    expect(screen.getByText("Move Duration (ms)")).toBeInTheDocument();
    expect(screen.getByText("Natural Randomness")).toBeInTheDocument();
    expect(screen.getByText("Overshoot Chance (%)")).toBeInTheDocument();
    expect(screen.getByText("Overshoot Max (px)")).toBeInTheDocument();
    expect(screen.getByText("Overshoot Severity")).toBeInTheDocument();
    expect(screen.getByText("Period Min (px)")).toBeInTheDocument();
    expect(screen.getByText("Period Max (px)")).toBeInTheDocument();
    expect(screen.getByText("Amplitude Min (px)")).toBeInTheDocument();
    expect(screen.getByText("Amplitude Max (px)")).toBeInTheDocument();
    expect(screen.getByText("Peak Reversal Chance (%)")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Move Duration"), { target: { value: "320" } });
    fireEvent.change(screen.getByLabelText("Natural Randomness"), { target: { value: "45" } });
    fireEvent.change(screen.getByLabelText("Natural Overshoot Chance"), { target: { value: "65" } });
    fireEvent.change(screen.getByLabelText("Natural Overshoot Px"), { target: { value: "24" } });
    fireEvent.change(screen.getByLabelText("Natural Overshoot Severity"), { target: { value: "72" } });
    fireEvent.change(screen.getByLabelText("Natural Period Min"), { target: { value: "12" } });
    fireEvent.change(screen.getByLabelText("Natural Period Max"), { target: { value: "64" } });
    fireEvent.change(screen.getByLabelText("Natural Amplitude Min"), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText("Natural Amplitude Max"), { target: { value: "16" } });
    fireEvent.change(screen.getByLabelText("Natural Peak Reversal Chance"), { target: { value: "43" } });
    expect(screen.getByDisplayValue("320")).toBeInTheDocument();
    expect(screen.getByText(/Natural move to 30, 40/i)).toBeInTheDocument();
  });

});
