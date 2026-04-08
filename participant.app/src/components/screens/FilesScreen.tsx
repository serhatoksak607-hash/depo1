import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Calendar,
  Download,
  Eye,
  FileBadge,
  FileText,
  Filter,
  Mail,
  Receipt,
  ScanText,
  Search,
  Share2,
  Smartphone,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { toast } from "@/components/ui/sonner";
import { getFiles } from "@/services/core";
import type { FileItem, Role } from "@/data/types";
import { useAppState } from "@/state/app-state";

type FileCategoryKey =
  | "all"
  | "fisler"
  | "karsilama_tabelalari"
  | "yasal_evraklar"
  | "operasyon_belgeleri";

const categoryOptions: Array<[FileCategoryKey, string]> = [
  ["all", "Tümü"],
  ["fisler", "Fişler"],
  ["karsilama_tabelalari", "Karşılama"],
  ["yasal_evraklar", "Yasal"],
  ["operasyon_belgeleri", "Operasyon"],
];

function getFileIcon(file: FileItem) {
  if (file.category === "fisler") return <Receipt className="h-5 w-5 text-gold-500" />;
  if (file.category === "karsilama_tabelalari") return <ScanText className="h-5 w-5 text-azure-500" />;
  if (file.category === "yasal_evraklar") return <FileBadge className="h-5 w-5 text-danger" />;
  return <FileText className="h-5 w-5 text-success" />;
}

function getCategoryLabel(category: FileItem["category"]) {
  const map: Record<FileItem["category"], string> = {
    fisler: "Fiş",
    karsilama_tabelalari: "Karşılama Tabelası",
    yasal_evraklar: "Yasal Evrak",
    operasyon_belgeleri: "Operasyon Belgesi",
  };
  return map[category];
}

function getCategoryColor(category: FileItem["category"]) {
  const map: Record<FileItem["category"], string> = {
    fisler: "bg-gold-500/10 text-gold-500",
    karsilama_tabelalari: "bg-azure-500/10 text-azure-500",
    yasal_evraklar: "bg-danger/10 text-danger",
    operasyon_belgeleri: "bg-success/10 text-success",
  };
  return map[category];
}

function buildFileShareText(file: FileItem) {
  return [
    `Belge: ${file.name}`,
    `Kategori: ${getCategoryLabel(file.category)}`,
    file.project_name ? `Proje: ${file.project_name}` : null,
    file.operation_label ? `Operasyon: ${file.operation_label}` : null,
    `Tarih: ${file.date}`,
  ]
    .filter(Boolean)
    .join("\n");
}

export function FilesScreen({ role }: { role: Role }) {
  const rawFiles = getFiles();
  const files = Array.isArray(rawFiles) ? rawFiles : [];
  const { selectedOperationContext } = useAppState();
  const [category, setCategory] = useState<FileCategoryKey>("all");
  const [search, setSearch] = useState("");
  const [operationFilter, setOperationFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("");
  const [previewFileId, setPreviewFileId] = useState<number | null>(null);
  const [shareFileId, setShareFileId] = useState<number | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const normalizedQuery = search.trim().toLowerCase();

  const operationOptions = useMemo(
    () =>
      Array.from(
        new Set(
          files
            .map((file) => (typeof file?.operation_label === "string" ? file.operation_label : null))
            .filter((value): value is string => Boolean(value)),
        ),
      ),
    [files],
  );

  useEffect(() => {
    const nextOperation = selectedOperationContext?.operationLabel;
    if (nextOperation && operationOptions.includes(nextOperation)) {
      setOperationFilter(nextOperation);
    }
  }, [operationOptions, selectedOperationContext]);

  const filtered = useMemo(
    () =>
      files
        .filter((file) => {
          const projectName = typeof file.project_name === "string" ? file.project_name : "";
          const operationLabel = typeof file.operation_label === "string" ? file.operation_label : "";
          const scopedOperationLabel = selectedOperationContext?.operationLabel?.trim() || "";
          const scopedProjectName = selectedOperationContext?.projectName?.trim() || "";
          const scopedJobTime = selectedOperationContext?.jobTime?.trim() || "";
          const contextMatch =
            !selectedOperationContext ||
            operationLabel === scopedOperationLabel ||
            projectName === scopedProjectName ||
            (Boolean(scopedJobTime) && operationLabel.startsWith(`${scopedJobTime} `));
          const categoryMatch = category === "all" || file.category === category;
          const operationMatch = operationFilter === "all" || operationLabel === operationFilter;
          const dateMatch = dateFilter.length === 0 || file.date === dateFilter;
          const searchMatch =
            normalizedQuery.length === 0 ||
            file.name.toLowerCase().includes(normalizedQuery) ||
            projectName.toLowerCase().includes(normalizedQuery) ||
            operationLabel.toLowerCase().includes(normalizedQuery);

          return contextMatch && categoryMatch && operationMatch && dateMatch && searchMatch;
        })
        .sort((a, b) => {
          const getPriority = (file: FileItem) => {
            if (role === "greeter" && file.category === "karsilama_tabelalari") return 0;
            if (role === "driver" && file.category === "yasal_evraklar") return 0;
            if (file.important) return 1;
            return 2;
          };

          const priorityDiff = getPriority(a) - getPriority(b);
          if (priorityDiff !== 0) return priorityDiff;
          return b.date.localeCompare(a.date);
        }),
    [category, dateFilter, files, normalizedQuery, operationFilter, role, selectedOperationContext],
  );

  const previewFile = filtered.find((file) => file.id === previewFileId) ?? null;
  const importantCount = filtered.filter((file) => file.important).length;
  const offlineCount = filtered.filter((file) => file.offline).length;
  const savedCount = filtered.filter((file) => file.savedToDevice).length;

  const handleDownload = (file: FileItem) => {
    const textContent = `${buildFileShareText(file)}\n\nNot: Gerçek dosya bağlantısı Core entegrasyonu ile gelecektir.`;
    const blob = new Blob([textContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const safeName = file.name.replace(/\.[^/.]+$/, "");
    link.href = url;
    link.download = `${safeName}-ozet.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("Belge özeti indirildi");
  };

  const handleDeviceShare = async (file: FileItem) => {
    const shareText = buildFileShareText(file);

    if (navigator.share) {
      try {
        await navigator.share({ title: file.name, text: shareText });
        return;
      } catch {
        return;
      }
    }

    try {
      await navigator.clipboard.writeText(shareText);
      toast.success("Belge bilgisi panoya kopyalandı");
    } catch {
      toast.error("Bu cihazda paylaşım desteklenmiyor");
    }
  };

  const handleMailShare = (file: FileItem) => {
    const subject = encodeURIComponent(`Belge Paylaşımı: ${file.name}`);
    const body = encodeURIComponent(buildFileShareText(file));
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  };

  const handleWhatsappShare = (file: FileItem) => {
    const text = encodeURIComponent(buildFileShareText(file));
    window.open(`https://wa.me/?text=${text}`, "_blank", "noopener,noreferrer");
  };

  const activeFilterCount = [
    category !== "all",
    operationFilter !== "all",
    dateFilter.length > 0,
  ].filter(Boolean).length;

  return (
    <div className="flex flex-col gap-4 px-4 pb-6">
      {selectedOperationContext?.operationLabel && (
        <div className="rounded-xl border border-azure-500/20 bg-azure-500/5 p-3.5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-azure-500">
            Seçili Operasyon
          </p>
          <p className="mt-1 text-sm font-semibold text-foreground">
            {selectedOperationContext.operationLabel}
          </p>
          {selectedOperationContext.projectName && (
            <p className="mt-0.5 text-xs text-muted-foreground">{selectedOperationContext.projectName}</p>
          )}
        </div>
      )}

      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Belgeler</p>
          <p className="mt-2 text-right text-base font-bold text-foreground">{filtered.length}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Önemli</p>
          <p className="mt-2 text-right text-base font-bold text-danger">{importantCount}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Cihazda</p>
          <p className="mt-2 text-right text-base font-bold text-success">{savedCount}</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex min-w-0 flex-1 items-center gap-2.5 rounded-xl border border-border bg-card px-3.5 py-3">
          <Search className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Belge, proje veya operasyon ara..."
            className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
          />
          {search && (
            <button onClick={() => setSearch("")} className="flex-shrink-0">
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          )}
        </div>

        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`relative flex h-[46px] w-[46px] flex-shrink-0 items-center justify-center rounded-xl border transition-colors ${
            showFilters || activeFilterCount > 0
              ? "border-azure-500 bg-azure-500/10 text-azure-500"
              : "border-border bg-card text-muted-foreground"
          }`}
        >
          <Filter className="h-4 w-4" />
          {activeFilterCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-azure-500 text-[9px] font-bold text-white">
              {activeFilterCount}
            </span>
          )}
        </button>
      </div>

      {showFilters && (
        <div className="space-y-3 rounded-xl border border-border bg-card p-3.5">
          <div>
            <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Tarih
            </label>
            <div className="flex items-center gap-2">
              <div className="flex flex-1 items-center gap-2 rounded-lg border border-border bg-secondary/50 px-3 py-2">
                <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                <input
                  type="date"
                  value={dateFilter}
                  onChange={(event) => setDateFilter(event.target.value)}
                  className="w-full bg-transparent text-sm text-foreground outline-none"
                />
              </div>
              {dateFilter && (
                <button
                  onClick={() => setDateFilter("")}
                  className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-muted-foreground active:bg-secondary"
                >
                  Temizle
                </button>
              )}
            </div>
          </div>

          {operationOptions.length > 0 && (
            <div>
              <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Operasyon
              </label>
              <div className="flex flex-wrap gap-1.5">
                <button
                  onClick={() => setOperationFilter("all")}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    operationFilter === "all" ? "bg-azure-500 text-white" : "bg-secondary text-foreground"
                  }`}
                >
                  Tümü
                </button>
                {operationOptions.map((label) => (
                  <button
                    key={label}
                    onClick={() => setOperationFilter(label)}
                    className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                      operationFilter === label ? "bg-azure-500 text-white" : "bg-secondary text-foreground"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-1.5 overflow-x-auto pb-0.5">
        {categoryOptions.map(([value, label]) => (
          <button
            key={value}
            onClick={() => setCategory(value)}
            className={`rounded-lg px-3.5 py-2 text-xs font-semibold whitespace-nowrap transition-all ${
              category === value ? "bg-primary text-primary-foreground shadow-sm" : "bg-secondary/70 text-muted-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <p className="text-xs text-muted-foreground">
        {filtered.length} belge bulundu
        {offlineCount > 0 ? ` • ${offlineCount} belge çevrimdışı hazır` : ""}
      </p>

      <div className="space-y-2.5">
        {filtered.map((file) => (
          <div key={file.id} className="overflow-hidden rounded-xl border border-border bg-card">
            <div className="flex items-start gap-3 p-4">
              <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-secondary/80">
                {getFileIcon(file)}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <p className="truncate text-[15px] font-semibold text-foreground">{file.name}</p>
                      {file.important && <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 text-danger" />}
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">{file.date}</p>
                  </div>

                  <span className={`flex-shrink-0 rounded-md px-2 py-0.5 text-[10px] font-semibold ${getCategoryColor(file.category)}`}>
                    {getCategoryLabel(file.category)}
                  </span>
                </div>

                <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                  {file.project_name && <span>{file.project_name}</span>}
                  {file.operation_label && <span>{file.operation_label}</span>}
                  {file.savedToDevice && (
                    <span className="inline-flex items-center gap-1 text-success">
                      <Smartphone className="h-2.5 w-2.5" /> Cihazda
                    </span>
                  )}
                  {file.offline ? (
                    <span className="inline-flex items-center gap-1">
                      <WifiOff className="h-2.5 w-2.5" /> Çevrimdışı
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-azure-500">
                      <Wifi className="h-2.5 w-2.5" /> Çevrimiçi
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex border-t border-border">
              <button
                onClick={() => {
                  setPreviewFileId((prev) => (prev === file.id ? null : file.id));
                  setShareFileId(null);
                }}
                className="flex flex-1 items-center justify-center gap-1.5 py-3 text-xs font-semibold text-azure-500 active:bg-azure-500/5"
              >
                <Eye className="h-4 w-4" />
                Görüntüle
              </button>
              <div className="w-px bg-border" />
              <button
                onClick={() => handleDownload(file)}
                className="flex flex-1 items-center justify-center gap-1.5 py-3 text-xs font-semibold text-foreground active:bg-secondary/50"
              >
                <Download className="h-4 w-4" />
                İndir
              </button>
              <div className="w-px bg-border" />
              <button
                onClick={() => {
                  setShareFileId((prev) => (prev === file.id ? null : file.id));
                  setPreviewFileId(null);
                }}
                className="flex flex-1 items-center justify-center gap-1.5 py-3 text-xs font-semibold text-success active:bg-success/5"
              >
                <Share2 className="h-4 w-4" />
                Paylaş
              </button>
            </div>

            {shareFileId === file.id && (
              <div className="border-t border-border bg-secondary/30 p-3">
                <p className="mb-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Paylaşım Seçenekleri
                </p>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    onClick={() => handleDeviceShare(file)}
                    className="flex flex-col items-center gap-1.5 rounded-lg bg-card p-3 text-[11px] font-semibold text-foreground active:bg-secondary"
                  >
                    <Smartphone className="h-5 w-5 text-success" />
                    Cihaza
                  </button>
                  <button
                    onClick={() => handleMailShare(file)}
                    className="flex flex-col items-center gap-1.5 rounded-lg bg-card p-3 text-[11px] font-semibold text-foreground active:bg-secondary"
                  >
                    <Mail className="h-5 w-5 text-azure-500" />
                    E-posta
                  </button>
                  <button
                    onClick={() => handleWhatsappShare(file)}
                    className="flex flex-col items-center gap-1.5 rounded-lg bg-card p-3 text-[11px] font-semibold text-foreground active:bg-secondary"
                  >
                    <Share2 className="h-5 w-5 text-gold-500" />
                    WhatsApp
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}

        {previewFile && (
          <div className="rounded-xl border border-azure-500/30 bg-card p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-azure-500/10">
                  {getFileIcon(previewFile)}
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">{previewFile.name}</p>
                  <p className="text-[11px] text-muted-foreground">{getCategoryLabel(previewFile.category)}</p>
                </div>
              </div>
              <button
                onClick={() => setPreviewFileId(null)}
                className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary text-muted-foreground active:bg-secondary/80"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-3 rounded-lg bg-secondary/40 px-4 py-5 text-center">
              <p className="text-sm text-muted-foreground">
                {previewFile.operation_label || previewFile.project_name || "Genel belge"}
              </p>
              <p className="mt-2 text-xs text-muted-foreground/70">
                Gerçek dosya önizlemesi Core entegrasyonu ile gelecek.
              </p>
            </div>
          </div>
        )}

        {filtered.length === 0 && (
          <div className="rounded-xl border border-dashed border-border bg-card/50 px-6 py-10 text-center">
            <FileText className="mx-auto h-8 w-8 text-muted-foreground/40" />
            <p className="mt-3 text-sm font-medium text-muted-foreground">Filtrelere uygun dosya bulunamadı</p>
            <p className="mt-1 text-xs text-muted-foreground/60">Farklı bir kategori veya arama terimi deneyin</p>
          </div>
        )}
      </div>
    </div>
  );
}
