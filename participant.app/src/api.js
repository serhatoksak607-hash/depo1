import { API_BASE } from "./config";

async function request(path, { method = "GET", token, body } = {}) {
  const headers = {
    "Content-Type": "application/json",
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.detail || data.error || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

export const api = {
  login: (username, password) =>
    request("/auth/login", { method: "POST", body: { username, password } }),
  me: (token) => request("/auth/me", { token }),
  projects: (token) => request("/projects", { token }),
  setActiveProject: (token, projectId) =>
    request("/auth/active-project", {
      method: "PUT",
      token,
      body: { project_id: projectId },
    }),
};
