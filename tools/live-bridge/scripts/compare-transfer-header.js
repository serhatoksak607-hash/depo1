const { chromium } = require('playwright');
const { loginAndPrepare, DEFAULT_BASE_URL } = require('./auth-helper');
const paths = ['/transfer-ui','/modules-ui','/kayit-ui','/kayit-sponsor-firmalar-ui','/konaklama-ui','/toplanti-ui','/tercuman-ui','/operasyon-ui','/muhasebe-finans-ui','/duyurular-ui','/yonetici-ui','/reports-ui','/projects-ui','/users-ui','/saas-admin-ui'];
(async()=>{
 const browser = await chromium.launch({headless:true});
 const page = await browser.newPage();
 await loginAndPrepare(page);
 for (const p of paths) {
   await page.goto(DEFAULT_BASE_URL + p, {waitUntil:'networkidle'});
   await page.waitForTimeout(1000);
   const data = await page.evaluate(() => {
     const head = document.querySelector('.head');
     const left = Array.from(document.querySelectorAll('.head .module-nav a, .head .head-left.module-nav a')).map(a => (a.textContent||'').trim()).filter(Boolean);
     const right = Array.from(document.querySelectorAll('.head .head-right a, .head .head-right .project-badge')).map(a => (a.textContent||'').trim()).filter(Boolean);
     return {
       headHtml: head ? head.outerHTML : '',
       left,
       right,
       hasHeadRight: !!document.querySelector('.head .head-right'),
       hasProjectBadgeInRight: !!document.querySelector('.head .head-right #activeProjectBadge'),
       hasDeskBadge: !!document.querySelector('.head #globalHeaderComputerBadge')
     };
   });
   console.log('PAGE ' + p);
   console.log(JSON.stringify(data));
 }
 await browser.close();
})().catch(err=>{ console.error(err); process.exit(1); });
