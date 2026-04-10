import React from "react";
import { ChevronRight, FileText, Mic, Presentation, Users } from "lucide-react";
import type { Role, TabKey } from "@/data/types";
import { getAppConfig } from "@/services/core";

interface JobsScreenProps {
  role: Role;
  onOpenTab: (tab: TabKey) => void;
}

const participantTasks = [
  {
    id: "oral-presentation",
    title: "Sözlü Bildiri Sunumu",
    time: "11 Nisan 2026 • 14:10",
    location: "Salon A",
    status: "Hazırlık Gerekli",
    tone: "bg-coral-500/10 text-coral-600",
    description: "Sunum dosyanızı yükleyin ve oturum başlamadan 20 dakika önce salonda hazır olun.",
  },
  {
    id: "session-chair",
    title: "Oturum Katılımı",
    time: "12 Nisan 2026 • 09:00",
    location: "Ana Salon",
    status: "Takvimde",
    tone: "bg-azure-500/10 text-azure-600",
    description: "Bilimsel programdaki size atanmış oturum başlangıcı için katılım onayı bekleniyor.",
  },
  {
    id: "satellite-symposium",
    title: "Uydu Sempozyumu",
    time: "12 Nisan 2026 • 12:30",
    location: "Fuaye Alanı",
    status: "Bilgilendirme",
    tone: "bg-emerald-500/10 text-emerald-600",
    description: "Ana sponsor sunumu ve networking oturumu aynı görev akışında gösterilecek.",
  },
];

export function JobsScreen({ role, onOpenTab }: JobsScreenProps) {
  const appConfig = getAppConfig(role);
  const projectName = appConfig.content.project_name || "Etkinlik";
  const primaryColor = appConfig.branding.primary_color || "#F28C28";

  return (
    <div className="flex flex-col gap-3 px-4 pb-5 pt-1">
      <section className="rounded-[28px] border border-slate-200 bg-white/92 p-4 shadow-[0_10px_24px_rgba(15,23,42,0.06)]">
        <div className="flex items-start gap-3">
          <div
            className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl"
            style={{ backgroundColor: `${primaryColor}18` }}
          >
            <Users className="h-6 w-6" style={{ color: primaryColor }} />
          </div>
          <div className="min-w-0">
            <p className="text-[12px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              Görevlerim
            </p>
            <h2 className="mt-1 text-lg font-bold leading-6 text-slate-950">
              {projectName} kapsamındaki bilimsel görevleriniz
            </h2>
            <p className="mt-2 text-[12px] leading-5 text-slate-600">
              Bu alan yalnızca toplantı, bildiri, kurs ve oturum katılım görevleri için kullanılacak.
            </p>
          </div>
        </div>
      </section>

      <div className="space-y-3">
        {participantTasks.map((task, index) => {
          const Icon = index === 0 ? Mic : index === 1 ? Presentation : FileText;
          return (
            <article
              key={task.id}
              className="rounded-[24px] border border-slate-200 bg-white/92 p-4 shadow-[0_10px_24px_rgba(15,23,42,0.05)]"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-slate-900/5">
                    <Icon className="h-5 w-5 text-slate-700" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-[15px] font-bold leading-5 text-slate-950">{task.title}</h3>
                    <p className="mt-1 text-[11px] text-slate-500">{task.time}</p>
                    <p className="mt-1 text-[11px] font-medium text-slate-600">{task.location}</p>
                  </div>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${task.tone}`}>
                  {task.status}
                </span>
              </div>
              <p className="mt-3 text-[12px] leading-5 text-slate-600">{task.description}</p>
            </article>
          );
        })}
      </div>

      <button
        type="button"
        onClick={() => onOpenTab("operations")}
        className="flex items-center justify-between rounded-[24px] border border-slate-200 bg-white/92 px-4 py-3 text-left shadow-[0_10px_24px_rgba(15,23,42,0.05)]"
      >
        <div>
          <p className="text-[12px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Toplantı Modülü
          </p>
          <p className="mt-1 text-sm font-bold text-slate-950">Alt modülleri aç ve detayları görüntüle</p>
        </div>
        <ChevronRight className="h-5 w-5 text-slate-400" />
      </button>
    </div>
  );
}
