const { test, expect } = require("@playwright/test");
const { openAuthedPage } = require("./helpers");

test("kayit-ui authenticated smoke", async ({ page }) => {
  await openAuthedPage(page, "/kayit-ui");
  await expect(page.locator("#cardsBody")).toBeVisible();
  await expect(page.locator("#listInfo")).toBeVisible();
  await expect(page.locator("#cardsBody tr").first()).toBeVisible();
});
