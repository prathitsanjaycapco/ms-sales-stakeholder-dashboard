import { spawn } from "node:child_process";
import process from "node:process";

import { createServer } from "vite";

const server = await createServer({
  clearScreen: false,
  server: { host: "127.0.0.1", port: 4274, strictPort: true },
});

let exitCode = 1;
try {
  await server.listen();
  const playwright = spawn(
    process.execPath,
    ["node_modules/@playwright/test/cli.js", "test", "-c", "playwright.visual.config.js", ...process.argv.slice(2)],
    { cwd: process.cwd(), env: process.env, stdio: "inherit" },
  );
  exitCode = await new Promise((resolve, reject) => {
    playwright.once("error", reject);
    playwright.once("exit", (code, signal) => resolve(code ?? (signal ? 1 : 0)));
  });
} finally {
  await server.close();
}

process.exitCode = exitCode;
