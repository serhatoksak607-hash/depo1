import React, { Suspense, lazy, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, Bell, ClipboardList, Home, Navigation, QrCode } from "lucide-react";
import type { Role, TabKey } from "@/data/types";
import { HomeScreen } from "@/components/screens/HomeScreen";
import { OperationsScreen } from "@/components/screens/OperationsScreen";
import { JobsScreen } from "@/components/screens/JobsScreen";
import brandFallbackLogo from "@/assets/brand/Ontur.png";
import creatroLogo from "@/assets/brand/kontrast_logo.png";
import { toast } from "@/components/ui/sonner";
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
  const loadingLogo = appConfig.branding.loading_logo_url || appConfig.branding.logo_url || creatroLogo;
  const loadingPrimary = appConfig.branding.loading_primary_color || appConfig.branding.primary_color || "#58C7F2";
  const loadingBase = appConfig.branding.loading_base_color || appConfig.branding.base_color || "#091028";
  const gradientEnd = appConfig.branding.base_color || "#10203F";

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

const Index = () => {
  const [activeTab, setActiveTab] = useState<TabKey>("home");
  const [role, setRole] = useState<Role>("driver");
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
  const { data: bootstrap } = useQuery({
    queryKey: ["core", "bootstrap", role],
    queryFn: async () => getCoreBootstrap(role),
    staleTime: Infinity,
  });
  const brandBg = appConfig.branding.base_color || "#091028";
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
    () => new Set<TabKey>([
      ...tabs.map((tab) => tab.key),
      ...((appConfig.navigation.hidden_routes || []) as TabKey[]),
    ]),
    [appConfig.navigation.hidden_routes, tabs],
  );

  useEffect(() => {
    if (allowedRoutes.has(activeTab)) return;
    setActiveTab((appConfig.navigation.home_route as TabKey) || "home");
  }, [activeTab, allowedRoutes, appConfig.navigation.home_route]);

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
      {/* Header */}
      <header className="flex-shrink-0 border-b border-border" style={{ backgroundColor: brandBg }}>
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
            <h1 className={`text-base font-bold uppercase tracking-[0.12em] ${tabColorMap[activeTab] ?? "text-primary-foreground"}`}>{tabTitles[activeTab]}</h1>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setRole(role === "driver" ? "greeter" : "driver")}
                className="rounded-lg bg-navy-600 px-3 py-1.5 text-[10px] font-bold text-azure-300"
              >
                {role === "driver" ? "Sürücü" : "Karşılamacı"}
              </button>
            </div>
          </div>
        )}
      </header>

      <main className="flex-1 overflow-y-auto overflow-x-hidden pt-[9px]">
        {activeTab === "home" && (
          alertsViewOpen ? (
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
              unreadNotifications={unreadNotifications}
              unreadAlerts={unreadAlerts}
              role={role}
              appConfig={appConfig}
            />
          )
        )}
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
            <QrCheckinScreen role={role} />
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

      <nav className="flex-shrink-0 border-t border-border bg-card/95 px-2 pb-2 pt-2 backdrop-blur">
        <div className="flex items-stretch gap-1">
          {tabs.map(tab => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => handleTabChange(tab.key)}
                className={`relative flex flex-1 flex-col items-center gap-1 rounded-2xl border px-1 py-2.5 transition-colors ${
                  isActive
                    ? `border-current bg-current/10 ${tab.activeColor}`
                    : "border-transparent text-muted-foreground"
                }`}
              >
                <div className="relative">
                  <tab.icon className={`h-5 w-5 ${isActive ? tab.activeColor : ""}`} />
                  {tab.badge && (
                    <span className="absolute -top-1.5 -right-2.5 flex h-4 w-4 items-center justify-center rounded-full bg-danger text-[8px] font-bold text-white">{tab.badge}</span>
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
        className="flex h-[60px] flex-shrink-0 items-center justify-between px-4"
        style={{ backgroundColor: brandBg }}
      >
        <a
          href="https://www.creatro.com.tr"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center"
        >
          <img
            src={creatroLogo}
            alt="Creatro"
            className="h-[50px] w-auto object-contain"
            width={150}
            height={50}
          />
        </a>
        <div className="text-right">
          <p
            className={`text-[11px] font-bold tracking-[0.18em] ${
              isOnline ? "text-azure-300" : "text-danger"
            }`}
          >
            • {isOnline ? "Çevrim İçi" : "Çevrim Dışı"}
          </p>
          <p className="text-[11px] text-slate-200">{lastSyncText}</p>
        </div>
      </footer>
    </div>
  );
};

export default Index;
