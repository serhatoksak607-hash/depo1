const { chromium } = require("@playwright/test");
const { DEFAULT_BASE_URL, loginAndPrepare } = require("./auth-helper");

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();

  try {
    await loginAndPrepare(page);
    await page.goto(`${DEFAULT_BASE_URL}/kayit-ui`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#cardsBody tr", { timeout: 30000 });

    const row = page.locator("#cardsBody tr").first();
    const initialImportance = ((await row.locator("td").nth(1).innerText()).trim() || "");
    const initialReason = ((await row.locator("td").nth(2).innerText()).trim() || "");

    await page.evaluate(() => {
      const el = document.querySelector("#editModeToggle");
      if (!el) throw new Error("editModeToggle not found");
      el.checked = true;
      el.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await row.locator('select.importance-letter[data-field="importance_level"]').first().selectOption("B");
    await row.locator('button.importance-step[data-field="importance_level"][data-dir="1"]').first().click();
    await row.locator('button.importance-step[data-field="importance_level"][data-dir="1"]').first().click();

    const reasonValue = `pw-${Date.now()}`;
    const reasonInput = row.locator('input[data-field="importance_reason"], textarea[data-field="importance_reason"]').first();
    await reasonInput.fill(reasonValue);
    await page.evaluate(() => {
      const el = document.querySelector("#editModeToggle");
      if (!el) throw new Error("editModeToggle not found");
      el.checked = false;
      el.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await page.waitForTimeout(1500);

    const visibleImportance = ((await row.locator("td").nth(1).innerText()).trim() || "");
    const visibleReason = ((await row.locator("td").nth(2).innerText()).trim() || "");

    console.log(JSON.stringify({
      ok: true,
      before: { importance: initialImportance, reason: initialReason },
      after: { importance: visibleImportance, reason: visibleReason },
      expected_reason: reasonValue,
    }));
  } catch (error) {
    console.error(JSON.stringify({ ok: false, error: String(error && error.message || error) }));
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
