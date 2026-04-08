import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowDownLeft,
  ArrowUpRight,
  ChevronDown,
  ChevronUp,
  Plus,
  Receipt,
  WalletCards,
} from "lucide-react";
import { getExpenses, getStatusColor, getStatusLabel } from "@/services/core";
import { useAppState } from "@/state/app-state";

const flowOptions: Array<["all" | "alacak" | "verecek", string]> = [
  ["all", "Tümü"],
  ["alacak", "Masraflar"],
  ["verecek", "Ödemeler"],
];

const settlementOptions: Array<["all" | "bekliyor" | "isleniyor" | "tamamlandi", string]> = [
  ["all", "Tümü"],
  ["bekliyor", "Bekliyor"],
  ["isleniyor", "İşleniyor"],
  ["tamamlandi", "Tamamlandı"],
];

function getExpenseTypeLabel(type: string) {
  const map: Record<string, string> = {
    transfer: "Transfer",
    project: "Proje",
    general: "Genel Gider",
  };
  return map[type] || type;
}

function getSettlementLabel(status?: string | null) {
  if (status === "tamamlandi") return "Tamamlandı";
  if (status === "isleniyor") return "İşleniyor";
  return "Bekliyor";
}

function getSettlementTone(status?: string | null) {
  if (status === "tamamlandi") return "bg-success/10 text-success";
  if (status === "isleniyor") return "bg-azure-500/10 text-azure-500";
  return "bg-gold-500/10 text-gold-500";
}

function formatMoneyCompact(value: number) {
  const hasDecimals = Math.abs(value % 1) > 0.001;
  const formatted = new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: hasDecimals ? 2 : 0,
    maximumFractionDigits: 2,
  }).format(value);
  return hasDecimals ? `${formatted} TL` : `${formatted},- TL`;
}

export function ExpensesScreen() {
  const expenses = getExpenses();
  const { selectedOperationContext } = useAppState();
  const [flowFilter, setFlowFilter] = useState<"all" | "alacak" | "verecek">("all");
  const [settlementFilter, setSettlementFilter] = useState<"all" | "bekliyor" | "isleniyor" | "tamamlandi">("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const filtered = useMemo(
    () =>
      expenses.filter((expense) => {
        const scopedOperationLabel = selectedOperationContext?.operationLabel?.trim() || "";
        const scopedProjectName = selectedOperationContext?.projectName?.trim() || "";
        const scopedJobTime = selectedOperationContext?.jobTime?.trim() || "";
        const contextMatch =
          !selectedOperationContext ||
          expense.operation_label === scopedOperationLabel ||
          expense.project_name === scopedProjectName ||
          (Boolean(scopedJobTime) && typeof expense.operation_label === "string" && expense.operation_label.startsWith(`${scopedJobTime} `));
        const flowMatch = flowFilter === "all" || expense.flow === flowFilter;
        const settlementMatch = settlementFilter === "all" || expense.settlement_status === settlementFilter;
        const startMatch = !startDate || expense.date >= startDate;
        const endMatch = !endDate || expense.date <= endDate;
        return contextMatch && flowMatch && settlementMatch && startMatch && endMatch;
      }),
    [endDate, expenses, flowFilter, selectedOperationContext, settlementFilter, startDate],
  );

  const summary = useMemo(() => {
    const masraflar = expenses.filter((e) => e.flow === "alacak").reduce((t, e) => t + e.amount, 0);
    const odemeler = expenses.filter((e) => e.flow === "verecek").reduce((t, e) => t + e.amount, 0);
    return { masraflar, odemeler, bakiye: masraflar - odemeler };
  }, [expenses]);

  const filteredSummary = useMemo(() => {
    const masraflar = filtered.filter((e) => e.flow === "alacak").reduce((t, e) => t + e.amount, 0);
    const odemeler = filtered.filter((e) => e.flow === "verecek").reduce((t, e) => t + e.amount, 0);
    const bekleyen = filtered.filter((e) => e.settlement_status === "bekliyor").length;
    return { masraflar, odemeler, bakiye: masraflar - odemeler, bekleyen };
  }, [filtered]);

  const balanceTitle =
    summary.bakiye > 0 ? "KALAN MASRAF" : summary.bakiye < 0 ? "AVANS BAKİYESİ" : "NET BAKİYE";
  const balanceTone =
    summary.bakiye > 0 ? "text-azure-500" : summary.bakiye < 0 ? "text-danger" : "text-muted-foreground";

  const hasFilters = flowFilter !== "all" || settlementFilter !== "all" || startDate || endDate;
  const activeSummary = hasFilters ? filteredSummary : summary;
  const activeBalanceTitle =
    activeSummary.bakiye > 0 ? "KALAN MASRAF" : activeSummary.bakiye < 0 ? "AVANS BAKİYESİ" : "NET BAKİYE";
  const activeBalanceTone =
    activeSummary.bakiye > 0 ? "text-azure-500" : activeSummary.bakiye < 0 ? "text-danger" : "text-muted-foreground";

  return (
    <div className="flex flex-col gap-4 px-4 pb-6">
      <button className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-azure-500 text-sm font-bold text-white active:bg-azure-500/90">
        <Plus className="h-5 w-5" />
        Yeni Masraf Kaydı
      </button>

      {selectedOperationContext?.operationLabel && (
        <div className="flex items-center gap-3 rounded-xl border border-gold-500/20 bg-gold-500/5 px-4 py-3">
          <AlertTriangle className="h-4 w-4 flex-shrink-0 text-gold-500" />
          <div className="min-w-0">
            <p className="text-xs font-semibold text-foreground">{selectedOperationContext.operationLabel}</p>
            {selectedOperationContext.projectName && (
              <p className="text-[11px] text-muted-foreground">{selectedOperationContext.projectName}</p>
            )}
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-xl border border-border bg-card p-3.5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-foreground">MASRAFLAR</p>
          <p className="mt-2 text-right text-base font-bold text-success">{formatMoneyCompact(activeSummary.masraflar)}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-3.5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-foreground">ÖDEMELER</p>
          <p className="mt-2 text-right text-base font-bold text-danger">{formatMoneyCompact(activeSummary.odemeler)}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-3.5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-foreground">{activeBalanceTitle}</p>
          <p className={`mt-2 text-right text-base font-bold ${activeBalanceTone}`}>{formatMoneyCompact(activeSummary.bakiye)}</p>
        </div>
      </div>

      {hasFilters && (
        <div className="flex items-center justify-between rounded-lg bg-secondary/50 px-3.5 py-2.5 text-xs">
          <span className="text-muted-foreground">
            Filtreli: <span className="font-semibold text-success">{filteredSummary.masraflar}</span> masraf
            {" / "}
            <span className="font-semibold text-danger">{filteredSummary.odemeler}</span> ödeme
          </span>
          {filteredSummary.bekleyen > 0 && (
            <span className="rounded-md bg-gold-500/10 px-2 py-0.5 font-semibold text-gold-500">
              {filteredSummary.bekleyen} bekleyen
            </span>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <select
          value={flowFilter}
          onChange={(e) => setFlowFilter(e.target.value as "all" | "alacak" | "verecek")}
          className="rounded-lg border border-border bg-card px-3 py-2 text-xs font-semibold text-foreground outline-none"
        >
          {flowOptions.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={settlementFilter}
          onChange={(e) => setSettlementFilter(e.target.value as "all" | "bekliyor" | "isleniyor" | "tamamlandi")}
          className="rounded-lg border border-border bg-card px-3 py-2 text-xs font-semibold text-foreground outline-none"
        >
          {settlementOptions.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <button className="ml-auto rounded-lg bg-azure-500 px-3.5 py-2 text-xs font-semibold text-white active:bg-azure-500/90">
          Hesap Dökümü Al
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="rounded-lg border border-border bg-card px-3 py-2.5 text-sm text-foreground outline-none"
        />
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="rounded-lg border border-border bg-card px-3 py-2.5 text-sm text-foreground outline-none"
        />
      </div>

      <div className="space-y-2.5">
        {filtered.map((expense) => {
          const statusColor = getStatusColor(expense.status);
          const isMasraf = expense.flow === "alacak";
          const expanded = expandedId === expense.id;

          return (
            <div key={expense.id} className="overflow-hidden rounded-xl border border-border bg-card">
              <div className="p-4">
                <div className="flex items-start gap-3">
                  <div
                    className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl ${
                      isMasraf ? "bg-success/10" : "bg-danger/10"
                    }`}
                  >
                    {isMasraf ? (
                      <ArrowDownLeft className="h-5 w-5 text-success" />
                    ) : (
                      <ArrowUpRight className="h-5 w-5 text-danger" />
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-base font-bold text-foreground">
                          {formatMoneyCompact(expense.amount)}
                        </p>
                        <p className="mt-0.5 text-sm text-foreground">{expense.description}</p>
                      </div>
                      <span className={`flex-shrink-0 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${statusColor.bg} ${statusColor.text}`}>
                        {getStatusLabel(expense.status)}
                      </span>
                    </div>

                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <span className="text-[11px] text-muted-foreground">
                        {isMasraf ? "Masraf" : "Ödeme"} • {getExpenseTypeLabel(expense.expense_type)} • {expense.date}
                      </span>
                    </div>

                    {expense.counterparty_label && (
                      <p className="mt-1 text-[11px] text-muted-foreground">{expense.counterparty_label}</p>
                    )}

                    <div className="mt-2.5 flex flex-wrap items-center gap-2">
                      <span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${getSettlementTone(expense.settlement_status)}`}>
                        {getSettlementLabel(expense.settlement_status)}
                      </span>
                      {expense.receipt_file_name && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-gold-500/10 px-2 py-1 text-[10px] font-semibold text-gold-500">
                          <Receipt className="h-3 w-3" />
                          Fiş mevcut
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <button
                onClick={() => setExpandedId(expanded ? null : expense.id)}
                className="flex w-full items-center justify-center gap-1.5 border-t border-border py-2.5 text-xs font-semibold text-muted-foreground active:bg-secondary/30"
              >
                {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                {expanded ? "Detayı gizle" : "Fiş detayını gör"}
              </button>

              {expanded && (
                <div className="border-t border-border bg-secondary/20 p-3.5">
                  <div className="grid gap-2">
                    {[
                      ["Operasyon", expense.operation_label || "Genel kayıt"],
                      ["Cari Karşılık", expense.counterparty_label || "Tanımsız"],
                      ["Fiş Dosyası", expense.receipt_file_name || "Belge henüz eklenmedi"],
                      ["Fiş Detayı", expense.receipt_detail || "Fiş açıklaması girilmemiş."],
                    ].map(([label, value]) => (
                      <div key={label} className="rounded-lg bg-card px-3 py-2.5">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
                        <p className="mt-0.5 text-sm text-foreground">{value}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="rounded-xl border border-dashed border-border bg-card/50 px-6 py-10 text-center">
            <WalletCards className="mx-auto h-8 w-8 text-muted-foreground/40" />
            <p className="mt-3 text-sm font-medium text-muted-foreground">Filtrelere uygun finans kaydı bulunamadı</p>
          </div>
        )}
      </div>
    </div>
  );
}

