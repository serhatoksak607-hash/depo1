const { chromium } = require('playwright');
const { loginAndPrepare, DEFAULT_BASE_URL } = require('./auth-helper');
(async()=>{
 const browser = await chromium.launch({headless:true});
 const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
 await loginAndPrepare(page);
 await page.goto(DEFAULT_BASE_URL + '/yonetici-ui', {waitUntil:'networkidle'});
 await page.waitForTimeout(1000);
 const btn = page.locator('.head .admin-menu > .admin-btn').first();
 const menu = page.locator('.head .admin-menu .links').first();
 await btn.hover();
 await page.waitForTimeout(200);
 const btnBox = await btn.boundingBox();
 const menuBox = await menu.boundingBox();
 if (btnBox && menuBox) {
   await page.mouse.move(btnBox.x + btnBox.width/2, btnBox.y + btnBox.height/2);
   await page.waitForTimeout(100);
   await page.mouse.move(menuBox.x + 20, menuBox.y + 20, { steps: 10 });
   await page.waitForTimeout(200);
 }
 const visible = await menu.isVisible();
 console.log(JSON.stringify({ visible, btnBox, menuBox }));
 await browser.close();
})().catch(err=>{ console.error(err); process.exit(1); });
