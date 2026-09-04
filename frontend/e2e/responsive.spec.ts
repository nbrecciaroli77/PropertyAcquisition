import { expect, test } from "@playwright/test";

const screens: [string, string][] = [
  ["/app/today", "today"],
  ["/app/brief", "brief"],
  ["/app/brief/locations", "brief-locations"],
  ["/app/journeys/new", "journey-onboarding"],
  ["/app/discover", "discover"],
  ["/app/pipeline", "pipeline"],
  ["/app/compare", "compare"],
  ["/app/saved", "saved"],
  ["/app/tasks", "tasks"],
  ["/app/agents", "agents"],
  ["/app/sources", "sources"],
  ["/app/settings", "settings"],
];

const publicScreens: [string, string][] = [
  ["/", "welcome"],
  ["/about", "about"],
  ["/signup", "sign-up"],
  ["/verify-pending?email=owner@propertyacquisition-demo.com", "verify-pending"],
  ["/forgot-password", "forgot-password"],
  ["/dev/outbox", "dev-outbox"],
];

async function assertNoOverflow(page: import("@playwright/test").Page, label: string) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, `horizontal overflow of ${overflow}px at ${label}`).toBeLessThanOrEqual(0);
}

test.describe("public screens", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  for (const [path, name] of publicScreens) {
    test(`${name} renders without horizontal overflow and has one h1`, async ({ page }, testInfo) => {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      // Supabase sits in another region, so first paint can trail the navigation by a second or two.
      await expect(page.locator("h1")).toHaveCount(1, { timeout: 45_000 });
      await assertNoOverflow(page, testInfo.project.name);
      if (testInfo.project.name !== "narrow") {
        await page.screenshot({ path: `e2e/screenshots/${testInfo.project.name}/${name}.png`, fullPage: true });
      }
    });
  }

  test("welcome: providers disabled and the account route is offered", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("sign-in-google")).toBeDisabled();
    await expect(page.getByTestId("sign-in-apple")).toBeDisabled();
    await page.getByTestId("create-account-link").click();
    await expect(page.getByTestId("sign-up-form")).toBeVisible();
  });

  test("an anonymous deep link into the shell returns to sign in", async ({ page }) => {
    await page.goto("/app/brief");
    await expect(page.getByTestId("welcome-page")).toBeVisible();
  });
});

test.describe("authenticated screens", () => {
  for (const [path, name] of screens) {
    test(`${name} renders without horizontal overflow and has one h1`, async ({ page }, testInfo) => {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      // Supabase sits in another region, so first paint can trail the navigation by a second or two.
      await expect(page.locator("h1")).toHaveCount(1, { timeout: 45_000 });
      await assertNoOverflow(page, testInfo.project.name);
      if (testInfo.project.name !== "narrow") {
        await page.screenshot({ path: `e2e/screenshots/${testInfo.project.name}/${name}.png`, fullPage: true });
      }
    });
  }

  for (const [suffix, name] of [["", "property-detail"], ["?view=match", "property-match"]] as const) {
    test(`${name} renders without horizontal overflow and has one h1`, async ({ page }, testInfo) => {
      await page.goto("/app/discover", { waitUntil: "domcontentloaded" });
      const link = page.locator('[data-legacy-ref="DEMO-006"] a[data-testid^="property-card-link"]');
      await link.waitFor({ timeout: 45_000 });
      const href = await link.getAttribute("href");
      await page.goto(`${href}${suffix}`, { waitUntil: "domcontentloaded" });
      await expect(page.getByTestId("property-header")).toBeVisible({ timeout: 45_000 });
      await expect(page.locator("h1")).toHaveCount(1);
      await assertNoOverflow(page, testInfo.project.name);
      if (testInfo.project.name !== "narrow") {
        await page.screenshot({ path: `e2e/screenshots/${testInfo.project.name}/${name}.png`, fullPage: true });
      }
    });
  }

  test("shell navigation adapts by viewport", async ({ page }, testInfo) => {
    await page.goto("/app/today");
    await expect(page.getByTestId("app-shell")).toBeVisible({ timeout: 45_000 });
    const rail = page.getByTestId("desktop-rail");
    const bottom = page.getByTestId("bottom-nav");
    if (testInfo.project.name === "desktop" || testInfo.project.name === "tablet") {
      await expect(rail).toBeVisible();
      await expect(bottom).toBeHidden();
    } else {
      await expect(bottom).toBeVisible();
      await expect(rail).toBeHidden();
      await expect(bottom.getByRole("link")).toHaveText(["Today", "Properties", "Saved", "More"]);
    }
  });

  test("keyboard: skip link reaches main content", async ({ page }) => {
    await page.goto("/app/today");
    await expect(page.getByTestId("app-shell")).toBeVisible({ timeout: 45_000 });
    await page.getByTestId("today-header").waitFor({ timeout: 45_000 });
    await page.keyboard.press("Tab");
    await expect(page.getByText("Skip to main content")).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("#main")).toBeFocused();
  });

  test("the brief editor exposes weights, blockers and version history", async ({ page }) => {
    await page.goto("/app/brief");
    await expect(page.getByTestId("weights-total")).toBeVisible({ timeout: 45_000 });
    await page.getByTestId("brief-toggle-versions").click();
    await expect(page.getByTestId("version-history")).toBeVisible({ timeout: 45_000 });
  });
});
