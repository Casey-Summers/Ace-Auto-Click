import { Settings } from "lucide-react";

import { CollapsibleSection } from "../../components/CollapsibleSection";
import { KeybindField } from "../../components/KeybindField";
import { Button } from "../../components/ui/button";
import { Input, Select } from "../../components/ui/input";
import type { AppSettings, AutomationProfile } from "../../lib/types";

export function SettingsPanel({
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
  return (
    <div className="grid gap-3">
      <CollapsibleSection
        title="Settings"
        icon={<Settings size={16} />}
        actions={<Button size="sm" variant="ghost" onClick={onClose}>Close</Button>}
      >
        <div className="grid gap-3">
          <label className="grid gap-1 text-xs text-muted-foreground">
            <span>Theme</span>
            <Select value={settings.theme} onChange={(event) => onSettingsChange({ theme: event.target.value as "dark" | "light" })}>
              <option value="dark">Dark</option>
              <option value="light">Light ready</option>
            </Select>
          </label>
          <label className="grid gap-1 text-xs text-muted-foreground">
            <span>Default mode</span>
            <Select value={settings.mode} onChange={(event) => onSettingsChange({ mode: event.target.value as "normal" | "advanced" })}>
              <option value="normal">Normal</option>
              <option value="advanced">Advanced</option>
            </Select>
          </label>
          <label className="flex items-center justify-between gap-3 rounded-lg bg-background/70 p-2 text-sm">
            <span>Show event log</span>
            <input
              type="checkbox"
              checked={settings.show_event_log}
              onChange={(event) => onSettingsChange({ show_event_log: event.target.checked })}
            />
          </label>
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Keybinds" icon={<Settings size={16} />} defaultOpen={focusEmergency}>
        <div className="grid gap-3">
          <KeybindField
            label="Run sequence toggle"
            value={settings.run_toggle_hotkey}
            disabled={running}
            onChange={(run_toggle_hotkey) => onSettingsChange({ run_toggle_hotkey })}
          />
          <KeybindField
            label="Emergency stop"
            value={settings.emergency_stop_hotkey}
            disabled={running}
            onChange={(emergency_stop_hotkey) => onSettingsChange({ emergency_stop_hotkey })}
          />
          {running ? <p className="text-xs text-warning">Keybinds are locked while automation is running.</p> : null}
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Profile" icon={<Settings size={16} />}>
        <div className="grid gap-3">
          <label className="grid gap-1 text-xs text-muted-foreground">
            <span>Profile name</span>
            <Input value={activeProfile.name} onChange={(event) => onProfileChange({ name: event.target.value })} />
          </label>
          <label className="grid gap-1 text-xs text-muted-foreground">
            <span>Active profile</span>
            <Select value={settings.active_profile_id} onChange={(event) => onSettingsChange({ active_profile_id: event.target.value })}>
              {settings.profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>{profile.name}</option>
              ))}
            </Select>
          </label>
        </div>
      </CollapsibleSection>
    </div>
  );
}
