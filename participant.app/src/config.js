const DEFAULT_LOCAL_API_BASE = "http://127.0.0.1:3000";
const DEFAULT_REMOTE_API_BASE = "https://www.micetro.org";

function resolveApiMode() {
  const explicitMode = String(process.env.EXPO_PUBLIC_PARTICIPANT_API_MODE || "").trim().toLowerCase();
  if (explicitMode === "mock" || explicitMode === "local" || explicitMode === "remote") {
    return explicitMode;
  }

  if (process.env.EXPO_PUBLIC_API_BASE) {
    return "remote";
  }

  if (typeof window !== "undefined") {
    const host = String(window.location.hostname || "").toLowerCase();
    if (host === "localhost" || host === "127.0.0.1") {
      return "local";
    }
  }

  return "mock";
}

export const API_MODE = resolveApiMode();
export const API_BASE =
  API_MODE === "local"
    ? DEFAULT_LOCAL_API_BASE
    : API_MODE === "remote"
      ? String(process.env.EXPO_PUBLIC_API_BASE || DEFAULT_REMOTE_API_BASE)
      : "";

export const API_DISPLAY_LABEL =
  API_MODE === "mock"
    ? "Demo Modu"
    : API_MODE === "local"
      ? DEFAULT_LOCAL_API_BASE
      : API_BASE;

export const PARTICIPANT_DEFAULTS = {
  appName: "Creatro Participant",
  loginHeroCode: "PARTICIPANT",
  fallbackAgencyName: "Acente",
  fallbackProjectName: "Katılımcı Projesi",
  fallbackSponsorName: "Ana Sponsor",
  agencyPrimary: "#113876",
  agencySecondary: "#8CD3FF",
  agencyBase: "#091028",
  projectPrimary: "#1E63C7",
  projectSecondary: "#DCEBFF",
};

export const MODULE_LABELS = {
  transfer: "Transferlerim",
  kayit: "Kayıt Bilgilerim",
  konaklama: "Konaklama Bilgilerim",
  toplanti: "Toplantı Modülü",
  tercuman: "Tercüman Desteği",
  muhasebe_finans: "Muhasebe - Finans",
  duyurular: "Duyurular",
  yonetim: "Yönetim",
};

export const MODULE_ORDER = [
  "toplanti",
  "kayit",
  "konaklama",
  "transfer",
  "duyurular",
  "tercuman",
  "muhasebe_finans",
  "yonetim",
];

export const PARTICIPANT_CARD_COPY = {
  oturumlar: "Oturumlar",
  program: "Program Akışı",
  bildiriler: "Bildiriler",
  sertifikalar: "Sertifikalar",
  kurslar: "Kurslar",
  rezervasyonlarim: "Rezervasyonlarım",
  duyurular: "Duyurular",
  qr: "Katılımcı QR",
};
