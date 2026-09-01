import { describe, expect, it } from "vitest";
import {
  DEFAULT_WORKSPACE_PREFERENCES, WORKSPACE_PREFERENCES_KEY, loadWorkspacePreferences,
  resetWorkspacePreferences, resolveInitialPod, saveWorkspacePreferences,
} from "./workspacePreferences";

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: (key) => values.delete(key) };
}

describe("workspace preferences", () => {
  it("persists valid values and resets to documented defaults", () => {
    const storage = memoryStorage();
    saveWorkspacePreferences({ defaultPod: "MSIM", compactTooltips: false, confirmChanges: false }, storage);
    expect(loadWorkspacePreferences(storage)).toEqual({ defaultPod: "MSIM", compactTooltips: false, confirmChanges: false });
    expect(resetWorkspacePreferences(storage)).toEqual(DEFAULT_WORKSPACE_PREFERENCES);
    expect(storage.getItem(WORKSPACE_PREFERENCES_KEY)).toBeNull();
  });

  it("lets an explicit URL pod override the stored default", () => {
    const preferences = { ...DEFAULT_WORKSPACE_PREFERENCES, defaultPod: "MSIM" };
    expect(resolveInitialPod("", preferences)).toBe("MSIM");
    expect(resolveInitialPod("?pod=ISG", preferences)).toBe("ISG");
    expect(resolveInitialPod("?pod=All", preferences, "Stakeholder Map")).toBe("All");
    expect(resolveInitialPod("", DEFAULT_WORKSPACE_PREFERENCES, "Stakeholder Map")).toBe("All");
  });
});
