import type { ActionStep, AppSettings, PixelSample, ProfileDirectoryStatus, ProfileFile, RuntimeState, SimpleSettings } from "./types";

const API_BASE = import.meta.env.VITE_ACE_API_BASE ?? "http://127.0.0.1:8765";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getState: () => request<RuntimeState>("/state"),
  getSettings: () => request<AppSettings>("/settings"),
  saveSettings: (settings: AppSettings) =>
    request<AppSettings>("/settings", {
      method: "PUT",
      body: JSON.stringify(settings)
    }),
  runSimple: (settings: SimpleSettings) =>
    request<{ state: RuntimeState }>("/run/simple", {
      method: "POST",
      body: JSON.stringify({ settings })
    }),
  runSequence: (steps: ActionStep[], loops = 0) =>
    request<{ state: RuntimeState }>("/run/sequence", {
      method: "POST",
      body: JSON.stringify({ steps, loops })
    }),
  runToggle: () => request<{ state: RuntimeState }>("/run/toggle", { method: "POST" }),
  stop: () => request<{ state: RuntimeState }>("/stop", { method: "POST" }),
  emergencyStop: () =>
    request<{ state: RuntimeState }>("/emergency-stop", { method: "POST" }),
  listProfiles: () => request<ProfileFile[]>("/profiles"),
  profileStatus: () => request<ProfileDirectoryStatus>("/profiles/status"),
  saveProfile: (settings: AppSettings) =>
    request<ProfileFile>("/profiles/save", {
      method: "POST",
      body: JSON.stringify(settings)
    }),
  loadProfile: (fileName: string) =>
    request<AppSettings>(`/profiles/load/${encodeURIComponent(fileName)}`, {
      method: "POST"
    }),
  openProfilesFolder: () =>
    request<{ message: string }>("/profiles/open-folder", { method: "POST" }),
  mousePosition: () => request<{ x: number; y: number }>("/mouse-position"),
  pixel: (x: number, y: number) => request<PixelSample>(`/pixel?x=${x}&y=${y}`)
};
