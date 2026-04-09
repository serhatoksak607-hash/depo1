import { QrCode } from "lucide-react";
import type { ProjectSummary, Role } from "@/data/types";
import { getCoreBootstrap } from "@/services/core";

interface QrCheckinScreenProps {
  synced?: boolean;
  role: Role;
  selectedProject: ProjectSummary;
}

export function QrCheckinScreen({ role, selectedProject }: QrCheckinScreenProps) {
  const bootstrap = getCoreBootstrap(role);
  const { appConfig } = bootstrap;
  const brandPrimary = appConfig.branding.primary_color || "#58C7F2";
  const brandBase = appConfig.branding.base_color || "#091028";
  const qrImageUrl = `https://api.qrserver.com/v1/create-qr-code/?size=360x360&data=${encodeURIComponent(selectedProject.qrValue)}`;
  const participantCode =
    selectedProject.qrValue
      .split("|")
      .map((part) => part.trim())
      .find((part) => part.startsWith("PARTICIPANT:") || part.startsWith("PERSON:"))
      ?.split(":")
      .slice(1)
      .join(":") || "Katılımcı kodu";

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
          <div className="flex min-w-0 flex-1 items-center">
            <p className="min-w-0 truncate text-[12px] leading-5 text-muted-foreground md:text-[13px]">
              <span className="font-bold text-foreground">{selectedProject.name}</span> QR kodunuz
            </p>
          </div>
        </div>
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
                alt={`${selectedProject.name} proje QR kodu`}
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
          <p className="mt-2 text-base font-bold text-foreground">{selectedProject.name}</p>
          <p className="mt-1 text-sm text-muted-foreground">{selectedProject.dateRange}</p>
          <p className="mt-1 text-sm text-muted-foreground">{selectedProject.location}</p>
          <p className="mt-3 break-all rounded-xl bg-card px-3 py-2 text-[11px] text-muted-foreground">
            Katılımcı Kodu: {participantCode}
          </p>
        </div>
      </div>
    </div>
  );
}
