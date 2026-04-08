const { chromium } = require("@playwright/test");

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  page.on("console", msg => console.log("[console]", msg.type(), msg.text()));
  page.on("pageerror", err => console.log("[pageerror]", err.message));

  await page.goto("http://localhost:3000/kayit-ui", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);

  const before = await page.evaluate(() => {
    const th = document.querySelector("thead tr th");
    const filter = document.querySelector(".filter-row th");
    if (!th || !filter) return null;
    return {
      thTop: Math.round(th.getBoundingClientRect().top),
      filterTop: Math.round(filter.getBoundingClientRect().top),
      scrollY: Math.round(window.scrollY)
    };
  });

  await page.evaluate(() => window.scrollTo(0, 1400));
  await page.waitForTimeout(400);

  const after = await page.evaluate(() => {
    const th = document.querySelector("thead tr th");
    const filter = document.querySelector(".filter-row th");
    if (!th || !filter) return null;
    return {
      thTop: Math.round(th.getBoundingClientRect().top),
      filterTop: Math.round(filter.getBoundingClientRect().top),
      scrollY: Math.round(window.scrollY),
      bodyHeight: Math.round(document.body.scrollHeight)
    };
  });

  console.log(JSON.stringify({ before, after }, null, 2));
  await page.screenshot({ path: "tools/live-bridge/check-kayit-sticky.png", fullPage: false });
  await browser.close();
})();
