const { loginAndPrepare } = require("../scripts/auth-helper");

async function openAuthedPage(page, path) {
  await loginAndPrepare(page);
  await page.goto(path, { waitUntil: "domcontentloaded" });
}

module.exports = {
  openAuthedPage,
};
