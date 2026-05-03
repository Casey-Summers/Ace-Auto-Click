import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ChevronDown,
  Command,
  Crosshair,
  Keyboard,
  MousePointerClick,
  Plus,
  RadioTower,
  Save,
  Square,
  Timer,
  Zap
} from "lucide-react";

import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card, Panel } from "./components/ui/card";
import { Input, Select } from "./components/ui/input";
import { Keycap } from "./components/keycap";
import { api } from "./lib/api";
import type { ActionStep, AppSettings, RuntimeState } from "./lib/types";

const defaultSettings: AppSettings = {
  hotkey: "F8",
  emergency_stop_hotkey: "F12",
  theme: "dark",
  simple: {
    action_type: "mouse",
    action_value: "left",
    interval_ms: 100,
    interval_random_ms: 0,
    x: 0,
    y: 0,
    position_random_px: 0
  }
};

const defaultState: RuntimeState = {
  product_name: "Ace Auto Click",
  running: false,
  recording: false,
  status: "Disconnected",
  last_error: null
};

const starterSteps: ActionStep[] = [
  {
    id: "step-click-1",
    type: "click",
    enabled: true,
    repeats: 1,
    interval_ms: 100,
    randomness_ms: 0,
    x: 500,
    y: 500,
    button: "left",
    clicks: 1,
    random_offset: 0
  },
  {
    id: "step-wait-1",
    type: "wait",
    enabled: true,
    repeats: 1,
    interval_ms: 0,
    randomness_ms: 0,
    ms: 1000,
    random_ms: 0
  }
];

function stepIcon(type: ActionStep["type"]) {
  if (type === "click") return <MousePointerClick size={16} />;
  if (type === "wait") return <Timer size={16} />;
  if (type === "pixel_check") return <Crosshair size={16} />;
  return <Keyboard size={16} />;
}

function stepTitle(step: ActionStep) {
  if (step.type === "click") return `Click ${step.button} at ${step.x}, ${step.y}`;
  if (step.type === "wait") return `Wait ${step.ms}ms`;
  if (step.type === "pixel_check") return `Pixel ${step.x}, ${step.y}`;
  return `Tap ${step.key}`;
}

function createStep(type: ActionStep["type"]): ActionStep {
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

export function App() {
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [state, setState] = useState<RuntimeState>(defaultState);
  const [steps, setSteps] = useState<ActionStep[]>(starterSteps);
  const [selectedId, setSelectedId] = useState(starterSteps[0].id);
  const [log, setLog] = useState<string[]>(["UI ready. Start the API with python main.py api."]);

  const selectedStep = useMemo(
    () => steps.find((step) => step.id === selectedId) ?? steps[0],
    [selectedId, steps]
  );

  useEffect(() => {
    document.documentElement.classList.toggle("light", settings.theme === "light");
  }, [settings.theme]);

  useEffect(() => {
    Promise.all([api.getSettings(), api.getState()])
      .then(([nextSettings, nextState]) => {
        setSettings(nextSettings);
        setState(nextState);
        setLog((items) => [`Connected to ${nextState.product_name}.`, ...items]);
      })
      .catch((error) => setLog((items) => [`API unavailable: ${error.message}`, ...items]));

    const timer = window.setInterval(() => {
      api.getState().then(setState).catch(() => undefined);
    }, 1200);

    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setLog((items) => ["Command palette scaffold opened via Ctrl+K.", ...items]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const patchSimple = (patch: Partial<AppSettings["simple"]>) => {
    setSettings((current) => ({
      ...current,
      simple: { ...current.simple, ...patch }
    }));
  };

  const patchSelected = (patch: Partial<ActionStep>) => {
    setSteps((current) =>
      current.map((step) => (step.id === selectedStep?.id ? ({ ...step, ...patch } as ActionStep) : step))
    );
  };

  const runSimple = async () => {
    const result = await api.runSimple(settings.simple);
    setState(result.state);
    setLog((items) => ["Simple automation started.", ...items]);
  };

  const runSequence = async () => {
    const result = await api.runSequence(steps, 0);
    setState(result.state);
    setLog((items) => ["Sequence started.", ...items]);
  };

  const stop = async () => {
    const result = await api.stop();
    setState(result.state);
    setLog((items) => ["Automation stopped.", ...items]);
  };

  const emergencyStop = async () => {
    const result = await api.emergencyStop();
    setState(result.state);
    setLog((items) => ["Emergency stop triggered.", ...items]);
  };

  const saveSettings = async () => {
    const next = await api.saveSettings(settings);
    setSettings(next);
    setLog((items) => ["Settings saved.", ...items]);
  };

  const capturePosition = async () => {
    const position = await api.mousePosition();
    patchSimple({ x: position.x, y: position.y });
    setLog((items) => [`Captured mouse position ${position.x}, ${position.y}.`, ...items]);
  };

  const addStep = (type: ActionStep["type"]) => {
    const step = createStep(type);
    setSteps((current) => [...current, step]);
    setSelectedId(step.id);
  };

  return (
    <main className="flex min-h-screen flex-col p-5">
      <header className="mb-4 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent/15 text-accent shadow-raycast">
              <Zap size={18} />
            </div>
            <h1 className="text-xl font-semibold">Ace Auto Click</h1>
            <Badge tone={state.running ? "success" : "neutral"}>{state.status}</Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Automation workspace for precise mouse, keyboard, pixel, and sequence control.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost">
            <Command size={16} />
            <Keycap>Ctrl</Keycap>
            <Keycap>K</Keycap>
          </Button>
          <Button variant="danger" onClick={emergencyStop}>
            <AlertTriangle size={16} />
            Emergency stop
          </Button>
        </div>
      </header>

      <div className="grid flex-1 grid-cols-[280px_minmax(360px,1fr)_320px] gap-4">
        <Panel className="p-3">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-muted-foreground">Action Library</h2>
            <ChevronDown size={14} className="text-muted-foreground" />
          </div>

          <div className="grid gap-2">
            <Button variant="default" className="justify-start" onClick={() => addStep("click")}>
              <MousePointerClick size={16} /> Click
            </Button>
            <Button variant="default" className="justify-start" onClick={() => addStep("wait")}>
              <Timer size={16} /> Wait
            </Button>
            <Button variant="default" className="justify-start" onClick={() => addStep("pixel_check")}>
              <Crosshair size={16} /> Pixel check
            </Button>
            <Button variant="default" className="justify-start" onClick={() => addStep("key_tap")}>
              <Keyboard size={16} /> Key tap
            </Button>
          </div>

          <Card className="mt-4">
            <h3 className="mb-3 text-sm font-semibold">Simple Mode</h3>
            <div className="grid gap-3">
              <Select
                value={settings.simple.action_type}
                onChange={(event) =>
                  patchSimple({ action_type: event.target.value as "mouse" | "keyboard" })
                }
              >
                <option value="mouse">Mouse</option>
                <option value="keyboard">Keyboard</option>
              </Select>
              <Input
                value={settings.simple.action_value}
                onChange={(event) => patchSimple({ action_value: event.target.value })}
              />
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="number"
                  value={settings.simple.x}
                  onChange={(event) => patchSimple({ x: Number(event.target.value) })}
                />
                <Input
                  type="number"
                  value={settings.simple.y}
                  onChange={(event) => patchSimple({ y: Number(event.target.value) })}
                />
              </div>
              <Input
                type="number"
                value={settings.simple.interval_ms}
                onChange={(event) => patchSimple({ interval_ms: Number(event.target.value) })}
              />
              <Button onClick={capturePosition}>
                <Crosshair size={16} /> Capture position
              </Button>
            </div>
          </Card>
        </Panel>

        <Panel className="flex flex-col p-3">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-muted-foreground">Sequence Builder</h2>
            <div className="flex gap-2">
              <Button variant="success" onClick={runSequence}>
                <RadioTower size={16} /> Run sequence
              </Button>
              <Button variant="danger" onClick={stop}>
                <Square size={16} /> Stop
              </Button>
            </div>
          </div>

          <div className="grid gap-2">
            {steps.map((step, index) => (
              <button
                key={step.id}
                className={`flex items-center justify-between rounded-lg border p-3 text-left transition ${
                  step.id === selectedStep?.id
                    ? "border-info/45 bg-info/10"
                    : "border-border bg-background/60 hover:bg-surface-strong"
                }`}
                onClick={() => setSelectedId(step.id)}
              >
                <div className="flex items-center gap-3">
                  <Badge>{String(index + 1).padStart(2, "0")}</Badge>
                  <span className="text-info">{stepIcon(step.type)}</span>
                  <div>
                    <div className="text-sm font-semibold">{stepTitle(step)}</div>
                    <div className="font-mono text-xs text-muted-foreground">
                      repeats {step.repeats} · delay {step.interval_ms}ms
                    </div>
                  </div>
                </div>
                <Badge tone={step.enabled ? "success" : "neutral"}>
                  {step.enabled ? "enabled" : "off"}
                </Badge>
              </button>
            ))}
          </div>
        </Panel>

        <Panel className="flex flex-col gap-4 p-3">
          <Card>
            <h2 className="mb-3 text-sm font-semibold">Runtime</h2>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <Badge tone={state.running ? "success" : "neutral"}>
                <Activity size={12} /> {state.running ? "running" : "idle"}
              </Badge>
              <Badge tone={state.recording ? "warning" : "neutral"}>
                {state.recording ? "recording" : "not recording"}
              </Badge>
              <Button variant="primary" onClick={runSimple}>
                Run simple
              </Button>
              <Button variant="default" onClick={saveSettings}>
                <Save size={16} /> Save
              </Button>
            </div>
          </Card>

          <Card>
            <h2 className="mb-3 text-sm font-semibold">Selected Step</h2>
            {selectedStep ? (
              <div className="grid gap-3">
                <Input
                  type="number"
                  value={selectedStep.repeats}
                  onChange={(event) => patchSelected({ repeats: Number(event.target.value) })}
                />
                <Input
                  type="number"
                  value={selectedStep.interval_ms}
                  onChange={(event) => patchSelected({ interval_ms: Number(event.target.value) })}
                />
                {selectedStep.type === "click" && (
                  <>
                    <div className="grid grid-cols-2 gap-2">
                      <Input
                        type="number"
                        value={selectedStep.x}
                        onChange={(event) => patchSelected({ x: Number(event.target.value) })}
                      />
                      <Input
                        type="number"
                        value={selectedStep.y}
                        onChange={(event) => patchSelected({ y: Number(event.target.value) })}
                      />
                    </div>
                    <Select
                      value={selectedStep.button}
                      onChange={(event) =>
                        patchSelected({ button: event.target.value as "left" | "right" | "middle" })
                      }
                    >
                      <option value="left">left</option>
                      <option value="right">right</option>
                      <option value="middle">middle</option>
                    </Select>
                  </>
                )}
                {selectedStep.type === "key_tap" && (
                  <Input
                    value={selectedStep.key}
                    onChange={(event) => patchSelected({ key: event.target.value })}
                  />
                )}
              </div>
            ) : null}
          </Card>

          <Card className="min-h-0 flex-1">
            <h2 className="mb-3 text-sm font-semibold">Event Log</h2>
            <div className="grid max-h-56 gap-2 overflow-auto font-mono text-xs text-muted-foreground">
              {log.slice(0, 12).map((entry, index) => (
                <div key={`${entry}-${index}`} className="rounded-md bg-background/70 p-2">
                  {entry}
                </div>
              ))}
            </div>
          </Card>
        </Panel>
      </div>
    </main>
  );
}
