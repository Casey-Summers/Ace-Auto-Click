export type RuntimeState = {
  product_name: string;
  running: boolean;
  recording: boolean;
  status: string;
  last_error: string | null;
  current_step_id?: string | null;
  current_step_state?: "running" | "waiting" | "condition_false" | null;
};

export type ExecutionEvent = {
  step_id: string;
  step_type: string;
  phase: "step_execute" | "step_wait" | "step_complete" | "loop_enter" | "loop_exit" | "loop_repeat" | "condition_waiting" | "condition_met";
  run_id: number;
  sequence_no: number;
  ts_ms: number;
  details?: {
    configured_combo?: string;
    parsed_modifiers?: string[];
    parsed_base?: string;
    dispatch_path?: "keyboard_tap" | "keyboard_hold" | "mouse_side_button" | string;
    hold_ms?: number;
    operations?: string[];
  } | null;
};

export type RuntimeInfo = {
  instance_id: string;
  pid: number;
  elevated: boolean;
  dpi_awareness: string;
  input_driver: { driver: string; checked: boolean; last_dispatch?: { submitted: number; inserted: number } | null };
  target: TargetRuntimeState;
};

export type TargetRect = { left: number; top: number; width: number; height: number };
export type TargetWindowConfig = { enabled: boolean; executable_path: string; window_title: string; reference_client_rect: TargetRect; layout_policy: "maximize_then_scale"; focus_policy: "require_foreground" };
export type TargetRuntimeState = { configured: boolean; resolved: boolean; hwnd?: number | null; pid?: number | null; executable_path?: string; window_title?: string; foreground?: boolean; elevated?: boolean | null; current_client_rect?: TargetRect | null; scale_x?: number; scale_y?: number; pixel_checks_stale?: boolean; warning?: string | null };

export type Point = {
  x: number;
  y: number;
};

export type Rgb = [number, number, number];

export type InputCaptureSnapshot = {
  id: string;
  status: "pending" | "complete" | "cancelled" | "failed";
  result: (Point & {
    kind: string;
    button?: string | null;
    key?: string | null;
    cancelled?: boolean;
  }) | null;
  error: string | null;
};

export type ProfileFile = {
  file_name: string;
  profile_name: string;
  modified_at: string;
  size: number;
};

export type ProfileDirectoryStatus = {
  path: string;
  available: boolean;
  file_count: number;
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

export type ActionIconType = "click" | "move" | "drag" | "wait" | "pixel_check" | "key_tap" | "key_hold" | "loop_start" | "loop_end";

export type AppSettings = {
  hotkey: string;
  run_toggle_hotkey: string;
  emergency_stop_hotkey: string;
  show_event_log: boolean;
  active_profile_id: string;
  mode: AppMode;
  simple: SimpleSettings;
  theme: "dark" | "light";
  icon_colors_profile_dependent?: boolean;
  action_icon_colors?: Partial<Record<ActionIconType, string>>;
  profiles: AutomationProfile[];
};

export type BaseStep = {
  id: string;
  enabled: boolean;
  repeats: number;
  interval_ms: number;
  randomness_ms: number;
};
export type LoopConfig = {
  loops_count: number;
  loops_infinite: boolean;
};

export type ClickStep = BaseStep & {
  type: "click";
  x: number;
  y: number;
  button: "left" | "right" | "middle";
  clicks: number;
  random_offset: number;
};

export type MoveStep = BaseStep & {
  type: "move";
  x: number;
  y: number;
  random_offset: number;
  movement_mode: "instant" | "smooth" | "natural";
  movement_duration_ms: number;
  movement_smoothness: number;
  path_randomness: number;
  arc_direction: "auto" | "left" | "right";
  natural_randomness: number;
  natural_overshoot_chance: number;
  natural_overshoot_px: number;
  natural_overshoot_severity: number;
  natural_period_min_px: number;
  natural_period_max_px: number;
  natural_amplitude_min_px: number;
  natural_amplitude_max_px: number;
  natural_peak_reversal_chance: number;
};

export type DragStep = BaseStep & {
  type: "drag";
  x: number;
  y: number;
  buttons: Array<"left" | "right" | "middle">;
  direction: "right" | "left" | "up" | "down";
  length_px: number;
  speed: number;
  acceleration: number;
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
  mode: "wait_until_match" | "wait_until_mismatch" | "stop_if_mismatch" | "skip_if_mismatch" | "exit_loop_when_match";
};

export type KeyTapStep = BaseStep & {
  type: "key_tap";
  key: string;
};

export type KeyHoldStep = BaseStep & {
  type: "key_hold";
  key: string;
  hold_ms: number;
};

export type LoopStartStep = BaseStep & {
  type: "loop_start";
  loop_id: string;
  loop_count: number;
  loop_infinite: boolean;
  collapsed: boolean;
};

export type LoopEndStep = BaseStep & {
  type: "loop_end";
  loop_id: string;
};

export type ActionStep = ClickStep | MoveStep | DragStep | WaitStep | PixelCheckStep | KeyTapStep | KeyHoldStep | LoopStartStep | LoopEndStep;

export type AutomationProfile = {
  id: string;
  name: string;
  mode: AppMode;
  normal: NormalProfileSettings;
  steps: ActionStep[];
  loops: number;
  loops_count: number;
  loops_infinite: boolean;
  action_icon_colors?: Partial<Record<ActionIconType, string>>;
  target?: TargetWindowConfig | null;
};

export type PixelSample = {
  x: number;
  y: number;
  rgb: [number, number, number];
};
