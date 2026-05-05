import { Settings, Zap } from "lucide-react";

import { EmergencyStopButton } from "./components/EmergencyStopButton";
import { ModeToggle } from "./components/ModeToggle";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { ActionLibrary } from "./features/actions/ActionLibrary";
import { EventLogPanel } from "./features/log/EventLogPanel";
import { ProfileLoadDialog, ProfileManager, ProfileSaveDialog } from "./features/runtime/RuntimePanel";
import { SettingsModal } from "./features/settings/SettingsPanel";
import { NormalRunPanel } from "./features/sequence/NormalRunPanel";
import { NormalDetailsPanel, StepDetailsPanel } from "./features/sequence/StepDetailsPanel";
import { SequenceBuilder } from "./features/sequence/SequenceBuilder";
import { useAppController } from "./hooks/useAppController";
import { AppShell } from "./layouts/AppShell";

export function App() {
  const controller = useAppController();
  const {
    activeProfile,
    confirmSaveProfile,
    emergencyStop,
    focusEmergency,
    loadDialogOpen,
    loadProfile,
    log,
    openEmergencySettings,
    openProfilesFolder,
    patchProfile,
    patchSelected,
    patchSettings,
    patchSteps,
    pickCursorPosition,
    pickClickPosition,
    pickingClickStepId,
    profileError,
    profileFiles,
    profileNameError,
    profileSaving,
    requestSaveProfile,
    runToggle,
    samplePixel,
    saveDialogOpen,
    selectedProfileFile,
    selectedStep,
    setFocusEmergency,
    setLoadDialogOpen,
    setProfileError,
    setSaveDialogOpen,
    setSelectedId,
    setSelectedProfileFile,
    setSettingsOpen,
    settings,
    settingsOpen,
    state,
    setMode
  } = controller;

  const header = (
    <header className="mb-4 flex items-center justify-between">
      <div>
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent/15 text-accent shadow-raycast">
            <Zap size={18} />
          </div>
          <h1 className="text-xl font-semibold">Ace Auto Click</h1>
          <ModeToggle value={settings.mode} onChange={setMode} />
          <Badge tone={state.running ? "success" : "neutral"}>{state.status}</Badge>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Automation workspace for precise mouse, keyboard, pixel, and sequence control.
        </p>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" onClick={() => setSettingsOpen(true)}>
          <Settings size={16} />
          Settings
        </Button>
        <EmergencyStopButton
          hotkey={settings.emergency_stop_hotkey}
          running={state.running}
          onStop={emergencyStop}
          onKeybindClick={openEmergencySettings}
        />
      </div>
    </header>
  );

  const left = (
    <>
      <ActionLibrary onAdd={controller.addStep} />
      <div className="mt-auto">{settings.show_event_log ? <EventLogPanel log={log} /> : null}</div>
    </>
  );

  const centerTop = (
    <ProfileManager
      activeProfile={activeProfile}
      saving={profileSaving}
      error={profileError}
      profileNameError={profileNameError}
      onProfileNameChange={(name) => patchProfile({ name })}
      onSaveProfile={requestSaveProfile}
      onOpenLoadProfiles={() => {
        setProfileError("");
        setLoadDialogOpen(true);
      }}
      onOpenProfilesFolder={openProfilesFolder}
    />
  );

  const center = settings.mode === "advanced" ? (
    <SequenceBuilder
      steps={activeProfile.steps}
      loops={activeProfile.loops}
      loopsCount={activeProfile.loops_count}
      loopsInfinite={activeProfile.loops_infinite}
      running={state.running}
      runHotkey={settings.run_toggle_hotkey}
      selectedId={selectedStep?.id ?? ""}
      onSelect={setSelectedId}
      onLoopsChange={(loops_count, loops_infinite) => patchProfile({ loops_count, loops_infinite, loops: loops_infinite ? 0 : loops_count })}
      onStepsChange={patchSteps}
      onRunToggle={runToggle}
    />
  ) : (
    <NormalRunPanel
      normal={activeProfile.normal}
      loops={activeProfile.loops}
      running={state.running}
      runHotkey={settings.run_toggle_hotkey}
      onLoopsChange={(loops) => patchProfile({ loops })}
      onRunToggle={runToggle}
    />
  );

  const right = settings.mode === "normal" ? (
    <NormalDetailsPanel
      normal={activeProfile.normal}
      onChange={(normalPatch) => patchProfile({ normal: { ...activeProfile.normal, ...normalPatch } })}
    />
  ) : (
    <StepDetailsPanel
      step={selectedStep}
      pickCursorPosition={pickCursorPosition}
      pickingClickPosition={selectedStep?.id === pickingClickStepId}
      onChange={patchSelected}
      onSamplePixel={samplePixel}
      onPickClickPosition={pickClickPosition}
    />
  );

  return (
    <>
      <AppShell header={header} left={left} centerTop={centerTop} center={center} right={right} />
      {settingsOpen ? (
        <SettingsModal
          settings={settings}
          activeProfile={activeProfile}
          running={state.running}
          focusEmergency={focusEmergency}
          onSettingsChange={patchSettings}
          onProfileChange={patchProfile}
          onClose={() => {
            setSettingsOpen(false);
            setFocusEmergency(false);
          }}
        />
      ) : null}
      {saveDialogOpen ? (
        <ProfileSaveDialog
          profile={activeProfile}
          mode={settings.mode}
          saving={profileSaving}
          error={profileError}
          onCancel={() => setSaveDialogOpen(false)}
          onConfirm={confirmSaveProfile}
        />
      ) : null}
      {loadDialogOpen ? (
        <ProfileLoadDialog
          profiles={profileFiles}
          selectedProfileFile={selectedProfileFile}
          error={profileError}
          onSelect={setSelectedProfileFile}
          onLoad={loadProfile}
          onClose={() => setLoadDialogOpen(false)}
        />
      ) : null}
    </>
  );
}
