import React from "react";
import { Bell, ChevronDown, ExternalLink, FolderOpen, QrCode, Receipt } from "lucide-react";
import type { AppConfig, ProjectSummary, Role, TabKey } from "@/data/types";
import { formatPersonName } from "@/lib/utils";
import { getShellProfile } from "@/services/core";
import toplantiCardIcon from "@/assets/brand/toplanti-card-transparent.png";

interface HomeScreenProps {
  onOpenTab: (tab: TabKey) => void;
  onOpenAlerts: () => void;
  onOpenProjectPicker: () => void;
  unreadNotifications: number;
  unreadAlerts: number;
  role: Role;
  appConfig: AppConfig;
  selectedProject: ProjectSummary;
}

export function HomeScreen({
  onOpenTab,
  onOpenAlerts,
  onOpenProjectPicker,
  unreadNotifications,
  unreadAlerts,
  role,
  appConfig,
  selectedProject,
}: HomeScreenProps) {
  const hasUnread = unreadNotifications > 0;
  const profile = getShellProfile(role);
  const hasAlerts = unreadAlerts > 0;
  const heroImage = appConfig.branding.hero_image_url || "";
  const brandPrimary = appConfig.branding.primary_color || "#F28C28";
  const brandBase = appConfig.branding.base_color || "#102B64";
  const qrAccent = "#102B64";
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
  const userName = formatPersonName(profile.full_name || "");
  const roleLabel =
    role === "greeter" ? "Karşılamacı" : role === "driver" ? "Katılımcı" : "Operasyon Sorumlusu";

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
          <p className="truncate text-sm font-bold text-foreground">{userName}</p>
        </div>
        <div className="flex min-w-[170px] flex-col items-end text-right">
          <button
            type="button"
            onClick={onOpenProjectPicker}
            className="inline-flex max-w-full items-center gap-1 truncate text-[11px] font-semibold text-foreground transition-opacity hover:opacity-80"
          >
            <span className="truncate">{selectedProject.name}</span>
            <ChevronDown className="h-3 w-3 flex-shrink-0 text-muted-foreground/70" />
          </button>
          <button
            type="button"
            onClick={onOpenProjectPicker}
            className="mt-0.5 inline-flex max-w-full items-center truncate text-[10px] font-medium text-muted-foreground transition-opacity hover:opacity-80"
          >
            <span className="truncate">{selectedProject.dateRange}</span>
          </button>
          <a
            href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(selectedProject.location)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-0.5 inline-flex max-w-full items-center gap-1 truncate text-[10px] font-medium text-azure-500/90 underline-offset-2 hover:underline"
          >
            <span className="truncate">{selectedProject.location}</span>
            <ExternalLink className="h-3 w-3 flex-shrink-0 text-azure-500/70" />
          </a>
        </div>
      </div>

      <button
        onClick={onOpenAlerts}
        className="flex items-center gap-3 rounded-2xl border border-gold-500/20 bg-card px-4 py-3 text-left active:bg-secondary"
      >
        <span className="h-2.5 w-2.5 rounded-full bg-gold-500" />
        <div>
          <p className="text-sm font-semibold text-foreground">
            {hasAlerts ? `${unreadAlerts} okunmayan uyarı var` : "Şu an her şey yolunda..."}
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
              style={{ borderColor: `${qrAccent}33` }}
            >
              <div
                className="flex h-14 w-14 items-center justify-center rounded-xl"
                style={{ backgroundColor: `${qrAccent}1A` }}
              >
                <QrCode className="h-6 w-6" style={{ color: qrAccent }} />
              </div>
              <div>
                <p className="text-sm font-bold text-foreground">QR Okut</p>
                <p className="mt-0.5 text-[10px] text-muted-foreground">Proje QR ekranı</p>
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
            background: `linear-gradient(140deg, ${brandBase} 0%, #183B7E 54%, #19564D 100%)`,
            boxShadow: `0 8px 18px ${brandPrimary}2E`,
          }}
        >
          <div className="relative h-40 w-full">
            <img
              src={heroImage}
              alt="Hero görseli"
              className="h-full w-full object-cover object-top"
              loading="eager"
              fetchPriority="high"
              decoding="async"
              width={640}
              height={288}
            />
            <div
              className="absolute inset-0"
              style={{ background: "linear-gradient(to top, rgba(16, 43, 100, 0.92) 0%, rgba(24, 59, 126, 0.56) 20%, rgba(25, 86, 77, 0.16) 38%, rgba(25, 86, 77, 0.00) 60%)" }}
            />
          </div>
          <div className="relative -mt-10 px-6 pb-5">
            <div className="flex items-center gap-3">
              <div
                className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl border"
                style={{ borderColor: `${brandPrimary}4D`, backgroundColor: `${brandPrimary}1A` }}
              >
                <span
                  aria-hidden="true"
                  className="h-7 w-7"
                  style={{
                    backgroundColor: brandPrimary,
                    WebkitMaskImage: `url(${toplantiCardIcon})`,
                    maskImage: `url(${toplantiCardIcon})`,
                    WebkitMaskRepeat: "no-repeat",
                    maskRepeat: "no-repeat",
                    WebkitMaskPosition: "center",
                    maskPosition: "center",
                    WebkitMaskSize: "contain",
                    maskSize: "contain",
                  }}
                />
              </div>
              <div>
                <h2 className="text-xl font-bold text-primary-foreground">Toplantı</h2>
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
