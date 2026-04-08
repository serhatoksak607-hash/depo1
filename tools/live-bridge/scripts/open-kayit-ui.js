const { chromium } = require("@playwright/test");

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  page.on("console", msg => console.log("[console]", msg.type(), msg.text()));
  page.on("pageerror", err => console.log("[pageerror]", err.message));
  await page.goto("http://localhost:3000/kayit-ui", { waitUntil: "domcontentloaded" });
  console.log("Kayit UI acildi.");
})();
