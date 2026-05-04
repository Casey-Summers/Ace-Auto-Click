import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Keyboard, ScrollText, Settings, Shield, UserRound, X } from "lucide-react";

import { KeybindField } from "../../components/KeybindField";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input, Select } from "../../components/ui/input";
import { cn } from "../../lib/utils";
import type { AppSettings, AutomationProfile } from "../../lib/types";

type Category = "general" | "profiles" | "keybinds" | "safety" | "logs";

const categories: Array<{ id: Category; label: string; icon: ReactNode }> = [
  { id: "general", label: "General", icon: <Settings size={16} /> },
  { id: "profiles", label: "Profiles", icon: <UserRound size={16} /> },
  { id: "keybinds", label: "Keybinds", icon: <Keyboard size={16} /> },
  { id: "safety", label: "Runtime / Safety", icon: <Shield size={16} /> },
  { id: "logs", label: "Logs", icon: <ScrollText size={16} /> }
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
  onSettingsChange,
  onProfileChange,
  onClose
}: {
  settings: AppSettings;
  activeProfile: AutomationProfile;
  running: boolean;
  focusEmergency: boolean;
  onSettingsChange: (patch: Partial<AppSettings>) => void;
  onProfileChange: (patch: Partial<AutomationProfile>) => void;
  onClose: () => void;
}) {
  const [category, setCategory] = useState<Category>(focusEmergency ? "keybinds" : "general");
  const panelRef = useRef<HTMLDivElement>(null);
  const firstButtonRef = useRef<HTMLButtonElement>(null);
  const reservedRun = useMemo(() => [settings.emergency_stop_hotkey], [settings.emergency_stop_hotkey]);
  const reservedEmergency = useMemo(() => [settings.run_toggle_hotkey], [settings.run_toggle_hotkey]);

  useEffect(() => {
    firstButtonRef.current?.focus();
  }, []);

  useEffect(() => {
    if (focusEmergency) setCategory("keybinds");
  }, [focusEmergency]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          "button:not([disabled]), input:not([disabled]), select:not([disabled])"
        )
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-background/75 p-6 backdrop-blur-sm">
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Settings"
        className="grid h-[min(720px,calc(100vh-48px))] w-[min(980px,calc(100vw-48px))] grid-cols-[220px_1fr] overflow-hidden rounded-xl border border-border bg-surface shadow-raycast"
      >
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
          <header className="flex min-h-14 items-center justify-between border-b border-border px-5">
            <div>
              <h2 className="text-base font-semibold">{categories.find((item) => item.id === category)?.label}</h2>
              <p className="text-xs text-muted-foreground">Predictable groups, clear current values, and immediate feedback for high-risk controls.</p>
            </div>
            <Button size="icon" variant="ghost" onClick={onClose} aria-label="Close settings">
              <X size={18} />
            </Button>
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
                <SettingRow label="Run sequence toggle" description="Captured reactively; click the field, then press the new key.">
                  <KeybindField
                    label="Run sequence toggle"
                    value={settings.run_toggle_hotkey}
                    disabled={running}
                    reserved={reservedRun}
                    onChange={(run_toggle_hotkey) => onSettingsChange({ run_toggle_hotkey })}
                  />
                </SettingRow>
                <SettingRow label="Emergency stop" description="Global backend listener uses this key while the API is running.">
                  <KeybindField
                    label="Emergency stop"
                    value={settings.emergency_stop_hotkey}
                    disabled={running}
                    reserved={reservedEmergency}
                    onChange={(emergency_stop_hotkey) => onSettingsChange({ emergency_stop_hotkey })}
                  />
                </SettingRow>
                {running ? <p className="text-xs text-warning">Keybinds are locked while automation is running.</p> : null}
              </div>
            ) : null}

            {category === "safety" ? (
              <div className="grid gap-3">
                <SettingRow label="Runtime state" description="Emergency stop stays visible in the header and is also bound by the backend.">
                  <div className="flex items-center gap-2">
                    <Badge tone={running ? "success" : "neutral"}>{running ? "running" : "idle"}</Badge>
                    <Badge tone="danger">Emergency {settings.emergency_stop_hotkey}</Badge>
                  </div>
                </SettingRow>
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
    </div>
  );
}
