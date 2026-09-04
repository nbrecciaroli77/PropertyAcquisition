import { expect, test } from "@playwright/test";

const screens: [string, string][] = [
  ["/", "welcome"],
  ["/about", "about"],
  ["/app/today", "today"],
  ["/app/discover", "discover"],
  ["/app/pipeline", "pipeline"],
  ["/app/compare", "compare"],
  ["/app/saved", "saved"],
  ["/app/tasks", "tasks"],
  ["/app/agents", "agents"],
  ["/app/sources", "sources"],
  ["/app/settings", "settings"],
  ["/app/properties/demo-006", "property-detail"],
];

for (const [path, name] of screens) {
  test(`${name} renders without horizontal overflow and has one h1`, async ({ page }, testInfo) => {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toHaveCount(1);

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `horizontal overflow of ${overflow}px at ${testInfo.project.name}`).toBeLessThanOrEqual(0);

    if (testInfo.project.name !== "narrow") {
      await page.screenshot({ path: `e2e/screenshots/${testInfo.project.name}/${name}.png`, fullPage: true });
    }
  });
}

test("shell navigation adapts by viewport", async ({ page }, testInfo) => {
  await page.goto("/app/today");
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
  await page.keyboard.press("Tab");
  await expect(page.getByText("Skip to main content")).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();
});

test("welcome: provider buttons disabled, preview link enters shell", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("sign-in-google")).toBeDisabled();
  await expect(page.getByTestId("sign-in-apple")).toBeDisabled();
  await page.getByTestId("preview-shell-link").click();
  await expect(page.getByTestId("today-header")).toBeVisible();
  await expect(page.getByTestId("synthetic-data-banner")).toBeVisible();
});
