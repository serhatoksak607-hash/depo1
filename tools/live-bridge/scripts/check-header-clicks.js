const { chromium } = require('playwright');
const { loginAndPrepare, DEFAULT_BASE_URL } = require('./auth-helper');

const PATHS = ['/kayit-ui', '/tercuman-ui', '/operasyon-ui'];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await loginAndPrepare(page);

  for (const path of PATHS) {
    await page.goto(DEFAULT_BASE_URL + path, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1200);
    const snapshot = await page.evaluate(() => {
      const left = Array.from(document.querySelectorAll('.head .module-nav a')).map(a => (a.textContent || '').trim()).filter(Boolean);
      const right = Array.from(document.querySelectorAll('.head .head-right a, .head .head-right .project-badge')).map(a => (a.textContent || '').trim()).filter(Boolean);
      const badgeCount = document.querySelectorAll('.head #activeProjectBadge').length;
      return { left, right, badgeCount };
    });
    console.log(`PAGE ${path}`);
    console.log(JSON.stringify(snapshot));
  }

  await page.goto(DEFAULT_BASE_URL + '/kayit-ui', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await page.locator('.head .module-nav a[href="/konaklama-ui"]').click();
  await page.waitForLoadState('networkidle');
  console.log(`CLICK_RESULT ${page.url()}`);

  await browser.close();
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
