const DEFAULT_BASE_URL = process.env.BASE_URL || "http://localhost:3000";
const DEFAULT_USERNAME = process.env.APP_ADMIN_USER || "CreaTRO";
const DEFAULT_PASSWORD = process.env.APP_ADMIN_PASS || "Micetro25+.";

async function apiFetch(context, path, options = {}) {
  return context.request.fetch(`${DEFAULT_BASE_URL}${path}`, options);
}

async function ensureActiveProject(context, token) {
  const headers = { Authorization: `Bearer ${token}` };
  const meRes = await apiFetch(context, "/auth/me", { headers });
  if (!meRes.ok()) throw new Error(`/auth/me failed with ${meRes.status()}`);
  const me = await meRes.json();
  if (me.active_project_id) return me;

  const projectsRes = await apiFetch(context, "/projects", { headers });
  if (!projectsRes.ok()) throw new Error(`/projects failed with ${projectsRes.status()}`);
  const projects = await projectsRes.json();
  const firstProject =
    (Array.isArray(projects) ? projects : []).find(
      (p) => p && p.id && !String(p.name || "").toLowerCase().includes("yönetim")
    ) || (Array.isArray(projects) ? projects : [])[0];

  if (!firstProject || !firstProject.id) {
    throw new Error("No project available for authenticated session");
  }

  const setRes = await apiFetch(context, "/auth/active-project", {
    method: "PUT",
    headers: { ...headers, "Content-Type": "application/json" },
    data: { project_id: firstProject.id },
  });
  if (!setRes.ok()) throw new Error(`/auth/active-project failed with ${setRes.status()}`);

  return {
    ...me,
    active_project_id: firstProject.id,
    active_project_name: firstProject.name,
    active_project_code: firstProject.operation_code,
  };
}

async function loginAndPrepare(page) {
  const loginRes = await page.request.post(`${DEFAULT_BASE_URL}/auth/login`, {
    data: {
      username: DEFAULT_USERNAME,
      password: DEFAULT_PASSWORD,
    },
  });
  if (!loginRes.ok()) throw new Error(`/auth/login failed with ${loginRes.status()}`);
  const loginData = await loginRes.json();
  const token = loginData?.access_token;
  if (!token) throw new Error("Login response missing access_token");

  const me = await ensureActiveProject(page.context(), token);
  await page.addInitScript(
    ({ authToken, mePayload }) => {
      try {
        localStorage.setItem("token", authToken);
        localStorage.setItem("access_token", authToken);
        sessionStorage.setItem("token", authToken);
        sessionStorage.setItem("access_token", authToken);
        if (mePayload && mePayload.active_project_id) {
          localStorage.setItem("activeProjectId", String(mePayload.active_project_id));
          sessionStorage.setItem("activeProjectId", String(mePayload.active_project_id));
        }
        if (mePayload) {
          localStorage.setItem("auth_me_cache", JSON.stringify(mePayload));
          sessionStorage.setItem("auth_me_cache", JSON.stringify(mePayload));
        }
      } catch (_) {}
    },
    { authToken: token, mePayload: me }
  );
  await page.setExtraHTTPHeaders({ Authorization: `Bearer ${token}` });
  return { token, me };
}

module.exports = {
  DEFAULT_BASE_URL,
  DEFAULT_USERNAME,
  loginAndPrepare,
};
