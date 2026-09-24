export const WORKSPACE_PREFERENCES_KEY = "ms-sales-dashboard.preferences.v1";
export const DEFAULT_WORKSPACE_PREFERENCES = {
  defaultPod: "All",
  compactTooltips: true,
  confirmChanges: true,
};

const browserStorage = () => {
  try { return globalThis.localStorage; } catch { return null; }
};

export function loadWorkspacePreferences(storage) {
  const target = storage === undefined ? browserStorage() : storage;
  if (!target) return { ...DEFAULT_WORKSPACE_PREFERENCES };
  try {
    const value = JSON.parse(target.getItem(WORKSPACE_PREFERENCES_KEY) || "{}");
    return {
      defaultPod: typeof value.defaultPod === "string" && value.defaultPod.trim() ? value.defaultPod : DEFAULT_WORKSPACE_PREFERENCES.defaultPod,
      compactTooltips: typeof value.compactTooltips === "boolean" ? value.compactTooltips : DEFAULT_WORKSPACE_PREFERENCES.compactTooltips,
      confirmChanges: typeof value.confirmChanges === "boolean" ? value.confirmChanges : DEFAULT_WORKSPACE_PREFERENCES.confirmChanges,
    };
  } catch {
    return { ...DEFAULT_WORKSPACE_PREFERENCES };
  }
}

export function saveWorkspacePreferences(preferences, storage) {
  const normalized = { ...DEFAULT_WORKSPACE_PREFERENCES, ...preferences };
  try { (storage === undefined ? browserStorage() : storage)?.setItem(WORKSPACE_PREFERENCES_KEY, JSON.stringify(normalized)); } catch { /* Preferences remain active for this session. */ }
  return normalized;
}

export function resetWorkspacePreferences(storage) {
  try { (storage === undefined ? browserStorage() : storage)?.removeItem(WORKSPACE_PREFERENCES_KEY); } catch { /* Reset still applies in memory. */ }
  return { ...DEFAULT_WORKSPACE_PREFERENCES };
}

export function resolveInitialPod(search, preferences = DEFAULT_WORKSPACE_PREFERENCES, section = "Executive View") {
  const query = new URLSearchParams(search);
  const requested = query.has("pod") ? query.get("pod") : preferences.defaultPod;
  return typeof requested === "string" && requested.trim() ? requested : "All";
}
