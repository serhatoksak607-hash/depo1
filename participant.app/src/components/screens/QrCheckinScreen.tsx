import { useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, LoaderCircle, QrCode, ScanLine } from "lucide-react";
import type { PassengerInfo, Role } from "@/data/types";
import { formatPersonName } from "@/lib/utils";
import { getCoreBootstrap, submitQrArrivalEvent } from "@/services/core";
import { useAppState } from "@/state/app-state";
import { toast } from "@/components/ui/sonner";

type ScanState = "idle" | "scanning" | "processing" | "success";

interface BarcodeDetectorLike {
  detect: (source: ImageBitmapSource) => Promise<Array<{ rawValue?: string }>>;
}

declare global {
  interface Window {
    BarcodeDetector?: new (options?: { formats?: string[] }) => BarcodeDetectorLike;
  }
}

interface QrCheckinScreenProps {
  synced?: boolean;
  role: Role;
}

export function QrCheckinScreen({ synced = false, role }: QrCheckinScreenProps) {
  const [scanState, setScanState] = useState<ScanState>(synced ? "scanning" : "idle");
  const [selectedPassengerTc, setSelectedPassengerTc] = useState<string | null>(null);
  const [lastProcessedPassengerTc, setLastProcessedPassengerTc] = useState<string | null>(null);
  const [cameraSupported, setCameraSupported] = useState(false);
  const [manualCode, setManualCode] = useState("");
  const [scanHint, setScanHint] = useState<string>("QR kodunu kameraya tutun.");
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const detectorRef = useRef<BarcodeDetectorLike | null>(null);
  const frameTimerRef = useRef<number | null>(null);
  const { markQrArrival, passengerMarksByOperation, qrArrivalRecords } = useAppState();
  const bootstrap = useMemo(() => getCoreBootstrap(role), [role]);
  const { appConfig, operations } = bootstrap;
  const brandPrimary = appConfig.branding.primary_color || "#58C7F2";
  const brandBase = appConfig.branding.base_color || "#091028";
  const activeOperation = operations[0];
  const activeTransfer = activeOperation
    ? {
        passenger: formatPersonName(activeOperation.passenger_name),
        flight: activeOperation.flight_code,
        project: activeOperation.project_name || "Genel operasyon",
        pickup: activeOperation.start_location,
      }
    : {
        passenger: "Aktif kayıt yok",
        flight: "Bilgi bekleniyor",
        project: "Genel operasyon",
        pickup: "Konum bekleniyor",
      };
  const normalizeSearchText = (value: string) =>
    value
      .toLocaleLowerCase("tr-TR")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  // Ideal kaynak Core tarafında hazır bir kullanıcı metni dönmek olur; burada mevcut policy alanlarından türetiliyor.
  const validationNote = activeOperation
    ? activeOperation.resolved_policies.allow_project_cross_vehicle
      ? activeOperation.resolved_policies.person_vehicle_restricted
        ? "Bu operasyonda kişi için proje ve araç eşleşmesi zorunludur."
        : "Bu operasyonda kişi için proje eşleşmesi yeterlidir."
      : activeOperation.resolved_policies.person_vehicle_restricted
        ? "Bu operasyonda kişi için araç eşleşmesi zorunludur."
        : "Bu operasyonda aktif transfer uygunluğu yeterlidir."
    : "Bu operasyonda doğrulama kuralları hazırlanıyor.";
  const sameProjectOperations =
    activeOperation &&
    activeOperation.resolved_policies.allow_project_cross_vehicle &&
    !activeOperation.resolved_policies.person_vehicle_restricted
      ? operations.filter((operation) => operation.project_name === activeOperation.project_name)
      : activeOperation
        ? [activeOperation]
        : [];
  const eligiblePassengers = useMemo(() => {
    if (!activeOperation) return [];

    if (
      activeOperation.resolved_policies.allow_project_cross_vehicle &&
      !activeOperation.resolved_policies.person_vehicle_restricted
    ) {
      const sameProjectPassengers = operations
        .filter((operation) => operation.project_name === activeOperation.project_name)
        .flatMap((operation) => operation.passenger_list);

      return sameProjectPassengers.filter(
        (passenger, index, list) => list.findIndex((item) => item.tc === passenger.tc) === index,
      );
    }

    return activeOperation.passenger_list;
  }, [activeOperation, operations]);
  const projectWideProcessedPassengerTcs = useMemo(() => {
    const next = new Set<string>();

    sameProjectOperations.forEach((operation) => {
      (passengerMarksByOperation[operation.id] ?? []).forEach((tc) => next.add(tc));
      qrArrivalRecords
        .filter((record) => record.operationId === operation.id && record.role === role)
        .forEach((record) => next.add(record.passengerTc));
    });

    return next;
  }, [passengerMarksByOperation, qrArrivalRecords, role, sameProjectOperations]);

  const selectedPassenger =
    eligiblePassengers.find((passenger) => passenger.tc === selectedPassengerTc) ?? null;
  const passengerSearchQuery = normalizeSearchText(manualCode);
  const filteredEligiblePassengers = useMemo(() => {
    const visiblePassengers = eligiblePassengers.filter(
      (passenger) => !projectWideProcessedPassengerTcs.has(passenger.tc),
    );

    if (!passengerSearchQuery) return visiblePassengers;

    return visiblePassengers.filter((passenger) => {
      const formattedName = formatPersonName(passenger.full_name);
      const normalizedName = normalizeSearchText(formattedName);
      const normalizedTitle = normalizeSearchText(passenger.title);
      const normalizedQr = normalizeSearchText(passenger.qr_code ?? "");

      return (
        passenger.tc.includes(manualCode.trim()) ||
        normalizedQr.includes(passengerSearchQuery) ||
        normalizedName.includes(passengerSearchQuery) ||
        normalizedTitle.includes(passengerSearchQuery)
      );
    });
  }, [eligiblePassengers, manualCode, passengerSearchQuery, projectWideProcessedPassengerTcs]);
  const arrivedPassengerTcs = useMemo(
    () =>
      new Set(
        [...projectWideProcessedPassengerTcs].filter((tc) =>
          eligiblePassengers.some((passenger) => passenger.tc === tc),
        ),
      ),
    [eligiblePassengers, projectWideProcessedPassengerTcs],
  );
  const manuallyCheckedPassengerTcs = useMemo(
    () =>
      new Set(
        (activeOperation ? passengerMarksByOperation[activeOperation.id] : [])?.filter((tc) =>
          eligiblePassengers.some((passenger) => passenger.tc === tc),
        ) ?? [],
      ),
    [activeOperation, eligiblePassengers, passengerMarksByOperation],
  );
  const processedPassengerTcs = useMemo(() => {
    const next = new Set(arrivedPassengerTcs);
    manuallyCheckedPassengerTcs.forEach((tc) => next.add(tc));
    return next;
  }, [arrivedPassengerTcs, manuallyCheckedPassengerTcs]);

  const warnAlreadyProcessed = (tc: string) => {
    const passenger = eligiblePassengers.find((item) => item.tc === tc);
    const passengerLabel = passenger ? formatPersonName(passenger.full_name) : "Bu kişi";
    setScanHint(`${passengerLabel} için geliş kaydı zaten alınmış.`);
    toast.info("Kişi zaten işlendi", {
      description: `${passengerLabel} için tekrar geliş kaydı alınmadı.`,
    });
  };

  const completePassengerArrival = (tc: string) => {
    if (processedPassengerTcs.has(tc)) {
      warnAlreadyProcessed(tc);
      return;
    }

    setSelectedPassengerTc(tc);
    setScanState("processing");
    window.setTimeout(() => {
      if (activeOperation) {
        const arrivalRecord = {
          operationId: activeOperation.id,
          passengerTc: tc,
          role,
          recordedAt: Date.now(),
        };

        markQrArrival(arrivalRecord);
        void submitQrArrivalEvent({
          operationId: activeOperation.id,
          passengerTc: tc,
          actorRole: role,
          vehicleContextId: activeOperation.vehicle_id ?? null,
          projectContextId: activeOperation.project_id ?? null,
          recordedAt: new Date(arrivalRecord.recordedAt).toISOString(),
        }).catch(() => {
          toast.error("QR kaydı Core'a iletilemedi", {
            description: "Bağlantı geldiğinde tekrar gönderilecek şekilde ele alınmalı.",
          });
        });
      }
      setLastProcessedPassengerTc(tc);
      setScanHint(`${formatPersonName(eligiblePassengers.find((item) => item.tc === tc)?.full_name || "")} geldi olarak işlendi.`);
      window.setTimeout(() => {
        setScanState("scanning");
      }, 1200);
    }, 900);
  };

  useEffect(() => {
    setCameraSupported(
      typeof navigator !== "undefined" &&
        typeof navigator.mediaDevices?.getUserMedia === "function" &&
        typeof window !== "undefined" &&
        typeof window.BarcodeDetector === "function",
    );
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined" && typeof window.BarcodeDetector === "function") {
      detectorRef.current = new window.BarcodeDetector({ formats: ["qr_code"] });
    }
  }, []);

  useEffect(() => {
    if (scanState !== "scanning" || !cameraSupported || !videoRef.current) return;

    let cancelled = false;

    const stopCamera = () => {
      if (frameTimerRef.current) {
        window.clearTimeout(frameTimerRef.current);
        frameTimerRef.current = null;
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };

    const detectLoop = async () => {
      if (cancelled || !videoRef.current || !detectorRef.current) return;

      try {
        const results = await detectorRef.current.detect(videoRef.current);
        const rawValues = results
          .map((result) => result.rawValue?.trim())
          .filter((value): value is string => Boolean(value));

        if (rawValues.length > 0) {
          const matchedPassenger = rawValues.reduce<PassengerInfo | null>((foundPassenger, rawValue) => {
            if (foundPassenger) return foundPassenger;
            return (
              eligiblePassengers.find(
                (passenger) => passenger.qr_code === rawValue || passenger.tc === rawValue,
              ) ?? null
            );
          }, null);

          if (matchedPassenger) {
            stopCamera();
            if (processedPassengerTcs.has(matchedPassenger.tc)) {
              warnAlreadyProcessed(matchedPassenger.tc);
              return;
            }
            setSelectedPassengerTc(matchedPassenger.tc);
            setScanHint(`${formatPersonName(matchedPassenger.full_name)} için QR bulundu.`);
            completePassengerArrival(matchedPassenger.tc);
            return;
          }

          setScanHint("Kamera açık, uygun QR okunmayı bekliyor.");
        }
      } catch {
        setScanHint("Kamera açık, QR okunmayı bekliyor.");
      }

      frameTimerRef.current = window.setTimeout(detectLoop, 700);
    };

    navigator.mediaDevices
      .getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
        },
        audio: false,
      })
      .then((stream) => {
        if (cancelled || !videoRef.current) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = stream;
        videoRef.current.srcObject = stream;
        void videoRef.current.play();
        frameTimerRef.current = window.setTimeout(detectLoop, 800);
      })
      .catch(() => {
        setScanHint("Kamera açılamadı. Aşağıdaki uygun kişi listesini veya manuel kod girişini kullanın.");
      });

    return () => {
      cancelled = true;
      stopCamera();
    };
  }, [activeOperation, cameraSupported, eligiblePassengers, markQrArrival, processedPassengerTcs, role, scanState]);

  const handleStartScan = () => {
    if (scanState === "processing") return;
    setSelectedPassengerTc(null);
    setManualCode("");
    setScanHint("QR kodunu kameraya tutun.");
    setScanState("scanning");
  };

  const handlePassengerScan = (tc: string) => {
    completePassengerArrival(tc);
  };

  const handleManualCodeSubmit = () => {
    const normalizedCode = manualCode.trim();
    if (!normalizedCode) {
      setScanHint("Lütfen QR, T.C. veya isim girin.");
      return;
    }

    const matchedPassenger = eligiblePassengers.find((passenger) => {
      const formattedName = formatPersonName(passenger.full_name);

      return (
        passenger.qr_code === normalizedCode ||
        passenger.tc === normalizedCode ||
        normalizeSearchText(formattedName) === passengerSearchQuery
      );
    });

    if (matchedPassenger) {
      setScanHint(`${formatPersonName(matchedPassenger.full_name)} için kod doğrulandı.`);
      completePassengerArrival(matchedPassenger.tc);
      return;
    }

    if (filteredEligiblePassengers.length === 1) {
      const singleMatch = filteredEligiblePassengers[0];
      setScanHint(`${formatPersonName(singleMatch.full_name)} için kayıt hazır.`);
      completePassengerArrival(singleMatch.tc);
      return;
    }

    if (filteredEligiblePassengers.length > 1) {
      setScanHint("Birden fazla uygun kişi bulundu. Listeden seçim yapın.");
      return;
    }

    const partialMatch = eligiblePassengers.find(
      (passenger) => normalizeSearchText(formatPersonName(passenger.full_name)).includes(passengerSearchQuery),
    );
    setScanHint(partialMatch ? "Birden fazla eşleşme bulunabilir. Listeden seçim yapın." : "Girilen bilgi bu iş için uygun görünmüyor.");
  };

  const eligiblePassengersSection = (
    <div className="rounded-2xl bg-secondary/60 px-4 py-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
        Bu iş için uygun kişiler
      </p>
      <div className="mt-3 flex flex-col gap-2">
        {filteredEligiblePassengers.map((passenger) => {
          const isProcessed =
            arrivedPassengerTcs.has(passenger.tc) || manuallyCheckedPassengerTcs.has(passenger.tc);

          return (
          <button
            key={passenger.tc}
            onClick={() => handlePassengerScan(passenger.tc)}
            className="flex items-center justify-between rounded-xl border border-border bg-card px-3 py-3 text-left transition-colors active:bg-secondary"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="truncate text-sm font-bold text-foreground">{formatPersonName(passenger.full_name)}</p>
                {isProcessed && (
                  <span className="rounded-full bg-success/15 px-2 py-0.5 text-[10px] font-bold text-success">
                    Geldi
                  </span>
                )}
              </div>
              <p className="truncate text-[11px] text-muted-foreground">
                {passenger.tc} • {passenger.title}
              </p>
            </div>
            <span
              className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${
                isProcessed
                  ? "bg-success/15 text-success"
                  : "bg-azure-500/10 text-azure-500"
              }`}
            >
              {isProcessed ? "İşlendi" : "Uygun"}
            </span>
          </button>
          );
        })}
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-3 px-4 pb-6">
      <div className="rounded-2xl border border-border bg-card p-5">
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(148px,176px)] items-start gap-3 md:grid-cols-[minmax(0,1fr)_minmax(220px,300px)]">
          <div className="flex min-w-0 items-center gap-3">
            <div
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl md:h-12 md:w-12"
              style={{ backgroundColor: `${brandPrimary}1A` }}
            >
              <QrCode className="h-5 w-5 md:h-6 md:w-6" style={{ color: brandPrimary }} />
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-base font-bold text-foreground md:text-lg">QR Okut</h2>
              <p className="line-clamp-1 text-[11px] text-muted-foreground md:text-xs">Seçilen transfer</p>
            </div>
          </div>

          <div className="justify-self-end rounded-2xl bg-secondary/70 px-3 py-2.5 md:min-w-[220px] md:max-w-[300px] md:px-4 md:py-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">Aktif Transfer</p>
            <p className="mt-1 text-sm font-bold text-foreground">{activeTransfer.passenger}</p>
            <p className="text-xs text-muted-foreground">
              {activeTransfer.flight} • {activeTransfer.project}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">{activeTransfer.pickup}</p>
          </div>
        </div>
        <p className="mt-4 text-sm leading-6 text-muted-foreground">
          Katılımcı QR kodunu gösterir. Sistem uygunluğu Core'dan gelen doğrulama kurallarına göre kontrol eder.
        </p>
        {scanState === "scanning" && !cameraSupported && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
            Bu cihazda doğrudan QR algılama desteklenmiyor. Manuel kod girişiyle devam edin.
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-border bg-card p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-success/10">
            <ScanLine className="h-6 w-6 text-success" />
          </div>
          <div>
            <h3 className="text-base font-bold text-foreground">Biniş Kaydı</h3>
            <p className="text-xs text-muted-foreground">{validationNote}</p>
          </div>
        </div>

        {scanState === "scanning" && (
          <div className="mt-4 space-y-3">
            {!cameraSupported && eligiblePassengersSection}

            {lastProcessedPassengerTc && (
              <div className="rounded-2xl border border-success/30 bg-success/10 px-4 py-3">
                <div className="flex items-center gap-2 text-sm font-bold text-success">
                  <CheckCircle2 className="h-4 w-4" />
                  Son işlenen kişi
                </div>
                <p className="mt-1 text-sm font-semibold text-foreground">
                  {formatPersonName(
                    eligiblePassengers.find((passenger) => passenger.tc === lastProcessedPassengerTc)?.full_name ||
                      activeTransfer.passenger,
                  )}{" "}
                  geldi olarak işlendi.
                </p>
              </div>
            )}

            {cameraSupported && (
              <div
                className="rounded-2xl border px-4 py-5 text-primary-foreground"
                style={{ borderColor: `${brandPrimary}33`, backgroundColor: `${brandBase}F2` }}
              >
                <p className="text-[10px] font-bold uppercase tracking-[0.16em]" style={{ color: brandPrimary }}>
                  Kamera Önizleme
                </p>
                <div
                  className="mt-3 overflow-hidden rounded-2xl border bg-black/30"
                  style={{ borderColor: `${brandPrimary}33` }}
                >
                  <video ref={videoRef} className="aspect-[3/4] w-full object-cover" muted playsInline autoPlay />
                </div>
                <p className="mt-3 text-sm font-semibold">{scanHint}</p>
                <p className="mt-1 text-xs" style={{ color: `${brandPrimary}CC` }}>
                  Test QR içeriği örneği: `PAX-12345678901`
                </p>
              </div>
            )}

            <div className="rounded-2xl bg-secondary/60 px-4 py-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
                Manuel Kod Girişi
              </p>
              <div className="mt-3 flex gap-2">
                <input
                  value={manualCode}
                  onChange={(event) => setManualCode(event.target.value)}
                  placeholder="QR, T.C. veya isim"
                  className="flex-1 rounded-xl border border-border bg-card px-3 py-3 text-sm text-foreground outline-none"
                />
                <button
                  type="button"
                  onClick={handleManualCodeSubmit}
                  className="rounded-xl bg-azure-500 px-4 py-3 text-sm font-bold text-white active:bg-azure-500/90"
                >
                  Doğrula
                </button>
              </div>
              <p className="mt-2 text-[11px] text-muted-foreground">
                Kamera okumazsa QR, T.C. veya isim ile arama yapın.
              </p>
            </div>

          </div>
        )}

        {scanState === "processing" && (
          <div
            className="mt-4 flex items-center gap-2 rounded-2xl border px-4 py-3 text-sm font-bold"
            style={{ borderColor: `${brandPrimary}4D`, backgroundColor: `${brandPrimary}1A`, color: brandPrimary }}
          >
            <LoaderCircle className="h-4 w-4 animate-spin" />
            QR doğrulanıyor, kayıt hazırlanıyor...
          </div>
        )}

      </div>
      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={handleStartScan}
          disabled={scanState === "processing"}
          className="rounded-2xl px-4 py-4 text-sm font-bold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-70"
          style={{ backgroundColor: brandBase }}
        >
          {scanState === "processing"
            ? "Doğrulanıyor..."
            : scanState === "scanning"
              ? "Kamera Açık"
            : "QR Okutmayı Başlat"}
        </button>
        <button
          onClick={() => {
            setSelectedPassengerTc(null);
            setLastProcessedPassengerTc(null);
            setScanState("idle");
          }}
          className="rounded-2xl border border-border bg-card px-4 py-4 text-sm font-bold text-foreground active:bg-secondary"
        >
          Sıfırla
        </button>
      </div>

      {cameraSupported && eligiblePassengersSection}
    </div>
  );
}




