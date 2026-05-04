import { useEffect, useMemo, useRef, useState } from "react";

import { api } from "../lib/api";
import { defaultProfile, defaultSettings } from "../lib/defaults";
import { createStep } from "../lib/steps";
import { defaultState, normalizeSettings } from "../lib/settings";
import type { ActionStep, AppMode, AppSettings, AutomationProfile, ProfileFile, RuntimeState } from "../lib/types";

export function useAppController() {
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
  const [pickingClickStepId, setPickingClickStepId] = useState("");
  const settingsHydrated = useRef(false);
  const settingsRef = useRef(settings);
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
    settingsRef.current = settings;
  }, [settings]);

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

    void refreshProfiles();

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
    setSettings((current) => {
      const next = { ...current, ...patch };
      settingsRef.current = next;
      return next;
    });
  };

  const patchProfile = (patch: Partial<AutomationProfile>) => {
    setSettings((current) => {
      const next = {
        ...current,
        profiles: current.profiles.map((profile) =>
          profile.id === activeProfile.id ? { ...profile, ...patch } : profile
        )
      };
      settingsRef.current = next;
      return next;
    });
  };

  const patchSteps = (steps: ActionStep[]) => patchProfile({ steps });

  const findLoopRange = (steps: ActionStep[], startIndex: number) => {
    const start = steps[startIndex];
    if (!start || start.type !== "loop_start") return null;
    let depth = 1;
    for (let index = startIndex + 1; index < steps.length; index += 1) {
      const step = steps[index];
      if (step.type === "loop_start") depth += 1;
      if (step.type === "loop_end") depth -= 1;
      if (depth === 0 && step.type === "loop_end" && step.loop_id === start.loop_id) {
        return { startIndex, endIndex: index };
      }
    }
    return null;
  };

  const patchSelected = (patch: Partial<ActionStep>) => {
    if (selectedStep?.type === "loop_start" && patch.enabled !== undefined) {
      const startIndex = activeProfile.steps.findIndex((step) => step.id === selectedStep.id);
      const range = findLoopRange(activeProfile.steps, startIndex);
      if (range) {
        patchSteps(
          activeProfile.steps.map((step, index) =>
            index >= range.startIndex && index <= range.endIndex
              ? step.type === "loop_start"
                ? ({ ...step, enabled: patch.enabled, collapsed: !patch.enabled ? true : step.collapsed } as ActionStep)
                : ({ ...step, enabled: patch.enabled } as ActionStep)
              : step
          )
        );
        return;
      }
    }
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

  const sequenceForRun = async (): Promise<ActionStep[]> => {
    const latestSettings = settingsRef.current;
    const latestProfile = latestSettings.profiles.find((profile) => profile.id === latestSettings.active_profile_id) ?? activeProfile;
    if (latestSettings.mode === "advanced") {
      return latestProfile.steps;
    }
    const normal = latestProfile.normal;
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

  const runToggle = async () => {
    if (state.running) {
      await emergencyStop();
      return;
    }
    const latestSettings = settingsRef.current;
    const latestProfile = latestSettings.profiles.find((profile) => profile.id === latestSettings.active_profile_id) ?? activeProfile;
    const result = await api.runSequence(await sequenceForRun(), latestProfile.loops_count, latestProfile.loops_infinite);
    setState(result.state);
    setLog((items) => [`Running ${latestProfile.name}.`, ...items]);
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

  const pickClickPosition = async () => {
    if (!selectedStep || selectedStep.type !== "click") return;
    setPickingClickStepId(selectedStep.id);
    try {
      const position = await api.pickClickPosition();
      patchSteps(
        activeProfile.steps.map((step) =>
          step.id === selectedStep.id && step.type === "click"
            ? { ...step, x: position.x, y: position.y }
            : step
        )
      );
      setLog((items) => [`Picked click position ${position.x}, ${position.y}.`, ...items]);
    } catch (error) {
      setLog((items) => [`Position picker failed: ${error instanceof Error ? error.message : String(error)}`, ...items]);
    } finally {
      setPickingClickStepId("");
    }
  };

  const setMode = (mode: AppMode) => {
    patchSettings({ mode });
    patchProfile({ mode });
  };

  return {
    addStep,
    activeProfile,
    confirmSaveProfile,
    emergencyStop,
    focusEmergency,
    loadDialogOpen,
    loadProfile,
    log,
    openEmergencySettings,
    openProfilesFolder,
    patchProfile,
    patchSelected,
    patchSettings,
    pickingClickStepId,
    profileError,
    profileFiles,
    profileNameError,
    profileSaving,
    requestSaveProfile,
    runToggle,
    samplePixel,
    saveDialogOpen,
    selectedProfileFile,
    selectedStep,
    setLoadDialogOpen,
    setProfileError,
    setSaveDialogOpen,
    setSelectedId,
    setSelectedProfileFile,
    setSettingsOpen,
    settings,
    settingsOpen,
    state,
    setFocusEmergency,
    setMode,
    patchSteps,
    pickClickPosition
  };
}
