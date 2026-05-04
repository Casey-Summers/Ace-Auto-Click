import { useEffect, useMemo, useRef, useState } from "react";
import { Settings, Zap } from "lucide-react";

import { EmergencyStopButton } from "./components/EmergencyStopButton";
import { ModeToggle } from "./components/ModeToggle";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { ActionLibrary } from "./features/actions/ActionLibrary";
import { EventLogPanel } from "./features/log/EventLogPanel";
import { ProfileLoadDialog, ProfileManager, ProfileSaveDialog } from "./features/runtime/RuntimePanel";
import { SettingsModal } from "./features/settings/SettingsPanel";
import { NormalRunPanel } from "./features/sequence/NormalRunPanel";
import { NormalDetailsPanel, StepDetailsPanel } from "./features/sequence/StepDetailsPanel";
import { SequenceBuilder } from "./features/sequence/SequenceBuilder";
import { AppShell } from "./layouts/AppShell";
import { api } from "./lib/api";
import { defaultProfile, defaultSettings } from "./lib/defaults";
import { createStep } from "./lib/steps";
import type { ActionStep, AppMode, AppSettings, AutomationProfile, ProfileFile, RuntimeState } from "./lib/types";

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
    show_event_log: settings.show_event_log ?? true,
    profiles: profiles.map((profile) => ({
      ...profile,
      loops_count: profile.loops_count ?? Math.max(1, profile.loops ?? 1),
      loops_infinite: profile.loops_infinite ?? (profile.loops === 0)
    }))
  };
}

export function App() {
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [state, setState] = useState<RuntimeState>(defaultState);
  const [selectedId, setSelectedId] = useState(defaultProfile.steps[0].id);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [focusEmergency, setFocusEmergency] = useState(false);
  const [profileFiles, setProfileFiles] = useState<ProfileFile[]>([]);
  const [selectedProfileFile, setSelectedProfileFile] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  const settingsHydrated = useRef(false);
  const [log, setLog] = useState<string[]>(["UI ready. Start the API with python app.py api."]);

  const activeProfile = useMemo(
    () => settings.profiles.find((profile) => profile.id === settings.active_profile_id) ?? settings.profiles[0] ?? defaultProfile,
    [settings]
  );
  const selectedStep = useMemo(
    () => activeProfile.steps.find((step) => step.id === selectedId) ?? activeProfile.steps[0],
    [activeProfile.steps, selectedId]
  );
  const profileNameError = useMemo(() => {
    const name = activeProfile.name.trim();
    if (!name) return "Profile name is required before saving.";
    const duplicate = settings.profiles.some((profile) => profile.id !== activeProfile.id && profile.name.trim().toLowerCase() === name.toLowerCase());
    return duplicate ? "Another imported profile already uses this name." : "";
  }, [activeProfile.id, activeProfile.name, settings.profiles]);

  useEffect(() => {
    document.documentElement.classList.toggle("light", settings.theme === "light");
  }, [settings.theme]);

  useEffect(() => {
    Promise.all([api.getSettings(), api.getState()])
      .then(([nextSettings, nextState]) => {
        setSettings(normalizeSettings(nextSettings));
        setState(nextState);
        settingsHydrated.current = true;
        setLog((items) => [`Connected to ${nextState.product_name}.`, ...items]);
      })
      .catch((error) => setLog((items) => [`API unavailable: ${error.message}`, ...items]));

    refreshProfiles();

    const timer = window.setInterval(() => {
      api.getState().then(setState).catch(() => undefined);
    }, 1200);

    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!settingsHydrated.current) return undefined;
    const timer = window.setTimeout(() => {
      api.saveSettings(settings).catch((error) => {
        setProfileError("Background keybind sync failed. Restart the app backend.");
        setLog((items) => [`Settings sync failed: ${error instanceof Error ? error.message : String(error)}`, ...items]);
      });
    }, 350);
    return () => window.clearTimeout(timer);
  }, [settings]);

  const refreshProfiles = async () => {
    try {
      const [nextProfileFiles] = await Promise.all([api.listProfiles(), api.profileStatus()]);
      setProfileFiles(nextProfileFiles);
      setProfileError("");
    } catch (error) {
      const message = error instanceof Error && /404|Not Found/i.test(error.message)
        ? "Profile API unavailable. Restart the app backend."
        : "Profiles folder is not ready.";
      setProfileError(message);
      setLog((items) => [`Profile manager: ${error instanceof Error ? error.message : String(error)}`, ...items]);
    }
  };

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
    if (type === "loop_start") {
      const loopId = `loop-${Date.now()}`;
      const start = { ...createStep("loop_start"), loop_id: loopId };
      const end = { ...createStep("loop_end"), loop_id: loopId };
      patchSteps([...activeProfile.steps, start, end]);
      setSelectedId(start.id);
    } else {
      const step = createStep(type);
      patchSteps([...activeProfile.steps, step]);
      setSelectedId(step.id);
    }
    patchProfile({ mode: "advanced" });
    patchSettings({ mode: "advanced" });
  };

  const requestSaveProfile = () => {
    setProfileError("");
    if (profileNameError) {
      setProfileError(profileNameError);
      return;
    }
    setSaveDialogOpen(true);
  };

  const confirmSaveProfile = async () => {
    setProfileSaving(true);
    setProfileError("");
    try {
      const saved = await api.saveProfile(settings);
      await refreshProfiles();
      setSelectedProfileFile(saved.file_name);
      setSaveDialogOpen(false);
      setLog((items) => [`Saved profile ${saved.profile_name}.`, ...items]);
    } catch (error) {
      const message = error instanceof Error && /404|Not Found/i.test(error.message)
        ? "Profile API unavailable. Restart the app backend."
        : error instanceof Error ? error.message : "Profile could not be saved.";
      setProfileError(message);
    } finally {
      setProfileSaving(false);
    }
  };

  const loadProfile = async () => {
    if (!selectedProfileFile) return;
    setProfileError("");
    try {
      const next = normalizeSettings(await api.loadProfile(selectedProfileFile));
      setSettings(next);
      await refreshProfiles();
      setLoadDialogOpen(false);
      setLog((items) => [`Loaded profile ${selectedProfileFile}.`, ...items]);
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : "Profile could not be loaded.");
    }
  };

  const openProfilesFolder = async () => {
    try {
      await api.openProfilesFolder();
      await refreshProfiles();
      setLog((items) => ["Opened profiles folder.", ...items]);
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : "Profiles folder could not be opened.");
    }
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
    const result = await api.runSequence(await sequenceForRun(), activeProfile.loops_count, activeProfile.loops_infinite);
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
      <ActionLibrary onAdd={addStep} />
      <div className="mt-auto">{settings.show_event_log ? <EventLogPanel log={log} /> : null}</div>
    </>
  );

  const centerTop = (
    <ProfileManager
      activeProfile={activeProfile}
      saving={profileSaving}
      error={profileError}
      profileNameError={profileNameError}
      onProfileNameChange={(name) => patchProfile({ name })}
      onSaveProfile={requestSaveProfile}
      onOpenLoadProfiles={() => {
        setProfileError("");
        setLoadDialogOpen(true);
      }}
      onOpenProfilesFolder={openProfilesFolder}
    />
  );

  const center = settings.mode === "advanced" ? (
    <SequenceBuilder
      steps={activeProfile.steps}
      loops={activeProfile.loops}
      loopsCount={activeProfile.loops_count}
      loopsInfinite={activeProfile.loops_infinite}
      running={state.running}
      runHotkey={settings.run_toggle_hotkey}
      selectedId={selectedStep?.id ?? ""}
      onSelect={setSelectedId}
      onLoopsChange={(loops_count, loops_infinite) => patchProfile({ loops_count, loops_infinite, loops: loops_infinite ? 0 : loops_count })}
      onStepsChange={patchSteps}
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

  const right = settings.mode === "normal" ? (
    <NormalDetailsPanel
      normal={activeProfile.normal}
      onChange={(normalPatch) => patchProfile({ normal: { ...activeProfile.normal, ...normalPatch } })}
    />
  ) : (
    <StepDetailsPanel step={selectedStep} onChange={patchSelected} onSamplePixel={samplePixel} />
  );

  return (
    <>
      <AppShell header={header} left={left} centerTop={centerTop} center={center} right={right} />
      {settingsOpen ? (
        <SettingsModal
          settings={settings}
          activeProfile={activeProfile}
          running={state.running}
          focusEmergency={focusEmergency}
          onSettingsChange={patchSettings}
          onProfileChange={patchProfile}
          onClose={() => {
            setSettingsOpen(false);
            setFocusEmergency(false);
          }}
        />
      ) : null}
      {saveDialogOpen ? (
        <ProfileSaveDialog
          profile={activeProfile}
          mode={settings.mode}
          saving={profileSaving}
          error={profileError}
          onCancel={() => setSaveDialogOpen(false)}
          onConfirm={confirmSaveProfile}
        />
      ) : null}
      {loadDialogOpen ? (
        <ProfileLoadDialog
          profiles={profileFiles}
          selectedProfileFile={selectedProfileFile}
          error={profileError}
          onSelect={setSelectedProfileFile}
          onLoad={loadProfile}
          onClose={() => setLoadDialogOpen(false)}
        />
      ) : null}
    </>
  );
}
