import React, { useEffect, useState } from "react";
import {
  Check, Clock, Users, Plane, MapPin, Phone, ChevronDown, ChevronUp, ExternalLink, LoaderCircle
} from "lucide-react";
import type { Operation, Role, RouteStop } from "@/data/types";
import {
  getAppConfig,
  getOperations,
  getStatusLabel,
  getStatusColor,
  isPassengerPhoneVisible,
  isWhatsappAllowed,
} from "@/services/core";
import { formatPersonName, getDisplayLabel } from "@/lib/utils";
import { useAppState } from "@/state/app-state";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "@/components/ui/sonner";

interface OperationsScreenProps {
  role: Role;
  onPendingSyncChange?: (count: number) => void;
}

const CORE_TIME_OFFSET_STORAGE_KEY = "creatro_core_time_offset_ms";
const PASSENGER_SYNC_RETRY_MS = 2400;
const PASSENGER_SYNC_COMPLETE_MS = 900;
const STAGE_SYNC_COMPLETE_MS = 1100;

function getEffectiveNowMinutes(): number {
  const deviceNow = Date.now();
  let cachedOffsetMs = 0;

  try {
    const raw = window.localStorage.getItem(CORE_TIME_OFFSET_STORAGE_KEY);
    cachedOffsetMs = raw ? Number(raw) || 0 : 0;
  } catch {
    cachedOffsetMs = 0;
  }

  const effectiveNow = new Date(deviceNow + cachedOffsetMs);
  return effectiveNow.getHours() * 60 + effectiveNow.getMinutes();
}

function getTimeBadge(startTime: string, isArrival: boolean, eta?: string | null): { label: string; tone: string } {
  const nowMin = getEffectiveNowMinutes();
  const plannedStartMin = toMinutes(startTime);
  const effectiveStartMin =
    isArrival && eta && toMinutes(eta) < plannedStartMin ? toMinutes(eta) : plannedStartMin;
  const diff = effectiveStartMin - nowMin;
  const absDiff = Math.abs(diff);
  const warningThreshold = isArrival ? 30 : 50;
  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes} dk`;
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    if (remainingMinutes === 0) return `${hours} sa`;
    return `${hours} sa ${remainingMinutes} dk`;
  };
  if (diff > 0) {
    return {
      label: `${formatDuration(diff)} kaldı`,
      tone: diff <= warningThreshold ? "text-danger" : "text-azure-500",
    };
  }
  if (diff === 0) return { label: "Şimdi", tone: "text-danger" };
  return { label: `${formatDuration(absDiff)} gecikti`, tone: "text-danger" };
}

function canOpenMap(stop: RouteStop): boolean {
  const policy = stop.map_share?.policy || "auto";
  return policy !== "approval_required" || Boolean(stop.map_share?.approved);
}

function getMapUrl(stop: RouteStop): string {
  if (stop.map_data?.coordinates?.lat && stop.map_data?.coordinates?.lng) {
    return `https://www.google.com/maps/dir/?api=1&destination=${stop.map_data.coordinates.lat},${stop.map_data.coordinates.lng}`;
  }
  const dest = stop.map_data?.address || stop.address_info || stop.value;
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(dest)}`;
}

function getWhatsappUrl(phone: string): string {
  const normalizedPhone = phone.replace(/[^\d]/g, "");
  return `https://wa.me/${normalizedPhone}`;
}

function shouldShowStopSubtitle(stop: RouteStop) {
  const normalizedSubtitle = (stop.sub_location || "").trim().toLocaleLowerCase("tr-TR");
  const normalizedLabel = (stop.label || "").trim().toLocaleLowerCase("tr-TR");

  if (!normalizedSubtitle) return false;

  return normalizedSubtitle !== `${normalizedLabel} noktası`;
}

function toMinutes(value: string): number {
  const [h, m] = value.split(":").map(Number);
  return h * 60 + m;
}

function getEtaBadgeTone(startTime: string, eta?: string | null): string {
  if (!eta) return "bg-secondary text-foreground";

  const transferMinutes = toMinutes(startTime);
  const etaMinutes = toMinutes(eta);
  const delta = etaMinutes - transferMinutes;

  if (delta <= -10) return "bg-azure-500/15 text-azure-500";
  if (delta >= 20) return "bg-danger/15 text-danger";
  return "bg-secondary text-foreground";
}

function isEtaCritical(startTime: string, eta?: string | null): boolean {
  if (!eta) return false;
  return toMinutes(eta) - toMinutes(startTime) >= 20;
}

function getOperationQueueLabel(status: Operation["status"]): string {
  if (status === "ready") return "Hazır";
  if (status === "assigned" || status === "planned") return "Sıradaki";
  if (status === "completed") return "Tamamlandı";
  return getStatusLabel(status);
}

function getOperationTypeLabel(item: Operation): string {
  if (item.transfer_direction === "arrival") return "Geliş";
  if (item.transfer_direction === "departure") return "Gidiş";
  return "Tahsis";
}

function getFlightCodeTone(startTime: string, eta?: string | null): string {
  if (!eta) return "bg-secondary text-foreground";

  const transferMinutes = toMinutes(startTime);
  const etaMinutes = toMinutes(eta);
  const delta = etaMinutes - transferMinutes;

  if (delta <= -10) return "bg-azure-500/10 text-azure-500";
  if (delta >= 20) return "bg-danger/10 text-danger";
  return "bg-secondary text-foreground";
}

function isEtaDrivingSchedule(startTime: string, eta?: string | null): boolean {
  if (!eta) return false;
  return toMinutes(eta) < toMinutes(startTime);
}

function getRouteSummary(item: Operation): {
  startMain: string;
  startSub?: string;
  middle?: string;
  endMain: string;
  endSub?: string;
} {
  if (!item.route_stops || item.route_stops.length < 2) {
    return {
      startMain: item.start_location,
      endMain: item.end_location,
    };
  }

  const intermediateStopCount = Math.max(item.route_stops.length - 2, 0);
  const startStop = item.route_stops[0];
  const endStop = item.route_stops[item.route_stops.length - 1];

  return {
    startMain: startStop?.main_location || item.start_location,
    startSub: startStop?.sub_location || startStop?.value || item.start_location,
    middle: intermediateStopCount > 0 ? `${intermediateStopCount} durak` : undefined,
    endMain: endStop?.main_location || item.end_location,
    endSub: endStop?.sub_location || endStop?.value || item.end_location,
  };
}

function getPassengersByTcList(operation: Operation, tcList: string[]) {
  return tcList
    .map((tc) => operation.passenger_list.find((passenger) => passenger.tc === tc))
    .filter((passenger): passenger is Operation["passenger_list"][number] => Boolean(passenger));
}

function splitGreetingLabel(value: string) {
  return value
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .flatMap((line) => {
      const parts = line.split(/\s*&\s*/g).map((part) => part.trim()).filter(Boolean);
      return parts.flatMap((part, index) => (index < parts.length - 1 ? [part, "&"] : [part]));
      });
}

function getContactLabel(role: Role, tenantType?: "vehicle_company" | "agency" | "customer_company" | "saas") {
  if (tenantType === "agency") return "Yetkili";
  if (role === "greeter") return "Greeter";
  return "Karşılamacı";
}

function getEffectiveRouteStops(item: Operation): RouteStop[] {
  if (item.route_stops && item.route_stops.length > 0) {
    return item.route_stops;
  }

  return [
    {
      label: "Başlangıç",
      value: item.start_location,
      main_location: item.start_location,
      sub_location: "Başlangıç noktası",
      address_info: item.start_location,
      map_data: { source: "address", address: item.start_location },
      map_share: { policy: "auto", approved: true },
      boarding_passenger_tcs: [],
      alighting_passenger_tcs: [],
    },
    {
      label: "Bitiş",
      value: item.end_location,
      main_location: item.end_location,
      sub_location: "Bitiş noktası",
      address_info: item.end_location,
      map_data: { source: "address", address: item.end_location },
      map_share: { policy: "auto", approved: true },
      boarding_passenger_tcs: [],
      alighting_passenger_tcs: [],
    },
  ];
}

function WhatsappIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={className} aria-hidden="true">
      <path
        d="M16 3.2C8.93 3.2 3.2 8.93 3.2 16c0 2.5.72 4.94 2.08 7.03L3.2 28.8l5.95-1.95A12.73 12.73 0 0 0 16 28.8c7.07 0 12.8-5.73 12.8-12.8S23.07 3.2 16 3.2Z"
        fill="#25D366"
      />
      <path
        d="M24.07 19.48c-.34-.17-2.02-1-2.34-1.11-.31-.11-.54-.17-.77.17-.23.34-.88 1.11-1.08 1.34-.2.23-.4.26-.74.09-.34-.17-1.45-.53-2.77-1.68-1.02-.91-1.71-2.03-1.91-2.37-.2-.34-.02-.52.15-.69.15-.15.34-.4.51-.6.17-.2.23-.34.34-.57.11-.23.06-.43-.03-.6-.09-.17-.77-1.86-1.06-2.55-.28-.67-.57-.58-.77-.59h-.66c-.23 0-.6.09-.91.43-.31.34-1.2 1.17-1.2 2.85 0 1.68 1.23 3.31 1.4 3.54.17.23 2.41 3.68 5.84 5.16.82.35 1.46.56 1.96.72.82.26 1.57.22 2.16.13.66-.1 2.02-.83 2.31-1.63.28-.8.28-1.48.2-1.63-.09-.14-.31-.23-.66-.4Z"
        fill="white"
      />
    </svg>
  );
}

function isOperationCompleted(operation: Operation, completedStageCount: number): boolean {
  if (operation.status === "completed") return true;
  return completedStageCount >= operation.operation_stages.length;
}

function OperationCard({
  item,
  role,
  featured,
  onPendingSyncChange,
}: {
  item: Operation;
  role: Role;
  featured?: boolean;
  onPendingSyncChange?: (count: number) => void;
}) {
  const [expanded, setExpanded] = useState(featured || false);
  const [routeOpen, setRouteOpen] = useState(false);
  const [passengerListOpen, setPassengerListOpen] = useState(false);
  const [contactActionsOpen, setContactActionsOpen] = useState(false);
  const [passengerContactActions, setPassengerContactActions] = useState<Record<string, boolean>>({});
  const [stopPassengerView, setStopPassengerView] = useState<Record<number, "boarding" | "alighting" | null>>({});
  const [pendingPassengerSync, setPendingPassengerSync] = useState<Record<string, { checked: boolean; attempt: number }>>({});
  const [pendingStageIndex, setPendingStageIndex] = useState<number | null>(null);
  const isArrival = item.transfer_direction === "arrival";
  const timeBadge = getTimeBadge(item.start_time, isArrival, item.flight_eta);
  const statusColor = getStatusColor(item.status);
  const {
    qrArrivalRecords,
    passengerMarksByOperation,
    togglePassengerMark,
    stageIndexByOperation,
    setOperationStageIndex,
  } = useAppState();
  const completedStageCount = stageIndexByOperation[item.id] ?? 0;
  const activeStageIndex = Math.min(completedStageCount, Math.max(item.operation_stages.length - 1, 0));
  const isCompleted = isOperationCompleted(item, completedStageCount);
  const effectiveStatus: Operation["status"] = isCompleted ? "completed" : item.status;
  const queueLabel = getOperationQueueLabel(effectiveStatus);
  const operationTypeLabel = getOperationTypeLabel(item);
  const etaBadgeTone = getEtaBadgeTone(item.start_time, item.flight_eta);
  const etaCritical = isEtaCritical(item.start_time, item.flight_eta);
  const flightCodeTone = isArrival ? getFlightCodeTone(item.start_time, item.flight_eta) : "bg-secondary text-foreground";
  const etaDrivesSchedule = isArrival && isEtaDrivingSchedule(item.start_time, item.flight_eta);
  const passengerPhoneVisible = isPassengerPhoneVisible(item);
  const whatsappAllowed = isWhatsappAllowed(item);
  const appConfig = getAppConfig(role);
  const brandPrimary = appConfig.branding.primary_color || "#58C7F2";
  const contactLabel = getContactLabel(role, appConfig.tenant_type);
  const operations = getOperations(role);
  const sameProjectOperations =
    item.resolved_policies.allow_project_cross_vehicle && !item.resolved_policies.person_vehicle_restricted
      ? operations.filter((operation) => operation.project_name === item.project_name)
      : [item];
  const routeSummary = getRouteSummary(item);
  const effectiveRouteStops = getEffectiveRouteStops(item);
  const routePlanBadgeTone = routeOpen
    ? "bg-secondary text-muted-foreground"
    : isArrival
      ? "bg-azure-500/15 text-azure-500"
      : "bg-coral-500/15 text-coral-500";
  const routePlanContainerStyle = routeOpen
    ? undefined
    : {
        borderColor: `${brandPrimary}40`,
        background: `linear-gradient(180deg, ${brandPrimary}12 0%, rgba(15, 23, 42, 0.18) 100%)`,
        boxShadow: `0 10px 24px ${brandPrimary}18`,
      };
  const greetingLines = splitGreetingLabel(getDisplayLabel(item.passenger_name, item.greeting_name));
  const isSingleGreetingLine = greetingLines.length === 1;
  const checkedPassengers = new Set(passengerMarksByOperation[item.id] ?? []);
  const isDetailAreaVisible = expanded || routeOpen || passengerListOpen;
  const pendingCount = Object.keys(pendingPassengerSync).length + (pendingStageIndex !== null ? 1 : 0);
  const arrivedPassengerTcs = new Set(
    qrArrivalRecords
      .filter((record) => record.operationId === item.id && record.role === role)
      .map((record) => record.passengerTc),
  );
  const projectWideProcessedPassengerTcs = new Set<string>();
  sameProjectOperations.forEach((operation) => {
    (passengerMarksByOperation[operation.id] ?? []).forEach((tc) => projectWideProcessedPassengerTcs.add(tc));
    qrArrivalRecords
      .filter((record) => record.operationId === operation.id && record.role === role)
      .forEach((record) => projectWideProcessedPassengerTcs.add(record.passengerTc));
  });
  const effectivePassengerList = sameProjectOperations
    .flatMap((operation) => operation.passenger_list)
    .filter(
      (passenger, index, list) => list.findIndex((candidate) => candidate.tc === passenger.tc) === index,
    )
    .filter((passenger) => {
      const isProcessedHere = checkedPassengers.has(passenger.tc) || arrivedPassengerTcs.has(passenger.tc);
      return !projectWideProcessedPassengerTcs.has(passenger.tc) || isProcessedHere;
    });
  const passengerCount = effectivePassengerList.length;
  const allPassengersProcessed =
    effectivePassengerList.length > 0 &&
    effectivePassengerList.every(
      (passenger) => checkedPassengers.has(passenger.tc) || arrivedPassengerTcs.has(passenger.tc),
    );

  useEffect(() => {
    onPendingSyncChange?.(pendingCount);
  }, [onPendingSyncChange, pendingPassengerSync, pendingStageIndex]);

  useEffect(() => {
    const pendingEntries = Object.entries(pendingPassengerSync);
    if (pendingEntries.length === 0) return;

    const [tc, queueItem] = pendingEntries[0];
    const retryTimer = window.setTimeout(() => {
      setPendingPassengerSync((prev) => ({
        ...prev,
        [tc]: {
          ...queueItem,
          attempt: queueItem.attempt + 1,
        },
      }));

      window.setTimeout(() => {
        setPendingPassengerSync((prev) => {
          const next = { ...prev };
          delete next[tc];
          return next;
        });
      }, PASSENGER_SYNC_COMPLETE_MS);
    }, PASSENGER_SYNC_RETRY_MS);

    return () => window.clearTimeout(retryTimer);
  }, [pendingPassengerSync]);

  useEffect(() => {
    if (pendingStageIndex === null) return;

    const syncTimer = window.setTimeout(() => {
      const nextCompletedStageCount = Math.min(pendingStageIndex + 1, item.operation_stages.length);
      setOperationStageIndex(item.id, nextCompletedStageCount);
      setPendingStageIndex(null);
      toast.success("Durum güncellendi", {
        icon: <Check className="h-4 w-4 text-success" />,
        description:
          nextCompletedStageCount >= item.operation_stages.length
            ? "Operasyon tamamlandı."
            : `"${item.operation_stages[pendingStageIndex]}" işlemi kaydedildi.`,
      });
    }, STAGE_SYNC_COMPLETE_MS);

    return () => window.clearTimeout(syncTimer);
  }, [item.id, item.operation_stages, pendingStageIndex, setOperationStageIndex]);

  useEffect(() => {
    if (!allPassengersProcessed) return;
    if (completedStageCount >= 2 || pendingStageIndex !== null) return;
    if (Object.keys(pendingPassengerSync).length > 0) return;

    setPendingStageIndex(1);
  }, [allPassengersProcessed, completedStageCount, pendingPassengerSync, pendingStageIndex]);

  const togglePassenger = (tc: string) => {
    const willBeChecked = !checkedPassengers.has(tc);
    togglePassengerMark(item.id, tc);
    setPendingPassengerSync((prevSync) => ({
      ...prevSync,
      [tc]: {
        checked: willBeChecked,
        attempt: 0,
      },
    }));
  };

  const togglePassengerContactActions = (tc: string) => {
    setPassengerContactActions((prev) => ({
      ...prev,
      [tc]: !prev[tc],
    }));
  };

  useEffect(() => {
    if (!contactActionsOpen && Object.keys(passengerContactActions).length === 0) return;

    const handleOutsideClick = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.closest("[data-contact-menu-root='true']")) return;

      setContactActionsOpen(false);
      setPassengerContactActions({});
    };

    document.addEventListener("click", handleOutsideClick, true);
    return () => document.removeEventListener("click", handleOutsideClick, true);
  }, [contactActionsOpen, passengerContactActions]);

  const handleStageAction = (index: number) => {
    if (pendingStageIndex !== null) {
      toast.info("İşlem gönderiliyor", {
        description: "Önce mevcut durum aksiyonu için Core onayı bekleniyor.",
      });
      return;
    }

    if (isCompleted || index !== completedStageCount) return;
    setPendingStageIndex(index);
  };

  return (
    <div
      className={`rounded-2xl border border-border overflow-hidden transition-all ${
        isCompleted
          ? "bg-slate-600/10 opacity-65 saturate-50 brightness-75"
          : featured
            ? "bg-card shadow-sm"
            : "bg-card"
      }`}
    >
      {/* Top accent */}
      <div
        className={`h-1 ${isCompleted ? "bg-success/50" : ""}`}
        style={{
          backgroundColor: isCompleted
            ? undefined
            : featured
              ? brandPrimary
              : isArrival
                ? `${brandPrimary}99`
                : "#fb718599",
        }}
      />

      <div className="p-4">
        {/* Header row */}
        <div className="mb-3">
          <div className="grid grid-cols-[1fr_auto_1fr] items-start gap-2">
            <div className="flex min-w-0 items-center gap-1.5">
              <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase ${statusColor.bg} ${statusColor.text}`}>
                {`${queueLabel} - ${operationTypeLabel}`}
              </span>
            </div>
            <div className="flex justify-center">
              <span className={`text-xs font-semibold ${timeBadge.tone}`}>{timeBadge.label}</span>
            </div>
            <div className="flex flex-col items-end gap-1 min-w-0">
              <span className="inline-flex items-center gap-1 rounded-lg bg-secondary px-2 py-1">
                <Clock className="h-3 w-3 text-muted-foreground" />
                <span className="text-[15px] font-bold leading-none text-foreground">{item.start_time}</span>
              </span>
            </div>
          </div>
          <div className="mt-0.5 grid grid-cols-2 items-center gap-2">
            <div className="flex min-h-[2.6rem] min-w-0 items-center justify-start">
              <div className={`max-h-[2.6rem] w-full overflow-hidden text-left ${isSingleGreetingLine ? "flex min-h-[2.6rem] items-center justify-start" : "space-y-0.5"}`}>
                {greetingLines.map((line, index) => (
                  <p
                    key={`${line}-${index}`}
                    className={line === "&" ? "text-[11px] font-semibold leading-4 text-muted-foreground" : "text-base font-bold leading-5 text-foreground"}
                  >
                    {line}
                  </p>
                ))}
              </div>
            </div>
            <div className="flex min-w-0 items-center justify-end gap-1 whitespace-nowrap">
              <button
                type="button"
                onClick={() => {
                  setExpanded(false);
                  setRouteOpen(false);
                  setPassengerListOpen((prev) => !prev);
                }}
                className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-secondary px-2 py-1 active:bg-secondary/80"
              >
                <Users className="h-3 w-3 text-muted-foreground" />
                <span className="text-xs font-semibold text-foreground">{passengerCount}</span>
              </button>
              {item.flight_tracking_url ? (
                <a
                  href={item.flight_tracking_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 ${flightCodeTone}`}
                >
                  <Plane className="h-3 w-3" />
                  <span className="text-xs font-semibold">{item.flight_code}</span>
                </a>
              ) : (
                <span className={`inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 ${flightCodeTone}`}>
                  <Plane className="h-3 w-3" />
                  <span className="text-xs font-semibold">{item.flight_code}</span>
                </span>
              )}
              {isArrival && item.flight_eta && (
                <span className={`inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 ${etaBadgeTone}`}>
                  <span className="text-[10px] font-bold">ETA</span>
                  <span className={`${etaCritical ? "text-[15px]" : "text-xs"} ${etaDrivesSchedule ? "underline underline-offset-2 decoration-current" : ""} font-semibold leading-none`}>
                    {item.flight_eta}
                  </span>
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="-mt-2 mb-3 grid grid-cols-[minmax(0,2fr)_minmax(0,1fr)] items-stretch gap-2">
          <button
            type="button"
            onClick={() => {
              const nextExpanded = !expanded;
              setExpanded(nextExpanded);
              setRouteOpen(nextExpanded);
              setPassengerListOpen(nextExpanded);
            }}
            className="-translate-y-1.5 flex h-[42px] w-full items-center justify-between rounded-xl border border-border bg-secondary/30 px-3 py-2 text-left transition-colors active:bg-secondary"
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
                {expanded ? "Detay içeriği açık." : "Detay alanını aç."}
              </p>
            </div>
            {expanded ? <ChevronUp className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" /> : <ChevronDown className="h-3.5 w-3.5 flex-shrink-0 text-foreground/70" />}
          </button>
          <div className="-translate-y-1.5 flex h-[42px] min-w-0 items-center justify-between gap-2 rounded-xl bg-secondary/60 px-2.5 py-1.5">
            <div className="min-w-0 flex flex-1 flex-col justify-center leading-none">
              <span className="truncate text-[7px] font-bold uppercase tracking-tight text-muted-foreground">{contactLabel}</span>
              <p className="truncate pt-0.5 text-[9px] font-bold leading-none text-foreground">{formatPersonName(item.contact_name)}</p>
            </div>
            <div className="relative" data-contact-menu-root="true">
              <button
                type="button"
                onClick={() => setContactActionsOpen((prev) => !prev)}
                className="ml-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg active:opacity-90"
                style={{ backgroundColor: `${brandPrimary}26` }}
              >
                <Phone className="h-2 w-2" style={{ color: brandPrimary }} />
              </button>
              {contactActionsOpen && (
                <div className="absolute right-full top-1/2 z-10 mr-2 w-36 -translate-y-1/2 rounded-xl border border-border bg-card p-2 shadow-lg">
                  <a
                    href={`tel:${item.contact_phone.replace(/\s/g, "")}`}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold active:bg-secondary"
                    style={{ color: brandPrimary }}
                  >
                    <Phone className="h-4 w-4" />
                    Ara
                  </a>
                  <a
                    href={whatsappAllowed ? getWhatsappUrl(item.contact_phone) : undefined}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-disabled={!whatsappAllowed}
                    className={`mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold ${
                      whatsappAllowed
                        ? "text-success active:bg-secondary"
                        : "cursor-not-allowed bg-secondary/40 text-muted-foreground/60 opacity-55"
                    }`}
                  >
                    <WhatsappIcon className="h-4 w-4" />
                    WhatsApp
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>

        {isDetailAreaVisible && (
          <div className="mb-3 space-y-3">
            {/* Action stages */}
            {expanded && (
              <div className="space-y-1.5">
                <p className="text-[10px] font-bold uppercase text-muted-foreground">Durum Aksiyonları</p>
                {item.operation_stages.map((stage, i) => (
                  <button
                    key={i}
                    onClick={() => handleStageAction(i)}
                    disabled={isCompleted || i > completedStageCount || pendingStageIndex !== null}
                    className={`w-full rounded-xl px-3 py-3 text-left text-sm font-bold transition-colors ${
                      i < completedStageCount
                        ? "bg-success/10 text-success"
                        : pendingStageIndex === i
                          ? ""
                          : i === activeStageIndex && !isCompleted
                          ? ""
                          : "bg-secondary text-muted-foreground"
                    } ${isCompleted || i > completedStageCount || pendingStageIndex !== null ? "cursor-not-allowed opacity-70" : ""}`}
                    style={
                      i < completedStageCount
                        ? undefined
                        : pendingStageIndex === i
                          ? { backgroundColor: `${brandPrimary}26`, color: brandPrimary }
                          : i === activeStageIndex && !isCompleted
                            ? { backgroundColor: `${brandPrimary}1A`, color: brandPrimary }
                            : undefined
                    }
                  >
                    <span className="flex items-center justify-between gap-3">
                      <span className="flex items-center gap-2">
                        {pendingStageIndex === i && <LoaderCircle className="h-3.5 w-3.5 animate-spin" />}
                        <span>{stage}</span>
                      </span>
                      <span className="text-[10px] font-bold uppercase tracking-[0.14em]">
                        {i < completedStageCount || isCompleted
                          ? "Tamamlandı"
                          : pendingStageIndex === i
                            ? "Gönderiliyor"
                            : i === activeStageIndex
                              ? "Sıradaki"
                              : "Bekliyor"}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            )}

            {/* Route plan - collapsible */}
            {effectiveRouteStops.length > 0 && (
              <div
                className={`overflow-hidden rounded-xl border transition-all duration-200 ${
                  routeOpen ? "border-border bg-secondary/30" : ""
                }`}
                style={routePlanContainerStyle}
              >
                <button
                  onClick={() => setRouteOpen(!routeOpen)}
                  className={`flex w-full items-center justify-between px-3 py-3 transition-colors ${
                    routeOpen ? "" : "active:bg-white/5"
                  }`}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      {!routeOpen && <span className="h-2 w-2 flex-shrink-0 rounded-full bg-gold-500" />}
                      <span className="truncate text-xs font-bold text-foreground">Rota Planı</span>
                      <span className={`inline-flex flex-shrink-0 items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] ${routePlanBadgeTone}`}>
                        {routeOpen ? "Açık" : `${queueLabel} - ${operationTypeLabel}`}
                      </span>
                    </div>
                    <p className={`mt-1 text-[11px] ${routeOpen ? "text-muted-foreground" : "text-foreground/80"}`}>
                      {routeOpen
                        ? `${effectiveRouteStops.length} duraklık rota detayları aşağıda açık.`
                        : `${effectiveRouteStops.length} durak hazır. Rota detayını aç.`}
                    </p>
                  </div>
                  {routeOpen ? <ChevronUp className="h-4 w-4 flex-shrink-0 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 flex-shrink-0 text-foreground/70" />}
                </button>
                {routeOpen && (
                  <div className="border-t border-border px-3 pb-3 space-y-2">
                    {effectiveRouteStops.map((stop, idx) => (
                      <div key={idx} className="mt-2 rounded-xl bg-card p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p className="text-[10px] font-bold uppercase text-muted-foreground">{stop.label}</p>
                            <p className="text-sm font-bold text-foreground">{stop.main_location}</p>
                            {shouldShowStopSubtitle(stop) && (
                              <p className="text-xs text-muted-foreground">{stop.sub_location}</p>
                            )}
                          </div>
                          {canOpenMap(stop) && (
                            <a
                              href={getMapUrl(stop)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex h-7 shrink-0 items-center gap-1 rounded-lg px-2 text-[10px] font-bold active:opacity-90"
                              style={{ backgroundColor: `${brandPrimary}1A`, color: brandPrimary }}
                            >
                              <ExternalLink className="h-3 w-3" />
                              Haritada Aç
                            </a>
                          )}
                        </div>
                        <p className="mt-1 text-[10px] leading-4 text-muted-foreground/80">{stop.address_info}</p>

                        {/* Boarding / Alighting indicators */}
                        <div className="mt-2 flex gap-2">
                          {stop.boarding_passenger_tcs.length > 0 && (
                            <button
                              type="button"
                              onClick={() =>
                                setStopPassengerView((prev) => ({
                                  ...prev,
                                  [idx]: prev[idx] === "boarding" ? null : "boarding",
                                }))
                              }
                              className={`rounded-md px-2 py-1 text-[10px] font-bold ${
                                stopPassengerView[idx] === "boarding"
                                  ? "bg-boarding-accent text-white"
                                  : "bg-boarding text-boarding-accent"
                              }`}
                            >
                              Binecek: {stop.boarding_passenger_tcs.length}
                            </button>
                          )}
                          {stop.alighting_passenger_tcs.length > 0 && (
                            <button
                              type="button"
                              onClick={() =>
                                setStopPassengerView((prev) => ({
                                  ...prev,
                                  [idx]: prev[idx] === "alighting" ? null : "alighting",
                                }))
                              }
                              className={`rounded-md px-2 py-1 text-[10px] font-bold ${
                                stopPassengerView[idx] === "alighting"
                                  ? "bg-alighting-accent text-white"
                                  : "bg-alighting text-alighting-accent"
                              }`}
                            >
                              İnecek: {stop.alighting_passenger_tcs.length}
                            </button>
                          )}
                        </div>

                        {stopPassengerView[idx] && (
                          <div className="mt-3 rounded-xl border border-border bg-secondary/20 p-3">
                            <p className="mb-2 text-[10px] font-bold uppercase text-muted-foreground">
                              {stopPassengerView[idx] === "boarding" ? "Bu durakta binecekler" : "Bu durakta inecekler"}
                            </p>
                            <div className="space-y-2">
                              {getPassengersByTcList(
                                item,
                                stopPassengerView[idx] === "boarding"
                                  ? stop.boarding_passenger_tcs
                                  : stop.alighting_passenger_tcs,
                              ).map((passenger) => {
                                const isArrived = arrivedPassengerTcs.has(passenger.tc);
                                const isChecked = checkedPassengers.has(passenger.tc) || isArrived;

                                return (
                                  <div
                                    key={`${idx}-${passenger.tc}`}
                                    className={`flex items-center justify-between gap-3 rounded-lg px-3 py-2 ${
                                      isArrived ? "bg-success/10" : "bg-card"
                                    }`}
                                  >
                                    <div className="min-w-0">
                                      <div className="flex items-center gap-2">
                                        <p className="truncate text-sm font-semibold text-foreground">{formatPersonName(passenger.full_name)}</p>
                                        {isArrived && (
                                          <span className="rounded-full bg-success/15 px-2 py-0.5 text-[10px] font-bold text-success">
                                            Geldi
                                          </span>
                                        )}
                                      </div>
                                      <p className="text-[10px] text-muted-foreground">
                                        {passenger.tc} • {passenger.title}
                                      </p>
                                      {pendingPassengerSync[passenger.tc] && (
                                        <p className="mt-0.5 flex items-center gap-1 text-[10px] font-semibold text-azure-500">
                                          <LoaderCircle className="h-3 w-3 animate-spin" />
                                          Kaydediliyor...
                                        </p>
                                      )}
                                    </div>
                                  <div className="flex items-center gap-3">
                                    {passengerPhoneVisible ? (
                                      <div className="relative" data-contact-menu-root="true">
                                        <button
                                          type="button"
                                          onClick={() => togglePassengerContactActions(passenger.tc)}
                                          className="text-xs font-semibold"
                                          style={{ color: brandPrimary }}
                                        >
                                          {passenger.phone}
                                        </button>
                                        {passengerContactActions[passenger.tc] && (
                                          <div className="absolute right-full top-1/2 z-10 mr-2 w-36 -translate-y-1/2 rounded-xl border border-border bg-card p-2 shadow-lg">
                                            <a
                                              href={`tel:${passenger.phone.replace(/\s/g, "")}`}
                                              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold active:bg-secondary"
                                              style={{ color: brandPrimary }}
                                            >
                                              <Phone className="h-4 w-4" />
                                              Ara
                                            </a>
                                            <a
                                              href={getWhatsappUrl(passenger.phone)}
                                              target="_blank"
                                              rel="noopener noreferrer"
                                              className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-success active:bg-secondary"
                                            >
                                              <WhatsappIcon className="h-4 w-4" />
                                              WhatsApp
                                            </a>
                                          </div>
                                        )}
                                      </div>
                                    ) : (
                                      <span className="text-xs font-semibold text-muted-foreground">Gizli</span>
                                    )}
                                    <div className="flex w-6 justify-center">
                                      <Checkbox
                                        checked={isChecked}
                                        onCheckedChange={() => togglePassenger(passenger.tc)}
                                      />
                                    </div>
                                  </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Passenger list - table style */}
            {(expanded || passengerListOpen) && (
              <div>
                <p className="text-[10px] font-bold uppercase text-muted-foreground mb-2">Yolcu Listesi</p>
                <div className="rounded-xl border border-border overflow-hidden">
                  {/* Header */}
                  <div className="grid grid-cols-[1fr_auto_auto] gap-2 bg-secondary/60 px-3 py-2 text-[10px] font-bold uppercase text-muted-foreground">
                    <span>Ad Soyad</span>
                    <span>Telefon</span>
                    <span className="flex w-6 items-center justify-center">
                      <Check className="h-3.5 w-3.5 text-success" />
                    </span>
                  </div>
                  {effectivePassengerList.map((p, i) => {
                    const isArrived = arrivedPassengerTcs.has(p.tc);
                    const isChecked = checkedPassengers.has(p.tc) || isArrived;
                    return (
                      <div
                        key={p.tc}
                        className={`grid grid-cols-[1fr_auto_auto] gap-2 items-center px-3 py-2.5 border-t border-border ${
                          isChecked ? "bg-success/8" : i % 2 === 1 ? "bg-secondary/20" : "bg-card"
                        }`}
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="truncate text-sm font-semibold text-foreground">{formatPersonName(p.full_name)}</p>
                            {isArrived && (
                              <span className="rounded-full bg-success/15 px-2 py-0.5 text-[10px] font-bold text-success">
                                Geldi
                              </span>
                            )}
                          </div>
                          <p className="text-[10px] text-muted-foreground">
                            {p.tc} • {p.title}
                          </p>
                          {pendingPassengerSync[p.tc] && (
                            <p className="mt-0.5 flex items-center gap-1 text-[10px] font-semibold text-azure-500">
                              <LoaderCircle className="h-3 w-3 animate-spin" />
                              Kaydediliyor...
                            </p>
                          )}
                        </div>
                        {passengerPhoneVisible ? (
                          <div className="relative" data-contact-menu-root="true">
                            <button
                              type="button"
                              onClick={() => togglePassengerContactActions(p.tc)}
                              className="text-xs font-semibold"
                              style={{ color: brandPrimary }}
                            >
                              {p.phone}
                            </button>
                            {passengerContactActions[p.tc] && (
                              <div className="absolute right-full top-1/2 z-10 mr-2 w-36 -translate-y-1/2 rounded-xl border border-border bg-card p-2 shadow-lg">
                                <a
                                  href={`tel:${p.phone.replace(/\s/g, "")}`}
                                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold active:bg-secondary"
                                  style={{ color: brandPrimary }}
                                >
                                  <Phone className="h-4 w-4" />
                                  Ara
                                </a>
                                <a
                                  href={getWhatsappUrl(p.phone)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-success active:bg-secondary"
                                >
                                  <WhatsappIcon className="h-4 w-4" />
                                  WhatsApp
                                </a>
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs font-semibold text-muted-foreground">Gizli</span>
                        )}
                        <div className="w-6 flex justify-center">
                          <Checkbox checked={isChecked} onCheckedChange={() => togglePassenger(p.tc)} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
        {/* Route summary */}
        <div className="mb-3 grid grid-cols-[1fr_auto_1fr] items-stretch gap-2 rounded-xl bg-secondary/30 px-3 py-2.5">
          <div className="min-w-0 text-left">
            <button
              type="button"
              onClick={() => window.open(getMapUrl(effectiveRouteStops[0]), "_blank", "noopener,noreferrer")}
              className="hidden"
            >
              Başlangıç
            </button>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <button
                type="button"
                onClick={() => window.open(getMapUrl(effectiveRouteStops[0]), "_blank", "noopener,noreferrer")}
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full transition-colors active:bg-secondary/60"
                aria-label="Baslangic konumunu ac"
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
            onClick={() => {
              setExpanded(false);
              setPassengerListOpen(false);
              setRouteOpen((prev) => !prev);
            }}
            className="flex min-w-[52px] items-center justify-center self-stretch rounded-lg px-1 py-2 text-[11px] font-semibold text-muted-foreground transition-colors active:bg-secondary/60"
          >
            {routeSummary.middle ? (
              <div className="flex items-center gap-1.5">
                <span className="text-sm leading-none text-muted-foreground/50">→</span>
                <span className="rounded-full bg-card px-2 py-1">{routeSummary.middle}</span>
                <span className="text-sm leading-none text-muted-foreground/50">→</span>
              </div>
            ) : (
              <span className="text-base leading-none text-muted-foreground/50">⟶</span>
            )}
          </button>
          <div className="min-w-0 text-right">
            <button
              type="button"
              onClick={() =>
                window.open(
                  getMapUrl(effectiveRouteStops[effectiveRouteStops.length - 1]),
                  "_blank",
                  "noopener,noreferrer",
                )
              }
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
                onClick={() =>
                  window.open(
                    getMapUrl(effectiveRouteStops[effectiveRouteStops.length - 1]),
                    "_blank",
                    "noopener,noreferrer",
                  )
                }
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full transition-colors active:bg-secondary/60"
                aria-label="Bitis konumunu ac"
              >
                <MapPin className="h-3 w-3 text-red-500" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function OperationsScreen({ role, onPendingSyncChange }: OperationsScreenProps) {
  const appConfig = getAppConfig(role);
  const brandPrimary = appConfig.branding.primary_color || "#58C7F2";
  const brandSecondary = appConfig.branding.base_color || "#091028";
  const { stageIndexByOperation } = useAppState();
  const operations = [...getOperations(role)].sort((a, b) => a.start_time.localeCompare(b.start_time));
  const [cardPendingCounts, setCardPendingCounts] = useState<Record<number, number>>({});

  useEffect(() => {
    const totalPending = Object.values(cardPendingCounts).reduce((sum, count) => sum + count, 0);
    onPendingSyncChange?.(totalPending);
  }, [cardPendingCounts, onPendingSyncChange]);

  const sortedOperations = [...operations].sort((a, b) => {
    const aCompleted = isOperationCompleted(a, stageIndexByOperation[a.id] ?? 0);
    const bCompleted = isOperationCompleted(b, stageIndexByOperation[b.id] ?? 0);

    if (aCompleted !== bCompleted) return aCompleted ? 1 : -1;
    return a.start_time.localeCompare(b.start_time);
  });

  const activeOperations = sortedOperations.filter(
    (item) => !isOperationCompleted(item, stageIndexByOperation[item.id] ?? 0),
  );
  const completedOperations = sortedOperations.filter(
    (item) => isOperationCompleted(item, stageIndexByOperation[item.id] ?? 0),
  );
  const sortedPrimary = activeOperations[0] || null;
  const sortedSecondary = activeOperations.slice(1);

  return (
    <div className="flex flex-col gap-3 px-4 pb-6">
      {sortedPrimary && (
        <div>
          <p className="mb-2 text-[10px] font-bold uppercase tracking-wider" style={{ color: brandPrimary }}>Aktif İşler</p>
          <OperationCard
            item={sortedPrimary}
            role={role}
            featured
            onPendingSyncChange={(count) =>
              setCardPendingCounts((prev) => ({ ...prev, [sortedPrimary.id]: count }))
            }
          />
        </div>
      )}
      {sortedSecondary.length > 0 && (
        <div>
          <p className="mb-2 mt-2 text-[10px] font-bold uppercase tracking-wider" style={{ color: brandSecondary }}>
            Sıradaki Görevler
          </p>
          <div className="space-y-2.5">
            {sortedSecondary.map(item => (
              <OperationCard
                key={item.id}
                item={item}
                role={role}
                onPendingSyncChange={(count) =>
                  setCardPendingCounts((prev) => ({ ...prev, [item.id]: count }))
                }
              />
            ))}
          </div>
        </div>
      )}
      {completedOperations.length > 0 && (
        <div>
          <p className="mb-2 mt-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            Tamamlanan Görevler
          </p>
          <div className="space-y-2.5">
            {completedOperations.map(item => (
              <OperationCard
                key={item.id}
                item={item}
                role={role}
                onPendingSyncChange={(count) =>
                  setCardPendingCounts((prev) => ({ ...prev, [item.id]: count }))
                }
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}



