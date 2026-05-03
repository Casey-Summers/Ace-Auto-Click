export type RuntimeState = {
  product_name: string;
  running: boolean;
  recording: boolean;
  status: string;
  last_error: string | null;
};

export type SimpleSettings = {
  action_type: "mouse" | "keyboard";
  action_value: string;
  interval_ms: number;
  interval_random_ms: number;
  x: number;
  y: number;
  position_random_px: number;
};

export type AppMode = "normal" | "advanced";

export type NormalProfileSettings = {
  use_current_mouse: boolean;
  button: "left" | "right" | "middle";
  interval_ms: number;
  interval_random_ms: number;
  position_random_px: number;
  clicks_per_cycle: number;
  double_click: boolean;
};

export type AppSettings = {
  hotkey: string;
  run_toggle_hotkey: string;
  emergency_stop_hotkey: string;
  show_event_log: boolean;
  active_profile_id: string;
  mode: AppMode;
  simple: SimpleSettings;
  theme: "dark" | "light";
  profiles: AutomationProfile[];
};

export type BaseStep = {
  id: string;
  enabled: boolean;
  repeats: number;
  interval_ms: number;
  randomness_ms: number;
};

export type ClickStep = BaseStep & {
  type: "click";
  x: number;
  y: number;
  button: "left" | "right" | "middle";
  clicks: number;
  random_offset: number;
};

export type WaitStep = BaseStep & {
  type: "wait";
  ms: number;
  random_ms: number;
};

export type PixelCheckStep = BaseStep & {
  type: "pixel_check";
  x: number;
  y: number;
  expected_rgb: [number, number, number];
  tolerance: number;
  mode: "wait_until_match" | "stop_if_mismatch" | "skip_if_mismatch";
};

export type KeyTapStep = BaseStep & {
  type: "key_tap";
  key: string;
};

export type ActionStep = ClickStep | WaitStep | PixelCheckStep | KeyTapStep;

export type AutomationProfile = {
  id: string;
  name: string;
  mode: AppMode;
  normal: NormalProfileSettings;
  steps: ActionStep[];
  loops: number;
};

export type PixelSample = {
  x: number;
  y: number;
  rgb: [number, number, number];
};
