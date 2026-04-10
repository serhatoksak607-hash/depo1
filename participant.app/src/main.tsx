import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

async function resetLegacyClientCaches() {
  if (typeof window === "undefined") return;

  try {
    if ("serviceWorker" in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(registrations.map((registration) => registration.unregister()));
    }

    if ("caches" in window) {
      const cacheKeys = await caches.keys();
      await Promise.all(cacheKeys.map((cacheKey) => caches.delete(cacheKey)));
    }
  } catch {
    // Old client cache cleanup should never block app boot.
  }
}

void resetLegacyClientCaches();

createRoot(document.getElementById("root")!).render(<App />);
