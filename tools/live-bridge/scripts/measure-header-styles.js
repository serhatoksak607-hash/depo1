const { chromium } = require('playwright');
const { loginAndPrepare, DEFAULT_BASE_URL } = require('./auth-helper');
const paths = ['/transfer-ui','/kayit-ui','/tercuman-ui','/operasyon-ui'];
(async()=>{
 const browser = await chromium.launch({headless:true});
 const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
 await loginAndPrepare(page);
 for (const p of paths) {
   await page.goto(DEFAULT_BASE_URL + p, {waitUntil:'networkidle'});
   await page.waitForTimeout(800);
   const data = await page.evaluate(() => {
     const finance = document.querySelector('#globalFinanceRightLink');
     const badge = document.querySelector('.head .head-right #activeProjectBadge');
     const adminBtn = document.querySelector('.head .admin-menu > .admin-btn');
     function styleOf(el){ if(!el) return null; const s=getComputedStyle(el); return {display:s.display, whiteSpace:s.whiteSpace, minWidth:s.minWidth, width:s.width, maxWidth:s.maxWidth, overflow:s.overflow, textOverflow:s.textOverflow, padding:s.padding, fontSize:s.fontSize, lineHeight:s.lineHeight, writingMode:s.writingMode, transform:s.transform, position:s.position}; }
     return { path: location.pathname, finance: styleOf(finance), adminBtn: styleOf(adminBtn), badge: styleOf(badge) };
   });
   console.log(JSON.stringify(data));
 }
 await browser.close();
})().catch(err=>{ console.error(err); process.exit(1); });
