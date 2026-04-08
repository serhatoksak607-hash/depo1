const { chromium } = require("@playwright/test");
const { loginAndPrepare, DEFAULT_BASE_URL } = require("./auth-helper");

async function api(page, token, path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  return page.request.fetch(`${DEFAULT_BASE_URL}${path}`, {
    ...options,
    headers,
  });
}

async function getCompanies(page, token, projectId) {
  const res = await api(
    page,
    token,
    `/module-data?module_name=kayit&entity_type=sponsor_firma&limit=2000&project_id=${encodeURIComponent(String(projectId))}`
  );
  if (!res.ok()) throw new Error(`/module-data failed with ${res.status()}`);
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

async function updateCompany(page, token, rowId, projectId, data) {
  const res = await api(page, token, `/module-data/${rowId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    data: {
      module_name: "kayit",
      entity_type: "sponsor_firma",
      project_id: projectId,
      data,
    },
  });
  if (!res.ok()) {
    const out = await res.json().catch(() => ({}));
    throw new Error(out.detail || `update failed with ${res.status()}`);
  }
  return res.json();
}

async function readSummaryState(page) {
  await page.goto(`${DEFAULT_BASE_URL}/kayit-sponsor-firmalar-ui`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1200);
  return page.evaluate(() => {
    const root = document.querySelector("#companyWarningSummary");
    if (!root) return null;
    const chips = Array.from(root.querySelectorAll(".warning-summary-chip")).map((el) => ({
      text: (el.textContent || "").trim(),
      klass: el.className,
      bg: getComputedStyle(el).backgroundColor,
      color: getComputedStyle(el).color,
    }));
    return chips;
  });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1680, height: 1200 } });
  const page = await context.newPage();
  let mutated = null;
  try {
    const { me, token } = await loginAndPrepare(page);
    const projectId = me && me.active_project_id;
    if (!projectId) throw new Error("active_project_id missing");

    const rows = await getCompanies(page, token, projectId);
    if (rows.length < 2) throw new Error("Not enough company rows for duplicate test");

    const first = rows.find((r) => r && r.data && (r.data.display_name || r.data.company_name)) || rows[0];
    const second = rows.find((r) => r && r.id !== first.id) || rows[1];
    if (!first || !second) throw new Error("Could not pick two rows");

    const firstData = first.data || {};
    const secondData = second.data || {};
    const original = { ...secondData };
    mutated = { rowId: second.id, projectId, original };

    const duplicateName = String(firstData.display_name || firstData.company_name || "").trim();
    const duplicateTax = String(firstData.tax_number || "").trim();
    if (!duplicateName) throw new Error("No source company name to duplicate");

    const nextData = {
      ...secondData,
      company_name: duplicateName,
      display_name: duplicateName,
      tax_number: duplicateTax,
    };

    await updateCompany(page, token, second.id, projectId, nextData);
    const chipsAfter = await readSummaryState(page);
    console.log(JSON.stringify({ ok: true, duplicatedRowId: second.id, chipsAfter }, null, 2));
  } finally {
    if (mutated) {
      try {
        const { token } = await loginAndPrepare(page);
        await updateCompany(page, token, mutated.rowId, mutated.projectId, mutated.original);
      } catch (err) {
        console.error("REVERT_FAILED", err && err.stack ? err.stack : String(err));
      }
    }
    await browser.close();
  }
})().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
