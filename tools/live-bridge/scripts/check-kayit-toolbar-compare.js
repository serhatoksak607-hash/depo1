const { chromium } = require("@playwright/test");
const { loginAndPrepare, DEFAULT_BASE_URL } = require("./auth-helper");

async function inspectPage(page, path) {
  await page.goto(`${DEFAULT_BASE_URL}${path}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1200);
  return page.evaluate(() => {
    const pick = (sel) => document.querySelector(sel);
    const rectOf = (sel) => {
      const el = pick(sel);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {
        x: Math.round(r.x),
        y: Math.round(r.y),
        width: Math.round(r.width),
        height: Math.round(r.height),
        right: Math.round(r.right),
      };
    };
    return {
      title: document.title,
      toolbarRow: rectOf(".toolbar-row"),
      toolbarLeft: rectOf(".toolbar-left"),
      toolbarRight: rectOf(".toolbar-right"),
      toolbarStack: rectOf(".toolbar-right-stack"),
      toolbarActions: rectOf(".toolbar-right-actions"),
      warningSummary: rectOf("#warningSummary, #companyWarningSummary"),
      bodyWidth: Math.round(document.documentElement.clientWidth),
      bodyText: document.body.innerText.slice(0, 500),
    };
  });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1680, height: 1200 } });
  const page = await context.newPage();
  try {
    await loginAndPrepare(page);
    const people = await inspectPage(page, "/kayit-ui");
    await page.screenshot({ path: "kayit-toolbar-debug.png", fullPage: true });
    const companies = await inspectPage(page, "/kayit-sponsor-firmalar-ui");
    await page.screenshot({ path: "firma-toolbar-debug.png", fullPage: true });
    console.log(JSON.stringify({ people, companies }, null, 2));
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
