const { test, expect } = require("@playwright/test");

test("kayit-ui smoke", async ({ page }) => {
  await page.goto("/kayit-ui", { waitUntil: "domcontentloaded" });
  await expect(page.locator("text=Kişi Kartları")).toBeVisible();
  await expect(page.locator("#cardsBody")).toBeVisible();
  await expect(page.locator("#listInfo")).toBeVisible();
});
