const { chromium } = require('playwright');
const { loginAndPrepare, DEFAULT_BASE_URL } = require('./auth-helper');
(async()=>{
 const browser = await chromium.launch({headless:true});
 const page = await browser.newPage();
 await loginAndPrepare(page);
 for (const p of ['/konaklama-ui','/kayit-ui','/tercuman-ui','/operasyon-ui']) {
   await page.goto(DEFAULT_BASE_URL + p, {waitUntil:'networkidle'});
   await page.waitForTimeout(1200);
   const data = await page.evaluate(() => {
     const head = document.querySelector('.head');
     const right = document.querySelector('.head .head-right');
     return {
       headClass: head ? head.className : null,
       rightClass: right ? right.className : null,
       rightHtml: right ? right.outerHTML : null,
       headHtml: head ? head.outerHTML : null,
     };
   });
   console.log('PAGE ' + p);
   console.log(JSON.stringify(data));
 }
 await browser.close();
})().catch(err=>{ console.error(err); process.exit(1); });
