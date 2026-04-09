import creatroLogo from "@/assets/brand/formice.png";
import type { Role } from "@/data/types";
import { getAppConfig } from "@/services/core";

interface AppLoadingScreenProps {
  role?: Role;
}

export function AppLoadingScreen({ role = "driver" }: AppLoadingScreenProps) {
  const appConfig = getAppConfig(role);
  const loadingLogo = appConfig.branding.loading_logo_url || creatroLogo;
  const loadingPrimary = appConfig.branding.loading_primary_color || "#F28C28";
  const loadingBase = appConfig.branding.loading_base_color || "#102B64";
  const gradientEnd = "#19564D";

  return (
    <div
      className="flex min-h-screen items-center justify-center px-6"
      style={{ background: `linear-gradient(180deg, ${loadingBase} 0%, ${gradientEnd} 100%)` }}
    >
      <div className="flex w-full max-w-sm flex-col items-center gap-6 text-center">
        <img
          src={loadingLogo}
          alt="Uygulama logosu"
          className="h-14 w-auto max-w-[180px] object-contain sm:h-20 sm:max-w-[240px]"
          width={240}
          height={80}
        />
        <div className="space-y-2">
          <p className="text-sm font-bold uppercase tracking-[0.24em]" style={{ color: loadingPrimary }}>
            Yükleniyor
          </p>
          <p className="text-sm text-slate-200">Katılımcı verileri hazırlanıyor...</p>
        </div>
        <div className="h-1.5 w-40 overflow-hidden rounded-full bg-white/10">
          <div className="loading-bar h-full w-1/2 rounded-full" style={{ backgroundColor: loadingPrimary }} />
        </div>
      </div>
    </div>
  );
}
