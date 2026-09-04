import { defineConfig, devices } from "@playwright/test";

/** Runs against the preview origin so the API and client share a site and the session cookie applies. */
const baseURL = process.env.E2E_BASE_URL ?? process.env.REACT_APP_BACKEND_URL ?? "http://localhost:3000";

const executablePath = process.env.PW_CHROMIUM_PATH;
const storageState = "e2e/.auth/owner.json";

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./e2e/results",
  timeout: 90_000,
  retries: 1,
  workers: 1,
  reporter: [["list"], ["html", { open: "never", outputFolder: "e2e/report" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    contextOptions: { reducedMotion: "reduce" },
    launchOptions: executablePath ? { executablePath } : undefined,
  },
  projects: [
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 }, storageState },
      dependencies: ["setup"],
      testIgnore: /auth\.setup\.ts/,
    },
    {
      name: "tablet",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1024, height: 768 }, hasTouch: true, storageState },
      dependencies: ["setup"],
      testIgnore: /auth\.setup\.ts/,
    },
    {
      name: "iphone",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 390, height: 844 },
        hasTouch: true,
        isMobile: true,
        storageState,
      },
      dependencies: ["setup"],
      testIgnore: /auth\.setup\.ts/,
    },
    {
      name: "android",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 412, height: 915 },
        hasTouch: true,
        isMobile: true,
        storageState,
      },
      dependencies: ["setup"],
      testIgnore: /auth\.setup\.ts/,
    },
    {
      name: "narrow",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 320, height: 700 },
        hasTouch: true,
        isMobile: true,
        storageState,
      },
      dependencies: ["setup"],
      testIgnore: /auth\.setup\.ts/,
    },
  ],
});
