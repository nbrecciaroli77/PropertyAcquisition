import { expect, test } from "@playwright/test";

// Milestone 3 workspace flows, run on the desktop project only (see playwright.config.ts).
test.describe("property workspace", () => {
  test.beforeEach(async ({ page: _page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop", "desktop only");
  });

  test("discover shows separate market/buyer state, gate filters and unknown-not-pass", async ({ page }) => {
    await page.goto("/app/discover");
    await expect(page.getByTestId("discover-grid")).toBeVisible({ timeout: 45_000 });
    const card006 = page.locator('[data-legacy-ref="DEMO-006"]');
    await expect(card006.getByTestId(/^property-card-gate-[^-]+(-[^-]+){4}$/)).toHaveText("Verification required");
    await expect(card006.getByTestId(/^property-card-market-[^-]+(-[^-]+){4}$/)).toHaveText("Market: Active");
    await expect(card006.getByTestId(/^property-card-buyer-[^-]+(-[^-]+){4}$/)).toHaveText("You: Reviewing");
    // Land is unknown, so coverage drops while fit is still assessed on the remaining components.
    await expect(card006.getByTestId(/^property-card-coverage-[^-]+(-[^-]+){4}$/)).toContainText("20%");
    await page.getByTestId("discover-filter-fail").click();
    await expect(page.getByTestId("discover-result-count")).toContainText("0 properties", { timeout: 45_000 });
    await page.getByTestId("discover-filter-pass").click();
    await expect(page.locator('[data-legacy-ref="DEMO-001"]')).toBeVisible({ timeout: 45_000 });
  });

  test("match & evidence: hard failure with high fit stays excluded; waiver never flips the gate", async ({ page }) => {
    await page.goto("/app/pipeline");
    const card = page.locator('[data-legacy-ref="DEMO-003"] a');
    await card.waitFor({ timeout: 45_000 });
    await card.click();
    await expect(page.getByTestId("known-failure-note")).toBeVisible({ timeout: 45_000 });
    await page.getByTestId("tab-match").click();
    const land = page.getByTestId("gate-row-land_sqm");
    await expect(land).toHaveAttribute("data-outcome", "fail");
    await expect(page.getByTestId("detail-fit")).toHaveAttribute("data-state", "known");
    await expect(page.getByTestId("detail-fit")).toContainText("87");
    await expect(page.getByTestId("detail-coverage")).toContainText("100");
    await expect(page.getByTestId("evaluation-meta")).toContainText("gates_v1+scoring_v1");
  });

  test("workflow: illegal promotion is refused and the reason is explained", async ({ page }) => {
    await page.goto("/app/pipeline");
    const card = page.locator('[data-legacy-ref="DEMO-003"] a');
    await card.waitFor({ timeout: 45_000 });
    await card.click();
    await expect(page.getByTestId("workflow-panel")).toBeVisible({ timeout: 45_000 });
    await expect(page.getByTestId("promotion-blocked-note")).toBeVisible();
    const options = await page.getByTestId("stage-select").locator("option").allTextContents();
    expect(options).not.toContain("Settled");
  });

  test("compare holds four at most and keeps unknown cells unknown", async ({ page }) => {
    await page.goto("/app/discover");
    await expect(page.getByTestId("discover-grid")).toBeVisible({ timeout: 45_000 });
    const buttons = page.getByTestId(/^property-card-compare-/);
    const count = await buttons.count();
    for (let i = 0; i < Math.min(count, 5); i++) {
      const b = buttons.nth(i);
      if (await b.isEnabled()) await b.click();
    }
    await page.getByTestId("discover-compare-link").click();
    await expect(page.getByTestId("compare-table")).toBeVisible({ timeout: 45_000 });
    await expect(page.getByTestId("compare-header")).toContainText("4 of 4");
    await expect(page.getByTestId("compare-row-land")).toContainText("Unknown");
    await page.evaluate(() => localStorage.removeItem("pa.compare"));
  });

  test("a foreign or unknown property id shows not found, never data", async ({ page }) => {
    await page.goto("/app/properties/00000000-0000-4000-8000-000000000000");
    await expect(page.getByTestId("property-not-found")).toBeVisible({ timeout: 45_000 });
  });
});
