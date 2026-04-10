import React, { useEffect } from "react";
import { BookOpen, FileText, GraduationCap, LayoutGrid, Presentation, ScrollText } from "lucide-react";
import type { Role } from "@/data/types";
import { getAppConfig } from "@/services/core";

interface OperationsScreenProps {
  role: Role;
  onPendingSyncChange?: (count: number) => void;
}

const meetingModules = [
  {
    key: "program-flow",
    title: "Program Akışı",
    description: "Günün genel oturum planını ve salon dağılımını izleyin.",
    icon: LayoutGrid,
    tint: "#F28C28",
    background: "linear-gradient(145deg, rgba(242,140,40,0.18) 0%, rgba(255,255,255,0.96) 100%)",
  },
  {
    key: "abstracts",
    title: "Bildiriler",
    description: "Sözlü ve poster bildirileri başlıklarına göre görüntüleyin.",
    icon: FileText,
    tint: "#1B3F73",
    background: "linear-gradient(145deg, rgba(27,63,115,0.18) 0%, rgba(255,255,255,0.96) 100%)",
  },
  {
    key: "courses",
    title: "Kurslar",
    description: "Katılım durumunuza göre kurs detaylarını burada toplayın.",
    icon: GraduationCap,
    tint: "#2E7D5A",
    background: "linear-gradient(145deg, rgba(46,125,90,0.18) 0%, rgba(255,255,255,0.96) 100%)",
  },
  {
    key: "certificates",
    title: "Sertifikalar",
    description: "Kazanılan ve hazır bekleyen sertifikaları bu alandan yönetin.",
    icon: ScrollText,
    tint: "#A66729",
    background: "linear-gradient(145deg, rgba(166,103,41,0.18) 0%, rgba(255,255,255,0.96) 100%)",
  },
];

export function OperationsScreen({ role, onPendingSyncChange }: OperationsScreenProps) {
  const appConfig = getAppConfig(role);
  const projectName = appConfig.content.project_name || "Etkinlik";
  const heroImage = appConfig.branding.hero_image_url || "";
  const primaryColor = appConfig.branding.primary_color || "#F28C28";
  const baseColor = appConfig.branding.base_color || "#102B64";

  useEffect(() => {
    onPendingSyncChange?.(0);
  }, [onPendingSyncChange]);

  return (
    <div className="flex flex-col gap-3 px-4 pb-5 pt-1">
      <section
        className="overflow-hidden rounded-[28px] border"
        style={{
          borderColor: `${primaryColor}40`,
          background: `linear-gradient(150deg, ${baseColor} 0%, #1A4B74 56%, #27634F 100%)`,
          boxShadow: `0 12px 28px ${primaryColor}26`,
        }}
      >
        <div className="relative h-40 w-full">
          <img
            src={heroImage}
            alt={`${projectName} toplantı görseli`}
            className="h-full w-full bg-slate-950 object-contain object-center sm:object-cover sm:object-top"
            loading="eager"
            fetchPriority="high"
            decoding="async"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-950/82 via-slate-950/42 to-transparent" />
        </div>
        <div className="relative -mt-12 px-5 pb-5">
          <div className="flex items-start gap-3">
            <div
              className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl border"
              style={{ borderColor: `${primaryColor}55`, backgroundColor: `${primaryColor}1F` }}
            >
              <Presentation className="h-6 w-6" style={{ color: primaryColor }} />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-white/70">
                Toplantı Modülü
              </p>
              <h2 className="mt-1 text-[22px] font-bold leading-6 text-white">Oturumlar</h2>
            </div>
          </div>
          <div className="mt-3 h-1.5 w-16 rounded-full" style={{ backgroundColor: primaryColor }} />
        </div>
      </section>

      <div className="grid grid-cols-2 gap-3">
        {meetingModules.map((module) => {
          const Icon = module.icon;
          return (
            <article
              key={module.key}
              className="rounded-[24px] border p-4"
              style={{
                borderColor: `${module.tint}30`,
                background: module.background,
                boxShadow: "0 10px 22px rgba(15, 23, 42, 0.08)",
              }}
            >
              <div
                className="flex h-12 w-12 items-center justify-center rounded-2xl"
                style={{ backgroundColor: `${module.tint}18` }}
              >
                <Icon className="h-6 w-6" style={{ color: module.tint }} />
              </div>
              <h3 className="mt-4 text-[15px] font-bold leading-5 text-slate-950">{module.title}</h3>
              <p className="mt-2 text-[11px] leading-4 text-slate-600">{module.description}</p>
            </article>
          );
        })}
      </div>

      <div className="rounded-[24px] border border-slate-200 bg-white/90 px-4 py-4 shadow-[0_10px_24px_rgba(15,23,42,0.06)]">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900/6">
            <BookOpen className="h-5 w-5 text-slate-700" />
          </div>
          <div>
            <p className="text-[12px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              Yakında Çekirdek Entegrasyonu
            </p>
            <p className="mt-1 text-sm font-semibold text-slate-900">
              Oturumlar, kurslar, bildiriler ve sertifikalar proje bazlı olarak bu ekrana bağlanacak.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
