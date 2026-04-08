import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
  MapPin,
  Plane,
  Receipt,
  Users,
} from "lucide-react";
import type { Job, Role, RouteStop, TabKey } from "@/data/types";
import { formatPersonName, getDisplayLabel } from "@/lib/utils";
import { getExpenses, getFiles, getJobsByDate, getOperations, getStatusColor, getStatusLabel } from "@/services/core";
import { useAppState } from "@/state/app-state";

function toDateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseDateKey(date: string): Date {
  const [year, month, day] = date.split("-").map(Number);
  return new Date(year, (month || 1) - 1, day || 1);
}

function getBestAvailableDate(dates: string[], targetDate: string): string {
  if (dates.length === 0) return targetDate;
  if (dates.includes(targetDate)) return targetDate;

  const targetTime = parseDateKey(targetDate).getTime();
  return dates.reduce((closestDate, currentDate) => {
    const closestDiff = Math.abs(parseDateKey(closestDate).getTime() - targetTime);
    const currentDiff = Math.abs(parseDateKey(currentDate).getTime() - targetTime);
    return currentDiff < closestDiff ? currentDate : closestDate;
  });
}

function getTurkeyDateKey(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Istanbul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function addDays(date: string, days: number): string {
  const d = parseDateKey(date);
  d.setDate(d.getDate() + days);
  return toDateKey(d);
}

function formatDateLabel(date: string): string {
  const d = parseDateKey(date);
  const days = ["Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi"];
  const months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  return `${d.getDate()} ${months[d.getMonth()]} ${days[d.getDay()]}`;
}

function getMapUrl(stop: RouteStop): string {
  if (stop.map_data?.coordinates?.lat && stop.map_data?.coordinates?.lng) {
    return `https://www.google.com/maps/dir/?api=1&destination=${stop.map_data.coordinates.lat},${stop.map_data.coordinates.lng}`;
  }

  const dest = stop.map_data?.address || stop.address_info || stop.value;
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(dest)}`;
}

function getFallbackJobStop(job: Job, type: "start" | "end"): RouteStop {
  const isStart = type === "start";
  const mainLocation = isStart ? job.pickup_main_location : job.dropoff_main_location;
  const subLocation = isStart ? job.pickup_sub_location : job.dropoff_sub_location;
  const value = isStart ? job.pickup_location : job.dropoff_location;

  return {
    label: isStart ? "Başlangıç" : "Bitiş",
    value,
    main_location: mainLocation || value,
    sub_location: subLocation || value,
    address_info: value || mainLocation || subLocation,
    map_data: { source: "address", address: value || mainLocation || subLocation },
    map_share: { policy: "auto", approved: true },
    boarding_passenger_tcs: [],
    alighting_passenger_tcs: [],
  };
}

function getRoutePlanUrl(job: Job, routeStops?: RouteStop[] | null) {
  const effectiveStops = routeStops && routeStops.length > 1 ? routeStops : null;

  if (!effectiveStops) {
    const origin = encodeURIComponent(job.pickup_location || job.pickup_main_location);
    const destination = encodeURIComponent(job.dropoff_location || job.dropoff_main_location);
    return `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}`;
  }

  const originStop = effectiveStops[0];
  const destinationStop = effectiveStops[effectiveStops.length - 1];
  const waypoints = effectiveStops
    .slice(1, -1)
    .map((stop) => encodeURIComponent(stop.map_data?.address || stop.address_info || stop.value))
    .join("|");

  const origin = encodeURIComponent(originStop.map_data?.address || originStop.address_info || originStop.value);
  const destination = encodeURIComponent(
    destinationStop.map_data?.address || destinationStop.address_info || destinationStop.value,
  );

  return waypoints
    ? `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}&waypoints=${waypoints}`
    : `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}`;
}

function getJobRouteSummary(job: Job, routeStops?: RouteStop[]) {
  const effectiveStops = routeStops && routeStops.length > 0 ? routeStops : null;
  const middleCount = effectiveStops ? Math.max(effectiveStops.length - 2, 0) : 0;

  return {
    startMain: effectiveStops?.[0]?.main_location || job.pickup_main_location,
    startSub: effectiveStops?.[0]?.sub_location || job.pickup_sub_location || "",
    endMain: effectiveStops?.[effectiveStops.length - 1]?.main_location || job.dropoff_main_location,
    endSub: effectiveStops?.[effectiveStops.length - 1]?.sub_location || job.dropoff_sub_location || "",
    middleLabel: middleCount > 0 ? `${middleCount} durak` : "Direkt",
    startStop: effectiveStops?.[0] || getFallbackJobStop(job, "start"),
    endStop: effectiveStops?.[effectiveStops.length - 1] || getFallbackJobStop(job, "end"),
  };
}

type DetailTab = "passengers" | "expenses" | "files";

interface JobsScreenProps {
  role: Role;
  onOpenTab: (tab: TabKey) => void;
}

interface JobCardProps {
  job: Job;
  role: Role;
  expanded: boolean;
  detailTab: DetailTab;
  routePlanOpen: boolean;
  onToggleExpanded: () => void;
  onDetailTabChange: (tab: DetailTab) => void;
  onRoutePlanToggle: () => void;
  onOpenTab: (tab: TabKey) => void;
  onOpenLinkedTab: (tab: TabKey, job: Job) => void;
}

function getMatchingOperation(role: Role, job: Job | null) {
  if (!job) return null;
  return (
    getOperations(role).find(
      (operation) =>
        operation.project_name === job.project_name &&
        operation.passenger_name === job.passenger_name &&
        operation.flight_code === job.flight_no,
    ) ?? null
  );
}

function JobCard({
  job,
  role,
  expanded,
  detailTab,
  routePlanOpen,
  onToggleExpanded,
  onDetailTabChange,
  onRoutePlanToggle,
  onOpenTab,
  onOpenLinkedTab,
}: JobCardProps) {
  const sc = getStatusColor(job.status);
  const operationForJob = getMatchingOperation(role, job);
  const routeSummary = getJobRouteSummary(job, operationForJob?.route_stops);
  const isCompletedJob = job.status === "completed";
  const relatedExpenses = getExpenses().filter((expense) => expense.operation_label?.includes(job.time));
  const relatedFiles = getFiles().filter((file) => file.operation_label?.includes(job.time) || file.project_name === job.project_name);
  const passengerCount = operationForJob?.passenger_list.length ?? 0;
  const routeStopCount = operationForJob?.route_stops?.length ?? 0;
  const typeLabel = operationForJob?.transfer_direction === "arrival" ? "Geliş" : operationForJob?.transfer_direction === "departure" ? "Gidiş" : "Görev";
  const jobAlerts = (() => {
    if (job.job_type === "operational" && job.operational_note) {
      return [job.operational_note];
    }
    if (!operationForJob) return [];
    const alerts: string[] = [];
    if (operationForJob.transfer_direction === "arrival" && operationForJob.flight_eta) {
      alerts.push(`ETA ${operationForJob.flight_eta} olarak izleniyor.`);
    }
    if ((operationForJob.route_stops?.length || 0) > 2) {
      alerts.push(`${operationForJob.route_stops!.length - 2} ara durak planlandı.`);
    }
    if (relatedExpenses.some((expense) => expense.settlement_status === "bekliyor")) {
      alerts.push("Bekleyen mahsup kaydı bulunuyor.");
    }
    if (relatedFiles.some((file) => file.important)) {
      alerts.push("Önemli operasyon belgesi mevcut.");
    }
    return alerts;
  })();

  return (
    <div
      className={`overflow-hidden rounded-2xl border border-border transition-all ${
        isCompletedJob ? "bg-slate-600/10 opacity-65 saturate-50 brightness-75" : "bg-card"
      }`}
    >
      <div className={`h-1 ${isCompletedJob ? "bg-success/50" : "bg-azure-500/70"}`} />
      <div className="p-4">
        <div className="mb-3">
          <div className="grid grid-cols-[1fr_auto_1fr] items-start gap-2">
            <div className="flex min-w-0 items-center gap-1.5">
              <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase ${sc.bg} ${sc.text}`}>
                {`${getStatusLabel(job.status)} - ${typeLabel}`}
              </span>
              {job.operational_badge && (
                <span className="rounded-full bg-coral-500/10 px-2 py-1 text-[10px] font-bold uppercase text-coral-500">
                  {job.operational_badge}
                </span>
              )}
            </div>
            <div className="flex justify-center">
              <span className="text-xs font-semibold text-muted-foreground">{job.role_assignment}</span>
            </div>
            <div className="flex flex-col items-end gap-1 min-w-0">
              <span className="inline-flex items-center gap-1 rounded-lg bg-secondary px-2 py-1">
                <Clock className="h-3 w-3 text-muted-foreground" />
                <span className="text-[15px] font-bold leading-none text-foreground">{job.time}</span>
              </span>
            </div>
          </div>
          <div className="mt-0.5 grid grid-cols-2 items-center gap-2">
            <div className="flex min-h-[2.6rem] min-w-0 items-center justify-start">
              <div className="max-h-[2.6rem] w-full overflow-hidden text-left">
                <p className="text-base font-bold leading-5 text-foreground">{getDisplayLabel(job.passenger_name, job.greeting_name)}</p>
                <p className="truncate text-[11px] text-muted-foreground">{job.project_name}</p>
              </div>
            </div>
            <div className="flex min-w-0 items-center justify-end gap-1 whitespace-nowrap">
              <span className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-secondary px-2 py-1">
                <Users className="h-3 w-3 text-muted-foreground" />
                <span className="text-xs font-semibold text-foreground">{passengerCount}</span>
              </span>
              <span className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-secondary px-2 py-1 text-foreground">
                <Plane className="h-3 w-3" />
                <span className="text-xs font-semibold">{job.flight_no}</span>
              </span>
            </div>
          </div>
        </div>

        <div className="mb-3 grid grid-cols-[minmax(0,2fr)_minmax(0,1fr)] items-stretch gap-2">
          <button
            type="button"
            onClick={onToggleExpanded}
            className="flex h-[42px] w-full items-center justify-between rounded-xl border border-border bg-secondary/30 px-3 py-2 text-left transition-colors active:bg-secondary"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate text-[11px] font-semibold text-foreground">
                  {expanded ? "Detay Paneli Kapat" : "Detay Paneli Aç"}
                </span>
                <span className={`inline-flex flex-shrink-0 items-center rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.12em] ${
                  expanded ? "bg-secondary text-muted-foreground" : "bg-azure-500/15 text-azure-500"
                }`}>
                  {expanded ? "Açık" : "Hazır"}
                </span>
              </div>
              <p className="mt-0.5 truncate text-[10px] text-muted-foreground">
                {expanded ? "Görev detay içeriği açık." : "Görev detay alanını aç."}
              </p>
            </div>
            {expanded ? <ChevronUp className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" /> : <ChevronDown className="h-3.5 w-3.5 flex-shrink-0 text-foreground/70" />}
          </button>
          <div className="flex h-[42px] min-w-0 items-center justify-between gap-2 rounded-xl bg-secondary/60 px-2.5 py-1.5">
            <div className="min-w-0 flex flex-1 flex-col justify-center leading-none">
              <span className="truncate text-[7px] font-bold uppercase tracking-tight text-muted-foreground">Atama</span>
              <p className="truncate pt-0.5 text-[9px] font-bold leading-none text-foreground">{job.role_assignment}</p>
            </div>
            <div className="flex h-6 min-w-6 items-center justify-center rounded-lg bg-azure-500/15 px-1.5">
              <Clock className="h-3 w-3 text-azure-500" />
            </div>
          </div>
        </div>

        {expanded && (
          <div className="mb-3 space-y-3">
            {jobAlerts.length > 0 && (
              <div className="space-y-1.5">
                {jobAlerts.map((alert, index) => (
                  <div key={`${alert}-${index}`} className="flex items-start gap-2.5 rounded-lg border border-gold-500/15 bg-gold-500/5 px-3.5 py-2.5">
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-gold-500" />
                    <p className="text-sm text-foreground">{alert}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="mb-3 grid grid-cols-[1fr_auto_1fr] items-stretch gap-2 rounded-xl bg-secondary/30 px-3 py-2.5">
          <div className="min-w-0 text-left">
            <button
              type="button"
              onClick={() => window.open(getMapUrl(routeSummary.startStop), "_blank", "noopener,noreferrer")}
              className="hidden"
            >
              Başlangıç
            </button>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <button
                type="button"
                onClick={() => window.open(getMapUrl(routeSummary.startStop), "_blank", "noopener,noreferrer")}
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full transition-colors active:bg-secondary/60"
                aria-label="Başlangıç konumunu aç"
              >
                <MapPin className="h-3 w-3 text-emerald-500" />
              </button>
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-foreground">{routeSummary.startMain}</p>
                {routeSummary.startSub && (
                  <p className="truncate text-[11px] text-muted-foreground">{routeSummary.startSub}</p>
                )}
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onRoutePlanToggle}
            className="flex min-w-[52px] items-center justify-center self-stretch rounded-lg px-1 py-2 text-[11px] font-semibold text-muted-foreground transition-colors active:bg-secondary/60"
            aria-label="Rota planını aç"
          >
            {routeSummary.middleLabel !== "Direkt" ? (
              <div className="flex items-center gap-1.5">
                <span className="text-sm leading-none text-muted-foreground/50">→</span>
                <span className="rounded-full bg-card px-2 py-1">{routeSummary.middleLabel}</span>
                <span className="text-sm leading-none text-muted-foreground/50">→</span>
              </div>
            ) : (
              <span className="text-base leading-none text-muted-foreground/50">⟶</span>
            )}
          </button>
          <div className="min-w-0 text-right">
            <button
              type="button"
              onClick={() => window.open(getMapUrl(routeSummary.endStop), "_blank", "noopener,noreferrer")}
              className="hidden"
            >
              Bitiş
            </button>
            <div className="flex items-center justify-end gap-1.5 text-xs text-muted-foreground">
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-foreground">{routeSummary.endMain}</p>
                {routeSummary.endSub && (
                  <p className="truncate text-[11px] text-muted-foreground">{routeSummary.endSub}</p>
                )}
              </div>
              <button
                type="button"
                onClick={() => window.open(getMapUrl(routeSummary.endStop), "_blank", "noopener,noreferrer")}
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full transition-colors active:bg-secondary/60"
                aria-label="Bitiş konumunu aç"
              >
                <MapPin className="h-3 w-3 text-red-500" />
              </button>
            </div>
          </div>
        </div>

        {expanded && (
          <div className="mt-3 space-y-3">
            {routePlanOpen && operationForJob?.route_stops && operationForJob.route_stops.length > 0 && (
              <div className="space-y-2 rounded-xl border border-border bg-secondary/20 p-3">
                {operationForJob.route_stops.map((stop, index) => (
                  <div key={`${stop.label}-${index}`} className="rounded-xl bg-card p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-[10px] font-bold uppercase text-muted-foreground">{stop.label}</p>
                        <p className="text-sm font-bold text-foreground">{stop.main_location}</p>
                        {stop.sub_location && <p className="text-xs text-muted-foreground">{stop.sub_location}</p>}
                        <p className="mt-1 line-clamp-2 text-[11px] text-muted-foreground/80">{stop.address_info}</p>
                      </div>
                      <a href={getMapUrl(stop)} target="_blank" rel="noopener noreferrer" className="flex h-8 items-center gap-1 rounded-lg px-2 text-[11px] font-bold active:opacity-90">
                        <MapPin className="h-3.5 w-3.5 text-azure-500" />
                        Haritada Aç
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-xl border border-border bg-card p-3 text-center">
                <Users className="mx-auto h-4 w-4 text-azure-500" />
                <p className="mt-1 text-lg font-bold text-foreground">{passengerCount}</p>
                <p className="text-[10px] text-muted-foreground">Yolcu</p>
              </div>
              <div className="rounded-xl border border-border bg-card p-3 text-center">
                <Receipt className="mx-auto h-4 w-4 text-gold-500" />
                <p className="mt-1 text-lg font-bold text-foreground">{relatedExpenses.length}</p>
                <p className="text-[10px] text-muted-foreground">Masraf</p>
              </div>
              <div className="rounded-xl border border-border bg-card p-3 text-center">
                <FileText className="mx-auto h-4 w-4 text-success" />
                <p className="mt-1 text-lg font-bold text-foreground">{relatedFiles.length}</p>
                <p className="text-[10px] text-muted-foreground">Dosya</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {operationForJob?.transfer_direction && (
                <div className="rounded-lg border border-border bg-card px-3 py-2.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Yön</p>
                  <p className="mt-0.5 text-sm font-semibold text-foreground">
                    {operationForJob.transfer_direction === "arrival" ? "Geliş" : "Gidiş"}
                  </p>
                </div>
              )}
              <div className="rounded-lg border border-border bg-card px-3 py-2.5">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Durak</p>
                <p className="mt-0.5 text-sm font-semibold text-foreground">
                  {routeStopCount > 0 ? `${Math.max(routeStopCount - 2, 0)} ara durak` : "Direkt"}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-1.5">
              {([
                { key: "passengers" as DetailTab, label: "Yolcular", icon: Users },
                { key: "expenses" as DetailTab, label: "Masraflar", icon: Receipt },
                { key: "files" as DetailTab, label: "Dosyalar", icon: FileText },
              ] as const).map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => onDetailTabChange(key)}
                  className={`flex items-center justify-center gap-1.5 rounded-lg py-2.5 text-xs font-semibold transition-colors ${
                    detailTab === key ? "bg-primary text-primary-foreground" : "bg-secondary/60 text-muted-foreground"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </button>
              ))}
            </div>

            {detailTab === "passengers" && (
              <div className="rounded-xl border border-border bg-card p-4">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Yolcu Listesi</p>
                {operationForJob ? (
                  <div className="space-y-2">
                    {operationForJob.passenger_list.map((passenger) => (
                      <div key={passenger.tc} className="flex items-center gap-3 rounded-lg bg-secondary/40 px-3 py-2.5">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-azure-500/10 text-xs font-bold text-azure-500">
                          {passenger.full_name.charAt(0)}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-foreground">{formatPersonName(passenger.full_name)}</p>
                          <p className="text-[10px] text-muted-foreground">{passenger.tc} • {passenger.title}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Bu görev için yolcu listesi henüz eşleşmedi.</p>
                )}
              </div>
            )}

            {detailTab === "expenses" && (
              <div className="rounded-xl border border-border bg-card p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Göreve Bağlı Masraflar</p>
                  <button onClick={() => onOpenLinkedTab("expenses", job)} className="rounded-lg bg-gold-500/10 px-3 py-1.5 text-[11px] font-semibold text-gold-500 active:bg-gold-500/20">
                    Tam ekranda aç
                  </button>
                </div>
                {relatedExpenses.length > 0 ? (
                  <div className="space-y-2">
                    {relatedExpenses.map((expense) => (
                      <div key={expense.id} className="flex items-center justify-between rounded-lg bg-secondary/40 px-3 py-2.5">
                        <div>
                          <p className="text-sm font-semibold text-foreground">{expense.description}</p>
                          <p className="text-[10px] text-muted-foreground">{expense.flow === "alacak" ? "Alacak" : "Verecek"}</p>
                        </div>
                        <p className={`text-sm font-bold ${expense.flow === "alacak" ? "text-success" : "text-danger"}`}>{expense.amount} {expense.currency}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Bu göreve bağlı finans kaydı yok.</p>
                )}
              </div>
            )}

            {detailTab === "files" && (
              <div className="rounded-xl border border-border bg-card p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Göreve Bağlı Dosyalar</p>
                  <button onClick={() => onOpenLinkedTab("files", job)} className="rounded-lg bg-success/10 px-3 py-1.5 text-[11px] font-semibold text-success active:bg-success/20">
                    Tam ekranda aç
                  </button>
                </div>
                {relatedFiles.length > 0 ? (
                  <div className="space-y-2">
                    {relatedFiles.map((file) => (
                      <div key={file.id} className="flex items-center gap-3 rounded-lg bg-secondary/40 px-3 py-2.5">
                        <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-semibold text-foreground">{file.name}</p>
                          <p className="text-[10px] text-muted-foreground">{file.operation_label || file.project_name || "Genel belge"}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Bu göreve bağlı dosya yok.</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function JobsScreen({ role, onOpenTab }: JobsScreenProps) {
  const allJobs = getJobsByDate(role);
  const availableDates = useMemo(() => Object.keys(allJobs).sort(), [allJobs]);
  const todayDate = useMemo(() => getTurkeyDateKey(), []);
  const resolvedTodayDate = useMemo(
    () => getBestAvailableDate(availableDates, todayDate),
    [availableDates, todayDate],
  );
  const [selectedDate, setSelectedDate] = useState(resolvedTodayDate);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [detailTab, setDetailTab] = useState<DetailTab>("passengers");
  const [routePlanOpen, setRoutePlanOpen] = useState(false);
  const { setSelectedOperationContext } = useAppState();
  const jobs = allJobs[selectedDate] || [];

  const openLinkedTab = (tab: TabKey, job: Job) => {
    setSelectedOperationContext({
      operationLabel: `${job.time} ${job.project_name}`,
      projectName: job.project_name,
      jobTime: job.time,
    });
    onOpenTab(tab);
  };

  useEffect(() => {
    setSelectedDate((currentDate) => {
      if (currentDate === resolvedTodayDate) {
        return currentDate;
      }

      if (availableDates.length === 0 || availableDates.includes(currentDate)) {
        return currentDate;
      }

      return resolvedTodayDate;
    });
  }, [availableDates, resolvedTodayDate]);

  return (
    <div className="flex flex-col gap-4 px-4 pb-6">
      {/* Date Navigator */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => { setSelectedJobId(null); setRoutePlanOpen(false); setSelectedDate(addDays(selectedDate, -1)); }}
          className="flex h-12 w-12 flex-shrink-0 flex-col items-center justify-center rounded-xl border border-border bg-card active:bg-secondary transition-colors"
        >
          <ChevronLeft className="h-5 w-5 text-foreground" />
          <span className="text-[8px] font-semibold leading-none text-muted-foreground">Önceki</span>
        </button>
        <div className="flex flex-1 flex-col items-center gap-1">
          <div className="flex w-full items-center justify-center rounded-xl bg-primary px-4 py-3">
            <p className="text-sm font-bold text-primary-foreground">{formatDateLabel(selectedDate)}</p>
          </div>
          <button
            onClick={() => { setSelectedJobId(null); setRoutePlanOpen(false); setSelectedDate(resolvedTodayDate); }}
            className="text-[11px] font-semibold text-azure-500 active:text-azure-400"
          >
            Bugüne git
          </button>
        </div>
        <button
          onClick={() => { setSelectedJobId(null); setRoutePlanOpen(false); setSelectedDate(addDays(selectedDate, 1)); }}
          className="flex h-12 w-12 flex-shrink-0 flex-col items-center justify-center rounded-xl border border-border bg-card active:bg-secondary transition-colors"
        >
          <ChevronRight className="h-5 w-5 text-foreground" />
          <span className="text-[8px] font-semibold leading-none text-muted-foreground">Sonraki</span>
        </button>
      </div>

      {jobs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-card/50 px-6 py-12 text-center">
          <Clock className="mx-auto h-8 w-8 text-muted-foreground/40" />
          <p className="mt-3 text-sm font-medium text-muted-foreground">
            {role === "greeter" ? "Bu gün için karşılama görevi yok" : "Bu gün için görev yok"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground/60">Tarih değiştirerek diğer günleri kontrol edebilirsiniz</p>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">{jobs.length} görev</p>
          {jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              role={role}
              expanded={selectedJobId === job.id}
              detailTab={selectedJobId === job.id ? detailTab : "passengers"}
              routePlanOpen={selectedJobId === job.id ? routePlanOpen : false}
              onToggleExpanded={() => {
                const nextIsSame = selectedJobId === job.id;
                setSelectedJobId(nextIsSame ? null : job.id);
                setDetailTab("passengers");
                setRoutePlanOpen(false);
                if (!nextIsSame) {
                  setSelectedOperationContext({
                    operationLabel: `${job.time} ${job.project_name}`,
                    projectName: job.project_name,
                    jobTime: job.time,
                  });
                }
              }}
              onDetailTabChange={setDetailTab}
              onRoutePlanToggle={() => {
                setSelectedJobId(job.id);
                setRoutePlanOpen((prev) => (selectedJobId === job.id ? !prev : true));
              }}
              onOpenTab={onOpenTab}
              onOpenLinkedTab={openLinkedTab}
            />
          ))}
        </div>
      )}
    </div>
  );
}


