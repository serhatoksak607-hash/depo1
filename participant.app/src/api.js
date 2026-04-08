import { API_BASE, API_MODE } from "./config";

const DEMO_STORAGE_KEY = "creatro_participant_demo_profile";
const DEMO_TOKEN = "demo-participant-token";

const DEMO_PROJECTS = [
  {
    id: 101,
    operation_code: "TOD2026-IST",
    name: "Türk Oftalmoloji Derneği 2026",
    is_active: true,
  },
  {
    id: 102,
    operation_code: "KON2026-ANK",
    name: "Kongre Participant Demo",
    is_active: true,
  },
];

function buildVisibleModules() {
  return [
    { key: "toplanti", href: "/toplanti-ui", description: "Oturumlar, program akışı ve bildiriler." },
    { key: "kayit", href: "/kayit-ui", description: "Kayıt ve badge bilgileri." },
    { key: "konaklama", href: "/konaklama-ui", description: "Otel ve oda bilgileri." },
    { key: "transfer", href: "/transfer-ui", description: "Transfer planı ve araç bilgileri." },
    { key: "duyurular", href: "/duyurular-ui", description: "Duyurular ve acil bildirimler." },
  ];
}

function buildDemoProfile(projectId = null) {
  const project = DEMO_PROJECTS.find((item) => item.id === projectId) || null;

  return {
    username: "participant.demo",
    role: "participant",
    agency_name: "Creatro Travel",
    agency_logo_name: "Creatro Travel",
    project_logo_name: project ? project.name : "",
    active_project_id: project ? project.id : null,
    active_project_name: project ? project.name : "",
    active_project_code: project ? project.operation_code : "",
    meeting_visual_name: project ? `${project.name} Hero` : "Katılımcı Toplantı Görseli",
    project_visual_name: project ? `${project.name} Hero` : "Katılımcı Toplantı Görseli",
    project_footer_banner_name: project ? `${project.name} Footer Banner` : "Participant Footer Banner",
    main_sponsor_name: "Ana Sponsor Demo",
    agency_theme: {
      base_color: "#091028",
      primary_color: "#113876",
      secondary_color: "#8CD3FF",
    },
    project_theme: {
      enabled: Boolean(project),
      base_color: "#0E2045",
      primary_color: "#1B5FC1",
      secondary_color: "#DDEEFF",
    },
    visible_modules: buildVisibleModules(),
  };
}

function saveDemoProfile(profile) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(profile));
}

function readDemoProfile() {
  if (typeof window === "undefined") {
    return buildDemoProfile();
  }
  const raw = window.localStorage.getItem(DEMO_STORAGE_KEY);
  if (!raw) return buildDemoProfile();
  try {
    return JSON.parse(raw);
  } catch (_) {
    return buildDemoProfile();
  }
}

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

async function mockLogin(username, password) {
  const allowed =
    (username === "participant.demo" && password === "participant.demo") ||
    (username === "CreaTRo" && password === "Micetro25+.");

  if (!allowed) {
    throw new Error("Demo giriş için kullanıcı adı veya şifre hatalı.");
  }

  const profile = buildDemoProfile();
  saveDemoProfile(profile);

  return {
    access_token: DEMO_TOKEN,
    token_type: "bearer",
    user: profile,
  };
}

async function mockMe() {
  return readDemoProfile();
}

async function mockProjects() {
  return DEMO_PROJECTS;
}

async function mockSetActiveProject(_, projectId) {
  const profile = buildDemoProfile(projectId);
  saveDemoProfile(profile);
  return {
    ok: true,
    active_project_id: projectId,
    user: profile,
  };
}

export const api = {
  isDemoMode: API_MODE === "mock",
  login: (username, password) =>
    API_MODE === "mock"
      ? mockLogin(username, password)
      : request("/auth/login", { method: "POST", body: { username, password } }),
  me: (token) => (API_MODE === "mock" ? mockMe(token) : request("/auth/me", { token })),
  projects: (token) => (API_MODE === "mock" ? mockProjects(token) : request("/projects", { token })),
  setActiveProject: (token, projectId) =>
    API_MODE === "mock"
      ? mockSetActiveProject(token, projectId)
      : request("/auth/active-project", {
          method: "PUT",
          token,
          body: { project_id: projectId },
        }),
};
