import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Keyboard, ScrollText, Settings, UserRound } from "lucide-react";

import { KeybindField } from "../../components/KeybindField";
import { ModalFrame } from "../../components/ModalFrame";
import { Badge } from "../../components/ui/badge";
import { Input, Select } from "../../components/ui/input";
import { cn } from "../../lib/utils";
import type { AppSettings, AutomationProfile } from "../../lib/types";

type Category = "general" | "profiles" | "keybinds" | "logs";

const categories: Array<{ id: Category; label: string; description: string; icon: ReactNode }> = [
  { id: "general", label: "General", description: "Choose the app-wide defaults that shape the workspace when profiles are opened.", icon: <Settings size={16} /> },
  { id: "profiles", label: "Profiles", description: "Manage imported profiles and the active profile used by the main workspace.", icon: <UserRound size={16} /> },
  { id: "keybinds", label: "Keybinds", description: "Capture shortcuts for starting automation and stopping it quickly.", icon: <Keyboard size={16} /> },
  { id: "logs", label: "Logs", description: "Control diagnostic visibility without changing automation behavior.", icon: <ScrollText size={16} /> }
];

function SettingRow({
  label,
  description,
  children
}: {
  label: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <div className="grid grid-cols-[220px_minmax(260px,1fr)] items-center gap-4 rounded-lg border border-border bg-background/45 p-3">
      <div>
        <div className="text-sm font-semibold text-foreground">{label}</div>
        {description ? <div className="mt-1 text-xs text-muted-foreground">{description}</div> : null}
      </div>
      <div>{children}</div>
    </div>
  );
}

export function SettingsModal({
  settings,
  activeProfile,
  running,
  focusEmergency,
  focusKeybind,
  onSettingsChange,
  onProfileChange,
  onClose
}: {
  settings: AppSettings;
  activeProfile: AutomationProfile;
  running: boolean;
  focusEmergency: boolean;
  focusKeybind: "" | "run" | "emergency";
  onSettingsChange: (patch: Partial<AppSettings>) => void;
  onProfileChange: (patch: Partial<AutomationProfile>) => void;
  onClose: () => void;
}) {
  const [category, setCategory] = useState<Category>(focusEmergency ? "keybinds" : "general");
  const [flashKeybind, setFlashKeybind] = useState<"" | "run" | "emergency">(focusKeybind);
  const firstButtonRef = useRef<HTMLButtonElement>(null);
  const reservedRun = useMemo(() => [settings.emergency_stop_hotkey], [settings.emergency_stop_hotkey]);
  const reservedEmergency = useMemo(() => [settings.run_toggle_hotkey], [settings.run_toggle_hotkey]);
  const activeCategory = categories.find((item) => item.id === category) ?? categories[0];

  useEffect(() => {
    firstButtonRef.current?.focus();
  }, []);

  useEffect(() => {
    if (focusEmergency) setCategory("keybinds");
  }, [focusEmergency]);

  useEffect(() => {
    if (!focusKeybind) return;
    setCategory("keybinds");
    setFlashKeybind(focusKeybind);
    const timer = window.setTimeout(() => setFlashKeybind(""), 1200);
    return () => window.clearTimeout(timer);
  }, [focusKeybind]);

  return (
    <ModalFrame
      title="Settings"
      description={activeCategory.description}
      widthClass="w-[min(980px,calc(100vw-48px))]"
      onClose={onClose}
    >
      <div className="grid h-[min(656px,calc(100vh-104px))] grid-cols-[220px_1fr]">
        <aside className="border-r border-border bg-background/45 p-3">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold">Settings</div>
            <Badge>menu</Badge>
          </div>
          <nav className="grid gap-1">
            {categories.map((item, index) => (
              <button
                key={item.id}
                ref={index === 0 ? firstButtonRef : undefined}
                type="button"
                className={cn(
                  "flex h-10 items-center gap-2 rounded-lg px-3 text-left text-sm transition",
                  category === item.id ? "bg-info/12 text-info ring-1 ring-info/25" : "text-muted-foreground hover:bg-surface-strong hover:text-foreground"
                )}
                onClick={() => setCategory(item.id)}
              >
                {item.icon}
                {item.label}
              </button>
            ))}
          </nav>
        </aside>

        <section className="grid min-h-0 grid-rows-[auto_1fr]">
          <header className="border-b border-border px-5 py-3">
            <h2 className="text-base font-semibold">{activeCategory.label}</h2>
          </header>
          <div className="min-h-0 overflow-auto p-5">
            {category === "general" ? (
              <div className="grid gap-3">
                <SettingRow label="Theme" description="Dark remains the primary app experience.">
                  <Select value={settings.theme} onChange={(event) => onSettingsChange({ theme: event.target.value as "dark" | "light" })}>
                    <option value="dark">Dark</option>
                    <option value="light">Light ready</option>
                  </Select>
                </SettingRow>
                <SettingRow label="Default mode" description="Choose the workspace mode used by the active profile.">
                  <Select value={settings.mode} onChange={(event) => onSettingsChange({ mode: event.target.value as "normal" | "advanced" })}>
                    <option value="normal">Normal</option>
                    <option value="advanced">Advanced</option>
                  </Select>
                </SettingRow>
                <SettingRow label="Action icon colors" description="Customize icon colors by action type.">
                  <div className="mb-2">
                    <label className="flex items-center gap-3 text-sm">
                      <input
                        type="checkbox"
                        checked={Boolean(settings.icon_colors_profile_dependent)}
                        onChange={(event) => onSettingsChange({ icon_colors_profile_dependent: event.target.checked })}
                      />
                      Profile-specific colors (off = global colors)
                    </label>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      ["click", "Click"],
                      ["wait", "Wait"],
                      ["pixel_check", "Pixel Match"],
                      ["key_tap", "Key tap"],
                      ["loop_start", "Loop start"],
                      ["loop_end", "Loop end"]
                    ].map(([key, label]) => (
                      <label key={key} className="flex items-center justify-between rounded-md border border-border bg-background/60 px-2 py-1 text-xs">
                        <span>{label}</span>
                        <input
                          type="color"
                          value={
                            (
                              (settings.icon_colors_profile_dependent
                                ? activeProfile.action_icon_colors?.[key as keyof NonNullable<AppSettings["action_icon_colors"]>]
                                : settings.action_icon_colors?.[key as keyof NonNullable<AppSettings["action_icon_colors"]>]
                              ) ?? "#55b3ff"
                            )
                          }
                          onChange={(event) => {
                            if (settings.icon_colors_profile_dependent) {
                              onProfileChange({
                                action_icon_colors: {
                                  ...(activeProfile.action_icon_colors ?? {}),
                                  [key]: event.target.value
                                }
                              });
                              return;
                            }
                            onSettingsChange({
                              action_icon_colors: {
                                ...(settings.action_icon_colors ?? {}),
                                [key]: event.target.value
                              }
                            });
                          }}
                        />
                      </label>
                    ))}
                  </div>
                </SettingRow>
              </div>
            ) : null}

            {category === "profiles" ? (
              <div className="grid gap-3">
                <SettingRow label="Profile name" description="Used for the active profile and default export filename.">
                  <Input value={activeProfile.name} onChange={(event) => onProfileChange({ name: event.target.value })} />
                </SettingRow>
                <SettingRow label="Active profile" description="Switch between profiles already imported into the app.">
                  <Select value={settings.active_profile_id} onChange={(event) => onSettingsChange({ active_profile_id: event.target.value })}>
                    {settings.profiles.map((profile) => (
                      <option key={profile.id} value={profile.id}>{profile.name}</option>
                    ))}
                  </Select>
                </SettingRow>
              </div>
            ) : null}

            {category === "keybinds" ? (
              <div className="grid gap-3">
                <div className={cn("rounded-lg transition", flashKeybind === "run" ? "ring-2 ring-info/55" : "")}>
                <SettingRow label="Run sequence toggle" description="Captured reactively; click the field, then press the new key.">
                  <KeybindField
                    label="Run sequence toggle"
                    value={settings.run_toggle_hotkey}
                    disabled={running}
                    reserved={reservedRun}
                    onChange={(run_toggle_hotkey) => onSettingsChange({ run_toggle_hotkey })}
                  />
                </SettingRow>
                </div>
                <div className={cn("rounded-lg transition", flashKeybind === "emergency" ? "ring-2 ring-danger/55" : "")}>
                <SettingRow label="Emergency stop" description="Global backend listener uses this key while the API is running.">
                  <KeybindField
                    label="Emergency stop"
                    value={settings.emergency_stop_hotkey}
                    disabled={running}
                    reserved={reservedEmergency}
                    onChange={(emergency_stop_hotkey) => onSettingsChange({ emergency_stop_hotkey })}
                  />
                </SettingRow>
                </div>
                {running ? <p className="text-xs text-warning">Keybinds are locked while automation is running.</p> : null}
              </div>
            ) : null}

            {category === "logs" ? (
              <div className="grid gap-3">
                <SettingRow label="Show event log" description="Controls the left-column event log panel.">
                  <label className="flex items-center gap-3 text-sm">
                    <input
                      type="checkbox"
                      checked={settings.show_event_log}
                      onChange={(event) => onSettingsChange({ show_event_log: event.target.checked })}
                    />
                    Show event log
                  </label>
                </SettingRow>
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </ModalFrame>
  );
}
