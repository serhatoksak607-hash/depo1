import { useEffect, useRef, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppLoadingScreen } from "@/components/AppLoadingScreen";
import creatroLogo from "@/assets/brand/formice.png";
import type { Role } from "@/data/types";
import { formatPersonName } from "@/lib/utils";
import {
  getAppConfig,
  getCoreBootstrap,
  getExpenses,
  getFiles,
  getJobsByDate,
  getOperations,
  getShellProfile,
} from "@/services/core";
import { AppStateProvider } from "@/state/app-state";
import Index from "./pages/Index.tsx";
import NotFound from "./pages/NotFound.tsx";

const queryClient = new QueryClient();
const LOADING_MIN_MS = 120;
const WELCOME_MIN_MS = 1200;
const ENABLE_WELCOME_VIDEO = false;
const AUTH_STORAGE_KEY = "participant-auth-v1";
const AUTH_USERNAME = "CreaTRo";
const AUTH_PASSWORD = "Micetro25+.";

function wait(ms: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function preloadCoreData(role: Role) {
  const appConfig = getAppConfig(role);
  const shellProfile = getShellProfile(role);
  const bootstrap = getCoreBootstrap(role);
  const operations = getOperations(role);
  const jobsByDate = getJobsByDate(role);
  const expenses = getExpenses();
  const files = getFiles();

  queryClient.setQueryData(["core", "app-config", role], appConfig);
  queryClient.setQueryData(["core", "shell-profile", role], shellProfile);
  queryClient.setQueryData(["core", "bootstrap", role], bootstrap);
  queryClient.setQueryData(["core", "operations", role], operations);
  queryClient.setQueryData(["core", "jobs-by-date", role], jobsByDate);
  queryClient.setQueryData(["core", "expenses"], expenses);
  queryClient.setQueryData(["core", "files"], files);
}

function getWelcomeMessage(date: Date) {
  const hour = date.getHours();

  if (hour < 12) return "Katılımcı paneli hazırlanıyor.";
  if (hour < 18) return "Katılımcı paneli hazırlanıyor.";
  return "Katılımcı paneli hazırlanıyor.";
}

function mixHexWithWhite(hex: string, whiteRatio: number) {
  const normalized = hex.replace("#", "");
  if (!/^[0-9a-fA-F]{6}$/.test(normalized)) {
    return "#C9D5E5";
  }

  const readChannel = (index: number) => parseInt(normalized.slice(index, index + 2), 16);
  const mixChannel = (value: number) => Math.round(value + (255 - value) * whiteRatio);

  const red = mixChannel(readChannel(0)).toString(16).padStart(2, "0");
  const green = mixChannel(readChannel(2)).toString(16).padStart(2, "0");
  const blue = mixChannel(readChannel(4)).toString(16).padStart(2, "0");

  return `#${red}${green}${blue}`;
}

interface WelcomeOverlayProps {
  role: Role;
}

function LoginGate({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = () => {
    if (username.trim() === AUTH_USERNAME && password === AUTH_PASSWORD) {
      window.localStorage.setItem(AUTH_STORAGE_KEY, "1");
      setError("");
      onLogin();
      return;
    }

    setError("Kullanıcı adı veya şifre hatalı.");
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#102B64]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(242,140,40,0.22),_transparent_42%),linear-gradient(140deg,_#102B64_0%,_#183B7E_52%,_#19564D_100%)]" />
      <div className="relative z-10 flex min-h-screen items-center justify-center px-5 py-10">
        <div className="w-full max-w-md overflow-hidden rounded-[32px] border border-white/10 bg-white shadow-[0_30px_80px_rgba(0,0,0,0.35)]">
          <div className="bg-white px-8 py-8 text-center">
            <img src={creatroLogo} alt="" className="mx-auto h-20 w-auto object-contain" />
            <p className="mt-5 text-xs font-bold uppercase tracking-[0.3em] text-[#F28C28]">Participant Login</p>
            <h1 className="mt-3 text-2xl font-semibold text-[#102B64]">Hoş Geldin</h1>
            <p className="mt-2 text-sm text-slate-300">Katılımcı uygulamasına giriş yaparak devam edin.</p>
          </div>
          <div className="space-y-4 px-8 py-8">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              <p><strong>Kullanıcı:</strong> {AUTH_USERNAME}</p>
              <p><strong>Şifre:</strong> {AUTH_PASSWORD}</p>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Kullanıcı Adı</label>
              <input
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-[#F28C28]"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") handleSubmit();
                }}
                placeholder="CreaTRo"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Şifre</label>
              <input
                type="password"
                className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-[#F28C28]"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") handleSubmit();
                }}
                placeholder="Micetro25+."
              />
            </div>
            {error ? <p className="text-sm font-medium text-rose-600">{error}</p> : null}
            <button
              type="button"
              onClick={handleSubmit}
              className="w-full rounded-2xl bg-[#F28C28] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#DF7B1D]"
            >
              Giriş Yap
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function WelcomeOverlay({ role }: WelcomeOverlayProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [videoReady, setVideoReady] = useState(false);
  const [videoFailed, setVideoFailed] = useState(false);
  const [showVideo, setShowVideo] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const appConfig = getAppConfig(role);
  const shellProfile = getShellProfile(role);
  const logoUrl = appConfig.branding.loading_logo_url || appConfig.branding.logo_url || creatroLogo;
  const primaryColor = appConfig.branding.loading_primary_color || appConfig.branding.primary_color || "#F28C28";
  const secondaryColor = mixHexWithWhite(
    appConfig.branding.loading_base_color || appConfig.branding.base_color || "#102B64",
    0.82,
  );
  const welcomeName = formatPersonName(shellProfile.full_name);
  const welcomeMessage = getWelcomeMessage(new Date());

  useEffect(() => {
    if (!ENABLE_WELCOME_VIDEO) {
      return;
    }

    const video = videoRef.current;
    if (!video) {
      return;
    }

    const attemptPlay = async () => {
      try {
        video.muted = true;
        await video.play();
        setShowVideo(true);
      } catch {
        setVideoFailed(true);
      }
    };

    void attemptPlay();
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => setIsClosing(true), Math.max(0, WELCOME_MIN_MS - 320));
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#102B64]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(242,140,40,0.22),_transparent_42%),linear-gradient(140deg,_#102B64_0%,_#183B7E_52%,_#19564D_100%)]" />
      <div className="absolute inset-0 flex items-center justify-center">
        <div
          className={`flex w-full max-w-[320px] flex-col items-center gap-4 px-6 text-center transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] sm:max-w-sm sm:gap-5 ${
            isClosing ? "-translate-y-[38vh] scale-[0.64] opacity-15 sm:-translate-y-[34vh] sm:scale-[0.68]" : "translate-y-0 scale-100 opacity-100"
          }`}
        >
          <img
            src={logoUrl}
            alt=""
            aria-hidden="true"
            className="h-14 w-auto max-w-[180px] object-contain sm:h-20 sm:max-w-[240px]"
            width={240}
            height={80}
          />
          <div className={`space-y-1.5 transition-all duration-150 sm:space-y-2 ${isClosing ? "translate-y-2 opacity-0" : "translate-y-0 opacity-100"}`}>
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] sm:text-xs sm:tracking-[0.3em]" style={{ color: primaryColor }}>
              Hoş Geldin
            </p>
            <p className="text-xl font-semibold tracking-[0.03em] text-white sm:text-2xl sm:tracking-[0.04em]">{welcomeName}</p>
            <p className="text-[13px] leading-5 sm:text-sm" style={{ color: secondaryColor }}>{welcomeMessage}</p>
          </div>
          <div className={`h-1.5 w-32 overflow-hidden rounded-full bg-white/10 transition-all duration-150 sm:w-40 ${isClosing ? "translate-y-2 opacity-0" : "translate-y-0 opacity-100"}`}>
            <div className="h-full w-1/2 rounded-full" style={{ backgroundColor: primaryColor }} />
          </div>
        </div>
      </div>
      {ENABLE_WELCOME_VIDEO && (
        <video
          ref={videoRef}
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-300 ${showVideo && videoReady && !videoFailed ? "opacity-100" : "opacity-0"}`}
          autoPlay
          muted
          playsInline
          preload="auto"
          onLoadedData={() => setVideoReady(true)}
          onCanPlay={() => setVideoReady(true)}
          onError={() => setVideoFailed(true)}
        >
          <source src="/coftransfer-welcome.mp4" type="video/mp4" />
        </video>
      )}
    </div>
  );
}

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(() => window.localStorage.getItem(AUTH_STORAGE_KEY) === "1");
  const [bootPhase, setBootPhase] = useState<"loading" | "welcome" | "ready">("loading");
  const [bootRole] = useState<Role>("driver");

  useEffect(() => {
    if (!isAuthenticated) {
      setBootPhase("loading");
      return;
    }

    let active = true;

    const runBootFlow = async () => {
      await Promise.all([
        preloadCoreData(bootRole),
        wait(LOADING_MIN_MS),
      ]);

      if (!active) {
        return;
      }

      setBootPhase("welcome");

      await wait(WELCOME_MIN_MS);

      if (!active) {
        return;
      }

      setBootPhase("ready");
    };

    void runBootFlow();

    return () => {
      active = false;
    };
  }, [bootRole, isAuthenticated]);

  return (
    <QueryClientProvider client={queryClient}>
      <AppStateProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          {!isAuthenticated ? (
            <LoginGate onLogin={() => setIsAuthenticated(true)} />
          ) : (
            bootPhase === "loading" ? (
              <AppLoadingScreen role={bootRole} />
            ) : bootPhase === "welcome" ? (
              <WelcomeOverlay role={bootRole} />
            ) : (
              <BrowserRouter>
                <Routes>
                  <Route path="/" element={<Index />} />
                  {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </BrowserRouter>
            )
          )}
        </TooltipProvider>
      </AppStateProvider>
    </QueryClientProvider>
  );
};

export default App;

