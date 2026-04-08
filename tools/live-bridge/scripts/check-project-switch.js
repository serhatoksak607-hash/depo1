const { chromium } = require('playwright');
const { loginAndPrepare, DEFAULT_BASE_URL } = require('./auth-helper');
(async()=>{
 const browser = await chromium.launch({headless:true});
 const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
 await loginAndPrepare(page);
 await page.goto(DEFAULT_BASE_URL + '/kayit-ui', {waitUntil:'networkidle'});
 await page.waitForTimeout(1200);
 const badge = page.locator('.head #activeProjectBadge').first();
 await badge.click();
 await page.waitForTimeout(500);
 const data = await page.evaluate(() => {
   const menu = document.getElementById('globalProjectSwitchMenu');
   const host = document.querySelector('.project-switch-wrap');
   const items = menu ? Array.from(menu.querySelectorAll('.project-switch-item')).map(x => (x.textContent || '').trim()) : [];
   return {
     menuExists: !!menu,
     hostOpen: !!(host && host.classList.contains('open')),
     itemCount: items.length,
     items
   };
 });
 console.log(JSON.stringify(data));
 await browser.close();
})().catch(err=>{ console.error(err); process.exit(1); });
