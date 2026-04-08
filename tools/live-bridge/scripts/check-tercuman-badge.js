const { chromium } = require('playwright');
const { loginAndPrepare, DEFAULT_BASE_URL } = require('./auth-helper');
(async()=>{
 const browser = await chromium.launch({headless:true});
 const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
 await loginAndPrepare(page);
 await page.goto(DEFAULT_BASE_URL + '/tercuman-ui', {waitUntil:'networkidle'});
 await page.waitForTimeout(800);
 const data = await page.evaluate(() => {
   const badge = document.querySelector('.head .head-right #activeProjectBadge');
   const s = getComputedStyle(badge);
   return { border:s.border, borderRadius:s.borderRadius, background:s.background, color:s.color, fontSize:s.fontSize, fontWeight:s.fontWeight, padding:s.padding };
 });
 console.log(JSON.stringify(data));
 await browser.close();
})().catch(err=>{ console.error(err); process.exit(1); });
