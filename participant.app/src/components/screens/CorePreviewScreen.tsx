import { Database, RefreshCw, ShieldCheck, Zap } from "lucide-react";
import type { Role } from "@/data/types";
import { formatPersonName } from "@/lib/utils";
import { getCoreBootstrap } from "@/services/core";

interface CorePreviewScreenProps {
  role: Role;
  onBack: () => void;
}

function KeyValueRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 border-t border-border/70 py-2 first:border-t-0 first:pt-0">
      <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </p>
      <p className="text-right text-sm font-semibold text-foreground">{value}</p>
    </div>
  );
}

export function CorePreviewScreen({ role, onBack }: CorePreviewScreenProps) {
  const bootstrap = getCoreBootstrap(role);
  const brandPrimary = bootstrap.appConfig.branding.primary_color || "#58C7F2";
  const firstOperation = bootstrap.operations[0] ?? null;
  const policyRows = [
    {
      key: "Telefon görünürlüğü",
      level: "Genel > Müşteri firma > Proje > Transfer",
      resolved: firstOperation?.resolved_policies.phone_visible ? "Göster" : "Gizle",
    },
    {
      key: "WhatsApp izni",
      level: "Genel > Müşteri firma > Proje > Transfer",
      resolved: firstOperation?.resolved_policies.whatsapp_allowed ? "Açık" : "Kapalı",
    },
    {
      key: "QR doğrulama",
      level: "Genel > Firma > Proje > Araç / kişi istisnası",
      resolved: firstOperation?.resolved_policies.qr_validation_mode || "Yok",
    },
    {
      key: "QR sonuç görünürlüğü",
      level: "Genel > Müşteri firma > Proje > Araç",
      resolved: bootstrap.qrResultVisibility?.showDriverGreeterNotice ? "Karşılamacı -> Sürücü görünür" : "Sessiz",
    },
    {
      key: "Dinamik QR süresi",
      level: "Genel > Firma > Proje > Araç",
      resolved: bootstrap.dynamicQrPolicy ? `${bootstrap.dynamicQrPolicy.intervalSeconds} sn` : "Yok",
    },
  ];
  const moduleRows = [
    ["operations", bootstrap.appConfig.modules.shared_modules.operations?.visible],
    ["tasks", bootstrap.appConfig.modules.shared_modules.tasks?.visible],
    ["qr_checkin", bootstrap.appConfig.modules.shared_modules.qr_checkin?.visible],
    ["notifications", bootstrap.appConfig.modules.shared_modules.notifications?.visible],
    ["files", bootstrap.appConfig.modules.shared_modules.files?.visible],
    ["expenses", bootstrap.appConfig.modules.shared_modules.expenses?.visible],
    ["flight_tracking", bootstrap.appConfig.modules.company_modules.flight_tracking?.visible],
    ["support_center", bootstrap.appConfig.modules.company_modules.support_center?.visible],
    ["passenger_contact", bootstrap.appConfig.modules.project_modules.passenger_contact?.visible],
    ["route_planning", bootstrap.appConfig.modules.project_modules.route_planning?.visible],
  ];

  return (
    <div className="flex flex-col gap-3 px-4 pb-6">
      <button
        onClick={onBack}
        className="inline-flex h-10 items-center justify-center rounded-xl border border-border bg-card px-4 text-xs font-bold text-foreground active:bg-secondary"
      >
        Ana sayfaya dön
      </button>

      <div
        className="rounded-3xl border bg-card p-5"
        style={{ borderColor: `${brandPrimary}33` }}
      >
        <div className="flex items-center gap-3">
          <div
            className="flex h-12 w-12 items-center justify-center rounded-xl"
            style={{ backgroundColor: `${brandPrimary}1A` }}
          >
            <Database className="h-6 w-6" style={{ color: brandPrimary }} />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
              Core Önizleme
            </p>
            <h2 className="text-lg font-bold text-foreground">Bootstrap Özeti</h2>
          </div>
        </div>

        <div className="mt-4 rounded-2xl bg-secondary/40 p-4">
          <KeyValueRow label="Rol" value={bootstrap.role === "driver" ? "Sürücü" : "Karşılamacı"} />
          <KeyValueRow label="Uygulama" value={bootstrap.appConfig.content.app_title || "CofTransfer"} />
          <KeyValueRow label="Senkron" value={bootstrap.syncedAt} />
          <KeyValueRow label="Operasyon" value={`${bootstrap.operations.length} kayıt`} />
          <KeyValueRow label="Görev" value={`${Object.keys(bootstrap.jobsByDate).length} gün`} />
        </div>
      </div>

      <div className="rounded-3xl border border-border bg-card p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-success/10">
            <ShieldCheck className="h-6 w-6 text-success" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
              Profil ve Shell
            </p>
            <h3 className="text-base font-bold text-foreground">{formatPersonName(bootstrap.shellProfile.full_name)}</h3>
          </div>
        </div>

        <div className="mt-4 rounded-2xl bg-secondary/40 p-4">
          <KeyValueRow label="Araç" value={bootstrap.shellProfile.vehicle_label} />
          <KeyValueRow label="Plaka" value={bootstrap.shellProfile.plate_label} />
          <KeyValueRow label="Tenant" value={bootstrap.appConfig.tenant_id} />
          <KeyValueRow label="Proje" value={bootstrap.appConfig.project_id || "Yok"} />
        </div>
      </div>

      <div className="rounded-3xl border border-border bg-card p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-azure-500/10">
            <RefreshCw className="h-6 w-6 text-azure-500" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
              Dinamik QR
            </p>
            <h3 className="text-base font-bold text-foreground">Resolved Policy</h3>
          </div>
        </div>

        <div className="mt-4 rounded-2xl bg-secondary/40 p-4">
          <KeyValueRow
            label="Durum"
            value={bootstrap.dynamicQrPolicy?.enabled ? "Aktif" : "Kapalı"}
          />
          <KeyValueRow
            label="Süre"
            value={
              bootstrap.dynamicQrPolicy
                ? `${bootstrap.dynamicQrPolicy.intervalSeconds} saniye`
                : "Yok"
            }
          />
          <KeyValueRow
            label="Format"
            value={bootstrap.dynamicQrPolicy?.formatType || "Yok"}
          />
        </div>
      </div>

      <div className="rounded-3xl border border-border bg-card p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gold-500/10">
            <Zap className="h-6 w-6 text-gold-500" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
              QR Sonuç Görünürlüğü
            </p>
            <h3 className="text-base font-bold text-foreground">Role göre çözüm</h3>
          </div>
        </div>

        <div className="mt-4 rounded-2xl bg-secondary/40 p-4">
          <KeyValueRow
            label="Sürücü kendi"
            value={bootstrap.qrResultVisibility?.showDriverOwnNotice ? "Göster" : "Sessiz"}
          />
          <KeyValueRow
            label="Karşılamacı -> Sürücü"
            value={bootstrap.qrResultVisibility?.showDriverGreeterNotice ? "Göster" : "Gizle"}
          />
          <KeyValueRow
            label="Sürücü -> Karşılamacı"
            value={bootstrap.qrResultVisibility?.showGreeterDriverNotice ? "Göster" : "Gizle"}
          />
        </div>
      </div>

      {firstOperation && (
        <div className="rounded-3xl border border-border bg-card p-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
            İlk Operasyon
          </p>
          <p className="mt-2 text-base font-bold text-foreground">
            {formatPersonName(firstOperation.passenger_name)}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {firstOperation.flight_code} • {firstOperation.project_name || "Genel operasyon"}
          </p>
          <div className="mt-4 rounded-2xl bg-secondary/40 p-4">
            <KeyValueRow label="QR doğrulama" value={firstOperation.resolved_policies.qr_validation_mode} />
            <KeyValueRow
              label="Araç esnekliği"
              value={firstOperation.resolved_policies.allow_project_cross_vehicle ? "Açık" : "Kapalı"}
            />
            <KeyValueRow
              label="Kişi araç kilidi"
              value={firstOperation.resolved_policies.person_vehicle_restricted ? "Aktif" : "Pasif"}
            />
          </div>
        </div>
      )}

      <div className="rounded-3xl border border-border bg-card p-5">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
          Policy Tablosu
        </p>
        <div className="mt-4 overflow-hidden rounded-2xl border border-border">
          <div className="grid grid-cols-[1.1fr_1.2fr_0.8fr] gap-3 bg-secondary/70 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
            <span>Kural</span>
            <span>Katman</span>
            <span className="text-right">Resolved</span>
          </div>
          {policyRows.map((row) => (
            <div
              key={row.key}
              className="grid grid-cols-[1.1fr_1.2fr_0.8fr] gap-3 border-t border-border px-3 py-3 text-sm"
            >
              <p className="font-semibold text-foreground">{row.key}</p>
              <p className="text-[11px] leading-5 text-muted-foreground">{row.level}</p>
              <p className="text-right text-xs font-bold text-foreground">{row.resolved}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-3xl border border-border bg-card p-5">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
          Modül Tablosu
        </p>
        <div className="mt-4 overflow-hidden rounded-2xl border border-border">
          <div className="grid grid-cols-[1.4fr_0.6fr] gap-3 bg-secondary/70 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
            <span>Modül</span>
            <span className="text-right">Durum</span>
          </div>
          {moduleRows.map(([moduleKey, visible]) => (
            <div
              key={String(moduleKey)}
              className="grid grid-cols-[1.4fr_0.6fr] gap-3 border-t border-border px-3 py-3 text-sm"
            >
              <p className="font-semibold text-foreground">{moduleKey}</p>
              <p className="text-right text-xs font-bold text-foreground">
                {visible ? "Açık" : "Kapalı"}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
