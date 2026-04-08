const fs = require("fs");
const path = require("path");

const appRoot = path.resolve(__dirname, "..");
const distDir = path.join(appRoot, "dist");
const assetsDir = path.join(appRoot, "pwa-assets");
const indexPath = path.join(distDir, "index.html");
const offlinePath = path.join(distDir, "offline.html");

if (!fs.existsSync(indexPath)) {
  throw new Error(`PWA postbuild could not find ${indexPath}`);
}

const manifest = {
  name: "Creatro Participant",
  short_name: "Participant",
  description: "Kat\u0131l\u0131mc\u0131 uygulamas\u0131 PWA s\u00fcr\u00fcm\u00fc",
  lang: "tr",
  start_url: "/",
  scope: "/",
  display: "standalone",
  orientation: "portrait",
  background_color: "#091028",
  theme_color: "#113876",
  icons: [
    {
      src: "/icon-192.png",
      sizes: "192x192",
      type: "image/png",
      purpose: "any maskable",
    },
    {
      src: "/icon-512.png",
      sizes: "512x512",
      type: "image/png",
      purpose: "any maskable",
    },
  ],
};

const offlineHtml = `<!DOCTYPE html>
<html lang="tr">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#113876" />
    <title>Participant \u00c7evrimd\u0131\u015f\u0131</title>
    <style>
      :root {
        color-scheme: light;
      }
      * {
        box-sizing: border-box;
      }
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 24px;
        font-family: "Segoe UI", Arial, sans-serif;
        background:
          radial-gradient(circle at top, rgba(140, 211, 255, 0.3), transparent 42%),
          linear-gradient(160deg, #091028 0%, #113876 58%, #1b5fc1 100%);
        color: #ffffff;
      }
      .card {
        width: min(100%, 420px);
        border-radius: 28px;
        padding: 28px 24px;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.18);
        backdrop-filter: blur(12px);
        box-shadow: 0 24px 60px rgba(4, 10, 24, 0.35);
      }
      .eyebrow {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #cde9ff;
      }
      h1 {
        margin: 14px 0 10px;
        font-size: 28px;
        line-height: 1.15;
      }
      p {
        margin: 0;
        font-size: 15px;
        line-height: 1.65;
        color: #e8f3ff;
      }
    </style>
  </head>
  <body>
    <section class="card">
      <div class="eyebrow">Creatro Participant</div>
      <h1>\u015eu anda \u00e7evrimd\u0131\u015f\u0131s\u0131n\u0131z</h1>
      <p>\u0130nternet ba\u011flant\u0131s\u0131 geldi\u011finde uygulama yeniden veri alacakt\u0131r. Daha \u00f6nce a\u00e7\u0131lan i\u00e7erikler \u00f6nbellekten g\u00f6sterilmeye devam eder.</p>
    </section>
  </body>
</html>`;

const serviceWorker = `const CACHE_NAME = "creatro-participant-v2";
const CORE_ASSETS = [
  "/",
  "/index.html",
  "/offline.html",
  "/manifest.webmanifest",
  "/icon-192.png",
  "/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(CORE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;

      return fetch(event.request)
        .then((response) => {
          if (!response || response.status !== 200) {
            return response;
          }

          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() => {
          const acceptsHtml = event.request.headers.get("accept")?.includes("text/html");
          if (acceptsHtml) {
            return caches.match("/offline.html");
          }
          return caches.match("/index.html");
        });
    })
  );
});`;

fs.writeFileSync(
  path.join(distDir, "manifest.webmanifest"),
  JSON.stringify(manifest, null, 2),
  "utf8",
);
fs.writeFileSync(path.join(distDir, "service-worker.js"), serviceWorker, "utf8");
fs.writeFileSync(offlinePath, offlineHtml, "utf8");

for (const fileName of ["icon-192.png", "icon-512.png"]) {
  const source = path.join(assetsDir, fileName);
  const target = path.join(distDir, fileName);
  if (!fs.existsSync(source)) {
    throw new Error(`Missing PWA asset: ${source}`);
  }
  fs.copyFileSync(source, target);
}

let html = fs.readFileSync(indexPath, "utf8");

html = html.replace('<html lang="en">', '<html lang="tr">');
html = html.replace(
  "<noscript>\n      You need to enable JavaScript to run this app.\n    </noscript>",
  "<noscript>\n      Bu uygulamay\u0131 \u00e7al\u0131\u015ft\u0131rmak i\u00e7in JavaScript etkin olmal\u0131d\u0131r.\n    </noscript>",
);

const pwaHead = [
  '    <meta name="theme-color" content="#113876" />',
  '    <meta name="apple-mobile-web-app-capable" content="yes" />',
  '    <meta name="apple-mobile-web-app-status-bar-style" content="default" />',
  '    <meta name="apple-mobile-web-app-title" content="Participant" />',
  '    <link rel="manifest" href="/manifest.webmanifest" />',
  '    <link rel="apple-touch-icon" href="/icon-192.png" />',
  "    <style>",
  "      html, body {",
  "        min-height: 100%;",
  "      }",
  "      body {",
  "        margin: 0;",
  "        overflow-y: auto !important;",
  "        overflow-x: hidden;",
  "        background:",
  "          radial-gradient(circle at top, rgba(140, 211, 255, 0.28), transparent 30%),",
  "          linear-gradient(180deg, #071127 0%, #0e2246 48%, #173b78 100%);",
  "      }",
  "      #root {",
  "        width: 100%;",
  "      }",
  "      @media (min-width: 980px) {",
  "        body {",
  "          padding: 32px 24px;",
  "        }",
  "        #root {",
  "          max-width: 430px;",
  "          min-height: calc(100vh - 64px);",
  "          margin: 0 auto;",
  "          border-radius: 34px;",
  "          overflow: hidden;",
  "          box-shadow: 0 32px 80px rgba(3, 10, 24, 0.45), 0 0 0 1px rgba(255,255,255,0.12);",
  "          background: #eff4ff;",
  "        }",
  "      }",
  "      @media (max-width: 979px) {",
  "        body {",
  "          padding: 0;",
  "        }",
  "        #root {",
  "          max-width: none;",
  "          min-height: 100vh;",
  "          border-radius: 0;",
  "          box-shadow: none;",
  "        }",
  "      }",
  "      #pwa-install-banner {",
  "        position: fixed;",
  "        left: 16px;",
  "        right: 16px;",
  "        bottom: 16px;",
  "        display: none;",
  "        align-items: center;",
  "        justify-content: space-between;",
  "        gap: 12px;",
  "        padding: 14px 16px;",
  "        border-radius: 18px;",
  "        background: rgba(9, 16, 40, 0.94);",
  "        color: #fff;",
  "        border: 1px solid rgba(140, 211, 255, 0.28);",
  "        box-shadow: 0 16px 32px rgba(9, 16, 40, 0.35);",
  '        font-family: "Segoe UI", Arial, sans-serif;',
  "        z-index: 9999;",
  "      }",
  "      #pwa-install-banner.show {",
  "        display: flex;",
  "      }",
  "      #pwa-install-banner button {",
  "        border: 0;",
  "        border-radius: 999px;",
  "        padding: 10px 14px;",
  "        font-weight: 700;",
  "        cursor: pointer;",
  "      }",
  "      #pwa-install-confirm {",
  "        background: #8cd3ff;",
  "        color: #091028;",
  "      }",
  "      #pwa-install-dismiss {",
  "        background: transparent;",
  "        color: #cfe8ff;",
  "      }",
  "    </style>",
].join("\n");

if (!html.includes('rel="manifest"')) {
  html = html.replace("</head>", `${pwaHead}\n  </head>`);
}

const installBannerHtml = [
  '  <div id="pwa-install-banner">',
  '    <span>Participant uygulamas\u0131n\u0131 ana ekrana ekleyebilirsiniz.</span>',
  '    <div>',
  '      <button id="pwa-install-dismiss" type="button">Daha Sonra</button>',
  '      <button id="pwa-install-confirm" type="button">Y\u00fckle</button>',
  "    </div>",
  "  </div>",
].join("\n");

const pwaScript = [
  "  <script>",
  "    if ('serviceWorker' in navigator) {",
  "      window.addEventListener('load', function () {",
  "        navigator.serviceWorker.register('/service-worker.js').catch(function (error) {",
  "          console.error('Service worker registration failed', error);",
  "        });",
  "      });",
  "    }",
  "    let deferredInstallPrompt = null;",
  "    const banner = document.getElementById('pwa-install-banner');",
  "    const confirmBtn = document.getElementById('pwa-install-confirm');",
  "    const dismissBtn = document.getElementById('pwa-install-dismiss');",
  "    window.addEventListener('beforeinstallprompt', function (event) {",
  "      event.preventDefault();",
  "      deferredInstallPrompt = event;",
  "      if (banner) banner.classList.add('show');",
  "    });",
  "    if (dismissBtn) {",
  "      dismissBtn.addEventListener('click', function () {",
  "        banner && banner.classList.remove('show');",
  "      });",
  "    }",
  "    if (confirmBtn) {",
  "      confirmBtn.addEventListener('click', async function () {",
  "        if (!deferredInstallPrompt) return;",
  "        deferredInstallPrompt.prompt();",
  "        await deferredInstallPrompt.userChoice;",
  "        deferredInstallPrompt = null;",
  "        banner && banner.classList.remove('show');",
  "      });",
  "    }",
  "    window.addEventListener('appinstalled', function () {",
  "      deferredInstallPrompt = null;",
  "      banner && banner.classList.remove('show');",
  "    });",
  "  </script>",
].join("\n");

if (!html.includes('id="pwa-install-banner"')) {
  html = html.replace("</body>", `${installBannerHtml}\n${pwaScript}\n</body>`);
}

fs.writeFileSync(indexPath, html, "utf8");
console.log("PWA assets generated in dist/");
