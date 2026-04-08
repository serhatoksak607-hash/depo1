const { chromium } = require("@playwright/test");

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  page.on("console", msg => console.log("[console]", msg.type(), msg.text()));
  page.on("pageerror", err => console.log("[pageerror]", err.message));

  await page.goto("http://localhost:3000/kayit-sponsor-firmalar-ui", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);

  const before = await page.evaluate(() => {
    const cb = document.querySelector("tbody .row-select-company");
    const info = document.getElementById("info");
    return {
      found: !!cb,
      checked: cb ? cb.checked : null,
      info: info ? info.textContent : null
    };
  });

  if (before.found) {
    await page.click("tbody .row-select-company");
    await page.waitForTimeout(500);
  }

  const after = await page.evaluate(() => {
    const cb = document.querySelector("tbody .row-select-company");
    const info = document.getElementById("info");
    return {
      found: !!cb,
      checked: cb ? cb.checked : null,
      info: info ? info.textContent : null
    };
  });

  console.log(JSON.stringify({ before, after }, null, 2));
  await page.screenshot({ path: "tools/live-bridge/check-firmalar-checkbox.png", fullPage: false });
  await browser.close();
})();
