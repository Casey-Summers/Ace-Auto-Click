import type { ActionStep, AppSettings, AutomationProfile } from "./types";

export const starterSteps: ActionStep[] = [
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

export const defaultProfile: AutomationProfile = {
  id: "default-profile",
  name: "Default Profile",
  mode: "advanced",
  normal: {
    use_current_mouse: true,
    button: "left",
    interval_ms: 100,
    interval_random_ms: 0,
    position_random_px: 0,
    clicks_per_cycle: 1,
    double_click: false
  },
  steps: starterSteps,
  loops: 1,
  loops_count: 1,
  loops_infinite: false
};

export const defaultSettings: AppSettings = {
  hotkey: "F8",
  run_toggle_hotkey: "F8",
  emergency_stop_hotkey: "F12",
  show_event_log: true,
  active_profile_id: defaultProfile.id,
  mode: "advanced",
  theme: "dark",
  action_icon_colors: {
    click: "#55B3FF",
    wait: "#55B3FF",
    pixel_check: "#55B3FF",
    key_tap: "#55B3FF",
    loop_start: "#55B3FF",
    loop_end: "#55B3FF"
  },
  simple: {
    action_type: "mouse",
    action_value: "left",
    interval_ms: 100,
    interval_random_ms: 0,
    x: 0,
    y: 0,
    position_random_px: 0
  },
  profiles: [defaultProfile]
};
