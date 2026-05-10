import { useEffect, useMemo, useRef, useState } from "react";

import { api } from "../lib/api";
import { defaultProfile, defaultSettings } from "../lib/defaults";
import { displayKeybind } from "../lib/keybinds";
import { createStep } from "../lib/steps";
import { defaultState, normalizeSettings } from "../lib/settings";
import type { ActionStep, AppMode, AppSettings, AutomationProfile, ExecutionEvent, Point, ProfileFile, Rgb, RuntimeState } from "../lib/types";

type CaptureKind = "position" | "pixel" | "key";
type CaptureContext = {
  kind: CaptureKind;
  stepId: string;
  sessionId: string;
  token: number;
};
type CaptureStatus = "pending" | "complete" | "cancelled" | "failed";
type CaptureSnapshot = {
  id: string;
  status: CaptureStatus;
  result: { x: number; y: number } | { key: string } | null;
  error: string | null;
};

function formatExecutionEventLog(event: ExecutionEvent): string | null {
  if (event.phase !== "step_execute") return null;
  if (event.step_type !== "key_tap" && event.step_type !== "key_hold") return null;
  const details = event.details;
  if (!details) return null;
  const combo = details.configured_combo ?? "unset";
  const ops = (details.operations ?? []).join(", ");
  const path = details.dispatch_path ?? "unknown";
  const typeLabel = event.step_type === "key_tap" ? "Key Tap" : "Key Hold";
  return `${typeLabel} step ${event.step_id}: parsed ${combo} via ${path}${ops ? ` -> ${ops}` : ""}`;
}

export function useAppController() {
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [state, setState] = useState<RuntimeState>(defaultState);
  const [selectedId, setSelectedId] = useState(defaultProfile.steps[0].id);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [focusEmergency, setFocusEmergency] = useState(false);
  const [focusKeybind, setFocusKeybind] = useState<"" | "run" | "emergency">("");
  const [profileFiles, setProfileFiles] = useState<ProfileFile[]>([]);
  const [selectedProfileFile, setSelectedProfileFile] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  const [pickingClickStepId, setPickingClickStepId] = useState("");
  const [pickCursorPosition, setPickCursorPosition] = useState<Point | null>(null);
  const [pixelLiveRgb, setPixelLiveRgb] = useState<Rgb | null>(null);
  const [samplingPixelStepId, setSamplingPixelStepId] = useState("");
  const [pickingKeyStepId, setPickingKeyStepId] = useState("");
  const captureSessionId = useRef("");
  const captureToken = useRef(0);
  const [captureContext, setCaptureContext] = useState<CaptureContext | null>(null);
  const settingsHydrated = useRef(false);
  const settingsRef = useRef(settings);
  const [log, setLog] = useState<string[]>(["UI ready. Start the API with python app.py api."]);
  const [executionEvents, setExecutionEvents] = useState<ExecutionEvent[]>([]);
  const executionAfter = useRef(0);

  const activeProfile = useMemo(
    () => settings.profiles.find((profile) => profile.id === settings.active_profile_id) ?? settings.profiles[0] ?? defaultProfile,
    [settings]
  );
  const selectedStep = useMemo(
    () => (selectedId ? activeProfile.steps.find((step) => step.id === selectedId) : undefined),
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
    const colors = settings.icon_colors_profile_dependent
      ? (activeProfile.action_icon_colors ?? settings.action_icon_colors ?? {})
      : (settings.action_icon_colors ?? {});
    document.documentElement.style.setProperty("--icon-click", colors.click ?? "#55B3FF");
    document.documentElement.style.setProperty("--icon-move", colors.move ?? "#55B3FF");
    document.documentElement.style.setProperty("--icon-drag", colors.drag ?? "#55B3FF");
    document.documentElement.style.setProperty("--icon-wait", colors.wait ?? "#55B3FF");
    document.documentElement.style.setProperty("--icon-pixel", colors.pixel_check ?? "#55B3FF");
    document.documentElement.style.setProperty("--icon-key", colors.key_tap ?? "#55B3FF");
    document.documentElement.style.setProperty("--icon-key-hold", colors.key_hold ?? colors.key_tap ?? "#55B3FF");
    document.documentElement.style.setProperty("--icon-loop-start", colors.loop_start ?? "#55B3FF");
    document.documentElement.style.setProperty("--icon-loop-end", colors.loop_end ?? "#55B3FF");
  }, [settings.theme, settings.icon_colors_profile_dependent, settings.action_icon_colors, activeProfile.action_icon_colors]);

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
  }, []);

  useEffect(() => {
    const intervalMs = state.running ? 120 : 1200;
    const timer = window.setInterval(() => {
      api.getState().then(setState).catch(() => undefined);
      api.executionEvents(executionAfter.current).then((events) => {
        if (!events.length) return;
        executionAfter.current = Math.max(executionAfter.current, ...events.map((event) => event.sequence_no));
        setExecutionEvents(events);
        const lines = events.map(formatExecutionEventLog).filter((line): line is string => Boolean(line));
        if (lines.length) {
          setLog((items) => [...lines.reverse(), ...items]);
        }
      }).catch(() => undefined);
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [state.running]);

  useEffect(() => {
    if (!pickingClickStepId && !samplingPixelStepId && !pickingKeyStepId) {
      setPickCursorPosition(null);
      setPixelLiveRgb(null);
      return undefined;
    }

    let active = true;
    const refreshLiveState = async () => {
      try {
        const position = await api.mousePosition();
        if (!active) return;
        setPickCursorPosition(position);
        if (selectedStep?.type === "pixel_check") {
          const pixel = await api.pixel(position.x, position.y);
          if (active) setPixelLiveRgb(pixel.rgb);
        } else if (samplingPixelStepId && selectedStep?.type === "click") {
          const pixel = await api.pixel(selectedStep.x, selectedStep.y);
          if (active) setPixelLiveRgb(pixel.rgb);
        }
      } catch {
        return undefined;
      }
    };
    void refreshLiveState();
    const timer = window.setInterval(() => void refreshLiveState(), 160);

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        const sessionId = captureSessionId.current;
        if (sessionId) {
          api.cancelInputCapture(sessionId).catch(() => undefined);
          captureSessionId.current = "";
        }
        setPickingClickStepId("");
        setSamplingPixelStepId("");
        setLog((items) => ["Position picker cancelled.", ...items]);
      }
    };
    window.addEventListener("keydown", onKey);

    return () => {
      active = false;
      window.clearInterval(timer);
      window.removeEventListener("keydown", onKey);
    };
  }, [pickingClickStepId, samplingPixelStepId, pickingKeyStepId, selectedStep?.type]);

  useEffect(() => {
    if (!captureContext) return;
    const stillExists = activeProfile.steps.some((step) => step.id === captureContext.stepId);
    const invalidForKind =
      (captureContext.kind === "position" && (!selectedStep || selectedStep.id !== captureContext.stepId || (selectedStep.type !== "click" && selectedStep.type !== "move" && selectedStep.type !== "drag"))) ||
      (captureContext.kind === "pixel" && (!selectedStep || selectedStep.id !== captureContext.stepId || selectedStep.type !== "pixel_check")) ||
      (captureContext.kind === "key" && (!selectedStep || selectedStep.id !== captureContext.stepId || (selectedStep.type !== "key_tap" && selectedStep.type !== "key_hold")));
    if (!stillExists || invalidForKind || settings.mode !== "advanced") {
      const sessionId = captureSessionId.current;
      if (sessionId) {
        api.cancelInputCapture(sessionId).catch(() => undefined);
      }
      captureSessionId.current = "";
      setCaptureContext(null);
      setPickingClickStepId("");
      setSamplingPixelStepId("");
      setPickingKeyStepId("");
    }
  }, [activeProfile.steps, captureContext, selectedStep, settings.mode]);

  useEffect(() => {
    if (!captureContext || captureContext.kind !== "key") return undefined;
    const suppressShortcuts = (event: KeyboardEvent) => {
      if (event.key === "Escape") return;
      event.preventDefault();
      event.stopPropagation();
    };
    window.addEventListener("keydown", suppressShortcuts, true);
    return () => window.removeEventListener("keydown", suppressShortcuts, true);
  }, [captureContext]);

  const runCaptureSession = async (kind: CaptureKind, stepId: string, starter: () => Promise<CaptureSnapshot>) => {
    const token = ++captureToken.current;
    const started = await starter();
    captureSessionId.current = started.id;
    setCaptureContext({ kind, stepId, sessionId: started.id, token });
    let snapshot = started;
    while (snapshot.status === "pending" && captureSessionId.current === started.id && captureToken.current === token) {
      await new Promise((resolve) => window.setTimeout(resolve, 100));
      try {
        snapshot = await api.inputCaptureStatus(started.id);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        if (/404|Not Found/i.test(message)) {
          if (captureSessionId.current === started.id && captureToken.current === token) {
            setLog((items) => ["Capture ended unexpectedly.", ...items]);
          }
          break;
        }
        throw error;
      }
    }
    if (captureSessionId.current === started.id) {
      captureSessionId.current = "";
    }
    if (captureToken.current === token) {
      setCaptureContext(null);
    }
    return snapshot;
  };

  const pickStepKey = async () => {
    if (!selectedStep || (selectedStep.type !== "key_tap" && selectedStep.type !== "key_hold")) return;
    if (pickingKeyStepId) return;
    const stepId = selectedStep.id;
    setPickingKeyStepId(stepId);
    try {
      const snapshot = await runCaptureSession("key", stepId, () => api.startKeyPressCapture() as Promise<CaptureSnapshot>);
      if (snapshot.status !== "complete" || !snapshot.result || !("key" in snapshot.result)) {
        return;
      }
      const key = snapshot.result.key;
      updateStepById(stepId, (step) => (step.type === "key_tap" || step.type === "key_hold") ? { ...step, key } : step);
      setLog((items) => [`Captured keybind ${displayKeybind(key)}.`, ...items]);
    } finally {
      setPickingKeyStepId("");
    }
  };

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

  useEffect(() => {
    if (state.running) setSelectedId("");
  }, [state.running]);

  const patchSettings = (patch: Partial<AppSettings>) => {
    setSettings((current) => {
      const next = { ...current, ...patch };
      settingsRef.current = next;
      return next;
    });
  };

  const updateActiveProfile = (updater: (profile: AutomationProfile) => AutomationProfile) => {
    setSettings((current) => {
      const activeId = current.active_profile_id;
      const next = {
        ...current,
        profiles: current.profiles.map((profile) =>
          profile.id === activeId ? updater(profile) : profile
        )
      };
      settingsRef.current = next;
      return next;
    });
  };

  const patchProfile = (patch: Partial<AutomationProfile>) => updateActiveProfile((profile) => ({ ...profile, ...patch }));

  const patchSteps = (steps: ActionStep[]) => patchProfile({ steps });

  const updateStepById = (stepId: string, updater: (step: ActionStep) => ActionStep) => {
    updateActiveProfile((profile) => ({
      ...profile,
      steps: profile.steps.map((step) => (step.id === stepId ? updater(step) : step))
    }));
  };

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
    if (!selectedStep) return;
    if (selectedStep?.type === "loop_start" && patch.enabled !== undefined) {
      const startIndex = activeProfile.steps.findIndex((step) => step.id === selectedStep.id);
      const range = findLoopRange(activeProfile.steps, startIndex);
      if (range) {
        patchSteps(activeProfile.steps.map((step, index) => index >= range.startIndex && index <= range.endIndex
          ? step.type === "loop_start"
            ? ({ ...step, enabled: patch.enabled, collapsed: !patch.enabled ? true : step.collapsed } as ActionStep)
            : ({ ...step, enabled: patch.enabled } as ActionStep)
          : step));
        return;
      }
    }
    updateStepById(selectedStep.id, (step) => ({ ...step, ...patch } as ActionStep));
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
    const result = await api.runToggle();
    setState(result.state);
    setLog((items) => [`Running ${settingsRef.current.profiles.find((profile) => profile.id === settingsRef.current.active_profile_id)?.name ?? activeProfile.name}.`, ...items]);
  };

  const openEmergencySettings = () => {
    setSettingsOpen(true);
    setFocusEmergency(true);
    setFocusKeybind("emergency");
  };

  const selectStep = (id: string) => {
    setSelectedId((current) => (current === id ? "" : id));
  };

  const openRunHotkeySettings = () => {
    setSettingsOpen(true);
    setFocusEmergency(false);
    setFocusKeybind("run");
  };

  const samplePixel = async () => {
    if (!selectedStep || selectedStep.type !== "pixel_check") return;
    if (samplingPixelStepId) return;
    const stepId = selectedStep.id;
    setSamplingPixelStepId(stepId);
    try {
      const snapshot = await runCaptureSession("pixel", stepId, () => api.startMouseClickCapture() as Promise<CaptureSnapshot>);
      if (snapshot.status === "cancelled") {
        setLog((items) => ["Pixel sample cancelled.", ...items]);
        return;
      }
      if (snapshot.status === "failed") {
        setLog((items) => [snapshot.error?.toLowerCase().includes("timed out") ? "Pixel sample timed out." : `Pixel sample failed: ${snapshot.error ?? "Unknown error"}`, ...items]);
        return;
      }
      const position = snapshot.result;
      if (!position || !("x" in position) || !("y" in position)) {
        setLog((items) => ["Pixel sample failed: capture completed without coordinates.", ...items]);
        return;
      }
      const sample = await api.pixel(position.x, position.y);
      updateStepById(stepId, (step) => step.type === "pixel_check" ? { ...step, x: position.x, y: position.y, expected_rgb: sample.rgb } : step);
      setLog((items) => [`Sampled pixel ${sample.rgb.join(", ")} at ${position.x}, ${position.y}.`, ...items]);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const cancelled = /cancel/i.test(message);
      const timedOut = /timed out|408/i.test(message);
      setLog((items) => [cancelled ? "Pixel sample cancelled." : timedOut ? "Pixel sample timed out." : `Pixel sample failed: ${message}`, ...items]);
    } finally {
      setSamplingPixelStepId("");
    }
  };

  const deleteSelectedStep = () => {
    if (!selectedStep) return;
    const currentIndex = activeProfile.steps.findIndex((step) => step.id === selectedStep.id);
    if (currentIndex < 0) return;
    const nextSteps = activeProfile.steps.filter((step) => step.id !== selectedStep.id);
    patchSteps(nextSteps);
    if (nextSteps.length === 0) return;
    const nextIndex = Math.max(0, Math.min(currentIndex, nextSteps.length - 1));
    setSelectedId(nextSteps[nextIndex].id);
  };

  const duplicateSelectedStep = () => {
    if (!selectedStep) return;
    const currentIndex = activeProfile.steps.findIndex((step) => step.id === selectedStep.id);
    if (currentIndex < 0) return;
    const duplicated = {
      ...selectedStep,
      id: `${selectedStep.id}-copy-${Date.now()}`
    } as ActionStep;
    const nextSteps = [...activeProfile.steps];
    nextSteps.splice(currentIndex + 1, 0, duplicated);
    patchSteps(nextSteps);
    setSelectedId(duplicated.id);
  };

  const samplePixelFromClickStep = async (clickStepId: string) => {
    if (!samplingPixelStepId) return;
    const clickStep = activeProfile.steps.find((step): step is Extract<ActionStep, { type: "click" }> => step.id === clickStepId && step.type === "click");
    if (!clickStep) return;
    try {
      // If the standard pixel capture flow is still running, cancel it so it
      // cannot later overwrite this click-coordinate sample.
      const activeSessionId = captureSessionId.current;
      if (activeSessionId) {
        captureSessionId.current = "";
        api.cancelInputCapture(activeSessionId).catch(() => undefined);
      }

      // Important: sampling from a click step must use that step's stored coordinates,
      // never the live mouse cursor position.
      const sourceX = clickStep.x;
      const sourceY = clickStep.y;
      const sample = await api.pixel(sourceX, sourceY);
      const targetPixelStepId = samplingPixelStepId;
      updateStepById(targetPixelStepId, (step) => step.type === "pixel_check" ? { ...step, x: sourceX, y: sourceY, expected_rgb: sample.rgb } : step);
      setSamplingPixelStepId("");
      setLog((items) => [`Copied click coordinates ${sourceX}, ${sourceY} and sampled ${sample.rgb.join(", ")}.`, ...items]);
    } catch (error) {
      setLog((items) => [`Pixel sample failed: ${error instanceof Error ? error.message : String(error)}`, ...items]);
    }
  };

  const pickClickPosition = async () => {
    if (!selectedStep || (selectedStep.type !== "click" && selectedStep.type !== "move" && selectedStep.type !== "drag")) return;
    if (pickingClickStepId) return;
    const stepId = selectedStep.id;
    setPickingClickStepId(stepId);
    try {
      const snapshot = await runCaptureSession("position", stepId, () => api.startMouseClickCapture() as Promise<CaptureSnapshot>);
      if (snapshot.status === "cancelled") {
        setLog((items) => ["Position picker cancelled.", ...items]);
        return;
      }
      if (snapshot.status === "failed") {
        setLog((items) => [snapshot.error?.toLowerCase().includes("timed out") ? "Position picker timed out." : `Position picker failed: ${snapshot.error ?? "Unknown error"}`, ...items]);
        return;
      }
      const position = snapshot.result;
      if (!position || !("x" in position) || !("y" in position)) {
        setLog((items) => ["Position picker failed: capture completed without coordinates.", ...items]);
        return;
      }
      updateStepById(stepId, (step) => (step.type === "click" || step.type === "move" || step.type === "drag") ? { ...step, x: position.x, y: position.y } : step);
      setLog((items) => [`Picked position ${position.x}, ${position.y}.`, ...items]);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const cancelled = /cancel/i.test(message);
      const timedOut = /timed out|408/i.test(message);
      setLog((items) => [cancelled ? "Position picker cancelled." : timedOut ? "Position picker timed out." : `Position picker failed: ${message}`, ...items]);
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
    duplicateSelectedStep,
    deleteSelectedStep,
    activeProfile,
    confirmSaveProfile,
    emergencyStop,
    focusEmergency,
    focusKeybind,
    loadDialogOpen,
    loadProfile,
    log,
    openEmergencySettings,
    openProfilesFolder,
    openRunHotkeySettings,
    patchProfile,
    patchSelected,
    patchSettings,
    pickCursorPosition,
    pixelLiveRgb,
    pickingClickStepId,
    pickingKeyStepId,
    captureWaitingKind: captureContext?.kind ?? null,
    captureWaitingStepId: captureContext?.stepId ?? "",
    profileError,
    profileFiles,
    profileNameError,
    profileSaving,
    requestSaveProfile,
    runToggle,
    samplingPixelStepId,
    samplePixel,
    samplePixelFromClickStep,
    saveDialogOpen,
    selectedProfileFile,
    selectedStep,
    setLoadDialogOpen,
    setProfileError,
    setSaveDialogOpen,
    setSelectedId,
    selectStep,
    setSelectedProfileFile,
    setSettingsOpen,
    settings,
    settingsOpen,
    state,
    executionEvents,
    setFocusEmergency,
    setFocusKeybind,
    setMode,
    patchSteps,
    pickClickPosition
    ,pickStepKey
  };
}
