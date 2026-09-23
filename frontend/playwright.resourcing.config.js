import { defineConfig } from "@playwright/test";

const apiPort = process.env.E2E_API_PORT || "8000";
const appPort = process.env.E2E_APP_PORT || "4173";
const apiBaseUrl = process.env.E2E_API_URL || `http://127.0.0.1:${apiPort}`;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  reporter: "line",
  use: {
    baseURL: `http://127.0.0.1:${appPort}`,
    trace: "retain-on-failure",
  },
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${appPort}`,
    url: `http://127.0.0.1:${appPort}`,
    reuseExistingServer: true,
    timeout: 30_000,
    env: { VITE_PROXY_TARGET: apiBaseUrl },
  },
});
