import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/visual",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  snapshotPathTemplate: "{testDir}/__screenshots__/{arg}{ext}",
  outputDir: ".playwright/visual-results",
  expect: { toHaveScreenshot: { animations: "disabled", caret: "hide", maxDiffPixelRatio: 0.002 } },
  use: {
    baseURL: "http://127.0.0.1:4274",
    browserName: "chromium",
    colorScheme: "light",
    locale: "en-US",
    timezoneId: "America/New_York",
  },
});
