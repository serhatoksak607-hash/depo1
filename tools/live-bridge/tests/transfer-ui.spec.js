const { test, expect } = require("@playwright/test");

test("transfer-ui smoke", async ({ page }) => {
  await page.goto("/transfer-ui", { waitUntil: "domcontentloaded" });
  await expect(page.locator("body")).toBeVisible();
});
