const { chromium } = require("@playwright/test");
const { DEFAULT_BASE_URL, loginAndPrepare } = require("./auth-helper");

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();

  try {
    const auth = await loginAndPrepare(page);
    await page.goto(`${DEFAULT_BASE_URL}/kayit-ui`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#cardsBody tr", { timeout: 30000 });
    const listInfo = (await page.locator("#listInfo").innerText()).trim();
    const rowCount = await page.locator("#cardsBody tr").count();
    console.log(JSON.stringify({
      ok: true,
      active_project_id: auth.me?.active_project_id || null,
      active_project_name: auth.me?.active_project_name || null,
      row_count: rowCount,
      list_info: listInfo,
    }));
  } catch (error) {
    console.error(JSON.stringify({ ok: false, error: String(error && error.message || error) }));
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
