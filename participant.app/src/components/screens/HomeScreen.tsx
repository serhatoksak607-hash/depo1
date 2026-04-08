import React from "react";
import { Bell, FolderOpen, Navigation, QrCode, Receipt } from "lucide-react";
import type { AppConfig, Role, TabKey } from "@/data/types";
import { formatPersonName } from "@/lib/utils";
import { getShellProfile } from "@/services/core";

interface HomeScreenProps {
  onOpenTab: (tab: TabKey) => void;
  onOpenAlerts: () => void;
  unreadNotifications: number;
  unreadAlerts: number;
  role: Role;
  appConfig: AppConfig;
}

function formatPlateLabel(value: string) {
  const cleaned = value.toUpperCase().replace(/[^A-Z0-9]/g, "");
  const match = cleaned.match(/^(\d{2})([A-Z]{1,3})(\d{2,4})$/);

  if (match) {
    return `${match[1]} ${match[2]} ${match[3]}`;
  }

  return value.trim().toUpperCase();
}

export function HomeScreen({
  onOpenTab,
  onOpenAlerts,
  unreadNotifications,
  unreadAlerts,
  role,
  appConfig,
}: HomeScreenProps) {
  const hasUnread = unreadNotifications > 0;
  const profile = getShellProfile(role);
  const hasAlerts = unreadAlerts > 0;
  const heroImage = appConfig.branding.hero_image_url || "";
  const brandPrimary = appConfig.branding.primary_color || "#58C7F2";
  const brandBase = appConfig.branding.base_color || "#091028";
  const modules = appConfig.modules;
  const isModuleVisible = (moduleKey: string) =>
    modules.project_modules[moduleKey]?.visible ??
    modules.company_modules[moduleKey]?.visible ??
    modules.shared_modules[moduleKey]?.visible ??
    false;
  const showQr = isModuleVisible("qr_checkin");
  const showNotifications = isModuleVisible("notifications");
  const showOperations = isModuleVisible("operations");
  const showFiles = isModuleVisible("files");
  const showExpenses = isModuleVisible("expenses");
  const plateMain = formatPlateLabel(profile.plate_label || "");
  const driverName = formatPersonName(profile.full_name || "");
  const roleLabel =
    role === "greeter" ? "Karşılamacı" : role === "driver" ? "Sürücü" : "Operasyon Sorumlusu";

  return (
    <div className="flex flex-col gap-3 px-4 pb-[8px] pt-0">
      <div
        className="flex items-center justify-between gap-3 rounded-2xl border bg-card px-4 py-2.5"
        style={{ borderColor: `${brandPrimary}33` }}
      >
        <div className="min-w-0">
          <p className="truncate text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            {roleLabel}
          </p>
          <p className="truncate text-sm font-bold text-foreground">{driverName}</p>
        </div>
        <div className="flex min-w-[118px] flex-col items-end gap-1">
          <p className="max-w-full truncate text-[11px] font-medium text-muted-foreground">
            {profile.vehicle_label}
          </p>
          <div className="flex items-stretch overflow-hidden rounded-sm border-2 border-slate-400 bg-white shadow-sm">
            <div className="flex w-4 items-end justify-center bg-[#1D4ED8] px-1 pb-0.5 text-white">
              <span className="text-[6px] font-black leading-none tracking-[0.04em]">TR</span>
            </div>
            <div className="flex min-h-[22px] items-center px-1.5 text-[10px] font-black tracking-[0.1em] text-slate-900">
              {plateMain}
            </div>
          </div>
        </div>
      </div>

      <button
        onClick={onOpenAlerts}
        className="flex items-center gap-3 rounded-2xl border border-gold-500/20 bg-card px-4 py-3 text-left active:bg-secondary"
      >
        <span className="h-2.5 w-2.5 rounded-full bg-gold-500" />
        <div>
          <p className="text-sm font-semibold text-foreground">
            {hasAlerts ? `${unreadAlerts} okunmayan uyarı var` : "Şuan herşey yolunda..."}
          </p>
        </div>
      </button>

      {showNotifications && (
        <button
          onClick={() => onOpenTab("notifications")}
          className="flex items-center gap-3 rounded-2xl border border-coral-500/20 bg-card px-4 py-3 text-left active:bg-secondary"
        >
          <span className="h-2.5 w-2.5 rounded-full bg-coral-500" />
          <div>
            <p className="text-sm font-semibold text-foreground">
              {hasUnread ? "Yeni bildirimler var" : "Bildirimler"}
            </p>
          </div>
        </button>
      )}

      {(showQr || showNotifications) && (
        <div className="grid grid-cols-2 gap-3">
          {showQr && (
            <button
              onClick={() => onOpenTab("qr-checkin")}
              className={`flex min-h-[118px] flex-col items-center justify-center gap-2 rounded-2xl border bg-card p-4 text-center transition-colors active:bg-secondary ${
                !showNotifications ? "col-span-2" : ""
              }`}
              style={{ borderColor: `${brandPrimary}33` }}
            >
              <div
                className="flex h-14 w-14 items-center justify-center rounded-xl"
                style={{ backgroundColor: `${brandPrimary}1A` }}
              >
                <QrCode className="h-6 w-6" style={{ color: brandPrimary }} />
              </div>
              <div>
                <p className="text-sm font-bold text-foreground">QR Okut</p>
                <p className="mt-0.5 text-[10px] text-muted-foreground">Hızlı biniş</p>
              </div>
            </button>
          )}

          {showNotifications && (
            <button
              onClick={() => onOpenTab("notifications")}
              className={`relative flex min-h-[118px] flex-col items-center justify-center gap-2 rounded-2xl border border-coral-500/20 bg-card p-4 text-center transition-colors active:bg-secondary ${
                !showQr ? "col-span-2" : ""
              }`}
            >
              <div className="relative flex h-14 w-14 items-center justify-center rounded-xl bg-coral-500/10">
                <Bell className="h-6 w-6 text-coral-500" />
                {hasUnread && (
                  <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-danger text-[9px] font-bold text-white">
                    {unreadNotifications}
                  </span>
                )}
              </div>
              <div>
                <p className="text-sm font-bold text-foreground">Bildirimler</p>
                <p className="mt-0.5 text-[10px] text-muted-foreground">
                  {hasUnread ? "Detayları aç" : "Güncel durum"}
                </p>
              </div>
            </button>
          )}
        </div>
      )}

      {showOperations && (
        <button
          onClick={() => onOpenTab("operations")}
          className="w-full overflow-hidden rounded-2xl border text-left transition-colors"
          style={{
            borderColor: `${brandPrimary}4D`,
            backgroundColor: brandBase,
            boxShadow: `0 8px 18px ${brandPrimary}2E`,
          }}
        >
          <div className="relative h-36 w-full">
            <img
              src={heroImage}
              alt="Transfer aracı"
              className="h-full w-full object-cover"
              loading="eager"
              fetchPriority="high"
              decoding="async"
              width={640}
              height={288}
            />
            <div
              className="absolute inset-0"
              style={{ background: `linear-gradient(to top, ${brandBase} 0%, ${brandBase}99 55%, transparent 100%)` }}
            />
          </div>
          <div className="relative -mt-10 px-6 pb-5">
            <div className="flex items-center gap-3">
              <div
                className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl border"
                style={{ borderColor: `${brandPrimary}4D`, backgroundColor: `${brandPrimary}1A` }}
              >
                <Navigation className="h-6 w-6" style={{ color: brandPrimary }} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-primary-foreground">Operasyon</h2>
                <p className="text-xs" style={{ color: `${brandPrimary}` }}>Aktif işleri aç</p>
              </div>
            </div>
            <div className="mt-3 h-1 w-14 rounded-full" style={{ backgroundColor: brandPrimary }} />
          </div>
        </button>
      )}

      {(showFiles || showExpenses) && (
        <div className="grid grid-cols-2 gap-3">
          {showFiles && (
            <button
              onClick={() => onOpenTab("files")}
              className={`flex min-h-[118px] flex-col items-center justify-center gap-2 rounded-2xl border border-success/20 bg-card p-4 text-center transition-colors active:bg-secondary ${
                !showExpenses ? "col-span-2" : ""
              }`}
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-success/10">
                <FolderOpen className="h-6 w-6 text-success" />
              </div>
              <div>
                <p className="text-sm font-bold text-foreground">Dosyalarım</p>
                <p className="mt-0.5 text-[10px] text-muted-foreground">Fiş ve belge</p>
              </div>
            </button>
          )}

          {showExpenses && (
            <button
              onClick={() => onOpenTab("expenses")}
              className={`flex min-h-[118px] flex-col items-center justify-center gap-2 rounded-2xl border border-gold-500/20 bg-card p-4 text-center transition-colors active:bg-secondary ${
                !showFiles ? "col-span-2" : ""
              }`}
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-gold-500/10">
                <Receipt className="h-6 w-6 text-gold-500" />
              </div>
              <div>
                <p className="text-sm font-bold text-foreground">Masraflar</p>
                <p className="mt-0.5 text-[10px] text-muted-foreground">Masraf gir</p>
              </div>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
