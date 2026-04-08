const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");
const { DEFAULT_BASE_URL, loginAndPrepare } = require("./auth-helper");

async function inspect(page, urlPath, targetSelector, screenshotName) {
  await page.goto(`${DEFAULT_BASE_URL}${urlPath}`, { waitUntil: "networkidle" });
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.waitForTimeout(1200);
  await page.locator(targetSelector).first().waitFor({ state: "visible", timeout: 15000 });

  const data = await page.evaluate((selector) => {
    const wrap = document.querySelector(selector);
    const th = document.querySelector(`${selector} thead th`);
    const td = document.querySelector(`${selector} tbody td`);
    const read = (el) => {
      if (!el) return null;
      const cs = getComputedStyle(el);
      return {
        borderTop: cs.borderTop,
        borderRight: cs.borderRight,
        borderBottom: cs.borderBottom,
        borderLeft: cs.borderLeft,
        background: cs.backgroundColor,
      };
    };
    return {
      wrap: read(wrap),
      th: read(th),
      td: read(td),
    };
  }, targetSelector);

  const outDir = path.join(__dirname, "..", "artifacts");
  fs.mkdirSync(outDir, { recursive: true });
  const shotPath = path.join(outDir, screenshotName);
  await page.screenshot({ path: shotPath, fullPage: true });
  return { data, shotPath };
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  try {
    await loginAndPrepare(page);
    const kayit = await inspect(page, "/kayit-ui", ".table-wrap.managed-scroll", "kayit-table-border.png");
    const firmalar = await inspect(page, "/kayit-sponsor-firmalar-ui", ".table-wrap", "firmalar-table-border.png");
    console.log(JSON.stringify({ kayit, firmalar }, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
