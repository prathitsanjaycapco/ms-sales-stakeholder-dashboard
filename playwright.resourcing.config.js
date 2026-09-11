import { defineConfig } from "@playwright/test";

const apiPort = process.env.E2E_API_PORT || "8000";
const appPort = process.env.E2E_APP_PORT || "4173";
const externalServers = process.env.E2E_EXTERNAL_SERVERS === "true";

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
  webServer: externalServers ? undefined : [
    {
      command: `python -m uvicorn backend.main:app --host 127.0.0.1 --port ${apiPort}`,
      url: `http://127.0.0.1:${apiPort}/api/health`,
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${appPort}`,
      url: `http://127.0.0.1:${appPort}`,
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
});
