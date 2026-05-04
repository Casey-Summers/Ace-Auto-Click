import { Activity, FolderOpen, Save, Upload } from "lucide-react";

import { CollapsibleSection } from "../../components/CollapsibleSection";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Select } from "../../components/ui/input";
import type { AutomationProfile, ProfileFile, RuntimeState } from "../../lib/types";

export function ProfileManager({
  state,
  activeProfile,
  profileFiles,
  selectedProfileFile,
  onSelectedProfileFileChange,
  onSaveProfile,
  onLoadProfile,
  onOpenProfilesFolder
}: {
  state: RuntimeState;
  activeProfile: AutomationProfile;
  profileFiles: ProfileFile[];
  selectedProfileFile: string;
  onSelectedProfileFileChange: (fileName: string) => void;
  onSaveProfile: () => void;
  onLoadProfile: () => void;
  onOpenProfilesFolder: () => void;
}) {
  const statusTone = state.last_error ? "danger" : state.running ? "success" : state.recording ? "warning" : "neutral";
  const statusLabel = state.last_error ? "error" : state.running ? "running" : state.recording ? "recording" : "idle";

  return (
    <CollapsibleSection title="Profile Manager" icon={<Activity size={16} />}>
      <div className="grid gap-3 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={statusTone}>
            <Activity size={12} /> {statusLabel}
          </Badge>
          <Badge>{state.status}</Badge>
          <span className="min-w-0 flex-1 truncate text-muted-foreground">
            Active profile: <span className="font-semibold text-foreground">{activeProfile.name}</span>
          </span>
        </div>
        {state.last_error ? <p className="text-xs text-danger">{state.last_error}</p> : null}
        <div className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-2">
          <Select
            aria-label="Saved profiles"
            value={selectedProfileFile}
            onChange={(event) => onSelectedProfileFileChange(event.target.value)}
          >
            <option value="">Select saved profile</option>
            {profileFiles.map((profile) => (
              <option key={profile.file_name} value={profile.file_name}>
                {profile.profile_name}
              </option>
            ))}
          </Select>
          <Button onClick={onSaveProfile}>
            <Save size={16} /> Save Profile
          </Button>
          <Button variant="default" onClick={onLoadProfile} disabled={!selectedProfileFile}>
            <Upload size={16} /> Load Profile
          </Button>
          <Button variant="ghost" onClick={onOpenProfilesFolder}>
            <FolderOpen size={16} /> Open Folder
          </Button>
        </div>
      </div>
    </CollapsibleSection>
  );
}
