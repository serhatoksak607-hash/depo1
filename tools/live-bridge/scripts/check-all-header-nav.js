const { chromium } = require('playwright');
const { loginAndPrepare, DEFAULT_BASE_URL } = require('./auth-helper');

const PATHS = [
  '/modules-ui',
  '/kayit-ui',
  '/kayit-sponsor-firmalar-ui',
  '/konaklama-ui',
  '/toplanti-ui',
  '/tercuman-ui',
  '/transfer-ui',
  '/operasyon-ui',
  '/muhasebe-finans-ui',
  '/duyurular-ui',
  '/yonetici-ui',
  '/reports-ui',
  '/projects-ui',
  '/users-ui',
  '/saas-admin-ui',
];

const EXPECTED = [
  'Ana Sayfa',
  'Kayıt Modülü',
  'Konaklama Modülü',
  'Toplantı Modülü',
  'Tercüman Modülü',
  'Ulaşım Modülü',
  'Operasyon Modülü',
  'Muhasebe - Finans Modülü',
  'Duyurular',
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await loginAndPrepare(page);

  let failures = 0;
  for (const path of PATHS) {
    await page.goto(DEFAULT_BASE_URL + path, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1200);
    const links = await page.$$eval('.head .module-nav a', (els) =>
      els
        .map((e) => ({
          text: (e.textContent || '').trim(),
          href: e.getAttribute('href') || '',
          display: getComputedStyle(e).display,
        }))
        .filter((x) => x.display !== 'none')
    );
    const texts = links.map((x) => x.text);
    const missing = EXPECTED.filter((x) => !texts.includes(x));
    console.log(`PAGE ${path}`);
    console.log(JSON.stringify(texts));
    if (missing.length) {
      failures += 1;
      console.log(`MISSING ${path}: ${missing.join(', ')}`);
    }
  }

  await browser.close();
  if (failures) process.exit(1);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
