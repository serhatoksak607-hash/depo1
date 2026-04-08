const { test, expect } = require("@playwright/test");
const { openAuthedPage } = require("./helpers");

test("kayit-ui importance and reason save", async ({ page }) => {
  await openAuthedPage(page, "/kayit-ui");

  const row = page.locator("#cardsBody tr").first();
  await expect(row).toBeVisible();

  await page.locator("#editModeToggle").check();

  const importanceSelect = row.locator('select[data-field="importance_letter"]').first();
  const reasonInput = row.locator('input[data-field="importance_reason"], textarea[data-field="importance_reason"]').first();

  await expect(importanceSelect).toBeVisible();
  await importanceSelect.selectOption("B");
  await row.locator('button[data-field="importance_level"][data-action="plus"]').click();
  await row.locator('button[data-field="importance_level"][data-action="plus"]').click();

  await expect(reasonInput).toBeVisible();
  const reasonText = `pw-${Date.now()}`;
  await reasonInput.fill(reasonText);

  await page.locator("#editModeToggle").uncheck();
  await page.waitForTimeout(1200);

  const visibleImportance = row.locator("td").nth(1);
  const visibleReason = row.locator("td").nth(2);
  await expect(visibleImportance).toContainText("B3");
  await expect(visibleReason).toContainText(reasonText);
});
