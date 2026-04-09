import React, { Suspense, lazy, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Bell,
  Check,
  ChevronRight,
  ClipboardList,
  Home,
  Navigation,
  QrCode,
} from "lucide-react";
import type { ProjectSummary, Role, TabKey } from "@/data/types";
import { HomeScreen } from "@/components/screens/HomeScreen";
import { OperationsScreen } from "@/components/screens/OperationsScreen";
import { JobsScreen } from "@/components/screens/JobsScreen";
import brandFallbackLogo from "@/assets/brand/formice.png";
import footerBanner from "@/assets/brand/footer2.png";
import { toast } from "@/components/ui/sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getAppConfig, getCoreBootstrap } from "@/services/core";
import { useAppState } from "@/state/app-state";

const ExpensesScreen = lazy(() =>
  import("@/components/screens/ExpensesScreen").then((module) => ({ default: module.ExpensesScreen })),
);
const FilesScreen = lazy(() =>
  import("@/components/screens/FilesScreen").then((module) => ({ default: module.FilesScreen })),
);
const QrCheckinScreen = lazy(() =>
  import("@/components/screens/QrCheckinScreen").then((module) => ({ default: module.QrCheckinScreen })),
);

const notificationItems = [
  { id: 1, title: "Uçuş saati güncellendi", detail: "PC2012 için yeni bilgilendirme var." },
  { id: 2, title: "Yeni dosya eklendi", detail: "Transfer evrakları güncellendi." },
  { id: 3, title: "Masraf durumu değişti", detail: "Gönderilen masraf kontrol bekliyor." },
];

const alertItems = [
  { id: 1, title: "Transfer saati değişti", detail: "09:30 transferi 09:50 olarak güncellendi." },
  { id: 2, title: "Uçuş saati değişti", detail: "PC2012 uçuşu 10 dakikanın üzerinde değişti." },
];

const tabTitles: Record<TabKey, string> = {
  home: "Ana Sayfa",
  operations: "Operasyon",
  jobs: "Görevlerim",
  expenses: "Masraflar",
  files: "Dosyalarım",
  notifications: "Bildirimler",
  "qr-checkin": "QR Okut",
};

const tabIconMap = {
  home: Home,
  "clipboard-list": ClipboardList,
  navigation: Navigation,
  bell: Bell,
  "qr-code": QrCode,
} as const;

const tabColorMap: Record<TabKey, string> = {
  home: "text-foreground",
  operations: "text-azure-400",
  jobs: "text-azure-500",
  expenses: "text-gold-500",
  files: "text-success",
  notifications: "text-coral-500",
  "qr-checkin": "text-success",
};

function formatBadgeCount(count: number): string | null {
  if (count <= 0) return null;
  if (count >= 10) return "9+";
  return String(count);
}

function formatLastSyncText(syncedAt?: string) {
  if (!syncedAt) return "Son senkron hazırlanıyor";

  const syncedDate = new Date(syncedAt);
  if (Number.isNaN(syncedDate.getTime())) return "Son senkron hazırlanıyor";

  const diffMinutes = Math.max(0, Math.floor((Date.now() - syncedDate.getTime()) / 60000));

  if (diffMinutes < 1) return "Son senkron az önce";
  if (diffMinutes < 60) return `Son senkron ${diffMinutes} dk önce`;

  const hour = syncedDate.getHours().toString().padStart(2, "0");
  const minute = syncedDate.getMinutes().toString().padStart(2, "0");
  return `Son senkron ${hour}:${minute}`;
}

function ScreenFallback({ role }: { role: Role }) {
  const appConfig = getAppConfig(role);
  const loadingLogo = appConfig.branding.loading_logo_url || appConfig.branding.logo_url || brandFallbackLogo;
  const loadingPrimary = appConfig.branding.loading_primary_color || appConfig.branding.primary_color || "#F28C28";
  const loadingBase = appConfig.branding.loading_base_color || appConfig.branding.base_color || "#102B64";
  const gradientEnd = "#19564D";

  return (
    <div
      className="flex min-h-[280px] items-center justify-center px-6"
      style={{ background: `linear-gradient(180deg, ${loadingBase} 0%, ${gradientEnd} 100%)` }}
    >
      <div className="flex w-full max-w-sm flex-col items-center gap-5 text-center">
        <img
          src={loadingLogo}
          alt=""
          aria-hidden="true"
          className="h-16 w-auto object-contain"
          width={220}
          height={64}
        />
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.24em]" style={{ color: loadingPrimary }}>
            Yükleniyor
          </p>
          <p className="text-sm text-slate-200">Ekran hazırlanıyor...</p>
        </div>
        <div className="h-1.5 w-36 overflow-hidden rounded-full bg-white/10">
          <div className="loading-bar h-full w-1/2 rounded-full" style={{ backgroundColor: loadingPrimary }} />
        </div>
      </div>
    </div>
  );
}

function buildProjectOptions(role: Role): ProjectSummary[] {
  const appConfig = getAppConfig(role);
  const primaryProject: ProjectSummary = {
    id: appConfig.project_id || "micetro-istanbul-zirvesi",
    name: appConfig.content.project_name || "Micetro İstanbul Zirvesi",
    dateRange: appConfig.content.project_date_range || "12-15 Ekim 2026",
    location: appConfig.content.project_location || "İstanbul Kongre Merkezi",
    qrValue:
      appConfig.content.project_qr_value ||
      `PROJECT:${appConfig.project_id || "micetro-istanbul-zirvesi"}|ROLE:${role}|PERSON:Serhat-OKSAK`,
  };

  return [
    primaryProject,
    {
      id: "global-saglik-forumu-2026",
      name: "Global Sağlık Forumu",
      dateRange: "21-23 Kasım 2026",
      location: "Antalya Gloria Kongre Merkezi",
      qrValue: "PROJECT:global-saglik-forumu-2026|ROLE:participant|PERSON:Serhat-OKSAK",
    },
    {
      id: "cof-executive-summit-2026",
      name: "COF Executive Summit",
      dateRange: "04-06 Aralık 2026",
      location: "İzmir Swissôtel Büyük Efes",
      qrValue: "PROJECT:cof-executive-summit-2026|ROLE:participant|PERSON:Serhat-OKSAK",
    },
  ];
}

const Index = () => {
  const [activeTab, setActiveTab] = useState<TabKey>("home");
  const [role, setRole] = useState<Role>("driver");
  const [isProjectDialogOpen, setIsProjectDialogOpen] = useState(false);
  const [pendingSyncCount, setPendingSyncCount] = useState(0);
  const [selectedNotificationId, setSelectedNotificationId] = useState<number | null>(null);
  const [selectedAlertId, setSelectedAlertId] = useState<number | null>(null);
  const [alertsViewOpen, setAlertsViewOpen] = useState(false);
  const {
    readNotificationIds,
    setReadNotificationIds,
    readAlertIds,
    setReadAlertIds,
  } = useAppState();
  const isOnline = true;
  const appConfig = getAppConfig(role);
  const projectOptions = useMemo(() => buildProjectOptions(role), [role]);
  const [selectedProjectId, setSelectedProjectId] = useState(projectOptions[0]?.id || "");
  const { data: bootstrap } = useQuery({
    queryKey: ["core", "bootstrap", role],
    queryFn: async () => getCoreBootstrap(role),
    staleTime: Infinity,
  });
  const selectedProject =
    projectOptions.find((project) => project.id === selectedProjectId) || projectOptions[0];
  const brandBg = appConfig.branding.base_color || "#102B64";
  const brandPrimary = appConfig.branding.primary_color || "#F28C28";
  const headerLogo = appConfig.branding.logo_url || brandFallbackLogo;
  const lastSyncText = formatLastSyncText(bootstrap?.syncedAt);
  const unreadNotifications = notificationItems.filter(
    (item) => !readNotificationIds.includes(item.id),
  ).length;
  const unreadAlerts = alertItems.filter((item) => !readAlertIds.includes(item.id)).length;
  const notificationBadgeLabel = formatBadgeCount(unreadNotifications);
  const selectedNotification =
    notificationItems.find((item) => item.id === selectedNotificationId) ?? null;
  const selectedAlert = alertItems.find((item) => item.id === selectedAlertId) ?? null;

  const tabs = useMemo(
    () =>
      appConfig.navigation.tab_items
        .filter((tab) => tab.enabled)
        .sort((a, b) => a.order - b.order)
        .map((tab) => ({
          key: tab.key,
          label: tab.label,
          icon: tabIconMap[tab.icon as keyof typeof tabIconMap] ?? Home,
          activeColor: tabColorMap[tab.key] ?? "text-foreground",
          badge: tab.key === "notifications" ? notificationBadgeLabel : undefined,
        })),
    [appConfig.navigation.tab_items, notificationBadgeLabel],
  );

  const allowedRoutes = useMemo(
    () =>
      new Set<TabKey>([
        ...tabs.map((tab) => tab.key),
        ...((appConfig.navigation.hidden_routes || []) as TabKey[]),
      ]),
    [appConfig.navigation.hidden_routes, tabs],
  );

  useEffect(() => {
    if (allowedRoutes.has(activeTab)) return;
    setActiveTab((appConfig.navigation.home_route as TabKey) || "home");
  }, [activeTab, allowedRoutes, appConfig.navigation.home_route]);

  useEffect(() => {
    if (!projectOptions.some((project) => project.id === selectedProjectId) && projectOptions[0]) {
      setSelectedProjectId(projectOptions[0].id);
    }
  }, [projectOptions, selectedProjectId]);

  const handleTabChange = (nextTab: TabKey) => {
    if (nextTab === activeTab) return;
    if (pendingSyncCount > 0) {
      toast.error("Tamamlanmamış işlem var", {
        description: "İşaretlenen yolcuların kaydedilmesi bekleniyor...",
      });
      return;
    }
    if (nextTab === "notifications") setSelectedNotificationId(null);
    setAlertsViewOpen(false);
    setSelectedAlertId(null);
    setActiveTab(nextTab);
  };

  const handleOpenAlerts = () => {
    setAlertsViewOpen(true);
    setSelectedAlertId(null);
  };

  return (
    <div className="mx-auto flex h-screen max-w-md flex-col overflow-hidden bg-background">
      <header
        className="flex-shrink-0 border-b border-white/10"
        style={{ background: `linear-gradient(140deg, ${brandBg} 0%, #183B7E 52%, #19564D 100%)` }}
      >
        <div className="flex h-[84px] items-center justify-center px-4">
          <img
            src={headerLogo}
            alt={appConfig.content.app_title || "Uygulama logosu"}
            className="max-h-[58px] w-auto max-w-[220px] object-contain"
            width={220}
            height={58}
          />
        </div>
        {activeTab !== "home" && (
          <div className="flex items-center justify-between px-4 pb-3">
            <h1 className={`text-base font-bold uppercase tracking-[0.12em] ${tabColorMap[activeTab] ?? "text-primary-foreground"}`}>
              {tabTitles[activeTab]}
            </h1>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setRole(role === "driver" ? "greeter" : "driver")}
                className="rounded-lg px-3 py-1.5 text-[10px] font-bold text-white"
                style={{ backgroundColor: brandPrimary }}
              >
                {role === "driver" ? "Sürücü" : "Karşılamacı"}
              </button>
            </div>
          </div>
        )}
      </header>

      <main className="flex-1 overflow-y-auto overflow-x-hidden pt-[9px]">
        {activeTab === "home" &&
          (alertsViewOpen ? (
            <div className="space-y-2.5 px-4 py-4">
              {selectedAlert ? (
                <div className="rounded-3xl border border-gold-500/20 bg-card p-5">
                  <button
                    onClick={() => setSelectedAlertId(null)}
                    className="mb-4 inline-flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-xs font-semibold text-muted-foreground transition-colors active:bg-secondary"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Uyarılara dön
                  </button>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-gold-500">
                    {selectedAlert.title}
                  </p>
                  <p className="mt-3 text-base font-semibold text-foreground">
                    {selectedAlert.detail}
                  </p>
                  <div className="mt-5 rounded-2xl bg-secondary/50 p-4 text-sm text-muted-foreground">
                    Bu uyarı ileride Core üzerinden ilgili transfer, değişiklik zamanı ve etki nedeni ile zenginleşecek.
                  </div>
                </div>
              ) : alertItems.length > 0 ? (
                <>
                  <button
                    onClick={() => setAlertsViewOpen(false)}
                    className="inline-flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-xs font-semibold text-muted-foreground transition-colors active:bg-secondary"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Ana sayfaya dön
                  </button>
                  {alertItems.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => {
                        setSelectedAlertId(item.id);
                        setReadAlertIds((prev) =>
                          prev.includes(item.id) ? prev : [...prev, item.id],
                        );
                      }}
                      className="block w-full rounded-2xl border border-gold-500/20 bg-card p-4 text-left transition-colors active:bg-secondary"
                    >
                      <p className="text-xs font-bold uppercase tracking-[0.16em] text-gold-500">
                        {item.title}
                      </p>
                      <p className="mt-1 text-sm font-semibold text-foreground">{item.detail}</p>
                    </button>
                  ))}
                </>
              ) : (
                <div className="flex flex-col items-center justify-center gap-3 py-16">
                  <AlertTriangle className="h-12 w-12 text-gold-500/40" />
                  <p className="text-sm text-muted-foreground">Henüz uyarı yok</p>
                </div>
              )}
            </div>
          ) : (
            <HomeScreen
              onOpenTab={handleTabChange}
              onOpenAlerts={handleOpenAlerts}
              onOpenProjectPicker={() => setIsProjectDialogOpen(true)}
              unreadNotifications={unreadNotifications}
              unreadAlerts={unreadAlerts}
              role={role}
              appConfig={appConfig}
              selectedProject={selectedProject}
            />
          ))}

        {activeTab === "operations" && <OperationsScreen role={role} onPendingSyncChange={setPendingSyncCount} />}
        {activeTab === "jobs" && <JobsScreen role={role} onOpenTab={handleTabChange} />}
        {activeTab === "expenses" && (
          <Suspense fallback={<ScreenFallback role={role} />}>
            <ExpensesScreen />
          </Suspense>
        )}
        {activeTab === "files" && (
          <Suspense fallback={<ScreenFallback role={role} />}>
            <FilesScreen role={role} />
          </Suspense>
        )}
        {activeTab === "qr-checkin" && (
          <Suspense fallback={<ScreenFallback role={role} />}>
            <QrCheckinScreen role={role} selectedProject={selectedProject} />
          </Suspense>
        )}
        {activeTab === "notifications" && (
          <div className="space-y-2.5 px-4 py-4">
            {selectedNotification ? (
              <div className="rounded-3xl border border-coral-500/20 bg-card p-5">
                <button
                  onClick={() => setSelectedNotificationId(null)}
                  className="mb-4 inline-flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-xs font-semibold text-muted-foreground transition-colors active:bg-secondary"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Bildirimlere dön
                </button>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-coral-500">
                  {selectedNotification.title}
                </p>
                <p className="mt-3 text-base font-semibold text-foreground">
                  {selectedNotification.detail}
                </p>
                <div className="mt-5 rounded-2xl bg-secondary/50 p-4 text-sm text-muted-foreground">
                  Bu bildirim ayrıntısı ileride Core üzerinden işlem zamanı, ilgili transfer ve değişiklik kaynağı ile zenginleşecek.
                </div>
              </div>
            ) : notificationItems.length > 0 ? (
              notificationItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    setSelectedNotificationId(item.id);
                    setReadNotificationIds((prev) =>
                      prev.includes(item.id) ? prev : [...prev, item.id],
                    );
                  }}
                  className="block w-full rounded-2xl border border-coral-500/20 bg-card p-4 text-left transition-colors active:bg-secondary"
                >
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-coral-500">{item.title}</p>
                  <p className="mt-1 text-sm font-semibold text-foreground">{item.detail}</p>
                </button>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center gap-3 py-16">
                <Bell className="h-12 w-12 text-coral-500/40" />
                <p className="text-sm text-muted-foreground">Henüz bildirim yok</p>
              </div>
            )}
          </div>
        )}
      </main>

      <Dialog open={isProjectDialogOpen} onOpenChange={setIsProjectDialogOpen}>
        <DialogContent className="max-w-[360px] rounded-[28px] border-none p-0">
          <DialogHeader className="border-b border-border px-5 py-4 text-left">
            <DialogTitle>Projeler</DialogTitle>
            <DialogDescription>
              Katılımcı olarak geçiş yapmak istediğiniz projeyi seçin.
            </DialogDescription>
          </DialogHeader>
          <div className="px-3 py-3">
            <div className="flex flex-col gap-2">
              {projectOptions.map((project) => {
                const isSelected = project.id === selectedProject?.id;
                return (
                  <button
                    key={project.id}
                    type="button"
                    onClick={() => {
                      setSelectedProjectId(project.id);
                      setIsProjectDialogOpen(false);
                    }}
                    className={`flex items-center justify-between rounded-2xl border px-4 py-3 text-left transition-colors ${
                      isSelected
                        ? "border-gold-500/30 bg-gold-500/10"
                        : "border-border bg-card active:bg-secondary"
                    }`}
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-foreground">{project.name}</p>
                      <p className="mt-1 text-[11px] text-muted-foreground">{project.dateRange}</p>
                      <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{project.location}</p>
                    </div>
                    <div className="ml-3 flex h-9 w-9 items-center justify-center">
                      {isSelected ? (
                        <Check className="h-5 w-5 text-gold-500" />
                      ) : (
                        <ChevronRight className="h-5 w-5 text-muted-foreground" />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <nav className="relative flex-shrink-0 overflow-hidden border-t border-[#d6deed] px-2 pb-2 pt-2 shadow-[0_-6px_18px_rgba(15,23,42,0.05)]">
        <div className="absolute inset-0 bg-[linear-gradient(90deg,_#fef4ea_0%,_#f6f2f7_28%,_#edf2fb_56%,_#f4faf7_100%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(180deg,_rgba(255,255,255,0.80)_0%,_rgba(255,255,255,0.35)_100%)]" />
        <div className="absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,_rgba(242,140,40,0.12)_0%,_rgba(16,43,100,0.24)_50%,_rgba(25,86,77,0.14)_100%)]" />
        <div className="relative flex items-stretch gap-1">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => handleTabChange(tab.key)}
                className={`relative flex flex-1 flex-col items-center gap-1 rounded-2xl border px-1 py-2.5 transition-colors ${
                  isActive
                    ? `border-current bg-current/10 shadow-[0_8px_18px_rgba(15,23,42,0.06)] ${tab.activeColor}`
                    : "border-transparent text-slate-500"
                }`}
              >
                <div className="relative">
                  <tab.icon className={`h-5 w-5 ${isActive ? tab.activeColor : ""}`} />
                  {tab.badge && (
                    <span className="absolute -top-1.5 -right-2.5 flex h-4 w-4 items-center justify-center rounded-full bg-danger text-[8px] font-bold text-white">
                      {tab.badge}
                    </span>
                  )}
                </div>
                <span className="text-[9px] font-bold">{tab.label}</span>
                <div className={`mt-0.5 h-0.5 w-5 rounded-full ${isActive ? tab.activeColor.replace("text-", "bg-") : "bg-transparent"}`} />
              </button>
            );
          })}
        </div>
      </nav>

      <footer
        className="relative flex h-[68px] flex-shrink-0 items-center overflow-hidden border-t border-white/10"
        style={{ background: `linear-gradient(140deg, ${brandBg} 0%, #183B7E 52%, #19564D 100%)` }}
      >
        <img
          src={footerBanner}
          alt="Footer banner"
          className="absolute right-0 top-0 w-full max-w-none"
          style={{ height: "calc(100% + 18px)" }}
        />
      </footer>
    </div>
  );
};

export default Index;
