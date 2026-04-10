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

  return (
    <div className="flex flex-col gap-3 px-4 pb-6">
      <div className="rounded-2xl border border-border bg-card p-5">
        <div className="flex flex-col items-center">
          <div
            className="mb-4 flex h-12 w-12 shrink-0 items-center justify-center rounded-xl"
            style={{ backgroundColor: `${brandPrimary}1A` }}
          >
            <QrCode className="h-6 w-6" style={{ color: brandPrimary }} />
          </div>
          <div
            className="w-full max-w-[320px] overflow-hidden rounded-[28px] border p-4"
            style={{ borderColor: `${brandPrimary}33`, backgroundColor: `${brandBase}08` }}
          >
            <div className="rounded-2xl bg-white p-4 shadow-sm">
              <img
                src={qrImageUrl}
                alt="Katılımcı QR kodu"
                className="mx-auto aspect-square w-full max-w-[280px] rounded-xl object-contain"
                loading="eager"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
