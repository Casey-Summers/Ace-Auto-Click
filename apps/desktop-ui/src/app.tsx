import { AlertTriangle, Settings, ShieldCheck, Zap } from "lucide-react";

import { ModeToggle } from "./components/ModeToggle";
import { SplitHotkeyActionButton } from "./components/SplitHotkeyActionButton";
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
    focusKeybind,
    loadDialogOpen,
    loadProfile,
    log,
    openEmergencySettings,
    openProfilesFolder,
    openRunHotkeySettings,
    patchProfile,
    patchSelected,
    patchSettings,
    patchSteps,
    pickCursorPosition,
    pixelLiveRgb,
    pickClickPosition,
    pickStepKey,
    captureWaitingKind,
    captureWaitingStepId,
    profileError,
    profileFiles,
    profileNameError,
    profileSaving,
    requestSaveProfile,
    runToggle,
    executionEvents,
    runtimeInfo,
    inputServiceBusy,
    startElevatedInput,
    stopElevatedInput,
    samplePixel,
    samplingPixelStepId,
    saveDialogOpen,
    selectedProfileFile,
    selectedStep,
    selectStep,
    setFocusEmergency,
    setFocusKeybind,
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
  const elevatedInput = Boolean(runtimeInfo?.elevated || runtimeInfo?.input_broker.connected);

  const header = (
    <header className="mb-4 flex items-center justify-between">
      <div>
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent/15 text-accent shadow-raycast">
            <Zap size={18} />
          </div>
          <h1 className="text-xl font-semibold">Ace Auto Click</h1>
          <ModeToggle value={settings.mode} onChange={setMode} />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" onClick={() => setSettingsOpen(true)}>
          <Settings size={16} />
          Settings
        </Button>
        <SplitHotkeyActionButton
          tone="danger"
          icon={<AlertTriangle size={16} />}
          label="Emergency stop"
          hotkey={settings.emergency_stop_hotkey}
          onAction={emergencyStop}
          onHotkey={state.running ? emergencyStop : openEmergencySettings}
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
    <><div className="mb-2 flex items-center justify-between rounded-xl border border-border bg-surface/55 px-3 py-2 text-xs">
      <div className="flex items-center gap-2">
        <ShieldCheck size={15} className={elevatedInput ? "text-success" : "text-warning"} />
        <span>
          Input: {elevatedInput ? "elevated service" : "local service"}
          {runtimeInfo ? ` · DPI ${runtimeInfo.dpi_awareness} · PID ${runtimeInfo.pid}` : " · checking runtime"}
          {runtimeInfo?.input_broker.last_error ? ` · ${runtimeInfo.input_broker.last_error}` : ""}
        </span>
      </div>
      {runtimeInfo?.input_broker.supported && (!runtimeInfo.elevated || runtimeInfo.input_broker.connected) ? (
        <Button size="sm" variant={runtimeInfo.input_broker.connected ? "ghost" : "default"} disabled={inputServiceBusy || state.running} onClick={runtimeInfo.input_broker.connected ? stopElevatedInput : startElevatedInput}>
          {inputServiceBusy ? "Working…" : runtimeInfo.input_broker.connected ? "Use local input" : "Restart input as administrator"}
        </Button>
      ) : null}
    </div><ProfileManager
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
    /></>
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
      selectedPixelLiveRgb={selectedStep?.type === "pixel_check" ? pixelLiveRgb : null}
      samplingPixelStepId={samplingPixelStepId}
      positionPickingStepId={captureWaitingKind === "position" ? captureWaitingStepId : ""}
      executingStepId={state.current_step_id}
      executingStepState={state.current_step_state}
      executionEvents={executionEvents}
      onSelect={selectStep}
      onLoopsChange={(loops_count, loops_infinite) => patchProfile({ loops_count, loops_infinite, loops: loops_infinite ? 0 : loops_count })}
      onStepsChange={patchSteps}
      onRunToggle={runToggle}
      onRunHotkeyClick={openRunHotkeySettings}
      onApplyCoordinatesFromStep={controller.applyCoordinatesFromStep}
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
      pickingClickPosition={selectedStep?.id === captureWaitingStepId && captureWaitingKind === "position"}
      pickingKey={selectedStep?.id === captureWaitingStepId && captureWaitingKind === "key"}
      pixelLiveRgb={pixelLiveRgb}
      samplingPixel={selectedStep?.id === captureWaitingStepId && captureWaitingKind === "pixel"}
      onChange={patchSelected}
        onSamplePixel={samplePixel}
        onPickClickPosition={pickClickPosition}
        onPickKey={pickStepKey}
        onDuplicate={controller.duplicateSelectedStep}
        onDelete={controller.deleteSelectedStep}
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
          focusKeybind={focusKeybind}
          onSettingsChange={patchSettings}
          onProfileChange={patchProfile}
          onClose={() => {
            setSettingsOpen(false);
            setFocusEmergency(false);
            setFocusKeybind("");
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
