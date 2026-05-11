import { defaultProfile, defaultSettings } from "./defaults";
import type { ActionStep, AppSettings, RuntimeState } from "./types";

export const defaultState: RuntimeState = {
  product_name: "Ace Auto Click",
  running: false,
  recording: false,
  status: "Disconnected",
  last_error: null
};

function normalizeStep(step: ActionStep): ActionStep {
  if (step.type === "move") {
    return {
      ...step,
      movement_mode: step.movement_mode ?? "instant",
      movement_duration_ms: step.movement_duration_ms ?? 0,
      movement_smoothness: step.movement_smoothness ?? 70,
      path_randomness: step.path_randomness ?? 20,
      arc_direction: step.arc_direction ?? "auto",
      natural_randomness: step.natural_randomness ?? 35,
      natural_overshoot_chance: step.natural_overshoot_chance ?? 30,
      natural_overshoot_px: step.natural_overshoot_px ?? 14,
      natural_overshoot_severity: step.natural_overshoot_severity ?? 45,
      natural_period_min_px: step.natural_period_min_px ?? 18,
      natural_period_max_px: Math.max(step.natural_period_min_px ?? 18, step.natural_period_max_px ?? 48),
      natural_amplitude_min_px: step.natural_amplitude_min_px ?? 2,
      natural_amplitude_max_px: Math.max(step.natural_amplitude_min_px ?? 2, step.natural_amplitude_max_px ?? 9),
      natural_peak_reversal_chance: step.natural_peak_reversal_chance ?? 28
    };
  }
  if (step.type === "drag") {
    const legacyAngle = (step as unknown as { angle_degrees?: number }).angle_degrees ?? 0;
    const legacyDistance = (step as unknown as { distance_px?: number }).distance_px ?? 100;
    const legacyDuration = (step as unknown as { duration_ms?: number }).duration_ms ?? 120;
    const direction = step.direction ?? (legacyAngle === 180 ? "left" : legacyAngle === 90 ? "down" : legacyAngle === 270 || legacyAngle === -90 ? "up" : "right");
    const speed = step.speed ?? (legacyDuration > 0 ? Math.round((Math.max(1, legacyDistance) / legacyDuration) * 1000) : 500);
    return {
      ...step,
      buttons: step.buttons?.length ? step.buttons : ["left", "right"],
      direction,
      length_px: step.length_px ?? legacyDistance,
      speed: Math.max(50, Math.min(5000, speed)),
      acceleration: step.acceleration ?? 1.6
    };
  }
  return step;
}

export function normalizeSettings(settings: AppSettings): AppSettings {
  const profiles = settings.profiles?.length ? settings.profiles : [defaultProfile];
  const active_profile_id = profiles.some((profile) => profile.id === settings.active_profile_id)
    ? settings.active_profile_id
    : profiles[0].id;
  return {
    ...defaultSettings,
    ...settings,
    active_profile_id,
    run_toggle_hotkey: settings.run_toggle_hotkey || settings.hotkey || "F8",
    emergency_stop_hotkey: settings.emergency_stop_hotkey || "F12",
    show_event_log: settings.show_event_log ?? true,
    profiles: profiles.map((profile) => ({
      ...profile,
      loops_count: profile.loops_count ?? Math.max(1, profile.loops ?? 1),
      loops_infinite: profile.loops_infinite ?? (profile.loops === 0),
      steps: profile.steps.map(normalizeStep)
    }))
  };
}
