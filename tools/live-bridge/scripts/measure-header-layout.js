const { chromium } = require('playwright');
const { loginAndPrepare, DEFAULT_BASE_URL } = require('./auth-helper');
const paths = ['/transfer-ui','/kayit-ui','/tercuman-ui','/operasyon-ui'];
(async()=>{
 const browser = await chromium.launch({headless:true});
 const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
 await loginAndPrepare(page);
 for (const p of paths) {
   await page.goto(DEFAULT_BASE_URL + p, {waitUntil:'networkidle'});
   await page.waitForTimeout(1200);
   const data = await page.evaluate(() => {
     function box(sel){ const el=document.querySelector(sel); if(!el) return null; const r=el.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; }
     const head = document.querySelector('.head');
     return {
       path: location.pathname,
       head: box('.head'),
       moduleNav: box('.head .module-nav, .head .head-left.module-nav'),
       headRight: box('.head .head-right'),
       finance: box('#globalFinanceRightLink'),
       adminBtn: box('.head .admin-menu > .admin-btn'),
       badge: box('.head .head-right #activeProjectBadge'),
       token: box('.head #globalTokenBadge'),
       desk: box('.head #globalHeaderComputerBadge'),
       children: Array.from(head ? head.children : []).map(el => ({tag:el.tagName, cls:el.className, text:(el.textContent||'').trim().slice(0,60)})),
       headStyle: getComputedStyle(head).cssText,
       rightStyle: document.querySelector('.head .head-right') ? getComputedStyle(document.querySelector('.head .head-right')).cssText : null,
     };
   });
   console.log(JSON.stringify(data));
 }
 await browser.close();
})().catch(err=>{ console.error(err); process.exit(1); });
