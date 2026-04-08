const { chromium } = require('playwright');
const { loginAndPrepare, DEFAULT_BASE_URL } = require('./auth-helper');
(async()=>{
 const browser = await chromium.launch({headless:true});
 const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
 await loginAndPrepare(page);
 await page.goto(DEFAULT_BASE_URL + '/yonetici-ui', {waitUntil:'networkidle'});
 await page.waitForTimeout(1200);
 const data = await page.evaluate(() => {
   const candidates = Array.from(document.querySelectorAll('.tab, .tabs .tab, .subtabs .tab, .dd, .dd-content, [data-go], button, a'))
     .map(el => ({tag:el.tagName, cls:el.className, text:(el.textContent||'').trim(), disp:getComputedStyle(el).display}))
     .filter(x => x.text && (x.text.includes('Dosyalar') || x.text.includes('Ayarlar') || x.text.includes('Veritabaný') || x.text.includes('Ürünler') || x.text.includes('Raporlar')));
   return candidates;
 });
 console.log(JSON.stringify(data));
 await browser.close();
})().catch(err=>{ console.error(err); process.exit(1); });
