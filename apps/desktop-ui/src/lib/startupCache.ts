import type { AppSettings, ProfileFile, RuntimeState } from "./types";
import { normalizeSettings } from "./settings";

const CACHE_KEY = "ace-auto-click:startup-cache:v1";

export type StartupCache = {
  settings: AppSettings;
  state: RuntimeState;
  profiles: ProfileFile[];
};

function canUseStorage() {
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

export function loadStartupCache(): StartupCache | null {
  if (!canUseStorage()) return null;
  try {
    const raw = window.localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StartupCache;
    return {
      settings: normalizeSettings(parsed.settings),
      state: parsed.state,
      profiles: Array.isArray(parsed.profiles) ? parsed.profiles : []
    };
  } catch {
    return null;
  }
}

export function saveStartupCache(cache: StartupCache) {
  if (!canUseStorage()) return;
  try {
    window.localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  } catch {
    return;
  }
}
