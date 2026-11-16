import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/ui",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  use: {
    baseURL: "http://127.0.0.1:1420",
    viewport: { width: 1440, height: 930 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  reporter: [["list"], ["html", { open: "never" }]],
  webServer: [
    {
      command:
        "node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 1420 --strictPort",
      url: "http://127.0.0.1:1420",
      reuseExistingServer: process.env.FRAMEATLAS_UI_REUSE === "1",
      timeout: 60_000,
    },
    {
      command:
        "..\\.venv\\Scripts\\python.exe ..\\scripts\\serve_desktop_fixture.py",
      port: 18765,
      reuseExistingServer: false,
      timeout: 90_000,
    },
  ],
});
