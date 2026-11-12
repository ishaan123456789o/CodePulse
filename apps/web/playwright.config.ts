import { defineConfig, devices } from "@playwright/test";
const database =
  process.env.E2E_DATABASE_URL || "sqlite+aiosqlite:///./codepulse_demo.db";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        ...(process.env.PLAYWRIGHT_CHROME_PATH
          ? {
              launchOptions: {
                executablePath: process.env.PLAYWRIGHT_CHROME_PATH,
              },
            }
          : {}),
      },
    },
  ],
  webServer: [
    {
      command:
        "cd ../api && .venv/bin/alembic upgrade head && .venv/bin/python -m app.workers.cli demo && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8100",
      url: "http://127.0.0.1:8100/api/v1/health",
      timeout: 60000,
      reuseExistingServer: !process.env.CI,
      env: {
        DATABASE_URL: database,
        DEMO_MODE: "true",
        GITHUB_TOKEN: "",
        REDIS_URL: process.env.E2E_REDIS_URL || "redis://127.0.0.1:6379/15",
      },
    },
    {
      command: "node scripts/start.mjs",
      url: "http://127.0.0.1:3100",
      timeout: 60000,
      reuseExistingServer: !process.env.CI,
      env: {
        API_INTERNAL_URL: "http://127.0.0.1:8100",
        PORT: "3100",
        HOSTNAME: "127.0.0.1",
      },
    },
  ],
});
