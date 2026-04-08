export const API_BASE =
  process.env.EXPO_PUBLIC_API_BASE ||
  "http://127.0.0.1:8000";

export const PARTICIPANT_DEFAULTS = {
  appName: "Creatro Participant",
  loginHeroCode: "PARTICIPANT",
  fallbackAgencyName: "Acente",
  fallbackProjectName: "Katilimci Projesi",
  fallbackSponsorName: "Ana Sponsor",
  agencyPrimary: "#113876",
  agencySecondary: "#8CD3FF",
  agencyBase: "#091028",
  projectPrimary: "#1E63C7",
  projectSecondary: "#DCEBFF",
};

export const MODULE_LABELS = {
  transfer: "Transferlerim",
  kayit: "Kayit Bilgilerim",
  konaklama: "Konaklama Bilgilerim",
  toplanti: "Toplanti Modulu",
  tercuman: "Tercuman Destegi",
  muhasebe_finans: "Muhasebe - Finans",
  duyurular: "Duyurular",
  yonetim: "Yonetim",
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
  program: "Program Akisi",
  bildiriler: "Bildiriler",
  sertifikalar: "Sertifikalar",
  kurslar: "Kurslar",
  rezervasyonlarim: "Rezervasyonlarim",
  duyurular: "Duyurular",
  qr: "Katilimci QR",
};
