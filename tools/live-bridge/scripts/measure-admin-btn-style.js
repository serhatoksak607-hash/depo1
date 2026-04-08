const { chromium } = require('playwright');
const { loginAndPrepare, DEFAULT_BASE_URL } = require('./auth-helper');
const paths = ['/transfer-ui','/kayit-ui'];
(async()=>{
 const browser = await chromium.launch({headless:true});
 const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
 await loginAndPrepare(page);
 for (const p of paths) {
   await page.goto(DEFAULT_BASE_URL + p, {waitUntil:'networkidle'});
   await page.waitForTimeout(800);
   const data = await page.evaluate(() => {
     const finance = document.querySelector('#globalFinanceRightLink');
     const admin = document.querySelector('.head .admin-menu > .admin-btn');
     function pick(el){ const s = getComputedStyle(el); return {border:s.border, borderRadius:s.borderRadius, background:s.background, color:s.color, fontSize:s.fontSize, fontWeight:s.fontWeight, boxShadow:s.boxShadow, textDecoration:s.textDecorationLine, padding:s.padding}; }
     return { path: location.pathname, finance: pick(finance), admin: pick(admin) };
   });
   console.log(JSON.stringify(data));
 }
 await browser.close();
})().catch(err=>{ console.error(err); process.exit(1); });
