import { FolderOpen, Save, Upload } from "lucide-react";

import { ModalFrame } from "../../components/ModalFrame";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import type { AppMode, AutomationProfile, ProfileFile } from "../../lib/types";

function sanitizeProfileFilename(name: string) {
  const stem = name.trim().replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^[.-]+|[.-]+$/g, "") || "profile";
  return `${stem}.aceprofile.json`;
}

function loopLabel(loops: number) {
  return loops === 0 ? "infinite loops" : `${loops} ${loops === 1 ? "loop" : "loops"}`;
}

export function ProfileManager({
  activeProfile,
  saving,
  error,
  profileNameError,
  onProfileNameChange,
  onSaveProfile,
  onOpenLoadProfiles,
  onOpenProfilesFolder
}: {
  activeProfile: AutomationProfile;
  saving: boolean;
  error: string;
  profileNameError: string;
  onProfileNameChange: (name: string) => void;
  onSaveProfile: () => void;
  onOpenLoadProfiles: () => void;
  onOpenProfilesFolder: () => void;
}) {
  const profileNameInvalid = profileNameError.length > 0;

  return (
    <section className="rounded-xl border border-border bg-surface/55 px-3 py-2 shadow-raycast">
      <div className="flex items-center gap-3">
        <Input
          aria-label="Profile name"
          value={activeProfile.name}
          className="h-9 min-w-0 flex-1 border-transparent bg-background/75 font-semibold"
          aria-invalid={profileNameInvalid}
          onChange={(event) => onProfileNameChange(event.target.value)}
        />
        <Button variant="success" onClick={onSaveProfile} disabled={profileNameInvalid || saving}>
          <Save size={16} /> {saving ? "Saving" : "Save"}
        </Button>
        <Button variant="default" onClick={onOpenLoadProfiles}>
          <Upload size={16} /> Load
        </Button>
        <Button size="icon" variant="ghost" onClick={onOpenProfilesFolder} aria-label="Open profiles folder">
          <FolderOpen size={17} />
        </Button>
      </div>
      {profileNameError ? <p className="mt-1 text-xs text-danger">{profileNameError}</p> : null}
      {error ? <p className="mt-1 text-xs text-danger">{error}</p> : null}
    </section>
  );
}

export function ProfileLoadDialog({
  profiles,
  selectedProfileFile,
  error,
  onSelect,
  onLoad,
  onClose
}: {
  profiles: ProfileFile[];
  selectedProfileFile: string;
  error: string;
  onSelect: (fileName: string) => void;
  onLoad: () => void;
  onClose: () => void;
}) {
  return (
    <ModalFrame
      title="Load profile"
      description="Choose a saved profile from the project profiles folder."
      widthClass="w-[min(720px,calc(100vw-48px))]"
      onClose={onClose}
    >
      <div className="grid max-h-[520px] gap-2 overflow-auto p-4">
        {profiles.length ? profiles.map((profile) => {
          const selected = profile.file_name === selectedProfileFile;
          return (
            <button
              key={profile.file_name}
              type="button"
              className={`grid rounded-lg border p-3 text-left transition ${
                selected ? "border-info/45 bg-info/10" : "border-border bg-background/55 hover:bg-surface-strong"
              }`}
              onClick={() => onSelect(profile.file_name)}
            >
              <span className="text-sm font-semibold">{profile.profile_name}</span>
              <span className="mt-1 font-mono text-xs text-muted-foreground">{profile.file_name}</span>
            </button>
          );
        }) : (
          <div className="rounded-lg border border-border bg-background/55 p-4 text-sm text-muted-foreground">
            No saved profiles yet.
          </div>
        )}
        {error ? <p className="text-xs text-danger">{error}</p> : null}
      </div>
      <div className="flex justify-end gap-2 border-t border-border p-4">
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button onClick={onLoad} disabled={!selectedProfileFile}>
          <Upload size={16} /> Load Profile
        </Button>
      </div>
    </ModalFrame>
  );
}

export function ProfileSaveDialog({
  profile,
  mode,
  saving,
  error,
  onCancel,
  onConfirm
}: {
  profile: AutomationProfile;
  mode: AppMode;
  saving: boolean;
  error: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <ModalFrame
      title="Save profile"
      description="Confirm the profile details before exporting to the project profiles folder."
      widthClass="w-[min(520px,calc(100vw-48px))]"
      zClass="z-[60]"
      onClose={onCancel}
    >
      <div className="p-4">
        <dl className="grid gap-2 rounded-lg border border-border bg-background/50 p-3 text-sm">
          <div className="flex justify-between gap-3">
            <dt className="text-muted-foreground">Name</dt>
            <dd className="font-semibold">{profile.name}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-muted-foreground">Mode</dt>
            <dd>{mode === "advanced" ? "Advanced" : "Normal"}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-muted-foreground">Sequence</dt>
            <dd>{profile.steps.length} {profile.steps.length === 1 ? "step" : "steps"} / {loopLabel(profile.loops)}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-muted-foreground">File</dt>
            <dd className="font-mono text-xs">{sanitizeProfileFilename(profile.name)}</dd>
          </div>
        </dl>
        {error ? <p className="mt-3 text-xs text-danger">{error}</p> : null}
      </div>
      <div className="flex justify-end gap-2 border-t border-border p-4">
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
        <Button variant="success" onClick={onConfirm} disabled={saving}>
          <Save size={16} /> {saving ? "Saving" : "Confirm Save"}
        </Button>
      </div>
    </ModalFrame>
  );
}
