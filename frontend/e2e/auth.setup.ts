import { expect, test as setup } from "@playwright/test";

const email = process.env.E2E_EMAIL ?? "owner@propertyacquisition-demo.com";
const password = process.env.E2E_PASSWORD ?? "Prototype2026pass";

/** Signs in with the seeded synthetic owner and stores the session for the viewport projects. */
setup("authenticate the seeded owner", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("sign-in-email").fill(email);
  await page.getByTestId("sign-in-password").fill(password);
  await page.getByTestId("sign-in-submit").click();
  await expect(page.getByTestId("app-shell")).toBeVisible({ timeout: 30_000 });
  await page.context().storageState({ path: "e2e/.auth/owner.json" });
});
