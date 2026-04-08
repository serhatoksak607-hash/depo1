from fastapi import FastAPI
from fastapi.responses import HTMLResponse


app = FastAPI(title="Creatro Acente Transfer AltyapÄ±sÄ±")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "domain": "agency", "port": "8003"}


@app.get("/", response_class=HTMLResponse)
def login_page() -> str:
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Acente Transfer GiriÅŸ</title>
  <style>
    :root {
      --bg-1: #121933;
      --bg-2: #213465;
      --bg-3: #1a2446;
      --panel: rgba(15, 23, 51, 0.84);
      --panel-line: rgba(160, 184, 255, 0.22);
      --line: rgba(183, 170, 241, 0.28);
      --accent: #6c7cff;
      --accent-2: #4357c9;
      --copper: #d9895d;
      --white: #f7f8fd;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--white);
      background:
        radial-gradient(circle at left top, rgba(217,137,93,0.18), transparent 24%),
        linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 58%, var(--bg-3) 100%);
      background-attachment: fixed;
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
    }
    .hero, .login-card {
      background: var(--panel);
      border: 1px solid var(--panel-line);
      border-radius: 24px;
      backdrop-filter: blur(12px);
      box-shadow: 0 20px 42px rgba(4, 9, 24, 0.34);
    }
    .hero { padding: 28px; }
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
      background: linear-gradient(135deg, rgba(108,124,255,0.24), rgba(217,137,93,0.20));
      border: 1px solid rgba(183,170,241,0.26);
      display: grid;
      place-items: center;
      color: #eef1ff;
      font-size: 22px;
      font-weight: 800;
    }
    h1 {
      margin: 0;
      font-size: clamp(34px, 5vw, 54px);
      line-height: 1.02;
      max-width: 10ch;
    }
    .hero p {
      color: #cfd5ee;
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
      border: 1px solid rgba(183,170,241,0.16);
      background: rgba(255,255,255,0.04);
      border-radius: 16px;
      padding: 14px;
    }
    .quick-card strong {
      display: block;
      margin-bottom: 6px;
      color: #f7f8fd;
      font-size: 14px;
    }
    .quick-card span {
      color: #cfd5ee;
      font-size: 12px;
      line-height: 1.55;
    }
    .login-card { padding: 24px; }
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
      border: 1px solid rgba(183,170,241,0.28);
      background: rgba(20, 28, 60, 0.62);
      color: #eef1ff;
    }
    .field { margin-bottom: 14px; }
    .field label {
      display: block;
      margin-bottom: 7px;
      color: #eef1ff;
      font-size: 12px;
      font-weight: 700;
    }
    .field input {
      width: 100%;
      min-height: 48px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.08);
      color: #f7f8fd;
      padding: 0 14px;
      outline: none;
      font-size: 14px;
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
      color: #171c43;
      background: linear-gradient(180deg, #aeb8ff 0%, #7b8cff 100%);
      box-shadow: 0 10px 20px rgba(108,124,255,0.24);
    }
    .ghost-link {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      text-decoration: none;
      color: #eef1ff;
      background: rgba(255,255,255,0.06);
      border-color: rgba(183,170,241,0.24);
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
      border-top: 1px solid rgba(183,170,241,0.14);
      padding-top: 10px;
      color: #cfd5ee;
      font-size: 12px;
    }
    .hint, .error {
      margin-top: 14px;
      border-radius: 14px;
      padding: 12px 14px;
      font-size: 12px;
      line-height: 1.6;
    }
    .hint {
      background: rgba(217,137,93,0.14);
      border: 1px solid rgba(217,137,93,0.20);
      color: #f6d6c3;
    }
    .error {
      display: none;
      background: rgba(191, 76, 93, 0.18);
      border: 1px solid rgba(255, 158, 171, 0.22);
      color: #ffe5e9;
    }
    @media (max-width: 860px) {
      .shell { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-top">
        <div class="mark">AT</div>
        <div>
          <strong>Acente Transfer AltyapÄ±sÄ±</strong>
          <span>Creatro destekli acente gÃ¶rÃ¼nÃ¼mÃ¼</span>
        </div>
      </div>

      <h1>Transfer odaklÄ±<br />acente giriÅŸi</h1>
      <p>
        Bu giriÅŸ ekranÄ± acente tarafÄ± iÃ§in sade, rezervasyon ve hizmet takibini Ã¶ne alan ayrÄ± bir yÃ¼zdÃ¼r.
        Kimlik doÄŸrulama ortak Ã§ekirdek olan <strong>8001</strong> Ã¼zerinden ilerler.
      </p>

      <div class="quick-grid">
        <div class="quick-card">
          <strong>Transfer Takibi</strong>
          <span>Talep, rezervasyon, uÃ§uÅŸ etkisi ve sade operasyon gÃ¶rÃ¼nÃ¼mÃ¼ ilk fazda burada toplanÄ±r.</span>
        </div>
        <div class="quick-card">
          <strong>Kongreye AÃ§Ä±k YapÄ±</strong>
          <span>Sonraki aÅŸamada kongre kayÄ±t ve katÄ±lÄ±mcÄ± akÄ±ÅŸlarÄ± bu yÃ¼zÃ¼n iÃ§ine baÄŸlanÄ±r.</span>
        </div>
        <div class="quick-card">
          <strong>Tek GiriÅŸ</strong>
          <span>AynÄ± kullanÄ±cÄ± adÄ± ve ÅŸifre ile Creatro, araÃ§ firmasÄ± ve acente yÃ¶nlerine ayrÄ±labilirsin.</span>
        </div>
        <div class="quick-card">
          <strong>Merkez Tema</strong>
          <span>Creatro marka alanÄ± sabit kalÄ±r, proje/acente hissi tema ailesiyle yÃ¼zeye yansÄ±r.</span>
        </div>
      </div>
    </section>

    <section class="login-card">
      <div class="login-head">
        <div>
          <span class="chip">Port 8003</span>
          <h2>GiriÅŸ Yap</h2>
          <p>Portal kullanÄ±cÄ±larÄ± ortak kimlik doÄŸrulama ile oturum aÃ§ar. AynÄ± oturumla Ã§alÄ±ÅŸma tipi seÃ§imine geÃ§ilir.</p>
        </div>
        <span class="chip">Ã‡ekirdek Auth: 8001</span>
      </div>

      <form id="loginForm">
        <div class="field">
          <label for="username">KullanÄ±cÄ± AdÄ± / Kod</label>
          <input id="username" name="username" type="text" autocomplete="username" placeholder="Ã–rn: CreaTRo veya kullanÄ±cÄ± kodu" />
        </div>
        <div class="field">
          <label for="password">Åifre</label>
          <input id="password" name="password" type="password" autocomplete="current-password" placeholder="Åifrenizi girin" />
        </div>
        <div class="actions">
          <button id="submitBtn" type="submit">Acente Paneline Gir</button>
          <a class="ghost-link" href="http://localhost:3000/modules-ui">3000 ReferansÄ±nÄ± AÃ§</a>
        </div>
        <div id="errorBox" class="error"></div>
      </form>

      <div class="helper">
        <div class="helper-row">
          <span>Oturum tipi</span>
          <strong>Portal KullanÄ±cÄ±sÄ±</strong>
        </div>
        <div class="helper-row">
          <span>Sonraki adÄ±m</span>
          <strong>Ã‡alÄ±ÅŸma tipi seÃ§imi</strong>
        </div>
        <div class="helper-row">
          <span>Tek giriÅŸ</span>
          <strong>Creatro / AraÃ§ FirmasÄ± / Acente</strong>
        </div>
      </div>

      <div class="hint">
        GiriÅŸ baÅŸarÄ±lÄ± olursa token tarayÄ±cÄ±da saklanÄ±r ve Ã§alÄ±ÅŸma tipi seÃ§imi ekranÄ±na yÃ¶nlendirilirsiniz.
      </div>
    </section>
  </div>

  <script>
    (function () {
      var API_BASE = 'http://localhost:3001';
      var TOKEN_KEY = 'agency_access_token';
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
            localStorage.setItem('fleet_access_token', token);
            window.location.href = 'http://localhost:3002/panel-secimi';
            return;
          }
        } catch (err) {}
        localStorage.removeItem(TOKEN_KEY);
      }

      form.addEventListener('submit', async function (event) {
        event.preventDefault();
        setError('');
        var u = String(username.value || '').trim();
        var p = String(password.value || '');
        if (!u || !p) {
          setError('KullanÄ±cÄ± adÄ± ve ÅŸifre zorunludur.');
          return;
        }
        submitBtn.disabled = true;
        submitBtn.textContent = 'GiriÅŸ yapÄ±lÄ±yor...';
        try {
          var res = await fetch(API_BASE + '/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p })
          });
          var data = {};
          try { data = await res.json(); } catch (err) {}
          if (!res.ok) {
            setError(data.detail || 'GiriÅŸ baÅŸarÄ±sÄ±z oldu.');
            return;
          }
          if (!data.access_token) {
            setError('Access token alÄ±namadÄ±.');
            return;
          }
          localStorage.setItem(TOKEN_KEY, String(data.access_token));
          localStorage.setItem('platform_core_token', String(data.access_token));
          localStorage.setItem('fleet_access_token', String(data.access_token));
          window.location.href = 'http://localhost:3002/panel-secimi';
        } catch (err) {
          setError('Ã‡ekirdek giriÅŸ servisine baÄŸlanÄ±lamadÄ±.');
        } finally {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Acente Paneline Gir';
        }
      });

      checkExistingSession();
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
  <title>Acente Bildirim Merkezi</title>
  <style>
    :root {
      --bg-1: #121933;
      --bg-2: #213465;
      --bg-3: #1a2446;
      --panel: rgba(15, 23, 51, 0.84);
      --panel-line: rgba(160, 184, 255, 0.22);
      --card-bg: linear-gradient(180deg, rgba(248, 249, 255, 0.97) 0%, rgba(235, 239, 255, 0.93) 100%);
      --card-line: rgba(150, 170, 255, 0.34);
      --ink: #2a2453;
      --white: #f7f8fd;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--white);
      background:
        radial-gradient(circle at left top, rgba(217,137,93,0.18), transparent 24%),
        linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 58%, var(--bg-3) 100%);
      background-attachment: fixed;
    }
    .wrap { width:min(1240px, calc(100% - 32px)); margin:22px auto 40px; }
    .head,.panel { background:var(--panel); border:1px solid var(--panel-line); border-radius:20px; backdrop-filter:blur(10px); box-shadow:0 18px 36px rgba(4, 9, 24, 0.30); }
    .head { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:14px 16px; margin-bottom:16px; }
    .head a { color:#eef1ff; text-decoration:none; border:1px solid rgba(183,170,241,0.24); background:rgba(255,255,255,0.06); min-height:38px; display:inline-flex; align-items:center; justify-content:center; border-radius:12px; padding:0 14px; font-weight:700; font-size:13px; }
    .panel { padding:24px; }
    .layout { display:grid; grid-template-columns:420px 1fr; gap:16px; }
    .card { background:var(--card-bg); border:1px solid var(--card-line); border-radius:18px; padding:18px; color:var(--ink); }
    .card h3 { margin:0 0 12px; font-size:18px; }
    .pref-list,.history-list { display:grid; gap:10px; }
    .pref-row,.history-item { border:1px solid rgba(80,97,188,0.12); border-radius:16px; padding:14px; background:rgba(255,255,255,0.78); }
    .channel-list { display:flex; flex-wrap:wrap; gap:10px; margin-top:10px; }
    .channel-list label { display:inline-flex; gap:6px; align-items:center; font-size:12px; }
    .status { margin-top:16px; border-radius:14px; padding:12px 14px; background:rgba(108,124,255,0.12); border:1px solid rgba(108,124,255,0.20); color:#2f3b88; font-size:12px; line-height:1.6; display:none; }
    .status.show { display:block; }
    .action-btn { min-height:40px; border-radius:12px; padding:0 14px; border:1px solid rgba(160,184,255,0.28); background:rgba(108,124,255,0.10); color:#24327f; font-weight:700; cursor:pointer; }
    .action-btn.primary { color:#fff; background:linear-gradient(180deg, #7b8cff 0%, #5f72f2 100%); border-color:transparent; }
    @media (max-width: 960px) { .layout { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="head">
      <div>
        <strong>Acente Bildirim Merkezi</strong>
        <span>Aktif kullanıcı tercihleri ve geriye dönük bildirim geçmişi</span>
      </div>
      <a href="/">Giriş Ekranına Dön</a>
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
      var TOKEN_KEYS = ['agency_access_token', 'platform_core_token', 'fleet_access_token'];
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
        window.clearTimeout(window.__agencyNotificationTimer);
        window.__agencyNotificationTimer = window.setTimeout(function () {
          statusBox.classList.remove('show');
        }, 2600);
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
          return '<div class="history-item"><strong>' + (item.title || '-') + '</strong><div>Kanal: ' + (item.channel || '-') + ' | Durum: ' + (item.status || '-') + '</div><div>' + (item.summary || '-') + '</div><div>' + (item.created_at || '-') + '</div></div>';
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


