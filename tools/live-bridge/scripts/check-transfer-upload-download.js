const { chromium } = require("@playwright/test");
const { loginAndPrepare, DEFAULT_BASE_URL } = require("./auth-helper");

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1680, height: 1100 } });
  const page = await context.newPage();
  page.on("console", (msg) => console.log("[console]", msg.type(), msg.text()));
  page.on("pageerror", (err) => console.log("[pageerror]", err.message));

  try {
    const { me } = await loginAndPrepare(page);
    console.log("[auth] active_project", me.active_project_name, me.active_project_code);
    await page.goto(`${DEFAULT_BASE_URL}/transfer-ui`, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle").catch(() => {});

    const uploadTab = page.getByText("Upload - Download", { exact: true });
    if (await uploadTab.count()) {
      await uploadTab.first().click().catch(() => {});
      await page.waitForTimeout(1200);
    }

    const frameHandle = await page.locator("#moduleFrame").elementHandle();
    const frame = frameHandle ? await frameHandle.contentFrame() : null;
    const diagnostics = await page.evaluate(() => {
      const pick = (sel) => document.querySelector(sel);
      const textOf = (sel) => (pick(sel)?.textContent || "").trim();
      const htmlOf = (sel) => (pick(sel)?.outerHTML || "").slice(0, 2500);
      const tableHeads = Array.from(document.querySelectorAll("thead th")).map((x) => (x.textContent || "").trim()).filter(Boolean).slice(0, 40);
      return {
        title: document.title,
        summary: textOf("#summary") || textOf(".summary") || textOf("#info"),
        uploadDownloadVisible: /Upload - Download/i.test(document.body.innerText),
        stageHtml: htmlOf("#stagedTable") || htmlOf("#stagedBody") || htmlOf("table"),
        transferHtml: htmlOf("#transferListTable") || htmlOf("#transferListBody"),
        heads: tableHeads,
      };
    });
    let frameDiagnostics = null;
    if (frame) {
      frameDiagnostics = await frame.evaluate(() => {
        const pick = (sel) => document.querySelector(sel);
        const htmlOf = (sel) => (pick(sel)?.outerHTML || "").slice(0, 4000);
        const textOf = (sel) => (pick(sel)?.textContent || "").trim();
        const heads = Array.from(document.querySelectorAll("thead th")).map((x) => (x.textContent || "").trim()).filter(Boolean).slice(0, 60);
        return {
          url: location.href,
          title: document.title,
          summary: textOf("#summary") || textOf(".summary") || textOf("#info"),
          heads,
          bodyText: document.body.innerText.slice(0, 2500),
          stagedHtml: htmlOf("#table") || htmlOf("#stagedTable") || htmlOf("#stagedBody") || htmlOf("table"),
        };
      });
    }
    console.log(JSON.stringify({ page: diagnostics, frame: frameDiagnostics }, null, 2));
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error("[fatal]", err && err.stack ? err.stack : String(err));
  process.exit(1);
});
