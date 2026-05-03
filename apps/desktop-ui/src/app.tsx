import { useEffect, useMemo, useState } from "react";
import { Settings, Zap } from "lucide-react";

import { EmergencyStopButton } from "./components/EmergencyStopButton";
import { ModeToggle } from "./components/ModeToggle";
import { Keycap } from "./components/keycap";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { ActionLibrary } from "./features/actions/ActionLibrary";
import { EventLogPanel } from "./features/log/EventLogPanel";
import { RuntimePanel } from "./features/runtime/RuntimePanel";
import { SettingsPanel } from "./features/settings/SettingsPanel";
import { NormalRunPanel } from "./features/sequence/NormalRunPanel";
import { NormalDetailsPanel, StepDetailsPanel } from "./features/sequence/StepDetailsPanel";
import { SequenceBuilder } from "./features/sequence/SequenceBuilder";
import { AppShell } from "./layouts/AppShell";
import { api } from "./lib/api";
import { defaultProfile, defaultSettings } from "./lib/defaults";
import { createStep } from "./lib/steps";
import type { ActionStep, AppMode, AppSettings, AutomationProfile, RuntimeState } from "./lib/types";

const defaultState: RuntimeState = {
  product_name: "Ace Auto Click",
  running: false,
  recording: false,
  status: "Disconnected",
  last_error: null
};

function normalizeSettings(settings: AppSettings): AppSettings {
  const profiles = settings.profiles?.length ? settings.profiles : [defaultProfile];
  const active_profile_id = profiles.some((profile) => profile.id === settings.active_profile_id)
    ? settings.active_profile_id
    : profiles[0].id;
  return {
    ...defaultSettings,
    ...settings,
    profiles,
    active_profile_id,
    run_toggle_hotkey: settings.run_toggle_hotkey || settings.hotkey || "F8",
    emergency_stop_hotkey: settings.emergency_stop_hotkey || "F12",
    show_event_log: settings.show_event_log ?? true
  };
}

export function App() {
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [state, setState] = useState<RuntimeState>(defaultState);
  const [selectedId, setSelectedId] = useState(defaultProfile.steps[0].id);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [focusEmergency, setFocusEmergency] = useState(false);
  const [log, setLog] = useState<string[]>(["UI ready. Start the API with python app.py api."]);

  const activeProfile = useMemo(
    () => settings.profiles.find((profile) => profile.id === settings.active_profile_id) ?? settings.profiles[0] ?? defaultProfile,
    [settings]
  );
  const selectedStep = useMemo(
    () => activeProfile.steps.find((step) => step.id === selectedId) ?? activeProfile.steps[0],
    [activeProfile.steps, selectedId]
  );

  useEffect(() => {
    document.documentElement.classList.toggle("light", settings.theme === "light");
  }, [settings.theme]);

  useEffect(() => {
    Promise.all([api.getSettings(), api.getState()])
      .then(([nextSettings, nextState]) => {
        setSettings(normalizeSettings(nextSettings));
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
      const key = event.key.toLowerCase();
      if (key === settings.emergency_stop_hotkey.toLowerCase()) {
        event.preventDefault();
        if (state.running) {
          void emergencyStop();
        } else {
          openEmergencySettings();
        }
      }
      if (key === settings.run_toggle_hotkey.toLowerCase()) {
        event.preventDefault();
        void runToggle();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const patchSettings = (patch: Partial<AppSettings>) => {
    setSettings((current) => ({ ...current, ...patch }));
  };

  const patchProfile = (patch: Partial<AutomationProfile>) => {
    setSettings((current) => ({
      ...current,
      profiles: current.profiles.map((profile) =>
        profile.id === activeProfile.id ? { ...profile, ...patch } : profile
      )
    }));
  };

  const patchSteps = (steps: ActionStep[]) => patchProfile({ steps });

  const patchSelected = (patch: Partial<ActionStep>) => {
    patchSteps(
      activeProfile.steps.map((step) =>
        step.id === selectedStep?.id ? ({ ...step, ...patch } as ActionStep) : step
      )
    );
  };

  const addStep = (type: ActionStep["type"]) => {
    const step = createStep(type);
    patchSteps([...activeProfile.steps, step]);
    setSelectedId(step.id);
    patchProfile({ mode: "advanced" });
    patchSettings({ mode: "advanced" });
  };

  const saveSettings = async () => {
    const next = await api.saveSettings(settings);
    setSettings(normalizeSettings(next));
    setLog((items) => [`Saved profile ${activeProfile.name}.`, ...items]);
  };

  const emergencyStop = async () => {
    const result = await api.emergencyStop();
    setState(result.state);
    setLog((items) => ["Emergency stop triggered.", ...items]);
  };

  const runToggle = async () => {
    if (state.running) {
      await emergencyStop();
      return;
    }
    const result = await api.runSequence(await sequenceForRun(), activeProfile.loops);
    setState(result.state);
    setLog((items) => [`Running ${activeProfile.name}.`, ...items]);
  };

  const sequenceForRun = async (): Promise<ActionStep[]> => {
    if (settings.mode === "advanced") {
      return activeProfile.steps;
    }
    const normal = activeProfile.normal;
    const position = normal.use_current_mouse ? await api.mousePosition() : { x: 0, y: 0 };
    return [
      {
        id: "normal-click",
        type: "click",
        enabled: true,
        repeats: 1,
        interval_ms: normal.interval_ms,
        randomness_ms: normal.interval_random_ms,
        x: position.x,
        y: position.y,
        button: normal.button,
        clicks: normal.double_click ? 2 : normal.clicks_per_cycle,
        random_offset: normal.position_random_px
      }
    ];
  };

  const openEmergencySettings = () => {
    setSettingsOpen(true);
    setFocusEmergency(true);
  };

  const samplePixel = async () => {
    if (!selectedStep || selectedStep.type !== "pixel_check") return;
    const sample = await api.pixel(selectedStep.x, selectedStep.y);
    patchSelected({ expected_rgb: sample.rgb });
    setLog((items) => [`Sampled pixel ${sample.rgb.join(", ")}.`, ...items]);
  };

  const setMode = (mode: AppMode) => {
    patchSettings({ mode });
    patchProfile({ mode });
  };

  const header = (
    <header className="mb-4 flex items-center justify-between">
      <div>
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent/15 text-accent shadow-raycast">
            <Zap size={18} />
          </div>
          <h1 className="text-xl font-semibold">Ace Auto Click</h1>
          <ModeToggle value={settings.mode} onChange={setMode} />
          <Badge tone={state.running ? "success" : "neutral"}>{state.status}</Badge>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Automation workspace for precise mouse, keyboard, pixel, and sequence control.
        </p>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" onClick={() => setSettingsOpen(true)}>
          <Settings size={16} />
          Settings
        </Button>
        <EmergencyStopButton
          hotkey={settings.emergency_stop_hotkey}
          running={state.running}
          onStop={emergencyStop}
          onKeybindClick={openEmergencySettings}
        />
      </div>
    </header>
  );

  const left = (
    <>
      <RuntimePanel state={state} onSaveProfile={saveSettings} />
      <ActionLibrary onAdd={addStep} />
      <div className="mt-auto">{settings.show_event_log ? <EventLogPanel log={log} /> : null}</div>
    </>
  );

  const center = settings.mode === "advanced" ? (
    <SequenceBuilder
      steps={activeProfile.steps}
      loops={activeProfile.loops}
      running={state.running}
      runHotkey={settings.run_toggle_hotkey}
      selectedId={selectedStep?.id ?? ""}
      onSelect={setSelectedId}
      onLoopsChange={(loops) => patchProfile({ loops })}
      onRunToggle={runToggle}
    />
  ) : (
    <NormalRunPanel
      normal={activeProfile.normal}
      loops={activeProfile.loops}
      running={state.running}
      runHotkey={settings.run_toggle_hotkey}
      onLoopsChange={(loops) => patchProfile({ loops })}
      onRunToggle={runToggle}
    />
  );

  const right = settingsOpen ? (
    <SettingsPanel
      settings={settings}
      activeProfile={activeProfile}
      running={state.running}
      focusEmergency={focusEmergency}
      onSettingsChange={patchSettings}
      onProfileChange={patchProfile}
      onClose={() => setSettingsOpen(false)}
    />
  ) : settings.mode === "normal" ? (
    <NormalDetailsPanel
      normal={activeProfile.normal}
      onChange={(normalPatch) => patchProfile({ normal: { ...activeProfile.normal, ...normalPatch } })}
    />
  ) : (
    <StepDetailsPanel step={selectedStep} onChange={patchSelected} onSamplePixel={samplePixel} />
  );

  return <AppShell header={header} left={left} center={center} right={right} />;
}
