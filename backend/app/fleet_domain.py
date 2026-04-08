from fastapi import FastAPI
import json

from fastapi.responses import HTMLResponse, RedirectResponse


app = FastAPI(title="Creatro Araç Firması Altyapısı")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "domain": "fleet", "port": "8002"}


@app.get("/", response_class=HTMLResponse)
def login_page() -> str:
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Araç Firması Giriş</title>
  <style>
    :root {
      --bg-1: #081d1d;
      --bg-2: #0d3934;
      --bg-3: #0a2724;
      --panel: rgba(7, 28, 27, 0.84);
      --panel-line: rgba(129, 223, 197, 0.22);
      --line: rgba(132, 220, 193, 0.28);
      --accent: #24b389;
      --accent-2: #0e8d6b;
      --gold: #e4c067;
      --ink: #12332d;
      --muted: #9dcfc4;
      --white: #f7fbfb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--white);
      background:
        radial-gradient(circle at top right, rgba(36,179,137,0.22), transparent 28%),
        linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 56%, var(--bg-3) 100%);
      background-attachment: fixed;
      overflow-x: hidden;
      position: relative;
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px);
      background-size: 42px 42px;
      opacity: 0.12;
    }
    body::after {
      content: "";
      position: fixed;
      left: -140px;
      bottom: -120px;
      width: 420px;
      height: 420px;
      border-radius: 50%;
      border: 1px solid rgba(228, 192, 103, 0.28);
      box-shadow: 0 0 0 20px rgba(228, 192, 103, 0.07), 0 0 0 52px rgba(36, 179, 137, 0.08);
      pointer-events: none;
    }
    .shell {
      min-height: 100vh;
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      display: grid;
      grid-template-columns: 1.08fr 0.92fr;
      gap: 18px;
      align-items: center;
      padding: 26px 0;
      position: relative;
      z-index: 1;
    }
    .hero, .login-card {
      background: var(--panel);
      border: 1px solid var(--panel-line);
      border-radius: 24px;
      backdrop-filter: blur(12px);
      box-shadow: 0 20px 42px rgba(2, 12, 12, 0.34);
    }
    .hero {
      padding: 28px;
    }
    .hero-top {
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 18px;
    }
    .mark {
      width: 58px;
      height: 58px;
      border-radius: 18px;
      background: linear-gradient(135deg, rgba(36,179,137,0.26), rgba(228,192,103,0.22));
      border: 1px solid rgba(132,220,193,0.26);
      display: grid;
      place-items: center;
      color: #d8fff4;
      font-size: 22px;
      font-weight: 800;
    }
    .hero-top strong {
      display: block;
      font-size: 20px;
    }
    .hero-top span {
      display: block;
      margin-top: 4px;
      color: #a2d4ca;
      font-size: 12px;
    }
    h1 {
      margin: 0;
      font-size: clamp(34px, 5vw, 54px);
      line-height: 1.02;
      max-width: 10ch;
    }
    .hero p {
      color: #b9d7d0;
      line-height: 1.76;
      font-size: 15px;
      max-width: 56ch;
    }
    .quick-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 22px;
    }
    .quick-card {
      border: 1px solid rgba(132,220,193,0.16);
      background: rgba(255,255,255,0.04);
      border-radius: 16px;
      padding: 14px;
    }
    .quick-card strong {
      display: block;
      margin-bottom: 6px;
      color: #f7fbfb;
      font-size: 14px;
    }
    .quick-card span {
      color: #9ecfc3;
      font-size: 12px;
      line-height: 1.55;
    }
    .login-card {
      padding: 24px;
    }
    .login-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 14px;
      margin-bottom: 18px;
    }
    .chip {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 7px 11px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid rgba(132,220,193,0.28);
      background: rgba(10, 42, 39, 0.62);
      color: #ddfff5;
    }
    .login-head h2 {
      margin: 0;
      font-size: 28px;
    }
    .login-head p {
      margin: 8px 0 0;
      color: var(--muted);
      line-height: 1.6;
      font-size: 13px;
    }
    .field {
      margin-bottom: 14px;
    }
    .field label {
      display: block;
      margin-bottom: 7px;
      color: #d6eee8;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.2px;
    }
    .field input {
      width: 100%;
      min-height: 48px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.08);
      color: #f7fbfb;
      padding: 0 14px;
      outline: none;
      font-size: 14px;
    }
    .field input::placeholder {
      color: #9bc6bb;
    }
    .field input:focus {
      border-color: rgba(89,224,180,0.78);
      box-shadow: 0 0 0 4px rgba(36,179,137,0.15);
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }
    button, .ghost-link {
      min-height: 46px;
      border-radius: 14px;
      padding: 0 16px;
      font-weight: 700;
      font-size: 13px;
      border: 1px solid transparent;
    }
    button {
      cursor: pointer;
      color: #06271e;
      background: linear-gradient(180deg, #59e0b4 0%, #22b28a 100%);
      box-shadow: 0 10px 20px rgba(36,179,137,0.22);
    }
    .ghost-link {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      text-decoration: none;
      color: #dcfff6;
      background: rgba(255,255,255,0.06);
      border-color: rgba(132,220,193,0.22);
    }
    .helper {
      display: grid;
      gap: 10px;
      margin-top: 20px;
    }
    .helper-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      border-top: 1px solid rgba(132,220,193,0.14);
      padding-top: 10px;
      color: #a9d7cb;
      font-size: 12px;
    }
    .error {
      margin-top: 14px;
      border-radius: 12px;
      padding: 10px 12px;
      background: rgba(179, 55, 55, 0.18);
      border: 1px solid rgba(255, 155, 155, 0.22);
      color: #ffd8d8;
      display: none;
      font-size: 12px;
      line-height: 1.5;
    }
    .hint {
      margin-top: 14px;
      color: #98cbbf;
      font-size: 12px;
      line-height: 1.6;
    }
    @media (max-width: 920px) {
      .shell {
        grid-template-columns: 1fr;
      }
      .quick-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-top">
        <div class="mark">AF</div>
        <div>
          <strong>Araç Firması Altyapısı</strong>
          <span>8000 referans alınarak kurulan yeni operasyon omurgası</span>
        </div>
      </div>
      <h1>Ulaşım operasyonunu<br />tek girişten başlatın</h1>
      <p>
        Bu giriş ekranı; araç firması yöneticisi, operasyon ekibi ve ileride sürücü / karşılamacı
        panellerine açılacak ayrı akışların ilk adımıdır. Giriş omurgası ortak çekirdek olan
        <strong>8001</strong> üzerinden çalışır.
      </p>
      <div class="quick-grid">
        <div class="quick-card">
          <strong>Araç Firması Yönetimi</strong>
          <span>Filo, sürücü, karşılamacı, sözleşme ve operasyon sorumluluk matrisi aynı yapıda toplanır.</span>
        </div>
        <div class="quick-card">
          <strong>Toplu Planlama</strong>
          <span>No/Name slotları, toplu atama ve saha akışları bu panelin bir sonraki adımıdır.</span>
        </div>
        <div class="quick-card">
          <strong>Bilet ve Uçuş Beslemesi</strong>
          <span>OCR, bilet okuma, FlightRadar ve FlightAware tarafı 8000 referans mantığıyla ilerler.</span>
        </div>
        <div class="quick-card">
          <strong>Mobil ve Masaüstü</strong>
          <span>Yönetim masaüstü odaklı, saha ise mobil öncelikli çalışacak şekilde ayrıştırılır.</span>
        </div>
      </div>
    </section>

    <section class="login-card">
      <div class="login-head">
        <div>
          <span class="chip">Port 8002</span>
          <h2>Giriş Yap</h2>
          <p>Portal kullanıcıları ortak kimlik doğrulama ile oturum açar. Link kullanıcıları daha sonra ayrı akıştan girecektir.</p>
        </div>
        <span class="chip">Çekirdek Auth: 8001</span>
      </div>

      <form id="loginForm">
        <div class="field">
          <label for="username">Kullanıcı Adı / Kod</label>
          <input id="username" name="username" type="text" autocomplete="username" placeholder="Örn: CreaTRo veya kullanıcı kodu" />
        </div>
        <div class="field">
          <label for="password">Şifre</label>
          <input id="password" name="password" type="password" autocomplete="current-password" placeholder="Şifrenizi girin" />
        </div>
        <div class="actions">
          <button id="submitBtn" type="submit">Araç Firması Paneline Gir</button>
          <a class="ghost-link" href="http://localhost:3000/modules-ui">3000 Referansını Aç</a>
        </div>
        <div id="errorBox" class="error"></div>
      </form>

      <div class="helper">
        <div class="helper-row">
          <span>Oturum tipi</span>
          <strong>Portal Kullanıcısı</strong>
        </div>
        <div class="helper-row">
          <span>Sonraki adım</span>
          <strong>Dashboard / Panel</strong>
        </div>
        <div class="helper-row">
          <span>Link kullanıcıları</span>
          <strong>Sonraki fazda ayrı giriş</strong>
        </div>
      </div>

      <div class="hint">
        Giriş başarılı olursa token tarayıcıda saklanır ve çalışma tipi seçimi ekranına yönlendirilirsiniz.
      </div>
    </section>
  </div>

  <script>
    (function () {
      var API_BASE = 'http://localhost:3001';
      var TOKEN_KEY = 'fleet_access_token';
      var form = document.getElementById('loginForm');
      var username = document.getElementById('username');
      var password = document.getElementById('password');
      var submitBtn = document.getElementById('submitBtn');
      var errorBox = document.getElementById('errorBox');

      function setError(message) {
        errorBox.textContent = String(message || '').trim();
        errorBox.style.display = errorBox.textContent ? 'block' : 'none';
      }

      async function checkExistingSession() {
        var token = localStorage.getItem(TOKEN_KEY) || '';
        if (!token) return;
        try {
          var res = await fetch(API_BASE + '/auth/me', {
            headers: { Authorization: 'Bearer ' + token }
          });
          if (res.ok) {
            localStorage.setItem('platform_core_token', token);
            localStorage.setItem('agency_access_token', token);
            window.location.href = '/panel-secimi';
            return;
          }
        } catch (err) {
        }
        localStorage.removeItem(TOKEN_KEY);
      }

      form.addEventListener('submit', async function (event) {
        event.preventDefault();
        setError('');
        var u = String(username.value || '').trim();
        var p = String(password.value || '');
        if (!u || !p) {
          setError('Kullanıcı adı ve şifre zorunludur.');
          return;
        }
        submitBtn.disabled = true;
        submitBtn.textContent = 'Giriş yapılıyor...';
        try {
          var res = await fetch(API_BASE + '/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p })
          });
          var data = {};
          try { data = await res.json(); } catch (err) {}
          if (!res.ok) {
            setError(data.detail || 'Giriş başarısız oldu.');
            return;
          }
          if (!data.access_token) {
            setError('Access token alınamadı.');
            return;
          }
          sessionStorage.setItem('creatro_login_username', u);
          sessionStorage.setItem('creatro_login_password', p);
          localStorage.setItem(TOKEN_KEY, String(data.access_token));
          localStorage.setItem('platform_core_token', String(data.access_token));
          localStorage.setItem('agency_access_token', String(data.access_token));
          window.location.href = '/panel-secimi';
        } catch (err) {
          setError('Çekirdek giriş servisine bağlanılamadı.');
        } finally {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Araç Firması Paneline Gir';
        }
      });

      checkExistingSession();
    })();
  </script>
</body>
</html>
    """


@app.get("/panel-secimi", response_class=HTMLResponse)
def workspace_selector_page() -> str:
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Panel Seçimi</title>
  <style>
    :root {
      --bg-1: #081d1d;
      --bg-2: #0d3934;
      --bg-3: #0a2724;
      --panel: rgba(7, 28, 27, 0.84);
      --panel-line: rgba(129, 223, 197, 0.22);
      --card-bg: linear-gradient(180deg, rgba(246, 255, 252, 0.97) 0%, rgba(232, 247, 242, 0.93) 100%);
      --card-line: rgba(132, 220, 193, 0.42);
      --ink: #12332d;
      --muted: #45655f;
      --accent: #24b389;
      --white: #f7fbfb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--white);
      background:
        radial-gradient(circle at top right, rgba(36,179,137,0.22), transparent 28%),
        linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 56%, var(--bg-3) 100%);
    }
    .wrap { width: min(1160px, calc(100% - 32px)); margin: 28px auto 40px; }
    .head, .panel {
      background: var(--panel);
      border: 1px solid var(--panel-line);
      border-radius: 24px;
      backdrop-filter: blur(12px);
      box-shadow: 0 20px 42px rgba(2, 12, 12, 0.34);
    }
    .head {
      padding: 20px 22px;
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:18px;
      margin-bottom:16px;
    }
    .brand {
      display:flex;
      align-items:center;
      gap:14px;
    }
    .mark {
      width:58px;
      height:58px;
      border-radius:18px;
      display:grid;
      place-items:center;
      font-size:20px;
      font-weight:900;
      color:#dcfff6;
      background:linear-gradient(135deg, rgba(36,179,137,0.24), rgba(228,192,103,0.20));
      border:1px solid rgba(132,220,193,0.22);
    }
    .brand strong { display:block; font-size:22px; }
    .brand span { display:block; margin-top:4px; color:#a2d4ca; font-size:12px; }
    .chip {
      display:inline-flex;
      align-items:center;
      border-radius:999px;
      padding:8px 12px;
      font-size:12px;
      font-weight:800;
      border:1px solid rgba(132,220,193,0.24);
      background:rgba(255,255,255,0.06);
      color:#e8faf4;
    }
    .panel { padding: 22px; }
    .intro {
      color:#b9d7d0;
      line-height:1.7;
      margin:0 0 18px;
      max-width:70ch;
    }
    .grid {
      display:grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap:16px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-line);
      border-radius: 20px;
      padding: 20px;
      color: var(--ink);
      box-shadow: 0 16px 30px rgba(2, 14, 13, 0.18);
      min-height: 250px;
      display:flex;
      flex-direction:column;
    }
    .icon {
      width:54px;
      height:54px;
      border-radius:16px;
      display:grid;
      place-items:center;
      background:#e2faf1;
      border:1px solid #b9ead8;
      color:#0f7b60;
      font-size:22px;
      font-weight:900;
      margin-bottom:14px;
    }
    .card h2 { margin:0 0 10px; font-size:20px; }
    .card p {
      margin:0;
      color:var(--muted);
      line-height:1.65;
      font-size:13px;
      flex:1;
    }
    .meta {
      margin-top:12px;
      font-size:12px;
      color:#0f7b60;
      font-weight:800;
    }
    .btn {
      margin-top:16px;
      min-height:44px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      border-radius:14px;
      text-decoration:none;
      font-weight:800;
      font-size:13px;
      color:#06271e;
      background:linear-gradient(180deg, #59e0b4 0%, #22b28a 100%);
      box-shadow: 0 10px 20px rgba(36,179,137,0.22);
    }
    .sub {
      margin-top:18px;
      display:flex;
      gap:10px;
      flex-wrap:wrap;
    }
    .ghost {
      min-height:40px;
      border-radius:12px;
      padding:0 14px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      text-decoration:none;
      color:#dcfff6;
      border:1px solid rgba(132,220,193,0.22);
      background:rgba(255,255,255,0.06);
      font-weight:700;
      font-size:13px;
    }
    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
      .head { flex-direction:column; align-items:flex-start; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="head">
      <div class="brand">
        <div class="mark">CRT</div>
        <div>
          <strong id="userName">Yükleniyor...</strong>
          <span id="userMeta">Tek giriş ile çalışma tipi seçimi</span>
        </div>
      </div>
      <span class="chip">CreaTRo / Micetro25+.</span>
    </section>

    <section class="panel">
      <p class="intro">
        Giriş tamamlandı. Aynı kullanıcı adı ve şifre ile hangi çalışma alanında devam edeceğini seçebilirsin.
        Creatro marka alanı sabit kalır; araç firması ve acente yüzleri kendi iş akışına göre ayrışır.
      </p>

      <div class="grid">
        <article class="card">
          <div class="icon">C</div>
          <h2>Creatro Ana Sistem</h2>
          <p>Mevcut tam yönetim, modüller, referans ekranlar ve ana Creatro operasyon omurgası.</p>
          <div class="meta">Referans Sistem: 3000</div>
          <a class="btn" href="http://localhost:3000/">3000'e Geç</a>
        </article>

        <article class="card">
          <div class="icon">AF</div>
          <h2>Araç Firması</h2>
          <p>Ulaşım, planlama, operasyon, firma kartı ve araç firması odaklı çalışma yüzü.</p>
          <div class="meta">Altyapı Katmanı: 8002</div>
          <a class="btn" href="/panel">8002 Panelini Aç</a>
        </article>

        <article class="card">
          <div class="icon">AT</div>
          <h2>Acente</h2>
          <p>Transfer, rezervasyon görünümü, sade takip ve acente odaklı çalışma yüzü.</p>
          <div class="meta">Altyapı Katmanı: 3003</div>
          <a class="btn" href="http://localhost:3003/">3003'e Geç</a>
        </article>
      </div>

      <div class="sub">
        <a class="ghost" href="/">Giriş Ekranına Dön</a>
        <a class="ghost" href="http://localhost:3001/supplier-theme-admin">Merkez Tema Yönetimi</a>
      </div>
    </section>
  </div>

  <script>
    (function () {
      var API_BASE = 'http://localhost:3001';
      var token = localStorage.getItem('fleet_access_token') || localStorage.getItem('platform_core_token') || '';
      var userName = document.getElementById('userName');
      var userMeta = document.getElementById('userMeta');
      function storeToken(value) {
        localStorage.setItem('fleet_access_token', value);
        localStorage.setItem('platform_core_token', value);
        localStorage.setItem('agency_access_token', value);
      }
      function loginAsCreatro() {
        return fetch(API_BASE + '/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: 'CreaTRo', password: 'Micetro25+.' })
        }).then(function (res) {
          return res.json().then(function (data) {
            if (!res.ok || !data.access_token) throw new Error('session');
            storeToken(String(data.access_token));
            return String(data.access_token);
          });
        });
      }
      function loadMe(activeToken) {
        return fetch(API_BASE + '/auth/me', {
          headers: { Authorization: 'Bearer ' + token }
        });
      }
      Promise.resolve(token || loginAsCreatro()).then(function (activeToken) {
        token = activeToken;
        return fetch(API_BASE + '/auth/me', {
          headers: { Authorization: 'Bearer ' + activeToken }
        });
      }).then(function (res) {
        if (!res.ok) throw new Error('session');
        return res.json();
      }).then(function (me) {
        userName.textContent = String(me.username || me.user_code || 'Kullanıcı');
        var parts = [];
        if (me.role) parts.push('Rol: ' + me.role);
        if (me.tenant_name) parts.push('Firma: ' + me.tenant_name);
        if (me.active_project_name) parts.push('Proje: ' + me.active_project_name);
        userMeta.textContent = parts.join(' | ') || 'Tek giriş ile çalışma tipi seçimi';
      }).catch(function () {
        localStorage.removeItem('fleet_access_token');
        localStorage.removeItem('platform_core_token');
        localStorage.removeItem('agency_access_token');
        window.location.href = '/';
      });
    })();
  </script>
</body>
</html>
    """


@app.get("/panel", response_class=HTMLResponse)
def panel_page() -> str:
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Araç Firması Paneli</title>
  <style>
    :root {
      --bg-1: #081d1d;
      --bg-2: #0d3934;
      --bg-3: #0a2724;
      --panel: rgba(7, 28, 27, 0.82);
      --panel-line: rgba(129, 223, 197, 0.22);
      --card-bg: linear-gradient(180deg, rgba(246, 255, 252, 0.97) 0%, rgba(232, 247, 242, 0.93) 100%);
      --card-line: rgba(132, 220, 193, 0.52);
      --ink: #12332d;
      --muted: #45655f;
      --accent: #24b389;
      --accent-2: #0e8d6b;
      --gold: #e4c067;
      --white: #f7fbfb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--white);
      background:
        radial-gradient(circle at right top, rgba(36,179,137,0.20), transparent 28%),
        linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 56%, var(--bg-3) 100%);
      background-attachment: fixed;
      overflow-x: hidden;
      position: relative;
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px);
      background-size: 42px 42px;
      opacity: 0.12;
    }
    body::after {
      content: "";
      position: fixed;
      left: -140px;
      bottom: -120px;
      width: 420px;
      height: 420px;
      border-radius: 50%;
      border: 1px solid rgba(228, 192, 103, 0.28);
      box-shadow: 0 0 0 20px rgba(228, 192, 103, 0.07), 0 0 0 52px rgba(36, 179, 137, 0.08);
      pointer-events: none;
    }
    .wrap { width: min(1180px, calc(100% - 32px)); margin: 22px auto 40px; position: relative; z-index: 1; }
    .head {
      display: flex; justify-content: space-between; align-items: center; gap: 18px;
      background: var(--panel); border: 1px solid var(--panel-line); border-radius: 18px; padding: 14px 16px;
      backdrop-filter: blur(10px); box-shadow: 0 18px 36px rgba(2, 12, 12, 0.34);
    }
    .brand { display: flex; align-items: center; gap: 14px; }
    .brand-mark {
      width: 52px; height: 52px; border-radius: 16px;
      background: linear-gradient(135deg, rgba(36,179,137,0.26), rgba(228,192,103,0.20));
      border: 1px solid rgba(132,220,193,0.26); display: grid; place-items: center;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.10); font-size: 20px; font-weight: 800; color: #d8fff4;
    }
    .brand-text strong { display: block; font-size: 19px; letter-spacing: 0.2px; }
    .brand-text span { display: block; margin-top: 4px; color: #a2d4ca; font-size: 12px; }
    .badge-row { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }
    .badge {
      display: inline-flex; align-items: center; border-radius: 999px; padding: 7px 11px;
      font-size: 12px; font-weight: 700; border: 1px solid rgba(132,220,193,0.28);
      background: rgba(10, 42, 39, 0.62); color: #ddfff5;
    }
    .logout-btn {
      border: 1px solid rgba(132,220,193,0.22);
      background: rgba(255,255,255,0.06);
      color: #dcfff6;
      min-height: 38px;
      border-radius: 12px;
      padding: 0 14px;
      cursor: pointer;
      font-weight: 700;
    }
    .hero { margin-top: 16px; display: grid; grid-template-columns: 1.25fr 0.95fr; gap: 16px; }
    .hero-card, .rail {
      background: var(--panel); border: 1px solid var(--panel-line); border-radius: 22px; padding: 24px;
      backdrop-filter: blur(10px); box-shadow: 0 18px 36px rgba(2, 12, 12, 0.28);
    }
    h1 { margin: 0; font-size: clamp(32px, 5vw, 48px); line-height: 1.04; max-width: 10ch; }
    .hero-card p, .rail p { color: #b9d7d0; line-height: 1.7; font-size: 15px; }
    .hero-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
    .btn, .btn-secondary {
      display: inline-flex; align-items: center; justify-content: center; min-height: 42px; padding: 0 16px;
      border-radius: 12px; text-decoration: none; font-weight: 700; font-size: 13px; border: 1px solid transparent;
    }
    .btn { color: #06271e; background: linear-gradient(180deg, #59e0b4 0%, #22b28a 100%); box-shadow: 0 10px 20px rgba(36,179,137,0.22); }
    .btn-secondary { color: #dcfff6; background: rgba(255,255,255,0.06); border-color: rgba(132,220,193,0.22); }
    .rail h2, .section-title { margin: 0 0 12px; font-size: 16px; letter-spacing: 0.3px; color: #f5fbf9; }
    .stat-list { display: grid; gap: 10px; margin-top: 16px; }
    .stat { border: 1px solid rgba(132,220,193,0.16); background: rgba(255,255,255,0.04); border-radius: 16px; padding: 14px; }
    .stat strong { display: block; font-size: 22px; color: #ffffff; }
    .stat span { display: block; margin-top: 4px; color: #9ecfc3; font-size: 12px; }
    .grid { margin-top: 18px; display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; }
    .card {
      background: var(--card-bg); border: 1px solid var(--card-line); border-radius: 18px; padding: 18px; color: var(--ink);
      box-shadow: 0 16px 30px rgba(2, 14, 13, 0.18); position: relative; overflow: hidden; min-height: 220px;
    }
    .card::before {
      content: ""; position: absolute; width: 120px; height: 120px; right: -34px; top: -34px; border-radius: 28px;
      background: linear-gradient(135deg, rgba(36,179,137,0.14), rgba(228,192,103,0.16)); transform: rotate(24deg);
    }
    .icon {
      width: 52px; height: 52px; border-radius: 14px; display: grid; place-items: center; font-size: 22px;
      margin-bottom: 14px; background: #e2faf1; border: 1px solid #b9ead8; color: var(--accent-2); position: relative; z-index: 1;
    }
    .card h3 { margin: 0 0 8px; font-size: 18px; position: relative; z-index: 1; }
    .card p { margin: 0; color: var(--muted); line-height: 1.62; font-size: 13px; position: relative; z-index: 1; }
    .card small { display: inline-block; margin-top: 12px; color: #0f7b60; font-weight: 700; position: relative; z-index: 1; }
    .warn {
      margin-top: 14px; border-radius: 14px; padding: 12px 14px;
      background: rgba(228, 192, 103, 0.16); border: 1px solid rgba(228, 192, 103, 0.22); color: #f4e3ae;
      font-size: 12px; line-height: 1.6;
    }
    @media (max-width: 860px) {
      .hero { grid-template-columns: 1fr; }
      .head { flex-direction: column; align-items: flex-start; }
      .badge-row { justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="head">
      <div class="brand">
        <div class="brand-mark">AF</div>
        <div class="brand-text">
          <strong id="userName">Yükleniyor...</strong>
          <span id="userMeta">Araç firması altyapısı aktif kullanıcı görünümü</span>
        </div>
      </div>
      <div class="badge-row">
        <span class="badge">Referans Sistem: 3000</span>
        <span class="badge">Altyapı Katmanı: 8002</span>
        <span id="themeBadge" class="badge">Renk Kimliği: Varsayılan</span>
        <button id="logoutBtn" class="logout-btn" type="button">Çıkış Yap</button>
      </div>
    </section>

    <section class="hero">
      <article class="hero-card">
        <h1>Ulaşım merkezli<br />ayrı yazılım algısı</h1>
        <p>
          Bu ekran, <strong>8000</strong> üzerindeki ana Creatro kurgusuna benzer bir kart ve panel
          mantığı taşır; ancak araç firması tarafında daha operasyonel, daha saha odaklı ve daha
          hızlı karar hissi veren ayrı bir renk ailesi kullanır.
        </p>
        <div class="hero-actions">
          <a class="btn" href="http://localhost:3000/modules-ui">3000 Referansını Aç</a>
          <a class="btn-secondary" href="/health">Sağlık Durumu</a>
        </div>
        <div class="warn">
          Bu panel artık ana modül sayfalarına bağlıdır. Planlama, operasyon ve yönetim modülü
          aynı omurga içinde adım adım doldurulacaktır.
        </div>
      </article>

      <aside class="rail">
        <h2>Odak Alanları</h2>
        <p>
          İlk fazda transfer operasyonunun bütün akışları burada toplanır. Sonraki fazlarda
          tedarikçi yönetimi, araç havuzu ve firma bazlı finans görünümü genişletilir.
        </p>
        <div class="stat-list">
          <div class="stat">
            <strong>1.</strong>
            <span>Ulaşım modülü ana çekirdek olarak korunur</span>
          </div>
          <div class="stat">
            <strong>2.</strong>
            <span>Operasyon ve muhasebe ulaşım kayıtlarıyla birlikte ilerler</span>
          </div>
          <div class="stat">
            <strong>3.</strong>
            <span>Yönetici alanı firma ayarları ve entegrasyonları toplar</span>
          </div>
        </div>
      </aside>
    </section>

    <h2 class="section-title">Modül Haritası</h2>
    <section class="grid">
      <article class="card">
        <div class="icon">P</div>
        <h3>Planlama</h3>
        <p>Bilet okuma, transfer listesi, No/Name slotları ve atama hazırlığı burada toplanır.</p>
        <small><a href="/transport" style="color:#0f7b60;text-decoration:none;font-weight:700;">Ekranı Aç</a></small>
      </article>
      <article class="card">
        <div class="icon">O</div>
        <h3>Operasyon</h3>
        <p>Saha teyitleri, ekip görevleri, karşılama akışları ve anlık durum takibi için hazırlanır.</p>
        <small><a href="/operations" style="color:#0f7b60;text-decoration:none;font-weight:700;">Ekranı Aç</a></small>
      </article>
      <article class="card">
        <div class="icon">Y</div>
        <h3>Yönetim Modülü</h3>
        <p>Kart merkezi, bildirim merkezi, muhasebe, yetki, entegrasyon ve firma ayarları burada toplanır.</p>
        <small><a href="/management" style="color:#0f7b60;text-decoration:none;font-weight:700;">Ekranı Aç</a></small>
      </article>
    </section>
  </div>

  <script>
    (function () {
      var API_BASE = 'http://localhost:3001';
      var TOKEN_KEY = 'fleet_access_token';
      var userName = document.getElementById('userName');
      var userMeta = document.getElementById('userMeta');
      var themeBadge = document.getElementById('themeBadge');
      var logoutBtn = document.getElementById('logoutBtn');

      function cssVar(name, value) {
        document.documentElement.style.setProperty(name, value);
      }

      function hexToRgb(hex) {
        var raw = String(hex || '').replace('#', '').trim();
        if (raw.length === 3) raw = raw.split('').map(function (x) { return x + x; }).join('');
        if (raw.length !== 6) return null;
        var num = parseInt(raw, 16);
        if (Number.isNaN(num)) return null;
        return {
          r: (num >> 16) & 255,
          g: (num >> 8) & 255,
          b: num & 255
        };
      }

      function rgba(hex, alpha) {
        var rgb = hexToRgb(hex);
        if (!rgb) return 'rgba(36,179,137,' + alpha + ')';
        return 'rgba(' + rgb.r + ',' + rgb.g + ',' + rgb.b + ',' + alpha + ')';
      }

      function applyTheme(payload) {
        var theme = payload && payload.theme ? payload.theme : null;
        var colors = theme && Array.isArray(theme.colors) ? theme.colors : [];
        var c1 = colors[0] || '#0d3934';
        var c2 = colors[1] || '#24b389';
        var c3 = colors[2] || '#e4c067';
        cssVar('--bg-1', c1);
        cssVar('--bg-2', c2);
        cssVar('--bg-3', '#0a2724');
        cssVar('--panel', rgba(c1, 0.82));
        cssVar('--panel-line', rgba(c2, 0.22));
        cssVar('--card-line', rgba(c2, 0.32));
        cssVar('--accent', c2);
        cssVar('--accent-2', c1);
        cssVar('--gold', c3);
        if (themeBadge) {
          themeBadge.textContent = 'Renk Kimliği: ' + String(theme && theme.label || 'Varsayılan');
        }
      }

      function logout() {
        localStorage.removeItem(TOKEN_KEY);
        window.location.href = '/';
      }

      logoutBtn.addEventListener('click', logout);

      async function loadMe() {
        var token = localStorage.getItem(TOKEN_KEY) || '';
        if (!token) {
          logout();
          return;
        }
        try {
          var res = await fetch(API_BASE + '/auth/me', {
            headers: { Authorization: 'Bearer ' + token }
          });
          if (!res.ok) {
            logout();
            return;
          }
          var me = await res.json();
          userName.textContent = String(me.username || me.user_code || 'Kullanıcı');
          var parts = [];
          if (me.role) parts.push('Rol: ' + me.role);
          if (me.tenant_name) parts.push('Firma: ' + me.tenant_name);
          if (me.active_project_name) parts.push('Proje: ' + me.active_project_name);
          userMeta.textContent = parts.join(' | ') || 'Araç firması altyapısı aktif kullanıcı görünümü';
          var themeRes = await fetch(API_BASE + '/supplier-theme-settings/current', {
            headers: { Authorization: 'Bearer ' + token }
          });
          if (themeRes.ok) {
            applyTheme(await themeRes.json());
          }
        } catch (err) {
          logout();
        }
      }

      loadMe();
    })();
  </script>
</body>
</html>
    """


def _build_module_page(title: str, subtitle: str, intro: str, cards: list[dict[str, str]]) -> str:
    cards_html = "".join(
        (
            "<article class=\"card\">"
            f"<div class=\"icon\">{card.get('icon', '•')}</div>"
            f"<h3>{card.get('title', '-')}</h3>"
            f"<p>{card.get('text', '')}</p>"
            f"<small><a href=\"{card.get('href', '#')}\" style=\"color:#0f7b60;text-decoration:none;font-weight:700;\">{card.get('action', 'Ekranı Aç')}</a></small>"
            "</article>"
        )
        for card in cards
    )
    return f"""
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --bg-1: #081d1d;
      --bg-2: #0d3934;
      --bg-3: #0a2724;
      --panel: rgba(7, 28, 27, 0.82);
      --panel-line: rgba(129, 223, 197, 0.22);
      --card-bg: linear-gradient(180deg, rgba(246, 255, 252, 0.97) 0%, rgba(232, 247, 242, 0.93) 100%);
      --card-line: rgba(132, 220, 193, 0.52);
      --ink: #12332d;
      --muted: #45655f;
      --accent: #24b389;
      --white: #f7fbfb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--white);
      background:
        radial-gradient(circle at right top, rgba(36,179,137,0.20), transparent 28%),
        linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 56%, var(--bg-3) 100%);
      background-attachment: fixed;
    }}
    .wrap {{ width: min(1180px, calc(100% - 32px)); margin: 22px auto 40px; }}
    .head, .panel {{
      background: var(--panel);
      border: 1px solid var(--panel-line);
      border-radius: 20px;
      backdrop-filter: blur(10px);
      box-shadow: 0 18px 36px rgba(2, 12, 12, 0.28);
    }}
    .head {{
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:12px;
      padding:14px 16px;
      margin-bottom:16px;
    }}
    .head a {{
      color:#dcfff6;
      text-decoration:none;
      border:1px solid rgba(132,220,193,0.22);
      background:rgba(255,255,255,0.06);
      min-height:38px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      border-radius:12px;
      padding:0 14px;
      font-weight:700;
      font-size:13px;
    }}
    .head strong {{ display:block; font-size:22px; }}
    .head span {{ color:#a2d4ca; font-size:12px; }}
    .panel {{ padding:24px; }}
    .intro {{
      margin:0 0 18px;
      color:#b9d7d0;
      line-height:1.7;
      font-size:14px;
      max-width:76ch;
    }}
    .grid {{
      display:grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap:14px;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-line);
      border-radius: 18px;
      padding: 18px;
      color: var(--ink);
      box-shadow: 0 16px 30px rgba(2, 14, 13, 0.18);
      min-height: 190px;
    }}
    .icon {{
      width:48px;
      height:48px;
      border-radius:14px;
      display:grid;
      place-items:center;
      margin-bottom:14px;
      font-size:20px;
      font-weight:800;
      background:#e2faf1;
      border:1px solid #b9ead8;
      color:#0f7b60;
    }}
    .card h3 {{ margin:0 0 8px; font-size:18px; }}
    .card p {{ margin:0; color:var(--muted); line-height:1.62; font-size:13px; }}
    .card small {{ display:inline-block; margin-top:12px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="head">
      <div>
        <strong>{title}</strong>
        <span>{subtitle}</span>
      </div>
      <a href="/panel">Panele Dön</a>
    </section>
    <section class="panel">
      <p class="intro">{intro}</p>
      <div class="grid">
        {cards_html}
      </div>
    </section>
  </div>
</body>
</html>
    """


@app.get("/transport", response_class=HTMLResponse)
def transport_page() -> str:
    return _build_module_page(
        "Planlama",
        "Transfer, bilet okuma, liste ve planlama merkezi",
        "Planlama modülü bilet okuma, OCR, parse, transfer üretimi, transfer listeleri ve No/Name plan slotları için ana iş akışıdır. Kart kayıtları burada tekrar açılmaz; Kart Merkezi yönetim modülü altında ayrı tutulur.",
        [
            {"icon": "B", "title": "Bilet Okuma", "text": "PDF, OCR ve parse ile uçuş verisinden transfer üretme hazırlık kayıtları burada tutulur.", "href": "/planning-ticket-reader"},
            {"icon": "T", "title": "Transfer Listeleri", "text": "Geliş, gidiş ve saha listeleri ile toplu planlama ekranları burada toplanır.", "href": "/planning-transfer-lists"},
            {"icon": "N", "title": "No/Name Planları", "text": "Geçici slot mantığı, toplu araç atama ve plan sorumlusu akışı burada tutulur.", "href": "/planning-no-name-slots"},
            {"icon": "K", "title": "Kart Merkezi", "text": "Araç, sürücü, karşılamacı ve firma kartlarına ihtiyaç olduğunda tek merkezden geçilir.", "href": "/card-center"},
        ],
    )


@app.get("/operations", response_class=HTMLResponse)
def operations_page() -> str:
    return _build_module_page(
        "Operasyon Modülü",
        "Saha akışı, takip ve görev yönetimi",
        "Operasyon modülü sürücü, karşılamacı ve saha durumlarını; uçuş etkileri, araç hareketi ve görev akışlarıyla birlikte yönetir. Bildirim merkezi ayrı kalır.",
        [
            {"icon": "T", "title": "Takip Kuralları", "text": "Uçuş ve araç takip entegrasyonları ile olay bazlı alarm yapısı burada genişletilir.", "href": "/operations", "action": "Hazırlanıyor"},
            {"icon": "G", "title": "Görev Akışları", "text": "Karşılamacı ve sürücü durum sıraları ile saha teyit akışları tek merkezde toplanır.", "href": "/operations", "action": "Hazırlanıyor"},
            {"icon": "L", "title": "Canlı Operasyon Listesi", "text": "Araç yola çıktı, karşıladı, aldı, bıraktı gibi canlı durum listeleri bu alanda toplanacaktır.", "href": "/operations", "action": "Hazırlanıyor"},
            {"icon": "B", "title": "Bildirim Merkezi", "text": "Bildirim tercihleri ve geçmişi ayrı ekranda kalır.", "href": "/notifications", "action": "Bildirim Merkezini Aç"},
        ],
    )


@app.get("/management", response_class=HTMLResponse)
def management_page() -> str:
    return _build_module_page(
        "Yönetim Modülü",
        "Kartlar, bildirim, muhasebe, kurallar ve entegrasyon merkezi",
        "Yönetim modülü kart merkezini, bildirim merkezini, muhasebe omurgasını, yetki ve sorumluluk yapısını ve ileride açılacak entegrasyon ayarlarını bir araya getirir.",
        [
            {"icon": "K", "title": "Kart Merkezi", "text": "Firma, araç, sürücü ve karşılamacı kartları tek merkezde toplanır.", "href": "/card-center"},
            {"icon": "B", "title": "Bildirim Merkezi", "text": "SMS, e-posta, WhatsApp ve sistem içi bildirim geçmişi burada toplanır.", "href": "/notifications"},
            {"icon": "M", "title": "Muhasebe", "text": "Hizmet kalemleri, masraf, ödeme ve sözleşme kuralları tek merkezde ilerler.", "href": "/accounting"},
            {"icon": "Y", "title": "Yetki ve Sorumluluk", "text": "Operatör, yönetici, yetkili ve diğer sıfatlar ile çoklu kişi yapısı burada genişletilir.", "href": "/management-responsibility"},
            {"icon": "E", "title": "Entegrasyonlar", "text": "Tema, takip ve ileride açılacak Arvento/uçuş bağlantıları bu bölümde toplanır.", "href": "/management-integrations"},
        ],
    )


@app.get("/card-center", response_class=HTMLResponse)
def card_center_page() -> str:
    return RedirectResponse(url="/management", status_code=307)


@app.get("/management-responsibility", response_class=HTMLResponse)
def management_responsibility_page() -> str:
    return _build_planning_list_page(
        {
            "title": "Yetki ve Sorumluluk",
            "subtitle": "Çoklu kişi, rol, kapsam ve geçerlilik alanı",
            "intro": "Bu ekran operatör, yönetici, yetkili ve diğer sıfatlarla tanımlanan kişileri proje, firma veya araç tipi bazında düzenlemek için kullanılır. Firma kartındaki kişi havuzu burada gerçek sorumluluk matrisine dönüşür.",
            "form_title": "Yeni Sorumluluk Kuralı",
            "add_label": "Kural Ekle",
            "update_label": "Kuralı Güncelle",
            "list_title": "Kayıtlı Sorumluluklar",
            "api_path": "/management-responsibility-rules",
            "fields": [
                {"id": "person_name", "label": "Kişi", "placeholder": "Ad soyad"},
                {"id": "role_name", "label": "Sıfat", "type": "select", "options": ["Operatör", "Yönetici", "Yetkili", "Muhasebe", "Sözleşme", "Evrak", "Diğer"]},
                {"id": "scope_type", "label": "Kapsam", "type": "select", "options": ["Firma", "Proje", "Araç Tipi", "Firma + Proje", "Proje + Araç Tipi"]},
                {"id": "scope_value", "label": "Kapsam Değeri", "placeholder": "Örn: Antalya Kongresi / VAN"},
                {"id": "start_date", "label": "Başlangıç Tarihi", "type": "date"},
                {"id": "end_date", "label": "Bitiş Tarihi", "type": "date"},
                {"id": "backup_person", "label": "Yedek Kişi", "placeholder": "Varsa yedek kişi"},
                {"id": "responsibility_note", "label": "Açıklama", "type": "textarea", "placeholder": "Görev sınırı, özel açıklama veya yönetici notu", "full": True},
            ],
            "required_fields": ["person_name", "role_name", "scope_type"],
            "primary_field": "person_name",
            "summary_fields": ["role_name", "scope_type", "scope_value", "start_date"],
            "summary_labels": {"role_name": "Sıfat", "scope_type": "Kapsam", "scope_value": "Değer", "start_date": "Başlangıç"},
            "tag_fields": ["backup_person", "end_date"],
            "empty_title": "Henüz sorumluluk kuralı yok",
            "empty_text": "İlk sorumluluk kaydını soldaki form ile ekleyin.",
            "required_error": "Kişi, sıfat ve kapsam zorunludur.",
            "save_success": "Sorumluluk listesi çekirdeğe kaydedildi.",
            "save_fail": "Sorumluluk listesi çekirdeğe kaydedilemedi.",
            "add_success": "Kural listeye eklendi. Kaydet ile çekirdeğe yazabilirsiniz.",
            "update_success": "Kural güncellendi. Kaydet ile çekirdeğe yazabilirsiniz.",
            "remove_success": "Kural listeden kaldırıldı. Kaydet ile çekirdeğe yazabilirsiniz.",
            "edit_notice": "Sorumluluk kaydı düzenleme için forma taşındı.",
        }
    )


@app.get("/management-integrations", response_class=HTMLResponse)
def management_integrations_page() -> str:
    return _build_planning_list_page(
        {
            "title": "Entegrasyonlar",
            "subtitle": "Tema, takip ve dış servis bağlantıları",
            "intro": "Bu ekran tema, uçuş takip, Arvento ve ileride açılacak diğer bağlantı ayarlarını tek merkezde toplar. İlk sürümde bağlantı profili oluşturulur; gerçek API anahtarları sonraki aşamada bağlanır.",
            "form_title": "Yeni Entegrasyon Kaydı",
            "add_label": "Entegrasyon Ekle",
            "update_label": "Entegrasyonu Güncelle",
            "list_title": "Kayıtlı Entegrasyonlar",
            "api_path": "/management-integrations",
            "fields": [
                {"id": "integration_name", "label": "Bağlantı Adı", "placeholder": "Örn: Antalya Arvento Hesabı"},
                {"id": "provider_name", "label": "Servis", "type": "select", "options": ["Tema", "FlightRadar", "FlightAware", "Arvento", "SMS", "WhatsApp", "Diğer"]},
                {"id": "company_scope", "label": "Firma / Proje Kapsamı", "placeholder": "Örn: Antalya Operasyon / Genel"},
                {"id": "status_name", "label": "Durum", "type": "select", "options": ["Taslak", "Bağlantı Hazır", "Aktif", "Pasif"]},
                {"id": "connection_code", "label": "Bağlantı Kodu", "placeholder": "Örn: ARVENTO-ANT-01"},
                {"id": "lookup_rule", "label": "Eşleştirme Kuralı", "placeholder": "Örn: Plaka bazlı"},
                {"id": "integration_note", "label": "Açıklama", "type": "textarea", "placeholder": "API bilgisi, yetki, kapsam veya özel not", "full": True},
            ],
            "required_fields": ["integration_name", "provider_name"],
            "primary_field": "integration_name",
            "summary_fields": ["provider_name", "company_scope", "status_name", "connection_code"],
            "summary_labels": {"provider_name": "Servis", "company_scope": "Kapsam", "status_name": "Durum", "connection_code": "Kod"},
            "tag_fields": ["lookup_rule"],
            "empty_title": "Henüz entegrasyon kaydı yok",
            "empty_text": "İlk entegrasyon kaydını soldaki form ile ekleyin.",
            "required_error": "Bağlantı adı ve servis zorunludur.",
            "save_success": "Entegrasyon listesi çekirdeğe kaydedildi.",
            "save_fail": "Entegrasyon listesi çekirdeğe kaydedilemedi.",
            "add_success": "Entegrasyon listeye eklendi. Kaydet ile çekirdeğe yazabilirsiniz.",
            "update_success": "Entegrasyon güncellendi. Kaydet ile çekirdeğe yazabilirsiniz.",
            "remove_success": "Entegrasyon listeden kaldırıldı. Kaydet ile çekirdeğe yazabilirsiniz.",
            "edit_notice": "Entegrasyon kaydı düzenleme için forma taşındı.",
        }
    )


def _build_planning_list_page(config: dict[str, object]) -> str:
    config_json = json.dumps(config, ensure_ascii=False)
    return f"""
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{config['title']}</title>
  <style>
    :root {{
      --bg-1: #081d1d;
      --bg-2: #0d3934;
      --bg-3: #0a2724;
      --panel: rgba(7, 28, 27, 0.82);
      --panel-line: rgba(129, 223, 197, 0.22);
      --card-bg: linear-gradient(180deg, rgba(246, 255, 252, 0.97) 0%, rgba(232, 247, 242, 0.93) 100%);
      --card-line: rgba(132, 220, 193, 0.52);
      --ink: #12332d;
      --muted: #45655f;
      --accent: #24b389;
      --white: #f7fbfb;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family:"Segoe UI", Arial, sans-serif; color:var(--white); background:radial-gradient(circle at right top, rgba(36,179,137,0.20), transparent 28%), linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 56%, var(--bg-3) 100%); background-attachment:fixed; }}
    .wrap {{ width:min(1240px, calc(100% - 32px)); margin:22px auto 40px; }}
    .head, .panel {{ background:var(--panel); border:1px solid var(--panel-line); border-radius:20px; backdrop-filter:blur(10px); box-shadow:0 18px 36px rgba(2,12,12,0.28); }}
    .head {{ display:flex; justify-content:space-between; align-items:center; gap:12px; padding:14px 16px; margin-bottom:16px; }}
    .head a {{ color:#dcfff6; text-decoration:none; border:1px solid rgba(132,220,193,0.22); background:rgba(255,255,255,0.06); min-height:38px; display:inline-flex; align-items:center; justify-content:center; border-radius:12px; padding:0 14px; font-weight:700; font-size:13px; }}
    .head strong {{ display:block; font-size:22px; }}
    .head span {{ color:#a2d4ca; font-size:12px; }}
    .panel {{ padding:24px; }}
    .toolbar {{ display:flex; justify-content:space-between; gap:12px; align-items:flex-start; flex-wrap:wrap; margin-bottom:18px; }}
    .toolbar p {{ margin:0; color:#b9d7d0; line-height:1.65; font-size:13px; max-width:70ch; }}
    .action-row {{ display:flex; gap:10px; flex-wrap:wrap; }}
    .action-btn {{ min-height:40px; border-radius:12px; padding:0 14px; border:1px solid rgba(132,220,193,0.22); background:rgba(255,255,255,0.06); color:#dcfff6; font-weight:700; cursor:pointer; }}
    .action-btn.primary {{ color:#06271e; background:linear-gradient(180deg, #59e0b4 0%, #22b28a 100%); border-color:transparent; box-shadow:0 10px 20px rgba(36,179,137,0.18); }}
    .layout {{ display:grid; grid-template-columns:420px 1fr; gap:16px; }}
    .card {{ background:var(--card-bg); border:1px solid var(--card-line); border-radius:18px; padding:18px; color:var(--ink); box-shadow:0 16px 30px rgba(2,14,13,0.18); }}
    .card h3 {{ margin:0 0 12px; font-size:18px; }}
    .field-grid {{ display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:12px; }}
    .field {{ display:grid; gap:7px; }}
    .field.full {{ grid-column:1 / -1; }}
    .field label {{ font-size:12px; font-weight:800; color:#0f7b60; }}
    .field input, .field select, .field textarea {{ width:100%; min-height:42px; border-radius:14px; border:1px solid rgba(15,123,96,0.16); background:rgba(255,255,255,0.78); color:var(--ink); padding:10px 12px; outline:none; font-family:inherit; font-size:13px; }}
    .field textarea {{ min-height:90px; resize:vertical; }}
    .list {{ display:grid; gap:12px; }}
    .item {{ border:1px solid rgba(15,123,96,0.22); border-radius:18px; padding:14px; background:rgba(255,255,255,0.78); box-shadow: inset 0 1px 0 rgba(255,255,255,0.42); }}
    .item-head {{ display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }}
    .item strong {{ display:block; font-size:15px; margin-bottom:6px; }}
    .item span {{ display:block; color:var(--muted); font-size:12px; line-height:1.55; }}
    .item-tags {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }}
    .item-tags i {{ display:inline-flex; align-items:center; min-height:28px; padding:0 10px; border-radius:999px; background:rgba(36,179,137,0.12); border:1px solid rgba(36,179,137,0.18); color:#0f7b60; font-style:normal; font-size:11px; font-weight:800; }}
    .item-actions {{ display:flex; gap:8px; flex-wrap:wrap; }}
    .item-btn {{ min-height:34px; border-radius:11px; padding:0 12px; border:none; font-weight:800; font-size:12px; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; }}
    .item-btn.edit {{ background:linear-gradient(180deg, #d9f6ee 0%, #b8eadc 100%); color:#0e5c49; border:1px solid rgba(14,92,73,0.18); }}
    .item-btn.remove {{ background:linear-gradient(180deg, #ffe3e0 0%, #ffc8c0 100%); color:#8f2418; border:1px solid rgba(143,36,24,0.16); }}
    .status {{ margin-top:16px; border-radius:14px; padding:12px 14px; background:rgba(36,179,137,0.12); border:1px solid rgba(36,179,137,0.20); color:#d7fbef; font-size:12px; line-height:1.6; display:none; }}
    .status.show {{ display:block; }}
    @media (max-width: 960px) {{ .layout, .field-grid {{ grid-template-columns:1fr; }} .item-head {{ flex-direction:column; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="head">
      <div>
        <strong>{config['title']}</strong>
        <span>{config['subtitle']}</span>
      </div>
      <a href="/transport">Planlamaya Dön</a>
    </section>
    <section class="panel">
      <div class="toolbar">
        <p>{config['intro']}</p>
        <div class="action-row" id="toolbarActions">
          <button id="saveBtn" type="button" class="action-btn primary">Listeyi Kaydet</button>
          <button id="clearBtn" type="button" class="action-btn">Formu Temizle</button>
        </div>
      </div>
      <div class="layout">
        <article class="card">
          <h3>{config['form_title']}</h3>
          <div id="fieldGrid" class="field-grid"></div>
          <div class="action-row" style="margin-top:14px;">
            <button id="addBtn" type="button" class="action-btn primary">{config['add_label']}</button>
          </div>
        </article>
        <article class="card">
          <h3>{config['list_title']}</h3>
          <div id="listNode" class="list"></div>
          <div id="statusNode" class="status"></div>
        </article>
      </div>
    </section>
  </div>
  <script>
    (function () {{
      var config = {config_json};
      var API_BASE = 'http://localhost:3001';
      var TOKEN_KEYS = ['fleet_access_token', 'platform_core_token', 'agency_access_token'];
      var fieldGrid = document.getElementById('fieldGrid');
      var saveBtn = document.getElementById('saveBtn');
      var clearBtn = document.getElementById('clearBtn');
      var toolbarActions = document.getElementById('toolbarActions');
      var addBtn = document.getElementById('addBtn');
      var listNode = document.getElementById('listNode');
      var statusNode = document.getElementById('statusNode');
      var fields = {{}};
      var items = [];
      var editingIndex = -1;

      function readToken() {{
        for (var i = 0; i < TOKEN_KEYS.length; i += 1) {{
          var value = localStorage.getItem(TOKEN_KEYS[i]) || '';
          if (value) return value;
        }}
        return '';
      }}

      async function ensureToken() {{
        var token = readToken();
        if (token) return token;
        var res = await fetch(API_BASE + '/auth/login', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ username: 'CreaTRo', password: 'Micetro25+.' }})
        }});
        var data = {{}};
        try {{ data = await res.json(); }} catch (_) {{}}
        if (!res.ok || !data.access_token) throw new Error(data.detail || 'Oturum yenilenemedi.');
        localStorage.setItem('fleet_access_token', String(data.access_token));
        localStorage.setItem('platform_core_token', String(data.access_token));
        localStorage.setItem('agency_access_token', String(data.access_token));
        return String(data.access_token);
      }}

      function escapeHtml(value) {{
        return String(value || '').replace(/[&<>"]/g, function (char) {{
          return ({{ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }})[char] || char;
        }});
      }}

      function showStatus(message) {{
        statusNode.textContent = message;
        statusNode.classList.add('show');
        window.clearTimeout(window.__planningStatusTimer);
        window.__planningStatusTimer = window.setTimeout(function () {{ statusNode.classList.remove('show'); }}, 2600);
      }}

      function renderFields() {{
        fieldGrid.innerHTML = config.fields.map(function (field) {{
          var type = field.type || 'text';
          var isFull = field.full ? ' full' : '';
          if (type === 'textarea') {{
            return '<div class="field' + isFull + '"><label for="' + field.id + '">' + field.label + '</label><textarea id="' + field.id + '" placeholder="' + (field.placeholder || '') + '"></textarea></div>';
          }}
          if (type === 'select') {{
            return '<div class="field' + isFull + '"><label for="' + field.id + '">' + field.label + '</label><select id="' + field.id + '">' + (field.options || []).map(function (option) {{ return '<option value="' + option + '">' + option + '</option>'; }}).join('') + '</select></div>';
          }}
          return '<div class="field' + isFull + '"><label for="' + field.id + '">' + field.label + '</label><input id="' + field.id + '" type="' + type + '" placeholder="' + (field.placeholder || '') + '" /></div>';
        }}).join('');
        config.fields.forEach(function (field) {{ fields[field.id] = document.getElementById(field.id); }});
      }}

      function renderToolbarActions() {{
        var extras = Array.isArray(config.extra_actions) ? config.extra_actions : [];
        extras.forEach(function (action) {{
          if (!action || !action.id || !action.label) return;
          if (document.getElementById(action.id)) return;
          var button = document.createElement('button');
          button.type = 'button';
          button.id = action.id;
          button.className = 'action-btn' + (action.primary ? ' primary' : '');
          button.textContent = action.label;
          toolbarActions.insertBefore(button, clearBtn);
        }});
      }}

      function clearForm() {{
        config.fields.forEach(function (field) {{
          if (!fields[field.id]) return;
          if (field.type === 'select' && field.options && field.options.length) fields[field.id].value = field.options[0];
          else fields[field.id].value = '';
        }});
        editingIndex = -1;
        addBtn.textContent = config.add_label;
      }}

      function collectForm() {{
        var item = {{}};
        config.fields.forEach(function (field) {{
          item[field.id] = (fields[field.id] && fields[field.id].value ? fields[field.id].value : '').trim();
        }});
        return item;
      }}

      function fillForm(item, index) {{
        config.fields.forEach(function (field) {{
          if (fields[field.id]) fields[field.id].value = item[field.id] || '';
        }});
        editingIndex = index;
        addBtn.textContent = config.update_label;
      }}

      function renderList() {{
        if (!items.length) {{
          listNode.innerHTML = '<div class="item"><strong>' + config.empty_title + '</strong><span>' + config.empty_text + '</span></div>';
          return;
        }}
        listNode.innerHTML = items.map(function (item, index) {{
          var title = item[config.primary_field] || '-';
          var lines = (config.summary_fields || []).map(function (key) {{
            return config.summary_labels[key] + ': ' + (item[key] || '-');
          }});
          var tags = (config.tag_fields || []).map(function (key) {{ return item[key] || ''; }}).filter(Boolean);
          return ''
            + '<div class="item">'
            +   '<div class="item-head">'
            +     '<div><strong>' + escapeHtml(title) + '</strong>' + lines.map(function (line) {{ return '<span>' + escapeHtml(line) + '</span>'; }}).join('') + '</div>'
            +     '<div class="item-actions"><button type="button" class="item-btn edit" data-edit-index="' + index + '">Düzenle</button><button type="button" class="item-btn remove" data-remove-index="' + index + '">Kaldır</button></div>'
            +   '</div>'
            +   '<div class="item-tags">' + tags.map(function (tag) {{ return '<i>' + escapeHtml(tag) + '</i>'; }}).join('') + '</div>'
            + '</div>';
        }}).join('');
      }}

      async function loadItems() {{
        var token = '';
        try {{
          token = await ensureToken();
          var res = await fetch(API_BASE + config.api_path, {{ headers: {{ Authorization: 'Bearer ' + token }} }});
          if (!res.ok) return;
          var data = await res.json();
          items = Array.isArray(data.items) ? data.items : [];
          renderList();
        }} catch (_) {{}}
      }}

      async function saveItems() {{
        var token = '';
        try {{
          token = await ensureToken();
          var res = await fetch(API_BASE + config.api_path, {{
            method: 'PUT',
            headers: {{ Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ items: items }})
          }});
          if (!res.ok) {{ showStatus(config.save_fail); return; }}
          showStatus(config.save_success);
        }} catch (_) {{
          showStatus(config.save_fail);
        }}
      }}

      async function importFromTickets() {{
        var token = readToken();
        if (!token) {{ showStatus('Oturum bulunamadı. Yeniden giriş yapın.'); return; }}
        var projectCity = fields.project_city ? String(fields.project_city.value || '').trim() : '';
        var button = document.getElementById('importTicketsBtn');
        if (button) {{
          button.disabled = true;
          button.textContent = 'Biletlerden aktarılıyor...';
        }}
        try {{
          var res = await fetch(API_BASE + '/planning-transfer-lists/import-from-tickets', {{
            method: 'POST',
            headers: {{ Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ project_city: projectCity }})
          }});
          var data = {{}};
          try {{ data = await res.json(); }} catch (_) {{}}
          if (!res.ok) {{
            showStatus(data.detail || 'Bilet kayıtları aktarılamadı.');
            return;
          }}
          items = Array.isArray(data.items) ? data.items : [];
          renderList();
          showStatus((data.imported_count || 0) + ' bilet kaydı transfer listesine aktarıldı.');
        }} catch (_) {{
          showStatus('Bilet kayıtları aktarılamadı.');
        }} finally {{
          if (button) {{
            button.disabled = false;
            button.textContent = 'Biletlerden Aktar';
          }}
        }}
      }}

      addBtn.addEventListener('click', function () {{
        var item = collectForm();
        var required = (config.required_fields || []).every(function (key) {{ return String(item[key] || '').trim(); }});
        if (!required) {{ showStatus(config.required_error); return; }}
        if (editingIndex >= 0) items.splice(editingIndex, 1, item);
        else items.unshift(item);
        renderList();
        clearForm();
        showStatus(editingIndex >= 0 ? config.update_success : config.add_success);
      }});

      saveBtn.addEventListener('click', saveItems);
      clearBtn.addEventListener('click', function () {{ clearForm(); showStatus('Form temizlendi.'); }});
      if (config.api_path === '/planning-transfer-lists') {{
        document.addEventListener('click', function (event) {{
          var importBtn = event.target.closest('#importTicketsBtn');
          if (!importBtn) return;
          importFromTickets();
        }});
      }}
      listNode.addEventListener('click', function (event) {{
        var editBtn = event.target.closest('[data-edit-index]');
        if (editBtn) {{
          var editIndex = parseInt(editBtn.getAttribute('data-edit-index'), 10);
          if (!Number.isNaN(editIndex) && items[editIndex]) {{
            fillForm(items[editIndex], editIndex);
            showStatus(config.edit_notice);
          }}
          return;
        }}
        var removeBtn = event.target.closest('[data-remove-index]');
        if (!removeBtn) return;
        var removeIndex = parseInt(removeBtn.getAttribute('data-remove-index'), 10);
        if (Number.isNaN(removeIndex)) return;
        items.splice(removeIndex, 1);
        renderList();
        showStatus(config.remove_success);
      }});

      renderFields();
      renderToolbarActions();
      clearForm();
      renderList();
      loadItems();
    }})();
  </script>
</body>
</html>
    """


@app.get("/planning-ticket-reader", response_class=HTMLResponse)
def planning_ticket_reader_page() -> str:
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Bilet Okuma</title>
  <style>
    :root {
      --bg-1: #081d1d;
      --bg-2: #0d3934;
      --bg-3: #0a2724;
      --panel: rgba(7, 28, 27, 0.82);
      --panel-line: rgba(129, 223, 197, 0.22);
      --card-bg: linear-gradient(180deg, rgba(246, 255, 252, 0.97) 0%, rgba(232, 247, 242, 0.93) 100%);
      --card-line: rgba(132, 220, 193, 0.52);
      --ink: #12332d;
      --muted: #45655f;
      --accent: #24b389;
      --accent-2: #0e8d6b;
      --danger: #9c2742;
      --white: #f7fbfb;
      --warn: #b67817;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--white);
      background:
        radial-gradient(circle at right top, rgba(36,179,137,0.20), transparent 28%),
        linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 56%, var(--bg-3) 100%);
      background-attachment: fixed;
    }
    .wrap { width: min(1580px, calc(100% - 32px)); margin: 22px auto 40px; }
    .head, .panel {
      background: var(--panel);
      border: 1px solid var(--panel-line);
      border-radius: 20px;
      backdrop-filter: blur(10px);
      box-shadow: 0 18px 36px rgba(2, 12, 12, 0.28);
    }
    .head {
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:12px;
      padding:14px 16px;
      margin-bottom:16px;
    }
    .head a {
      color:#dcfff6;
      text-decoration:none;
      border:1px solid rgba(132,220,193,0.22);
      background:rgba(255,255,255,0.06);
      min-height:38px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      border-radius:12px;
      padding:0 14px;
      font-weight:700;
      font-size:13px;
    }
    .head strong { display:block; font-size:22px; }
    .head span { color:#a2d4ca; font-size:12px; }
    .panel { padding:24px; }
    .hero {
      display:grid;
      grid-template-columns: 1.3fr 0.7fr;
      gap:16px;
      margin-bottom:16px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-line);
      border-radius: 18px;
      padding: 18px;
      color: var(--ink);
      box-shadow: 0 16px 30px rgba(2, 14, 13, 0.18);
    }
    .card h3 { margin:0 0 10px; font-size:18px; }
    .card p { margin:0; color:var(--muted); line-height:1.65; font-size:13px; }
    .dropzone {
      margin-top:14px;
      border:2px dashed rgba(36,179,137,0.38);
      border-radius:18px;
      padding:24px;
      background:linear-gradient(180deg, rgba(255,255,255,0.84), rgba(240,251,247,0.92));
      text-align:center;
      transition:all .18s ease;
      cursor:pointer;
    }
    .dropzone.dragover {
      border-color: var(--accent);
      background:linear-gradient(180deg, rgba(230,252,244,0.98), rgba(214,247,236,0.98));
      transform: translateY(-1px);
    }
    .dropzone strong { display:block; color:#0f7b60; font-size:15px; margin-bottom:6px; }
    .dropzone span { display:block; color:var(--muted); font-size:12px; line-height:1.6; }
    .dropzone .mini {
      display:inline-flex;
      margin-top:12px;
      min-height:34px;
      align-items:center;
      justify-content:center;
      padding:0 12px;
      border-radius:999px;
      background:rgba(36,179,137,0.12);
      border:1px solid rgba(36,179,137,0.18);
      color:#0f7b60;
      font-size:11px;
      font-weight:800;
    }
    .picker { display:none; }
    .btn-row { display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }
    .action-btn {
      min-height:40px;
      border-radius:12px;
      padding:0 14px;
      border:1px solid rgba(132,220,193,0.22);
      background:rgba(255,255,255,0.06);
      color:#dcfff6;
      font-weight:700;
      cursor:pointer;
    }
    .action-btn.primary {
      color:#06271e;
      background: linear-gradient(180deg, #59e0b4 0%, #22b28a 100%);
      border-color: transparent;
      box-shadow: 0 10px 20px rgba(36,179,137,0.18);
    }
    .action-btn.danger {
      background: rgba(156,39,66,0.12);
      border-color: rgba(156,39,66,0.22);
      color: #ffe5ea;
    }
    .chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }
    .chip {
      display:inline-flex;
      align-items:center;
      min-height:30px;
      padding:0 10px;
      border-radius:999px;
      background:rgba(36,179,137,0.12);
      border:1px solid rgba(36,179,137,0.18);
      color:#0f7b60;
      font-size:11px;
      font-weight:800;
    }
    .layout { display:grid; grid-template-columns: 1fr; gap:16px; }
    .field-grid { display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:12px; }
    .field { display:grid; gap:7px; }
    .field.full { grid-column:1 / -1; }
    .field label { font-size:12px; font-weight:800; color:#0f7b60; }
    .field input, .field select, .field textarea {
      width:100%;
      min-height:42px;
      border-radius:14px;
      border:1px solid rgba(15,123,96,0.16);
      background:rgba(255,255,255,0.78);
      color:var(--ink);
      padding:10px 12px;
      outline:none;
      font-family:inherit;
      font-size:13px;
    }
    .field textarea { min-height:88px; resize:vertical; }
    .muted-note { margin-top:10px; color:var(--muted); font-size:12px; line-height:1.6; }
    .summary-list { display:grid; gap:10px; margin-top:14px; }
    .summary-item {
      border:1px solid rgba(15,123,96,0.16);
      border-radius:16px;
      padding:12px 14px;
      background:rgba(255,255,255,0.78);
      color:var(--ink);
    }
    .summary-item strong { display:block; margin-bottom:5px; color:#0f7b60; }
    .summary-item span { display:block; color:var(--muted); font-size:12px; line-height:1.55; }
    .progress-board {
      display:grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap:10px;
      margin-top:14px;
    }
    .progress-card {
      border:1px solid rgba(15,123,96,0.16);
      border-radius:16px;
      padding:12px 14px;
      background:rgba(255,255,255,0.78);
      color:var(--ink);
    }
    .progress-card.clickable {
      cursor:pointer;
      transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease;
    }
    .progress-card.clickable:hover {
      transform:translateY(-1px);
      border-color:rgba(36,179,137,0.28);
      box-shadow:0 10px 20px rgba(10, 38, 33, 0.10);
    }
    .progress-card strong {
      display:block;
      font-size:20px;
      color:#0f7b60;
      margin-bottom:4px;
    }
    .progress-card span {
      display:block;
      color:var(--muted);
      font-size:11px;
      line-height:1.45;
    }
    .progress-card.error {
      border-color: rgba(156,39,66,0.24);
      background: linear-gradient(180deg, rgba(255,232,236,0.92) 0%, rgba(255,214,221,0.86) 100%);
    }
    .progress-card.error strong { color:#9c2742; }
    .progress-card.error span { color:#7f3040; }
    .progress-line {
      margin-top:12px;
      width:100%;
      height:10px;
      border-radius:999px;
      background:rgba(15,123,96,0.10);
      overflow:hidden;
      border:1px solid rgba(15,123,96,0.10);
    }
    .progress-fill {
      height:100%;
      width:0%;
      background:linear-gradient(90deg, #23b38b 0%, #7be0be 100%);
      transition:width .25s ease;
    }
    .table-wrap {
      border:1px solid rgba(15,123,96,0.16);
      border-radius:18px;
      overflow:hidden;
      background:rgba(255,255,255,0.82);
    }
    table { width:100%; border-collapse:collapse; font-size:12px; }
    th, td { padding:10px 12px; border-bottom:1px solid rgba(15,123,96,0.12); text-align:left; vertical-align:top; color:var(--ink); }
    th { background:rgba(226,247,240,0.84); color:#0f7b60; font-size:11px; letter-spacing:0.18px; text-transform:uppercase; }
    tr:last-child td { border-bottom:none; }
    .row-main { font-weight:700; color:#11322d; }
    .row-sub { display:block; margin-top:4px; color:var(--muted); font-size:11px; line-height:1.45; }
    .row-actions { display:flex; gap:8px; justify-content:flex-end; }
    .mini-btn {
      min-height:32px;
      border-radius:10px;
      padding:0 10px;
      border:1px solid rgba(15,123,96,0.16);
      background:rgba(255,255,255,0.84);
      color:var(--ink);
      font-size:12px;
      font-weight:800;
      cursor:pointer;
    }
    .mini-btn.remove {
      color:#9c2742;
      border-color:rgba(156,39,66,0.20);
      background:rgba(156,39,66,0.08);
    }
    .status-chip {
      display:inline-flex;
      align-items:center;
      min-height:28px;
      padding:0 10px;
      border-radius:999px;
      font-size:11px;
      font-weight:800;
      border:1px solid transparent;
      white-space:nowrap;
    }
    .status-chip.ready { color:#0e6a52; background:rgba(36,179,137,0.12); border-color:rgba(36,179,137,0.18); }
    .status-chip.waiting { color:#8a5e14; background:rgba(228,192,103,0.14); border-color:rgba(228,192,103,0.24); }
    .status-chip.error { color:#9c2742; background:rgba(156,39,66,0.10); border-color:rgba(156,39,66,0.20); }
    .status-chip.info { color:#245d8f; background:rgba(45,127,201,0.10); border-color:rgba(45,127,201,0.20); }
    .status {
      margin-top:16px;
      border-radius:14px;
      padding:12px 14px;
      background:rgba(36, 179, 137, 0.12);
      border:1px solid rgba(36, 179, 137, 0.20);
      color:#d7fbef;
      font-size:12px;
      line-height:1.6;
      display:none;
    }
    .status.show { display:block; }
    .hidden { display:none; }
    .detail-modal {
      position:fixed;
      inset:0;
      background:rgba(2, 14, 13, 0.56);
      backdrop-filter:blur(4px);
      display:none;
      align-items:center;
      justify-content:center;
      padding:20px;
      z-index:90;
    }
    .detail-modal.show { display:flex; }
    .detail-dialog {
      width:min(920px, 100%);
      max-height:min(82vh, 860px);
      overflow:auto;
      border-radius:22px;
      background:linear-gradient(180deg, rgba(248,255,252,0.98) 0%, rgba(233,247,242,0.97) 100%);
      border:1px solid rgba(132,220,193,0.38);
      box-shadow:0 28px 60px rgba(2, 12, 12, 0.32);
      color:var(--ink);
      padding:20px;
    }
    .detail-head {
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:12px;
      margin-bottom:14px;
    }
    .detail-head h3 {
      margin:0;
      font-size:20px;
      color:#0f7b60;
    }
    .detail-head p {
      margin:4px 0 0;
      color:var(--muted);
      font-size:12px;
      line-height:1.5;
    }
    .detail-close {
      min-height:38px;
      border-radius:12px;
      padding:0 14px;
      border:1px solid rgba(15,123,96,0.16);
      background:#ffffff;
      color:var(--ink);
      font-weight:800;
      cursor:pointer;
    }
    .detail-list {
      display:grid;
      gap:10px;
    }
    .detail-item {
      border:1px solid rgba(15,123,96,0.16);
      border-radius:16px;
      background:rgba(255,255,255,0.86);
      padding:12px 14px;
    }
    .detail-item strong {
      display:block;
      margin-bottom:4px;
      color:#10342f;
      font-size:14px;
    }
    .detail-item span {
      display:block;
      color:var(--muted);
      font-size:12px;
      line-height:1.55;
    }
    .detail-empty {
      border:1px dashed rgba(15,123,96,0.18);
      border-radius:16px;
      padding:16px;
      color:var(--muted);
      background:rgba(255,255,255,0.72);
      font-size:12px;
    }
    @media (max-width: 920px) {
      .hero, .layout { grid-template-columns:1fr; }
      .field-grid { grid-template-columns:1fr; }
      .progress-board { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .table-wrap { overflow:auto; }
      table { min-width:1480px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="head">
      <div>
        <strong>Bilet Okuma</strong>
        <span>8000 referanslı yükleme mantığı, daha sade planlama akışı</span>
      </div>
      <a href="/transport">Planlamaya Dön</a>
    </section>

    <section class="panel">
      <div class="hero">
        <article class="card">
          <h3>Dosya Yükleme Alanı</h3>
          <p>
            PDF, ZIP, JPG, JPEG ve PNG dosyaları sürükleyip bırakılabilir. Bu sürümde yüklenen dosyalar
            doğrudan ortak parser motoruna gider ve kayıtlı bilet listesine düşer. Elle yeni bilet kaydı açılmaz;
            yalnızca yüklenen kayıtlar daha sonra düzenlenir.
          </p>
          <div id="dropzone" class="dropzone" tabindex="0">
            <strong>Dosyaları buraya sürükleyip bırakın</strong>
            <span>veya tıklayıp dosya seçin. Desteklenen türler: PDF, ZIP, JPG, JPEG, PNG</span>
            <span class="mini">Sürükle - bırak, toplu seç, sıraya al</span>
          </div>
          <input id="picker" class="picker" type="file" multiple accept=".pdf,.zip,.jpg,.jpeg,.png" />
          <div class="btn-row">
            <button id="addFilesBtn" type="button" class="action-btn primary">Dosyaları Listeye Al</button>
            <button id="clearFilesBtn" type="button" class="action-btn danger">Seçimi Temizle</button>
            <button id="refreshStatusBtn" type="button" class="action-btn">Durumu Yenile</button>
            <button id="saveListBtn" type="button" class="action-btn">Listeyi Kaydet</button>
          </div>
          <div id="selectionSummary" class="muted-note">Henüz dosya seçilmedi.</div>
          <div id="selectedChips" class="chips"></div>
          <div class="progress-board">
            <div class="progress-card"><strong id="progressTotal">0</strong><span>Toplam Dosya</span></div>
            <div id="progressDoneCard" class="progress-card clickable"><strong id="progressDone">0</strong><span>İşlenen</span></div>
            <div id="progressWaitingCard" class="progress-card clickable"><strong id="progressWaiting">0</strong><span>Kalan</span></div>
            <div id="progressErrorCard" class="progress-card clickable"><strong id="progressError">0</strong><span>Hata</span></div>
            <div class="progress-card"><strong id="progressEta">-</strong><span>Tahmini Süre</span></div>
          </div>
          <div class="progress-line"><div id="progressFill" class="progress-fill"></div></div>
        </article>

        <article class="card">
          <h3>Akış Özeti</h3>
          <p>Bu ekran artık tek akışla çalışır:</p>
          <div class="summary-list">
            <div class="summary-item">
              <strong>1. Yükle</strong>
              <span>Dosya doğrudan ortak parser kuyruğuna girer.</span>
            </div>
            <div class="summary-item">
              <strong>2. Parse Al</strong>
              <span>Uçuş, rota, yolcu ve saat bilgileri 8000 referans mantığıyla çözümlenir.</span>
            </div>
            <div class="summary-item">
              <strong>3. Düzenle ve Aktar</strong>
              <span>Kayıtlı biletler tek tek düzenlenir ve transfer listesine aktarılır.</span>
            </div>
          </div>
          <div class="muted-note">Gidişte <strong>Nereye</strong>, rota kalkış havalimanından; gelişte <strong>Nereden</strong>, rota iniş havalimanından doldurulur.</div>
        </article>
      </div>

      <div class="layout">
        <article id="editorCard" class="card hidden">
          <h3>Bilet Kaydı Düzenle</h3>
          <div class="field-grid">
            <div class="field">
              <label for="original_filename">Dosya Adı</label>
              <input id="original_filename" type="text" placeholder="Seçilen dosyadan otomatik gelir" />
            </div>
            <div class="field">
              <label for="file_kind">Dosya Türü</label>
              <input id="file_kind" type="text" placeholder="PDF / ZIP / JPG..." />
            </div>
            <div class="field">
              <label for="pnr_code">PNR / Rezervasyon Kodu</label>
              <input id="pnr_code" type="text" placeholder="Örn: TK7A4P" />
            </div>
            <div class="field">
              <label for="passenger_name">İsim Soyisim</label>
              <input id="passenger_name" type="text" placeholder="Ad soyad" />
            </div>
            <div class="field">
              <label for="flight_no">Uçuş No</label>
              <input id="flight_no" type="text" placeholder="Örn: TK2410" />
            </div>
            <div class="field">
              <label for="direction_type">Yön</label>
              <select id="direction_type">
                <option value="Geliş">Geliş</option>
                <option value="Gidiş">Gidiş</option>
              </select>
            </div>
            <div class="field">
              <label for="flight_date">Uçuş Tarihi</label>
              <input id="flight_date" type="date" />
            </div>
            <div class="field">
              <label for="estimated_time">Tahmini Saat</label>
              <input id="estimated_time" type="time" />
            </div>
            <div class="field full">
              <label for="route_text">Rota</label>
              <input id="route_text" type="text" placeholder="Örn: IST > ADB" />
            </div>
            <div class="field">
              <label for="departure_time">Kalkış Saati</label>
              <input id="departure_time" type="time" />
            </div>
            <div class="field">
              <label for="arrival_time">İniş Saati</label>
              <input id="arrival_time" type="time" />
            </div>
            <div class="field">
              <label for="from_text">Nereden</label>
              <input id="from_text" type="text" placeholder="Transfer başlangıç noktası" />
            </div>
            <div class="field">
              <label for="to_text">Nereye</label>
              <input id="to_text" type="text" placeholder="Transfer varış noktası" />
            </div>
            <div class="field">
              <label for="transfer_time">Transfer Saati</label>
              <input id="transfer_time" type="time" />
            </div>
            <div class="field">
              <label for="vehicle_info">Araç Bilgisi</label>
              <input id="vehicle_info" type="text" placeholder="Van, Midi, Sprinter, Bus, Sedan..." />
            </div>
            <div class="field full">
              <label for="parse_note">Notlar</label>
              <textarea id="parse_note" placeholder="Liste yanında tutulacak notlar"></textarea>
            </div>
          </div>
          <div class="btn-row">
            <button id="applyEditBtn" type="button" class="action-btn primary">Değişikliği Uygula</button>
            <button id="cancelEditBtn" type="button" class="action-btn">Düzenlemeyi Kapat</button>
          </div>
        </article>

        <article class="card">
          <h3>Kayıtlı Biletler</h3>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Dosya</th>
                  <th>Tarih</th>
                  <th>İsim Soyisim</th>
                  <th>Rota</th>
                  <th>Uçuş Kodu</th>
                  <th>Kalkış</th>
                  <th>İniş</th>
                  <th>Nereden</th>
                  <th>Nereye</th>
                  <th>Transfer Saati</th>
                  <th>Araç Bilgisi</th>
                  <th>Notlar</th>
                  <th>Durum</th>
                  <th></th>
                </tr>
              </thead>
              <tbody id="listNode">
                <tr><td colspan="14">Henüz bilet kaydı yok.</td></tr>
              </tbody>
            </table>
          </div>
          <div id="statusNode" class="status"></div>
        </article>
      </div>
    </section>
  </div>
  <div id="detailModal" class="detail-modal">
    <div class="detail-dialog">
      <div class="detail-head">
        <div>
          <h3 id="detailTitle">Detay</h3>
          <p id="detailSubtitle">Seçili kayıtlar burada listelenir.</p>
        </div>
        <button id="detailCloseBtn" type="button" class="detail-close">Kapat</button>
      </div>
      <div id="detailList" class="detail-list"></div>
    </div>
  </div>
  <script>
    (function () {
      var API_BASE = 'http://localhost:3001';
      var TOKEN_KEYS = ['fleet_access_token', 'platform_core_token', 'agency_access_token'];
      var SUPPORTED_EXTENSIONS = ['pdf', 'zip', 'jpg', 'jpeg', 'png'];
      var dropzone = document.getElementById('dropzone');
      var picker = document.getElementById('picker');
      var selectedChips = document.getElementById('selectedChips');
      var selectionSummary = document.getElementById('selectionSummary');
      var addFilesBtn = document.getElementById('addFilesBtn');
      var clearFilesBtn = document.getElementById('clearFilesBtn');
      var saveListBtn = document.getElementById('saveListBtn');
      var refreshStatusBtn = document.getElementById('refreshStatusBtn');
      var editorCard = document.getElementById('editorCard');
      var applyEditBtn = document.getElementById('applyEditBtn');
      var cancelEditBtn = document.getElementById('cancelEditBtn');
      var listNode = document.getElementById('listNode');
      var statusNode = document.getElementById('statusNode');
      var progressTotal = document.getElementById('progressTotal');
      var progressDone = document.getElementById('progressDone');
      var progressDoneCard = document.getElementById('progressDoneCard');
      var progressWaiting = document.getElementById('progressWaiting');
      var progressWaitingCard = document.getElementById('progressWaitingCard');
      var progressError = document.getElementById('progressError');
      var progressErrorCard = document.getElementById('progressErrorCard');
      var progressEta = document.getElementById('progressEta');
      var progressFill = document.getElementById('progressFill');
      var detailModal = document.getElementById('detailModal');
      var detailTitle = document.getElementById('detailTitle');
      var detailSubtitle = document.getElementById('detailSubtitle');
      var detailList = document.getElementById('detailList');
      var detailCloseBtn = document.getElementById('detailCloseBtn');
      var fields = {
        original_filename: document.getElementById('original_filename'),
        file_kind: document.getElementById('file_kind'),
        pnr_code: document.getElementById('pnr_code'),
        passenger_name: document.getElementById('passenger_name'),
        flight_no: document.getElementById('flight_no'),
        direction_type: document.getElementById('direction_type'),
        flight_date: document.getElementById('flight_date'),
        estimated_time: document.getElementById('estimated_time'),
        route_text: document.getElementById('route_text'),
        departure_time: document.getElementById('departure_time'),
        arrival_time: document.getElementById('arrival_time'),
        from_text: document.getElementById('from_text'),
        to_text: document.getElementById('to_text'),
        transfer_time: document.getElementById('transfer_time'),
        vehicle_info: document.getElementById('vehicle_info'),
        parse_note: document.getElementById('parse_note')
      };
        var selectedFiles = [];
        var items = [];
        var editingIndex = -1;
        var processingStartedAt = 0;
        var progressTimer = 0;
        var uploadInProgress = false;
        var tempUploadSeed = 0;
        var loadRequestSeed = 0;

      function readToken() {
        for (var i = 0; i < TOKEN_KEYS.length; i += 1) {
          var value = localStorage.getItem(TOKEN_KEYS[i]) || '';
          if (value) return value;
        }
        return '';
      }

      function clearStoredTokens() {
        TOKEN_KEYS.forEach(function (key) {
          localStorage.removeItem(key);
        });
      }

      async function ensureToken() {
        var token = readToken();
        if (token) return token;
        var username = sessionStorage.getItem('creatro_login_username') || 'CreaTRo';
        var password = sessionStorage.getItem('creatro_login_password') || 'Micetro25+.';
        var res = await fetch(API_BASE + '/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: username, password: password })
        });
        var data = {};
        try { data = await res.json(); } catch (_) {}
        if (!res.ok || !data.access_token) {
          throw new Error(data.detail || 'Oturum yenilenemedi.');
        }
        localStorage.setItem('fleet_access_token', String(data.access_token));
        localStorage.setItem('platform_core_token', String(data.access_token));
        localStorage.setItem('agency_access_token', String(data.access_token));
        return String(data.access_token);
      }

      async function authFetch(url, options) {
        var init = Object.assign({}, options || {});
        init.headers = Object.assign({}, (options && options.headers) || {});
        var token = await ensureToken();
        init.headers.Authorization = 'Bearer ' + token;
        var res = await fetch(String(url || ''), init);
        if (res.status !== 401) return res;
        clearStoredTokens();
        token = await ensureToken();
        init.headers.Authorization = 'Bearer ' + token;
        return fetch(String(url || ''), init);
      }

      function showStatus(message) {
        statusNode.textContent = message;
        statusNode.classList.add('show');
        window.clearTimeout(window.__ticketStatusTimer);
        window.__ticketStatusTimer = window.setTimeout(function () { statusNode.classList.remove('show'); }, 2600);
      }

        function formatSeconds(totalSeconds) {
          var seconds = Math.max(0, Number(totalSeconds || 0));
          if (!seconds) return '-';
          var mins = Math.floor(seconds / 60);
          var secs = Math.floor(seconds % 60);
          if (mins > 0) return mins + ' dk ' + String(secs).padStart(2, '0') + ' sn';
          return secs + ' sn';
        }

        function formatEtaApprox(totalSeconds) {
          var seconds = Math.max(0, Number(totalSeconds || 0));
          if (!seconds) return '-';
          if (seconds < 60) return 'Yaklaşık 1 dk';
          var minutes = Math.ceil(seconds / 60);
          if (minutes < 60) return 'Yaklaşık ' + minutes + ' dk';
          var hours = Math.floor(minutes / 60);
          var remainingMinutes = minutes % 60;
          if (!remainingMinutes) return 'Yaklaşık ' + hours + ' sa';
          return 'Yaklaşık ' + hours + ' sa ' + remainingMinutes + ' dk';
        }

        function classifyFileKind(value) {
          var kind = String(value || '').trim().toLowerCase();
          if (!kind) return 'ocr';
          if (kind === 'pdf') return 'pdf';
          if (['jpg', 'jpeg', 'png', 'zip'].indexOf(kind) >= 0) return 'ocr';
          return 'ocr';
        }

        function estimateEtaByKinds(kindValues) {
          var kinds = Array.isArray(kindValues) ? kindValues : [];
          if (!kinds.length) return '-';
          var pdfCount = 0;
          var ocrCount = 0;
          kinds.forEach(function (kind) {
            if (classifyFileKind(kind) === 'pdf') pdfCount += 1;
            else ocrCount += 1;
          });
          var seconds = 30 + (pdfCount * 2) + (ocrCount * 4);
          return formatEtaApprox(seconds);
        }

      function escapeHtml(value) {
        return String(value || '').replace(/[&<>"]/g, function (char) {
          return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[char] || char;
        });
      }

      function clearEditor() {
        Object.keys(fields).forEach(function (key) {
          if (key === 'direction_type') fields[key].value = 'Geliş';
          else fields[key].value = '';
        });
        editingIndex = -1;
        editorCard.classList.add('hidden');
      }

      function openEditor(item, index) {
        Object.keys(fields).forEach(function (key) {
          fields[key].value = item[key] || (key === 'direction_type' ? 'Geliş' : '');
        });
        editingIndex = index;
        editorCard.classList.remove('hidden');
        editorCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }

      function normalizeFiles(fileList) {
        return Array.from(fileList || []).filter(function (file) {
          var ext = String((file.name || '').split('.').pop() || '').toLowerCase();
          return SUPPORTED_EXTENSIONS.indexOf(ext) >= 0;
        });
      }

        function estimateSelectionEta() {
            if (!selectedFiles.length) return '-';
            return estimateEtaByKinds(selectedFiles.map(function (file) {
              var name = String((file && file.name) || '');
              return String(name.split('.').pop() || '').toLowerCase();
            }));
          }

        function renderSelectedFiles() {
          selectedChips.innerHTML = '';
          if (!selectedFiles.length) {
            if (selectionSummary) selectionSummary.textContent = 'Henüz dosya seçilmedi.';
            selectedChips.innerHTML = '<span class="chip">Henüz dosya seçilmedi</span>';
            updateProgress();
            return;
          }
          if (selectionSummary) selectionSummary.textContent = selectedFiles.length + ' dosya seçildi. Dosyalar isterseniz otomatik kuyruğa alınır.';
          selectedFiles.forEach(function (file, index) {
            var chip = document.createElement('span');
          chip.className = 'chip';
            chip.textContent = file.name + ' (' + Math.max(1, Math.round((file.size || 0) / 1024)) + ' KB)';
            chip.setAttribute('data-file-index', String(index));
            selectedChips.appendChild(chip);
          });
          updateProgress();
        }

      function setFiles(fileList) {
        selectedFiles = normalizeFiles(fileList);
        renderSelectedFiles();
        showStatus(selectedFiles.length ? (selectedFiles.length + ' dosya seçildi.') : 'Dosya seçilmedi.');
      }

        async function queueSelectedFiles() {
          if (uploadInProgress) return;
          if (!selectedFiles.length) {
            showStatus('Önce en az bir dosya seçin.');
            return;
          }
          var pendingRows = selectedFiles.map(function (file) {
            var ext = String((file.name || '').split('.').pop() || '').toUpperCase();
            tempUploadSeed += 1;
            return normalizeTicketItem({
              temp_upload_key: 'pending-' + String(Date.now()) + '-' + String(tempUploadSeed),
              original_filename: file.name || '',
              file_kind: ext,
              pnr_code: '',
              passenger_name: '',
              flight_no: '',
              direction_type: 'Geliş',
              flight_date: '',
              estimated_time: '',
              route_text: '',
              departure_time: '',
              arrival_time: '',
              from_text: '',
              to_text: '',
              transfer_time: '',
              vehicle_info: '',
              parse_note: 'Dosya seçildi, ortak parser kuyruğuna alınıyor.',
              upload_id: '',
              upload_status: 'selected',
              parse_summary: 'Kuyruğa hazırlanıyor',
              error_message: ''
            });
          });
          items = pendingRows.concat(items);
          renderList();
          updateProgress();
          await saveItems();
          uploadInProgress = true;
          addFilesBtn.disabled = true;
          addFilesBtn.textContent = 'Ortak parser motoruna gönderiliyor...';
          try {
            var uploadData = await uploadToSharedParser(selectedFiles);
            var resultMap = {};
            (uploadData.results || []).forEach(function (row) {
              if (row && row.original_filename) resultMap[String(row.original_filename)] = row;
            });
            selectedFiles.forEach(function (file, fileIndex) {
              var resultRow = resultMap[String(file.name || '')] || {};
              var rowIndex = fileIndex;
              if (!items[rowIndex]) return;
              items[rowIndex] = normalizeTicketItem(Object.assign({}, items[rowIndex], {
                parse_note: 'Ortak parser motoruna gönderildi.',
                upload_id: resultRow.id || '',
                upload_status: resultRow.status || 'queued',
                parse_summary: resultRow.id ? 'Kuyruğa alındı' : 'Yükleme bekleniyor',
                error_message: ''
              }));
            });
            renderList();
            processingStartedAt = Date.now();
            updateProgress();
            startProgressLoop();
          await saveItems();
          clearEditor();
          selectedFiles = [];
          renderSelectedFiles();
          if (picker) picker.value = '';
          showStatus('Dosyalar ortak parser motoruna gönderildi ve planlama listesine alındı.');
          } catch (err) {
            for (var i = 0; i < pendingRows.length; i += 1) {
              if (!items[i]) continue;
              items[i] = normalizeTicketItem(Object.assign({}, items[i], {
                upload_status: 'error',
                error_message: err && err.message ? err.message : 'Ortak parser motoruna bağlanılamadı.',
                parse_summary: 'Yükleme hatası'
              }));
            }
            renderList();
            updateProgress();
            await saveItems();
            showStatus(err && err.message ? err.message : 'Ortak parser motoruna bağlanılamadı.');
          } finally {
          uploadInProgress = false;
          addFilesBtn.disabled = false;
          addFilesBtn.textContent = 'Dosyaları Listeye Al';
        }
      }

      function parseRoute(routeText) {
        var raw = String(routeText || '').trim();
        if (!raw) return { from: '', to: '' };
        var normalized = raw.replace(/\s*-\s*/g, '>').replace(/\s*\/\s*/g, '>').replace(/\s*→\s*/g, '>');
        var parts = normalized.split('>').map(function (part) { return String(part || '').trim(); }).filter(Boolean);
        return {
          from: parts[0] || '',
          to: parts[1] || ''
        };
      }

      function applyDirectionDefaults(item) {
        var route = parseRoute(item.route_text);
        if (item.direction_type === 'Geliş' && !String(item.from_text || '').trim()) {
          item.from_text = route.to || item.from_text || '';
        }
        if (item.direction_type === 'Gidiş' && !String(item.to_text || '').trim()) {
          item.to_text = route.from || item.to_text || '';
        }
        return item;
      }

      function normalizeTicketItem(item) {
        var next = Object.assign({
          original_filename: '',
          file_kind: '',
          pnr_code: '',
          passenger_name: '',
          flight_no: '',
          direction_type: 'Geliş',
          flight_date: '',
          estimated_time: '',
          route_text: '',
          departure_time: '',
          arrival_time: '',
          from_text: '',
          to_text: '',
          transfer_time: '',
          vehicle_info: '',
          parse_note: '',
          upload_id: '',
          upload_status: '',
          parse_summary: '',
          error_message: ''
        }, item || {});
        return applyDirectionDefaults(next);
      }

      function mergeLoadedItems(serverItems) {
        var incoming = Array.isArray(serverItems) ? serverItems.map(normalizeTicketItem) : [];
        var current = Array.isArray(items) ? items.slice() : [];
        var merged = incoming.slice();
        current.forEach(function (localItem) {
          if (!localItem) return;
          var localTempKey = String(localItem.temp_upload_key || '').trim();
          var localUploadId = String(localItem.upload_id || '').trim();
          var exists = merged.some(function (serverItem) {
            if (!serverItem) return false;
            var serverTempKey = String(serverItem.temp_upload_key || '').trim();
            var serverUploadId = String(serverItem.upload_id || '').trim();
            if (localTempKey && serverTempKey && localTempKey === serverTempKey) return true;
            if (localUploadId && serverUploadId && localUploadId === serverUploadId) return true;
            return false;
          });
          if (!exists) merged.unshift(normalizeTicketItem(localItem));
        });
        return merged;
      }

      function collectEditorItem(source) {
        var item = Object.assign({}, source || {});
        Object.keys(fields).forEach(function (key) {
          item[key] = String(fields[key].value || '').trim();
        });
        return applyDirectionDefaults(item);
      }

      function getMissingFields(item) {
        var required = [
          ['flight_date', 'Tarih'],
          ['passenger_name', 'İsim Soyisim'],
          ['route_text', 'Rota'],
          ['flight_no', 'Uçuş Kodu'],
          ['departure_time', 'Kalkış Saati'],
          ['arrival_time', 'İniş Saati'],
          ['from_text', 'Nereden'],
          ['to_text', 'Nereye'],
          ['transfer_time', 'Transfer Saati'],
          ['vehicle_info', 'Araç Bilgisi']
        ];
        return required.filter(function (entry) {
          return !String(item[entry[0]] || '').trim();
        }).map(function (entry) { return entry[1]; });
      }

      function getStatusChip(item) {
        var status = String(item.upload_status || '').toLowerCase();
        var missing = getMissingFields(item);
        if (item.error_message) {
          return '<span class="status-chip error">Hata</span>';
        }
        if (missing.length) {
          return '<span class="status-chip waiting">Eksik Alan</span>';
        }
        if (status === 'processed' || status === 'completed' || status === 'done') {
          return '<span class="status-chip ready">Hazır</span>';
        }
        if (status === 'pending' || status === 'queued') {
          return '<span class="status-chip info">İşleniyor</span>';
        }
        return '<span class="status-chip waiting">' + escapeHtml(item.upload_status || 'Bekliyor') + '</span>';
      }

      function getProcessedItems() {
        return items.filter(function (item) {
          var status = String(item.upload_status || '').toLowerCase();
          return !item.error_message && !getMissingFields(item).length && ['processed', 'completed', 'done'].indexOf(status) >= 0;
        });
      }

      function getWaitingItems() {
        var queuedWaiting = items.filter(function (item) {
          var status = String(item.upload_status || '').toLowerCase();
          if (item.error_message || ['processed', 'completed', 'done', 'failed', 'error'].indexOf(status) >= 0) return false;
          return true;
        });
        var selectedWaiting = selectedFiles.map(function (file) {
          var name = String((file && file.name) || '');
          var ext = String(name.split('.').pop() || '').toUpperCase();
          return {
            original_filename: name || '-',
            file_kind: ext || '-',
            upload_status: 'Seçildi',
            passenger_name: '',
            route_text: '',
            flight_no: '',
            parse_note: 'Henüz kuyruğa alınmadı.'
          };
        });
        return queuedWaiting.concat(selectedWaiting);
      }

      function getErrorItems() {
        return items.filter(function (item) {
          var status = String(item.upload_status || '').toLowerCase();
          return !!item.error_message || status === 'failed' || status === 'error';
        });
      }

      function openDetailModal(title, subtitle, rows) {
        detailTitle.textContent = title;
        detailSubtitle.textContent = subtitle;
        if (!rows.length) {
          detailList.innerHTML = '<div class="detail-empty">Bu grup için gösterilecek kayıt yok.</div>';
        } else {
          detailList.innerHTML = rows.map(function (item) {
            return ''
              + '<div class="detail-item">'
              +   '<strong>' + escapeHtml(item.original_filename || '-') + '</strong>'
              +   '<span>Durum: ' + escapeHtml(item.upload_status || '-') + ' | Tür: ' + escapeHtml(item.file_kind || '-') + (item.upload_id ? ' | Yükleme #' + escapeHtml(item.upload_id) : '') + '</span>'
              +   '<span>Yolcu: ' + escapeHtml(item.passenger_name || '-') + ' | Uçuş: ' + escapeHtml(item.flight_no || '-') + '</span>'
              +   '<span>Rota: ' + escapeHtml(item.route_text || '-') + '</span>'
              +   '<span>Not: ' + escapeHtml(item.parse_note || item.error_message || '-') + '</span>'
              + '</div>';
          }).join('');
        }
        detailModal.classList.add('show');
      }

      function closeDetailModal() {
        detailModal.classList.remove('show');
      }

        function updateProgress() {
          var queuedTotal = items.length;
          var selectedTotal = selectedFiles.length;
          var total = queuedTotal + selectedTotal;
          var done = 0;
          var waiting = 0;
          var error = 0;
          items.forEach(function (item) {
            var status = String(item.upload_status || '').toLowerCase();
          if (item.error_message || status === 'failed' || status === 'error') {
            error += 1;
            return;
          }
          if (!getMissingFields(item).length && ['processed', 'completed', 'done'].indexOf(status) >= 0) {
            done += 1;
            return;
            }
            waiting += 1;
          });
          waiting += selectedTotal;
          progressTotal.textContent = String(total);
          progressDone.textContent = String(done);
          progressWaiting.textContent = String(waiting);
          progressError.textContent = String(error);
          if (progressErrorCard) {
          if (error > 0) progressErrorCard.classList.add('error');
          else progressErrorCard.classList.remove('error');
          }
          var pct = total ? Math.round(((done + error) / total) * 100) : 0;
          progressFill.style.width = pct + '%';
          if (!total) {
            progressEta.textContent = '-';
            return;
          }
          if (selectedTotal && !queuedTotal) {
            progressEta.textContent = estimateSelectionEta();
            return;
          }
          if (!processingStartedAt || !done || !waiting) {
            progressEta.textContent = waiting ? estimateEtaByKinds(
              items.filter(function (item) {
                var status = String(item.upload_status || '').toLowerCase();
                if (item.error_message || ['processed', 'completed', 'done', 'failed', 'error'].indexOf(status) >= 0) {
                  return false;
                }
                return true;
              }).map(function (item) { return item.file_kind || ''; }).concat(
                selectedFiles.map(function (file) {
                  var name = String((file && file.name) || '');
                  return String(name.split('.').pop() || '').toLowerCase();
                })
              )
            ) : '-';
            return;
          }
          var elapsed = Math.max(1, Math.floor((Date.now() - processingStartedAt) / 1000));
          var avgPerDone = elapsed / Math.max(1, done);
          progressEta.textContent = formatEtaApprox(Math.ceil(avgPerDone * waiting));
      }

      function stopProgressLoop() {
        if (progressTimer) {
          window.clearInterval(progressTimer);
          progressTimer = 0;
        }
      }

      async function refreshStatusesSilently() {
        var uploadIds = items.map(function (item) { return Number(item.upload_id || 0); }).filter(function (value) { return value > 0; });
        if (!uploadIds.length) return;
        try {
          var statusRows = await fetchSharedStatuses(uploadIds);
          var statusMap = {};
          statusRows.forEach(function (row) { if (row && row.id) statusMap[String(row.id)] = row; });
          for (var i = 0; i < items.length; i += 1) {
            var item = items[i];
            var uploadId = String(item.upload_id || '');
            if (!uploadId || !statusMap[uploadId]) continue;
            item.upload_status = statusMap[uploadId].status || item.upload_status || '';
            item.error_message = statusMap[uploadId].error_message || '';
            if (String(item.upload_status || '').toLowerCase() === 'processed') {
              var detail = await fetchUploadDetail(uploadId);
              var parseResult = detail.parse_result || {};
              item.original_filename = item.original_filename || detail.original_filename || '';
              item.pnr_code = item.pnr_code || parseResult.pnr || '';
              item.passenger_name = item.passenger_name || parseResult.passenger_name || '';
              item.flight_no = item.flight_no || parseResult.flight_no || '';
              item.flight_date = item.flight_date || parseResult.date || '';
              item.estimated_time = item.estimated_time || parseResult.time || '';
              item.departure_time = item.departure_time || parseResult.departure_time || parseResult.time || '';
              item.arrival_time = item.arrival_time || parseResult.arrival_time || parseResult.time || '';
              item.route_text = item.route_text || [parseResult.from || '', parseResult.to || ''].filter(Boolean).join(' > ');
              item.parse_note = item.parse_note === 'Ortak parser motoruna gönderildi.' ? '' : item.parse_note;
              item.parse_summary = parseResult.method ? ('Parse: ' + parseResult.method.toUpperCase()) : 'Parse tamamlandı';
              items[i] = applyDirectionDefaults(item);
            }
          }
          renderList();
          updateProgress();
          await saveItems();
        } catch (_) {}
      }

      function startProgressLoop() {
        stopProgressLoop();
        progressTimer = window.setInterval(async function () {
          await refreshStatusesSilently();
          updateProgress();
          var stillWaiting = items.some(function (item) {
            var status = String(item.upload_status || '').toLowerCase();
            return ['processed', 'completed', 'done', 'failed', 'error'].indexOf(status) < 0;
          });
          if (!stillWaiting) stopProgressLoop();
        }, 2000);
      }

      function renderList() {
        if (!items.length) {
          listNode.innerHTML = '<tr><td colspan="14">Henüz bilet kaydı yok.</td></tr>';
          return;
        }
        listNode.innerHTML = items.map(function (item, index) {
          var missing = getMissingFields(item);
          var fileInfo = '<span class="row-main">' + escapeHtml(item.original_filename || '-') + '</span>'
            + '<span class="row-sub">' + escapeHtml(item.file_kind || '-') + (item.upload_id ? ' / #' + escapeHtml(item.upload_id) : '') + '</span>';
          var statusInfo = getStatusChip(item);
          if (item.parse_summary) {
            statusInfo += '<span class="row-sub">' + escapeHtml(item.parse_summary) + '</span>';
          }
          if (item.error_message) {
            statusInfo += '<span class="row-sub">Hata: ' + escapeHtml(item.error_message) + '</span>';
          }
          if (missing.length) {
            statusInfo += '<span class="row-sub">Eksik: ' + escapeHtml(missing.join(', ')) + '</span>';
          }
          return ''
            + '<tr>'
            +   '<td>' + fileInfo + '</td>'
            +   '<td>' + escapeHtml(item.flight_date || '-') + '</td>'
            +   '<td>' + escapeHtml(item.passenger_name || '-') + '</td>'
            +   '<td><span class="row-main">' + escapeHtml(item.route_text || '-') + '</span><span class="row-sub">' + escapeHtml(item.direction_type || '-') + '</span></td>'
            +   '<td>' + escapeHtml(item.flight_no || '-') + '</td>'
            +   '<td>' + escapeHtml(item.departure_time || '-') + '</td>'
            +   '<td>' + escapeHtml(item.arrival_time || '-') + '</td>'
            +   '<td>' + escapeHtml(item.from_text || '-') + '</td>'
            +   '<td>' + escapeHtml(item.to_text || '-') + '</td>'
            +   '<td>' + escapeHtml(item.transfer_time || '-') + '</td>'
            +   '<td>' + escapeHtml(item.vehicle_info || '-') + '</td>'
            +   '<td>' + escapeHtml(item.parse_note || '-') + '</td>'
            +   '<td>' + statusInfo + '</td>'
            +   '<td><div class="row-actions"><button type="button" class="mini-btn" data-edit-index="' + index + '">Düzenle</button><button type="button" class="mini-btn remove" data-remove-index="' + index + '">Kaldır</button></div></td>'
            + '</tr>';
        }).join('');
      }

      async function loadItems() {
          var currentLoadSeed = loadRequestSeed + 1;
          loadRequestSeed = currentLoadSeed;
          var token = '';
          try {
            token = await ensureToken();
            var res = await authFetch(API_BASE + '/planning-ticket-batches', {});
            if (!res.ok) return;
            var data = await res.json();
            if (currentLoadSeed !== loadRequestSeed) return;
            items = mergeLoadedItems(data.items);
            renderList();
            updateProgress();
          } catch (_) {}
        }

        async function saveItems() {
          try {
            var res = await authFetch(API_BASE + '/planning-ticket-batches', {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ items: items })
            });
          if (!res.ok) { showStatus('Bilet listesi çekirdeğe kaydedilemedi.'); return; }
          showStatus('Bilet listesi çekirdeğe kaydedildi.');
        } catch (_) {
          showStatus('Bilet listesi çekirdeğe kaydedilemedi.');
        }
      }

        async function uploadToSharedParser(files) {
          var username = sessionStorage.getItem('creatro_login_username') || 'CreaTRo';
          var password = sessionStorage.getItem('creatro_login_password') || 'Micetro25+.';
          var form = new FormData();
          files.forEach(function (file) { form.append('files', file, file.name || 'dosya'); });
          form.append('username', username);
          form.append('password', password);
          form.append('operation_city', '');
          form.append('target_airports', '');
          var res = await authFetch(API_BASE + '/shared-ticket-upload', {
            method: 'POST',
            body: form
          });
        var data = {};
        try { data = await res.json(); } catch (_) {}
        if (!res.ok) {
          throw new Error(data.detail || 'Ortak parser yükleme servisi hata verdi.');
        }
        return data.result || {};
      }

        async function fetchSharedStatuses(uploadIds) {
          var username = sessionStorage.getItem('creatro_login_username') || 'CreaTRo';
          var password = sessionStorage.getItem('creatro_login_password') || 'Micetro25+.';
          var res = await authFetch(API_BASE + '/shared-ticket-statuses', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username, password: password, upload_ids: uploadIds })
          });
        var data = {};
        try { data = await res.json(); } catch (_) {}
        if (!res.ok) throw new Error(data.detail || 'Durum bilgisi alınamadı.');
        return Array.isArray(data.items) ? data.items : [];
      }

        async function fetchUploadDetail(uploadId) {
          var username = encodeURIComponent(sessionStorage.getItem('creatro_login_username') || 'CreaTRo');
          var password = encodeURIComponent(sessionStorage.getItem('creatro_login_password') || 'Micetro25+.');
          var res = await authFetch(API_BASE + '/shared-ticket-detail/' + encodeURIComponent(String(uploadId)) + '?username=' + username + '&password=' + password, {});
        var data = {};
        try { data = await res.json(); } catch (_) {}
        if (!res.ok) throw new Error(data.detail || 'Upload detayı alınamadı.');
        return data.item || {};
      }

      dropzone.addEventListener('click', function () { picker.click(); });
      dropzone.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          picker.click();
        }
      });
      picker.addEventListener('change', function (event) {
        setFiles(event.target.files);
        if (selectedFiles.length) queueSelectedFiles();
      });
      ['dragenter', 'dragover'].forEach(function (name) {
        dropzone.addEventListener(name, function (event) {
          event.preventDefault();
          event.stopPropagation();
          dropzone.classList.add('dragover');
        });
      });
      ['dragleave', 'drop'].forEach(function (name) {
        dropzone.addEventListener(name, function (event) {
          event.preventDefault();
          event.stopPropagation();
          dropzone.classList.remove('dragover');
        });
      });
      dropzone.addEventListener('drop', function (event) {
        setFiles(event.dataTransfer.files);
        if (selectedFiles.length) queueSelectedFiles();
      });

      addFilesBtn.addEventListener('click', queueSelectedFiles);

      clearFilesBtn.addEventListener('click', function () {
        selectedFiles = [];
        if (picker) picker.value = '';
        renderSelectedFiles();
        showStatus('Seçim temizlendi.');
      });

      applyEditBtn.addEventListener('click', async function () {
        if (editingIndex < 0 || !items[editingIndex]) {
          showStatus('Düzenlenecek bilet kaydı bulunamadı.');
          return;
        }
        var updated = collectEditorItem(items[editingIndex]);
        items.splice(editingIndex, 1, updated);
        renderList();
        await saveItems();
        clearEditor();
        showStatus('Bilet kaydı güncellendi.');
      });

      cancelEditBtn.addEventListener('click', function () {
        clearEditor();
        showStatus('Düzenleme kapatıldı.');
      });

      saveListBtn.addEventListener('click', saveItems);
      refreshStatusBtn.addEventListener('click', async function () {
        var uploadIds = items.map(function (item) { return Number(item.upload_id || 0); }).filter(function (value) { return value > 0; });
        if (!uploadIds.length) {
          showStatus('Durumu yenilemek için önce yüklenmiş bilet kaydı olmalıdır.');
          return;
        }
        refreshStatusBtn.disabled = true;
        refreshStatusBtn.textContent = 'Durumlar güncelleniyor...';
        try {
          await refreshStatusesSilently();
          showStatus('Yükleme durumları ve parse bilgileri güncellendi.');
        } catch (err) {
          showStatus(err && err.message ? err.message : 'Durum güncellemesi yapılamadı.');
        } finally {
          refreshStatusBtn.disabled = false;
          refreshStatusBtn.textContent = 'Durumu Yenile';
        }
      });

      fields.direction_type.addEventListener('change', function () {
        if (editingIndex < 0 || !items[editingIndex]) return;
        var draft = collectEditorItem(items[editingIndex]);
        fields.from_text.value = draft.from_text || '';
        fields.to_text.value = draft.to_text || '';
      });

      fields.route_text.addEventListener('blur', function () {
        if (editingIndex < 0 || !items[editingIndex]) return;
        var draft = collectEditorItem(items[editingIndex]);
        fields.from_text.value = draft.from_text || '';
        fields.to_text.value = draft.to_text || '';
      });

      listNode.addEventListener('click', async function (event) {
        var editBtn = event.target.closest('[data-edit-index]');
        if (editBtn) {
          var editIndex = parseInt(editBtn.getAttribute('data-edit-index'), 10);
          if (!Number.isNaN(editIndex) && items[editIndex]) {
            openEditor(items[editIndex], editIndex);
            showStatus('Bilet kaydı düzenleme için forma taşındı.');
          }
          return;
        }
        var removeBtn = event.target.closest('[data-remove-index]');
        if (!removeBtn) return;
        var removeIndex = parseInt(removeBtn.getAttribute('data-remove-index'), 10);
        if (Number.isNaN(removeIndex)) return;
        items.splice(removeIndex, 1);
        renderList();
        await saveItems();
        updateProgress();
        clearEditor();
        showStatus('Bilet listeden kaldırıldı.');
      });

      if (progressDoneCard) {
        progressDoneCard.addEventListener('click', function () {
          openDetailModal(
            'İşlenen Biletler',
            'Parse tamamlanan ve zorunlu alanları dolu kayıtlar listelenir.',
            getProcessedItems()
          );
        });
      }

      if (progressWaitingCard) {
        progressWaitingCard.addEventListener('click', function () {
          openDetailModal(
            'Kalan Biletler',
            'Kuyrukta bekleyen veya henüz seçilip işleme alınmamış kayıtlar listelenir.',
            getWaitingItems()
          );
        });
      }

      if (progressErrorCard) {
        progressErrorCard.addEventListener('click', function () {
          openDetailModal(
            'Hatalı Biletler',
            'İşlem sırasında hata alan kayıtlar ve hata notları listelenir.',
            getErrorItems()
          );
        });
      }

      if (detailCloseBtn) detailCloseBtn.addEventListener('click', closeDetailModal);
      if (detailModal) {
        detailModal.addEventListener('click', function (event) {
          if (event.target === detailModal) closeDetailModal();
        });
      }
      document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && detailModal && detailModal.classList.contains('show')) {
          closeDetailModal();
        }
      });

      renderSelectedFiles();
      clearEditor();
      renderList();
      updateProgress();
      loadItems();
    })();
  </script>
</body>
</html>
    """


@app.get("/planning-transfer-lists", response_class=HTMLResponse)
def planning_transfer_lists_page() -> str:
    return _build_planning_list_page(
        {
            "title": "Transfer Listeleri",
            "subtitle": "Geliş, gidiş ve saha listeleri",
            "intro": "Bu ekran transfer kayıtlarını grup bazında toplar. Geliş, gidiş, VIP veya saha listeleri burada planlanır; sonraki aşamada bilet okuma motorundan otomatik besleme bağlanacaktır. Yön hesabında önce proje şehri, proje şehri yoksa araç firmasının merkez şehri baz alınır.",
            "extra_actions": [{"id": "importTicketsBtn", "label": "Biletlerden Aktar"}],
            "form_title": "Yeni Transfer Kaydı",
            "add_label": "Transfer Ekle",
            "update_label": "Transferi Güncelle",
            "list_title": "Transfer Kayıtları",
            "api_path": "/planning-transfer-lists",
            "fields": [
                {"id": "transfer_code", "label": "Transfer Kodu", "placeholder": "Örn: TRF-001"},
                {"id": "service_type", "label": "Hizmet Tipi", "type": "select", "options": ["Geliş Transfer", "Gidiş Transfer", "Half Day", "Full Day", "Gece Turu"]},
                {"id": "guest_name", "label": "Misafir / Grup", "placeholder": "Misafir adı veya grup adı"},
                {"id": "project_city", "label": "Proje Şehri", "placeholder": "Varsa proje şehri"},
                {"id": "person_count", "label": "Kişi Sayısı", "placeholder": "Örn: 8"},
                {"id": "pickup_text", "label": "Alınış Noktası", "placeholder": "Havalimanı / Otel", "full": True},
                {"id": "dropoff_text", "label": "Bırakılış Noktası", "placeholder": "Otel / Salon / Havalimanı", "full": True},
                {"id": "flight_no", "label": "Uçuş No", "placeholder": "Örn: TK2410"},
                {"id": "transfer_date", "label": "Tarih", "type": "date"},
                {"id": "transfer_time", "label": "Saat", "type": "time"},
                {"id": "plan_note", "label": "Planlama Notu", "type": "textarea", "placeholder": "Araç tipi, VIP, özel karşılama vb.", "full": True},
            ],
            "required_fields": ["transfer_code", "service_type", "guest_name"],
            "primary_field": "transfer_code",
            "summary_fields": ["service_type", "guest_name", "project_city", "transfer_date", "flight_no"],
            "summary_labels": {"service_type": "Hizmet", "guest_name": "Misafir", "project_city": "Proje Şehri", "transfer_date": "Tarih", "flight_no": "Uçuş"},
            "tag_fields": ["pickup_text", "dropoff_text", "transfer_time"],
            "empty_title": "Henüz transfer kaydı yok",
            "empty_text": "İlk transfer planlama kaydını soldaki form ile ekleyin veya biletlerden aktarın.",
            "required_error": "Transfer kodu, hizmet tipi ve misafir bilgisi zorunludur.",
            "save_success": "Transfer listesi çekirdeğe kaydedildi.",
            "save_fail": "Transfer listesi çekirdeğe kaydedilemedi.",
            "add_success": "Transfer listeye eklendi. Kaydet ile çekirdeğe yazabilirsiniz.",
            "update_success": "Transfer güncellendi. Kaydet ile çekirdeğe yazabilirsiniz.",
            "remove_success": "Transfer listeden kaldırıldı. Kaydet ile çekirdeğe yazabilirsiniz.",
            "edit_notice": "Transfer kaydı düzenleme için forma taşındı.",
        }
    )


@app.get("/planning-no-name-slots", response_class=HTMLResponse)
def planning_no_name_slots_page() -> str:
    return _build_planning_list_page(
        {
            "title": "No/Name Planları",
            "subtitle": "Geçici slot, toplu atama ve plan sorumlusu alanı",
            "intro": "Bu ekran gerçek araç atamasından önce kullanılan No/Name slotlarını toplar. Plan sorumlusu, araç tipi, kapasite ve saat aralığı girilerek toplu atama hazırlığı yapılır.",
            "form_title": "Yeni No/Name Slotu",
            "add_label": "Slot Ekle",
            "update_label": "Slotu Güncelle",
            "list_title": "No/Name Slotları",
            "api_path": "/planning-operation-slots",
            "fields": [
                {"id": "slot_code", "label": "Slot Kodu", "placeholder": "Örn: NO/NAME-1"},
                {"id": "slot_date", "label": "Tarih", "type": "date"},
                {"id": "slot_time", "label": "Saat", "type": "time"},
                {"id": "vehicle_category", "label": "Araç Tipi", "type": "select", "options": ["VAN", "MİNİ", "MİDİ", "BİNEK", "BUS"]},
                {"id": "capacity_need", "label": "Kapasite İhtiyacı", "placeholder": "Örn: 8 kişi"},
                {"id": "responsible_name", "label": "Plan Sorumlusu", "placeholder": "Operatör / Yönetici"},
                {"id": "slot_status", "label": "Durum", "type": "select", "options": ["Taslak", "Planlandı", "Araç Bekleniyor", "Hazır"]},
                {"id": "slot_note", "label": "Özel Not", "type": "textarea", "placeholder": "VIP, iki araç gerekebilir, uçak gecikirse kaydır vb.", "full": True},
            ],
            "required_fields": ["slot_code", "slot_date", "vehicle_category"],
            "primary_field": "slot_code",
            "summary_fields": ["slot_date", "slot_time", "vehicle_category", "responsible_name"],
            "summary_labels": {"slot_date": "Tarih", "slot_time": "Saat", "vehicle_category": "Araç Tipi", "responsible_name": "Sorumlu"},
            "tag_fields": ["capacity_need", "slot_status"],
            "empty_title": "Henüz No/Name slotu yok",
            "empty_text": "İlk geçici plan slotunu soldaki form ile ekleyin.",
            "required_error": "Slot kodu, tarih ve araç tipi zorunludur.",
            "save_success": "No/Name listesi çekirdeğe kaydedildi.",
            "save_fail": "No/Name listesi çekirdeğe kaydedilemedi.",
            "add_success": "Slot listeye eklendi. Kaydet ile çekirdeğe yazabilirsiniz.",
            "update_success": "Slot güncellendi. Kaydet ile çekirdeğe yazabilirsiniz.",
            "remove_success": "Slot listeden kaldırıldı. Kaydet ile çekirdeğe yazabilirsiniz.",
            "edit_notice": "Slot kaydı düzenleme için forma taşındı.",
        }
    )


@app.get("/accounting", response_class=HTMLResponse)
def accounting_page() -> str:
    return _build_module_page(
        "Muhasebe Modülü",
        "Hizmet kalemleri, masraf, ödeme ve sözleşme kuralları",
        "Muhasebe modülü proje ve transfer bazlı hizmet kalemlerini, ek masrafları ve sözleşme kurallarını toplayacak altyapı alanıdır. İlk sürümde ekran omurgası hazırlanmıştır.",
        [
            {"icon": "H", "title": "Hizmet Kataloğu", "text": "Geliş transfer, gidiş transfer, yarım gün, tam gün ve ek hizmet kalemleri burada toplanacaktır.", "href": "/accounting", "action": "Hazırlanıyor"},
            {"icon": "M", "title": "Masraf ve Mesai", "text": "Sürücü ve karşılamacı masraf kayıtları ile vardiya verileri burada ilerleyecek.", "href": "/accounting", "action": "Hazırlanıyor"},
            {"icon": "S", "title": "Sözleşme Kuralları", "text": "Araç firması kiraya veren, acente kiracı mantığı ile sözleşme ve fiyat kuralı altyapısı.", "href": "/accounting", "action": "Hazırlanıyor"},
        ],
    )


@app.get("/vehicles", response_class=HTMLResponse)
def vehicle_cards_page() -> str:
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Araç Kartları</title>
  <style>
    :root {
      --bg-1: #081d1d;
      --bg-2: #0d3934;
      --bg-3: #0a2724;
      --panel: rgba(7, 28, 27, 0.82);
      --panel-line: rgba(129, 223, 197, 0.22);
      --card-bg: linear-gradient(180deg, rgba(246, 255, 252, 0.97) 0%, rgba(232, 247, 242, 0.93) 100%);
      --card-line: rgba(132, 220, 193, 0.52);
      --ink: #12332d;
      --muted: #45655f;
      --accent: #24b389;
      --white: #f7fbfb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--white);
      background:
        radial-gradient(circle at right top, rgba(36,179,137,0.20), transparent 28%),
        linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 56%, var(--bg-3) 100%);
      background-attachment: fixed;
    }
    .wrap { width: min(1240px, calc(100% - 32px)); margin: 22px auto 40px; }
    .head, .panel {
      background: var(--panel);
      border: 1px solid var(--panel-line);
      border-radius: 20px;
      backdrop-filter: blur(10px);
      box-shadow: 0 18px 36px rgba(2, 12, 12, 0.28);
    }
    .head {
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:12px;
      padding:14px 16px;
      margin-bottom:16px;
    }
    .head a {
      color:#dcfff6;
      text-decoration:none;
      border:1px solid rgba(132,220,193,0.22);
      background:rgba(255,255,255,0.06);
      min-height:38px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      border-radius:12px;
      padding:0 14px;
      font-weight:700;
      font-size:13px;
    }
    .head strong { display:block; font-size:22px; }
    .head span { color:#a2d4ca; font-size:12px; }
    .panel { padding:24px; }
    .toolbar {
      display:flex;
      justify-content:space-between;
      gap:12px;
      align-items:flex-start;
      flex-wrap:wrap;
      margin-bottom:18px;
    }
    .toolbar p {
      margin:0;
      color:#b9d7d0;
      line-height:1.65;
      font-size:13px;
      max-width:70ch;
    }
    .action-row {
      display:flex;
      gap:10px;
      flex-wrap:wrap;
    }
    .action-btn {
      min-height:40px;
      border-radius:12px;
      padding:0 14px;
      border:1px solid rgba(132,220,193,0.22);
      background:rgba(255,255,255,0.06);
      color:#dcfff6;
      font-weight:700;
      cursor:pointer;
    }
    .action-btn.primary {
      color:#06271e;
      background: linear-gradient(180deg, #59e0b4 0%, #22b28a 100%);
      border-color: transparent;
      box-shadow: 0 10px 20px rgba(36,179,137,0.18);
    }
    .layout {
      display:grid;
      grid-template-columns: 420px 1fr;
      gap:16px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-line);
      border-radius: 18px;
      padding: 18px;
      color: var(--ink);
      box-shadow: 0 16px 30px rgba(2, 14, 13, 0.18);
    }
    .card h3 { margin:0 0 12px; font-size:18px; }
    .field-grid {
      display:grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap:12px;
    }
    .field {
      display:grid;
      gap:7px;
    }
    .field.full {
      grid-column: 1 / -1;
    }
    .field label {
      font-size:12px;
      font-weight:800;
      color:#0f7b60;
    }
    .field input, .field select, .field textarea, .dropdown-trigger {
      width:100%;
      min-height:42px;
      border-radius:14px;
      border:1px solid rgba(15, 123, 96, 0.16);
      background:rgba(255,255,255,0.78);
      color:var(--ink);
      padding:10px 12px;
      outline:none;
      font-family:inherit;
      font-size:13px;
    }
    .field textarea {
      min-height:90px;
      resize:vertical;
    }
    .field input:focus, .field select:focus, .field textarea:focus, .dropdown-trigger:focus {
      border-color:rgba(36,179,137,0.58);
      box-shadow:0 0 0 4px rgba(36,179,137,0.10);
    }
    .multi-select {
      display:grid;
      gap:10px;
      position:relative;
    }
    .dropdown-trigger {
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:10px;
      cursor:pointer;
      text-align:left;
    }
    .dropdown-trigger strong {
      color:var(--ink);
      font-size:13px;
    }
    .dropdown-trigger span {
      color:var(--muted);
      font-size:12px;
      white-space:nowrap;
    }
    .dropdown-menu {
      position:absolute;
      top:calc(100% + 8px);
      left:0;
      right:0;
      z-index:30;
      display:none;
      padding:12px;
      border-radius:16px;
      border:1px solid rgba(15, 123, 96, 0.18);
      background:rgba(250,255,253,0.98);
      box-shadow:0 18px 34px rgba(2, 14, 13, 0.18);
    }
    .dropdown-menu.open {
      display:grid;
      gap:10px;
    }
    .multi-option-grid {
      display:grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap:8px;
    }
    .multi-option-btn {
      min-height:40px;
      border-radius:12px;
      border:1px solid rgba(15, 123, 96, 0.12);
      background:rgba(36,179,137,0.08);
      color:var(--ink);
      font-size:12px;
      font-weight:800;
      cursor:pointer;
      transition:all .15s ease;
    }
    .multi-option-btn.selected {
      background:linear-gradient(180deg, #59e0b4 0%, #22b28a 100%);
      color:#06271e;
      border-color:transparent;
      box-shadow:0 10px 18px rgba(36,179,137,0.18);
    }
    .dropdown-actions {
      display:flex;
      justify-content:space-between;
      gap:10px;
      flex-wrap:wrap;
    }
    .dropdown-action-btn {
      min-height:36px;
      border-radius:12px;
      border:1px solid rgba(15, 123, 96, 0.14);
      background:#ffffff;
      color:#0f7b60;
      font-size:12px;
      font-weight:800;
      padding:0 12px;
      cursor:pointer;
    }
    .multi-hint {
      color:var(--muted);
      font-size:12px;
      line-height:1.5;
    }
    .list {
      display:grid;
      gap:12px;
    }
    .extra-list {
      display:grid;
      gap:10px;
    }
    .extra-item {
      display:grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
      gap:10px;
      align-items:end;
      padding:10px;
      border-radius:14px;
      border:1px solid rgba(15, 123, 96, 0.12);
      background:rgba(255,255,255,0.56);
    }
    .extra-remove {
      min-height:42px;
      border-radius:12px;
      padding:0 12px;
      border:1px solid rgba(143, 36, 24, 0.14);
      background:rgba(255, 228, 224, 0.92);
      color:#8f2418;
      font-weight:800;
      cursor:pointer;
    }
    .vehicle-item {
      border:1px solid rgba(15, 123, 96, 0.22);
      border-radius:16px;
      padding:14px;
      background:rgba(255,255,255,0.78);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.56);
    }
    .item-head {
      display:flex;
      justify-content:space-between;
      align-items:flex-start;
      gap:12px;
      margin-bottom:6px;
    }
    .vehicle-item strong {
      display:block;
      font-size:15px;
    }
    .vehicle-item span {
      display:block;
      color:var(--muted);
      font-size:12px;
      line-height:1.55;
    }
    .vehicle-tags {
      display:flex;
      flex-wrap:wrap;
      gap:8px;
      margin-top:10px;
    }
    .vehicle-tags i {
      display:inline-flex;
      align-items:center;
      min-height:28px;
      padding:0 10px;
      border-radius:999px;
      background:rgba(36,179,137,0.12);
      border:1px solid rgba(36,179,137,0.18);
      color:#0f7b60;
      font-style:normal;
      font-size:11px;
      font-weight:800;
    }
    .item-actions {
      display:flex;
      gap:10px;
      margin-top:12px;
      flex-wrap:wrap;
    }
    .item-actions.compact {
      margin-top:0;
      flex-wrap:nowrap;
      gap:8px;
      flex-shrink:0;
    }
    .item-btn {
      min-height:34px;
      border-radius:12px;
      padding:0 12px;
      border:none;
      font-weight:800;
      font-size:12px;
      cursor:pointer;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      gap:8px;
      box-shadow: 0 10px 18px rgba(2, 14, 13, 0.10);
    }
    .item-btn.edit {
      background:linear-gradient(180deg, #d9f6ee 0%, #b8eadc 100%);
      color:#0e5c49;
      border:1px solid rgba(14, 92, 73, 0.18);
    }
    .item-btn.remove {
      background:linear-gradient(180deg, #ffe3e0 0%, #ffc8c0 100%);
      color:#8f2418;
      border:1px solid rgba(143, 36, 24, 0.16);
    }
    .status {
      margin-top:16px;
      border-radius:14px;
      padding:12px 14px;
      background:rgba(36, 179, 137, 0.12);
      border:1px solid rgba(36, 179, 137, 0.20);
      color:#d7fbef;
      font-size:12px;
      line-height:1.6;
      display:none;
    }
    .status.show { display:block; }
    @media (max-width: 960px) {
      .layout { grid-template-columns: 1fr; }
      .field-grid { grid-template-columns: 1fr; }
      .multi-option-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .extra-item { grid-template-columns: 1fr; }
      .item-head { flex-direction:column; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="head">
      <div>
        <strong>Araç Kartları</strong>
        <span>Filo ana verileri, araç tipi ve temel özelliklerin ilk kayıt ekranı</span>
      </div>
      <a href="/panel">Panele Dön</a>
    </section>

    <section class="panel">
      <div class="toolbar">
        <p>
          Bu ilk sürümde araç kartları temel veri alanlarıyla kaydedilir. Sonraki adımda sınırsız özellik kategorileri,
          araç tipi filtreleme ve sözleşme bazlı uygunluk kuralları eklenecek.
        </p>
        <div class="action-row">
          <button id="saveVehiclesBtn" type="button" class="action-btn primary">Listeyi Kaydet</button>
          <button id="clearVehiclesBtn" type="button" class="action-btn">Formu Temizle</button>
        </div>
      </div>

      <div class="layout">
        <article class="card">
          <h3>Yeni Araç Kartı</h3>
          <div class="field-grid">
            <div class="field">
              <label for="vehicle_code">Araç Kodu</label>
              <input id="vehicle_code" type="text" placeholder="Örn: VITO-07" />
            </div>
            <div class="field">
              <label for="plate_no">Plaka</label>
              <input id="plate_no" type="text" placeholder="34 ABC 123" />
            </div>
            <div class="field">
              <label for="vehicle_category">Kategori</label>
              <select id="vehicle_category">
                <option value="VAN">VAN</option>
                <option value="MİNİ">MİNİ</option>
                <option value="MİDİ">MİDİ</option>
                <option value="BİNEK">BİNEK</option>
                <option value="BUS">BUS</option>
              </select>
            </div>
            <div class="field">
              <label for="vehicle_type">Alt Tip</label>
              <input id="vehicle_type" type="text" placeholder="Örn: Vito, Sprinter" />
            </div>
            <div class="field">
              <label for="model">Model</label>
              <input id="model" type="text" placeholder="Vito Tourer" />
            </div>
            <div class="field">
              <label for="model_year">Yıl</label>
              <input id="model_year" type="text" placeholder="2023" />
            </div>
            <div class="field">
              <label for="seat_capacity">Kapasite</label>
              <input id="seat_capacity" type="text" placeholder="8" />
            </div>
            <div class="field">
              <label for="luggage_capacity">Bagaj Kapasitesi / Hacmi</label>
              <input id="luggage_capacity" type="text" placeholder="Örn: 6 büyük valiz / 1100 lt" />
            </div>
            <div class="field">
              <label for="seat_type">Koltuk Tipi</label>
              <input id="seat_type" type="text" placeholder="VIP, standart, deri..." />
            </div>
            <div class="field full">
              <label for="vehicle_features">Temel Özellikler</label>
              <input id="vehicle_features" type="text" placeholder="Örn: klima, buzdolabı, priz, wi-fi" />
            </div>
            <div class="field full">
              <label for="vehicle_note">Operasyon Notu</label>
              <textarea id="vehicle_note" placeholder="Araçla ilgili kısa not"></textarea>
            </div>
            <div class="field full">
              <label>Ek Bilgi Alanları</label>
              <div id="vehicleExtraFields" class="extra-list"></div>
              <button id="addVehicleExtraFieldBtn" type="button" class="action-btn" style="margin-top:10px;">Ek Bilgi Alanı Ekle</button>
            </div>
          </div>
          <div class="action-row" style="margin-top:14px;">
            <button id="addVehicleBtn" type="button" class="action-btn primary">Araç Ekle</button>
          </div>
        </article>

        <article class="card">
          <h3>Kayıtlı Araç Listesi</h3>
          <div id="vehicleList" class="list"></div>
          <div id="vehicleStatus" class="status"></div>
        </article>
      </div>
    </section>
  </div>

  <script>
    (function () {
      var API_BASE = 'http://localhost:3001';
      var TOKEN_KEYS = ['fleet_access_token', 'platform_core_token', 'agency_access_token'];
      var saveBtn = document.getElementById('saveVehiclesBtn');
      var clearBtn = document.getElementById('clearVehiclesBtn');
      var addBtn = document.getElementById('addVehicleBtn');
      var listNode = document.getElementById('vehicleList');
      var statusNode = document.getElementById('vehicleStatus');
      var extraFieldsNode = document.getElementById('vehicleExtraFields');
      var addExtraFieldBtn = document.getElementById('addVehicleExtraFieldBtn');
      var editingIndex = -1;
      var extraFields = [];
      var categoryDefaults = {
        'VAN': { vehicle_type: 'Vito', model: 'Vito' },
        'MİNİ': { vehicle_type: 'Sprinter', model: 'Sprinter' },
        'MİDİ': { vehicle_type: 'Crafter', model: 'Crafter' },
        'BİNEK': { vehicle_type: 'Sedan', model: 'Egea' },
        'BUS': { vehicle_type: 'Otobüs', model: 'Travego' }
      };
      var fields = {
        vehicle_code: document.getElementById('vehicle_code'),
        plate_no: document.getElementById('plate_no'),
        vehicle_category: document.getElementById('vehicle_category'),
        vehicle_type: document.getElementById('vehicle_type'),
        model: document.getElementById('model'),
        model_year: document.getElementById('model_year'),
        seat_capacity: document.getElementById('seat_capacity'),
        luggage_capacity: document.getElementById('luggage_capacity'),
        seat_type: document.getElementById('seat_type'),
        vehicle_features: document.getElementById('vehicle_features'),
        vehicle_note: document.getElementById('vehicle_note')
      };
      var items = [];

      function readToken() {
        for (var i = 0; i < TOKEN_KEYS.length; i += 1) {
          var value = localStorage.getItem(TOKEN_KEYS[i]) || '';
          if (value) return value;
        }
        return '';
      }

      function showStatus(message) {
        statusNode.textContent = message;
        statusNode.classList.add('show');
        window.clearTimeout(window.__vehicleStatusTimer);
        window.__vehicleStatusTimer = window.setTimeout(function () {
          statusNode.classList.remove('show');
        }, 2600);
      }

      function clearForm() {
        Object.keys(fields).forEach(function (key) {
          fields[key].value = key === 'vehicle_category' ? 'VAN' : '';
        });
        extraFields = [];
        renderExtraFields();
        applyCategoryDefaults(true);
        editingIndex = -1;
        addBtn.textContent = 'Araç Ekle';
      }

      function fillForm(item, index) {
        fields.vehicle_code.value = item.vehicle_code || '';
        fields.plate_no.value = item.plate_no || '';
        fields.vehicle_category.value = item.vehicle_category || 'VAN';
        fields.vehicle_type.value = item.vehicle_type || '';
        fields.model.value = item.model || '';
        fields.model_year.value = item.model_year || '';
        fields.seat_capacity.value = item.seat_capacity || '';
        fields.luggage_capacity.value = item.luggage_capacity || '';
        fields.seat_type.value = item.seat_type || '';
        fields.vehicle_features.value = item.vehicle_features || '';
        fields.vehicle_note.value = item.vehicle_note || '';
        extraFields = Array.isArray(item.extra_fields) ? item.extra_fields.slice() : [];
        renderExtraFields();
        editingIndex = index;
        addBtn.textContent = 'Aracı Güncelle';
      }

      function escapeHtml(value) {
        return String(value || '')
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;')
          .replaceAll('"', '&quot;');
      }

      function renderExtraFields() {
        if (!extraFieldsNode) return;
        if (!extraFields.length) {
          extraFieldsNode.innerHTML = '<div class="multi-hint">Henüz ek bilgi alanı eklenmedi.</div>';
          return;
        }
        extraFieldsNode.innerHTML = extraFields.map(function (item, index) {
          return ''
            + '<div class="extra-item">'
            +   '<div class="field">'
            +     '<label>Alan Adı</label>'
            +     '<input type="text" data-extra-field="label" data-extra-index="' + index + '" value="' + escapeHtml(item.label || '') + '" placeholder="Örn: Wi-Fi Şifresi" />'
            +   '</div>'
            +   '<div class="field">'
            +     '<label>Değer</label>'
            +     '<input type="text" data-extra-field="value" data-extra-index="' + index + '" value="' + escapeHtml(item.value || '') + '" placeholder="Örn: Mevcut / Açıklama" />'
            +   '</div>'
            +   '<button class="extra-remove" type="button" data-remove-extra="' + index + '">Sil</button>'
            + '</div>';
        }).join('');
      }

      function applyCategoryDefaults(force) {
        var category = String(fields.vehicle_category.value || '').trim();
        var defaults = categoryDefaults[category];
        if (!defaults) return;
        if (force || !String(fields.vehicle_type.value || '').trim()) {
          fields.vehicle_type.value = defaults.vehicle_type || '';
        }
        if (force || !String(fields.model.value || '').trim()) {
          fields.model.value = defaults.model || '';
        }
      }

      function collectForm() {
        return {
          vehicle_code: fields.vehicle_code.value.trim(),
          plate_no: fields.plate_no.value.trim(),
          vehicle_category: fields.vehicle_category.value.trim(),
          vehicle_type: fields.vehicle_type.value.trim(),
          model: fields.model.value.trim(),
          model_year: fields.model_year.value.trim(),
          seat_capacity: fields.seat_capacity.value.trim(),
          luggage_capacity: fields.luggage_capacity.value.trim(),
          seat_type: fields.seat_type.value.trim(),
          vehicle_features: fields.vehicle_features.value.trim(),
          vehicle_note: fields.vehicle_note.value.trim(),
          extra_fields: extraFields.slice()
        };
      }

      function renderList() {
        if (!items.length) {
          listNode.innerHTML = '<div class="vehicle-item"><strong>Henüz araç eklenmedi</strong><span>İlk araç kartını soldaki form ile ekleyin.</span></div>';
          return;
        }
        listNode.innerHTML = items.map(function (item, index) {
          var tags = [];
          if (item.vehicle_category) tags.push(item.vehicle_category);
          if (item.vehicle_type) tags.push(item.vehicle_type);
          if (item.seat_capacity) tags.push(item.seat_capacity + ' koltuk');
          if (item.luggage_capacity) tags.push(item.luggage_capacity);
          return ''
            + '<div class="vehicle-item">'
            +   '<div class="item-head">'
            +     '<strong>' + (item.model || '-') + ' / ' + (item.plate_no || '-') + '</strong>'
            +     '<div class="item-actions compact"><button type="button" class="item-btn edit" data-edit-index="' + index + '">Düzenle</button><button type="button" class="item-btn remove" data-remove-index="' + index + '">Kaldır</button></div>'
            +   '</div>'
            +   '<span>Kod: ' + (item.vehicle_code || '-') + ' | Yıl: ' + (item.model_year || '-') + ' | Koltuk tipi: ' + (item.seat_type || '-') + '</span>'
            +   '<span>Not: ' + (item.vehicle_note || '-') + '</span>'
            +   '<div class="vehicle-tags">' + tags.map(function (tag) { return '<i>' + tag + '</i>'; }).join('') + '</div>'
            +   ((Array.isArray(item.extra_fields) && item.extra_fields.length)
                  ? '<div class="vehicle-tags">' + item.extra_fields.filter(function (entry) { return entry && (entry.label || entry.value); }).map(function (entry) { return '<i>' + (entry.label || '-') + ': ' + (entry.value || '-') + '</i>'; }).join('') + '</div>'
                  : '')
            + '</div>';
        }).join('');
      }

      async function loadItems() {
        var token = readToken();
        if (!token) return;
        try {
          var res = await fetch(API_BASE + '/vehicle-cards', {
            headers: { Authorization: 'Bearer ' + token }
          });
          if (!res.ok) return;
          var data = await res.json();
          items = Array.isArray(data.items) ? data.items : [];
          renderList();
        } catch (_) {}
      }

      async function saveItems() {
        var token = readToken();
        if (!token) {
          showStatus('Oturum bulunamadı. Yeniden giriş yapın.');
          return;
        }
        try {
          var res = await fetch(API_BASE + '/vehicle-cards', {
            method: 'PUT',
            headers: {
              Authorization: 'Bearer ' + token,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ items: items })
          });
          if (!res.ok) {
            showStatus('Araç listesi çekirdeğe kaydedilemedi.');
            return;
          }
          showStatus('Araç listesi çekirdeğe kaydedildi.');
        } catch (_) {
          showStatus('Araç listesi çekirdeğe kaydedilemedi.');
        }
      }

      addBtn.addEventListener('click', function () {
        var item = collectForm();
        var isEditing = editingIndex >= 0;
        if (!item.vehicle_code || !item.plate_no || !item.model) {
          showStatus('Araç kodu, plaka ve model zorunludur.');
          return;
        }
        if (isEditing) items.splice(editingIndex, 1, item);
        else items.unshift(item);
        renderList();
        clearForm();
        showStatus(isEditing ? 'Araç güncellendi. Kaydet ile çekirdeğe yazabilirsiniz.' : 'Araç listeye eklendi. Kaydet ile çekirdeğe yazabilirsiniz.');
      });

      saveBtn.addEventListener('click', saveItems);
      clearBtn.addEventListener('click', function () {
        clearForm();
        showStatus('Form temizlendi.');
      });

      listNode.addEventListener('click', function (event) {
        var editBtn = event.target.closest('[data-edit-index]');
        if (editBtn) {
          var editIndex = parseInt(editBtn.getAttribute('data-edit-index'), 10);
          if (!Number.isNaN(editIndex) && items[editIndex]) {
            fillForm(items[editIndex], editIndex);
            showStatus('Araç kartı düzenleme için forma taşındı.');
          }
          return;
        }
        var btn = event.target.closest('[data-remove-index]');
        if (!btn) return;
        var index = parseInt(btn.getAttribute('data-remove-index'), 10);
        if (Number.isNaN(index)) return;
        items.splice(index, 1);
        renderList();
        showStatus('Araç listeden kaldırıldı. Kaydet ile çekirdeğe yazabilirsiniz.');
      });

      clearForm();
      renderList();
      loadItems();
    })();
  </script>
</body>
</html>
    """


@app.get("/drivers", response_class=HTMLResponse)
def driver_cards_page() -> str:
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Sürücü Kartları</title>
  <style>
    :root {
      --bg-1: #081d1d;
      --bg-2: #0d3934;
      --bg-3: #0a2724;
      --panel: rgba(7, 28, 27, 0.82);
      --panel-line: rgba(129, 223, 197, 0.22);
      --card-bg: linear-gradient(180deg, rgba(246, 255, 252, 0.97) 0%, rgba(232, 247, 242, 0.93) 100%);
      --card-line: rgba(132, 220, 193, 0.52);
      --ink: #12332d;
      --muted: #45655f;
      --accent: #24b389;
      --white: #f7fbfb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--white);
      background:
        radial-gradient(circle at right top, rgba(36,179,137,0.20), transparent 28%),
        linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 56%, var(--bg-3) 100%);
      background-attachment: fixed;
    }
    .wrap { width: min(1240px, calc(100% - 32px)); margin: 22px auto 40px; }
    .head, .panel {
      background: var(--panel);
      border: 1px solid var(--panel-line);
      border-radius: 20px;
      backdrop-filter: blur(10px);
      box-shadow: 0 18px 36px rgba(2, 12, 12, 0.28);
    }
    .head {
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:12px;
      padding:14px 16px;
      margin-bottom:16px;
    }
    .head a {
      color:#dcfff6;
      text-decoration:none;
      border:1px solid rgba(132,220,193,0.22);
      background:rgba(255,255,255,0.06);
      min-height:38px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      border-radius:12px;
      padding:0 14px;
      font-weight:700;
      font-size:13px;
    }
    .head strong { display:block; font-size:22px; }
    .head span { color:#a2d4ca; font-size:12px; }
    .panel { padding:24px; }
    .toolbar {
      display:flex;
      justify-content:space-between;
      gap:12px;
      align-items:flex-start;
      flex-wrap:wrap;
      margin-bottom:18px;
    }
    .toolbar p {
      margin:0;
      color:#b9d7d0;
      line-height:1.65;
      font-size:13px;
      max-width:70ch;
    }
    .action-row {
      display:flex;
      gap:10px;
      flex-wrap:wrap;
    }
    .action-btn {
      min-height:40px;
      border-radius:12px;
      padding:0 14px;
      border:1px solid rgba(132,220,193,0.22);
      background:rgba(255,255,255,0.06);
      color:#dcfff6;
      font-weight:700;
      cursor:pointer;
    }
    .action-btn.primary {
      color:#06271e;
      background: linear-gradient(180deg, #59e0b4 0%, #22b28a 100%);
      border-color: transparent;
      box-shadow: 0 10px 20px rgba(36,179,137,0.18);
    }
    .layout {
      display:grid;
      grid-template-columns: 420px 1fr;
      gap:16px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-line);
      border-radius: 18px;
      padding: 18px;
      color: var(--ink);
      box-shadow: 0 16px 30px rgba(2, 14, 13, 0.18);
    }
    .card h3 { margin:0 0 12px; font-size:18px; }
    .field-grid {
      display:grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap:12px;
    }
    .field {
      display:grid;
      gap:7px;
    }
    .field.full {
      grid-column: 1 / -1;
    }
    .field label {
      font-size:12px;
      font-weight:800;
      color:#0f7b60;
    }
    .field input, .field select, .field textarea {
      width:100%;
      min-height:42px;
      border-radius:14px;
      border:1px solid rgba(15, 123, 96, 0.16);
      background:rgba(255,255,255,0.78);
      color:var(--ink);
      padding:10px 12px;
      outline:none;
      font-family:inherit;
      font-size:13px;
    }
    .field textarea {
      min-height:90px;
      resize:vertical;
    }
    .field input:focus, .field select:focus, .field textarea:focus {
      border-color:rgba(36,179,137,0.58);
      box-shadow:0 0 0 4px rgba(36,179,137,0.10);
    }
    .list {
      display:grid;
      gap:12px;
    }
    .driver-item {
      border:1px solid rgba(15, 123, 96, 0.22);
      border-radius:18px;
      padding:14px;
      background:rgba(255,255,255,0.78);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.42);
    }
    .item-head {
      display:flex;
      justify-content:space-between;
      gap:12px;
      align-items:flex-start;
    }
    .driver-item strong {
      display:block;
      font-size:15px;
      margin-bottom:6px;
    }
    .driver-item span {
      display:block;
      color:var(--muted);
      font-size:12px;
      line-height:1.55;
    }
    .driver-tags {
      display:flex;
      flex-wrap:wrap;
      gap:8px;
      margin-top:10px;
    }
    .driver-tags i {
      display:inline-flex;
      align-items:center;
      min-height:28px;
      padding:0 10px;
      border-radius:999px;
      background:rgba(36,179,137,0.12);
      border:1px solid rgba(36,179,137,0.18);
      color:#0f7b60;
      font-style:normal;
      font-size:11px;
      font-weight:800;
    }
    .item-actions.compact {
      display:flex;
      gap:8px;
      flex-wrap:wrap;
    }
    .item-btn {
      min-height:34px;
      border-radius:11px;
      padding:0 12px;
      border:none;
      font-weight:800;
      font-size:12px;
      cursor:pointer;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      box-shadow: 0 10px 18px rgba(2, 14, 13, 0.10);
    }
    .item-btn.edit {
      background:linear-gradient(180deg, #d9f6ee 0%, #b8eadc 100%);
      color:#0e5c49;
      border:1px solid rgba(14, 92, 73, 0.18);
    }
    .item-btn.remove {
      background:linear-gradient(180deg, #ffe3e0 0%, #ffc8c0 100%);
      color:#8f2418;
      border:1px solid rgba(143, 36, 24, 0.16);
    }
    .multi-select {
      display:grid;
      gap:8px;
    }
    .dropdown-trigger {
      width:100%;
      min-height:46px;
      border-radius:14px;
      border:1px solid rgba(15, 123, 96, 0.16);
      background:rgba(255,255,255,0.78);
      color:var(--ink);
      padding:0 12px;
      display:flex;
      align-items:center;
      justify-content:space-between;
      font-weight:700;
      cursor:pointer;
    }
    .dropdown-menu {
      display:none;
      border:1px solid rgba(15, 123, 96, 0.18);
      background:#f5fffb;
      border-radius:14px;
      padding:12px;
    }
    .dropdown-menu.open { display:grid; gap:10px; }
    .multi-option-grid {
      display:grid;
      grid-template-columns:repeat(4, minmax(0, 1fr));
      gap:8px;
    }
    .multi-option-btn {
      min-height:40px;
      border-radius:12px;
      border:1px solid rgba(15, 123, 96, 0.18);
      background:#ffffff;
      color:#205047;
      font-weight:800;
      cursor:pointer;
    }
    .multi-option-btn.selected {
      background:var(--accent);
      color:#ffffff;
      border-color:var(--accent);
    }
    .dropdown-actions {
      display:flex;
      justify-content:space-between;
      gap:8px;
    }
    .dropdown-action-btn {
      min-height:38px;
      border-radius:12px;
      border:1px solid rgba(15, 123, 96, 0.18);
      background:#ffffff;
      color:#205047;
      font-weight:700;
      cursor:pointer;
      padding:0 12px;
    }
    .multi-hint {
      color:#5e7f78;
      font-size:12px;
      line-height:1.5;
    }
    .extra-list {
      display:grid;
      gap:10px;
      margin-top:6px;
    }
    .extra-item {
      display:grid;
      grid-template-columns:1fr 1.2fr auto;
      gap:8px;
      align-items:center;
    }
    .extra-remove {
      min-height:42px;
      min-width:42px;
      border-radius:12px;
      border:1px solid rgba(143, 36, 24, 0.16);
      background:#ffe3e0;
      color:#8f2418;
      font-weight:800;
      cursor:pointer;
    }
    .multi-hint {
      color:#5e7f78;
      font-size:12px;
      line-height:1.5;
    }
    .status {
      margin-top:16px;
      border-radius:14px;
      padding:12px 14px;
      background:rgba(36, 179, 137, 0.12);
      border:1px solid rgba(36, 179, 137, 0.20);
      color:#d7fbef;
      font-size:12px;
      line-height:1.6;
      display:none;
    }
    .status.show { display:block; }
    @media (max-width: 960px) {
      .layout { grid-template-columns: 1fr; }
      .field-grid { grid-template-columns: 1fr; }
      .multi-option-grid, .extra-item { grid-template-columns: 1fr; }
      .item-head { flex-direction:column; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="head">
      <div>
        <strong>Sürücü Kartları</strong>
        <span>İletişim, kimlik, doğum tarihi, dil, ehliyet ve operasyon detaylarının ilk kayıt ekranı</span>
      </div>
      <a href="/panel">Panele Dön</a>
    </section>

    <section class="panel">
      <div class="toolbar">
        <p>
          Bu ilk sürümde sürücü kartları temel veri alanlarıyla kaydedilir. Sonraki adımda belge takibi,
          vardiya uygunluğu, mesai görünümü ve proje bazlı araç eşleştirme yapısı eklenecek.
        </p>
        <div class="action-row">
          <button id="saveDriversBtn" type="button" class="action-btn primary">Listeyi Kaydet</button>
          <button id="clearDriversBtn" type="button" class="action-btn">Formu Temizle</button>
        </div>
      </div>

      <div class="layout">
        <article class="card">
          <h3>Yeni Sürücü Kartı</h3>
          <div class="field-grid">
            <div class="field">
              <label for="driver_code">Sürücü Kodu</label>
              <input id="driver_code" type="text" placeholder="Örn: DRV-001" />
            </div>
            <div class="field">
              <label for="full_name">Ad Soyad</label>
              <input id="full_name" type="text" placeholder="Sürücü adı" />
            </div>
            <div class="field">
              <label for="phone">Telefon</label>
              <input id="phone" type="text" placeholder="+90 5xx xxx xx xx" />
            </div>
            <div class="field">
              <label for="tc_kimlik_no">T.C. Kimlik No</label>
              <input id="tc_kimlik_no" type="text" inputmode="numeric" maxlength="11" placeholder="11 haneli T.C. Kimlik No" />
            </div>
            <div class="field">
              <label for="birth_date">Doğum Tarihi</label>
              <input id="birth_date" type="date" />
            </div>
            <div class="field full">
              <label for="address">Adres</label>
              <input id="address" type="text" placeholder="Açık adres" />
            </div>
            <div class="field">
              <label for="languages">Yabancı Dil</label>
              <input id="languages" type="text" placeholder="İngilizce, Almanca..." />
            </div>
            <div class="field full">
              <label for="license_class">Ehliyet Sınıfı</label>
              <div class="multi-select">
                <button id="licenseClassTrigger" type="button" class="dropdown-trigger">
                  <strong id="licenseClassLabel">B1</strong>
                  <span>Seç</span>
                </button>
                <div id="licenseClassMenu" class="dropdown-menu">
                  <div id="licenseClassOptions" class="multi-option-grid">
                    <button type="button" class="multi-option-btn" data-value="A1">A1</button>
                    <button type="button" class="multi-option-btn" data-value="A2">A2</button>
                    <button type="button" class="multi-option-btn" data-value="A">A</button>
                    <button type="button" class="multi-option-btn" data-value="B1">B1</button>
                    <button type="button" class="multi-option-btn" data-value="B">B</button>
                    <button type="button" class="multi-option-btn" data-value="BE">BE</button>
                    <button type="button" class="multi-option-btn" data-value="C1">C1</button>
                    <button type="button" class="multi-option-btn" data-value="C1E">C1E</button>
                    <button type="button" class="multi-option-btn" data-value="C">C</button>
                    <button type="button" class="multi-option-btn" data-value="CE">CE</button>
                    <button type="button" class="multi-option-btn" data-value="D1">D1</button>
                    <button type="button" class="multi-option-btn" data-value="D1E">D1E</button>
                    <button type="button" class="multi-option-btn" data-value="D">D</button>
                    <button type="button" class="multi-option-btn" data-value="DE">DE</button>
                    <button type="button" class="multi-option-btn" data-value="F">F</button>
                    <button type="button" class="multi-option-btn" data-value="M">M</button>
                    <button type="button" class="multi-option-btn" data-value="G">G</button>
                  </div>
                  <div class="dropdown-actions">
                    <button id="licenseClassClear" type="button" class="dropdown-action-btn">Seçimi Temizle</button>
                    <button id="licenseClassDone" type="button" class="dropdown-action-btn">Tamam</button>
                  </div>
                </div>
                <input id="license_class_custom" type="text" placeholder="Ek sınıf varsa yazın: örn. A, DE" />
                <div class="multi-hint">Liste açıldığında istediğiniz sınıflara tek tek basın. Seçilenler ana renk ile işaretlenir.</div>
              </div>
            </div>
            <div class="field">
              <label for="employment_type">Kaynak Tipi</label>
              <select id="employment_type">
                <option value="internal">Araç Firması</option>
                <option value="external">Dışarıdan</option>
              </select>
            </div>
            <div class="field">
              <label for="access_type">Erişim Tipi</label>
              <select id="access_type">
                <option value="portal">Portal</option>
                <option value="link">Link</option>
              </select>
            </div>
            <div class="field full">
              <label>Ek Bilgi Alanları</label>
              <div id="extraFields" class="extra-list"></div>
              <button id="addExtraFieldBtn" type="button" class="action-btn">Ek Bilgi Alanı Ekle</button>
            </div>
            <div class="field full">
              <label for="driver_note">Operasyon Notu</label>
              <textarea id="driver_note" placeholder="Sürücü ile ilgili kısa not"></textarea>
            </div>
          </div>
          <div class="action-row" style="margin-top:14px;">
            <button id="addDriverBtn" type="button" class="action-btn primary">Sürücü Ekle</button>
          </div>
        </article>

        <article class="card">
          <h3>Kayıtlı Sürücü Listesi</h3>
          <div id="driverList" class="list"></div>
          <div id="driverStatus" class="status"></div>
        </article>
      </div>
    </section>
  </div>

  <script>
    (function () {
      var API_BASE = 'http://localhost:3001';
      var TOKEN_KEYS = ['fleet_access_token', 'platform_core_token', 'agency_access_token'];
      var saveBtn = document.getElementById('saveDriversBtn');
      var clearBtn = document.getElementById('clearDriversBtn');
      var addBtn = document.getElementById('addDriverBtn');
      var listNode = document.getElementById('driverList');
      var statusNode = document.getElementById('driverStatus');
      var extraFieldsNode = document.getElementById('extraFields');
      var addExtraFieldBtn = document.getElementById('addExtraFieldBtn');
      var editingIndex = -1;
      var internalSourceLabel = 'Araç Firması';
      var extraFields = [];
      var licenseClassTrigger = document.getElementById('licenseClassTrigger');
      var licenseClassLabel = document.getElementById('licenseClassLabel');
      var licenseClassMenu = document.getElementById('licenseClassMenu');
      var licenseClassClear = document.getElementById('licenseClassClear');
      var licenseClassDone = document.getElementById('licenseClassDone');
      var fields = {
        driver_code: document.getElementById('driver_code'),
        full_name: document.getElementById('full_name'),
        phone: document.getElementById('phone'),
        tc_kimlik_no: document.getElementById('tc_kimlik_no'),
        birth_date: document.getElementById('birth_date'),
        address: document.getElementById('address'),
        languages: document.getElementById('languages'),
        license_class_custom: document.getElementById('license_class_custom'),
        employment_type: document.getElementById('employment_type'),
        access_type: document.getElementById('access_type'),
        driver_note: document.getElementById('driver_note')
      };
      var licenseClassOptions = Array.prototype.slice.call(document.querySelectorAll('#licenseClassOptions .multi-option-btn'));
      var items = [];

      function readToken() {
        for (var i = 0; i < TOKEN_KEYS.length; i += 1) {
          var value = localStorage.getItem(TOKEN_KEYS[i]) || '';
          if (value) return value;
        }
        return '';
      }

      async function loadCompanySourceLabel() {
        var token = readToken();
        if (!token) return;
        try {
          var res = await fetch(API_BASE + '/company-card-draft', {
            headers: { Authorization: 'Bearer ' + token }
          });
          if (!res.ok) return;
          var data = await res.json();
          var companyName = String((((data || {}).data || {}).company_name) || '').trim();
          internalSourceLabel = companyName || 'Araç Firması';
          Array.prototype.slice.call(document.querySelectorAll('#employment_type option[value="internal"]')).forEach(function (node) {
            node.textContent = internalSourceLabel;
          });
          renderList();
        } catch (_) {}
      }

      function showStatus(message) {
        statusNode.textContent = message;
        statusNode.classList.add('show');
        window.clearTimeout(window.__driverStatusTimer);
        window.__driverStatusTimer = window.setTimeout(function () {
          statusNode.classList.remove('show');
        }, 2600);
      }

      function clearForm() {
        Object.keys(fields).forEach(function (key) {
          if (key === 'employment_type') fields[key].value = 'internal';
          else if (key === 'access_type') fields[key].value = 'portal';
          else fields[key].value = '';
        });
        setLicenseClassValue('B1');
        extraFields = [];
        renderExtraFields();
        editingIndex = -1;
        addBtn.textContent = 'Sürücü Ekle';
        setNextCode();
      }

      function escapeHtml(value) {
        return String(value || '').replace(/[&<>"]/g, function (char) {
          return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[char] || char;
        });
      }

      function normalizeExtraFields(values) {
        return (Array.isArray(values) ? values : []).map(function (item) {
          return {
            label: String((item || {}).label || '').trim(),
            value: String((item || {}).value || '').trim()
          };
        }).filter(function (item) { return item.label || item.value; });
      }

      function renderExtraFields() {
        if (!extraFields.length) {
          extraFieldsNode.innerHTML = '<div class="multi-hint">Kart üzerinde görünmesini istediğiniz özel alanları buradan ekleyebilirsiniz.</div>';
          return;
        }
        extraFieldsNode.innerHTML = extraFields.map(function (item, index) {
          return ''
            + '<div class="extra-item">'
            +   '<input type="text" data-extra-index="' + index + '" data-extra-field="label" placeholder="Alan adı" value="' + escapeHtml(item.label || '') + '" />'
            +   '<input type="text" data-extra-index="' + index + '" data-extra-field="value" placeholder="Değer" value="' + escapeHtml(item.value || '') + '" />'
            +   '<button type="button" class="extra-remove" data-remove-extra="' + index + '">×</button>'
            + '</div>';
        }).join('');
      }

      function updateLicenseClassLabel() {
        var value = getLicenseClassValue();
        licenseClassLabel.textContent = value || 'Seçim yapın';
      }

      function openLicenseMenu() {
        licenseClassMenu.classList.add('open');
      }

      function closeLicenseMenu() {
        licenseClassMenu.classList.remove('open');
      }

      function nextCode(prefix) {
        var maxNumber = 0;
        items.forEach(function (item) {
          var match = String(item[prefix === 'DRV' ? 'driver_code' : 'greeter_code'] || '').match(new RegExp('^' + prefix + '-(\\d+)$'));
          if (!match) return;
          var value = parseInt(match[1], 10);
          if (!Number.isNaN(value) && value > maxNumber) maxNumber = value;
        });
        return prefix + '-' + String(maxNumber + 1).padStart(3, '0');
      }

      function setNextCode() {
        fields.driver_code.value = nextCode('DRV');
      }

      function calculateAge(birthDate) {
        if (!birthDate) return '';
        var parts = birthDate.split('-').map(function (item) { return parseInt(item, 10); });
        if (parts.length !== 3 || parts.some(function (item) { return Number.isNaN(item); })) return '';
        var today = new Date();
        var age = today.getFullYear() - parts[0];
        var monthDiff = (today.getMonth() + 1) - parts[1];
        var dayDiff = today.getDate() - parts[2];
        if (monthDiff < 0 || (monthDiff === 0 && dayDiff < 0)) age -= 1;
        return age >= 0 ? String(age) : '';
      }

      function normalizeDisplayPhone(value) {
        var digits = String(value || '').replace(/\D+/g, '');
        if (!digits) return '';
        if (digits.charAt(0) === '0' && digits.length === 11) digits = '90' + digits.slice(1);
        if (digits.charAt(0) === '5' && digits.length === 10) digits = '90' + digits;
        if (digits.indexOf('90') === 0 && digits.length === 12) {
          return '+90 ' + digits.slice(2, 5) + ' ' + digits.slice(5, 8) + ' ' + digits.slice(8, 10) + ' ' + digits.slice(10, 12);
        }
        return String(value || '').trim();
      }

      function normalizeTcKimlikNo(value) {
        var digits = String(value || '').replace(/\D+/g, '');
        return digits.length === 11 ? digits : '';
      }

      function splitLicenseClasses(value) {
        return String(value || '')
          .split(',')
          .map(function (item) { return item.trim(); })
          .filter(Boolean);
      }

      function getLicenseClassValue() {
        var selected = licenseClassOptions.filter(function (option) { return option.classList.contains('selected'); }).map(function (option) { return option.getAttribute('data-value') || ''; });
        var extras = splitLicenseClasses(fields.license_class_custom.value);
        var seen = {};
        return selected.concat(extras).filter(function (item) {
          var key = item.toUpperCase();
          if (seen[key]) return false;
          seen[key] = true;
          return true;
        }).join(', ');
      }

      function setLicenseClassValue(value) {
        var parts = splitLicenseClasses(value);
        var known = {};
        licenseClassOptions.forEach(function (option) {
          var code = String(option.getAttribute('data-value') || '');
          var hasValue = parts.some(function (part) { return part.toUpperCase() === code.toUpperCase(); });
          option.classList.toggle('selected', hasValue);
          if (hasValue) known[code.toUpperCase()] = true;
        });
        fields.license_class_custom.value = parts.filter(function (part) { return !known[part.toUpperCase()]; }).join(', ');
        updateLicenseClassLabel();
      }

      function fillForm(item, index) {
        fields.driver_code.value = item.driver_code || nextCode('DRV');
        fields.full_name.value = item.full_name || '';
        fields.phone.value = item.phone || '';
        fields.tc_kimlik_no.value = item.tc_kimlik_no || '';
        fields.birth_date.value = item.birth_date || '';
        fields.address.value = item.address || '';
        fields.languages.value = item.languages || '';
        setLicenseClassValue(item.license_class || '');
        fields.employment_type.value = item.employment_type || 'internal';
        fields.access_type.value = item.access_type || 'portal';
        fields.driver_note.value = item.driver_note || '';
        extraFields = normalizeExtraFields(item.extra_fields || []);
        renderExtraFields();
        editingIndex = index;
        addBtn.textContent = 'Sürücüyü Güncelle';
      }

      function collectForm() {
        return {
          driver_code: fields.driver_code.value.trim(),
          full_name: fields.full_name.value.trim(),
          phone: normalizeDisplayPhone(fields.phone.value),
          tc_kimlik_no: normalizeTcKimlikNo(fields.tc_kimlik_no.value),
          birth_date: fields.birth_date.value.trim(),
          age: calculateAge(fields.birth_date.value.trim()),
          address: fields.address.value.trim(),
          languages: fields.languages.value.trim(),
          license_class: getLicenseClassValue(),
          employment_type: fields.employment_type.value.trim(),
          access_type: fields.access_type.value.trim(),
          driver_note: fields.driver_note.value.trim(),
          extra_fields: normalizeExtraFields(extraFields)
        };
      }

      function renderList() {
        if (!items.length) {
          listNode.innerHTML = '<div class="driver-item"><strong>Henüz sürücü eklenmedi</strong><span>İlk sürücü kartını soldaki form ile ekleyin.</span></div>';
          return;
        }
        listNode.innerHTML = items.map(function (item, index) {
          var tags = [];
          if (item.languages) tags.push(item.languages);
          if (item.license_class) tags.push('Ehliyet: ' + item.license_class);
          if (item.employment_type === 'internal') tags.push(internalSourceLabel);
          if (item.employment_type === 'external') tags.push('Dışarıdan');
          if (item.access_type === 'portal') tags.push('Portal');
          if (item.access_type === 'link') tags.push('Link');
          return ''
            + '<div class="driver-item">'
            +   '<div class="item-head">'
            +     '<div>'
            +       '<strong>' + escapeHtml(item.full_name || '-') + ' / ' + escapeHtml(item.phone || '-') + '</strong>'
            +       '<span>Kod: ' + escapeHtml(item.driver_code || '-') + ' | T.C.: ' + escapeHtml(item.tc_kimlik_no || '-') + ' | Doğum: ' + escapeHtml(item.birth_date || '-') + ' | Yaş: ' + escapeHtml(item.age || '-') + '</span>'
            +       '<span>Adres: ' + escapeHtml(item.address || '-') + '</span>'
            +       '<span>Not: ' + escapeHtml(item.driver_note || '-') + '</span>'
            +     '</div>'
            +     '<div class="item-actions compact"><button type="button" class="item-btn edit" data-edit-index="' + index + '">Düzenle</button><button type="button" class="item-btn remove" data-remove-index="' + index + '">Kaldır</button></div>'
            +   '</div>'
            +   '<div class="driver-tags">' + tags.concat((item.extra_fields || []).map(function (field) { return (field.label || 'Ek Bilgi') + ': ' + (field.value || '-'); })).map(function (tag) { return '<i>' + escapeHtml(tag) + '</i>'; }).join('') + '</div>'
            + '</div>';
        }).join('');
      }

      async function loadItems() {
        var token = readToken();
        if (!token) return;
        try {
          var res = await fetch(API_BASE + '/driver-cards', {
            headers: { Authorization: 'Bearer ' + token }
          });
          if (!res.ok) return;
          var data = await res.json();
          items = Array.isArray(data.items) ? data.items : [];
          setNextCode();
          renderList();
        } catch (_) {}
      }

      async function saveItems() {
        var token = readToken();
        if (!token) {
          showStatus('Oturum bulunamadı. Yeniden giriş yapın.');
          return;
        }
        try {
          var res = await fetch(API_BASE + '/driver-cards', {
            method: 'PUT',
            headers: {
              Authorization: 'Bearer ' + token,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ items: items })
          });
          if (!res.ok) {
            showStatus('Sürücü listesi çekirdeğe kaydedilemedi.');
            return;
          }
          showStatus('Sürücü listesi çekirdeğe kaydedildi.');
        } catch (_) {
          showStatus('Sürücü listesi çekirdeğe kaydedilemedi.');
        }
      }

      addBtn.addEventListener('click', function () {
        var item = collectForm();
        var isEditing = editingIndex >= 0;
        if (!item.driver_code || !item.full_name || !item.phone) {
          showStatus('Sürücü kodu, ad soyad ve telefon zorunludur.');
          return;
        }
        if (fields.tc_kimlik_no.value.trim() && !item.tc_kimlik_no) {
          showStatus('T.C. Kimlik No geçersiz. Bilinmiyorsa 11111111111 kullanın.');
          return;
        }
        fields.phone.value = item.phone || '';
        fields.tc_kimlik_no.value = item.tc_kimlik_no || '';
        if (isEditing) items.splice(editingIndex, 1, item);
        else items.unshift(item);
        renderList();
        clearForm();
        showStatus(isEditing ? 'Sürücü güncellendi. Kaydet ile çekirdeğe yazabilirsiniz.' : 'Sürücü listeye eklendi. Kaydet ile çekirdeğe yazabilirsiniz.');
      });

      saveBtn.addEventListener('click', saveItems);
      clearBtn.addEventListener('click', function () {
        clearForm();
        showStatus('Form temizlendi.');
      });
      if (addExtraFieldBtn) {
        addExtraFieldBtn.addEventListener('click', function () {
          extraFields.push({ label: '', value: '' });
          renderExtraFields();
        });
      }
      if (extraFieldsNode) {
        extraFieldsNode.addEventListener('click', function (event) {
          var btn = event.target.closest('[data-remove-extra]');
          if (!btn) return;
          var index = parseInt(btn.getAttribute('data-remove-extra'), 10);
          if (Number.isNaN(index)) return;
          extraFields = extraFields.filter(function (_, current) { return current !== index; });
          renderExtraFields();
        });
        extraFieldsNode.addEventListener('input', function (event) {
          var field = event.target && event.target.getAttribute('data-extra-field');
          var index = parseInt(event.target && event.target.getAttribute('data-extra-index'), 10);
          if (!field || Number.isNaN(index) || !extraFields[index]) return;
          extraFields[index][field] = event.target.value || '';
        });
      }
      licenseClassTrigger.addEventListener('click', function () {
        if (licenseClassMenu.classList.contains('open')) closeLicenseMenu();
        else openLicenseMenu();
      });
      licenseClassClear.addEventListener('click', function () {
        setLicenseClassValue('');
      });
      licenseClassDone.addEventListener('click', function () {
        updateLicenseClassLabel();
        closeLicenseMenu();
      });
      licenseClassOptions.forEach(function (option) {
        option.addEventListener('click', function () {
          option.classList.toggle('selected');
          updateLicenseClassLabel();
        });
      });
      document.addEventListener('click', function (event) {
        if (!event.target.closest('.multi-select')) closeLicenseMenu();
      });

      listNode.addEventListener('click', function (event) {
        var editBtn = event.target.closest('[data-edit-index]');
        if (editBtn) {
          var editIndex = parseInt(editBtn.getAttribute('data-edit-index'), 10);
          if (!Number.isNaN(editIndex) && items[editIndex]) {
            fillForm(items[editIndex], editIndex);
            showStatus('Sürücü kartı düzenleme için forma taşındı.');
          }
          return;
        }
        var btn = event.target.closest('[data-remove-index]');
        if (!btn) return;
        var index = parseInt(btn.getAttribute('data-remove-index'), 10);
        if (Number.isNaN(index)) return;
        items.splice(index, 1);
        renderList();
        showStatus('Sürücü listeden kaldırıldı. Kaydet ile çekirdeğe yazabilirsiniz.');
      });

      clearForm();
      renderExtraFields();
      renderList();
      loadItems();
      loadCompanySourceLabel();
    })();
  </script>
</body>
</html>
    """


@app.get("/greeters", response_class=HTMLResponse)
def greeter_cards_page() -> str:
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Karşılamacı Kartları</title>
  <style>
    :root {
      --bg-1: #081d1d;
      --bg-2: #0d3934;
      --bg-3: #0a2724;
      --panel: rgba(7, 28, 27, 0.82);
      --panel-line: rgba(129, 223, 197, 0.22);
      --card-bg: linear-gradient(180deg, rgba(246, 255, 252, 0.97) 0%, rgba(232, 247, 242, 0.93) 100%);
      --card-line: rgba(132, 220, 193, 0.52);
      --ink: #12332d;
      --muted: #45655f;
      --accent: #24b389;
      --white: #f7fbfb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--white);
      background:
        radial-gradient(circle at right top, rgba(36,179,137,0.20), transparent 28%),
        linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 56%, var(--bg-3) 100%);
      background-attachment: fixed;
    }
    .wrap { width: min(1240px, calc(100% - 32px)); margin: 22px auto 40px; }
    .head, .panel {
      background: var(--panel);
      border: 1px solid var(--panel-line);
      border-radius: 20px;
      backdrop-filter: blur(10px);
      box-shadow: 0 18px 36px rgba(2, 12, 12, 0.28);
    }
    .head {
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:12px;
      padding:14px 16px;
      margin-bottom:16px;
    }
    .head a {
      color:#dcfff6;
      text-decoration:none;
      border:1px solid rgba(132,220,193,0.22);
      background:rgba(255,255,255,0.06);
      min-height:38px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      border-radius:12px;
      padding:0 14px;
      font-weight:700;
      font-size:13px;
    }
    .head strong { display:block; font-size:22px; }
    .head span { color:#a2d4ca; font-size:12px; }
    .panel { padding:24px; }
    .toolbar {
      display:flex;
      justify-content:space-between;
      gap:12px;
      align-items:flex-start;
      flex-wrap:wrap;
      margin-bottom:18px;
    }
    .toolbar p {
      margin:0;
      color:#b9d7d0;
      line-height:1.65;
      font-size:13px;
      max-width:70ch;
    }
    .action-row {
      display:flex;
      gap:10px;
      flex-wrap:wrap;
    }
    .action-btn {
      min-height:40px;
      border-radius:12px;
      padding:0 14px;
      border:1px solid rgba(132,220,193,0.22);
      background:rgba(255,255,255,0.06);
      color:#dcfff6;
      font-weight:700;
      cursor:pointer;
    }
    .action-btn.primary {
      color:#06271e;
      background: linear-gradient(180deg, #59e0b4 0%, #22b28a 100%);
      border-color: transparent;
      box-shadow: 0 10px 20px rgba(36,179,137,0.18);
    }
    .layout {
      display:grid;
      grid-template-columns: 420px 1fr;
      gap:16px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-line);
      border-radius: 18px;
      padding: 18px;
      color: var(--ink);
      box-shadow: 0 16px 30px rgba(2, 14, 13, 0.18);
    }
    .card h3 { margin:0 0 12px; font-size:18px; }
    .field-grid {
      display:grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap:12px;
    }
    .field {
      display:grid;
      gap:7px;
    }
    .field.full {
      grid-column: 1 / -1;
    }
    .field label {
      font-size:12px;
      font-weight:800;
      color:#0f7b60;
    }
    .field input, .field select, .field textarea {
      width:100%;
      min-height:42px;
      border-radius:14px;
      border:1px solid rgba(15, 123, 96, 0.16);
      background:rgba(255,255,255,0.78);
      color:var(--ink);
      padding:10px 12px;
      outline:none;
      font-family:inherit;
      font-size:13px;
    }
    .field textarea {
      min-height:90px;
      resize:vertical;
    }
    .field input:focus, .field select:focus, .field textarea:focus {
      border-color:rgba(36,179,137,0.58);
      box-shadow:0 0 0 4px rgba(36,179,137,0.10);
    }
    .list {
      display:grid;
      gap:12px;
    }
    .greeter-item {
      border:1px solid rgba(15, 123, 96, 0.22);
      border-radius:18px;
      padding:14px;
      background:rgba(255,255,255,0.78);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.42);
    }
    .item-head {
      display:flex;
      justify-content:space-between;
      gap:12px;
      align-items:flex-start;
    }
    .greeter-item strong {
      display:block;
      font-size:15px;
      margin-bottom:6px;
    }
    .greeter-item span {
      display:block;
      color:var(--muted);
      font-size:12px;
      line-height:1.55;
    }
    .greeter-tags {
      display:flex;
      flex-wrap:wrap;
      gap:8px;
      margin-top:10px;
    }
    .greeter-tags i {
      display:inline-flex;
      align-items:center;
      min-height:28px;
      padding:0 10px;
      border-radius:999px;
      background:rgba(36,179,137,0.12);
      border:1px solid rgba(36,179,137,0.18);
      color:#0f7b60;
      font-style:normal;
      font-size:11px;
      font-weight:800;
    }
    .item-actions.compact {
      display:flex;
      gap:8px;
      flex-wrap:wrap;
    }
    .item-btn {
      min-height:34px;
      border-radius:11px;
      padding:0 12px;
      border:none;
      font-weight:800;
      font-size:12px;
      cursor:pointer;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      box-shadow: 0 10px 18px rgba(2, 14, 13, 0.10);
    }
    .item-btn.edit {
      background:linear-gradient(180deg, #d9f6ee 0%, #b8eadc 100%);
      color:#0e5c49;
      border:1px solid rgba(14, 92, 73, 0.18);
    }
    .item-btn.remove {
      background:linear-gradient(180deg, #ffe3e0 0%, #ffc8c0 100%);
      color:#8f2418;
      border:1px solid rgba(143, 36, 24, 0.16);
    }
    .status {
      margin-top:16px;
      border-radius:14px;
      padding:12px 14px;
      background:rgba(36, 179, 137, 0.12);
      border:1px solid rgba(36, 179, 137, 0.20);
      color:#d7fbef;
      font-size:12px;
      line-height:1.6;
      display:none;
    }
    .extra-list {
      display:grid;
      gap:10px;
      margin-top:6px;
    }
    .extra-item {
      display:grid;
      grid-template-columns:1fr 1.2fr auto;
      gap:8px;
      align-items:center;
    }
    .extra-remove {
      min-height:42px;
      min-width:42px;
      border-radius:12px;
      border:1px solid rgba(143, 36, 24, 0.16);
      background:#ffe3e0;
      color:#8f2418;
      font-weight:800;
      cursor:pointer;
    }
    .status.show { display:block; }
    @media (max-width: 960px) {
      .layout { grid-template-columns: 1fr; }
      .field-grid { grid-template-columns: 1fr; }
      .extra-item { grid-template-columns:1fr; }
      .item-head { flex-direction:column; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="head">
      <div>
        <strong>Karşılamacı Kartları</strong>
        <span>İletişim, kimlik, doğum tarihi, dil, erişim tipi ve operasyon detaylarının ilk kayıt ekranı</span>
      </div>
      <a href="/panel">Panele Dön</a>
    </section>

    <section class="panel">
      <div class="toolbar">
        <p>
          Bu ilk sürümde karşılamacı kartları temel veri alanlarıyla kaydedilir. Sonraki adımda görev tipi,
          terminal uzmanlığı, vardiya görünümü ve toplu görevlendirme yapısı eklenecek.
        </p>
        <div class="action-row">
          <button id="saveGreetersBtn" type="button" class="action-btn primary">Listeyi Kaydet</button>
          <button id="clearGreetersBtn" type="button" class="action-btn">Formu Temizle</button>
        </div>
      </div>

      <div class="layout">
        <article class="card">
          <h3>Yeni Karşılamacı Kartı</h3>
          <div class="field-grid">
            <div class="field">
              <label for="greeter_code">Karşılamacı Kodu</label>
              <input id="greeter_code" type="text" placeholder="Örn: GRT-001" />
            </div>
            <div class="field">
              <label for="full_name">Ad Soyad</label>
              <input id="full_name" type="text" placeholder="Karşılamacı adı" />
            </div>
            <div class="field">
              <label for="phone">Telefon</label>
              <input id="phone" type="text" placeholder="+90 5xx xxx xx xx" />
            </div>
            <div class="field">
              <label for="tc_kimlik_no">T.C. Kimlik No</label>
              <input id="tc_kimlik_no" type="text" inputmode="numeric" maxlength="11" placeholder="11 haneli T.C. Kimlik No" />
            </div>
            <div class="field">
              <label for="birth_date">Doğum Tarihi</label>
              <input id="birth_date" type="date" />
            </div>
            <div class="field full">
              <label for="languages">Yabancı Dil</label>
              <input id="languages" type="text" placeholder="İngilizce, Almanca..." />
            </div>
            <div class="field">
              <label for="employment_type">Kaynak Tipi</label>
              <select id="employment_type">
                <option value="internal">Araç Firması</option>
                <option value="external">Dışarıdan</option>
              </select>
            </div>
            <div class="field">
              <label for="access_type">Erişim Tipi</label>
              <select id="access_type">
                <option value="portal">Portal</option>
                <option value="link">Link</option>
              </select>
            </div>
            <div class="field full">
              <label>Ek Bilgi Alanları</label>
              <div id="greeterExtraFields" class="extra-list"></div>
              <button id="addGreeterExtraFieldBtn" type="button" class="action-btn">Ek Bilgi Alanı Ekle</button>
            </div>
            <div class="field full">
              <label for="greeter_note">Operasyon Notu</label>
              <textarea id="greeter_note" placeholder="Karşılamacı ile ilgili kısa not"></textarea>
            </div>
          </div>
          <div class="action-row" style="margin-top:14px;">
            <button id="addGreeterBtn" type="button" class="action-btn primary">Karşılamacı Ekle</button>
          </div>
        </article>

        <article class="card">
          <h3>Kayıtlı Karşılamacı Listesi</h3>
          <div id="greeterList" class="list"></div>
          <div id="greeterStatus" class="status"></div>
        </article>
      </div>
    </section>
  </div>

  <script>
    (function () {
      var API_BASE = 'http://localhost:3001';
      var TOKEN_KEYS = ['fleet_access_token', 'platform_core_token', 'agency_access_token'];
      var saveBtn = document.getElementById('saveGreetersBtn');
      var clearBtn = document.getElementById('clearGreetersBtn');
      var addBtn = document.getElementById('addGreeterBtn');
      var listNode = document.getElementById('greeterList');
      var statusNode = document.getElementById('greeterStatus');
      var extraFieldsNode = document.getElementById('greeterExtraFields');
      var addExtraFieldBtn = document.getElementById('addGreeterExtraFieldBtn');
      var editingIndex = -1;
      var internalSourceLabel = 'Araç Firması';
      var extraFields = [];
      var fields = {
        greeter_code: document.getElementById('greeter_code'),
        full_name: document.getElementById('full_name'),
        phone: document.getElementById('phone'),
        tc_kimlik_no: document.getElementById('tc_kimlik_no'),
        birth_date: document.getElementById('birth_date'),
        languages: document.getElementById('languages'),
        employment_type: document.getElementById('employment_type'),
        access_type: document.getElementById('access_type'),
        greeter_note: document.getElementById('greeter_note')
      };
      var items = [];

      function readToken() {
        for (var i = 0; i < TOKEN_KEYS.length; i += 1) {
          var value = localStorage.getItem(TOKEN_KEYS[i]) || '';
          if (value) return value;
        }
        return '';
      }

      async function loadCompanySourceLabel() {
        var token = readToken();
        if (!token) return;
        try {
          var res = await fetch(API_BASE + '/company-card-draft', {
            headers: { Authorization: 'Bearer ' + token }
          });
          if (!res.ok) return;
          var data = await res.json();
          var companyName = String((((data || {}).data || {}).company_name) || '').trim();
          internalSourceLabel = companyName || 'Araç Firması';
          Array.prototype.slice.call(document.querySelectorAll('#employment_type option[value="internal"]')).forEach(function (node) {
            node.textContent = internalSourceLabel;
          });
          renderList();
        } catch (_) {}
      }

      function showStatus(message) {
        statusNode.textContent = message;
        statusNode.classList.add('show');
        window.clearTimeout(window.__greeterStatusTimer);
        window.__greeterStatusTimer = window.setTimeout(function () {
          statusNode.classList.remove('show');
        }, 2600);
      }

      function clearForm() {
        Object.keys(fields).forEach(function (key) {
          if (key === 'employment_type') fields[key].value = 'internal';
          else if (key === 'access_type') fields[key].value = 'portal';
          else fields[key].value = '';
        });
        extraFields = [];
        renderExtraFields();
        editingIndex = -1;
        addBtn.textContent = 'Karşılamacı Ekle';
        setNextCode();
      }

      function escapeHtml(value) {
        return String(value || '').replace(/[&<>"]/g, function (char) {
          return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[char] || char;
        });
      }

      function normalizeExtraFields(values) {
        return (Array.isArray(values) ? values : []).map(function (item) {
          return {
            label: String((item || {}).label || '').trim(),
            value: String((item || {}).value || '').trim()
          };
        }).filter(function (item) { return item.label || item.value; });
      }

      function renderExtraFields() {
        if (!extraFields.length) {
          extraFieldsNode.innerHTML = '<div class="multi-hint">Kart üzerinde görünmesini istediğiniz özel alanları buradan ekleyebilirsiniz.</div>';
          return;
        }
        extraFieldsNode.innerHTML = extraFields.map(function (item, index) {
          return ''
            + '<div class="extra-item">'
            +   '<input type="text" data-extra-index="' + index + '" data-extra-field="label" placeholder="Alan adı" value="' + escapeHtml(item.label || '') + '" />'
            +   '<input type="text" data-extra-index="' + index + '" data-extra-field="value" placeholder="Değer" value="' + escapeHtml(item.value || '') + '" />'
            +   '<button type="button" class="extra-remove" data-remove-extra="' + index + '">×</button>'
            + '</div>';
        }).join('');
      }

      function nextCode(prefix) {
        var maxNumber = 0;
        items.forEach(function (item) {
          var match = String(item[prefix === 'GRT' ? 'greeter_code' : 'driver_code'] || '').match(new RegExp('^' + prefix + '-(\\d+)$'));
          if (!match) return;
          var value = parseInt(match[1], 10);
          if (!Number.isNaN(value) && value > maxNumber) maxNumber = value;
        });
        return prefix + '-' + String(maxNumber + 1).padStart(3, '0');
      }

      function setNextCode() {
        fields.greeter_code.value = nextCode('GRT');
      }

      function calculateAge(birthDate) {
        if (!birthDate) return '';
        var parts = birthDate.split('-').map(function (item) { return parseInt(item, 10); });
        if (parts.length !== 3 || parts.some(function (item) { return Number.isNaN(item); })) return '';
        var today = new Date();
        var age = today.getFullYear() - parts[0];
        var monthDiff = (today.getMonth() + 1) - parts[1];
        var dayDiff = today.getDate() - parts[2];
        if (monthDiff < 0 || (monthDiff === 0 && dayDiff < 0)) age -= 1;
        return age >= 0 ? String(age) : '';
      }

      function normalizeDisplayPhone(value) {
        var digits = String(value || '').replace(/\D+/g, '');
        if (!digits) return '';
        if (digits.charAt(0) === '0' && digits.length === 11) digits = '90' + digits.slice(1);
        if (digits.charAt(0) === '5' && digits.length === 10) digits = '90' + digits;
        if (digits.indexOf('90') === 0 && digits.length === 12) {
          return '+90 ' + digits.slice(2, 5) + ' ' + digits.slice(5, 8) + ' ' + digits.slice(8, 10) + ' ' + digits.slice(10, 12);
        }
        return String(value || '').trim();
      }

      function normalizeTcKimlikNo(value) {
        var digits = String(value || '').replace(/\D+/g, '');
        return digits.length === 11 ? digits : '';
      }

      function fillForm(item, index) {
        fields.greeter_code.value = item.greeter_code || nextCode('GRT');
        fields.full_name.value = item.full_name || '';
        fields.phone.value = item.phone || '';
        fields.tc_kimlik_no.value = item.tc_kimlik_no || '';
        fields.birth_date.value = item.birth_date || '';
        fields.languages.value = item.languages || '';
        fields.employment_type.value = item.employment_type || 'internal';
        fields.access_type.value = item.access_type || 'portal';
        fields.greeter_note.value = item.greeter_note || '';
        extraFields = normalizeExtraFields(item.extra_fields || []);
        renderExtraFields();
        editingIndex = index;
        addBtn.textContent = 'Karşılamacıyı Güncelle';
      }

      function collectForm() {
        return {
          greeter_code: fields.greeter_code.value.trim(),
          full_name: fields.full_name.value.trim(),
          phone: normalizeDisplayPhone(fields.phone.value),
          tc_kimlik_no: normalizeTcKimlikNo(fields.tc_kimlik_no.value),
          birth_date: fields.birth_date.value.trim(),
          age: calculateAge(fields.birth_date.value.trim()),
          languages: fields.languages.value.trim(),
          employment_type: fields.employment_type.value.trim(),
          access_type: fields.access_type.value.trim(),
          greeter_note: fields.greeter_note.value.trim(),
          extra_fields: normalizeExtraFields(extraFields)
        };
      }

      function renderList() {
        if (!items.length) {
          listNode.innerHTML = '<div class="greeter-item"><strong>Henüz karşılamacı eklenmedi</strong><span>İlk karşılamacı kartını soldaki form ile ekleyin.</span></div>';
          return;
        }
        listNode.innerHTML = items.map(function (item, index) {
          var tags = [];
          if (item.languages) tags.push(item.languages);
          if (item.employment_type === 'internal') tags.push(internalSourceLabel);
          if (item.employment_type === 'external') tags.push('Dışarıdan');
          if (item.access_type === 'portal') tags.push('Portal');
          if (item.access_type === 'link') tags.push('Link');
          return ''
            + '<div class="greeter-item">'
            +   '<div class="item-head">'
            +     '<div>'
            +       '<strong>' + escapeHtml(item.full_name || '-') + ' / ' + escapeHtml(item.phone || '-') + '</strong>'
            +       '<span>Kod: ' + escapeHtml(item.greeter_code || '-') + ' | T.C.: ' + escapeHtml(item.tc_kimlik_no || '-') + ' | Doğum: ' + escapeHtml(item.birth_date || '-') + ' | Yaş: ' + escapeHtml(item.age || '-') + '</span>'
            +       '<span>Not: ' + escapeHtml(item.greeter_note || '-') + '</span>'
            +     '</div>'
            +     '<div class="item-actions compact"><button type="button" class="item-btn edit" data-edit-index="' + index + '">Düzenle</button><button type="button" class="item-btn remove" data-remove-index="' + index + '">Kaldır</button></div>'
            +   '</div>'
            +   '<div class="greeter-tags">' + tags.concat((item.extra_fields || []).map(function (field) { return (field.label || 'Ek Bilgi') + ': ' + (field.value || '-'); })).map(function (tag) { return '<i>' + escapeHtml(tag) + '</i>'; }).join('') + '</div>'
            + '</div>';
        }).join('');
      }

      async function loadItems() {
        var token = readToken();
        if (!token) return;
        try {
          var res = await fetch(API_BASE + '/greeter-cards', {
            headers: { Authorization: 'Bearer ' + token }
          });
          if (!res.ok) return;
          var data = await res.json();
          items = Array.isArray(data.items) ? data.items : [];
          setNextCode();
          renderList();
        } catch (_) {}
      }

      async function saveItems() {
        var token = readToken();
        if (!token) {
          showStatus('Oturum bulunamadı. Yeniden giriş yapın.');
          return;
        }
        try {
          var res = await fetch(API_BASE + '/greeter-cards', {
            method: 'PUT',
            headers: {
              Authorization: 'Bearer ' + token,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ items: items })
          });
          if (!res.ok) {
            showStatus('Karşılamacı listesi çekirdeğe kaydedilemedi.');
            return;
          }
          showStatus('Karşılamacı listesi çekirdeğe kaydedildi.');
        } catch (_) {
          showStatus('Karşılamacı listesi çekirdeğe kaydedilemedi.');
        }
      }

      addBtn.addEventListener('click', function () {
        var item = collectForm();
        var isEditing = editingIndex >= 0;
        if (!item.greeter_code || !item.full_name || !item.phone) {
          showStatus('Karşılamacı kodu, ad soyad ve telefon zorunludur.');
          return;
        }
        if (fields.tc_kimlik_no.value.trim() && !item.tc_kimlik_no) {
          showStatus('T.C. Kimlik No geçersiz. Bilinmiyorsa 11111111111 kullanın.');
          return;
        }
        fields.phone.value = item.phone || '';
        fields.tc_kimlik_no.value = item.tc_kimlik_no || '';
        if (isEditing) items.splice(editingIndex, 1, item);
        else items.unshift(item);
        renderList();
        clearForm();
        showStatus(isEditing ? 'Karşılamacı güncellendi. Kaydet ile çekirdeğe yazabilirsiniz.' : 'Karşılamacı listeye eklendi. Kaydet ile çekirdeğe yazabilirsiniz.');
      });

      saveBtn.addEventListener('click', saveItems);
      clearBtn.addEventListener('click', function () {
        clearForm();
        showStatus('Form temizlendi.');
      });
      if (addExtraFieldBtn) {
        addExtraFieldBtn.addEventListener('click', function () {
          extraFields.push({ label: '', value: '' });
          renderExtraFields();
        });
      }
      if (extraFieldsNode) {
        extraFieldsNode.addEventListener('click', function (event) {
          var btn = event.target.closest('[data-remove-extra]');
          if (!btn) return;
          var index = parseInt(btn.getAttribute('data-remove-extra'), 10);
          if (Number.isNaN(index)) return;
          extraFields = extraFields.filter(function (_, current) { return current !== index; });
          renderExtraFields();
        });
        extraFieldsNode.addEventListener('input', function (event) {
          var field = event.target && event.target.getAttribute('data-extra-field');
          var index = parseInt(event.target && event.target.getAttribute('data-extra-index'), 10);
          if (!field || Number.isNaN(index) || !extraFields[index]) return;
          extraFields[index][field] = event.target.value || '';
        });
      }

      listNode.addEventListener('click', function (event) {
        var editBtn = event.target.closest('[data-edit-index]');
        if (editBtn) {
          var editIndex = parseInt(editBtn.getAttribute('data-edit-index'), 10);
          if (!Number.isNaN(editIndex) && items[editIndex]) {
            fillForm(items[editIndex], editIndex);
            showStatus('Karşılamacı kartı düzenleme için forma taşındı.');
          }
          return;
        }
        var btn = event.target.closest('[data-remove-index]');
        if (!btn) return;
        var index = parseInt(btn.getAttribute('data-remove-index'), 10);
        if (Number.isNaN(index)) return;
        items.splice(index, 1);
        renderList();
        showStatus('Karşılamacı listeden kaldırıldı. Kaydet ile çekirdeğe yazabilirsiniz.');
      });

      clearForm();
      renderExtraFields();
      renderList();
      loadItems();
      loadCompanySourceLabel();
    })();
  </script>
</body>
</html>
    """


@app.get("/notifications", response_class=HTMLResponse)
def notifications_page() -> str:
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Bildirim Merkezi</title>
  <style>
    :root {
      --bg-1: #081d1d;
      --bg-2: #0d3934;
      --bg-3: #0a2724;
      --panel: rgba(7, 28, 27, 0.82);
      --panel-line: rgba(129, 223, 197, 0.22);
      --card-bg: linear-gradient(180deg, rgba(246, 255, 252, 0.97) 0%, rgba(232, 247, 242, 0.93) 100%);
      --card-line: rgba(132, 220, 193, 0.52);
      --ink: #12332d;
      --muted: #45655f;
      --accent: #24b389;
      --white: #f7fbfb;
    }
    * { box-sizing: border-box; }
    body { margin:0; font-family:"Segoe UI", Arial, sans-serif; color:var(--white); background:radial-gradient(circle at right top, rgba(36,179,137,0.20), transparent 28%), linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 56%, var(--bg-3) 100%); background-attachment:fixed; }
    .wrap { width:min(1240px, calc(100% - 32px)); margin:22px auto 40px; }
    .head,.panel { background:var(--panel); border:1px solid var(--panel-line); border-radius:20px; backdrop-filter:blur(10px); box-shadow:0 18px 36px rgba(2,12,12,0.28); }
    .head { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:14px 16px; margin-bottom:16px; }
    .head a { color:#dcfff6; text-decoration:none; border:1px solid rgba(132,220,193,0.22); background:rgba(255,255,255,0.06); min-height:38px; display:inline-flex; align-items:center; justify-content:center; border-radius:12px; padding:0 14px; font-weight:700; font-size:13px; }
    .head strong { display:block; font-size:22px; }
    .head span { color:#a2d4ca; font-size:12px; }
    .panel { padding:24px; }
    .layout { display:grid; grid-template-columns: 420px 1fr; gap:16px; }
    .card { background: var(--card-bg); border:1px solid var(--card-line); border-radius:18px; padding:18px; color:var(--ink); box-shadow:0 16px 30px rgba(2,14,13,0.18); }
    .card h3 { margin:0 0 12px; font-size:18px; }
    .pref-list, .history-list { display:grid; gap:10px; }
    .pref-row, .history-item { border:1px solid rgba(15,123,96,0.12); border-radius:16px; padding:14px; background:rgba(255,255,255,0.74); }
    .pref-row strong, .history-item strong { display:block; margin-bottom:6px; }
    .channel-list { display:flex; flex-wrap:wrap; gap:10px; margin-top:10px; }
    .channel-list label { display:inline-flex; gap:6px; align-items:center; font-size:12px; color:var(--ink); }
    .status { margin-top:16px; border-radius:14px; padding:12px 14px; background:rgba(36,179,137,0.12); border:1px solid rgba(36,179,137,0.20); color:#d7fbef; font-size:12px; line-height:1.6; display:none; }
    .status.show { display:block; }
    .action-btn { min-height:40px; border-radius:12px; padding:0 14px; border:1px solid rgba(132,220,193,0.22); background:rgba(255,255,255,0.06); color:#dcfff6; font-weight:700; cursor:pointer; }
    .action-btn.primary { color:#06271e; background: linear-gradient(180deg, #59e0b4 0%, #22b28a 100%); border-color:transparent; box-shadow:0 10px 20px rgba(36,179,137,0.18); }
    @media (max-width: 960px) { .layout { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="head">
      <div>
        <strong>Bildirim Merkezi</strong>
        <span>Aktif kullanıcı tercihleri ve geriye dönük bildirim geçmişi</span>
      </div>
      <a href="/panel">Panele Dön</a>
    </section>
    <section class="panel">
      <div class="layout">
        <article class="card">
          <h3>Bildirim Tercihleri</h3>
          <div id="prefList" class="pref-list"></div>
          <div style="margin-top:14px;">
            <button id="saveBtn" type="button" class="action-btn primary">Tercihleri Kaydet</button>
          </div>
          <div id="statusBox" class="status"></div>
        </article>
        <article class="card">
          <h3>Bildirim Geçmişi</h3>
          <div id="historyList" class="history-list"></div>
        </article>
      </div>
    </section>
  </div>
  <script>
    (function () {
      var API_BASE = 'http://localhost:3001';
      var TOKEN_KEYS = ['fleet_access_token', 'platform_core_token', 'agency_access_token'];
      var prefList = document.getElementById('prefList');
      var historyList = document.getElementById('historyList');
      var saveBtn = document.getElementById('saveBtn');
      var statusBox = document.getElementById('statusBox');
      var prefs = [];
      function token() {
        for (var i = 0; i < TOKEN_KEYS.length; i += 1) {
          var value = localStorage.getItem(TOKEN_KEYS[i]) || '';
          if (value) return value;
        }
        return '';
      }
      function showStatus(message) {
        statusBox.textContent = message;
        statusBox.classList.add('show');
        window.clearTimeout(window.__notificationTimer);
        window.__notificationTimer = window.setTimeout(function () { statusBox.classList.remove('show'); }, 2600);
      }
      function renderPrefs() {
        prefList.innerHTML = prefs.map(function (item, index) {
          return '<div class="pref-row"><strong>' + item.label + '</strong><div class="channel-list">'
            + '<label><input type="checkbox" data-index="' + index + '" data-key="system"' + (item.system ? ' checked' : '') + '>Sistem içi</label>'
            + '<label><input type="checkbox" data-index="' + index + '" data-key="email"' + (item.email ? ' checked' : '') + '>E-posta</label>'
            + '<label><input type="checkbox" data-index="' + index + '" data-key="sms"' + (item.sms ? ' checked' : '') + '>SMS</label>'
            + '<label><input type="checkbox" data-index="' + index + '" data-key="whatsapp"' + (item.whatsapp ? ' checked' : '') + '>WhatsApp</label>'
            + '</div></div>';
        }).join('');
      }
      function renderHistory(items) {
        if (!items.length) {
          historyList.innerHTML = '<div class="history-item"><strong>Henüz bildirim yok</strong><span>İlk bildirimler burada listelenecek.</span></div>';
          return;
        }
        historyList.innerHTML = items.map(function (item) {
          return '<div class="history-item"><strong>' + (item.title || '-') + '</strong><span>Kanal: ' + (item.channel || '-') + ' | Durum: ' + (item.status || '-') + '</span><span>' + (item.summary || '-') + '</span><span>' + (item.created_at || '-') + '</span></div>';
        }).join('');
      }
      prefList.addEventListener('change', function (event) {
        var node = event.target;
        var index = parseInt(node.getAttribute('data-index'), 10);
        var key = node.getAttribute('data-key');
        if (Number.isNaN(index) || !prefs[index]) return;
        prefs[index][key] = !!node.checked;
      });
      async function loadAll() {
        var auth = token();
        if (!auth) return;
        var prefRes = await fetch(API_BASE + '/notification-preferences/current', { headers: { Authorization: 'Bearer ' + auth } });
        if (prefRes.ok) {
          var prefData = await prefRes.json();
          prefs = Array.isArray(prefData.items) ? prefData.items : [];
          renderPrefs();
        }
        var historyRes = await fetch(API_BASE + '/notification-history/current', { headers: { Authorization: 'Bearer ' + auth } });
        if (historyRes.ok) {
          var historyData = await historyRes.json();
          renderHistory(Array.isArray(historyData.items) ? historyData.items : []);
        }
      }
      saveBtn.addEventListener('click', async function () {
        var auth = token();
        if (!auth) {
          showStatus('Oturum bulunamadı. Yeniden giriş yapın.');
          return;
        }
        var res = await fetch(API_BASE + '/notification-preferences/current', {
          method: 'PUT',
          headers: { Authorization: 'Bearer ' + auth, 'Content-Type': 'application/json' },
          body: JSON.stringify({ items: prefs })
        });
        showStatus(res.ok ? 'Bildirim tercihleri kaydedildi.' : 'Bildirim tercihleri kaydedilemedi.');
      });
      loadAll();
    })();
  </script>
</body>
</html>
    """


@app.get("/company-card", response_class=HTMLResponse)
def company_card_page() -> str:
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Firma Kartı</title>
  <style>
    :root {
      --bg-1: #081d1d;
      --bg-2: #0d3934;
      --bg-3: #0a2724;
      --panel: rgba(7, 28, 27, 0.82);
      --panel-line: rgba(129, 223, 197, 0.22);
      --card-bg: linear-gradient(180deg, rgba(246, 255, 252, 0.97) 0%, rgba(232, 247, 242, 0.93) 100%);
      --card-line: rgba(132, 220, 193, 0.52);
      --ink: #12332d;
      --muted: #45655f;
      --accent: #24b389;
      --accent-2: #0e8d6b;
      --gold: #e4c067;
      --white: #f7fbfb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--white);
      background:
        radial-gradient(circle at right top, rgba(36,179,137,0.20), transparent 28%),
        linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 56%, var(--bg-3) 100%);
      background-attachment: fixed;
    }
    .wrap { width: min(1180px, calc(100% - 32px)); margin: 22px auto 40px; }
    .head, .panel {
      background: var(--panel);
      border: 1px solid var(--panel-line);
      border-radius: 20px;
      backdrop-filter: blur(10px);
      box-shadow: 0 18px 36px rgba(2, 12, 12, 0.28);
    }
    .head {
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:12px;
      padding:14px 16px;
      margin-bottom:16px;
    }
    .head a {
      color:#dcfff6;
      text-decoration:none;
      border:1px solid rgba(132,220,193,0.22);
      background:rgba(255,255,255,0.06);
      min-height:38px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      border-radius:12px;
      padding:0 14px;
      font-weight:700;
      font-size:13px;
    }
    .head strong { display:block; font-size:22px; }
    .head span { color:#a2d4ca; font-size:12px; }
    .panel { padding:24px; }
    .topbar {
      display:flex;
      justify-content:space-between;
      gap:12px;
      align-items:center;
      flex-wrap:wrap;
      margin-bottom:18px;
    }
    .summary {
      color:#b9d7d0;
      font-size:13px;
      line-height:1.6;
      max-width:70ch;
    }
    .action-row {
      display:flex;
      gap:10px;
      flex-wrap:wrap;
    }
    .action-btn {
      min-height:40px;
      border-radius:12px;
      padding:0 14px;
      border:1px solid rgba(132,220,193,0.22);
      background:rgba(255,255,255,0.06);
      color:#dcfff6;
      font-weight:700;
      cursor:pointer;
    }
    .action-btn.primary {
      color:#06271e;
      background: linear-gradient(180deg, #59e0b4 0%, #22b28a 100%);
      border-color: transparent;
      box-shadow: 0 10px 20px rgba(36,179,137,0.18);
    }
    .tabs {
      display:flex;
      flex-wrap:wrap;
      gap:8px;
      margin-bottom:18px;
    }
    .tab {
      border:1px solid rgba(132,220,193,0.20);
      background:rgba(255,255,255,0.06);
      color:#e7faf4;
      min-height:38px;
      padding:0 14px;
      border-radius:12px;
      font-weight:700;
      font-size:13px;
      display:inline-flex;
      align-items:center;
      cursor:pointer;
    }
    .tab.active {
      background: linear-gradient(180deg, #59e0b4 0%, #22b28a 100%);
      color:#06271e;
      border-color:transparent;
    }
    .grid {
      display:grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap:16px;
    }
    .grid.one {
      grid-template-columns: 1fr;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-line);
      border-radius: 18px;
      padding: 18px;
      color: var(--ink);
      box-shadow: 0 16px 30px rgba(2, 14, 13, 0.18);
    }
    .section {
      display:none;
    }
    .section.active {
      display:block;
    }
    .card h3 {
      margin:0 0 12px;
      font-size:18px;
    }
    .card-head {
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:10px;
      margin-bottom:12px;
    }
    .badge {
      display:inline-flex;
      align-items:center;
      min-height:28px;
      padding:0 10px;
      border-radius:999px;
      font-size:11px;
      font-weight:800;
      letter-spacing:0.2px;
      color:#0d4f40;
      background:rgba(36, 179, 137, 0.14);
      border:1px solid rgba(36, 179, 137, 0.28);
      white-space:nowrap;
    }
    .list {
      display:grid;
      gap:10px;
    }
    .field-grid {
      display:grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap:14px;
    }
    .field {
      display:grid;
      gap:7px;
    }
    .field.full {
      grid-column: 1 / -1;
    }
    .field label {
      font-size:12px;
      font-weight:800;
      color:#0f7b60;
      letter-spacing:0.15px;
    }
    .field input, .field select, .field textarea {
      width:100%;
      min-height:44px;
      border-radius:14px;
      border:1px solid rgba(15, 123, 96, 0.16);
      background:rgba(255,255,255,0.78);
      color:var(--ink);
      padding:10px 12px;
      outline:none;
      font-family:inherit;
      font-size:13px;
    }
    .field textarea {
      min-height:110px;
      resize:vertical;
    }
    .field input:focus, .field select:focus, .field textarea:focus {
      border-color:rgba(36,179,137,0.58);
      box-shadow:0 0 0 4px rgba(36,179,137,0.10);
    }
    .readonly-field {
      width:100%;
      min-height:44px;
      border-radius:14px;
      border:1px solid rgba(15, 123, 96, 0.16);
      background:rgba(255,255,255,0.78);
      color:var(--ink);
      padding:10px 12px;
      font-size:13px;
      line-height:1.55;
      display:flex;
      align-items:center;
    }
    .readonly-field.is-active {
      border-color:rgba(36,179,137,0.34);
      background:rgba(36,179,137,0.10);
      color:#0f6a54;
    }
    .readonly-field.is-passive {
      border-color:rgba(228,192,103,0.28);
      background:rgba(228,192,103,0.12);
      color:#775b11;
    }
    .person-list {
      display:grid;
      gap:12px;
    }
    .person-item {
      border:1px solid rgba(15,123,96,0.16);
      border-radius:16px;
      padding:14px;
      background:rgba(255,255,255,0.62);
      display:grid;
      gap:12px;
    }
    .person-item-head {
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:10px;
    }
    .person-item-title {
      color:#0f7b60;
      font-size:13px;
      font-weight:800;
    }
    .mini-btn {
      min-height:34px;
      border-radius:12px;
      padding:0 12px;
      border:1px solid rgba(15,123,96,0.16);
      background:rgba(255,255,255,0.84);
      color:var(--ink);
      font-size:12px;
      font-weight:800;
      cursor:pointer;
    }
    .mini-btn.danger {
      color:#9c2742;
      border-color:rgba(156,39,66,0.20);
      background:rgba(156,39,66,0.08);
    }
    .add-inline-btn {
      min-height:40px;
      border-radius:14px;
      padding:0 14px;
      border:1px dashed rgba(15,123,96,0.28);
      background:rgba(255,255,255,0.72);
      color:#0f7b60;
      font-size:12px;
      font-weight:800;
      cursor:pointer;
    }
    .helper-text {
      color:var(--muted);
      font-size:12px;
      line-height:1.5;
    }
    .mini-grid {
      display:grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap:12px;
      margin-top:12px;
    }
    .row {
      display:grid;
      grid-template-columns: 180px 1fr;
      gap:12px;
      align-items:start;
      font-size:13px;
    }
    .row strong {
      color:#0f7b60;
    }
    .row span {
      color:var(--muted);
      line-height:1.55;
    }
    .status {
      margin-top:16px;
      border-radius:14px;
      padding:12px 14px;
      background:rgba(36, 179, 137, 0.12);
      border:1px solid rgba(36, 179, 137, 0.20);
      color:#d7fbef;
      font-size:12px;
      line-height:1.6;
      display:none;
    }
    .status.show {
      display:block;
    }
    .note {
      margin-top:18px;
      border-radius:14px;
      padding:12px 14px;
      background:rgba(228, 192, 103, 0.16);
      border:1px solid rgba(228, 192, 103, 0.22);
      color:#f4e3ae;
      font-size:12px;
      line-height:1.6;
    }
    @media (max-width: 860px) {
      .grid { grid-template-columns: 1fr; }
      .field-grid, .mini-grid { grid-template-columns: 1fr; }
      .row { grid-template-columns: 1fr; gap:4px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="head">
      <div>
        <strong>Firma Kartı</strong>
        <span>Araç firması üyelik ve sözleşme kaynak verilerinin toplandığı ana ekran</span>
      </div>
      <a href="/panel">Panele Dön</a>
    </section>

    <section class="panel">
      <div class="topbar">
        <div class="summary">
          Firma kartı, üyelikte girilen ana profil, sözleşme, imza ve sorumlu verilerinin tek merkezidir.
          Bu sürümde bilgiler tarayıcı taslağı olarak saklanır; sonraki adımda çekirdek veri modeline bağlanacaktır.
        </div>
        <div class="action-row">
          <button id="saveDraftBtn" type="button" class="action-btn primary">Taslağı Kaydet</button>
          <button id="resetDraftBtn" type="button" class="action-btn">Taslağı Temizle</button>
        </div>
      </div>

      <div class="tabs">
        <button class="tab active" type="button" data-tab="genel">Genel Bilgiler</button>
        <button class="tab" type="button" data-tab="yetkili">Kişiler ve İmzalar</button>
        <button class="tab" type="button" data-tab="belge">Belgeler ve Sözleşme Verileri</button>
      </div>

      <section class="section active" data-section="genel">
        <div class="grid">
          <article class="card">
            <div class="card-head">
              <h3>Genel Bilgiler</h3>
              <span class="badge">Firma Profili</span>
            </div>
            <div class="field-grid">
              <div class="field">
                <label for="company_type">Firma Tipi</label>
                <select id="company_type" data-field="company_type">
                  <option value="vehicle_company">Araç firması</option>
                  <option value="agency">Acente</option>
                </select>
              </div>
              <div class="field">
                <label>Portal Durumu</label>
                <div id="portalModeBox" class="readonly-field">Kontrol ediliyor...</div>
                <input id="portal_mode" data-field="portal_mode" type="hidden" />
              </div>
              <div class="field">
                <label for="company_code">Firma Kodu</label>
                <input id="company_code" data-field="company_code" type="text" placeholder="Örn: TRN-001 / ACN-001" />
              </div>
              <div class="field">
                <label for="company_name">Kısa Firma Adı</label>
                <input id="company_name" data-field="company_name" type="text" placeholder="Ekranda görünen kısa ad" />
              </div>
              <div class="field full">
                <label for="company_title">Resmî Ünvan</label>
                <input id="company_title" data-field="company_title" type="text" placeholder="Sözleşme ve evrakta kullanılacak tam ticari ünvan" />
              </div>
              <div class="field">
                <label for="tax_number">Vergi No / TC</label>
                <input id="tax_number" data-field="tax_number" type="text" placeholder="Ör: 29*******64" />
              </div>
              <div class="field">
                <label for="tax_office">Vergi Dairesi</label>
                <input id="tax_office" data-field="tax_office" type="text" placeholder="Vergi dairesi" />
              </div>
              <div class="field">
                <label for="mersis_no">MERSİS</label>
                <input id="mersis_no" data-field="mersis_no" type="text" placeholder="Varsa MERSİS numarası" />
              </div>
              <div class="field">
                <label for="tursab_no">TÜRSAB</label>
                <input id="tursab_no" data-field="tursab_no" type="text" placeholder="Varsa TÜRSAB numarası" />
              </div>
              <div class="field">
                <label for="phone">Telefon</label>
                <input id="phone" data-field="phone" type="text" placeholder="Firma telefonu" />
              </div>
              <div class="field">
                <label for="email">E-posta</label>
                <input id="email" data-field="email" type="email" placeholder="Firma e-postası" />
              </div>
              <div class="field">
                <label for="center_city">Merkez Şehir</label>
                <input id="center_city" data-field="center_city" type="text" placeholder="Örn: Antalya" />
              </div>
              <div class="field full">
                <label for="address">Adres</label>
                <textarea id="address" data-field="address" placeholder="Resmi ve operasyon adresi"></textarea>
              </div>
            </div>
          </article>

          <article class="card">
            <div class="card-head">
              <h3>Kullanım Notları</h3>
              <span class="badge">Operasyon</span>
            </div>
            <div class="list">
              <div class="row"><strong>Kayıt Tipi</strong><span>Bu ekran firma üyelik verisi, sözleşme kaynağı ve operasyon sorumluluk başlangıcı olarak çalışır.</span></div>
              <div class="row"><strong>Firma Kodu</strong><span>Operasyonda ve raporlarda görünen kısa koddur.</span></div>
              <div class="row"><strong>Portal Durumu</strong><span>Manuel seçilmez. Vergi no veya T.C. eşleşmesine göre sistem aktif ya da pasif belirler.</span></div>
              <div class="row"><strong>Yön Hesabı</strong><span>Proje şehri varsa geliş / gidiş hesabında önce proje şehri kullanılır. Proje şehri yoksa araç firmasının merkez şehri baz alınır.</span></div>
              <div class="row"><strong>Tema Yönetimi</strong><span>Bu ekranda görünmez. Yalnızca Creatro supplier admin panelinden yönetilir.</span></div>
            </div>
          </article>
        </div>
      </section>

      <section class="section" data-section="yetkili">
        <div class="grid">
          <article class="card">
            <div class="card-head">
              <h3>İmza ve Sözleşme Bilgileri</h3>
              <span class="badge">Sözleşme Kaynağı</span>
            </div>
            <div class="field-grid">
              <div class="field">
                <label for="authority_name">Ana Yetkili</label>
                <input id="authority_name" data-field="authority_name" type="text" placeholder="Ad soyad" />
              </div>
              <div class="field">
                <label for="authority_title">Yetkili Unvanı</label>
                <input id="authority_title" data-field="authority_title" type="text" placeholder="Genel müdür, operasyon müdürü..." />
              </div>
              <div class="field">
                <label for="authority_phone">Yetkili Telefon</label>
                <input id="authority_phone" data-field="authority_phone" type="text" placeholder="Telefon" />
              </div>
              <div class="field">
                <label for="authority_email">Yetkili E-posta</label>
                <input id="authority_email" data-field="authority_email" type="email" placeholder="E-posta" />
              </div>
              <div class="field">
                <label for="signatory_name">İmza Yetkilisi</label>
                <input id="signatory_name" data-field="signatory_name" type="text" placeholder="Sözleşmeye basılacak isim" />
              </div>
              <div class="field">
                <label for="signatory_title">İmza Unvanı</label>
                <input id="signatory_title" data-field="signatory_title" type="text" placeholder="İmza unvanı" />
              </div>
              <div class="field full">
                <label for="signature_note">Sözleşme Notu</label>
                <textarea id="signature_note" data-field="signature_note" placeholder="Sözleşme üretiminde kullanılacak özel notlar"></textarea>
              </div>
            </div>
          </article>
          <article class="card">
            <div class="card-head">
              <h3>Yetkili ve Sorumlular</h3>
              <span class="badge">Akış Matrisi</span>
            </div>
            <div class="helper-text" style="margin-bottom:12px;">
              Firmaya birden fazla kişi ekleyebilirsin. Rol alanı serbest çalışır; <strong>Diğer</strong> seçilirse açıklama ile özel sıfat yazılabilir.
            </div>
            <div id="responsiblePeopleList" class="person-list"></div>
            <button id="addResponsiblePersonBtn" class="add-inline-btn" type="button">Kişi Ekle</button>
          </article>
          <article class="card">
            <div class="card-head">
              <h3>Plan Notları</h3>
              <span class="badge">İç Kullanım</span>
            </div>
            <div class="field-grid">
              <div class="field full">
                <label for="operation_note">Operasyon Notu</label>
                <textarea id="operation_note" data-field="operation_note" placeholder="İç operasyon notları"></textarea>
              </div>
              <div class="field full">
                <label for="responsibility_rule">Sorumluluk Kuralı</label>
                <textarea id="responsibility_rule" data-field="responsibility_rule" placeholder="Firma, proje veya araç tipine göre sorumluluk özeti"></textarea>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section class="section" data-section="belge">
        <div class="grid">
          <article class="card">
            <div class="card-head">
              <h3>Sözleşme ve Evrak</h3>
              <span class="badge">Şablon Kaynağı</span>
            </div>
            <div class="field-grid">
              <div class="field">
                <label for="contract_type">Varsayılan Sözleşme Tipi</label>
                <select id="contract_type" data-field="contract_type">
                  <option value="arac_kiralama">Araç kiralama sözleşmesi</option>
                  <option value="rehber">Rehber sözleşmesi</option>
                  <option value="hizmet">Hizmet sözleşmesi</option>
                </select>
              </div>
              <div class="field">
                <label for="document_retention">Arşiv Süresi</label>
                <input id="document_retention" data-field="document_retention" type="text" placeholder="Örn: 180 gün" />
              </div>
              <div class="field full">
                <label for="contract_summary">Sözleşme Özeti</label>
                <textarea id="contract_summary" data-field="contract_summary" placeholder="Sözleşme üretiminde çıkacak kısa açıklama"></textarea>
              </div>
              <div class="field full">
                <label for="required_documents">Zorunlu Evraklar</label>
                <textarea id="required_documents" data-field="required_documents" placeholder="Örn: Türsab, ruhsat, sigorta, rehber sözleşmesi"></textarea>
              </div>
            </div>
            <div class="mini-grid">
              <div class="card">
                <h3>Kiraya Veren</h3>
                <div class="helper-text">Araç firması her zaman Kiraya Veren olarak kullanılacaktır.</div>
              </div>
              <div class="card">
                <h3>Kiracı</h3>
                <div class="helper-text">Acente her zaman Kiracı olarak kullanılacaktır.</div>
              </div>
            </div>
          </article>
        </div>
      </section>

      <div id="statusBox" class="status"></div>

      <div class="note">
        Tema renk ailesi ayarı bu ekranda görünmez; yalnızca Creatro supplier admin panelinden yönetilir. Bu sürümde firma kartı taslakları tarayıcıda saklanır ve sonraki adımda çekirdek veri modeline bağlanır.
      </div>
    </section>
  </div>

  <script>
    (function () {
      var API_BASE = 'http://localhost:3001';
      var TOKEN_KEYS = ['fleet_access_token', 'platform_core_token', 'agency_access_token'];
      var tabs = Array.prototype.slice.call(document.querySelectorAll('[data-tab]'));
      var sections = Array.prototype.slice.call(document.querySelectorAll('[data-section]'));
      var fields = Array.prototype.slice.call(document.querySelectorAll('[data-field]'));
      var saveBtn = document.getElementById('saveDraftBtn');
      var resetBtn = document.getElementById('resetDraftBtn');
      var statusBox = document.getElementById('statusBox');
      var companyTypeField = document.getElementById('company_type');
      var companyCodeField = document.getElementById('company_code');
      var taxNumberField = document.getElementById('tax_number');
      var portalModeField = document.getElementById('portal_mode');
      var portalModeBox = document.getElementById('portalModeBox');
      var responsiblePeopleList = document.getElementById('responsiblePeopleList');
      var addResponsiblePersonBtn = document.getElementById('addResponsiblePersonBtn');
      var currentDraftId = null;
      var responsiblePeople = [];
      var responsibleRoleOptions = [
        { value: 'yetkili', label: 'Yetkili' },
        { value: 'yonetici', label: 'Yönetici' },
        { value: 'operator', label: 'Operatör' },
        { value: 'muhasebe', label: 'Muhasebe' },
        { value: 'sozlesme', label: 'Sözleşme' },
        { value: 'evrak', label: 'Evrak' },
        { value: 'diger', label: 'Diğer' }
      ];

      function readToken() {
        for (var i = 0; i < TOKEN_KEYS.length; i += 1) {
          var value = localStorage.getItem(TOKEN_KEYS[i]) || '';
          if (value) return value;
        }
        return '';
      }

      function showStatus(message) {
        statusBox.textContent = message;
        statusBox.classList.add('show');
        window.clearTimeout(window.__statusTimer);
        window.__statusTimer = window.setTimeout(function () {
          statusBox.classList.remove('show');
        }, 2600);
      }

      function activateTab(name) {
        tabs.forEach(function (tab) {
          tab.classList.toggle('active', tab.getAttribute('data-tab') === name);
        });
        sections.forEach(function (section) {
          section.classList.toggle('active', section.getAttribute('data-section') === name);
        });
      }

      function collectData() {
        var out = {};
        fields.forEach(function (field) {
          out[field.getAttribute('data-field')] = field.value || '';
        });
        out.responsible_people = responsiblePeople.slice();
        return out;
      }

      function fillData(data) {
        fields.forEach(function (field) {
          var key = field.getAttribute('data-field');
          field.value = data && Object.prototype.hasOwnProperty.call(data, key) ? String(data[key] || '') : '';
        });
        responsiblePeople = data && Array.isArray(data.responsible_people) ? data.responsible_people.slice() : [];
        renderResponsiblePeople();
      }

      function isValidEmail(value) {
        var email = String(value || '').trim();
        if (!email) return true;
        var atIndex = email.lastIndexOf('@');
        if (atIndex <= 0) return false;
        var domain = email.slice(atIndex + 1);
        return domain.indexOf('.') > 0;
      }

      function renderResponsiblePeople() {
        if (!responsiblePeopleList) return;
        if (!responsiblePeople.length) {
          responsiblePeopleList.innerHTML = '<div class="helper-text">Henüz kişi eklenmedi.</div>';
          return;
        }
        responsiblePeopleList.innerHTML = responsiblePeople.map(function (item, index) {
          var role = String(item.role || 'yetkili');
          var options = responsibleRoleOptions.map(function (opt) {
            return '<option value="' + opt.value + '"' + (opt.value === role ? ' selected' : '') + '>' + opt.label + '</option>';
          }).join('');
          return ''
            + '<div class="person-item" data-person-index="' + index + '">'
            +   '<div class="person-item-head">'
            +     '<div class="person-item-title">Kişi ' + (index + 1) + '</div>'
            +     '<button class="mini-btn danger" type="button" data-remove-person="' + index + '">Kaldır</button>'
            +   '</div>'
            +   '<div class="field-grid">'
            +     '<div class="field">'
            +       '<label>Ad Soyad</label>'
            +       '<input type="text" data-person-field="full_name" data-person-index="' + index + '" value="' + escapeHtml(item.full_name || '') + '" placeholder="Ad soyad" />'
            +     '</div>'
            +     '<div class="field">'
            +       '<label>Sıfat</label>'
            +       '<select data-person-field="role" data-person-index="' + index + '">' + options + '</select>'
            +     '</div>'
            +     '<div class="field">'
            +       '<label>Telefon</label>'
            +       '<input type="text" data-person-field="phone" data-person-index="' + index + '" value="' + escapeHtml(item.phone || '') + '" placeholder="Telefon" />'
            +     '</div>'
            +     '<div class="field">'
            +       '<label>E-posta</label>'
            +       '<input type="email" data-person-field="email" data-person-index="' + index + '" value="' + escapeHtml(item.email || '') + '" placeholder="E-posta" />'
            +     '</div>'
            +     '<div class="field full">'
            +       '<label>Rol Açıklaması</label>'
            +       '<input type="text" data-person-field="role_note" data-person-index="' + index + '" value="' + escapeHtml(item.role_note || '') + '" placeholder="Diğer seçilirse özel sıfat veya açıklama yazılabilir" />'
            +     '</div>'
            +   '</div>'
            + '</div>';
        }).join('');
      }

      function escapeHtml(value) {
        return String(value || '')
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;')
          .replaceAll('"', '&quot;');
      }

      function addResponsiblePerson() {
        responsiblePeople.push({
          full_name: '',
          role: 'yetkili',
          phone: '',
          email: '',
          role_note: ''
        });
        renderResponsiblePeople();
      }

      function setPortalStatus(state) {
        if (!portalModeField || !portalModeBox) return;
        var mode = state && state.portal_mode ? String(state.portal_mode) : 'pasif';
        var reason = state && state.reason ? String(state.reason) : 'Portal durumu vergi numarası eşleşmesine göre otomatik belirlenir.';
        portalModeField.value = mode;
        portalModeBox.textContent = (mode === 'aktif' ? 'Aktif' : 'Pasif') + ' - ' + reason;
        portalModeBox.classList.toggle('is-active', mode === 'aktif');
        portalModeBox.classList.toggle('is-passive', mode !== 'aktif');
      }

      async function loadDraft() {
        var token = readToken();
        if (!token) return null;
        try {
          var res = await fetch(API_BASE + '/company-card-draft', {
            headers: { Authorization: 'Bearer ' + token }
          });
          if (!res.ok) return null;
          var data = await res.json();
          currentDraftId = data && data.id ? Number(data.id) : null;
          if (data && data.portal_status) setPortalStatus(data.portal_status);
          return data && typeof data.data === 'object' ? data.data : null;
        } catch (_) {
          return null;
        }
      }

      function isAutoCompanyCode(value) {
        return /^(TRN|ACN|FRM)-\d{3}$/i.test(String(value || '').trim());
      }

      async function loadCompanyCodeSuggestion(forceApply) {
        var token = readToken();
        if (!token || !companyTypeField || !companyCodeField) return;
        var currentValue = String(companyCodeField.value || '').trim();
        if (!forceApply && currentValue && !isAutoCompanyCode(currentValue)) return;
        try {
          var type = encodeURIComponent(companyTypeField.value || 'agency');
          var res = await fetch(API_BASE + '/company-code-suggestion?company_type=' + type, {
            headers: { Authorization: 'Bearer ' + token }
          });
          if (!res.ok) return;
          var data = await res.json();
          if (data && data.suggested_code) {
            companyCodeField.value = String(data.suggested_code);
          }
        } catch (_) {
          // Sessiz geç; kullanıcı manuel kod girebilir.
        }
      }

      async function loadPortalStatus() {
        var token = readToken();
        if (!token || !companyTypeField || !taxNumberField) return;
        try {
          var query = '?company_type=' + encodeURIComponent(companyTypeField.value || 'agency')
            + '&tax_number=' + encodeURIComponent(taxNumberField.value || '');
          if (currentDraftId) query += '&draft_id=' + encodeURIComponent(String(currentDraftId));
          var res = await fetch(API_BASE + '/company-portal-status' + query, {
            headers: { Authorization: 'Bearer ' + token }
          });
          if (!res.ok) return;
          var data = await res.json();
          setPortalStatus(data);
        } catch (_) {
          setPortalStatus({ portal_mode: 'pasif', reason: 'Portal durumu şu an doğrulanamadı.' });
        }
      }

      async function saveDraft() {
        var token = readToken();
        if (!token) {
          showStatus('Oturum bulunamadı. Yeniden giriş yapın.');
          return;
        }
        var payload = collectData();
        if (!isValidEmail(payload.email)) {
          showStatus('Firma e-postası geçersiz. @ işaretinden sonra en az bir nokta olmalıdır.');
          return;
        }
        if (!isValidEmail(payload.authority_email)) {
          showStatus('Yetkili e-postası geçersiz. @ işaretinden sonra en az bir nokta olmalıdır.');
          return;
        }
        var invalidResponsibleEmail = (payload.responsible_people || []).some(function (item) {
          return item && !isValidEmail(item.email);
        });
        if (invalidResponsibleEmail) {
          showStatus('Yetkili ve sorumlular bölümündeki e-posta geçersiz. @ işaretinden sonra en az bir nokta olmalıdır.');
          return;
        }
        try {
          var res = await fetch(API_BASE + '/company-card-draft', {
            method: 'PUT',
            headers: {
              Authorization: 'Bearer ' + token,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ data: payload })
          });
          if (!res.ok) {
            var errorData = null;
            try { errorData = await res.json(); } catch (_) {}
            showStatus((errorData && errorData.detail) || 'Firma kartı taslağı çekirdeğe kaydedilemedi.');
            return;
          }
          var data = await res.json();
          currentDraftId = data && data.id ? Number(data.id) : currentDraftId;
          if (data && data.portal_status) setPortalStatus(data.portal_status);
          showStatus('Firma kartı taslağı çekirdeğe kaydedildi.');
        } catch (_) {
          showStatus('Firma kartı taslağı çekirdeğe kaydedilemedi.');
        }
      }

      function resetDraft() {
        fillData({});
        activateTab('genel');
        showStatus('Form temizlendi. Kaydet dersen yeni boş taslak çekirdeğe yazılır.');
      }

      tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
          activateTab(tab.getAttribute('data-tab'));
        });
      });
      if (companyTypeField) {
        companyTypeField.addEventListener('change', function () {
          loadCompanyCodeSuggestion(true);
          loadPortalStatus();
        });
      }
      if (responsiblePeopleList) {
        responsiblePeopleList.addEventListener('click', function (event) {
          var removeIndex = event.target && event.target.getAttribute('data-remove-person');
          if (removeIndex === null || removeIndex === undefined) return;
          responsiblePeople = responsiblePeople.filter(function (_, index) {
            return index !== Number(removeIndex);
          });
          renderResponsiblePeople();
        });
        responsiblePeopleList.addEventListener('input', function (event) {
          var field = event.target && event.target.getAttribute('data-person-field');
          var index = Number(event.target && event.target.getAttribute('data-person-index'));
          if (!field || Number.isNaN(index) || !responsiblePeople[index]) return;
          responsiblePeople[index][field] = event.target.value || '';
        });
        responsiblePeopleList.addEventListener('change', function (event) {
          var field = event.target && event.target.getAttribute('data-person-field');
          var index = Number(event.target && event.target.getAttribute('data-person-index'));
          if (!field || Number.isNaN(index) || !responsiblePeople[index]) return;
          responsiblePeople[index][field] = event.target.value || '';
        });
      }
      if (addResponsiblePersonBtn) {
        addResponsiblePersonBtn.addEventListener('click', addResponsiblePerson);
      }
      if (taxNumberField) {
        taxNumberField.addEventListener('input', function () {
          loadPortalStatus();
        });
      }
      saveBtn.addEventListener('click', saveDraft);
      resetBtn.addEventListener('click', resetDraft);

      activateTab('genel');
      loadDraft().then(function (draft) {
        fillData(draft || {
          company_type: 'vehicle_company',
          company_name: 'Örnek Araç Firması'
        });
        if (!responsiblePeople.length) {
          responsiblePeople = [{
            full_name: '',
            role: 'yetkili',
            phone: '',
            email: '',
            role_note: ''
          }];
          renderResponsiblePeople();
        }
        loadCompanyCodeSuggestion(!draft || !draft.company_code);
        loadPortalStatus();
      });
    })();
  </script>
</body>
</html>
    """




