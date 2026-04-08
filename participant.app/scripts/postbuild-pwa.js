const fs = require("fs");
const path = require("path");

const appRoot = path.resolve(__dirname, "..");
const distDir = path.join(appRoot, "dist");
const assetsDir = path.join(appRoot, "pwa-assets");
const indexPath = path.join(distDir, "index.html");

if (!fs.existsSync(indexPath)) {
  throw new Error(`PWA postbuild could not find ${indexPath}`);
}

const manifest = {
  name: "Creatro Participant",
  short_name: "Participant",
  description: "Katılımcı uygulaması PWA sürümü",
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

const serviceWorker = `const CACHE_NAME = "creatro-participant-v1";
const CORE_ASSETS = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/icon-192.png",
  "/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        if (!response || response.status !== 200 || response.type !== "basic") {
          return response;
        }
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        return response;
      }).catch(() => caches.match("/index.html"));
    })
  );
});`;

fs.writeFileSync(
  path.join(distDir, "manifest.webmanifest"),
  JSON.stringify(manifest, null, 2),
  "utf8",
);
fs.writeFileSync(path.join(distDir, "service-worker.js"), serviceWorker, "utf8");

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
  "<noscript>\n      Bu uygulamayı çalıştırmak için JavaScript etkin olmalıdır.\n    </noscript>",
);

if (!html.includes('rel="manifest"')) {
  html = html.replace(
    "</head>",
    [
      '    <meta name="theme-color" content="#113876" />',
      '    <meta name="apple-mobile-web-app-capable" content="yes" />',
      '    <meta name="apple-mobile-web-app-status-bar-style" content="default" />',
      '    <meta name="apple-mobile-web-app-title" content="Participant" />',
      '    <link rel="manifest" href="/manifest.webmanifest" />',
      '    <link rel="apple-touch-icon" href="/icon-192.png" />',
      "  </head>",
    ].join("\n"),
  );
}

if (!html.includes("serviceWorker.register")) {
  html = html.replace(
    "</body>",
    [
      '  <script>',
      '    if ("serviceWorker" in navigator) {',
      '      window.addEventListener("load", function () {',
      '        navigator.serviceWorker.register("/service-worker.js").catch(function (error) {',
      '          console.error("Service worker registration failed", error);',
      "        });",
      "      });",
      "    }",
      "  </script>",
      "</body>",
    ].join("\n"),
  );
}

fs.writeFileSync(indexPath, html, "utf8");
console.log("PWA assets generated in dist/");
