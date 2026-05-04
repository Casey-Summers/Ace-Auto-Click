import { defaultProfile, defaultSettings } from "./defaults";
import type { AppSettings, RuntimeState } from "./types";

export const defaultState: RuntimeState = {
  product_name: "Ace Auto Click",
  running: false,
  recording: false,
  status: "Disconnected",
  last_error: null
};

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
      loops_infinite: profile.loops_infinite ?? (profile.loops === 0)
    }))
  };
}
