import { QrCode } from "lucide-react";
import type { Role } from "@/data/types";
import { getCoreBootstrap } from "@/services/core";

interface QrCheckinScreenProps {
  synced?: boolean;
  role: Role;
}

export function QrCheckinScreen({ role }: QrCheckinScreenProps) {
  const bootstrap = getCoreBootstrap(role);
  const { appConfig, operations } = bootstrap;
  const brandPrimary = appConfig.branding.primary_color || "#58C7F2";
  const brandBase = appConfig.branding.base_color || "#091028";
  const activeOperation = operations[0];
  const projectName = appConfig.content.project_name || activeOperation?.project_name || "Proje";
  const projectDateRange = appConfig.content.project_date_range || "Tarih bilgisi eklenecek";
  const projectLocation = appConfig.content.project_location || activeOperation?.start_location || "Konum eklenecek";
  const projectQrValue =
    appConfig.content.project_qr_value ||
    `PROJECT:${appConfig.project_id || "default"}|ROLE:${role}|PERSON:Serhat-OKSAK`;
  const qrImageUrl = `https://api.qrserver.com/v1/create-qr-code/?size=360x360&data=${encodeURIComponent(projectQrValue)}`;

  return (
    <div className="flex flex-col gap-3 px-4 pb-6">
      <div className="rounded-2xl border border-border bg-card p-5">
        <div className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl md:h-12 md:w-12"
            style={{ backgroundColor: `${brandPrimary}1A` }}
          >
            <QrCode className="h-5 w-5 md:h-6 md:w-6" style={{ color: brandPrimary }} />
          </div>
          <div className="min-w-0">
            <h2 className="truncate text-base font-bold text-foreground md:text-lg">Proje QR</h2>
            <p className="line-clamp-1 text-[11px] text-muted-foreground md:text-xs">
              Modüle girildiğinde proje QR kodu doğrudan açılır
            </p>
          </div>
        </div>
        <p className="mt-4 text-sm leading-6 text-muted-foreground">
          Bu ekranda tarayıcı açılmaz. Katılımcının projeye ait QR kodu doğrudan gösterilir.
        </p>
      </div>

      <div className="rounded-2xl border border-border bg-card p-5">
        <div className="flex flex-col items-center">
          <div
            className="w-full max-w-[320px] overflow-hidden rounded-[28px] border p-4"
            style={{ borderColor: `${brandPrimary}33`, backgroundColor: `${brandBase}08` }}
          >
            <div className="rounded-2xl bg-white p-4 shadow-sm">
              <img
                src={qrImageUrl}
                alt={`${projectName} proje QR kodu`}
                className="mx-auto aspect-square w-full max-w-[280px] rounded-xl object-contain"
                loading="eager"
              />
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-2xl bg-secondary/60 px-4 py-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
            Proje Bilgisi
          </p>
          <p className="mt-2 text-base font-bold text-foreground">{projectName}</p>
          <p className="mt-1 text-sm text-muted-foreground">{projectDateRange}</p>
          <p className="mt-1 text-sm text-muted-foreground">{projectLocation}</p>
          <p className="mt-3 break-all rounded-xl bg-card px-3 py-2 text-[11px] text-muted-foreground">
            {projectQrValue}
          </p>
        </div>
      </div>
    </div>
  );
}
