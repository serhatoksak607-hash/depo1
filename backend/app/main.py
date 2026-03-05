import os
import io
import uuid
import zipfile
import hashlib
import secrets
import re
import json
import unicodedata
import urllib.request
import qrcode
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import redis
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, Header, Form, Request, Cookie
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, Response
from rq import Queue
from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session

from .db import Base, SessionLocal, engine
from .arvento import fetch_arvento_positions
from .models import (
    ModuleData,
    ModuleReport,
    OpsEvent,
    Project,
    ProjectModule,
    ProjectServiceProduct,
    ServiceProduct,
    SupplierCompany,
    SupplierClient,
    SupplierStaff,
    SupplierBooking,
    SupplierBookingContact,
    Tenant,
    SupplierServiceType,
    SupplierSmsQueue,
    SupplierSmsTemplate,
    TranslationAssignment,
    TranslationListenerEvent,
    TranslationSession,
    Transfer,
    Upload,
    User,
    DriverPanelToken,
    UserModuleAccess,
    UserProjectAccess,
    UserSession,
)
from .ops_events import ALLOWED_OPS_EVENT_TYPES, EVENT_AUDIT_ACTION


ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".zip"}
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "storage/uploads"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
RQ_QUEUE = os.getenv("RQ_QUEUE", "upload_processing")
SESSION_HOURS = int(os.getenv("SESSION_HOURS", "24"))
SESSION_IDLE_MINUTES = int(os.getenv("SESSION_IDLE_MINUTES", "10"))
DEFAULT_TARGET_AIRPORTS = os.getenv("DEFAULT_TARGET_AIRPORTS", "").strip().upper()
SMS_SENDER_TITLE = os.getenv("SMS_SENDER_TITLE", "CREATRO").strip() or "CREATRO"
ADMIN_DB_COOKIE_NAME = "admin_db_session"
APP_ENV = str(os.getenv("APP_ENV") or "development").strip().lower()
CORS_ORIGINS_RAW = str(os.getenv("CORS_ORIGINS") or "*").strip()
TRUSTED_HOSTS_RAW = str(os.getenv("TRUSTED_HOSTS") or "*").strip()
COOKIE_SECURE = str(os.getenv("COOKIE_SECURE") or ("1" if APP_ENV == "production" else "0")).strip().lower() in {"1", "true", "yes", "on"}
COOKIE_SAMESITE = str(os.getenv("COOKIE_SAMESITE") or ("none" if COOKIE_SECURE else "lax")).strip().lower()
if COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    COOKIE_SAMESITE = "none" if COOKIE_SECURE else "lax"

CITY_TO_IATA = {
    "ADANA": "ADA,COV",
    "ADIYAMAN": "ADF",
    "AFYONKARAHISAR": "KZR",
    "AGRI": "AJI",
    "AKSARAY": "NAV",
    "AMASYA": "MZH",
    "ANKARA": "ESB",
    "ANTALYA": "AYT",
    "ARDAHAN": "KSY",
    "ARTVIN": "RZV",
    "AYDIN": "ADB",
    "BALIKESIR": "EDO",
    "BARTIN": "ONQ",
    "BATMAN": "BAL",
    "BAYBURT": "ERZ",
    "BILECIK": "YEI",
    "BINGOL": "BGG",
    "BITLIS": "VAN",
    "BOLU": "KCO",
    "BURDUR": "ISE",
    "BURSA": "YEI",
    "CANAKKALE": "CKZ",
    "CANKIRI": "ESB",
    "CORUM": "MZH",
    "DENIZLI": "DNZ",
    "DIYARBAKIR": "DIY",
    "DUZCE": "KCO",
    "EDIRNE": "TEQ",
    "ELAZIG": "EZS",
    "ERZINCAN": "ERC",
    "ERZURUM": "ERZ",
    "ESKISEHIR": "AOE",
    "GAZIANTEP": "GZT",
    "GIRESUN": "OGU",
    "GUMUSHANE": "TZX",
    "HAKKARI": "YKO",
    "HATAY": "HTY",
    "IGDIR": "IGD",
    "ISPARTA": "ISE",
    "ISTANBUL": "IST,SAW",
    "IZMIR": "ADB",
    "KAHRAMANMARAS": "KCM",
    "KARABUK": "ONQ",
    "KARAMAN": "KYA",
    "KARS": "KSY",
    "KASTAMONU": "KFS",
    "KAYSERI": "ASR",
    "KILIS": "GZT",
    "KIRIKKALE": "ESB",
    "KIRKLARELI": "TEQ",
    "KIRSEHIR": "NAV",
    "KOCAELI": "KCO",
    "KONYA": "KYA",
    "KUTAHYA": "KZR",
    "MALATYA": "MLX",
    "MANISA": "ADB",
    "MARDIN": "MQM",
    "MERSIN": "COV",
    "MUGLA": "DLM,BJV",
    "MUS": "MSR",
    "NEVSEHIR": "NAV",
    "NIGDE": "NAV",
    "ORDU": "OGU",
    "OSMANIYE": "COV",
    "RIZE": "RZV",
    "SAKARYA": "KCO",
    "SAMSUN": "SZF",
    "SANLIURFA": "GNY",
    "SIIRT": "SXZ",
    "SINOP": "NOP",
    "SIRNAK": "NKT",
    "SIVAS": "VAS",
    "TEKIRDAG": "TEQ",
    "TOKAT": "TJK",
    "TRABZON": "TZX",
    "TUNCELI": "EZS",
    "USAK": "KZR",
    "VAN": "VAN",
    "YALOVA": "SAW",
    "YOZGAT": "ASR",
    "ZONGULDAK": "ONQ",
}
PROJECT_CITY_CODES = sorted(CITY_TO_IATA.keys())
PROJECT_CITY_PRIORITY = ["ISTANBUL", "ANKARA", "ANTALYA", "IZMIR"]
ALLOWED_PROJECT_CITIES = set(PROJECT_CITY_CODES)

TRANSFER_ACTION_FLOW = [
    "karsilamaya_gectim",
    "karsiladim",
    "misafiri_bekliyorum",
    "misafiri_aldim",
    "misafiri_biraktim",
]
PERSONNEL_ACTION_FLOW = ["bekliyorum", "aldim", "biraktim"]

ROLE_LEVEL = {
    "driver": 20,
    "greeter": 25,
    "participant": 30,
    "tenant_operator": 40,
    "interpreter": 45,
    "supplier_admin": 50,
    "tenant_manager": 60,
    "tenant_admin": 80,
    "supertranslator": 90,
    "superadmin_staff": 95,
    "superadmin": 100,
    # backward compatibility
    "operator": 40,
    "manager": 60,
    "admin": 80,
}

ROLE_ALIASES = {
    "operator": "tenant_operator",
    "manager": "tenant_manager",
    "admin": "tenant_admin",
}

ALLOWED_USER_ROLES = {
    "superadmin",
    "superadmin_staff",
    "supertranslator",
    "tenant_admin",
    "tenant_manager",
    "tenant_operator",
    "participant",
    "interpreter",
    "supplier_admin",
    "greeter",
    "driver",
    # legacy accepts
    "admin",
    "manager",
    "operator",
}

MANAGEMENT_PROJECT_CODE = "YONETIM"
DEFAULT_MODULE_KEYS = [
    "transfer",
    "kayit",
    "konaklama",
    "toplanti",
    "tercuman",
    "muhasebe_finans",
    "duyurular",
    "yonetim",
]
MODULE_DISPLAY_ORDER = [
    "transfer",
    "kayit",
    "konaklama",
    "toplanti",
    "tercuman",
    "muhasebe_finans",
    "duyurular",
    "yonetim",
]
MODULE_HREF_MAP = {
    "transfer": "/transfer-ui",
    "kayit": "/kayit-ui",
    "konaklama": "/konaklama-ui",
    "toplanti": "/toplanti-ui",
    "tercuman": "/tercuman-ui",
    "muhasebe_finans": "/muhasebe-finans-ui",
    "duyurular": "/duyurular-ui",
    "yonetim": "/yonetici-ui",
}
SERVICE_PRODUCT_CATEGORIES = {"kayit", "konaklama", "transfer", "dis_katilim", "diger"}
ALLOWED_MODULE_DATA_NAMES = {
    "kayit",
    "konaklama",
    "transfer",
    "muhasebe_finans",
    "toplanti",
    "duyurular",
}
MODULES_REQUIRING_KAYIT = {"konaklama", "transfer", "toplanti"}
AUDIT_SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "secret",
    "api_key",
}
AUDIT_SKIP_PREFIXES = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PASSIVE_WRITE_ALLOW_PATHS = {
    "/auth/login",
    "/auth/active-project",
    "/auth/management-project",
    "/auth/keepalive",
}
MODULE_ENFORCEMENT_EXCLUDE_PREFIXES = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/assets/",
    "/auth/",
    "/admin-db/",
    "/admin/db/",
    "/driver-panel",
    "/greeter-panel",
}
MODULE_ENFORCEMENT_ROUTE_MAP = [
    ("/transfer-ui", "transfer"),
    ("/transfer-list-ui", "transfer"),
    ("/upload-ui", "transfer"),
    ("/upload", "transfer"),
    ("/uploads", "transfer"),
    ("/transfers", "transfer"),
    ("/supplier-transfers", "transfer"),
    ("/supplier-transfers-ui", "transfer"),
    ("/exports/zip", "transfer"),
    ("/kayit-ui", "kayit"),
    ("/desk-ui", "kayit"),
    ("/desk/search", "kayit"),
    ("/konaklama-ui", "konaklama"),
    ("/toplanti-ui", "toplanti"),
    ("/tercuman-ui", "tercuman"),
    ("/translation", "tercuman"),
    ("/muhasebe-finans-ui", "muhasebe_finans"),
    ("/finance/", "muhasebe_finans"),
    ("/duyurular-ui", "duyurular"),
    ("/yonetici-ui", "yonetim"),
    ("/projects-ui", "yonetim"),
    ("/users-ui", "yonetim"),
    ("/reports-ui", "yonetim"),
]

app = FastAPI(title="Transport Module MVP")
_cors_origins = [item.strip() for item in CORS_ORIGINS_RAW.split(",") if item.strip()]
if not _cors_origins:
    _cors_origins = ["*"]
_trusted_hosts = [item.strip() for item in TRUSTED_HOSTS_RAW.split(",") if item.strip()]
if not _trusted_hosts:
    _trusted_hosts = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_trusted_hosts)

redis_client = redis.Redis.from_url(REDIS_URL)
upload_queue = Queue(RQ_QUEUE, connection=redis_client)
APP_DIR = Path(__file__).resolve().parent

STANDARD_HEADER_CSS = """
<style id="creatro-standard-header">
  html, body { margin: 0 !important; padding: 0 !important; }
  .wrap { width: 100% !important; max-width: none !important; margin: 0 !important; padding: 10px 12px !important; padding-top: 0 !important; box-sizing: border-box !important; }
  .box { width: 100% !important; max-width: none !important; box-sizing: border-box !important; }
  .table-wrap { width: 100% !important; overflow-x: auto !important; }
  table { width: 100% !important; }
  table thead th, table th { text-align: center !important; }
  table th, table td {
    font-weight: 700 !important;
    white-space: nowrap !important;
    word-break: keep-all !important;
    overflow-wrap: normal !important;
  }
  table[data-auto-sort="1"] thead tr:first-child th {
    cursor: pointer !important;
    user-select: none !important;
  }
  table[data-auto-sort="1"] thead tr:first-child th.sort-asc::after {
    content: " \\2191";
    font-size: 10px;
    opacity: 0.85;
  }
  table[data-auto-sort="1"] thead tr:first-child th.sort-desc::after {
    content: " \\2193";
    font-size: 10px;
    opacity: 0.85;
  }
  .head {
    width: 100vw !important;
    max-width: 100vw !important;
    margin: 0 calc(50% - 50vw) 10px calc(50% - 50vw) !important;
    border-radius: 0 !important;
    box-sizing: border-box !important;
    background: #0A1024 !important;
    color: #fff !important;
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    padding: 10px 12px !important;
    gap: 10px !important;
  }
  .head-left, .module-nav { display: flex !important; gap: 6px !important; flex-wrap: wrap !important; align-items: center !important; }
  .head-right { display: flex !important; gap: 8px !important; align-items: center !important; margin-left: auto !important; margin-right: 0 !important; }
  .right-panel {
    border: 0 !important;
    background: transparent !important;
    padding: 0 !important;
    box-shadow: none !important;
  }
  .token-badge-gold {
    display: inline-flex !important;
    align-items: center !important;
    background: rgba(255, 214, 102, 0.18) !important;
    color: #FFD666 !important;
    border: 1px solid #D4AF37 !important;
    border-radius: 8px !important;
    padding: 6px 11px !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    white-space: nowrap !important;
    transform: none !important;
    margin-left: 8px !important;
  }
  .token-badge-gold .tb-crea { color: #FFFFFF !important; }
  .token-badge-gold .tb-token { color: #FFD666 !important; }
  .m-btn {
    background: rgba(255,255,255,0.18) !important;
    color: #fff !important;
    text-decoration: none !important;
    border: 1px solid rgba(255,255,255,0.35) !important;
    border-radius: 8px !important;
    padding: 5px 9px !important;
    font-size: 12px !important;
    display: inline-flex !important;
    align-items: center !important;
  }
  .m-btn.active { background: #fff !important; color: #0A1024 !important; font-weight: 700 !important; }
  .lang-mini {
    position: fixed !important;
    right: 10px !important;
    bottom: 10px !important;
    top: auto !important;
    margin-left: 0 !important;
    z-index: 1205 !important;
    font-size: 11px !important;
    padding: 4px 6px !important;
    border-radius: 6px !important;
    border: 1px solid rgba(159,216,255,0.45) !important;
    background: #0A1024 !important;
    color: #fff !important;
  }
  .project-switch-btn {
    display: inline-flex !important;
    align-items: center !important;
    margin-left: 8px !important;
    padding: 4px 8px !important;
    border-radius: 8px !important;
    border: 1px solid rgba(159,216,255,0.78) !important;
    color: #9FD8FF !important;
    background: rgba(7,19,46,0.28) !important;
    text-decoration: none !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
  }
  .project-switch-wrap {
    position: relative !important;
    display: inline-flex !important;
    align-items: center !important;
    margin-left: 0 !important;
  }
  .project-switch-menu {
    position: absolute !important;
    top: 100% !important;
    right: 0 !important;
    min-width: 260px !important;
    max-height: 280px !important;
    overflow: auto !important;
    background: #0A1024 !important;
    border: 1px solid rgba(159,216,255,0.45) !important;
    border-radius: 8px !important;
    padding: 6px !important;
    display: none !important;
    z-index: 1200 !important;
  }
  .project-switch-wrap.open .project-switch-menu { display: block !important; }
  .project-switch-item {
    display: block !important;
    width: 100% !important;
    text-align: left !important;
    background: transparent !important;
    color: #9FD8FF !important;
    border: 0 !important;
    border-radius: 6px !important;
    padding: 6px 8px !important;
    font-size: 12px !important;
    cursor: pointer !important;
  }
  .project-switch-item:hover { background: rgba(159,216,255,0.16) !important; color: #fff !important; }

  .tabs { display: flex !important; gap: 8px !important; flex-wrap: wrap !important; margin-top: 10px !important; }
  .tab {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: #2b7fff !important;
    color: #fff !important;
    border: 0 !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    cursor: pointer !important;
    text-decoration: none !important;
    font-weight: 700 !important;
  }
  .tab.alt { background: #5c6b82 !important; }
  .tab:visited { color: #fff !important; }
  .computer-badge {
    width: 34px !important;
    height: 34px !important;
    border-radius: 999px !important;
    border: 2px solid #d4af37 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #d4af37 !important;
    background: rgba(212,175,55,0.12) !important;
    flex: 0 0 auto !important;
    box-sizing: border-box !important;
    text-decoration: none !important;
    z-index: 30 !important;
  }
  .computer-badge svg {
    width: 18px !important;
    height: 18px !important;
    stroke: currentColor !important;
    fill: none !important;
    stroke-width: 1.8 !important;
    stroke-linecap: round !important;
    stroke-linejoin: round !important;
    display: block !important;
  }
  .computer-badge:hover { background: rgba(212,175,55,0.24) !important; color: #f7d774 !important; border-color: #f7d774 !important; }
  .computer-badge-header {
    position: absolute !important;
    left: 50% !important;
    top: 50% !important;
    transform: translate(-50%, -50%) !important;
  }
  .footer-brand .computer-badge-footer {
    position: absolute !important;
    left: 50% !important;
    top: 50% !important;
    transform: translate(-50%, -50%) !important;
  }
  .session-warning-overlay {
    position: fixed !important;
    inset: 0 !important;
    background: rgba(10,16,36,0.52) !important;
    display: none !important;
    align-items: center !important;
    justify-content: center !important;
    z-index: 4000 !important;
  }
  .session-warning-overlay.show { display: flex !important; }
  .session-warning-card {
    width: min(520px, 92vw) !important;
    background: #ffffff !important;
    border: 1px solid #d8e0ee !important;
    border-radius: 12px !important;
    box-shadow: 0 12px 30px rgba(10,16,36,0.28) !important;
    padding: 16px !important;
    color: #1c2635 !important;
  }
  .session-warning-title { font-size: 17px !important; font-weight: 700 !important; margin: 0 0 8px 0 !important; }
  .session-warning-text { font-size: 14px !important; margin: 0 0 10px 0 !important; }
  .session-warning-counter { font-size: 22px !important; font-weight: 800 !important; color: #b91c1c !important; margin-bottom: 12px !important; }
  .session-warning-actions { display: flex !important; gap: 8px !important; justify-content: flex-end !important; }
  .session-warning-btn {
    border: 0 !important;
    border-radius: 8px !important;
    padding: 9px 12px !important;
    font-weight: 700 !important;
    cursor: pointer !important;
  }
  .session-warning-btn.yes { background: #0a7a2f !important; color: #fff !important; }
  .session-warning-btn.no { background: #b91c1c !important; color: #fff !important; }
  .save-btn-prominent {
    background: linear-gradient(135deg, #0f8f3f 0%, #0a7a2f 100%) !important;
    color: #ffffff !important;
    border: 1px solid #0b6e2e !important;
    border-radius: 10px !important;
    padding: 9px 14px !important;
    font-weight: 800 !important;
    letter-spacing: 0.2px !important;
    box-shadow: 0 6px 16px rgba(10, 122, 47, 0.28) !important;
    transition: transform .12s ease, box-shadow .12s ease, filter .12s ease !important;
  }
  .save-btn-prominent:hover {
    filter: brightness(1.06) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 10px 20px rgba(10, 122, 47, 0.33) !important;
  }
  .save-btn-prominent:active {
    transform: translateY(0) !important;
    box-shadow: 0 6px 12px rgba(10, 122, 47, 0.26) !important;
  }
  .save-btn-prominent:disabled {
    opacity: 0.65 !important;
    cursor: not-allowed !important;
    transform: none !important;
    box-shadow: none !important;
  }
</style>
"""

STANDARD_HEADER_JS = """
<script id="creatro-standard-header-js">
  document.addEventListener('DOMContentLoaded', function () {
    var path = (window.location && window.location.pathname) ? window.location.pathname : '';
    var sessionWarn = {
      token: localStorage.getItem('access_token') || '',
      expiresAtMs: 0,
      pollTimer: null,
      tickTimer: null,
      popupEl: null,
      counterEl: null,
      keepaliveBusy: false,
      shown: false
    };
    function cleanupAndLogout() {
      try {
        var uiLang = localStorage.getItem('ui_lang') || '';
        localStorage.clear();
        sessionStorage.clear();
        if (uiLang) localStorage.setItem('ui_lang', uiLang);
      } catch (_) {}
      window.location.href = '/';
    }
    function ensureSessionPopup() {
      if (sessionWarn.popupEl) return;
      var root = document.createElement('div');
      root.id = 'sessionWarningOverlay';
      root.className = 'session-warning-overlay';
      root.innerHTML = ''
        + '<div class="session-warning-card" role="dialog" aria-modal="true" aria-labelledby="sessionWarningTitle">'
        + '<h3 id="sessionWarningTitle" class="session-warning-title">Oturum Süreniz Doluyor</h3>'
        + '<p class="session-warning-text">İşleminize devam ediyor musunuz?</p>'
        + '<div id="sessionWarningCounter" class="session-warning-counter">59</div>'
        + '<div class="session-warning-actions">'
        + '<button id="sessionWarningNo" class="session-warning-btn no" type="button">Hayır</button>'
        + '<button id="sessionWarningYes" class="session-warning-btn yes" type="button">Evet</button>'
        + '</div></div>';
      document.body.appendChild(root);
      sessionWarn.popupEl = root;
      sessionWarn.counterEl = document.getElementById('sessionWarningCounter');
      var noBtn = document.getElementById('sessionWarningNo');
      var yesBtn = document.getElementById('sessionWarningYes');
      if (noBtn) noBtn.addEventListener('click', cleanupAndLogout);
      if (yesBtn) yesBtn.addEventListener('click', async function () {
        if (sessionWarn.keepaliveBusy) return;
        sessionWarn.keepaliveBusy = true;
        try {
          var res = await fetch('/auth/keepalive', {
            method: 'POST',
            headers: { Authorization: 'Bearer ' + sessionWarn.token }
          });
          if (!res.ok) { cleanupAndLogout(); return; }
          var data = await res.json().catch(function(){ return {}; });
          var nextMs = Date.parse(String(data.expires_at || ''));
          if (!Number.isFinite(nextMs)) { cleanupAndLogout(); return; }
          sessionWarn.expiresAtMs = nextMs;
          sessionWarn.shown = false;
          if (sessionWarn.popupEl) sessionWarn.popupEl.classList.remove('show');
        } catch (_) {
          cleanupAndLogout();
          return;
        } finally {
          sessionWarn.keepaliveBusy = false;
        }
      });
    }
    async function refreshSessionStatus() {
      if (!sessionWarn.token) return;
      try {
        var res = await fetch('/auth/session-status', {
          headers: { Authorization: 'Bearer ' + sessionWarn.token }
        });
        if (!res.ok) { cleanupAndLogout(); return; }
        var data = await res.json().catch(function(){ return {}; });
        var nextMs = Date.parse(String(data.expires_at || ''));
        if (!Number.isFinite(nextMs)) { cleanupAndLogout(); return; }
        sessionWarn.expiresAtMs = nextMs;
      } catch (_) {}
    }
    function startSessionWarning() {
      if (!sessionWarn.token) return;
      ensureSessionPopup();
      refreshSessionStatus();
      if (!sessionWarn.pollTimer) {
        sessionWarn.pollTimer = setInterval(refreshSessionStatus, 15000);
      }
      if (!sessionWarn.tickTimer) {
        sessionWarn.tickTimer = setInterval(function () {
          if (!sessionWarn.expiresAtMs) return;
          var remaining = Math.floor((sessionWarn.expiresAtMs - Date.now()) / 1000);
          if (remaining <= 0) {
            cleanupAndLogout();
            return;
          }
          if (remaining <= 59) {
            if (sessionWarn.popupEl) sessionWarn.popupEl.classList.add('show');
            sessionWarn.shown = true;
            if (sessionWarn.counterEl) sessionWarn.counterEl.textContent = String(remaining);
          } else if (sessionWarn.shown) {
            if (sessionWarn.popupEl) sessionWarn.popupEl.classList.remove('show');
            sessionWarn.shown = false;
          }
        }, 1000);
      }
    }
    startSessionWarning();
    function isSaveButtonText(txt) {
      var t = String(txt || '').trim().toLocaleLowerCase('tr-TR');
      return t === 'kaydet' || t === 'save';
    }
    function applyProminentSaveButtons() {
      var nodes = Array.prototype.slice.call(document.querySelectorAll(
        'button, input[type="button"], input[type="submit"], a[role="button"]'
      ));
      nodes.forEach(function (el) {
        if (!el) return;
        var id = String(el.id || '').toLowerCase();
        var cls = String(el.className || '').toLowerCase();
        var txt = el.tagName === 'INPUT' ? (el.value || '') : (el.textContent || '');
        var byName = id.indexOf('save') >= 0 || cls.indexOf('save') >= 0;
        var byText = isSaveButtonText(txt);
        if (byName || byText) el.classList.add('save-btn-prominent');
      });
    }
    applyProminentSaveButtons();
    var saveBtnObserverTick = null;
    var saveBtnObserver = new MutationObserver(function(){
      if (saveBtnObserverTick) return;
      saveBtnObserverTick = setTimeout(function(){
        saveBtnObserverTick = null;
        applyProminentSaveButtons();
      }, 60);
    });
    if (document.body) {
      saveBtnObserver.observe(document.body, { childList: true, subtree: true, characterData: true });
    }
    function createComputerBadge(extraClass) {
      var wrap = document.createElement('a');
      wrap.className = 'computer-badge ' + (extraClass || '');
      wrap.href = '/desk-ui';
      wrap.title = 'Desk';
      wrap.setAttribute('aria-label', 'Desk');
      wrap.innerHTML = ''
        + '<svg viewBox="0 0 24 24" role="img" focusable="false">'
        +   '<rect x="4" y="6" width="16" height="10" rx="1.8"></rect>'
        +   '<path d="M9 19h6"></path>'
        +   '<path d="M12 16v3"></path>'
        + '</svg>';
      return wrap;
    }
    var headerHost = document.querySelector('.head');
    if (headerHost && !document.getElementById('globalHeaderComputerBadge')) {
      var headerBadge = createComputerBadge('computer-badge-header');
      headerBadge.id = 'globalHeaderComputerBadge';
      headerHost.appendChild(headerBadge);
    }
    var footerHost = document.querySelector('.footer-brand');
    if (footerHost && !document.getElementById('globalFooterComputerBadge')) {
      var footerBadge = createComputerBadge('computer-badge-footer');
      footerBadge.id = 'globalFooterComputerBadge';
      footerHost.appendChild(footerBadge);
    }
    var navButtons = Array.prototype.slice.call(document.querySelectorAll('.head .m-btn[href], .head .admin-btn[href]'));
    navButtons.forEach(function (btn) {
      try {
        var href = btn.getAttribute('href') || '';
        var isActive = href === path;
        if (isActive) btn.classList.add('active');
        else btn.classList.remove('active');
      } catch (_) {}
    });
    var adminLinks = document.querySelector('.head .admin-menu .links');
    if (adminLinks && !adminLinks.querySelector('a[href="/urunler-ui"]')) {
      var productsLink = document.createElement('a');
      productsLink.href = '/urunler-ui';
      productsLink.textContent = 'Ürünler';
      adminLinks.appendChild(productsLink);
    }
    Array.prototype.slice.call(
      document.querySelectorAll('.head .head-left .m-btn[href="/muhasebe-finans-ui"], .head .module-nav .m-btn[href="/muhasebe-finans-ui"]')
    ).forEach(function(el){
      if (el && el.parentNode) el.parentNode.removeChild(el);
    });
    var headRightForFinance = document.querySelector('.head .head-right');
    var adminMenuForFinance = document.querySelector('.head .head-right .admin-menu');
    if (headRightForFinance && !document.getElementById('globalFinanceRightLink')) {
      var financeLink = document.createElement('a');
      financeLink.id = 'globalFinanceRightLink';
      financeLink.className = 'admin-btn';
      financeLink.href = '/muhasebe-finans-ui';
      financeLink.textContent = 'Muhasebe - Finans Modülü';
      if (adminMenuForFinance && adminMenuForFinance.parentNode === headRightForFinance) {
        headRightForFinance.insertBefore(financeLink, adminMenuForFinance);
      } else {
        headRightForFinance.appendChild(financeLink);
      }
    }
    function applyInterpreterVisibility(role) {
      var r = String(role || '').trim().toLowerCase();
      var allowed = {
        interpreter: 1,
        supertranslator: 1,
        superadmin: 1,
        tenant_admin: 1,
        tenant_manager: 1,
        tenant_operator: 1,
        admin: 1,
        manager: 1,
        operator: 1,
        supplier_admin: 1
      };
      var show = !!allowed[r];
      var navs = Array.prototype.slice.call(document.querySelectorAll('.head .m-btn[href="/tercuman-ui"], #navInterpreterToplanti, #navInterpreterCeviri'));
      navs.forEach(function(el){
        if (!el) return;
        if (show) el.style.setProperty('display', 'inline-flex', 'important');
        else el.style.setProperty('display', 'none', 'important');
      });
      var linkInterpreterPanel = document.getElementById('linkInterpreterPanel');
      if (linkInterpreterPanel) {
        if (show) linkInterpreterPanel.style.removeProperty('display');
        else linkInterpreterPanel.style.setProperty('display', 'none', 'important');
      }
      var cardInterpreterBtn = document.getElementById('cardInterpreterBtn');
      if (cardInterpreterBtn) {
        var card = cardInterpreterBtn.closest('.card');
        if (card) {
          if (show) card.style.removeProperty('display');
          else card.style.setProperty('display', 'none', 'important');
        }
      }
    }
    applyInterpreterVisibility('');

    var tokenBadgeHost = document.querySelector('.head .head-right');
    if (tokenBadgeHost && !document.getElementById('globalTokenBadge')) {
      var tokenBadge = document.createElement('span');
      tokenBadge.id = 'globalTokenBadge';
      tokenBadge.className = 'token-badge-gold';
      tokenBadge.style.display = 'none';
      tokenBadge.innerHTML = '<span class="tb-crea">Crea</span><span class="tb-token">Token</span>: -';
      tokenBadgeHost.appendChild(tokenBadge);
      (async function(){
        try {
          var tkn = localStorage.getItem('access_token') || '';
          if (!tkn) return;
          var meRes2 = await fetch('/auth/me', { headers: { Authorization: 'Bearer ' + tkn } });
          var me2 = await meRes2.json().catch(function(){ return {}; });
          if (!meRes2.ok) return;
          var role2 = String(me2.role || '').toLowerCase();
          applyInterpreterVisibility(role2);
          var tokenRoles = { tenant_admin:1, tenant_manager:1, tenant_operator:1, supplier_admin:1, operator:1, manager:1, admin:1 };
          if (!tokenRoles[role2]) return;
          var rem = (me2 && me2.token_remaining != null) ? me2.token_remaining : '-';
          tokenBadge.innerHTML = '<span class="tb-crea">Crea</span><span class="tb-token">Token</span>: ' + rem;
          tokenBadge.style.display = 'inline-flex';
        } catch (_) {}
      })();
    }

    var orderedLinks = [
      '/modules-ui',
      '/kayit-ui',
      '/konaklama-ui',
      '/toplanti-ui',
      '/transfer-ui',
      '/muhasebe-finans-ui',
      '/duyurular-ui',
      '/yonetici-ui'
    ];
    orderedLinks.forEach(function (href, idx) {
      var btn = document.querySelector('.head .m-btn[href="' + href + '"], .head .admin-btn[href="' + href + '"]');
      if (!btn) return;
      var key = String(idx + 1);
      btn.setAttribute('accesskey', key);
      btn.setAttribute('title', 'Kısayol: Alt+' + key);
    });

    var uiI18n = {
      tr: {
        refresh_list: 'Listeyi Yenile',
        print: 'Yazdır',
        import: 'İçeri Aktar',
        export: 'Dışarı Aktar',
        upload: 'Yükle',
        close: 'Kapat',
        edit: 'Düzenle',
        status: 'Durum',
        file: 'Dosya',
        upload_id: 'Yükleme ID',
        passenger: 'Yolcu',
        gender: 'Cinsiyet',
        issue_date: 'Düzenlenme Tarihi',
        flight_type: 'Uçuş Şekli',
        flight_code: 'Uçuş Kodu',
        route: 'Rota',
        dep_dt: 'Kalkış Tarihi-Saati',
        arr_dt: 'İniş Tarihi-Saati',
        pickup_time: 'Karşılama Saati',
        transfer_point: 'Transfer Noktası',
        vehicle_code: 'Araç Kodu',
        note: 'Not',
        transfer_list: 'Transfer Listesi',
        transfer_list_refresh: 'Transfer Listesini Yenile',
        select_and_transfer: 'Seçilenleri Aktar',
        transfer_all: 'İçeri Aktar (Tümü)',
        zip_export: 'ZIP Dışarı Aktar',
        upload_complete: 'Yükleme Tamamlandı',
        operations: 'İşlemler',
        file_upload: 'Dosya Yükleme',
        filter_ph: 'filtre'
      },
      en: {
        refresh_list: 'Refresh List',
        print: 'Print',
        import: 'Import',
        export: 'Export',
        upload: 'Upload',
        close: 'Close',
        edit: 'Edit',
        status: 'Status',
        file: 'File',
        upload_id: 'Upload ID',
        passenger: 'Passenger',
        gender: 'Gender',
        issue_date: 'Issue Date',
        flight_type: 'Flight Type',
        flight_code: 'Flight Code',
        route: 'Route',
        dep_dt: 'Departure Datetime',
        arr_dt: 'Arrival Datetime',
        pickup_time: 'Pick-up Time',
        transfer_point: 'Transfer Point',
        vehicle_code: 'Vehicle Code',
        note: 'Note',
        transfer_list: 'Transfer List',
        transfer_list_refresh: 'Refresh Transfer List',
        select_and_transfer: 'Transfer Selected',
        transfer_all: 'Import (All)',
        zip_export: 'ZIP Export',
        upload_complete: 'Upload Completed',
        operations: 'Operations',
        file_upload: 'File Upload',
        filter_ph: 'filter'
      },
      es: {
        refresh_list: 'Actualizar Lista',
        print: 'Imprimir',
        import: 'Importar',
        export: 'Exportar',
        upload: 'Subir',
        close: 'Cerrar',
        edit: 'Editar',
        status: 'Estado',
        file: 'Archivo',
        upload_id: 'ID de Carga',
        passenger: 'Pasajero',
        gender: 'Género',
        issue_date: 'Fecha de Emisión',
        flight_type: 'Tipo de Vuelo',
        flight_code: 'Código de Vuelo',
        route: 'Ruta',
        dep_dt: 'Fecha-Hora Salida',
        arr_dt: 'Fecha-Hora Llegada',
        pickup_time: 'Hora de Recogida',
        transfer_point: 'Punto de Traslado',
        vehicle_code: 'Código del Vehículo',
        note: 'Nota',
        transfer_list: 'Lista de Traslados',
        transfer_list_refresh: 'Actualizar Lista de Traslados',
        select_and_transfer: 'Transferir Seleccionados',
        transfer_all: 'Importar (Todo)',
        zip_export: 'Exportar ZIP',
        upload_complete: 'Carga Completada',
        operations: 'Operaciones',
        file_upload: 'Carga de Archivos',
        filter_ph: 'filtro'
      },
      it: {
        refresh_list: 'Aggiorna Elenco',
        print: 'Stampa',
        import: 'Importa',
        export: 'Esporta',
        upload: 'Carica',
        close: 'Chiudi',
        edit: 'Modifica',
        status: 'Stato',
        file: 'File',
        upload_id: 'ID Caricamento',
        passenger: 'Passeggero',
        gender: 'Genere',
        issue_date: 'Data Emissione',
        flight_type: 'Tipo Volo',
        flight_code: 'Codice Volo',
        route: 'Rotta',
        dep_dt: 'Data-Ora Partenza',
        arr_dt: 'Data-Ora Arrivo',
        pickup_time: 'Orario Pick-up',
        transfer_point: 'Punto Trasferimento',
        vehicle_code: 'Codice Veicolo',
        note: 'Nota',
        transfer_list: 'Lista Trasferimenti',
        transfer_list_refresh: 'Aggiorna Lista Trasferimenti',
        select_and_transfer: 'Trasferisci Selezionati',
        transfer_all: 'Importa (Tutti)',
        zip_export: 'Esporta ZIP',
        upload_complete: 'Caricamento Completato',
        operations: 'Operazioni',
        file_upload: 'Caricamento File',
        filter_ph: 'filtro'
      },
      ru: {
        refresh_list: '???????? ??????',
        print: '??????',
        import: '??????',
        export: '???????',
        upload: '?????????',
        close: '???????',
        edit: '????????',
        status: '??????',
        file: '????',
        upload_id: 'ID ????????',
        passenger: '????????',
        gender: '???',
        issue_date: '???? ??????????',
        flight_type: '??? ?????',
        flight_code: '??? ?????',
        route: '???????',
        dep_dt: '????-????? ??????',
        arr_dt: '????-????? ???????',
        pickup_time: '????? ???????',
        transfer_point: '????? ?????????',
        vehicle_code: '??? ??',
        note: '???????',
        transfer_list: '?????? ??????????',
        transfer_list_refresh: '???????? ?????? ??????????',
        select_and_transfer: '????????? ?????????',
        transfer_all: '?????? (???)',
        zip_export: '??????? ZIP',
        upload_complete: '???????? ?????????',
        operations: '????????',
        file_upload: '???????? ??????',
        filter_ph: '??????'
      },
      ar: {
        refresh_list: '????? ???????',
        print: '?????',
        import: '???????',
        export: '?????',
        upload: '???',
        close: '?????',
        edit: '?????',
        status: '??????',
        file: '???',
        upload_id: '????? ?????',
        passenger: '???????',
        gender: '?????',
        issue_date: '????? ???????',
        flight_type: '??? ??????',
        flight_code: '??? ??????',
        route: '??????',
        dep_dt: '?????-??? ???????',
        arr_dt: '?????-??? ??????',
        pickup_time: '??? ?????????',
        transfer_point: '???? ???????',
        vehicle_code: '??? ???????',
        note: '??????',
        transfer_list: '????? ?????',
        transfer_list_refresh: '????? ????? ?????',
        select_and_transfer: '??? ??????',
        transfer_all: '??????? (????)',
        zip_export: '????? ZIP',
        upload_complete: '????? ?????',
        operations: '????????',
        file_upload: '??? ???????',
        filter_ph: '?????'
      }
    };

    function normalizePhrase(s) {
      return String(s || '').trim().replace(/\\s+/g, ' ').replace(/:$/, '').toLocaleLowerCase('tr-TR');
    }
    var uiReverse = {};
    Object.keys(uiI18n).forEach(function(lang){
      uiReverse[lang] = {};
      Object.keys(uiI18n[lang]).forEach(function(k){
        uiReverse[lang][normalizePhrase(uiI18n[lang][k])] = k;
      });
    });
    function detectI18nKey(text) {
      var n = normalizePhrase(text);
      if (!n) return '';
      var langs = Object.keys(uiReverse);
      for (var i = 0; i < langs.length; i += 1) {
        var m = uiReverse[langs[i]];
        if (m && m[n]) return m[n];
      }
      return '';
    }
    function keepCase(source, target) {
      var src = String(source || '');
      var tgt = String(target || '');
      if (!src) return tgt;
      if (src === src.toUpperCase()) return tgt.toUpperCase();
      return tgt;
    }
    function translateStaticUi() {
      var lang = (localStorage.getItem('ui_lang') || document.documentElement.lang || 'tr').toLowerCase();
      var pack = uiI18n[lang] || uiI18n.en || uiI18n.tr;
      var selectors = [
        'th', 'button', 'label', '.btn', '.m-btn', '.admin-btn',
        '.section-title', '.title', 'h1', 'h2', 'h3', 'h4',
        '.popup .title', '.muted', '.project-switch-btn'
      ].join(',');
      Array.prototype.slice.call(document.querySelectorAll(selectors)).forEach(function(el){
        if (!el) return;
        var raw = (el.textContent || '').trim();
        if (!raw) return;
        var key = el.getAttribute('data-i18n-auto-key') || detectI18nKey(raw);
        if (!key || !pack[key]) return;
        el.setAttribute('data-i18n-auto-key', key);
        var nextText = keepCase(raw, pack[key]);
        if (nextText !== raw) el.textContent = nextText;
      });
      Array.prototype.slice.call(document.querySelectorAll('input[placeholder], textarea[placeholder]')).forEach(function(el){
        var ph = el.getAttribute('placeholder') || '';
        if (!ph) return;
        var key = el.getAttribute('data-i18n-auto-ph-key') || detectI18nKey(ph);
        if (!key || !pack[key]) return;
        el.setAttribute('data-i18n-auto-ph-key', key);
        if (pack[key] !== ph) el.setAttribute('placeholder', pack[key]);
      });
      document.documentElement.lang = lang;
      document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
    }
    translateStaticUi();
    window.addEventListener('storage', function(e){
      if (e && e.key === 'ui_lang') translateStaticUi();
    });
    var lsGlobal = document.getElementById('langSelect');
    if (lsGlobal) {
      lsGlobal.addEventListener('change', function(){
        localStorage.setItem('ui_lang', lsGlobal.value || 'tr');
        translateStaticUi();
      });
    }
    var i18nTick = null;
    var i18nObserver = new MutationObserver(function(){
      if (i18nTick) return;
      i18nTick = setTimeout(function(){
        i18nTick = null;
        translateStaticUi();
      }, 60);
    });
    if (document.body) {
      i18nObserver.observe(document.body, { childList: true, subtree: true });
    }

    function asComparable(value) {
      var txt = (value == null ? '' : String(value)).trim();
      if (!txt) return { type: 'text', v: '' };
      var normalized = txt.replace(/\\s+/g, ' ');
      var trDate = normalized.match(/^(\\d{1,2})[./-](\\d{1,2})[./-](\\d{2,4})(?:\\s+(\\d{1,2}):(\\d{2}))?$/);
      if (trDate) {
        var dd = parseInt(trDate[1], 10);
        var mm = parseInt(trDate[2], 10) - 1;
        var yy = parseInt(trDate[3], 10);
        if (yy < 100) yy += 2000;
        var hh = trDate[4] ? parseInt(trDate[4], 10) : 0;
        var mi = trDate[5] ? parseInt(trDate[5], 10) : 0;
        var dt = new Date(yy, mm, dd, hh, mi, 0, 0).getTime();
        if (!Number.isNaN(dt)) return { type: 'num', v: dt };
      }
      var isoDate = Date.parse(normalized);
      if (!Number.isNaN(isoDate) && /\\d/.test(normalized)) return { type: 'num', v: isoDate };
      var num = Number(normalized.replace(/\\./g, '').replace(',', '.'));
      if (!Number.isNaN(num) && /[\\d]/.test(normalized)) return { type: 'num', v: num };
      return { type: 'text', v: normalized.toLocaleUpperCase('tr-TR') };
    }

    function enableAutoSort(table) {
      if (!table || table.dataset.noSort === '1') return;
      var head = table.tHead;
      var body = table.tBodies && table.tBodies[0];
      if (!head || !body || !body.rows) return;
      if (table.querySelector('thead th[data-sort], thead th[data-tsort]')) return; // Manuel sıralama var.

      var firstHeadRow = head.rows && head.rows[0];
      if (!firstHeadRow) return;
      table.setAttribute('data-auto-sort', '1');
      var headers = Array.prototype.slice.call(firstHeadRow.cells || []);
      headers.forEach(function (th, colIdx) {
        if (!th) return;
        if (th.classList.contains('no-sort')) return;
        if (th.querySelector('input,select,button,a')) return;
        th.addEventListener('click', function () {
          var prevCol = parseInt(table.dataset.sortCol || '-1', 10);
          var prevDir = table.dataset.sortDir || 'asc';
          var dir = (prevCol === colIdx && prevDir === 'asc') ? 'desc' : 'asc';
          table.dataset.sortCol = String(colIdx);
          table.dataset.sortDir = dir;
          headers.forEach(function (h) { h.classList.remove('sort-asc', 'sort-desc'); });
          th.classList.add(dir === 'asc' ? 'sort-asc' : 'sort-desc');

          var rows = Array.prototype.slice.call(body.rows || []);
          rows.sort(function (a, b) {
            var aTxt = (a.cells[colIdx] ? a.cells[colIdx].innerText : '').trim();
            var bTxt = (b.cells[colIdx] ? b.cells[colIdx].innerText : '').trim();
            var av = asComparable(aTxt);
            var bv = asComparable(bTxt);
            var cmp = 0;
            if (av.type === 'num' && bv.type === 'num') {
              cmp = av.v - bv.v;
            } else {
              cmp = String(av.v).localeCompare(String(bv.v), 'tr', { sensitivity: 'base' });
            }
            return dir === 'asc' ? cmp : -cmp;
          });
          rows.forEach(function (r) { body.appendChild(r); });
        });
      });
    }

    Array.prototype.slice.call(document.querySelectorAll('table')).forEach(enableAutoSort);

    if (!document.getElementById('globalProjectSwitchMenu')) {
      var badge = document.getElementById('activeProjectBadge');
      var host = (badge && badge.parentElement) || null;
      if (badge && host) {
        var qs = '?return=' + encodeURIComponent(path || '/modules-ui');
        host.classList.add('project-switch-wrap');
        var menu = document.createElement('div');
        menu.id = 'globalProjectSwitchMenu';
        menu.className = 'project-switch-menu';
        menu.innerHTML = '<div style="color:#9FD8FF;font-size:11px;padding:4px 6px;">Aktif projeler yükleniyor...</div>';
        host.appendChild(menu);
        badge.style.cursor = 'pointer';
        if (!badge.getAttribute('title')) badge.setAttribute('title', 'Proje Değiştir');

        var token = localStorage.getItem('access_token') || '';
        var authHeaders = token ? { 'Authorization': 'Bearer ' + token } : {};
        var closeTimer = null;
        var openMenu = function(){
          if (closeTimer) { clearTimeout(closeTimer); closeTimer = null; }
          host.classList.add('open');
        };
        var closeMenu = function(){
          if (closeTimer) { clearTimeout(closeTimer); }
          closeTimer = setTimeout(function(){ host.classList.remove('open'); }, 220);
        };
        var closeMenuNow = function(){
          if (closeTimer) { clearTimeout(closeTimer); closeTimer = null; }
          host.classList.remove('open');
        };
        host.addEventListener('mouseenter', openMenu);
        host.addEventListener('mouseleave', closeMenu);
        menu.addEventListener('mouseenter', openMenu);
        menu.addEventListener('mouseleave', closeMenu);
        badge.addEventListener('click', function(e){
          e.preventDefault();
          if (host.classList.contains('open')) closeMenuNow();
          else openMenu();
        });
        document.addEventListener('click', function(e){
          if (!host.contains(e.target)) closeMenuNow();
        });

        var setActiveProject = async function(projectId){
          if (!token) return;
          try {
            var res = await fetch('/auth/active-project', {
              method: 'PUT',
              headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders),
              body: JSON.stringify({ project_id: parseInt(projectId, 10) })
            });
            var data = await res.json().catch(function(){ return {}; });
            if (!res.ok) return;
            window.location.reload();
          } catch (_) {}
        };

        var renderActiveProjects = function(list, activeId){
          if (!Array.isArray(list) || !list.length) {
            menu.innerHTML = '<div style="color:#9FD8FF;font-size:11px;padding:4px 6px;">Aktif proje bulunamadı</div>';
            return;
          }
          menu.innerHTML = '';
          var sorted = list.slice().sort(function(a,b){
            return String(a.operation_code || '').localeCompare(String(b.operation_code || ''));
          });
          sorted.forEach(function(p){
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'project-switch-item';
            var mark = String(p.id) === String(activeId) ? ' *' : '';
            btn.textContent = (p.operation_code || '-') + ' | ' + (p.name || '-') + mark;
            btn.addEventListener('click', function(){ setActiveProject(p.id); });
            menu.appendChild(btn);
          });
          var go = document.createElement('a');
          go.href = '/project-select-ui' + qs;
          go.className = 'project-switch-item';
          go.style.textDecoration = 'none';
          go.style.borderTop = '1px solid rgba(159,216,255,0.25)';
          go.style.marginTop = '6px';
          go.style.paddingTop = '8px';
          go.textContent = 'Proje Seçim Sayfasına Git';
          menu.appendChild(go);
        };

        (async function(){
          if (!token) {
            menu.innerHTML = '<div style="color:#9FD8FF;font-size:11px;padding:4px 6px;">Oturum gerekli</div>';
            return;
          }
          try {
            var meRes = await fetch('/auth/me', { headers: authHeaders });
            var me = await meRes.json().catch(function(){ return {}; });
            var pRes = await fetch('/projects', { headers: authHeaders });
            var projects = await pRes.json().catch(function(){ return []; });
            if (!pRes.ok) {
              menu.innerHTML = '<div style="color:#9FD8FF;font-size:11px;padding:4px 6px;">Projeler alınamadı</div>';
              return;
            }
            var activeOnly = (Array.isArray(projects) ? projects : []).filter(function(x){ return !!x.is_active; });
            renderActiveProjects(activeOnly, me && me.active_project_id);
          } catch (_) {
            menu.innerHTML = '<div style="color:#9FD8FF;font-size:11px;padding:4px 6px;">Projeler alınamadı</div>';
          }
        })();
      }
    }

    document.addEventListener('keydown', function(e){
      if (e.key !== 'Escape') return;
      var openModals = document.querySelectorAll('.modal.show');
      openModals.forEach(function(m){ m.classList.remove('show'); });
      var projectWrap = document.querySelector('.project-switch-wrap.open');
      if (projectWrap) projectWrap.classList.remove('open');
      var adminMenu = document.querySelector('.admin-menu.open');
      if (adminMenu) adminMenu.classList.remove('open');
    });
  });
</script>
"""


def _inject_standard_header_style(html_text: str) -> str:
    if "</head>" not in html_text:
        return html_text
    chunks = []
    if "id=\"creatro-standard-header\"" not in html_text:
        chunks.append(STANDARD_HEADER_CSS)
    if "id=\"creatro-standard-header-js\"" not in html_text:
        chunks.append(STANDARD_HEADER_JS)
    if not chunks:
        return html_text
    return html_text.replace("</head>", "\n".join(chunks) + "\n</head>", 1)


@app.middleware("http")
async def apply_standard_header_style(request: Request, call_next):
    response = await call_next(request)
    content_type = (response.headers.get("content-type") or "").lower()
    if "text/html" not in content_type:
        return response

    body = b""
    async for chunk in response.body_iterator:
        body += chunk

    try:
        html_text = body.decode("utf-8")
    except UnicodeDecodeError:
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    patched = _inject_standard_header_style(html_text)
    if patched == html_text:
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    headers = dict(response.headers)
    headers.pop("content-length", None)
    return Response(
        content=patched.encode("utf-8"),
        status_code=response.status_code,
        headers=headers,
        media_type=response.media_type,
    )


@app.middleware("http")
async def block_writes_for_passive_project(request: Request, call_next):
    method = (request.method or "").upper()
    path = request.url.path or ""
    if method not in WRITE_METHODS:
        return await call_next(request)
    if path in PASSIVE_WRITE_ALLOW_PATHS:
        return await call_next(request)
    if path.startswith("/auth/"):
        return await call_next(request)

    token = _extract_bearer_token(request.headers.get("authorization"))
    if not token:
        return await call_next(request)

    db = SessionLocal()
    try:
        user = _find_user_by_token(db, token, touch_session=False)
        if not user:
            return await call_next(request)
        active_project_id = int(user.active_project_id or 0)
        if not active_project_id:
            return await call_next(request)
        project = db.query(Project).filter(Project.id == active_project_id).first()
        if project and not bool(project.is_active):
            return Response(
                content=json.dumps(
                    {
                        "detail": "Passive project: data changes are disabled. Please switch to an active project."
                    }
                ),
                status_code=403,
                media_type="application/json",
            )
    finally:
        db.close()
    return await call_next(request)


@app.middleware("http")
async def enforce_module_rbac_abac(request: Request, call_next):
    if (request.method or "").upper() == "OPTIONS":
        return await call_next(request)

    body_payload = await _read_json_body_for_audit(request)
    module_key = _module_key_for_request(request, body_payload if isinstance(body_payload, dict) else None)
    if not module_key:
        return await call_next(request)

    token = _extract_bearer_token(request.headers.get("authorization"))
    if not token:
        return await call_next(request)

    db = SessionLocal()
    try:
        user = _find_user_by_token(db, token, touch_session=False)
        if not user:
            return await call_next(request)
        try:
            _require_module_access(db, user, module_key)
        except HTTPException as exc:
            return Response(
                content=json.dumps({"detail": exc.detail}),
                status_code=int(exc.status_code),
                media_type="application/json",
            )
    finally:
        db.close()
    return await call_next(request)


@app.middleware("http")
async def audit_request_middleware(request: Request, call_next):
    path = request.url.path or ""
    should_skip = any(path.startswith(prefix) for prefix in AUDIT_SKIP_PREFIXES)
    body_payload = None if should_skip else await _read_json_body_for_audit(request)

    response = None
    status_code = 500
    error_text = None
    try:
        response = await call_next(request)
        status_code = int(response.status_code)
        return response
    except Exception as exc:
        error_text = str(exc)[:500]
        raise
    finally:
        if not should_skip:
            db = SessionLocal()
            try:
                token = _extract_bearer_token(request.headers.get("authorization"))
                user = _find_user_by_token(db, token, touch_session=False)

                actor_username = user.username if user else None
                if actor_username is None and isinstance(body_payload, dict) and "/auth/login" in path:
                    actor_username = str(body_payload.get("username") or "").strip() or None

                project_id = _resolve_request_project_id(request, body_payload, user)
                related_transfer_id = _resolve_related_transfer_id(request, body_payload)
                ip_address = request.headers.get("x-forwarded-for") or (request.client.host if request.client else None)
                query_payload = _mask_sensitive(dict(request.query_params)) if request.query_params else {}
                action = _classify_action(request.method, path)
                response_payload = _read_json_response_for_audit(response)

                db.add(
                    OpsEvent(
                        tenant_id=str(user.tenant_id) if user and user.tenant_id is not None else None,
                        project_id=project_id,
                        actor_user_id=user.id if user else None,
                        actor_username=actor_username,
                        event_id=f"audit-{uuid.uuid4().hex[:12]}",
                        event_type=EVENT_AUDIT_ACTION,
                        action=action,
                        request_method=(request.method or "").upper()[:10],
                        request_path=path[:255],
                        status_code=status_code,
                        ip_address=(ip_address or "")[:64] or None,
                        user_agent=(request.headers.get("user-agent") or "")[:255] or None,
                        related_transfer_id=related_transfer_id,
                        payload={
                            "query": query_payload,
                            "path_params": request.path_params or {},
                            "request_body": body_payload,
                            "response_body": response_payload,
                            "change_kind": action if action in {"create", "update", "delete"} else None,
                            "error": error_text,
                        },
                    )
                )
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _hash_password(password: str, salt: str | None = None) -> str:
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_value.encode("utf-8"),
        120_000,
    ).hex()
    return f"{salt_value}${digest}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, expected = password_hash.split("$", 1)
    except ValueError:
        return False
    current = _hash_password(password, salt=salt).split("$", 1)[1]
    return secrets.compare_digest(current, expected)


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


def _mask_sensitive(value):
    if isinstance(value, dict):
        masked: dict = {}
        for key, item in value.items():
            key_lower = str(key).lower()
            if key_lower in AUDIT_SENSITIVE_KEYS:
                masked[key] = "***"
            else:
                masked[key] = _mask_sensitive(item)
        return masked
    if isinstance(value, list):
        return [_mask_sensitive(item) for item in value]
    return value


def _safe_int(value) -> int | None:
    if value is None:
        return None
    txt = str(value).strip()
    if not txt:
        return None
    try:
        return int(txt)
    except Exception:
        return None


def _resolve_request_project_id(request: Request, body_payload, user: User | None) -> int | None:
    query_project = _safe_int(request.query_params.get("project_id"))
    if query_project is not None:
        return query_project
    if isinstance(body_payload, dict):
        body_project = _safe_int(body_payload.get("project_id"))
        if body_project is not None:
            return body_project
    if user is not None:
        return _safe_int(user.active_project_id)
    return None


def _resolve_related_transfer_id(request: Request, body_payload) -> int | None:
    for key in ("transfer_id", "related_transfer_id"):
        if key in request.path_params:
            value = _safe_int(request.path_params.get(key))
            if value is not None:
                return value
        value = _safe_int(request.query_params.get(key))
        if value is not None:
            return value
    if isinstance(body_payload, dict):
        for key in ("transfer_id", "related_transfer_id"):
            value = _safe_int(body_payload.get(key))
            if value is not None:
                return value
    return None


def _module_key_for_request(request: Request, body_payload: dict | None = None) -> str | None:
    path = request.url.path or ""
    if any(path.startswith(pfx) for pfx in MODULE_ENFORCEMENT_EXCLUDE_PREFIXES):
        return None

    if path == "/module-data":
        module_name = request.query_params.get("module_name")
        if not module_name and isinstance(body_payload, dict):
            module_name = body_payload.get("module_name")
        if module_name:
            try:
                return _normalize_module_name(module_name)
            except HTTPException:
                return None
        return None

    for route_prefix, module_key in MODULE_ENFORCEMENT_ROUTE_MAP:
        if path == route_prefix or path.startswith(route_prefix + "/"):
            return module_key
    return None


def _classify_action(method: str, path: str) -> str:
    verb = (method or "").upper()
    if verb == "POST":
        if "/auth/login" in path:
            return "auth_login"
        return "create"
    if verb in {"PUT", "PATCH"}:
        return "update"
    if verb == "DELETE":
        return "delete"
    if verb == "GET":
        return "read"
    return verb.lower() or "unknown"


async def _read_json_body_for_audit(request: Request):
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        return None
    content_length = _safe_int(request.headers.get("content-length")) or 0
    if content_length > 200_000:
        return {"_truncated": True, "reason": "payload_too_large", "size": content_length}
    try:
        raw = await request.body()
    except Exception:
        return None
    if not raw:
        return None
    if len(raw) > 200_000:
        return {"_truncated": True, "reason": "payload_too_large", "size": len(raw)}
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        return {"_raw": raw[:500].decode("utf-8", errors="ignore")}
    return _mask_sensitive(parsed)


def _read_json_response_for_audit(response):
    if response is None:
        return None
    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        return None
    raw = getattr(response, "body", None)
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        return None
    if len(raw) > 200_000:
        return {"_truncated": True, "reason": "response_too_large", "size": len(raw)}
    try:
        parsed = json.loads(bytes(raw).decode("utf-8"))
    except Exception:
        return None
    return _mask_sensitive(parsed)


def _find_user_by_token(db: Session, token: str | None, touch_session: bool) -> User | None:
    if not token:
        return None
    now = datetime.now(timezone.utc)
    session = (
        db.query(UserSession)
        .filter(UserSession.token == token, UserSession.expires_at > now)
        .first()
    )
    if not session:
        return None
    if touch_session:
        session.expires_at = now + timedelta(minutes=max(1, SESSION_IDLE_MINUTES))
        db.commit()
    user = db.query(User).filter(User.id == session.user_id, User.is_active.is_(True)).first()
    return user


def require_auth(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    user = _find_user_by_token(db, token, touch_session=True)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user


def require_admin_db_auth(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    admin_db_session: str | None = Cookie(default=None),
) -> User:
    token = _extract_bearer_token(authorization) or (str(admin_db_session or "").strip() or None)
    if not token:
        raise HTTPException(status_code=401, detail="Admin DB login required")
    user = _find_user_by_token(db, token, touch_session=True)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired admin DB session")
    if normalize_role(user.role) != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin required")
    return user


def require_company_admin(current_user: User = Depends(require_auth)) -> User:
    if role_level(current_user.role) < role_level("tenant_manager"):
        raise HTTPException(status_code=403, detail="Admin or manager role required")
    return current_user


def is_superadmin(user: User) -> bool:
    return (user.role or "").lower() == "superadmin"


def is_supertranslator(user: User) -> bool:
    return normalize_role(user.role) == "supertranslator"


def normalize_role(role: str | None) -> str:
    raw = str(role or "").strip().lower()
    if not raw:
        return "tenant_operator"
    return ROLE_ALIASES.get(raw, raw)


def role_level(role: str | None) -> int:
    return ROLE_LEVEL.get(normalize_role(role), 0)


def can_access_interpreter_module(user: User) -> bool:
    role = normalize_role(user.role)
    return role in {
        "interpreter",
        "tenant_manager",
        "tenant_admin",
        "supertranslator",
        "superadmin_staff",
        "superadmin",
    }


def can_assign_role(current_user: User, target_role: str) -> bool:
    if is_superadmin(current_user):
        return True
    return role_level(target_role) <= role_level(current_user.role)


def can_manage_user(current_user: User, target_user: User) -> bool:
    if is_superadmin(current_user):
        return True
    if target_user.tenant_id != current_user.tenant_id:
        return False
    return role_level(target_user.role) < role_level(current_user.role)


def _is_management_project(project: Project | None) -> bool:
    if not project:
        return False
    return str(project.operation_code or "").strip().upper() == MANAGEMENT_PROJECT_CODE


def _resolve_active_project(db: Session, user: User) -> Project | None:
    if not user.active_project_id:
        return None
    return db.query(Project).filter(Project.id == user.active_project_id).first()


def _can_user_access_project(db: Session, user: User, project: Project) -> bool:
    if is_superadmin(user):
        return True
    if not project or not user.tenant_id or int(project.tenant_id or 0) != int(user.tenant_id):
        return False
    deny = (
        db.query(UserProjectAccess)
        .filter(
            UserProjectAccess.user_id == user.id,
            UserProjectAccess.project_id == project.id,
            UserProjectAccess.is_denied.is_(True),
        )
        .first()
    )
    if deny:
        return False
    allow = (
        db.query(UserProjectAccess)
        .filter(
            UserProjectAccess.user_id == user.id,
            UserProjectAccess.project_id == project.id,
            UserProjectAccess.is_denied.is_(False),
            UserProjectAccess.can_view.is_(True),
        )
        .first()
    )
    if allow:
        return True
    return True


def _ensure_project_modules_defaults(db: Session, project_id: int) -> None:
    for key in DEFAULT_MODULE_KEYS:
        db.execute(
            text(
                "INSERT INTO project_modules (project_id, module_key, enabled) "
                "VALUES (:project_id, :module_key, true) "
                "ON CONFLICT (project_id, module_key) DO NOTHING"
            ),
            {"project_id": int(project_id), "module_key": str(key)},
        )


def _ensure_management_project_for_tenant(db: Session, tenant_id: int) -> Project:
    project = (
        db.query(Project)
        .filter(
            Project.tenant_id == tenant_id,
            Project.operation_code == MANAGEMENT_PROJECT_CODE,
        )
        .first()
    )
    if not project:
        project = Project(
            tenant_id=tenant_id,
            name="Yönetim Projesi",
            city="Sistem",
            operation_code=MANAGEMENT_PROJECT_CODE,
            token_limit=None,
            token_used=0,
            is_active=True,
        )
        db.add(project)
        db.flush()
    _ensure_project_modules_defaults(db, int(project.id))
    return project


def _is_module_enabled_for_project(db: Session, project_id: int, module_key: str) -> bool:
    row = (
        db.query(ProjectModule)
        .filter(
            ProjectModule.project_id == project_id,
            ProjectModule.module_key == str(module_key or "").strip().lower(),
        )
        .first()
    )
    if not row:
        return True
    return bool(row.enabled)


def _role_default_module_set(role: str | None) -> set[str]:
    r = normalize_role(role)
    if r == "superadmin":
        return set(MODULE_DISPLAY_ORDER)
    if r in {"superadmin_staff", "tenant_admin", "tenant_manager"}:
        return set(MODULE_DISPLAY_ORDER)
    if r == "supertranslator":
        return {"toplanti", "tercuman"}
    if r == "interpreter":
        return {"toplanti", "tercuman"}
    if r == "participant":
        return {"toplanti", "duyurular"}
    if r in {"driver", "greeter", "supplier_admin"}:
        return {"transfer"}
    return {"transfer", "kayit", "konaklama", "toplanti", "muhasebe_finans", "duyurular"}


def _is_user_module_allowed(db: Session, user: User, project_id: int, module_key: str) -> bool:
    mk = str(module_key or "").strip().lower()
    if mk == "yonetim":
        return normalize_role(user.role) in {"superadmin", "superadmin_staff", "tenant_admin"}
    role_key = normalize_role(user.role)
    base_allowed = _role_default_module_set(role_key)
    # Strict ceiling for scoped roles: DB override cannot expand beyond role base set.
    if role_key in {"driver", "greeter", "supplier_admin", "participant", "interpreter", "supertranslator"}:
        return mk in base_allowed
    row = (
        db.query(UserModuleAccess)
        .filter(
            UserModuleAccess.user_id == int(user.id),
            UserModuleAccess.project_id == int(project_id),
            UserModuleAccess.module_key == mk,
        )
        .first()
    )
    if row is not None:
        return bool(row.allowed)
    return mk in base_allowed


def _visible_modules_for_user(db: Session, user: User) -> list[str]:
    if is_superadmin(user) and not user.active_project_id:
        return ["transfer", "tercuman", "yonetim"]
    project = _resolve_active_project(db, user)
    if not project:
        return []
    if not _can_user_access_project(db, user, project):
        return []
    visible = []
    for mk in MODULE_DISPLAY_ORDER:
        if mk != "yonetim" and not _is_module_enabled_for_project(db, int(project.id), mk):
            continue
        if _is_user_module_allowed(db, user, int(project.id), mk):
            visible.append(mk)
    return visible


def _visible_module_payload(db: Session, user: User) -> list[dict]:
    keys = _visible_modules_for_user(db, user)
    return [
        {
            "key": mk,
            "href": MODULE_HREF_MAP.get(mk, ""),
        }
        for mk in keys
    ]


def _require_module_access(db: Session, current_user: User, module_key: str) -> None:
    mk = str(module_key or "").strip().lower()
    if is_superadmin(current_user) and not current_user.active_project_id:
        if mk not in {"yonetim", "transfer", "tercuman"}:
            raise HTTPException(status_code=403, detail="Management mode: select a project for this module")
        return
    project = _resolve_active_project(db, current_user)
    if not project:
        raise HTTPException(status_code=403, detail="Active project required")
    if not _can_user_access_project(db, current_user, project):
        raise HTTPException(status_code=403, detail="Project access denied")
    if mk != "yonetim" and not _is_module_enabled_for_project(db, int(project.id), mk):
        raise HTTPException(status_code=403, detail="Module disabled for active project")
    if not _is_user_module_allowed(db, current_user, int(project.id), mk):
        raise HTTPException(status_code=403, detail="Module access denied for user")


def _active_project_and_management_scope(db: Session, user: User) -> tuple[Project | None, bool]:
    active_project = _resolve_active_project(db, user)
    management_scope = bool(
        (active_project is not None and _is_management_project(active_project))
        or (is_superadmin(user) and user.active_project_id is None)
    )
    return active_project, management_scope


def _resolve_project_scope_for_user(
    db: Session,
    user: User,
    requested_project_id: int | str | None = None,
) -> tuple[int | None, bool]:
    active_project, management_scope = _active_project_and_management_scope(db, user)
    parsed_project_id: int | None = None
    if requested_project_id is not None and str(requested_project_id).strip() != "":
        try:
            parsed_project_id = int(requested_project_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="project_id must be integer")
    elif active_project is not None:
        parsed_project_id = int(active_project.id)

    if management_scope:
        if (
            active_project is not None
            and _is_management_project(active_project)
            and parsed_project_id == int(active_project.id)
        ):
            parsed_project_id = None
        return parsed_project_id, True

    if active_project is None:
        raise HTTPException(status_code=400, detail="Active project required")
    if parsed_project_id is not None and parsed_project_id != int(active_project.id):
        raise HTTPException(status_code=403, detail="Only active project is allowed")
    return int(active_project.id), False


def _normalize_module_name(module_name: str | None) -> str:
    name = str(module_name or "").strip().lower()
    if name not in ALLOWED_MODULE_DATA_NAMES:
        raise HTTPException(status_code=400, detail="Invalid module_name")
    return name


def _resolve_tenant_for_module_data(
    db: Session,
    current_user: User,
    scoped_project_id: int | None,
    payload_tenant_id: int | None = None,
) -> int:
    if scoped_project_id is not None:
        project = db.query(Project).filter(Project.id == scoped_project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return int(project.tenant_id)

    if not is_superadmin(current_user):
        if not current_user.tenant_id:
            raise HTTPException(status_code=400, detail="Tenant scope required")
        return int(current_user.tenant_id)

    if payload_tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant_id is required in management scope")
    return int(payload_tenant_id)


def _extract_kayit_id_from_payload(payload: dict | None) -> int | None:
    payload = payload or {}
    direct = payload.get("kayit_id")
    if direct is None:
        data_obj = payload.get("data")
        if isinstance(data_obj, dict):
            direct = data_obj.get("kayit_id")
    if direct is None or str(direct).strip() == "":
        return None
    try:
        return int(direct)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="kayit_id must be integer")


def _ensure_kayit_exists_for_scope(
    db: Session,
    tenant_id: int,
    project_id: int | None,
    kayit_id: int | None,
) -> int:
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant scope required")
    if kayit_id is None:
        raise HTTPException(status_code=400, detail="kayit_id is required for this module")
    query = db.query(ModuleData).filter(
        ModuleData.id == kayit_id,
        ModuleData.module_name == "kayit",
        ModuleData.tenant_id == tenant_id,
    )
    if project_id is not None:
        query = query.filter(ModuleData.project_id == project_id)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Kişi kartı bulunamadı (kayit_id)")
    return int(row.id)


def _resolve_superadmin_tenant_id(db: Session, payload: dict | None = None) -> int | None:
    payload = payload or {}
    raw = payload.get("tenant_id")
    if raw is not None and str(raw).strip() != "":
        return int(raw)
    first_tenant = db.query(Tenant).order_by(Tenant.id.asc()).first()
    return int(first_tenant.id) if first_tenant else None


def _safe_name_part(value: str | None) -> str:
    txt = (value or "").strip()
    txt = re.sub(r"\s+", "_", txt)
    txt = re.sub(r"[^A-Za-z0-9._-]", "", txt)
    return txt or "BILET"


def _to_float(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).strip()
    if not raw:
        return 0.0
    if raw.lower() in {"hidden", "nan", "none", "-"}:
        return 0.0
    cleaned = re.sub(r"[^0-9,.\-]", "", raw)
    if not cleaned:
        return 0.0
    if cleaned.count(",") > 0 and cleaned.count(".") > 0:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif cleaned.count(",") > 0:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except Exception:
        m = re.search(r"-?\d+(?:[.,]\d+)?", cleaned)
        if not m:
            return 0.0
        try:
            return float(m.group(0).replace(",", "."))
        except Exception:
            return 0.0


def _normalize_project_city(value: str | None) -> str:
    txt = str(value or "").strip().upper()
    if not txt:
        return ""
    repl = {
        "İ": "I",
        "İ": "I",
        "Ş": "S",
        "Ğ": "G",
        "Ü": "U",
        "Ö": "O",
        "Ç": "C",
        "Â": "A",
        "Î": "I",
        "Û": "U",
    }
    for k, v in repl.items():
        txt = txt.replace(k, v)
    txt = re.sub(r"\s+", " ", txt)
    return txt


def _safe_translation_code() -> str:
    raw = secrets.token_urlsafe(7).upper()
    raw = re.sub(r"[^A-Z0-9]", "", raw)
    return (raw[:10] or "TRN0000001")


def _public_listener_url(req: Request | None, access_code: str) -> str:
    code = str(access_code or "").strip()
    if not code:
        return ""
    if req is None:
        return f"/canli-ceviri?code={code}"
    base = str(req.base_url).rstrip("/")
    return f"{base}/canli-ceviri?code={code}"


PRODUCT_META_PREFIX = "__META__"
PRODUCT_META_DESC_SEP = "__DESC__"


def _pack_product_description(raw_description: str | None, meta: dict | None) -> str | None:
    desc = str(raw_description or "").strip()
    meta_obj = meta or {}
    has_meta = any(v not in (None, "") for v in meta_obj.values())
    if not has_meta:
        return desc or None
    payload = json.dumps(meta_obj, ensure_ascii=False, separators=(",", ":"))
    return f"{PRODUCT_META_PREFIX}{payload}{PRODUCT_META_DESC_SEP}{desc}"


def _unpack_product_description(stored_description: str | None) -> tuple[str | None, dict]:
    raw = str(stored_description or "")
    if not raw.startswith(PRODUCT_META_PREFIX):
        return (raw.strip() or None), {}
    body = raw[len(PRODUCT_META_PREFIX):]
    sep_idx = body.find(PRODUCT_META_DESC_SEP)
    if sep_idx < 0:
        return (raw.strip() or None), {}
    meta_json = body[:sep_idx]
    desc = body[sep_idx + len(PRODUCT_META_DESC_SEP):].strip() or None
    try:
        meta_obj = json.loads(meta_json)
        if not isinstance(meta_obj, dict):
            meta_obj = {}
    except Exception:
        meta_obj = {}
    return desc, meta_obj


def _normalized_person_name(transfer: Transfer | None) -> str:
    if not transfer or not transfer.passenger_name:
        return ""
    parts = [p for p in transfer.passenger_name.split() if p]
    if not parts:
        return ""
    # TK kaynaklÄ± OCR'de isim formatÄ± Ã§oÄŸunlukla "SOYISIM ISIM" gelir.
    if (transfer.airline or "").lower() == "thy" and len(parts) >= 2:
        return " ".join(parts[1:] + [parts[0]])
    return transfer.passenger_name


def _split_person_name(transfer: Transfer | None) -> tuple[str, str]:
    full = (_normalized_person_name(transfer) or "").strip()
    parts = [p for p in full.split() if p]
    if len(parts) <= 1:
        return full, ""
    return " ".join(parts[:-1]), parts[-1]


def _resolve_target_airports(target_airports: str | None, operation_city: str | None) -> str | None:
    def _normalize(value: str | None) -> str | None:
        raw = (value or "").strip().upper()
        if not raw:
            return None
        parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
        expanded: list[str] = []
        for p in parts:
            if p in CITY_TO_IATA:
                expanded.extend([x.strip() for x in CITY_TO_IATA[p].split(",") if x.strip()])
            elif re.fullmatch(r"[A-Z]{3}", p):
                expanded.append(p)
        if not expanded:
            return None
        # tekilleştir ve sırayı koru
        seen = set()
        ordered = []
        for c in expanded:
            if c in seen:
                continue
            seen.add(c)
            ordered.append(c)
        return ",".join(ordered) if ordered else None

    # 1) Öncelik Operasyon Şehri
    city_codes = _normalize(operation_city)
    if city_codes:
        return city_codes
    # 2) Sonra opsiyonel alan (şehir veya IATA kabul edilir)
    manual_codes = _normalize(target_airports)
    if manual_codes:
        return manual_codes
    # 3) Boşsa worker tarafında biletten otomatik bulunacak
    return DEFAULT_TARGET_AIRPORTS or None


def _join_dt(date_value: str | None, time_value: str | None) -> str | None:
    d = (date_value or "").strip()
    t = (time_value or "").strip()
    if not d and not t:
        return None
    return f"{d} {t}".strip()


def _transfer_datetimes(transfer: Transfer) -> tuple[str | None, str | None]:
    # Ã–ncelik: segment bazlÄ± net alanlar
    if transfer.trip_type == "return_only":
        dep = _join_dt(transfer.return_departure_date, transfer.return_departure_time)
        arr = _join_dt(transfer.return_arrival_date, transfer.return_arrival_time)
        if dep or arr:
            return dep, arr

    dep = _join_dt(transfer.outbound_departure_date, transfer.outbound_departure_time)
    arr = _join_dt(transfer.outbound_arrival_date, transfer.outbound_arrival_time)
    if dep or arr:
        return dep, arr

    raw = transfer.raw_parse or {}
    if isinstance(raw, dict):
        segments = raw.get("segments") or []
        if isinstance(segments, list) and segments:
            chosen = None
            if transfer.trip_type == "return_only":
                chosen = next((s for s in segments if s.get("segment_role") == "donus"), None)
            if not chosen:
                chosen = next((s for s in segments if s.get("segment_role") == "gidis"), None)
            if not chosen:
                chosen = segments[0]
            dep = _join_dt(chosen.get("departure_date"), chosen.get("departure_time"))
            arr = _join_dt(chosen.get("arrival_date"), chosen.get("arrival_time"))
            if dep or arr:
                return dep, arr

    # Fallback: eski alanlar
    dep = _join_dt(transfer.flight_date, transfer.flight_time)
    return dep, None


def _gender_label_tr(value: str | None) -> str:
    v = (value or "").lower()
    if v == "male":
        return "Erkek"
    if v == "female":
        return "Kadin"
    return "UNKNOW"


def _next_transfer_action(current: str | None) -> str | None:
    if not current:
        return TRANSFER_ACTION_FLOW[0]
    try:
        idx = TRANSFER_ACTION_FLOW.index(current)
    except ValueError:
        return TRANSFER_ACTION_FLOW[0]
    if idx >= len(TRANSFER_ACTION_FLOW) - 1:
        return None
    return TRANSFER_ACTION_FLOW[idx + 1]


def _next_personnel_action(current: str | None) -> str | None:
    if not current:
        return PERSONNEL_ACTION_FLOW[0]
    key = str(current or "").strip().lower()
    try:
        idx = PERSONNEL_ACTION_FLOW.index(key)
    except ValueError:
        return PERSONNEL_ACTION_FLOW[0]
    if idx >= len(PERSONNEL_ACTION_FLOW) - 1:
        return None
    return PERSONNEL_ACTION_FLOW[idx + 1]


def _build_reservation_code(vehicle_code: str, flight_date: str | None, project_id: int | None) -> str:
    safe_vehicle = re.sub(r"[^A-Za-z0-9]", "", (vehicle_code or "").upper())[:12] or "VEH"
    safe_date = (flight_date or datetime.now().strftime("%Y-%m-%d")).replace("-", "")
    safe_project = str(project_id or 0)
    random_part = secrets.token_hex(2).upper()
    return f"RSV-{safe_vehicle}-{safe_date}-{safe_project}-{random_part}"


def _flight_shape_label(transfer: Transfer) -> str:
    raw = transfer.raw_parse or {}
    segments = raw.get("segments") if isinstance(raw, dict) else []
    roles = [str(s.get("segment_role") or "") for s in (segments or []) if isinstance(s, dict)]
    has_gidis = "gidis" in roles
    has_donus = "donus" in roles
    has_aktarma = "aktarma" in roles
    if has_gidis and has_donus and has_aktarma:
        return "gelis+donus+aktarma"
    if has_gidis and has_donus:
        return "gelis+donus"
    if has_donus and has_aktarma:
        return "donus_aktarma"
    if has_gidis and has_aktarma:
        return "gelis_aktarma"
    if has_donus:
        return "donus"
    if has_gidis:
        return "gelis"
    if has_aktarma:
        return "aktarma"
    trip = (transfer.trip_type or "").lower()
    if trip == "return_only":
        return "donus"
    if trip == "round_trip":
        return "gelis+donus"
    if trip == "connection":
        return "aktarma"
    if trip == "one_way":
        return "gelis"
    return ""


def _parse_segment_dt(seg: dict, date_key: str, time_key: str) -> datetime | None:
    d = (seg.get(date_key) or "").strip()
    t = (seg.get(time_key) or "").strip()
    if not d or not t:
        return None
    try:
        return datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _infer_center_airport(segments: list[dict]) -> str | None:
    # En uzun bekleme (arrival -> next departure) oluşan havalimanı operasyon merkezi adayıdır.
    best_airport = None
    best_gap = None
    for i in range(len(segments) - 1):
        cur = segments[i]
        nxt = segments[i + 1]
        if cur.get("to") != nxt.get("from"):
            continue
        arr = _parse_segment_dt(cur, "arrival_date", "arrival_time")
        dep = _parse_segment_dt(nxt, "departure_date", "departure_time")
        if not arr or not dep:
            continue
        gap = dep - arr
        if gap.total_seconds() < 0:
            continue
        if best_gap is None or gap > best_gap:
            best_gap = gap
            best_airport = cur.get("to")
    return best_airport


def _segment_rows_for_transfer(transfer: Transfer) -> list[dict]:
    raw = transfer.raw_parse or {}
    segments = raw.get("segments") if isinstance(raw, dict) else None
    if not isinstance(segments, list) or not segments:
        return [
            {
                "ucus_sekli": _flight_shape_label(transfer),
                "flight_no": transfer.flight_no,
                "from_to": f"{transfer.pickup_location or ''}/{transfer.dropoff_location or ''}".strip("/"),
                "kalkis_tarihi_saati": _transfer_datetimes(transfer)[0],
                "inis_tarihi_saati": _transfer_datetimes(transfer)[1],
            }
        ]

    center = _infer_center_airport(segments)
    first_donus_idx = None
    for i, seg in enumerate(segments):
        if (seg.get("segment_role") or "") == "donus":
            first_donus_idx = i
            break

    rows: list[dict] = []
    for i, seg in enumerate(segments):
        role = (seg.get("segment_role") or "").lower()
        ucus_sekli = ""
        if role == "gidis":
            ucus_sekli = "gelis"
        elif role == "donus":
            ucus_sekli = "donus"
        elif role == "aktarma":
            if first_donus_idx is not None and i >= first_donus_idx:
                ucus_sekli = "donus_aktarma"
            else:
                ucus_sekli = "gelis_aktarma"
        else:
            # Eski kayıtlarda role yoksa merkez havalimanına göre türet.
            from_code = seg.get("from")
            to_code = seg.get("to")
            if center and to_code == center and from_code != center:
                ucus_sekli = "gelis"
            elif center and from_code == center and to_code != center:
                ucus_sekli = "donus"
            elif first_donus_idx is not None and i >= first_donus_idx:
                ucus_sekli = "donus_aktarma"
            else:
                ucus_sekli = "gelis_aktarma"

        rows.append(
            {
                "ucus_sekli": ucus_sekli,
                "flight_no": seg.get("flight_no") or transfer.flight_no,
                "from_to": f"{seg.get('from') or ''}/{seg.get('to') or ''}".strip("/"),
                "kalkis_tarihi_saati": _join_dt(seg.get("departure_date"), seg.get("departure_time")),
                "inis_tarihi_saati": _join_dt(seg.get("arrival_date"), seg.get("arrival_time")),
            }
        )
    return rows


@app.on_event("startup")
def startup_event():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    # Keep schema forward-compatible for existing MVP databases.
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE uploads "
                "ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pending'"
            )
        )
        conn.execute(
            text("ALTER TABLE uploads ADD COLUMN IF NOT EXISTS parse_result JSONB")
        )
        conn.execute(
            text("ALTER TABLE uploads ADD COLUMN IF NOT EXISTS tenant_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE uploads ADD COLUMN IF NOT EXISTS user_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE uploads ADD COLUMN IF NOT EXISTS project_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE uploads ADD COLUMN IF NOT EXISTS operation_city VARCHAR(64)")
        )
        conn.execute(
            text("ALTER TABLE uploads ADD COLUMN IF NOT EXISTS operation_code VARCHAR(9)")
        )
        conn.execute(
            text("ALTER TABLE uploads ADD COLUMN IF NOT EXISTS error_message TEXT")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS upload_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS tenant_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS project_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS airline VARCHAR(32) NOT NULL DEFAULT 'unknown'")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS passenger_name VARCHAR(255)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS participant_phone VARCHAR(32)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS participant_order_no INTEGER")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS passenger_gender VARCHAR(16)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS pnr VARCHAR(16)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS flight_no VARCHAR(16)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS flight_date VARCHAR(10)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS flight_time VARCHAR(5)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS trip_type VARCHAR(24)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS outbound_date VARCHAR(10)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS return_date VARCHAR(10)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS segment_count INTEGER")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS outbound_departure_date VARCHAR(10)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS outbound_departure_time VARCHAR(5)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS outbound_arrival_date VARCHAR(10)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS outbound_arrival_time VARCHAR(5)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS return_departure_date VARCHAR(10)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS return_departure_time VARCHAR(5)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS return_arrival_date VARCHAR(10)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS return_arrival_time VARCHAR(5)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS needs_review BOOLEAN NOT NULL DEFAULT TRUE")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS payment_type VARCHAR(32)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS issue_date VARCHAR(10)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS pickup_time VARCHAR(16)")
        )
        conn.execute(
            text(
                "DO $$ BEGIN "
                "IF EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name='transfers' AND column_name='pickup_time' "
                "AND data_type <> 'character varying') THEN "
                "ALTER TABLE transfers ALTER COLUMN pickup_time TYPE VARCHAR(16) "
                "USING CASE "
                "WHEN pickup_time IS NULL THEN NULL "
                "ELSE to_char(pickup_time, 'HH24:MI') "
                "END; "
                "END IF; "
                "END $$;"
            )
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS transfer_point VARCHAR(255)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS vehicle_code VARCHAR(64)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS reservation_code VARCHAR(64)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS supplier_company_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS greeter_staff_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS driver_staff_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS transfer_action VARCHAR(32)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS driver_action VARCHAR(24)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS greeter_action VARCHAR(24)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS currency VARCHAR(8)")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS total_amount DOUBLE PRECISION")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS base_fare DOUBLE PRECISION")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS tax_total DOUBLE PRECISION")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS tax_breakdown JSONB")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS pricing_visibility VARCHAR(16) NOT NULL DEFAULT 'masked'")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS raw_parse JSONB")
        )
        conn.execute(
            text("ALTER TABLE transfers ALTER COLUMN ticket_id DROP NOT NULL")
        )
        conn.execute(
            text("ALTER TABLE transfers ALTER COLUMN pickup_location DROP NOT NULL")
        )
        conn.execute(
            text("ALTER TABLE transfers ALTER COLUMN dropoff_location DROP NOT NULL")
        )
        conn.execute(
            text("ALTER TABLE transfers ALTER COLUMN pickup_time DROP NOT NULL")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'unassigned'")
        )
        conn.execute(
            text("ALTER TABLE transfers ALTER COLUMN status SET DEFAULT 'unassigned'")
        )
        conn.execute(
            text("UPDATE transfers SET status = 'unassigned' WHERE status = 'pending' OR status IS NULL")
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_transfers_upload_id ON transfers (upload_id)"
            )
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_transfers_vehicle_code ON transfers (vehicle_code)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_transfers_participant_phone ON transfers (participant_phone)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_transfers_participant_order_no ON transfers (participant_order_no)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_transfers_reservation_code ON transfers (reservation_code)")
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_uploads_tenant_project_created "
                "ON uploads (tenant_id, project_id, created_at DESC)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_transfers_tenant_project_created "
                "ON transfers (tenant_id, project_id, created_at DESC)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_transfers_project_flight_dt "
                "ON transfers (project_id, flight_date, flight_time)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_transfers_project_lookup "
                "ON transfers (project_id, pnr, flight_no)"
            )
        )
        conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS default_supplier_company_id INTEGER")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_projects_default_supplier_company_id ON projects (default_supplier_company_id)")
        )
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS city_iata_map ("
                "city_code VARCHAR(64) PRIMARY KEY, "
                "iata_codes VARCHAR(64) NOT NULL, "
                "updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
                ")"
            )
        )
        for city_code, iata_codes in CITY_TO_IATA.items():
            conn.execute(
                text(
                    "INSERT INTO city_iata_map (city_code, iata_codes, updated_at) "
                    "VALUES (:city_code, :iata_codes, NOW()) "
                    "ON CONFLICT (city_code) DO UPDATE SET "
                    "iata_codes = EXCLUDED.iata_codes, updated_at = NOW()"
                ),
                {"city_code": city_code, "iata_codes": iata_codes},
            )
        conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS token_limit INTEGER")
        )
        conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS active_project_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS token_used INTEGER NOT NULL DEFAULT 0")
        )
        conn.execute(
            text("ALTER TABLE ops_events ADD COLUMN IF NOT EXISTS project_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE ops_events ADD COLUMN IF NOT EXISTS actor_user_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE ops_events ADD COLUMN IF NOT EXISTS actor_username VARCHAR(64)")
        )
        conn.execute(
            text("ALTER TABLE ops_events ADD COLUMN IF NOT EXISTS action VARCHAR(64)")
        )
        conn.execute(
            text("ALTER TABLE ops_events ADD COLUMN IF NOT EXISTS request_method VARCHAR(10)")
        )
        conn.execute(
            text("ALTER TABLE ops_events ADD COLUMN IF NOT EXISTS request_path VARCHAR(255)")
        )
        conn.execute(
            text("ALTER TABLE ops_events ADD COLUMN IF NOT EXISTS status_code INTEGER")
        )
        conn.execute(
            text("ALTER TABLE ops_events ADD COLUMN IF NOT EXISTS ip_address VARCHAR(64)")
        )
        conn.execute(
            text("ALTER TABLE ops_events ADD COLUMN IF NOT EXISTS user_agent VARCHAR(255)")
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_ops_events_scope_created "
                "ON ops_events (tenant_id, event_id, created_at DESC)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_ops_events_actor_created "
                "ON ops_events (actor_user_id, created_at DESC)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_ops_events_project_created "
                "ON ops_events (project_id, created_at DESC)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_ops_events_action_created "
                "ON ops_events (action, created_at DESC)"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_project_modules_project_module "
                "ON project_modules (project_id, module_key)"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_user_project_access_user_project "
                "ON user_project_access (user_id, project_id)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS user_module_access ("
                "id SERIAL PRIMARY KEY, "
                "user_id INTEGER NOT NULL, "
                "project_id INTEGER NOT NULL, "
                "module_key VARCHAR(64) NOT NULL, "
                "allowed BOOLEAN NOT NULL DEFAULT TRUE, "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_user_module_access_user_project_module "
                "ON user_module_access (user_id, project_id, module_key)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS driver_panel_tokens ("
                "id SERIAL PRIMARY KEY, "
                "token_hash VARCHAR(128) NOT NULL, "
                "tenant_id INTEGER NOT NULL, "
                "project_id INTEGER NULL, "
                "supplier_company_id INTEGER NULL, "
                "driver_staff_id INTEGER NOT NULL, "
                "greeter_staff_id INTEGER NULL, "
                "panel_role VARCHAR(16) NOT NULL DEFAULT 'driver', "
                "created_by_user_id INTEGER NULL, "
                "is_active BOOLEAN NOT NULL DEFAULT TRUE, "
                "expires_at TIMESTAMPTZ NOT NULL, "
                "consumed_at TIMESTAMPTZ NULL, "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
                ")"
            )
        )
        conn.execute(
            text("ALTER TABLE driver_panel_tokens ADD COLUMN IF NOT EXISTS greeter_staff_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE driver_panel_tokens ADD COLUMN IF NOT EXISTS panel_role VARCHAR(16) NOT NULL DEFAULT 'driver'")
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_driver_panel_tokens_hash "
                "ON driver_panel_tokens (token_hash)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_driver_panel_tokens_driver_exp "
                "ON driver_panel_tokens (driver_staff_id, expires_at DESC)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS supplier_clients ("
                "id SERIAL PRIMARY KEY, "
                "tenant_id INTEGER NOT NULL, "
                "supplier_company_id INTEGER NOT NULL, "
                "project_id INTEGER NULL, "
                "full_name VARCHAR(128) NOT NULL, "
                "phone VARCHAR(32) NULL, "
                "email VARCHAR(128) NULL, "
                "source_type VARCHAR(16) NOT NULL DEFAULT 'external', "
                "status VARCHAR(24) NOT NULL DEFAULT 'active', "
                "notes TEXT NULL, "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_supplier_clients_scope_created "
                "ON supplier_clients (tenant_id, supplier_company_id, created_at DESC)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS supplier_sms_templates ("
                "id SERIAL PRIMARY KEY, "
                "tenant_id INTEGER NOT NULL, "
                "supplier_company_id INTEGER NOT NULL, "
                "event_key VARCHAR(64) NOT NULL, "
                "template_text TEXT NOT NULL, "
                "is_active BOOLEAN NOT NULL DEFAULT TRUE, "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_supplier_sms_tpl_scope_event "
                "ON supplier_sms_templates (tenant_id, supplier_company_id, event_key)"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_service_products_tenant_code "
                "ON service_products (COALESCE(tenant_id, 0), code)"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_project_service_products_project_product "
                "ON project_service_products (project_id, product_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_module_data_scope_created "
                "ON module_data (tenant_id, project_id, module_name, created_at DESC)"
            )
        )
    db = SessionLocal()
    try:
        tenant_name = os.getenv("APP_DEFAULT_TENANT", "Default Company")
        tenant_tokens = int(os.getenv("APP_DEFAULT_TENANT_TOKENS", "100000"))
        tenant = db.query(Tenant).filter(Tenant.name == tenant_name).first()
        if not tenant:
            tenant = Tenant(name=tenant_name, token_balance=max(0, tenant_tokens), is_active=True)
            db.add(tenant)
            db.flush()
        _ensure_management_project_for_tenant(db, int(tenant.id))
        for t in db.query(Tenant).all():
            _ensure_management_project_for_tenant(db, int(t.id))
        admin_user = os.getenv("APP_ADMIN_USER", "CreaTRO")
        admin_pass = os.getenv("APP_ADMIN_PASS", "Micetro25+.")
        existing_exact = db.query(User).filter(User.username == admin_user).first()
        existing_alias = (
            db.query(User)
            .filter(User.username.in_(["admin", "CreaTRo", "CreaTRO"]))
            .order_by(User.id.asc())
            .first()
        )
        existing = existing_exact or existing_alias
        if not existing:
            db.add(
                User(
                    tenant_id=None,
                    username=admin_user,
                    password_hash=_hash_password(admin_pass),
                    role="superadmin",
                    is_active=True,
                )
            )
        else:
            existing.username = admin_user
            existing.password_hash = _hash_password(admin_pass)
            existing.role = "superadmin"
            existing.is_active = True
        db.query(User).filter(User.tenant_id.is_(None)).update({"tenant_id": tenant.id})
        db.query(Upload).filter(Upload.tenant_id.is_(None)).update({"tenant_id": tenant.id})
        db.query(Transfer).filter(Transfer.tenant_id.is_(None)).update({"tenant_id": tenant.id})
        if existing:
            existing.tenant_id = None

        # Global translation power user (cross-project / cross-tenant translation control)
        st_user = os.getenv("APP_SUPER_TRANSLATOR_USER", "SuperTranslator")
        st_pass = os.getenv("APP_SUPER_TRANSLATOR_PASS", "Micetro25+.")
        st = db.query(User).filter(User.username == st_user).first()
        if not st:
            db.add(
                User(
                    tenant_id=None,
                    username=st_user,
                    password_hash=_hash_password(st_pass),
                    role="supertranslator",
                    is_active=True,
                )
            )
        else:
            st.password_hash = _hash_password(st_pass)
            st.role = "supertranslator"
            st.is_active = True
            st.tenant_id = None
        db.commit()
    finally:
        db.close()


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db_status = "ok"
    redis_status = "ok"

    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        redis_client.ping()
    except Exception:
        redis_status = "error"

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return {"status": overall, "database": db_status, "redis": redis_status}


@app.get("/cities")
def list_cities():
    special = {
        "ISTANBUL": "İstanbul",
        "ANKARA": "Ankara",
        "ANTALYA": "Antalya",
        "IZMIR": "İzmir",
    }
    rest = sorted([c for c in PROJECT_CITY_CODES if c not in PROJECT_CITY_PRIORITY])
    ordered = PROJECT_CITY_PRIORITY + rest
    return [
        {
            "code": code,
            "name": special.get(code, code.title()),
            "iata_codes": CITY_TO_IATA.get(code, ""),
        }
        for code in ordered
    ]


@app.post("/admin-db/login")
def admin_db_login(payload: dict, response: Response, db: Session = Depends(get_db)):
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")
    user = (
        db.query(User)
        .filter(func.lower(User.username) == username.lower(), User.is_active.is_(True))
        .first()
    )
    if not user or not _verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if normalize_role(user.role) != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin required")
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=max(1, SESSION_IDLE_MINUTES))
    db.add(UserSession(user_id=user.id, token=token, expires_at=expires_at))
    db.commit()
    response.set_cookie(
        key=ADMIN_DB_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        max_age=max(60, SESSION_IDLE_MINUTES * 60),
        path="/",
    )
    return {"ok": True, "username": user.username, "role": user.role, "expires_at": expires_at.isoformat()}


@app.post("/admin-db/logout")
def admin_db_logout(
    response: Response,
    admin_db_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    token = str(admin_db_session or "").strip()
    if token:
        db.query(UserSession).filter(UserSession.token == token).delete()
        db.commit()
    response.delete_cookie(ADMIN_DB_COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/admin-db/me")
def admin_db_me(current_user: User = Depends(require_admin_db_auth)):
    return {"id": current_user.id, "username": current_user.username, "role": current_user.role}


@app.get("/admin/db/tables")
def admin_db_tables(
    scope: str = Query(default="all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_db_auth),
):
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    out = []
    for t in sorted(table_names):
        cols = inspector.get_columns(t)
        col_names = [str(c.get("name") or "") for c in cols]
        has_project_id = "project_id" in col_names
        if scope == "project" and not has_project_id:
            continue
        if scope == "general" and has_project_id:
            continue
        out.append({"name": t, "has_project_id": has_project_id, "columns": col_names})
    return out


@app.get("/admin/db/projects-active")
def admin_db_projects_active(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_db_auth),
):
    rows = db.query(Project).filter(Project.is_active.is_(True)).order_by(Project.operation_code.asc()).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "city": r.city,
            "operation_code": r.operation_code,
            "tenant_id": r.tenant_id,
        }
        for r in rows
    ]


@app.get("/admin/db/table/{table_name}")
def admin_db_table_rows(
    table_name: str,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_db_auth),
):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name or ""):
        raise HTTPException(status_code=400, detail="Invalid table name")
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if table_name not in table_names:
        raise HTTPException(status_code=404, detail="Table not found")
    cols = inspector.get_columns(table_name)
    col_names = [str(c.get("name") or "") for c in cols]
    has_project_id = "project_id" in col_names
    order_col = "id" if "id" in col_names else None
    where_sql = ""
    params: dict = {"limit": int(limit), "offset": int(offset)}
    if has_project_id and project_id is not None:
        where_sql = " WHERE project_id = :project_id"
        params["project_id"] = int(project_id)
    order_sql = f" ORDER BY {order_col} DESC" if order_col else ""
    q = text(f"SELECT * FROM {table_name}{where_sql}{order_sql} LIMIT :limit OFFSET :offset")
    count_q = text(f"SELECT COUNT(*) AS cnt FROM {table_name}{where_sql}")
    with engine.connect() as conn:
        rows = conn.execute(q, params).mappings().all()
        cnt = int(conn.execute(count_q, {k: v for k, v in params.items() if k != "limit" and k != "offset"}).scalar() or 0)
    def _json_safe(v):
        if isinstance(v, (datetime, )):
            return v.isoformat()
        return v
    return {
        "table": table_name,
        "columns": col_names,
        "has_project_id": has_project_id,
        "count": cnt,
        "rows": [{k: _json_safe(v) for k, v in dict(r).items()} for r in rows],
    }


@app.post("/auth/login")
def auth_login(payload: dict, db: Session = Depends(get_db)):
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active or not _verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = secrets.token_urlsafe(48)
    # İlk açılışta da idle timeout uygulanır; her istekle sliding olarak yenilenir.
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=max(1, SESSION_IDLE_MINUTES))
    db.add(UserSession(user_id=user.id, token=token, expires_at=expires_at))
    db.commit()
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first() if user.tenant_id else None
    active_project = (
        db.query(Project).filter(Project.id == user.active_project_id).first()
        if user.active_project_id
        else None
    )
    management_mode = bool(is_superadmin(user) and not user.active_project_id)
    visible_modules = _visible_module_payload(db, user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
        "tenant_token_balance": tenant.token_balance if tenant else None,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "tenant_name": tenant.name if tenant else None,
            "token_limit": user.token_limit,
            "token_used": user.token_used,
            "token_remaining": (
                max(0, int(user.token_limit or 0) - int(user.token_used or 0))
                if user.token_limit is not None
                else None
            ),
            "active_project_id": user.active_project_id,
            "active_project_name": active_project.name if active_project else None,
            "active_project_code": active_project.operation_code if active_project else None,
            "management_mode": management_mode,
            "visible_modules": visible_modules,
        },
    }


@app.get("/auth/me")
def auth_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first() if current_user.tenant_id else None
    active_project = (
        db.query(Project).filter(Project.id == current_user.active_project_id).first()
        if current_user.active_project_id
        else None
    )
    management_mode = bool(is_superadmin(current_user) and not current_user.active_project_id)
    visible_modules = _visible_module_payload(db, current_user)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "tenant_id": current_user.tenant_id,
        "tenant_name": tenant.name if tenant else None,
        "token_limit": current_user.token_limit,
        "token_used": current_user.token_used,
        "token_remaining": (
            max(0, int(current_user.token_limit or 0) - int(current_user.token_used or 0))
            if current_user.token_limit is not None
            else None
        ),
        "tenant_token_balance": tenant.token_balance if tenant else None,
        "active_project_id": current_user.active_project_id,
        "active_project_name": active_project.name if active_project else None,
        "active_project_code": active_project.operation_code if active_project else None,
        "management_mode": management_mode,
        "visible_modules": visible_modules,
    }


@app.get("/auth/session-status")
def auth_session_status(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    now = datetime.now(timezone.utc)
    session = (
        db.query(UserSession)
        .filter(UserSession.token == token, UserSession.expires_at > now)
        .first()
    )
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = db.query(User).filter(User.id == session.user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    remaining_seconds = max(0, int((session.expires_at - now).total_seconds()))
    return {
        "expires_at": session.expires_at.isoformat(),
        "remaining_seconds": remaining_seconds,
        "idle_timeout_minutes": max(1, SESSION_IDLE_MINUTES),
    }


@app.post("/auth/keepalive")
def auth_keepalive(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    user = _find_user_by_token(db, token, touch_session=True)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    now = datetime.now(timezone.utc)
    session = (
        db.query(UserSession)
        .filter(UserSession.token == token, UserSession.expires_at > now)
        .first()
    )
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    remaining_seconds = max(0, int((session.expires_at - now).total_seconds()))
    return {
        "ok": True,
        "expires_at": session.expires_at.isoformat(),
        "remaining_seconds": remaining_seconds,
    }


@app.get("/auth/personal-qr")
def auth_personal_qr(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    active_project = (
        db.query(Project).filter(Project.id == current_user.active_project_id).first()
        if current_user.active_project_id
        else None
    )
    project_code = (active_project.operation_code if active_project else "PROJESIZ") or "PROJESIZ"
    payload = f"UID:{current_user.id}|PROJECT:{project_code}"
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    headers = {"X-QR-Payload": payload}
    return StreamingResponse(buf, media_type="image/png", headers=headers)


@app.put("/auth/active-project")
def set_active_project(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    project_id_raw = payload.get("project_id")
    if project_id_raw is None:
        if is_superadmin(current_user):
            current_user.active_project_id = None
            db.commit()
            return {
                "ok": True,
                "active_project_id": None,
                "active_project_name": None,
                "active_project_code": None,
                "management_mode": True,
            }
        raise HTTPException(status_code=400, detail="project_id is required")
    try:
        project_id = int(project_id_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="project_id must be integer")
    query = db.query(Project).filter(Project.id == project_id, Project.is_active.is_(True))
    if not is_superadmin(current_user):
        query = query.filter(Project.tenant_id == current_user.tenant_id)
    project = query.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not _can_user_access_project(db, current_user, project):
        raise HTTPException(status_code=403, detail="Project access denied")
    current_user.active_project_id = project.id
    db.commit()
    return {
        "ok": True,
        "active_project_id": project.id,
        "active_project_name": project.name,
        "active_project_code": project.operation_code,
        "management_mode": False,
    }


@app.put("/auth/management-project")
def set_management_project(
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = current_user.tenant_id
    if is_superadmin(current_user):
        raw = (payload or {}).get("tenant_id") if payload else None
        if raw is not None:
            try:
                tenant_id = int(raw)
            except Exception:
                raise HTTPException(status_code=400, detail="tenant_id must be integer")
        elif tenant_id is None:
            first_tenant = db.query(Tenant).order_by(Tenant.id.asc()).first()
            tenant_id = int(first_tenant.id) if first_tenant else None
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    mgmt = _ensure_management_project_for_tenant(db, int(tenant_id))
    current_user.active_project_id = mgmt.id
    db.commit()
    return {
        "ok": True,
        "active_project_id": mgmt.id,
        "active_project_name": mgmt.name,
        "active_project_code": mgmt.operation_code,
        "management_mode": False,
    }


@app.get("/", response_class=HTMLResponse)
def home_login():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Creatro Giriş</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .box { max-width: 680px; margin: 50px auto; background: #fff; border: 1px solid #dde4ef; border-radius: 12px; padding: 24px; }
    input { padding: 9px; }
    button { background: #2b7fff; color: #fff; border: 0; border-radius: 8px; padding: 10px 14px; cursor: pointer; }
    .muted { color: #5c6b82; font-size: 13px; margin-top: 8px; }
    .footer-brand { position: fixed; left: 0; right: 0; bottom: 0; height: 54px; background: #0A1024; display: flex; align-items: center; padding-left: 12px; z-index: 998; overflow: hidden; }
    .footer-brand img { height: 150%; width: auto; display: block; object-fit: cover; object-position: center; clip-path: inset(0 3% 0 0); }
    .logo-reg { color: #fff; font-size: 12px; line-height: 1; margin-left: 0; font-weight: 700; position: relative; left: -26px; transform: translateY(-45%); }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
    .overlay { position: fixed; inset: 0; background: rgba(10,16,36,0.45); display: none; align-items: center; justify-content: center; z-index: 1200; }
    .overlay .card { background: #fff; border: 1px solid #d8e0ee; border-radius: 12px; min-width: 320px; padding: 16px; text-align: center; box-shadow: 0 12px 30px rgba(10,16,36,0.22); }
    .spinner { width: 28px; height: 28px; border: 3px solid #d9e5fb; border-top-color: #2b7fff; border-radius: 50%; margin: 0 auto 10px auto; animation: spin 1s linear infinite; }
    .popup { position: fixed; inset: 0; background: rgba(10,16,36,0.45); display: none; align-items: center; justify-content: center; z-index: 1250; }
    .popup .card { background: #fff; border: 1px solid #d8e0ee; border-radius: 12px; min-width: 360px; max-width: 92vw; padding: 16px; box-shadow: 0 12px 30px rgba(10,16,36,0.22); }
    .popup .title { font-size: 15px; font-weight: 700; margin-bottom: 8px; }
    .popup .actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
    .btn-small { padding: 6px 10px; font-size: 12px; border-radius: 6px; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .dup-alert td { background: #FDE7E9 !important; color: #7A0010 !important; font-weight: 700 !important; }
  </style>
</head>
<body>
  <div class="box">
    <h2>Creatro Panel Girişi</h2>
    <div>
      <input id="username" placeholder="Kullanıcı adi" />
      <input id="password" type="password" placeholder="Şifre" />
      <label style="margin-left:6px; font-size:13px;"><input id="rememberMe" type="checkbox" /> Beni Hatirla</label>
      <button id="loginBtn" type="button">Giriş Yap</button>
    </div>
    <div id="tokenInfo" class="muted"></div>
    <div id="summary" class="muted"></div>
    <div class="links" style="margin-top:14px;">
      <a href="/modules-ui">Modüller</a>
      <a href="/transfer-ui">Ulaşım Modülü</a>
      <a href="/reports-ui">Raporlar</a>
            <a href="/duyurular-ui">Duyurular</a>
      <a href="/upload-ui">Upload</a>
      <a href="/projects-ui">Projeler</a>
      <a href="/users-ui">Kullanıcılar</a>
      <a href="/supplier-ui">Arac Firmasi</a>
    </div>
  </div>
  <script>
    const username = document.getElementById('username');
    const password = document.getElementById('password');
    const rememberMe = document.getElementById('rememberMe');
    const loginBtn = document.getElementById('loginBtn');
    const tokenInfo = document.getElementById('tokenInfo');
    const summary = document.getElementById('summary');
    const rememberedUsername = localStorage.getItem('remembered_username') || '';
    const rememberedEnabled = localStorage.getItem('remember_me') === '1';
    if (rememberedEnabled && rememberedUsername) {
      username.value = rememberedUsername;
      rememberMe.checked = true;
    }
    const loginOnEnter = (e) => { if (e.key === 'Enter') { e.preventDefault(); loginBtn.click(); } };
    username.addEventListener('keydown', loginOnEnter);
    password.addEventListener('keydown', loginOnEnter);
    const clearSessionCache = () => {
      const uiLang = localStorage.getItem('ui_lang') || '';
      localStorage.clear();
      sessionStorage.clear();
      if (uiLang) localStorage.setItem('ui_lang', uiLang);
    };
    const authHeaders = () => ({ 'Authorization': `Bearer ${token}` });
    const renderTokenInfo = (user, tenantBalance) => {
      const personal = user && user.token_remaining != null ? user.token_remaining : 'SINIRSIZ';
      const firma = tenantBalance != null ? tenantBalance : '-';
      tokenInfo.textContent = `Kisisel Token: ${personal} | Firma Token: ${firma}`;
    };
    const loadSessionInfo = async () => {
      const t = localStorage.getItem('access_token') || '';
      if (!t) return;
      try {
        const res = await fetch('/auth/me', { headers: { Authorization: `Bearer ${t}` } });
        const data = await res.json();
        if (!res.ok) {
          clearSessionCache();
          summary.textContent = 'Oturum suresi dolmus, tekrar giris yapin.';
          return;
        }
        renderTokenInfo(data, data.tenant_token_balance);
        summary.textContent = `Oturum aktif: ${data.username}`;
      } catch (_) {}
    };
    loadSessionInfo();

    loginBtn.addEventListener('click', async () => {
      summary.textContent = 'Giriş yapiliyor...';
      try {
        const res = await fetch('/auth/login', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ username: username.value, password: password.value })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Giriş başarısız');
        clearSessionCache();
        localStorage.setItem('access_token', data.access_token || '');
        renderTokenInfo(data.user || {}, data.tenant_token_balance);
        if (rememberMe.checked) {
          localStorage.setItem('remember_me', '1');
          localStorage.setItem('remembered_username', username.value || '');
        } else {
          localStorage.removeItem('remember_me');
          localStorage.removeItem('remembered_username');
        }
        summary.textContent = `Giriş başarılı: ${data.user.username}`;
        if (data.user && (data.user.active_project_id || data.user.role === 'superadmin')) window.location.href = '/modules-ui';
        else window.location.href = '/project-select-ui';
      } catch (err) {
        summary.textContent = `Hata: ${err.message}`;
      }
    });
  </script>  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""


@app.get("/assets/kontrast-logo.png")
def asset_kontrast_logo():
    logo_path = APP_DIR / "kontrast_logo.png"
    if not logo_path.exists():
        raise HTTPException(status_code=404, detail="Logo not found")
    return FileResponse(str(logo_path), media_type="image/png")


@app.get("/project-select-ui", response_class=HTMLResponse)
def project_select_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Proje Seçimi</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color:#1c2635; }
    .wrap { max-width: 760px; margin: 30px auto; padding: 16px; }
    .head { background:#0A1024; color:#fff; border-radius:10px; padding:10px 12px; margin-bottom:12px; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .muted { color:#5c6b82; font-size:13px; margin-top:8px; }
    select, input { padding:9px; border:1px solid #cfd9e8; border-radius:8px; min-width: 280px; }
    button { background:#2b7fff; color:#fff; border:0; border-radius:8px; padding:9px 12px; cursor:pointer; }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
    .overlay { position: fixed; inset: 0; background: rgba(10,16,36,0.45); display: none; align-items: center; justify-content: center; z-index: 1200; }
    .overlay .card { background: #fff; border: 1px solid #d8e0ee; border-radius: 12px; min-width: 320px; padding: 16px; text-align: center; box-shadow: 0 12px 30px rgba(10,16,36,0.22); }
    .spinner { width: 28px; height: 28px; border: 3px solid #d9e5fb; border-top-color: #2b7fff; border-radius: 50%; margin: 0 auto 10px auto; animation: spin 1s linear infinite; }
    .popup { position: fixed; inset: 0; background: rgba(10,16,36,0.45); display: none; align-items: center; justify-content: center; z-index: 1250; }
    .popup .card { background: #fff; border: 1px solid #d8e0ee; border-radius: 12px; min-width: 360px; max-width: 92vw; padding: 16px; box-shadow: 0 12px 30px rgba(10,16,36,0.22); }
    .popup .title { font-size: 15px; font-weight: 700; margin-bottom: 8px; }
    .popup .actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
    .btn-small { padding: 6px 10px; font-size: 12px; border-radius: 6px; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head"><strong>PROJE SEÇİMİ</strong></div>
    <div class="box">
      <div>Devam etmek için bir proje seçmelisiniz.</div>
      <div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
        <select id="projectSelect"><option value="">Proje Seçiniz</option></select>
        <button id="saveBtn" type="button">Projeye Geçiş Yap</button>
        <button id="togglePassiveBtn" type="button" style="background:#5c6b82;">Pasifleri Göster</button>
      </div>
      <div id="summary" class="muted"></div>
    </div>
  </div>
  <script>
    const token = localStorage.getItem('access_token') || '';
    const projectSelect = document.getElementById('projectSelect');
    const togglePassiveBtn = document.getElementById('togglePassiveBtn');
    const saveBtn = document.getElementById('saveBtn');
    const summary = document.getElementById('summary');
    let showPassive = false;
    let allProjects = [];
    const returnParam = new URLSearchParams(window.location.search).get('return') || '/modules-ui';
    const sanitizeReturn = (v) => {
      const s = String(v || '/modules-ui').trim();
      if (!s.startsWith('/')) return '/modules-ui';
      if (s.startsWith('//')) return '/modules-ui';
      return s;
    };
    const returnTo = sanitizeReturn(returnParam);
    const headers = () => ({ Authorization: `Bearer ${token}` });
    const renderProjects = (activeProjectId) => {
      projectSelect.innerHTML = '<option value="">Proje Seçiniz</option>';
      const filtered = (allProjects || []).filter((p) => showPassive ? true : !!p.is_active);
      filtered.forEach((p) => {
        const op = document.createElement('option');
        op.value = String(p.id);
        op.textContent = `${p.name} | ${p.city} | ${p.operation_code}${p.is_active ? '' : ' (PASIF)'}`;
        projectSelect.appendChild(op);
      });
      if (activeProjectId) {
        const exists = filtered.some((p) => String(p.id) === String(activeProjectId));
        if (exists) projectSelect.value = String(activeProjectId);
      }
      togglePassiveBtn.textContent = showPassive ? 'Pasifleri Gizle' : 'Pasifleri Göster';
    };
    const load = async () => {
      if (!token) { window.location.href = '/'; return; }
      const meRes = await fetch('/auth/me', { headers: headers() });
      const me = await meRes.json();
      if (!meRes.ok) { const uiLang = localStorage.getItem('ui_lang') || ''; localStorage.clear(); sessionStorage.clear(); if (uiLang) localStorage.setItem('ui_lang', uiLang); window.location.href = '/'; return; }
      const res = await fetch('/projects', { headers: headers() });
      const data = await res.json();
      if (!res.ok) { summary.textContent = data.detail || 'Projeler alınamadı.'; return; }
      allProjects = Array.isArray(data) ? data : [];
      renderProjects(me.active_project_id);
    };
    togglePassiveBtn.addEventListener('click', () => {
      const current = projectSelect.value;
      showPassive = !showPassive;
      renderProjects(current);
    });
    saveBtn.addEventListener('click', async () => {
      const val = projectSelect.value;
      if (!val) { summary.textContent = 'Önce proje seçiniz.'; return; }
      summary.textContent = 'Kaydediliyor...';
      const res = await fetch('/auth/active-project', {
        method: 'PUT',
        headers: { ...headers(), 'Content-Type':'application/json' },
        body: JSON.stringify({ project_id: parseInt(val, 10) })
      });
      const data = await res.json();
      if (!res.ok) { summary.textContent = data.detail || 'Proje kaydedilemedi.'; return; }
      summary.textContent = `Aktif proje: ${data.active_project_name}`;
      window.location.href = returnTo;
    });
    load();
  </script>
  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""


@app.get("/modules-ui", response_class=HTMLResponse)
def modules_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Modüller</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { width: 100%; margin: 0; padding: 16px; box-sizing: border-box; }
    .head {
      display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;
      background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; position:relative;
    }
    .head-left { display:flex; align-items:center; gap:12px; }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn {
      background: rgba(255,255,255,0.18); color:#fff; text-decoration:none;
      border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px;
    }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .head-right { display:flex; flex-direction:row; align-items:center; gap:8px; margin-right:68px; }
    .right-panel {
      border:1px solid rgba(159,216,255,0.45);
      border-radius:8px;
      padding:4px 7px;
      background:rgba(8,23,56,0.20);
    }
    .links a { margin-right: 6px; color: #9FD8FF; text-decoration: none; font-size: 11px; font-weight: 600; }
    .admin-menu { position:relative; }
    .admin-btn { display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF; border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600; text-decoration:none; cursor:pointer; white-space:nowrap; }
    .admin-menu .links { display:none; position:absolute; top:100%; margin-top:2px; right:0; min-width:150px; background:#0A1024; border:1px solid rgba(159,216,255,0.35); border-radius:8px; padding:6px; z-index:50; }
    .admin-menu .links a { display:block; margin:0; padding:5px 6px; color:#9FD8FF; border-radius:6px; }
    .admin-menu .links a:hover { background:rgba(159,216,255,0.12); }
    .admin-menu:hover .links, .admin-menu:focus-within .links, .admin-menu.open .links { display:block; }
    .project-badge {
      display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF;
      border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600;
      letter-spacing:0.15px; white-space:nowrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08);
    }
    .project-badge {
      display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF;
      border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600;
      letter-spacing:0.15px; white-space:nowrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08);
    }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn {
      background: rgba(255,255,255,0.18); color:#fff; text-decoration:none;
      border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px;
    }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .dd { position: relative; display: inline-block; margin-right: 10px; }
    .dd > a { color:#fff; text-decoration:none; font-size:14px; }
    .dd-content {
      display:none; position:absolute; top:22px; left:0; min-width:180px;
      background:#fff; border:1px solid #dde4ef; border-radius:8px; z-index:10; padding:6px 0;
    }
    .dd-content a { display:block; color:#1c2635; text-decoration:none; padding:7px 10px; margin:0; font-size:13px; }
    .dd-content a:hover { background:#f0f5ff; }
    .dd:hover .dd-content { display:block; }
    .lang-mini { position:absolute; top:4px; right:8px; font-size:11px; padding:2px 4px; border-radius:6px; border:0; }
    .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; max-width: 1100px; margin: 0 auto; }
    .card {
      background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:14px;
      display:flex; flex-direction:column; gap:8px; align-items:center; position:relative; overflow:hidden;
      transition: background-color .18s ease, border-color .18s ease, color .18s ease;
    }
    .card-icon {
      width:54px; height:54px; border-radius:14px; display:flex; align-items:center; justify-content:center;
      background:#eaf2ff; border:1px solid #cad8f2; z-index:1;
    }
    .card-icon svg {
      width:28px; height:28px; stroke:currentColor; fill:none; stroke-width:2; stroke-linecap:round; stroke-linejoin:round;
    }
    .card-shape {
      position:absolute; right:-16px; top:-16px; width:74px; height:74px; border-radius:20px;
      transform:rotate(18deg); opacity:0.16; pointer-events:none;
    }
    .card-register { --accent:#0d6efd; }
    .card-hotel { --accent:#2a9d8f; }
    .card-meeting { --accent:#e67e22; }
    .card-interpreter { --accent:#8e44ad; }
    .card-transport { --accent:#1f78ff; }
    .card-finance { --accent:#16a34a; }
    .card-announcement { --accent:#f59e0b; }
    .card-admin { --accent:#ef4444; }
    .card-register .card-icon { background:#e7f0ff; border-color:#b9d4ff; color:#0d6efd; }
    .card-hotel .card-icon { background:#e8faf7; border-color:#b8ece4; color:#2a9d8f; }
    .card-meeting .card-icon { background:#fff2e6; border-color:#ffd8b6; color:#e67e22; }
    .card-interpreter .card-icon { background:#f6ecfb; border-color:#ddc5ef; color:#8e44ad; }
    .card-transport .card-icon { background:#e9f2ff; border-color:#bfd7ff; color:#1f78ff; }
    .card-finance .card-icon { background:#eaf9ef; border-color:#bde8cb; color:#16a34a; }
    .card-announcement .card-icon { background:#fff8e9; border-color:#ffe1a6; color:#f59e0b; }
    .card-admin .card-icon { background:#ffecec; border-color:#ffc8c8; color:#ef4444; }
    .card-register .card-shape,
    .card-hotel .card-shape,
    .card-meeting .card-shape,
    .card-interpreter .card-shape,
    .card-transport .card-shape,
    .card-finance .card-shape,
    .card-announcement .card-shape,
    .card-admin .card-shape {
      background:var(--accent);
    }
    .card h3 { margin:0; font-size:18px; text-align:center; width:100%; }
    .card .muted { color:#5c6b82; font-size:13px; min-height:32px; text-align:center; width:100%; }
    .card a {
      width: fit-content; background:#2b7fff; color:#fff; text-decoration:none;
      border-radius:8px; padding:8px 12px; border:1px solid #2b7fff;
      transition: background-color .18s ease, color .18s ease, border-color .18s ease;
    }
    .card:has(a:hover),
    .card:has(a:focus-visible) {
      background:#0A1024;
      border-color:#0A1024;
    }
    .card:has(a:hover) h3,
    .card:has(a:hover) .muted,
    .card:has(a:focus-visible) h3,
    .card:has(a:focus-visible) .muted {
      color:#fff;
    }
    .card:has(a:hover) .card-icon,
    .card:has(a:focus-visible) .card-icon {
      background:rgba(255,255,255,0.15);
      border-color:rgba(255,255,255,0.38);
      color:#fff;
    }
    .card:has(a:hover) .card-shape,
    .card:has(a:focus-visible) .card-shape {
      background:rgba(255,255,255,0.3);
      opacity:0.28;
    }
    .card:has(a:hover) a,
    .card:has(a:focus-visible) a {
      background:#fff;
      color:#0A1024;
      border-color:#fff;
    }
    .logout-fab {
      position: fixed;
      right: 18px;
      bottom: 8px;
      z-index: 1200;
      border: 0;
      border-radius: 999px;
      background: #0A1024;
      color: #fff;
      padding: 10px 14px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 8px 20px rgba(0,0,0,0.22);
    }
    .logout-fab:hover { background:#121a34; }
    .footer-brand { position: fixed; left: 0; right: 0; bottom: 0; height: 54px; background: #0A1024; display: flex; align-items: center; padding-left: 12px; z-index: 998; overflow: hidden; }
    .footer-brand img { height: 150%; width: auto; display: block; object-fit: cover; object-position: center; clip-path: inset(0 3% 0 0); }
    .logo-reg { color: #fff; font-size: 12px; line-height: 1; margin-left: 0; font-weight: 700; position: relative; left: -26px; transform: translateY(-45%); }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
    .overlay { position: fixed; inset: 0; background: rgba(10,16,36,0.45); display: none; align-items: center; justify-content: center; z-index: 1200; }
    .overlay .card { background: #fff; border: 1px solid #d8e0ee; border-radius: 12px; min-width: 320px; padding: 16px; text-align: center; box-shadow: 0 12px 30px rgba(10,16,36,0.22); }
    .spinner { width: 28px; height: 28px; border: 3px solid #d9e5fb; border-top-color: #2b7fff; border-radius: 50%; margin: 0 auto 10px auto; animation: spin 1s linear infinite; }
    .popup { position: fixed; inset: 0; background: rgba(10,16,36,0.45); display: none; align-items: center; justify-content: center; z-index: 1250; }
    .popup .card { background: #fff; border: 1px solid #d8e0ee; border-radius: 12px; min-width: 360px; max-width: 92vw; padding: 16px; box-shadow: 0 12px 30px rgba(10,16,36,0.22); }
    .popup .title { font-size: 15px; font-weight: 700; margin-bottom: 8px; }
    .popup .actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
    .btn-small { padding: 6px 10px; font-size: 12px; border-radius: 6px; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="head-left module-nav">
        <a id="navHome" class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a id="navRegister" class="m-btn" href="/kayit-ui" accesskey="2" title="Kısayol: Alt+2">Kayıt Modülü</a>
        <a id="navHotel" class="m-btn" href="/konaklama-ui" accesskey="3" title="Kısayol: Alt+3">Konaklama Modülü</a>
        <a id="navMeeting" class="m-btn" href="/toplanti-ui" accesskey="4" title="Kısayol: Alt+4">Toplantı Modülü</a>
        <a id="navInterpreter" class="m-btn" href="/tercuman-ui">Tercüman Modülü</a>
        <a id="navTransfer" class="m-btn" href="/transfer-ui" accesskey="1" title="Kısayol: Alt+1">Ulaşım Modülü</a>
        <a id="navFinance" class="m-btn" href="/muhasebe-finans-ui" accesskey="5" title="Kısayol: Alt+5">Muhasebe - Finans Modülü</a>
        <a id="navAnnouncements" class="m-btn" href="/duyurular-ui" accesskey="6" title="Kısayol: Alt+6">Duyurular</a>
      </div>
      <div class="head-right">
        <div class="admin-menu">
          <a id="linkAdmin" class="admin-btn" href="/yonetici-ui">Yönetici Modülü</a>
          <div class="links">
            <a id="linkReports" href="/reports-ui">Raporlar</a>
            <a href="/duyurular-ui">Duyurular</a>
            <a id="linkProjects" href="/projects-ui">Projeler</a>
            <a id="linkUsers" href="/users-ui">Kullanıcılar</a>
          </div>
        </div>
        <div class="right-panel">
          <span id="activeProjectBadge" class="project-badge">AKTİF PROJE: -</span>
        </div>
      </div>
      <select id="langSelect" class="lang-mini">
        <option value="tr">TR</option>
        <option value="en">EN</option>
        <option value="es">ES</option>
        <option value="ar">??</option>
        <option value="it">IT</option>
        <option value="ru">??</option>
      </select>
    </div>
    <div class="grid">
      <div class="card card-register">
        <span class="card-shape"></span>
        <div class="card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M8 3h8l4 4v14H4V3h4z"></path><path d="M9 3v6h6V3"></path><path d="M8 14h8"></path></svg>
        </div>
        <h3 id="cardRegisterTitle">Kayıt Modülü</h3>
        <div id="cardRegisterDesc" class="muted">Kayıt operasyonları için ana modül.</div>
        <a id="cardRegisterBtn" href="/kayit-ui">Aç</a>
      </div>
      <div class="card card-hotel">
        <span class="card-shape"></span>
        <div class="card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M3 21V9l9-6 9 6v12"></path><path d="M9 21v-6h6v6"></path><path d="M8 10h.01M12 10h.01M16 10h.01"></path></svg>
        </div>
        <h3 id="cardHotelTitle">Konaklama Modülü</h3>
        <div id="cardHotelDesc" class="muted">Konaklama operasyonları için ana modül.</div>
        <a id="cardHotelBtn" href="/konaklama-ui">Aç</a>
      </div>
      <div class="card card-meeting">
        <span class="card-shape"></span>
        <div class="card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="12" rx="2"></rect><path d="M8 20h8M12 16v4"></path></svg>
        </div>
        <h3 id="cardMeetingTitle">Toplantı Modülü</h3>
        <div id="cardMeetingDesc" class="muted">Toplantı operasyonları için ana modül.</div>
        <a id="cardMeetingBtn" href="/toplanti-ui">Aç</a>
      </div>
      <div class="card card-interpreter">
        <span class="card-shape"></span>
        <div class="card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M4 5h16v10H9l-5 4V5z"></path><path d="M14 8h3M14 11h3"></path></svg>
        </div>
        <h3 id="cardInterpreterTitle">Tercüman Modülü</h3>
        <div id="cardInterpreterDesc" class="muted">Çeviri oturumları ve canlı online tercüme yönetimi.</div>
        <a id="cardInterpreterBtn" href="/tercuman-ui">Aç</a>
      </div>
      <div class="card card-transport">
        <span class="card-shape"></span>
        <div class="card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <path fill="currentColor" d="M6.2 7h9.7c1.2 0 2.2.7 2.7 1.8L20 12v4.5c0 .8-.7 1.5-1.5 1.5H17v1a1 1 0 0 1-2 0v-1H9v1a1 1 0 1 1-2 0v-1H5.5c-.8 0-1.5-.7-1.5-1.5V12l1.3-3.2C5.8 7.7 6.9 7 8 7h-1.8z"></path>
            <path fill="#ffffff" d="M8 8.2h7.4c.8 0 1.5.5 1.9 1.2l.8 1.8H7l.7-1.8c.2-.7.8-1.2 1.3-1.2z"></path>
            <rect x="7.1" y="12.6" width="9.8" height="1.1" fill="#ffffff"></rect>
            <circle cx="7.4" cy="16.2" r="1.4" fill="#ffffff"></circle>
            <circle cx="16.6" cy="16.2" r="1.4" fill="#ffffff"></circle>
          </svg>
        </div>
        <h3 id="cardTransferTitle">Ulaşım Modülü</h3>
        <div id="cardTransferDesc" class="muted">Upload/Download, İçeri Aktar/Dışarı Aktar, Uçak Takip ve Araç Takip.</div>
        <a id="cardTransferBtn" href="/transfer-ui">Aç</a>
      </div>
      <div class="card card-announcement">
        <span class="card-shape"></span>
        <div class="card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M4 12h3l7-5v10l-7-5H4z"></path><path d="M14 10h2a3 3 0 0 1 0 6h-2"></path></svg>
        </div>
        <h3 id="cardAnnouncementTitle">Duyurular Modülü</h3>
        <div id="cardAnnouncementDesc" class="muted">Sistem ve operasyon duyurularının yönetimi.</div>
        <a id="cardAnnouncementBtn" href="/duyurular-ui">Aç</a>
      </div>
      <div class="card card-finance">
        <span class="card-shape"></span>
        <div class="card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M4 18h16M7 14l3-3 2 2 5-5"></path><path d="M17 8h2v2"></path></svg>
        </div>
        <h3 id="cardFinanceTitle">Muhasebe - Finans Modülü</h3>
        <div id="cardFinanceDesc" class="muted">Bütçe, tahsilat ve finansal operasyonların yönetimi.</div>
        <a id="cardFinanceBtn" href="/muhasebe-finans-ui">Aç</a>
      </div>
      <div class="card card-admin">
        <span class="card-shape"></span>
        <div class="card-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="3"></circle><path d="M5 21a7 7 0 0 1 14 0"></path><path d="M4 4l2 2M20 4l-2 2"></path></svg>
        </div>
        <h3 id="cardAdminTitle">Yönetici Modülü</h3>
        <div id="cardAdminDesc" class="muted">Raporlar, projeler ve kullanıcı yönetimi ekranları.</div>
        <a id="cardAdminBtn" href="/yonetici-ui">Aç</a>
      </div>
    </div>
  </div>
  <button id="logoutFab" class="logout-fab" type="button">&rarr; Çıkış</button><script>
    const token = localStorage.getItem('access_token') || '';
    const projectBadge = document.getElementById('activeProjectBadge');
    const moduleDomMap = {
      transfer: { navId: 'navTransfer', cardBtnId: 'cardTransferBtn' },
      kayit: { navId: 'navRegister', cardBtnId: 'cardRegisterBtn' },
      konaklama: { navId: 'navHotel', cardBtnId: 'cardHotelBtn' },
      toplanti: { navId: 'navMeeting', cardBtnId: 'cardMeetingBtn' },
      tercuman: { navId: 'navInterpreter', cardBtnId: 'cardInterpreterBtn' },
      muhasebe_finans: { navId: 'navFinance', cardBtnId: 'cardFinanceBtn' },
      duyurular: { navId: 'navAnnouncements', cardBtnId: 'cardAnnouncementBtn' },
      yonetim: { navId: 'linkAdmin', cardBtnId: 'cardAdminBtn' },
    };
    const roleDefaultVisibleModules = (role) => {
      const r = String(role || '').trim().toLowerCase();
      if (r === 'superadmin') return ['transfer', 'kayit', 'konaklama', 'toplanti', 'tercuman', 'muhasebe_finans', 'duyurular', 'yonetim'];
      if (r === 'superadmin_staff' || r === 'tenant_admin' || r === 'tenant_manager') return ['transfer', 'kayit', 'konaklama', 'toplanti', 'tercuman', 'muhasebe_finans', 'duyurular', 'yonetim'];
      if (r === 'supertranslator' || r === 'interpreter') return ['toplanti', 'tercuman'];
      if (r === 'participant') return ['toplanti', 'duyurular'];
      if (r === 'driver' || r === 'greeter' || r === 'supplier_admin') return ['transfer'];
      return ['transfer', 'kayit', 'konaklama', 'toplanti', 'muhasebe_finans', 'duyurular'];
    };
    const setModuleVisible = (moduleKey, visible) => {
      const cfg = moduleDomMap[moduleKey];
      if (!cfg) return;
      const navEl = document.getElementById(cfg.navId);
      if (navEl) navEl.style.display = visible ? '' : 'none';
      const cardBtn = document.getElementById(cfg.cardBtnId);
      if (cardBtn) {
        const card = cardBtn.closest('.card');
        if (card) card.style.display = visible ? '' : 'none';
      }
    };
    const applyVisibleModules = (visibleModules, role) => {
      const fromApi = Array.isArray(visibleModules)
        ? visibleModules
            .map((item) => (typeof item === 'string' ? item : (item && item.key ? String(item.key) : '')))
            .filter((k) => !!k)
        : [];
      const finalKeys = fromApi.length ? fromApi : roleDefaultVisibleModules(role);
      const allowSet = new Set(finalKeys);
      Object.keys(moduleDomMap).forEach((k) => setModuleVisible(k, allowSet.has(k)));
      const adminMenu = document.querySelector('.admin-menu');
      if (adminMenu) adminMenu.style.display = allowSet.has('yonetim') ? '' : 'none';
      const adminLinks = document.querySelectorAll('.admin-menu .links a');
      adminLinks.forEach((el) => { el.style.display = allowSet.has('yonetim') ? '' : 'none'; });
    };
    const ensureActiveProject = async () => {
      if (!token) { window.location.href = '/'; return; }
      try {
        const res = await fetch('/auth/me', { headers: { Authorization: `Bearer ${token}` } });
        const me = await res.json();
        if (!res.ok) { const uiLang = localStorage.getItem('ui_lang') || ''; localStorage.clear(); sessionStorage.clear(); if (uiLang) localStorage.setItem('ui_lang', uiLang); window.location.href = '/'; return; }
        const role = String(me.role || '').trim().toLowerCase();
        applyVisibleModules(me.visible_modules, role);
        if (!me.active_project_id && role !== 'superadmin') { window.location.href = '/project-select-ui'; return; }
        if (projectBadge) {
          const pName = me.active_project_name || (role === 'superadmin' ? 'Yönetim Modu' : '-');
          const pCode = me.active_project_code || (role === 'superadmin' ? 'PROJESIZ' : '-');
          projectBadge.textContent = `AKTİF PROJE: ${pName} (${pCode})`;
        }
      } catch (_) {
        window.location.href = '/';
      }
    };
    ensureActiveProject();
    const i18n = {
      tr: {
        navHome: "Ana Sayfa",
        titleModules: "MODÜLLER",
        navTransfer: "Ulaşım Modülü",
        navRegister: "Kayıt Modülü",
        navHotel: "Konaklama Modülü",
        navMeeting: "Toplantı Modülü",
        navInterpreter: "Tercüman Modülü",
        navFinance: "Muhasebe - Finans Modülü",
        linkReports: "Raporlar",
        linkProjects: "Projeler",
        linkUsers: "Kullanıcılar",
        cardTransferTitle: "Ulaşım Modülü",
        cardTransferDesc: "Upload/Download, İçeri Aktar/Dışarı Aktar, Uçak Takip ve Araç Takip.",
        cardTransferBtn: "Aç",
        cardRegisterTitle: "Kayıt Modülü",
        cardRegisterDesc: "Ana modül: kişi kartlarının yönetildiği alt modüller.",
        cardRegisterBtn: "Aç",
        cardHotelTitle: "Konaklama Modülü",
        cardHotelDesc: "Konaklama operasyonları için ana modül.",
        cardHotelBtn: "Aç",
        cardMeetingTitle: "Toplantı Modülü",
        cardMeetingDesc: "Toplantı operasyonları için ana modül.",
        cardMeetingBtn: "Aç",
        cardInterpreterTitle: "Tercüman Modülü",
        cardInterpreterDesc: "Çeviri oturumları ve canlı online tercüme yönetimi.",
        cardInterpreterBtn: "Aç",
        cardFinanceTitle: "Muhasebe - Finans Modülü",
        cardFinanceDesc: "Bütçe, tahsilat ve finansal operasyonların yönetimi.",
        cardFinanceBtn: "Aç",
        cardAdminTitle: "Yönetici Modülü",
        cardAdminDesc: "Raporlar, projeler ve kullanıcı yönetimi ekranları.",
        cardAdminBtn: "Aç",
        cardAnnouncementTitle: "Duyurular Modülü",
        cardAnnouncementDesc: "Sistem ve operasyon duyurularının yönetimi.",
        cardAnnouncementBtn: "Aç"
      },
      en: {
        navHome: "Main Home",
        titleModules: "MODULES",
        navTransfer: "Transport Module",
        navRegister: "Registration Module",
        navHotel: "Accommodation Module",
        navMeeting: "Meeting Module",
        navInterpreter: "Interpreter Module",
        navFinance: "Accounting - Finance Module",
        linkReports: "Reports",
        linkProjects: "Projects",
        linkUsers: "Users",
        cardTransferTitle: "Transport Module",
        cardTransferDesc: "Upload/Download, İçeri Aktar/Dışarı Aktar, Flight Tracking and Vehicle Tracking.",
        cardTransferBtn: "Open",
        cardRegisterTitle: "Registration Module",
        cardRegisterDesc: "Main module for person-card based sub-modules.",
        cardRegisterBtn: "Open",
        cardHotelTitle: "Accommodation Module",
        cardHotelDesc: "Main module for accommodation operations.",
        cardHotelBtn: "Open",
        cardMeetingTitle: "Meeting Module",
        cardMeetingDesc: "Main module for meeting operations.",
        cardMeetingBtn: "Open",
        cardInterpreterTitle: "Interpreter Module",
        cardInterpreterDesc: "Translation sessions and live online interpretation management.",
        cardInterpreterBtn: "Open",
        cardFinanceTitle: "Accounting - Finance Module",
        cardFinanceDesc: "Management of budget, collection and financial operations.",
        cardFinanceBtn: "Open",
        cardAdminTitle: "Admin Module",
        cardAdminDesc: "Screens for reports, projects and user management.",
        cardAdminBtn: "Open",
        cardAnnouncementTitle: "Announcements Module",
        cardAnnouncementDesc: "Management of system and operation announcements.",
        cardAnnouncementBtn: "Open"
      },
      es: {
        navHome: "Inicio",
        titleModules: "MÓDULOS",
        navTransfer: "Módulo de Transporte",
        navRegister: "Módulo de Registro",
        navHotel: "Módulo de Alojamiento",
        navMeeting: "Módulo de Reunión",
        navFinance: "Módulo de Finanzas",
        linkReports: "Informes",
        linkProjects: "Proyectos",
        linkUsers: "Usuarios",
        cardTransferTitle: "Módulo de Transporte",
        cardTransferDesc: "Carga/Descarga, İçeri Aktar/Dışarı Aktar, Seguimiento de Vuelo y Vehículo.",
        cardTransferBtn: "Abrir",
        cardRegisterTitle: "Módulo de Registro",
        cardRegisterDesc: "Módulo principal para submódulos de tarjetas de persona.",
        cardRegisterBtn: "Abrir",
        cardHotelTitle: "Módulo de Alojamiento",
        cardHotelDesc: "Módulo principal para operaciones de alojamiento.",
        cardHotelBtn: "Abrir",
        cardMeetingTitle: "Módulo de Reunión",
        cardMeetingDesc: "Módulo principal para operaciones de reunión.",
        cardMeetingBtn: "Abrir",
        cardFinanceTitle: "Módulo de Finanzas",
        cardFinanceDesc: "Gestión de presupuesto, cobros y operaciones financieras.",
        cardFinanceBtn: "Abrir",
        cardAdminTitle: "Módulo de Administración",
        cardAdminDesc: "Pantallas de informes, proyectos y gestión de usuarios.",
        cardAdminBtn: "Abrir",
        cardAnnouncementTitle: "Módulo de Anuncios",
        cardAnnouncementDesc: "Gestión de anuncios del sistema y de operaciones.",
        cardAnnouncementBtn: "Abrir"
      },
      ar: {
        navHome: "????????",
        titleModules: "???????",
        navTransfer: "???? ?????????",
        navRegister: "???? ???????",
        navHotel: "???? ???????",
        navMeeting: "???? ??????????",
        navFinance: "???? ???????? ????????",
        linkReports: "????????",
        linkProjects: "????????",
        linkUsers: "??????????",
        cardTransferTitle: "???? ?????????",
        cardTransferDesc: "???/?????? ???????/?????? ???? ??????? ?????????.",
        cardTransferBtn: "???",
        cardRegisterTitle: "???? ???????",
        cardRegisterDesc: "?????? ???????? ??????? ??????? ??????? ???????.",
        cardRegisterBtn: "???",
        cardHotelTitle: "???? ???????",
        cardHotelDesc: "?????? ???????? ??????? ???????.",
        cardHotelBtn: "???",
        cardMeetingTitle: "???? ??????????",
        cardMeetingDesc: "?????? ???????? ??????? ??????????.",
        cardMeetingBtn: "???",
        cardFinanceTitle: "???? ???????? ????????",
        cardFinanceDesc: "????? ????????? ???????? ????????? ???????.",
        cardFinanceBtn: "???",
        cardAdminTitle: "???? ???????",
        cardAdminDesc: "????? ???????? ????????? ?????? ??????????.",
        cardAdminBtn: "???",
        cardAnnouncementTitle: "???? ?????????",
        cardAnnouncementDesc: "????? ??????? ?????? ?????????.",
        cardAnnouncementBtn: "???"
      },
      it: {
        navHome: "Home",
        titleModules: "MODULI",
        navTransfer: "Modulo Trasporto",
        navRegister: "Modulo Registrazione",
        navHotel: "Modulo Alloggio",
        navMeeting: "Modulo Riunione",
        navFinance: "Modulo Contabilità - Finanza",
        linkReports: "Report",
        linkProjects: "Progetti",
        linkUsers: "Utenti",
        cardTransferTitle: "Modulo Trasporto",
        cardTransferDesc: "Upload/Download, İçeri Aktar/Dışarı Aktar, Tracciamento Voli e Veicoli.",
        cardTransferBtn: "Apri",
        cardRegisterTitle: "Modulo Registrazione",
        cardRegisterDesc: "Modulo principale per i sottomoduli delle schede persona.",
        cardRegisterBtn: "Apri",
        cardHotelTitle: "Modulo Alloggio",
        cardHotelDesc: "Modulo principale per operazioni di alloggio.",
        cardHotelBtn: "Apri",
        cardMeetingTitle: "Modulo Riunione",
        cardMeetingDesc: "Modulo principale per operazioni di riunione.",
        cardMeetingBtn: "Apri",
        cardFinanceTitle: "Modulo Contabilità - Finanza",
        cardFinanceDesc: "Gestione di budget, incassi e operazioni finanziarie.",
        cardFinanceBtn: "Apri",
        cardAdminTitle: "Modulo Admin",
        cardAdminDesc: "Schermate per report, progetti e gestione utenti.",
        cardAdminBtn: "Apri",
        cardAnnouncementTitle: "Modulo Annunci",
        cardAnnouncementDesc: "Gestione degli annunci di sistema e operativi.",
        cardAnnouncementBtn: "Apri"
      },
      ru: {
        navHome: "???????",
        titleModules: "??????",
        navTransfer: "?????? ?????????",
        navRegister: "?????? ???????????",
        navHotel: "?????? ??????????",
        navMeeting: "?????? ??????",
        navFinance: "?????? ??????? - ???????????",
        linkReports: "??????",
        linkProjects: "???????",
        linkUsers: "????????????",
        cardTransferTitle: "?????? ?????????",
        cardTransferDesc: "????????/????????, ??????/???????, ???????????? ?????? ? ????.",
        cardTransferBtn: "???????",
        cardRegisterTitle: "?????? ???????????",
        cardRegisterDesc: "??????? ?????? ??? ?????????? ???????? ??????????.",
        cardRegisterBtn: "???????",
        cardHotelTitle: "?????? ??????????",
        cardHotelDesc: "??????? ?????? ???????? ??????????.",
        cardHotelBtn: "???????",
        cardMeetingTitle: "?????? ??????",
        cardMeetingDesc: "??????? ?????? ???????? ??????.",
        cardMeetingBtn: "???????",
        cardFinanceTitle: "?????? ??????? - ???????????",
        cardFinanceDesc: "?????????? ????????, ?????? ? ??????????? ??????????.",
        cardFinanceBtn: "???????",
        cardAdminTitle: "?????? ?????????????????",
        cardAdminDesc: "?????? ???????, ???????? ? ?????????? ??????????????.",
        cardAdminBtn: "???????",
        cardAnnouncementTitle: "?????? ??????????",
        cardAnnouncementDesc: "?????????? ?????????? ? ????????????? ????????????.",
        cardAnnouncementBtn: "???????"
      }
    };
    const langSelect = document.getElementById("langSelect");
    const keys = Object.keys(i18n.tr);
    const applyLang = (lang) => {
      const pack = i18n[lang] || i18n.en || i18n.tr;
      keys.forEach((k) => {
        const el = document.getElementById(k);
        if (!el) return;
        const text = pack[k] ?? i18n.tr[k] ?? i18n.en[k] ?? "";
        el.textContent = text;
      });
      document.documentElement.lang = lang;
      document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
      localStorage.setItem("ui_lang", lang);
      if (langSelect) langSelect.value = lang;
    };
    const initialLang = localStorage.getItem("ui_lang") || "tr";
    applyLang(initialLang);
    if (langSelect) langSelect.addEventListener("change", () => applyLang(langSelect.value));
    const logoutFab = document.getElementById("logoutFab");
    if (logoutFab) {
      logoutFab.addEventListener("click", () => {
        const uiLang = localStorage.getItem("ui_lang") || "";
        localStorage.clear();
        sessionStorage.clear();
        if (uiLang) localStorage.setItem("ui_lang", uiLang);
        window.location.href = "/";
      });
    }
  </script>
  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""


@app.get("/user-settings-ui", response_class=HTMLResponse)
def user_settings_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kullanıcı Ayarları</title>
  <style>
    body { margin:0; font-family: Arial, sans-serif; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color:#1c2635; }
    .wrap { max-width: 900px; margin: 0 auto; padding: 16px; }
    .head { background:#0A1024; color:#fff; border-radius:10px; padding:10px 12px; margin-bottom:12px; display:flex; justify-content:space-between; }
    .head a { color:#fff; text-decoration:none; margin-left:10px; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .muted { color:#5c6b82; font-size:13px; margin-top:8px; }
    select { padding:9px; border:1px solid #cfd9e8; border-radius:8px; min-width: 320px; }
    button { background:#2b7fff; color:#fff; border:0; border-radius:8px; padding:9px 12px; cursor:pointer; }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
    .overlay { position: fixed; inset: 0; background: rgba(10,16,36,0.45); display: none; align-items: center; justify-content: center; z-index: 1200; }
    .overlay .card { background: #fff; border: 1px solid #d8e0ee; border-radius: 12px; min-width: 320px; padding: 16px; text-align: center; box-shadow: 0 12px 30px rgba(10,16,36,0.22); }
    .spinner { width: 28px; height: 28px; border: 3px solid #d9e5fb; border-top-color: #2b7fff; border-radius: 50%; margin: 0 auto 10px auto; animation: spin 1s linear infinite; }
    .popup { position: fixed; inset: 0; background: rgba(10,16,36,0.45); display: none; align-items: center; justify-content: center; z-index: 1250; }
    .popup .card { background: #fff; border: 1px solid #d8e0ee; border-radius: 12px; min-width: 360px; max-width: 92vw; padding: 16px; box-shadow: 0 12px 30px rgba(10,16,36,0.22); }
    .popup .title { font-size: 15px; font-weight: 700; margin-bottom: 8px; }
    .popup .actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
    .btn-small { padding: 6px 10px; font-size: 12px; border-radius: 6px; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <strong>KULLANICI AYARLARI</strong>
      <div><a href="/modules-ui">Modüller</a><a href="/transfer-ui">Transfer</a></div>
    </div>
    <div class="box">
      <h3 style="margin-top:0;">Aktif Proje</h3>
      <div class="muted">Buradan proje değiştirmedikçe tüm modüllerde aynı proje kullanılacaktır.</div>
      <div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
        <select id="projectSelect"><option value="">Proje Seçiniz</option></select>
        <button id="saveBtn" type="button">Kaydet</button>
      </div>
      <div id="summary" class="muted"></div>
    </div>
  </div>
  <script>
    const token = localStorage.getItem('access_token') || '';
    const projectSelect = document.getElementById('projectSelect');
    const saveBtn = document.getElementById('saveBtn');
    const summary = document.getElementById('summary');
    const headers = () => ({ Authorization: `Bearer ${token}` });
    const load = async () => {
      if (!token) { window.location.href = '/'; return; }
      const meRes = await fetch('/auth/me', { headers: headers() });
      const me = await meRes.json();
      if (!meRes.ok) { const uiLang = localStorage.getItem('ui_lang') || ''; localStorage.clear(); sessionStorage.clear(); if (uiLang) localStorage.setItem('ui_lang', uiLang); window.location.href = '/'; return; }
      const res = await fetch('/projects', { headers: headers() });
      const data = await res.json();
      if (!res.ok) { summary.textContent = data.detail || 'Projeler alınamadı.'; return; }
      const arr = Array.isArray(data) ? data : [];
      arr.forEach((p) => {
        const op = document.createElement('option');
        op.value = String(p.id);
        op.textContent = `${p.name} | ${p.city} | ${p.operation_code}`;
        projectSelect.appendChild(op);
      });
      if (me.active_project_id) projectSelect.value = String(me.active_project_id);
      summary.textContent = me.active_project_id ? `Mevcut aktif proje: ${me.active_project_name || '-'}` : 'Aktif proje seçilmemiş.';
    };
    saveBtn.addEventListener('click', async () => {
      const val = projectSelect.value;
      if (!val) { summary.textContent = 'Önce proje seçiniz.'; return; }
      const res = await fetch('/auth/active-project', {
        method: 'PUT',
        headers: { ...headers(), 'Content-Type':'application/json' },
        body: JSON.stringify({ project_id: parseInt(val, 10) })
      });
      const data = await res.json();
      if (!res.ok) { summary.textContent = data.detail || 'Kaydetme hatası'; return; }
      summary.textContent = `Aktif proje güncellendi: ${data.active_project_name}`;
    });
    load();
  </script>
  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""


@app.get("/transfer-ui", response_class=HTMLResponse)
def transfer_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Ulaşım Modülü</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { padding: 14px; }
    .head {
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;
      background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; position:relative;
    }
    .head-left { display:flex; align-items:center; gap:12px; }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn {
      background: rgba(255,255,255,0.18); color:#fff; text-decoration:none;
      border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px;
    }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .tabs { display: flex; gap: 8px; flex-wrap: wrap; }
    .tab { background: #2b7fff; color: #fff; border: 0; border-radius: 8px; padding: 8px 12px; cursor: pointer; }
    .tab.alt { background: #5c6b82; }
    .frame { width: 100%; height: calc(100vh - 168px); border: 1px solid #dde4ef; border-radius: 10px; background: #fff; }
    .head-right { display:flex; flex-direction:row; align-items:center; gap:8px; margin-right:68px; }
    .right-panel {
      border:1px solid rgba(159,216,255,0.45);
      border-radius:8px;
      padding:4px 7px;
      background:rgba(8,23,56,0.20);
    }
    .links a { margin-right: 6px; color: #9FD8FF; text-decoration: none; font-size: 11px; font-weight: 600; }
    .admin-menu { position:relative; }
    .admin-btn { display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF; border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600; text-decoration:none; cursor:pointer; white-space:nowrap; }
    .admin-menu .links { display:none; position:absolute; top:100%; margin-top:2px; right:0; min-width:150px; background:#0A1024; border:1px solid rgba(159,216,255,0.35); border-radius:8px; padding:6px; z-index:50; }
    .admin-menu .links a { display:block; margin:0; padding:5px 6px; color:#9FD8FF; border-radius:6px; }
    .admin-menu .links a:hover { background:rgba(159,216,255,0.12); }
    .admin-menu:hover .links, .admin-menu:focus-within .links, .admin-menu.open .links { display:block; }
    .project-badge {
      display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF;
      border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600;
      letter-spacing:0.15px; white-space:nowrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08);
    }
    .lang-mini { position:absolute; top:4px; right:8px; font-size:11px; padding:2px 4px; border-radius:6px; border:0; }
    .logout-fab {
      position: fixed;
      right: 18px;
      bottom: 8px;
      z-index: 1200;
      border: 0;
      border-radius: 999px;
      background: #0A1024;
      color: #fff;
      padding: 10px 14px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 8px 20px rgba(0,0,0,0.22);
    }
    .logout-fab:hover { background:#121a34; }
    .footer-brand { position: fixed; left: 0; right: 0; bottom: 0; height: 54px; background: #0A1024; display: flex; align-items: center; padding-left: 12px; z-index: 998; overflow: hidden; }
    .footer-brand img { height: 150%; width: auto; display: block; object-fit: cover; object-position: center; clip-path: inset(0 3% 0 0); }
    .logo-reg { color: #fff; font-size: 12px; line-height: 1; margin-left: 0; font-weight: 700; position: relative; left: -26px; transform: translateY(-45%); }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="head-left module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn" href="/kayit-ui" accesskey="2" title="Kısayol: Alt+2">Kayıt Modülü</a>
        <a class="m-btn" href="/konaklama-ui" accesskey="3" title="Kısayol: Alt+3">Konaklama Modülü</a>
        <a class="m-btn" href="/toplanti-ui" accesskey="4" title="Kısayol: Alt+4">Toplantı Modülü</a>
        <a class="m-btn active" href="/transfer-ui" accesskey="1" title="Kısayol: Alt+1">Ulaşım Modülü</a>
        <a class="m-btn" href="/muhasebe-finans-ui" accesskey="5" title="Kısayol: Alt+5">Muhasebe - Finans Modülü</a>
        <a class="m-btn" href="/duyurular-ui" accesskey="6" title="Kısayol: Alt+6">Duyurular</a>
      </div>
      <div class="head-right">
        <div class="admin-menu">
          <a id="linkAdmin" class="admin-btn" href="/yonetici-ui">Yönetici Modülü</a>
          <div class="links">
            <a id="linkReports" href="/reports-ui">Raporlar</a>
            <a href="/duyurular-ui">Duyurular</a>
            <a id="linkProjects" href="/projects-ui">Projeler</a>
            <a id="linkUsers" href="/users-ui">Kullanıcılar</a>
          </div>
        </div>
        <div class="right-panel">
          <span id="activeProjectBadge" class="project-badge">AKTİF PROJE: -</span>
        </div>
      </div>
      <select id="langSelect" class="lang-mini">
        <option value="tr">TR</option>
        <option value="en">EN</option>
        <option value="es">ES</option>
        <option value="ar">??</option>
        <option value="it">IT</option>
        <option value="ru">??</option>
      </select>
    </div>
    <div class="tabs">
      <button id="tabTransferList" class="tab" data-url="/transfer-list-ui">Transfer Listesi</button>
      <button id="tabTicket" class="tab alt" data-url="/bilet-ui">Bilet</button>
      <button id="tabUpload" class="tab alt" data-url="/upload-ui">Upload - Download</button>
      <button id="tabFlight" class="tab alt" data-url="/ucak-ui">Uçak Takip</button>
      <button id="tabVehicle" class="tab alt" data-url="/supplier-ui">Araç Takip</button>
    </div>
    <iframe id="moduleFrame" class="frame" src="/transfer-list-ui"></iframe>
  </div>
  <button id="logoutFab" class="logout-fab" type="button">&rarr; Çıkış</button><script>
    const frame = document.getElementById('moduleFrame');
    const token = localStorage.getItem('access_token') || '';
    const projectBadge = document.getElementById('activeProjectBadge');
    const tabs = Array.from(document.querySelectorAll('.tab'));
    const i18n = {
      tr: {
        titleTransfer: "TRANSFER MODÜLÜ",
        linkModules: "Modüller",
        linkHome: "Ana Sayfa",
        linkProjects: "Projeler",
        linkUsers: "Kullanıcılar",
        mainTransfer: "Ulaşım Modülü",
        mainRegister: "Kayıt Modülü",
        mainHotel: "Konaklama Modülü",
        mainMeeting: "Toplantı Modülü",
        tabTransferList: "Transfer Listesi",
        tabTicket: "Bilet",
        tabUpload: "Upload - Download",
        tabImportExport: "Transfer List",
        tabFlight: "Uçak Takip",
        tabVehicle: "Araç Takip"
      },
      en: {
        titleTransfer: "TRANSFER MODULE",
        linkModules: "Modules",
        linkHome: "Home",
        linkProjects: "Projects",
        linkUsers: "Users",
        mainTransfer: "Transport Module",
        mainRegister: "Registration Module",
        mainHotel: "Accommodation Module",
        mainMeeting: "Meeting Module",
        tabTransferList: "Transfer List",
        tabTicket: "Ticket",
        tabUpload: "Upload - Download",
        tabImportExport: "Transfer List",
        tabFlight: "Flight Tracking",
        tabVehicle: "Vehicle Tracking"
      },
      es: {
        titleTransfer: "MÓDULO DE TRANSFER",
        linkModules: "Módulos",
        linkHome: "Inicio",
        linkProjects: "Proyectos",
        linkUsers: "Usuarios",
        mainTransfer: "Módulo de Transporte",
        mainRegister: "Módulo de Registro",
        mainHotel: "Módulo de Alojamiento",
        mainMeeting: "Módulo de Reunión",
        tabTransferList: "Lista de Transfer",
        tabTicket: "Billete",
        tabUpload: "Carga - Descarga",
        tabImportExport: "Lista Transfer",
        tabFlight: "Seguimiento de Vuelo",
        tabVehicle: "Seguimiento de Vehículo"
      },
      ar: {
        titleTransfer: "???? ?????????",
        linkModules: "???????",
        linkHome: "????????",
        linkProjects: "????????",
        linkUsers: "??????????",
        mainTransfer: "???? ?????????",
        mainRegister: "???? ???????",
        mainHotel: "???? ???????",
        mainMeeting: "???? ??????????",
        tabTransferList: "????? ?????",
        tabTicket: "???????",
        tabUpload: "??? - ?????",
        tabImportExport: "????? ?????",
        tabFlight: "???? ???????",
        tabVehicle: "???? ????????"
      },
      it: {
        titleTransfer: "MODULO TRANSFER",
        linkModules: "Moduli",
        linkHome: "Home",
        linkProjects: "Progetti",
        linkUsers: "Utenti",
        mainTransfer: "Modulo Trasporto",
        mainRegister: "Modulo Registrazione",
        mainHotel: "Modulo Alloggio",
        mainMeeting: "Modulo Riunione",
        tabTransferList: "Lista Transfer",
        tabTicket: "Biglietto",
        tabUpload: "Upload - Download",
        tabImportExport: "Lista Transfer",
        tabFlight: "Tracciamento Voli",
        tabVehicle: "Tracciamento Veicoli"
      },
      ru: {
        titleTransfer: "?????? ????????",
        linkModules: "??????",
        linkHome: "???????",
        linkProjects: "???????",
        linkUsers: "????????????",
        mainTransfer: "?????? ?????????",
        mainRegister: "?????? ???????????",
        mainHotel: "?????? ??????????",
        mainMeeting: "?????? ??????",
        tabTransferList: "?????? ??????????",
        tabTicket: "?????",
        tabUpload: "???????? - ????????",
        tabImportExport: "?????? ??????????",
        tabFlight: "???????????? ??????",
        tabVehicle: "???????????? ????"
      }
    };
    const langSelect = document.getElementById("langSelect");
    const keys = Object.keys(i18n.tr);
    const applyLang = (lang) => {
      const pack = i18n[lang] || i18n.en || i18n.tr;
      keys.forEach((k) => {
        const el = document.getElementById(k);
        if (el) el.textContent = pack[k];
      });
      document.documentElement.lang = lang;
      document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
      localStorage.setItem("ui_lang", lang);
      langSelect.value = lang;
    };
    const initialLang = localStorage.getItem("ui_lang") || "tr";
    applyLang(initialLang);
    langSelect.addEventListener("change", () => applyLang(langSelect.value));
    const setActive = (btn) => {
      tabs.forEach(x => { x.classList.remove('tab'); x.classList.add('tab','alt'); });
      btn.classList.remove('alt');
    };
    tabs.forEach(btn => {
      btn.addEventListener('click', () => {
        frame.src = btn.getAttribute('data-url');
        setActive(btn);
      });
    });
    const logoutFab = document.getElementById("logoutFab");
    if (logoutFab) {
      logoutFab.addEventListener("click", () => {
        const uiLang = localStorage.getItem("ui_lang") || "";
        localStorage.clear();
        sessionStorage.clear();
        if (uiLang) localStorage.setItem("ui_lang", uiLang);
        window.location.href = "/";
      });
    }
    (async () => {
      if (!token || !projectBadge) return;
      try {
        const res = await fetch('/auth/me', { headers: { Authorization: `Bearer ${token}` } });
        const me = await res.json();
        if (!res.ok || !me) return;
        const pName = me.active_project_name || '-';
        const pCode = me.active_project_code || '-';
        projectBadge.textContent = `AKTİF PROJE: ${pName} (${pCode})`;
      } catch (_) {}
    })();
  </script>
  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""


@app.get("/import-export-ui", response_class=HTMLResponse)
def import_export_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Transfer List</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 18px; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .muted { color:#5c6b82; font-size:13px; margin-top:6px; }
    .row { display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }
    .btn { background:#2b7fff; color:#fff; border:0; border-radius:8px; padding:8px 12px; text-decoration:none; }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
</head>
<body>
  <div class="box">
    <h3>Transfer List</h3>
    <div class="muted">Bu alanda İçeri Aktar ve Dışarı Aktar işlemleri için kısayol butonları yer alır.</div>
    <div class="row">
      <a class="btn" href="/upload-ui" target="_top">İçeri Aktar</a>
      <a class="btn" href="/upload-ui" target="_top">Dışarı Aktar</a>
    </div>
  </div>
</body>
</html>
"""


@app.get("/karşılama-ui", response_class=HTMLResponse)
def karşılama_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Karşılama Modülü</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 18px; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .subtabs { display:flex; gap:8px; flex-wrap:wrap; margin:10px 0 8px; }
    .subtab {
      display:inline-flex; align-items:center; justify-content:center;
      border:0; border-radius:8px; padding:8px 12px; cursor:pointer;
      background:#2b7fff; color:#fff; font-size:12px; font-weight:700; text-decoration:none;
    }
    .subtab.alt { background:#5c6b82; }
    .muted { color:#5c6b82; font-size:13px; }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
</head>
<body>
  <div class="box">
    <h3>Karşılama Modülü</h3>
    <div class="muted">Karsilama akislarini /supplier-ui icindeki transfer aksiyon adimlarindan takip edebilirsiniz.</div>
    <div class="muted" style="margin-top:8px;">Aksiyonlar: karsilamaya_gectim, karsiladim, misafiri_bekliyorum, misafiri_aldim, misafiri_biraktim</div>
  </div>
</body>
</html>
"""


def _parse_ticket_budget(data_obj: dict | None) -> float | None:
    if not isinstance(data_obj, dict):
        return None
    candidates = [
        data_obj.get("bilet_limiti"),
        data_obj.get("ticket_budget"),
        data_obj.get("f_bilet_limiti"),
        data_obj.get("bilet_butcesi"),
    ]
    for raw in candidates:
        if raw is None:
            continue
        txt = str(raw).strip().replace(",", ".")
        if not txt:
            continue
        try:
            v = float(txt)
            if v >= 0:
                return v
        except Exception:
            continue
    return None


def require_transfer_operator(current_user: User = Depends(require_auth)) -> User:
    if role_level(current_user.role) < role_level("supplier_admin"):
        raise HTTPException(status_code=403, detail="Transfer operator role required")
    return current_user


def _driver_panel_token_hash(raw_token: str) -> str:
    return hashlib.sha256(str(raw_token or "").encode("utf-8")).hexdigest()


def _issue_driver_panel_token(
    db: Session,
    *,
    tenant_id: int,
    project_id: int | None,
    supplier_company_id: int | None,
    panel_role: str,
    staff_id: int,
    created_by_user_id: int | None,
    ttl_minutes: int,
) -> tuple[str, DriverPanelToken]:
    role = str(panel_role or "").strip().lower()
    if role not in {"driver", "greeter"}:
        raise HTTPException(status_code=400, detail="panel_role must be driver or greeter")
    token_raw = secrets.token_urlsafe(32)
    row = DriverPanelToken(
        token_hash=_driver_panel_token_hash(token_raw),
        tenant_id=int(tenant_id),
        project_id=int(project_id) if project_id is not None else None,
        supplier_company_id=int(supplier_company_id) if supplier_company_id is not None else None,
        driver_staff_id=int(staff_id) if role == "driver" else int(staff_id),
        greeter_staff_id=int(staff_id) if role == "greeter" else None,
        panel_role=role,
        created_by_user_id=int(created_by_user_id) if created_by_user_id is not None else None,
        is_active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=max(5, int(ttl_minutes))),
    )
    db.add(row)
    db.flush()
    return token_raw, row


def _get_driver_panel_token_row(db: Session, raw_token: str | None) -> DriverPanelToken | None:
    token_hash = _driver_panel_token_hash(str(raw_token or "").strip())
    if not token_hash:
        return None
    now = datetime.now(timezone.utc)
    return (
        db.query(DriverPanelToken)
        .filter(
            DriverPanelToken.token_hash == token_hash,
            DriverPanelToken.is_active.is_(True),
            DriverPanelToken.expires_at > now,
        )
        .first()
    )


def _driver_panel_transfers_query(db: Session, token_row: DriverPanelToken):
    role = str(token_row.panel_role or "driver").strip().lower()
    if role == "greeter":
        q = db.query(Transfer).filter(
            Transfer.tenant_id == int(token_row.tenant_id or 0),
            Transfer.greeter_staff_id == int(token_row.greeter_staff_id or token_row.driver_staff_id or 0),
        )
    else:
        q = db.query(Transfer).filter(
            Transfer.tenant_id == int(token_row.tenant_id or 0),
            Transfer.driver_staff_id == int(token_row.driver_staff_id or 0),
        )
    if token_row.project_id is not None:
        q = q.filter(Transfer.project_id == int(token_row.project_id))
    if token_row.supplier_company_id is not None:
        q = q.filter(Transfer.supplier_company_id == int(token_row.supplier_company_id))
    return q


def _transfer_sms_status_text(action: str | None) -> str:
    key = str(action or "").strip().lower()
    mapping = {
        "bekliyorum": "Sorumlu personelimiz sizi bekliyor.",
        "aldim": "Sorumlu personelimiz sizi aldı.",
        "biraktim": "Sorumlu personelimiz sizi bıraktı.",
        "karsilamaya_gectim": "Sürücünüz karşılama noktasına geçmiştir.",
        "karsiladim": "Sürücünüz sizi karşıladı.",
        "misafiri_bekliyorum": "Sürücünüz sizi bekliyor.",
        "misafiri_aldim": "Transferiniz başladı, sürücünüz sizi araca aldı.",
        "misafiri_biraktim": "Transferiniz tamamlandı, varış noktasına bırakıldınız.",
    }
    return mapping.get(key, f"Transfer durumunuz güncellendi: {key or '-'}")


def _lookup_kayit_phone_by_name(db: Session, tenant_id: int, project_id: int | None, full_name: str) -> str | None:
    n = str(full_name or "").strip().lower()
    if not n:
        return None
    if project_id is not None:
        row = db.execute(
            text(
                "SELECT data FROM module_data "
                "WHERE module_name='kayit' AND tenant_id=:tenant_id AND project_id=:project_id "
                "AND ("
                "lower(trim(coalesce(data->>'isim','') || ' ' || coalesce(data->>'soyisim',''))) = :n "
                "OR lower(trim(coalesce(data->>'f_isim','') || ' ' || coalesce(data->>'f_soyisim',''))) = :n "
                "OR lower(trim(coalesce(data->>'full_name',''))) = :n "
                "OR lower(trim(coalesce(data->>'ad_soyad',''))) = :n "
                ") "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"tenant_id": int(tenant_id), "project_id": int(project_id), "n": n},
        ).fetchone()
    else:
        row = db.execute(
            text(
                "SELECT data FROM module_data "
                "WHERE module_name='kayit' AND tenant_id=:tenant_id "
                "AND ("
                "lower(trim(coalesce(data->>'isim','') || ' ' || coalesce(data->>'soyisim',''))) = :n "
                "OR lower(trim(coalesce(data->>'f_isim','') || ' ' || coalesce(data->>'f_soyisim',''))) = :n "
                "OR lower(trim(coalesce(data->>'full_name',''))) = :n "
                "OR lower(trim(coalesce(data->>'ad_soyad',''))) = :n "
                ") "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"tenant_id": int(tenant_id), "n": n},
        ).fetchone()
    if not row:
        return None
    data = row[0] if isinstance(row[0], dict) else {}
    phone = str(data.get("telefon") or data.get("f_telefon") or "").strip()
    return phone or None


def _queue_driver_group_sms(db: Session, base_transfer: Transfer, action_key: str | None) -> int:
    if not base_transfer:
        return 0
    group_q = db.query(Transfer).filter(
        Transfer.tenant_id == int(base_transfer.tenant_id or 0),
        Transfer.project_id == base_transfer.project_id,
    )
    if str(base_transfer.reservation_code or "").strip():
        group_q = group_q.filter(Transfer.reservation_code == base_transfer.reservation_code)
    elif str(base_transfer.vehicle_code or "").strip() and str(base_transfer.flight_date or "").strip():
        group_q = group_q.filter(
            Transfer.vehicle_code == base_transfer.vehicle_code,
            Transfer.flight_date == base_transfer.flight_date,
        )
    else:
        group_q = group_q.filter(Transfer.id == base_transfer.id)
    members = group_q.order_by(Transfer.id.asc()).all()
    if not members:
        members = [base_transfer]

    queued = 0
    status_text = _transfer_sms_status_text(action_key)
    for idx, tr in enumerate(members, start=1):
        if tr.participant_order_no is None:
            tr.participant_order_no = idx
        person_name = (_normalized_person_name(tr) or tr.passenger_name or "").strip()
        if not person_name:
            continue
        phone = str(tr.participant_phone or "").strip() or None
        if not phone:
            phone = _lookup_kayit_phone_by_name(
                db,
                int(tr.tenant_id or 0),
                int(tr.project_id) if tr.project_id is not None else None,
                person_name,
            )
            if phone:
                tr.participant_phone = phone
        if not phone:
            continue
        msg = (
            f"{idx}. sıradaki {person_name} sayın katılımcımız, {status_text} "
            f"Rezervasyon: {tr.reservation_code or '-'} | Araç: {tr.vehicle_code or '-'}"
        ).strip()
        db.add(
            SupplierSmsQueue(
                tenant_id=int(tr.tenant_id or 0),
                booking_id=None,
                to_phone=phone,
                message=msg,
                status="queued",
                error_message=None,
            )
        )
        queued += 1
    return queued


def _ticket_demo_options() -> list[dict]:
    # Offline/MVP amaçlı statik liste; canlı tarife entegrasyonunda sağlayıcıdan okunacak.
    return [
        {"airline": "Pegasus", "flight_no": "PC 2012", "route": "IST - AYT", "depart_at": "2026-03-12 08:15", "arrive_at": "2026-03-12 09:35", "price": 2450.0, "currency": "TRY"},
        {"airline": "Pegasus", "flight_no": "PC 2018", "route": "SAW - AYT", "depart_at": "2026-03-12 13:40", "arrive_at": "2026-03-12 15:00", "price": 3120.0, "currency": "TRY"},
        {"airline": "AJet", "flight_no": "VF 3041", "route": "ESB - AYT", "depart_at": "2026-03-12 10:10", "arrive_at": "2026-03-12 11:20", "price": 1980.0, "currency": "TRY"},
        {"airline": "AJet", "flight_no": "VF 3079", "route": "SAW - AYT", "depart_at": "2026-03-12 19:25", "arrive_at": "2026-03-12 20:40", "price": 2790.0, "currency": "TRY"},
        {"airline": "THY", "flight_no": "TK 2418", "route": "IST - AYT", "depart_at": "2026-03-12 07:30", "arrive_at": "2026-03-12 08:55", "price": 3650.0, "currency": "TRY"},
        {"airline": "THY", "flight_no": "TK 2436", "route": "IST - AYT", "depart_at": "2026-03-12 16:20", "arrive_at": "2026-03-12 17:45", "price": 4290.0, "currency": "TRY"},
        {"airline": "SunExpress", "flight_no": "XQ 121", "route": "ADB - AYT", "depart_at": "2026-03-12 09:20", "arrive_at": "2026-03-12 10:30", "price": 2190.0, "currency": "TRY"},
        {"airline": "SunExpress", "flight_no": "XQ 125", "route": "ADB - AYT", "depart_at": "2026-03-12 18:05", "arrive_at": "2026-03-12 19:15", "price": 3340.0, "currency": "TRY"},
    ]


@app.get("/ticket-passengers")
def ticket_passengers(
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    scoped_project_id, management_scope = _resolve_project_scope_for_user(db, current_user, project_id)
    if not management_scope and scoped_project_id is None:
        raise HTTPException(status_code=400, detail="Active project required")

    q = db.query(ModuleData).filter(ModuleData.module_name == "kayit")
    if not is_superadmin(current_user):
        q = q.filter(ModuleData.tenant_id == current_user.tenant_id)
    if not management_scope:
        q = q.filter(ModuleData.project_id == scoped_project_id)
    elif scoped_project_id is not None:
        q = q.filter(ModuleData.project_id == scoped_project_id)

    rows = q.order_by(ModuleData.created_at.desc()).limit(2000).all()
    out = []
    for r in rows:
        d = r.data or {}
        if not isinstance(d, dict):
            continue
        isim = (d.get("isim") or d.get("f_isim") or "").strip()
        soyisim = (d.get("soyisim") or d.get("f_soyisim") or "").strip()
        if not isim and not soyisim:
            continue
        budget = _parse_ticket_budget(d)
        out.append(
            {
                "row_id": r.id,
                "full_name": (f"{isim} {soyisim}").strip(),
                "kimlik_no": d.get("kimlik_no") or d.get("f_kimlik") or "",
                "telefon": d.get("telefon") or d.get("f_telefon") or "",
                "mail": d.get("mail") or d.get("f_mail") or "",
                "budget": budget,
                "budget_currency": "TRY",
            }
        )
    return out


@app.get("/ticket-options")
def ticket_options(
    passenger_row_id: int = Query(..., ge=1),
    airline: str | None = Query(default=None),
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    scoped_project_id, management_scope = _resolve_project_scope_for_user(db, current_user, project_id)
    row = db.query(ModuleData).filter(ModuleData.id == passenger_row_id, ModuleData.module_name == "kayit").first()
    if not row:
        raise HTTPException(status_code=404, detail="Participant not found")
    if not is_superadmin(current_user) and row.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="forbidden")
    if not management_scope:
        if scoped_project_id is None or row.project_id != scoped_project_id:
            raise HTTPException(status_code=403, detail="forbidden")
    elif scoped_project_id is not None and row.project_id != scoped_project_id:
        raise HTTPException(status_code=403, detail="forbidden")

    d = row.data or {}
    budget = _parse_ticket_budget(d)
    if budget is None:
        budget = 0.0

    target_airline = str(airline or "").strip().lower()
    all_items = _ticket_demo_options()
    if target_airline:
        all_items = [x for x in all_items if str(x.get("airline") or "").strip().lower() == target_airline]

    visible = [x for x in all_items if float(x.get("price") or 0) <= float(budget)]
    hidden_count = max(0, len(all_items) - len(visible))
    return {
        "passenger_row_id": row.id,
        "budget": budget,
        "currency": "TRY",
        "airline_filter": airline or "",
        "items": visible,
        "hidden_count": hidden_count,
        "total_candidates": len(all_items),
        "source": "demo_static",
    }


@app.get("/bilet-ui", response_class=HTMLResponse)
def bilet_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Bilet</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 16px; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); color: #1c2635; }
    .box { max-width: 1300px; margin: 0 auto; background: #fff; border: 1px solid #dde4ef; border-radius: 12px; padding: 16px; }
    .row { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
    .input, .sel { border:1px solid #cfd9e8; border-radius:8px; padding:8px 10px; font-size:12px; min-width:220px; }
    .btn { border:0; border-radius:8px; background:#2b7fff; color:#fff; padding:8px 12px; cursor:pointer; }
    .btn.alt { background:#5c6b82; }
    table { width:100%; border-collapse: collapse; margin-top:12px; font-size:12px; }
    th, td { border:1px solid #dde4ef; padding:8px; text-align:left; }
    th { background:#f0f5ff; }
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
    .muted { color:#5c6b82; font-size:13px; }
    .badge { display:inline-flex; align-items:center; border:1px solid #b9d4ff; color:#1d4ed8; background:#eff6ff; border-radius:999px; padding:4px 8px; font-size:11px; font-weight:700; }
  </style>
</head>
<body>
  <div class="box">
    <h3 style="margin-top:0;">Bilet</h3>
    <div class="muted">Pegasus, AJet, THY ve SunExpress seçenekleri katılımcı limitine göre listelenir. Limit üstü seçenekler gösterilmez.</div>
    <div class="row">
      <select id="passengerSel" class="sel"></select>
      <select id="airlineSel" class="sel">
        <option value="">Tüm Havayolları</option>
        <option value="Pegasus">Pegasus</option>
        <option value="AJet">AJet</option>
        <option value="THY">THY</option>
        <option value="SunExpress">SunExpress</option>
      </select>
      <button id="loadBtn" class="btn" type="button">Uçuşları Getir</button>
      <button id="refreshBtn" class="btn alt" type="button">Katılımcıları Yenile</button>
      <span class="badge">Demo Veri</span>
    </div>
    <div id="summary" class="muted" style="margin-top:8px;">Yükleniyor...</div>
    <table id="tbl" style="display:none;">
      <thead><tr><th>Havayolu</th><th>Uçuş No</th><th>Rota</th><th>Kalkış</th><th>Varış</th><th>Fiyat</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
  <script>
    const token = localStorage.getItem('access_token') || '';
    const headers = () => token ? ({ Authorization: 'Bearer ' + token }) : ({});
    const passengerSel = document.getElementById('passengerSel');
    const airlineSel = document.getElementById('airlineSel');
    const loadBtn = document.getElementById('loadBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    const summary = document.getElementById('summary');
    const tbl = document.getElementById('tbl');
    const tbody = tbl.querySelector('tbody');
    let passengers = [];
    let activeProjectId = null;
    const esc = (v) => String(v || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

    const loadPassengers = async () => {
      if (!token) { summary.textContent = 'Oturum yok, giriş yapınız.'; return; }
      const meRes = await fetch('/auth/me', { headers: headers() });
      const me = await meRes.json().catch(() => ({}));
      if (!meRes.ok) throw new Error(me.detail || 'Oturum doğrulanamadı');
      activeProjectId = me.active_project_id || null;
      let url = '/ticket-passengers';
      if (activeProjectId) url += `?project_id=${encodeURIComponent(String(activeProjectId))}`;
      const res = await fetch(url, { headers: headers() });
      const data = await res.json().catch(() => []);
      if (!res.ok) throw new Error(data.detail || 'Katılımcılar alınamadı');
      passengers = Array.isArray(data) ? data : [];
      passengerSel.innerHTML = passengers.map(p => {
        const lim = p.budget != null ? `${p.budget} ${p.budget_currency || 'TRY'}` : 'Tanımsız';
        return `<option value="${p.row_id}">${esc(p.full_name)} | Limit: ${esc(lim)}</option>`;
      }).join('');
      if (!passengers.length) summary.textContent = 'Katılımcı bulunamadı.';
      else summary.textContent = `${passengers.length} katılımcı yüklendi.`;
    };

    const loadTickets = async () => {
      const rowId = Number(passengerSel.value || 0);
      if (!rowId) { summary.textContent = 'Katılımcı seçiniz.'; return; }
      let url = `/ticket-options?passenger_row_id=${encodeURIComponent(String(rowId))}`;
      if (activeProjectId) url += `&project_id=${encodeURIComponent(String(activeProjectId))}`;
      if (airlineSel.value) url += `&airline=${encodeURIComponent(airlineSel.value)}`;
      const res = await fetch(url, { headers: headers() });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Uçuşlar alınamadı');
      const items = Array.isArray(data.items) ? data.items : [];
      tbody.innerHTML = items.map(x => `<tr><td>${esc(x.airline)}</td><td>${esc(x.flight_no)}</td><td>${esc(x.route)}</td><td>${esc(x.depart_at)}</td><td>${esc(x.arrive_at)}</td><td>${esc(x.price)} ${esc(x.currency || 'TRY')}</td></tr>`).join('');
      tbl.style.display = items.length ? '' : 'none';
      const hidden = Number(data.hidden_count || 0);
      const budget = Number(data.budget || 0);
      summary.textContent = `Bütçe: ${budget} ${esc(data.currency || 'TRY')} | Gösterilen: ${items.length} | Limit üstü gizlenen: ${hidden}`;
    };

    refreshBtn.addEventListener('click', async () => {
      try { await loadPassengers(); } catch (err) { summary.textContent = `Hata: ${err.message}`; }
    });
    loadBtn.addEventListener('click', async () => {
      try { await loadTickets(); } catch (err) { summary.textContent = `Hata: ${err.message}`; }
    });
    loadPassengers().catch((err) => { summary.textContent = `Hata: ${err.message}`; });
  </script>
</body>
</html>
"""


@app.get("/ucak-ui", response_class=HTMLResponse)
def ucak_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Uçak Modülü</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 18px; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .muted { color:#5c6b82; font-size:13px; }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
</head>
<body>
  <div class="box">
    <h3>Uçak Modülü</h3>
    <div class="muted">Ucus ve biletleme islemleri Upload modulunden yonetilir.</div>
  </div>
</body>
</html>
"""


@app.get("/kayit-ui", response_class=HTMLResponse)
@app.get("/kayıt-ui", response_class=HTMLResponse)
def kayıt_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kayıt Modülü</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .head {
      display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;
      background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; position:relative;
    }
    .head-right { display:flex; flex-direction:row; align-items:center; gap:8px; margin-right:68px; }
    .right-panel {
      border:1px solid rgba(159,216,255,0.45);
      border-radius:8px;
      padding:4px 7px;
      background:rgba(8,23,56,0.20);
    }
    .links a { margin-right: 6px; color: #9FD8FF; text-decoration: none; font-size: 11px; font-weight: 600; }
    .admin-menu { position:relative; }
    .admin-btn { display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF; border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600; text-decoration:none; cursor:pointer; white-space:nowrap; }
    .admin-menu .links { display:none; position:absolute; top:100%; margin-top:2px; right:0; min-width:150px; background:#0A1024; border:1px solid rgba(159,216,255,0.35); border-radius:8px; padding:6px; z-index:50; }
    .admin-menu .links a { display:block; margin:0; padding:5px 6px; color:#9FD8FF; border-radius:6px; }
    .admin-menu .links a:hover { background:rgba(159,216,255,0.12); }
    .admin-menu:hover .links, .admin-menu:focus-within .links, .admin-menu.open .links { display:block; }
    .project-badge {
      display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF;
      border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600;
      letter-spacing:0.15px; white-space:nowrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08);
    }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn {
      background: rgba(255,255,255,0.18); color:#fff; text-decoration:none;
      border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px;
    }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .lang-mini { position:absolute; top:4px; right:8px; font-size:11px; padding:2px 4px; border-radius:6px; border:0; }
    .dd { position: relative; display: inline-block; margin-right: 10px; }
    .dd > a { color:#fff; text-decoration:none; font-size:14px; }
    .dd-content { display:none; position:absolute; top:22px; left:0; min-width:180px; background:#fff; border:1px solid #dde4ef; border-radius:8px; z-index:10; padding:6px 0; }
    .dd-content a { display:block; color:#1c2635; text-decoration:none; padding:7px 10px; margin:0; font-size:13px; }
    .dd-content a:hover { background:#f0f5ff; }
    .dd:hover .dd-content { display:block; }
    .dd { position: relative; display: inline-block; margin-right: 10px; }
    .dd > a { color:#fff; text-decoration:none; font-size:14px; }
    .dd-content { display:none; position:absolute; top:22px; left:0; min-width:180px; background:#fff; border:1px solid #dde4ef; border-radius:8px; z-index:10; padding:6px 0; }
    .dd-content a { display:block; color:#1c2635; text-decoration:none; padding:7px 10px; margin:0; font-size:13px; }
    .dd-content a:hover { background:#f0f5ff; }
    .dd:hover .dd-content { display:block; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .muted { color:#5c6b82; font-size:13px; }
    .grid { display:grid; grid-template-columns: repeat(3, minmax(220px, 1fr)); gap: 10px; margin-top: 12px; }
    .field { display:flex; flex-direction:column; gap:5px; }
    .field label { font-size:11px; color:#3b4b66; font-weight:700; }
    .field input, .field select, .field textarea {
      border:1px solid #cfd9e8; border-radius:7px; padding:6px 8px; font-size:12px; font-family: Arial, sans-serif;
    }
    .field textarea { min-height:54px; resize:vertical; }
    .full { grid-column: 1 / -1; }
    .section-title { margin-top: 14px; font-size: 14px; font-weight: 700; color:#0f2242; }
    .actions { display:flex; gap:8px; margin-top:12px; }
    .btn { border:0; border-radius:8px; padding:8px 12px; cursor:pointer; color:#fff; background:#2b7fff; }
    .btn.alt { background:#5c6b82; }
    table { width:100%; border-collapse: collapse; margin-top: 12px; font-size:12px; }
    th, td { border:1px solid #dde4ef; padding:7px; text-align:left; vertical-align: top; }
    th { background:#f0f5ff; position: sticky; top: 0; z-index: 1; }
    .table-wrap { max-height: 62vh; overflow:auto; border:1px solid #dde4ef; border-radius:10px; }
    .modal {
      position: fixed; inset: 0; background: rgba(0,0,0,0.35);
      display: none; align-items: center; justify-content: center; z-index: 1000;
    }
    .modal.show { display:flex; }
    .modal-card {
      width: min(460px, 92vw); max-height: 85vh; overflow:auto;
      background:#fff; border-radius:12px; border:1px solid #dde4ef; padding:12px;
    }
    .modal-grid { display:grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 6px; margin-top: 6px; }
    .col-1 { grid-column: span 1; }
    .col-2 { grid-column: span 2; }
    .col-3 { grid-column: span 3; }
    .col-6 { grid-column: span 6; }
    .modal-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
    .xbtn { border:0; background:#e9eef8; color:#1c2635; border-radius:8px; padding:6px 9px; cursor:pointer; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="head-left module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn active" href="/kayit-ui" accesskey="2" title="Kısayol: Alt+2">Kayıt Modülü</a>
        <a class="m-btn" href="/konaklama-ui" accesskey="3" title="Kısayol: Alt+3">Konaklama Modülü</a>
        <a class="m-btn" href="/toplanti-ui" accesskey="4" title="Kısayol: Alt+4">Toplantı Modülü</a>
        <a class="m-btn" href="/transfer-ui" accesskey="1" title="Kısayol: Alt+1">Ulaşım Modülü</a>
        <a class="m-btn" href="/muhasebe-finans-ui" accesskey="5" title="Kısayol: Alt+5">Muhasebe - Finans Modülü</a>
        <a class="m-btn" href="/duyurular-ui" accesskey="6" title="Kısayol: Alt+6">Duyurular</a>
      </div>
      <div class="head-right">
        <div class="admin-menu">
          <a class="admin-btn" href="/yonetici-ui">Yönetici Modülü</a>
          <div class="links">
            <a href="/reports-ui">Raporlar</a>
            <a href="/duyurular-ui">Duyurular</a>
            <a href="/projects-ui">Projeler</a>
            <a href="/users-ui">Kullanıcılar</a>
          </div>
        </div>
        <div class="right-panel">
          <span id="activeProjectBadge" class="project-badge">AKTİF PROJE: -</span>
        </div>
      </div>
      <select id="langSelect" class="lang-mini">
        <option value="tr">TR</option><option value="en">EN</option><option value="es">ES</option>
        <option value="ar">??</option><option value="it">IT</option><option value="ru">??</option>
      </select>
    </div>
    <script>
      (function(){
        function resolveToken(){
          return localStorage.getItem('access_token')
            || sessionStorage.getItem('access_token')
            || localStorage.getItem('token')
            || sessionStorage.getItem('token')
            || '';
        }
        window.__refreshActiveProjectBadge = async function(){
          var badge = document.getElementById('activeProjectBadge');
          if (!badge) return;
          var token = resolveToken();
          if (!token) {
            badge.textContent = 'AKTİF PROJE: -';
            return;
          }
          try {
            var res = await fetch('/auth/me', { headers: { Authorization: 'Bearer ' + token } });
            var me = await res.json();
            if (!res.ok || !me) {
              badge.textContent = 'AKTİF PROJE: -';
              return;
            }
            if (!me.active_project_id) {
              window.location.href = '/project-select-ui';
              return;
            }
            var pName = me.active_project_name || '-';
            var pCode = me.active_project_code || (me.active_project_id ? ('ID-' + me.active_project_id) : '-');
            badge.textContent = 'AKTİF PROJE: ' + pName + ' (' + pCode + ')';
          } catch (_) {
            badge.textContent = 'AKTİF PROJE: -';
          }
        };
        window.__refreshActiveProjectBadge();
        setTimeout(function(){ window.__refreshActiveProjectBadge(); }, 1200);
      })();
    </script>
    <div class="box">
      <h3 id="pageTitle" style="margin-top:0;">Kişi Kartları</h3>
      <div id="pageDesc" class="muted">Bu ekranda mevcut kartlar listelenir. Yeni kart ekleme pop-up üzerinden yapılır.</div>
      <div class="subtabs" style="display:flex; gap:8px; flex-wrap:wrap; margin:10px 0 8px;">
        <button id="tabPersonCards" class="subtab" type="button" style="border:0; border-radius:8px; padding:8px 12px; background:#2b7fff; color:#fff; font-size:12px; font-weight:700;">Kişi Kartları</button>
        <a id="tabCompanies" class="subtab alt" href="/kayit-sponsor-firmalar-ui" style="display:inline-flex; align-items:center; border-radius:8px; padding:8px 12px; background:#5c6b82; color:#fff; text-decoration:none; font-size:12px; font-weight:700;">Firmalar</a>
      </div>
      <div class="actions">
        <button id="newCardBtn" class="btn" type="button" accesskey="n" title="Kısayol: Alt+N" onclick="document.getElementById('cardModal').classList.add('show');">Yeni Kişi Kartı</button>
        <button id="refreshBtn" class="btn alt" type="button" accesskey="f" title="Kısayol: Alt+F">Listeyi Yenile</button>
        <button id="importBtn" class="btn alt" type="button" accesskey="i" title="Kısayol: Alt+I">İçeri Aktar</button>
        <button id="exportBtn" class="btn alt" type="button" accesskey="d" title="Kısayol: Alt+D">Dışarı Aktar</button>
        <input id="importFile" type="file" accept=".json,.csv" style="display:none;" />
      </div>
      <div id="listInfo" class="muted">Toplam kart: 0</div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Akademik Ünvan</th><th>İsim</th><th>Soyisim</th><th>ID</th><th>Kimlik No</th><th>Doğum Tarihi</th>
              <th>Cinsiyet</th><th>Telefon</th><th>Mail</th><th>Kurum</th><th>Ünvan</th><th>Adres</th>
              <th>Asistan</th><th>Asistan Telefon</th><th>Transfer Detay</th><th>Konaklama Detay</th>
            </tr>
          </thead>
          <tbody id="cardsBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <div id="cardModal" class="modal">
    <div class="modal-card">
      <div class="modal-head">
        <strong>Yeni Kişi Kartı</strong>
        <button id="closeModalBtn" class="xbtn" type="button" onclick="document.getElementById('cardModal').classList.remove('show');">Kapat</button>
      </div>
      <div class="modal-grid">
        <div class="field col-1"><label>Akademik Ünvan</label><input id="f_unvan_akd" placeholder="Prof. Dr. / Dr. / Öğr. Gör." /></div>
        <div class="field col-2"><label>İsim</label><input id="f_isim" placeholder="İsim" /></div>
        <div class="field col-2"><label>Soyisim</label><input id="f_soyisim" placeholder="Soyisim" /></div>

        <div class="field col-2"><label>Kimlik No</label><input id="f_kimlik" placeholder="T.C. Kimlik No" maxlength="11" inputmode="numeric" /></div>
        <div class="field col-2"><label>Doğum Tarihi</label><input id="f_dogum" type="date" /></div>
        <div class="field col-2">
          <label>Cinsiyet</label>
          <select id="f_cinsiyet">
            <option value="">Seçiniz</option>
            <option>Erkek</option>
            <option>Kadın</option>
            <option>Belirtmek İstemiyorum</option>
          </select>
        </div>

        <div class="field col-3">
          <label>Telefon</label>
          <div style="display:flex; gap:6px;">
            <select id="f_tel_country" style="max-width:84px; width:84px; font-size:10px;">
              <option value="+90">???? +90 TR</option>
            </select>
            <input id="f_telefon" placeholder="Telefon numarası" inputmode="numeric" />
          </div>
        </div>
        <div class="field col-2"><label>Mail</label><input id="f_mail" type="email" placeholder="ornek@firma.com" /></div>

        <div class="field col-2"><label>Kurum</label><input id="f_kurum" placeholder="Kurum/Firma" /></div>
        <div class="field col-2"><label>Ünvan</label><input id="f_unvan" placeholder="Görev/Ünvan" /></div>

        <div class="field col-2"><label>Asistan</label><input id="f_asistan" placeholder="Asistan Ad Soyad" /></div>
        <div class="field col-3">
          <label>Asistan Telefon</label>
          <div style="display:flex; gap:6px;">
            <select id="f_asistan_country" style="max-width:84px; width:84px; font-size:10px;">
              <option value="+90">???? +90 TR</option>
            </select>
            <input id="f_asistan_tel" placeholder="Telefon numarası" inputmode="numeric" />
          </div>
        </div>

        <div class="field col-6"><label>Adres</label><textarea id="f_adres" placeholder="Açık adres"></textarea></div>
        <div class="field col-6"><label>Transfer Bilgileri</label><textarea id="f_transfer" placeholder="Uçuş, karşılama, araç, pickup, transfer noktası vb."></textarea></div>
        <div class="field col-6"><label>Konaklama Bilgileri</label><textarea id="f_konaklama" placeholder="Otel, check-in/check-out, oda tipi, notlar vb."></textarea></div>

        <div class="field col-2"><label>ID (Otomatik)</label><input id="f_id" placeholder="Sistem otomatik oluşturur" readonly /></div>
      </div>
      <div class="actions">
        <button id="saveCardBtn" class="btn" type="button" accesskey="s" title="Kısayol: Alt+S" onclick="if(window.__saveCardFallback){window.__saveCardFallback();}">Kaydet</button>
        <button id="clearCardBtn" class="btn alt" type="button" accesskey="t" title="Kısayol: Alt+T" onclick="if(window.__clearCardFallback){window.__clearCardFallback();}">Temizle</button>
      </div>
    </div>
  </div>

  <script>
    (function(){
      if (!window.__cardsFallback) window.__cardsFallback = [];
      function clickById(id){
        var el = document.getElementById(id);
        if (el && typeof el.click === "function") el.click();
      }
      document.addEventListener("keydown", function(e){
        if (!e.altKey || e.ctrlKey || e.metaKey) return;
        var k = String(e.key || "").toLowerCase();
        if (k === "n") { e.preventDefault(); clickById("newCardBtn"); return; }
        if (k === "f") { e.preventDefault(); clickById("refreshBtn"); return; }
        if (k === "i") { e.preventDefault(); clickById("importBtn"); return; }
        if (k === "d") { e.preventDefault(); clickById("exportBtn"); return; }
        if (k === "s") { e.preventDefault(); clickById("saveCardBtn"); return; }
        if (k === "t") { e.preventDefault(); clickById("clearCardBtn"); return; }
      });
      function onlyDigits(v){ return String(v || "").replace(/[^0-9]/g, ""); }
      function setCountryOptions(list){
        var s1 = document.getElementById("f_tel_country");
        var s2 = document.getElementById("f_asistan_country");
        if (!s1 || !s2) return;
        var html = "";
        for (var i=0;i<list.length;i++){
          var it = list[i];
          html += '<option value="' + it.code + '">' + (it.flag || "???") + ' ' + it.code + ' ' + (it.abbr || "") + '</option>';
        }
        s1.innerHTML = html;
        s2.innerHTML = html;
        s1.value = "+90";
        s2.value = "+90";
      }
      function loadAllCountryCodes(){
        function flagFromCca2(cca2){
          if (!cca2 || String(cca2).length !== 2) return "???";
          var up = String(cca2).toUpperCase();
          var A = 127397;
          return String.fromCodePoint(A + up.charCodeAt(0), A + up.charCodeAt(1));
        }
        var fallback = [
          {code:"+90", flag:"????", name:"Türkiye", abbr:"TR"},
          {code:"+1", flag:"????", name:"United States", abbr:"US"},
          {code:"+44", flag:"????", name:"United Kingdom", abbr:"GB"},
          {code:"+49", flag:"????", name:"Germany", abbr:"DE"},
          {code:"+33", flag:"????", name:"France", abbr:"FR"},
          {code:"+39", flag:"????", name:"Italy", abbr:"IT"},
          {code:"+34", flag:"????", name:"Spain", abbr:"ES"},
          {code:"+7", flag:"????", name:"Russia", abbr:"RU"},
          {code:"+971", flag:"????", name:"UAE", abbr:"AE"}
        ];
        fetch("https://restcountries.com/v3.1/all?fields=name,idd,flag,cca2")
          .then(function(r){ return r.json(); })
          .then(function(arr){
            var out = [];
            for (var i=0;i<(arr || []).length;i++){
              var c = arr[i] || {};
              var idd = c.idd || {};
              var root = idd.root || "";
              var suff = idd.suffixes || [];
              var nm = (c.name && (c.name.common || c.name.official)) || "";
              var cca2 = (c.cca2 || "").toUpperCase();
              var flag = c.flag || flagFromCca2(cca2);
              if (!root) continue;
              // +1 kodunda sadece US tek satır kalsın
              if (root === "+1") {
                if (cca2 === "US") out.push({ code: "+1", flag: flag, name: "United States", abbr: "US" });
                continue;
              }
              if (!suff.length) {
                out.push({ code: root, flag: flag, name: nm, abbr: cca2 || "" });
              } else {
                for (var j=0;j<suff.length;j++){
                  out.push({ code: root + suff[j], flag: flag, name: nm, abbr: cca2 || "" });
                }
              }
            }
            var seen = {};
            var uniq = [];
            for (var k=0;k<out.length;k++){
              var key = out[k].code + "|" + out[k].name;
              if (seen[key]) continue;
              seen[key] = 1;
              uniq.push(out[k]);
            }
            uniq.sort(function(a,b){
              if (a.code === "+90") return -1;
              if (b.code === "+90") return 1;
              var aus = (a.code === "+1" && a.name === "United States");
              var bus = (b.code === "+1" && b.name === "United States");
              if (aus) return -1;
              if (bus) return 1;
              if (a.name < b.name) return -1;
              if (a.name > b.name) return 1;
              return 0;
            });
            if (!uniq.length) { setCountryOptions(fallback); return; }
            setCountryOptions(uniq);
          })
          .catch(function(){ setCountryOptions(fallback); });
      }
      function makeId(){
        var chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
        var out = "";
        for (var i = 0; i < 6; i++) {
          out += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return out;
      }
      function esc(v){
        v = v || "";
        return String(v).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
      }
      function get(id){ var el = document.getElementById(id); return el ? (el.value || "").trim() : ""; }
      function render(){
        var body = document.getElementById("cardsBody");
        var info = document.getElementById("listInfo");
        if (!body) return;
        var html = "";
        for (var i=0;i<window.__cardsFallback.length;i++){
          var c = window.__cardsFallback[i];
          html += "<tr>"
            + "<td>"+esc(c.f_unvan_akd)+"</td><td>"+esc(c.f_isim)+"</td><td>"+esc(c.f_soyisim)+"</td><td>"+esc(c.f_id)+"</td>"
            + "<td>"+esc(c.f_kimlik)+"</td><td>"+esc(c.f_dogum)+"</td><td>"+esc(c.f_cinsiyet)+"</td><td>"+esc(c.f_telefon)+"</td>"
            + "<td>"+esc(c.f_mail)+"</td><td>"+esc(c.f_kurum)+"</td><td>"+esc(c.f_unvan)+"</td><td>"+esc(c.f_adres)+"</td>"
            + "<td>"+esc(c.f_asistan)+"</td><td>"+esc(c.f_asistan_tel)+"</td><td>"+esc(c.f_transfer)+"</td><td>"+esc(c.f_konaklama)+"</td>"
            + "</tr>";
        }
        body.innerHTML = html;
        if (info) info.textContent = "Toplam kart: " + window.__cardsFallback.length;
      }
      window.__saveCardFallback = function(){
        var idEl = document.getElementById("f_id");
        if (idEl && !idEl.value) idEl.value = makeId();
        var tc = onlyDigits(get("f_kimlik"));
        if (tc && tc.length !== 11) { alert("T.C. Kimlik No 11 haneli olmalıdır."); return; }
        var telCode = get("f_tel_country") || "+90";
        var telNum = onlyDigits(get("f_telefon"));
        if (telCode === "+90" && telNum && telNum.length !== 10) { alert("Türkiye telefon numarası 10 haneli olmalıdır."); return; }
        var asCode = get("f_asistan_country") || "+90";
        var asNum = onlyDigits(get("f_asistan_tel"));
        if (asCode === "+90" && asNum && asNum.length !== 10) { alert("Türkiye asistan telefon numarası 10 haneli olmalıdır."); return; }
        var row = {
          f_unvan_akd:get("f_unvan_akd"), f_isim:get("f_isim"), f_soyisim:get("f_soyisim"), f_id:get("f_id"),
          f_kimlik:tc, f_dogum:get("f_dogum"), f_cinsiyet:get("f_cinsiyet"), f_telefon:(telNum ? (telCode + " " + telNum) : ""),
          f_mail:get("f_mail"), f_kurum:get("f_kurum"), f_unvan:get("f_unvan"), f_adres:get("f_adres"),
          f_asistan:get("f_asistan"), f_asistan_tel:(asNum ? (asCode + " " + asNum) : ""), f_transfer:get("f_transfer"), f_konaklama:get("f_konaklama")
        };
        if (!row.f_isim || !row.f_soyisim) { alert("İsim ve soyisim zorunludur."); return; }
        window.__cardsFallback.unshift(row);
        render();
        var ids = ["f_unvan_akd","f_isim","f_soyisim","f_id","f_kimlik","f_dogum","f_cinsiyet","f_telefon","f_mail","f_kurum","f_unvan","f_adres","f_asistan","f_asistan_tel","f_transfer","f_konaklama"];
        for (var i=0;i<ids.length;i++){ var el=document.getElementById(ids[i]); if(el) el.value=""; }
        var tc1 = document.getElementById("f_tel_country"); if (tc1) tc1.value = "+90";
        var tc2 = document.getElementById("f_asistan_country"); if (tc2) tc2.value = "+90";
        var modal = document.getElementById("cardModal");
        if (modal) modal.classList.remove("show");
      };
      window.__clearCardFallback = function(){
        var ids = ["f_unvan_akd","f_isim","f_soyisim","f_id","f_kimlik","f_dogum","f_cinsiyet","f_telefon","f_mail","f_kurum","f_unvan","f_adres","f_asistan","f_asistan_tel","f_transfer","f_konaklama"];
        for (var i=0;i<ids.length;i++){ var el=document.getElementById(ids[i]); if(el) el.value=""; }
        var tc1 = document.getElementById("f_tel_country"); if (tc1) tc1.value = "+90";
        var tc2 = document.getElementById("f_asistan_country"); if (tc2) tc2.value = "+90";
      };
      loadAllCountryCodes();
    })();
  </script>

  <script>
    (function(){
      var ls = document.getElementById("langSelect");
      var saved = localStorage.getItem("ui_lang") || "tr";
      var i18n = {
        tr: { pageTitle: "Kişi Kartları", pageDesc: "Bu ekranda mevcut kartlar listelenir. Yeni kart ekleme pop-up üzerinden yapılır.", tabPersonCards: "Kişi Kartları", tabCompanies: "Firmalar" },
        en: { pageTitle: "Person Cards", pageDesc: "Existing cards are listed on this screen. New card creation is done via pop-up.", tabPersonCards: "Person Cards", tabCompanies: "Companies" },
        es: { pageTitle: "Tarjetas de Persona", pageDesc: "Las tarjetas existentes se listan en esta pantalla. El alta de nuevas tarjetas se realiza mediante ventana emergente.", tabPersonCards: "Tarjetas de Persona", tabCompanies: "Empresas" },
        ar: { pageTitle: "?????? ???????", pageDesc: "??? ??? ???????? ??????? ?? ??? ??????. ??? ????? ????? ????? ??? ????? ??????.", tabPersonCards: "?????? ???????", tabCompanies: "???????" },
        it: { pageTitle: "Schede Persona", pageDesc: "In questa schermata sono elencate le schede esistenti. La creazione di una nuova scheda avviene tramite pop-up.", tabPersonCards: "Schede Persona", tabCompanies: "Aziende" },
        ru: { pageTitle: "???????? ??????????", pageDesc: "?? ???? ?????? ???????????? ?????? ???????????? ????????. ?????????? ????? ???????? ??????????? ????? ??????????? ????.", tabPersonCards: "???????? ??????????", tabCompanies: "????????" }
      };
      function applyLang(lang){
        var pack = i18n[lang] || i18n.tr;
        var titleEl = document.getElementById("pageTitle");
        var descEl = document.getElementById("pageDesc");
        var tabPersonCardsEl = document.getElementById("tabPersonCards");
        var tabCompaniesEl = document.getElementById("tabCompanies");
        if (titleEl) titleEl.textContent = pack.pageTitle;
        if (descEl) descEl.textContent = pack.pageDesc;
        if (tabPersonCardsEl) tabPersonCardsEl.textContent = pack.tabPersonCards || "Kişi Kartları";
        if (tabCompaniesEl) tabCompaniesEl.textContent = pack.tabCompanies || "Firmalar";
        document.documentElement.lang = lang;
        document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
        localStorage.setItem("ui_lang", lang);
        if (ls) ls.value = lang;
      }
      applyLang(saved);
      if (ls) ls.addEventListener("change", function(){
        applyLang(ls.value || "tr");
      });
    })();
    var cardsBody = document.getElementById("cardsBody");
    var listInfo = document.getElementById("listInfo");
    var cardModal = document.getElementById("cardModal");
    var newCardBtn = document.getElementById("newCardBtn");
    var closeModalBtn = document.getElementById("closeModalBtn");
    var refreshBtn = document.getElementById("refreshBtn");
    var importBtn = document.getElementById("importBtn");
    var exportBtn = document.getElementById("exportBtn");
    var importFile = document.getElementById("importFile");
    var saveCardBtn = document.getElementById("saveCardBtn");
    var clearCardBtn = document.getElementById("clearCardBtn");
    var fields = [
      "f_unvan_akd","f_isim","f_soyisim","f_id","f_kimlik","f_dogum","f_cinsiyet","f_telefon","f_mail",
      "f_kurum","f_unvan","f_adres","f_asistan","f_asistan_tel","f_transfer","f_konaklama"
    ];
    var cards = [];
    function resolveToken() {
      return localStorage.getItem("access_token")
        || sessionStorage.getItem("access_token")
        || localStorage.getItem("token")
        || sessionStorage.getItem("token")
        || "";
    }
    var authToken = resolveToken();
    function authHeaders() {
      return authToken ? { Authorization: "Bearer " + authToken } : {};
    }
    function rowToCard(r) {
      var d = (r && r.data) || {};
      return normalizeCard({
        f_unvan_akd: d.akademik_unvan || d.f_unvan_akd || "",
        f_isim: d.isim || d.f_isim || "",
        f_soyisim: d.soyisim || d.f_soyisim || "",
        f_id: d.f_id || ("KAYIT-" + String(r && r.id || "")),
        f_kimlik: d.kimlik_no || d.f_kimlik || "",
        f_dogum: d.dogum_tarihi || d.f_dogum || "",
        f_cinsiyet: d.cinsiyet || d.f_cinsiyet || "",
        f_telefon: d.telefon || d.f_telefon || "",
        f_mail: d.mail || d.f_mail || "",
        f_kurum: d.kurum || d.f_kurum || "",
        f_unvan: d.unvan || d.f_unvan || "",
        f_adres: d.adres || d.f_adres || "",
        f_asistan: d.asistan || d.f_asistan || "",
        f_asistan_tel: d.asistan_telefon || d.f_asistan_tel || "",
        f_transfer: d.transfer_detay || d.f_transfer || "",
        f_konaklama: d.konaklama_detay || d.f_konaklama || ""
      });
    }
    async function loadCardsFromApi() {
      authToken = resolveToken();
      if (!authToken) {
        listInfo.textContent = "Oturum bulunamadı. Lütfen yeniden giriş yapın.";
        cards = [];
        render();
        return;
      }
      try {
        var meRes = await fetch("/auth/me", { headers: authHeaders() });
        var me = await meRes.json().catch(function(){ return {}; });
        if (!meRes.ok) {
          listInfo.textContent = (me && me.detail) ? String(me.detail) : "Oturum doğrulanamadı.";
          cards = [];
          render();
          return;
        }
        var url = "/module-data?module_name=kayit&limit=2000";
        if (me && me.active_project_id) {
          url += "&project_id=" + encodeURIComponent(String(me.active_project_id));
        }
        var res = await fetch(url, { headers: authHeaders() });
        var data = await res.json();
        if (!res.ok) {
          listInfo.textContent = (data && data.detail) ? String(data.detail) : "Kayıtlar alınamadı.";
          cards = [];
          render();
          return;
        }
        if (!Array.isArray(data)) {
          listInfo.textContent = "Kayıt formatı beklenenden farklı.";
          cards = [];
          render();
          return;
        }
        cards = data.map(rowToCard);
        render();
      } catch (_) {
        listInfo.textContent = "Kayıtlar yüklenirken bağlantı hatası oluştu.";
      }
    }

    function esc(s) {
      s = s || "";
      return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function getVals() {
      var out = {};
      for (var i = 0; i < fields.length; i++) {
        var id = fields[i];
        out[id] = (document.getElementById(id).value || "").trim();
      }
      return out;
    }

    function clearVals() {
      for (var i = 0; i < fields.length; i++) {
        document.getElementById(fields[i]).value = "";
      }
      var c1 = document.getElementById("f_tel_country");
      var c2 = document.getElementById("f_asistan_country");
      if (c1) c1.value = "+90";
      if (c2) c2.value = "+90";
    }

    function normalizeCard(c) {
      c = c || {};
      return {
        f_unvan_akd: c.f_unvan_akd || "",
        f_isim: c.f_isim || "",
        f_soyisim: c.f_soyisim || "",
        f_id: c.f_id || "",
        f_kimlik: c.f_kimlik || "",
        f_dogum: c.f_dogum || "",
        f_cinsiyet: c.f_cinsiyet || "",
        f_telefon: c.f_telefon || "",
        f_mail: c.f_mail || "",
        f_kurum: c.f_kurum || "",
        f_unvan: c.f_unvan || "",
        f_adres: c.f_adres || "",
        f_asistan: c.f_asistan || "",
        f_asistan_tel: c.f_asistan_tel || "",
        f_transfer: c.f_transfer || "",
        f_konaklama: c.f_konaklama || ""
      };
    }

    function render() {
      listInfo.textContent = "Toplam kart: " + cards.length;
      var html = "";
      for (var i = 0; i < cards.length; i++) {
        var c = cards[i];
        html += "<tr>"
          + "<td>" + esc(c.f_unvan_akd) + "</td><td>" + esc(c.f_isim) + "</td><td>" + esc(c.f_soyisim) + "</td><td>" + esc(c.f_id) + "</td>"
          + "<td>" + esc(c.f_kimlik) + "</td><td>" + esc(c.f_dogum) + "</td><td>" + esc(c.f_cinsiyet) + "</td><td>" + esc(c.f_telefon) + "</td>"
          + "<td>" + esc(c.f_mail) + "</td><td>" + esc(c.f_kurum) + "</td><td>" + esc(c.f_unvan) + "</td><td>" + esc(c.f_adres) + "</td>"
          + "<td>" + esc(c.f_asistan) + "</td><td>" + esc(c.f_asistan_tel) + "</td><td>" + esc(c.f_transfer) + "</td><td>" + esc(c.f_konaklama) + "</td>"
          + "</tr>";
      }
      cardsBody.innerHTML = html;
    }

    function parseCsv(text) {
      var lines = text.split(/\r?\n/);
      var clean = [];
      for (var i = 0; i < lines.length; i++) {
        if ((lines[i] || "").trim()) clean.push(lines[i]);
      }
      if (clean.length < 2) return [];
      var headers = clean[0].split(",");
      for (i = 0; i < headers.length; i++) headers[i] = headers[i].trim();
      var out = [];
      for (var r = 1; r < clean.length; r++) {
        var cols = clean[r].split(",");
        var obj = {};
        for (var h = 0; h < headers.length; h++) obj[headers[h]] = (cols[h] || "").trim();
        obj = normalizeCard(obj);
        if (obj.f_isim || obj.f_soyisim) out.push(obj);
      }
      return out;
    }

    function exportCsv() {
      var headers = fields.join(",");
      var rows = [];
      for (var i = 0; i < cards.length; i++) {
        var c = cards[i];
        var row = [];
        for (var k = 0; k < fields.length; k++) {
          var key = fields[k];
          var v = String(c[key] || "").replace(/"/g, '""');
          row.push('"' + v + '"');
        }
        rows.push(row.join(","));
      }
      var csv = [headers].concat(rows).join("\n");
      var blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = "kayıt_kartlari_output.csv";
      document.body.appendChild(a);
      a.click();
      a.parentNode.removeChild(a);
      URL.revokeObjectURL(url);
    }

    function readTextFile(file, done, fail) {
      var reader = new FileReader();
      reader.onload = function () { done(String(reader.result || "")); };
      reader.onerror = function () { fail(); };
      reader.readAsText(file);
    }

    newCardBtn.addEventListener("click", function () {
      cardModal.classList.add("show");
      var idEl = document.getElementById("f_id");
      if (idEl && !idEl.value && window.__saveCardFallback) {
        // ID, ilk açılışta boş görünmesin
        var chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
        var out = "";
        for (var i = 0; i < 6; i++) out += chars.charAt(Math.floor(Math.random() * chars.length));
        idEl.value = out;
      }
    });
    closeModalBtn.addEventListener("click", function () { cardModal.classList.remove("show"); });
    cardModal.addEventListener("click", function (e) { if (e.target === cardModal) cardModal.classList.remove("show"); });
    clearCardBtn.addEventListener("click", clearVals);
    saveCardBtn.addEventListener("click", function (e) {
      if (window.__saveCardFallback) {
        try { window.__saveCardFallback(); } catch (_) {}
      }
      if (e && e.stopImmediatePropagation) e.stopImmediatePropagation();
    });
    refreshBtn.addEventListener("click", loadCardsFromApi);
    importBtn.addEventListener("click", function () { importFile.click(); });
    exportBtn.addEventListener("click", exportCsv);
    importFile.addEventListener("change", function (e) {
      var file = e.target.files && e.target.files[0];
      if (!file) return;
      readTextFile(file, function (text) {
        var parsed = [];
        var name = (file.name || "").toLowerCase();
        try {
          if (name.slice(-5) === ".json") {
            var json = JSON.parse(text);
            if (Object.prototype.toString.call(json) === "[object Array]") {
              for (var i = 0; i < json.length; i++) parsed.push(normalizeCard(json[i]));
            }
          } else {
            parsed = parseCsv(text);
          }
        } catch (err) {
          alert("İçeri Aktar sırasında dosya okunamadı.");
          importFile.value = "";
          return;
        }
        if (!parsed.length) {
          alert("İçeri Aktar dosyasında geçerli kayıt bulunamadı.");
          importFile.value = "";
          return;
        }
        for (var j = parsed.length - 1; j >= 0; j--) cards.unshift(parsed[j]);
        render();
        importFile.value = "";
      }, function () {
        alert("İçeri Aktar sırasında dosya okunamadı.");
        importFile.value = "";
      });
    });
    loadCardsFromApi();
    if (window.__refreshActiveProjectBadge) window.__refreshActiveProjectBadge();
  </script>
  <script>
    (async function(){
      try {
        var tbody = document.getElementById("cardsBody");
        var info = document.getElementById("listInfo");
        if (!tbody || !info) return;
        var token = localStorage.getItem("access_token")
          || sessionStorage.getItem("access_token")
          || localStorage.getItem("token")
          || sessionStorage.getItem("token")
          || "";
        if (!token) return;
        var h = { Authorization: "Bearer " + token };
        var meRes = await fetch("/auth/me", { headers: h });
        var me = await meRes.json().catch(function(){ return {}; });
        if (!meRes.ok) return;
        var url = "/module-data?module_name=kayit&limit=2000";
        if (me && me.active_project_id) url += "&project_id=" + encodeURIComponent(String(me.active_project_id));
        var res = await fetch(url, { headers: h });
        var rows = await res.json().catch(function(){ return []; });
        if (!res.ok || !Array.isArray(rows)) return;
        var esc = function(v){ return String(v || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); };
        var html = "";
        for (var i = 0; i < rows.length; i++) {
          var d = (rows[i] && rows[i].data) || {};
          html += "<tr>"
            + "<td>" + esc(d.akademik_unvan || d.f_unvan_akd || "") + "</td>"
            + "<td>" + esc(d.isim || d.f_isim || "") + "</td>"
            + "<td>" + esc(d.soyisim || d.f_soyisim || "") + "</td>"
            + "<td>" + esc(d.f_id || ("KAYIT-" + (rows[i].id || ""))) + "</td>"
            + "<td>" + esc(d.kimlik_no || d.f_kimlik || "") + "</td>"
            + "<td>" + esc(d.dogum_tarihi || d.f_dogum || "") + "</td>"
            + "<td>" + esc(d.cinsiyet || d.f_cinsiyet || "") + "</td>"
            + "<td>" + esc(d.telefon || d.f_telefon || "") + "</td>"
            + "<td>" + esc(d.mail || d.f_mail || "") + "</td>"
            + "<td>" + esc(d.kurum || d.f_kurum || "") + "</td>"
            + "<td>" + esc(d.unvan || d.f_unvan || "") + "</td>"
            + "<td>" + esc(d.adres || d.f_adres || "") + "</td>"
            + "<td>" + esc(d.asistan || d.f_asistan || "") + "</td>"
            + "<td>" + esc(d.asistan_telefon || d.f_asistan_tel || "") + "</td>"
            + "<td>" + esc(d.transfer_detay || d.f_transfer || "") + "</td>"
            + "<td>" + esc(d.konaklama_detay || d.f_konaklama || "") + "</td>"
            + "</tr>";
        }
        tbody.innerHTML = html;
        info.textContent = "Toplam kart: " + rows.length;
      } catch (_) {}
    })();
  </script>
  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""


@app.get("/kayit-sponsor-firmalar-ui", response_class=HTMLResponse)
def kayit_sponsor_firmalar_ui():
    html = """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kayıt Modülü - Firmalar</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .head { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; position:relative; }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn { background: rgba(255,255,255,0.18); color:#fff; text-decoration:none; border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px; }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .muted { color:#5c6b82; font-size:13px; }
    .subtabs { display:flex; gap:8px; flex-wrap:wrap; margin:10px 0 8px; }
    .subtab { display:inline-flex; align-items:center; border-radius:8px; padding:8px 12px; background:#2b7fff; color:#fff; text-decoration:none; font-size:12px; font-weight:700; border:0; }
    .subtab.alt { background:#5c6b82; }
    .grid { display:grid; grid-template-columns: repeat(4, minmax(180px, 1fr)); gap: 8px; margin-top: 8px; }
    .field { display:flex; flex-direction:column; gap:4px; }
    .field label { font-size:11px; color:#3b4b66; font-weight:700; }
    .field input, .field select { border:1px solid #cfd9e8; border-radius:7px; padding:7px 8px; font-size:12px; }
    .actions { display:flex; gap:8px; margin-top:10px; }
    .btn { border:0; border-radius:8px; padding:8px 12px; cursor:pointer; color:#fff; background:#2b7fff; }
    .btn.alt { background:#5c6b82; }
    .btn.danger { background:#c62828; }
    table { width:100%; border-collapse: collapse; margin-top: 12px; font-size:12px; }
    th, td { border:1px solid #dde4ef; padding:7px; text-align:left; vertical-align: top; }
    th { background:#f0f5ff; }
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
    .table-wrap { width:100%; overflow-x:auto; border:1px solid #dde4ef; border-radius:10px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn active" href="/kayit-ui">Kayıt Modülü</a>
      </div>
    </div>
    <div class="box">
      <h3 style="margin-top:0;">Firmalar</h3>
      <div class="muted">Kayıt modülü için sponsor firmaları bu ekrandan yönetebilirsin.</div>
      <div class="subtabs">
        <a class="subtab alt" href="/kayit-ui">Kişi Kartları</a>
        <button class="subtab" type="button">Firmalar</button>
      </div>

      <div class="grid">
        <div class="field"><label>Firma Adı</label><input id="f_name" placeholder="Firma adı" /></div>
        <div class="field"><label>Sponsor Türü</label><select id="f_type"><option value="">Seçiniz</option><option>Platin</option><option>Altın</option><option>Gümüş</option><option>Bronz</option><option>Destekçi</option></select></div>
        <div class="field"><label>Yetkili</label><input id="f_contact" placeholder="Yetkili kişi" /></div>
        <div class="field"><label>Telefon</label><input id="f_phone" placeholder="Telefon" /></div>
        <div class="field"><label>E-posta</label><input id="f_email" placeholder="E-posta" /></div>
        <div class="field" style="grid-column: span 3;"><label>Not</label><input id="f_note" placeholder="Not" /></div>
      </div>
      <div class="actions">
        <button id="btnAdd" class="btn" type="button">Kaydet</button>
        <button id="btnRefresh" class="btn alt" type="button">Listeyi Yenile</button>
      </div>
      <div id="info" class="muted" style="margin-top:8px;">Toplam firma: 0</div>

      <div class="table-wrap">
        <table>
          <thead><tr><th>ID</th><th>Firma Adı</th><th>Sponsor Türü</th><th>Yetkili</th><th>Telefon</th><th>E-posta</th><th>Not</th><th>İşlem</th></tr></thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
    </div>
  </div>
  <script>
    (function(){
      const token = localStorage.getItem("access_token")
        || sessionStorage.getItem("access_token")
        || localStorage.getItem("token")
        || sessionStorage.getItem("token")
        || "";
      const headers = () => token ? ({ Authorization: "Bearer " + token }) : ({});
      const tbody = document.getElementById("tbody");
      const info = document.getElementById("info");
      const esc = (v) => String(v || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      let activeProjectId = null;
      let rows = [];

      async function ensureProject(){
        const meRes = await fetch("/auth/me", { headers: headers() });
        const me = await meRes.json().catch(() => ({}));
        if (!meRes.ok) throw new Error(me.detail || "Oturum bulunamadı");
        activeProjectId = me.active_project_id || null;
      }

      function render(){
        tbody.innerHTML = rows.map((r) => {
          const d = r.data || {};
          return `<tr>
            <td>${esc(r.id)}</td>
            <td>${esc(d.company_name)}</td>
            <td>${esc(d.sponsor_type)}</td>
            <td>${esc(d.contact_name)}</td>
            <td>${esc(d.phone)}</td>
            <td>${esc(d.email)}</td>
            <td>${esc(d.note)}</td>
            <td><button class="btn danger" data-id="${esc(r.id)}" type="button">Sil</button></td>
          </tr>`;
        }).join("");
        info.textContent = "Toplam firma: " + rows.length;
      }

      async function load(){
        if (!token) { info.textContent = "Oturum yok. Önce giriş yapın."; return; }
        await ensureProject();
        let url = "/module-data?module_name=kayit&entity_type=sponsor_firma&limit=2000";
        if (activeProjectId) url += "&project_id=" + encodeURIComponent(String(activeProjectId));
        const res = await fetch(url, { headers: headers() });
        const data = await res.json().catch(() => []);
        if (!res.ok) throw new Error(data.detail || "Sponsor firmalar yüklenemedi");
        rows = Array.isArray(data) ? data : [];
        render();
      }

      async function add(){
        const company_name = (document.getElementById("f_name").value || "").trim();
        if (!company_name) { alert("Firma adı zorunludur."); return; }
        const payload = {
          module_name: "kayit",
          entity_type: "sponsor_firma",
          project_id: activeProjectId,
          data: {
            company_name,
            sponsor_type: (document.getElementById("f_type").value || "").trim(),
            contact_name: (document.getElementById("f_contact").value || "").trim(),
            phone: (document.getElementById("f_phone").value || "").trim(),
            email: (document.getElementById("f_email").value || "").trim(),
            note: (document.getElementById("f_note").value || "").trim()
          }
        };
        const res = await fetch("/module-data", {
          method: "POST",
          headers: { ...headers(), "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const out = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(out.detail || "Kaydedilemedi");
        ["f_name","f_type","f_contact","f_phone","f_email","f_note"].forEach((id) => { const el = document.getElementById(id); if (el) el.value = ""; });
        await load();
      }

      async function removeRow(id){
        if (!confirm("Bu sponsor firma kaydı silinsin mi?")) return;
        const url = activeProjectId ? `/module-data/${id}?project_id=${encodeURIComponent(String(activeProjectId))}` : `/module-data/${id}`;
        const res = await fetch(url, { method: "DELETE", headers: headers() });
        const out = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(out.detail || "Silinemedi");
        await load();
      }

      document.getElementById("btnRefresh").addEventListener("click", async () => {
        try { await load(); } catch (err) { info.textContent = "Hata: " + err.message; }
      });
      document.getElementById("btnAdd").addEventListener("click", async () => {
        try { await add(); } catch (err) { info.textContent = "Hata: " + err.message; }
      });
      tbody.addEventListener("click", async (e) => {
        const btn = e.target && e.target.closest ? e.target.closest("button[data-id]") : null;
        if (!btn) return;
        try { await removeRow(Number(btn.getAttribute("data-id"))); } catch (err) { info.textContent = "Hata: " + err.message; }
      });

      load().catch((err) => { info.textContent = "Hata: " + err.message; });
    })();
  </script>
  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""
    return HTMLResponse(_inject_standard_header_style(html))


@app.get("/konaklama-ui", response_class=HTMLResponse)
def konaklama_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Konaklama Modülü</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .head {
      display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;
      background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; position:relative;
    }
    .head-right { display:flex; flex-direction:row; align-items:center; gap:8px; margin-right:68px; }
    .right-panel {
      border:1px solid rgba(159,216,255,0.45);
      border-radius:8px;
      padding:4px 7px;
      background:rgba(8,23,56,0.20);
    }
    .links a { margin-right: 6px; color: #9FD8FF; text-decoration: none; font-size: 11px; font-weight: 600; }
    .admin-menu { position:relative; }
    .admin-btn { display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF; border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600; text-decoration:none; cursor:pointer; white-space:nowrap; }
    .admin-menu .links { display:none; position:absolute; top:100%; margin-top:2px; right:0; min-width:150px; background:#0A1024; border:1px solid rgba(159,216,255,0.35); border-radius:8px; padding:6px; z-index:50; }
    .admin-menu .links a { display:block; margin:0; padding:5px 6px; color:#9FD8FF; border-radius:6px; }
    .admin-menu .links a:hover { background:rgba(159,216,255,0.12); }
    .admin-menu:hover .links, .admin-menu:focus-within .links, .admin-menu.open .links { display:block; }
    .project-badge {
      display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF;
      border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600;
      letter-spacing:0.15px; white-space:nowrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08);
    }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn {
      background: rgba(255,255,255,0.18); color:#fff; text-decoration:none;
      border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px;
    }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .lang-mini { position:absolute; top:4px; right:8px; font-size:11px; padding:2px 4px; border-radius:6px; border:0; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .muted { color:#5c6b82; font-size:13px; }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="head-left module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn" href="/kayit-ui" accesskey="2" title="Kısayol: Alt+2">Kayıt Modülü</a>
        <a class="m-btn active" href="/konaklama-ui" accesskey="3" title="Kısayol: Alt+3">Konaklama Modülü</a>
        <a class="m-btn" href="/toplanti-ui" accesskey="4" title="Kısayol: Alt+4">Toplantı Modülü</a>
        <a class="m-btn" href="/transfer-ui" accesskey="1" title="Kısayol: Alt+1">Ulaşım Modülü</a>
        <a class="m-btn" href="/muhasebe-finans-ui" accesskey="5" title="Kısayol: Alt+5">Muhasebe - Finans Modülü</a>
        <a class="m-btn" href="/duyurular-ui" accesskey="6" title="Kısayol: Alt+6">Duyurular</a>
      </div>
      <div class="head-right">
        <div class="admin-menu">
          <a class="admin-btn" href="/yonetici-ui">Yönetici Modülü</a>
          <div class="links">
            <a href="/reports-ui">Raporlar</a>
            <a href="/duyurular-ui">Duyurular</a>
            <a href="/projects-ui">Projeler</a>
            <a href="/users-ui">Kullanıcılar</a>
          </div>
        </div>
        <div class="right-panel">
          <span id="activeProjectBadge" class="project-badge">AKTİF PROJE: -</span>
        </div>
      </div>
      <select id="langSelect" class="lang-mini">
        <option value="tr">TR</option><option value="en">EN</option><option value="es">ES</option>
        <option value="ar">??</option><option value="it">IT</option><option value="ru">??</option>
      </select>
    </div>
    <div class="box">
      <h3 id="pageTitle">Konaklama Modülü</h3>
      <div id="pageDesc" class="muted">Otel, paket ve oda planlarına göre konaklama hesaplama ve kayıt işlemleri.</div>
      <div style="margin-top:12px; display:grid; grid-template-columns:repeat(4,minmax(180px,1fr)); gap:10px;">
        <div><label>Otel</label><input id="f_hotel" placeholder="Örn: Otel 1" /></div>
        <div><label>Paket Kodu</label><input id="f_paket_kod" placeholder="Örn: PKT-01" /></div>
        <div><label>Paket Adı</label><input id="f_paket_ad" placeholder="Örn: 20-24 Mart" /></div>
        <div><label>Oda Tipi</label>
          <select id="f_room_type">
            <option value="SNG">SNG</option>
            <option value="DBL">DBL</option>
            <option value="TRP">TRP</option>
          </select>
        </div>
      </div>
      <div style="margin-top:10px; display:grid; grid-template-columns:repeat(4,minmax(180px,1fr)); gap:10px;">
        <div><label>SNG Fiyatı</label><input id="f_price_sng" type="number" min="0" step="0.01" placeholder="0.00" /></div>
        <div><label>DBL Fiyatı</label><input id="f_price_dbl" type="number" min="0" step="0.01" placeholder="0.00" /></div>
        <div><label>TRP Fiyatı</label><input id="f_price_trp" type="number" min="0" step="0.01" placeholder="0.00" /></div>
        <div><label>Ödeme Planı</label>
          <select id="f_plan">
            <option value="tek_kisi_tam">Tek Kişi Tüm Oda</option>
            <option value="dbl_yarim">DBL İki Kişi Eşit</option>
            <option value="dbl_sng_plus_fark">DBL: Ana SNG + Eşlikçi Fark</option>
            <option value="trp_ucuncu_fark">TRP: 3. Kişi TRP Farkı</option>
            <option value="manuel_tutar">Manuel Tutar Girişi</option>
          </select>
        </div>
      </div>

      <div style="margin-top:12px; border:1px solid #dde4ef; border-radius:10px; padding:10px;">
        <div style="font-weight:700; margin-bottom:8px;">Kişi Eşleştirme (5 karakterle arama)</div>
        <div style="display:grid; grid-template-columns:repeat(3,minmax(220px,1fr)); gap:10px;">
          <div style="position:relative;">
            <label>1. Kişi (Ana)</label>
            <input id="p1_query" placeholder="ID veya isim yazın (min 5 karakter)" autocomplete="off" />
            <input id="p1_id" type="hidden" />
            <div id="p1_suggest" style="display:none; position:absolute; z-index:20; top:58px; left:0; right:0; max-height:180px; overflow:auto; background:#fff; border:1px solid #d0d9e8; border-radius:8px;"></div>
            <div class="muted" id="p1_hint"></div>
          </div>
          <div style="position:relative;">
            <label>2. Kişi</label>
            <input id="p2_query" placeholder="ID veya isim yazın (min 5 karakter)" autocomplete="off" />
            <input id="p2_id" type="hidden" />
            <div id="p2_suggest" style="display:none; position:absolute; z-index:20; top:58px; left:0; right:0; max-height:180px; overflow:auto; background:#fff; border:1px solid #d0d9e8; border-radius:8px;"></div>
            <div class="muted" id="p2_hint"></div>
          </div>
          <div style="position:relative;">
            <label>3. Kişi</label>
            <input id="p3_query" placeholder="ID veya isim yazın (min 5 karakter)" autocomplete="off" />
            <input id="p3_id" type="hidden" />
            <div id="p3_suggest" style="display:none; position:absolute; z-index:20; top:58px; left:0; right:0; max-height:180px; overflow:auto; background:#fff; border:1px solid #d0d9e8; border-radius:8px;"></div>
            <div class="muted" id="p3_hint"></div>
          </div>
        </div>
      </div>

      <div style="margin-top:10px; display:grid; grid-template-columns:repeat(4,minmax(180px,1fr)); gap:10px;">
        <div><label>1. Kişi Tutar</label><input id="f_amt1" type="number" min="0" step="0.01" placeholder="0.00" /></div>
        <div><label>2. Kişi Tutar</label><input id="f_amt2" type="number" min="0" step="0.01" placeholder="0.00" /></div>
        <div><label>3. Kişi Tutar</label><input id="f_amt3" type="number" min="0" step="0.01" placeholder="0.00" /></div>
        <div><label>Toplam</label><input id="f_total" type="text" readonly /></div>
      </div>
      <div style="margin-top:10px;"><label>Not</label><input id="f_note" placeholder="Opsiyonel not" /></div>

      <div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
        <button id="btnCalc" class="tab">Hesapla</button>
        <button id="btnSave" class="tab">Kaydet</button>
        <button id="btnRefresh" class="tab alt">Listeyi Yenile</button>
      </div>
      <div id="msg" class="muted" style="margin-top:8px;"></div>

      <div style="margin-top:12px; overflow:auto;">
        <table style="width:100%; border-collapse:collapse; min-width:1300px;">
          <thead>
            <tr>
              <th>ID</th><th>OTEL</th><th>PAKET</th><th>ODA</th><th>PLAN</th>
              <th>1. KİŞİ</th><th>1. TUTAR</th><th>2. KİŞİ</th><th>2. TUTAR</th><th>3. KİŞİ</th><th>3. TUTAR</th>
              <th>TOPLAM</th><th>NOT</th><th>KAYIT TARİHİ</th>
            </tr>
          </thead>
          <tbody id="rowsBody"></tbody>
        </table>
      </div>
    </div>
  </div>
  <script>
    (function(){
      var ls = document.getElementById("langSelect");
      var saved = localStorage.getItem("ui_lang") || "tr";
      var i18n = {
        tr: { pageTitle: "Konaklama Modülü", pageDesc: "Otel, paket ve oda planlarına göre konaklama hesaplama ve kayıt işlemleri." },
        en: { pageTitle: "Accommodation Module", pageDesc: "Accommodation pricing and records by hotel, package and room plan." },
        es: { pageTitle: "Módulo de Alojamiento", pageDesc: "Cálculo y registro de alojamiento por hotel, paquete y plan de habitación." },
        ar: { pageTitle: "???? ???????", pageDesc: "????? ?????? ??????? ??? ?????? ??????? ???? ??????." },
        it: { pageTitle: "Modulo Alloggio", pageDesc: "Calcolo e registrazione alloggio per hotel, pacchetto e piano camera." },
        ru: { pageTitle: "?????? ??????????", pageDesc: "?????? ? ???? ?????????? ?? ?????, ?????? ? ???? ??????." }
      };
      function applyLang(lang){
        var pack = i18n[lang] || i18n.tr;
        var titleEl = document.getElementById("pageTitle");
        var descEl = document.getElementById("pageDesc");
        if (titleEl) titleEl.textContent = pack.pageTitle;
        if (descEl) descEl.textContent = pack.pageDesc;
        document.documentElement.lang = lang;
        document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
        localStorage.setItem("ui_lang", lang);
        if (ls) ls.value = lang;
      }
      applyLang(saved);
      if (ls) ls.addEventListener("change", function(){
        applyLang(ls.value || "tr");
      });
    })();
    (async function(){
      var token = localStorage.getItem('access_token') || '';
      var badge = document.getElementById('activeProjectBadge');
      if (!token || !badge) return;
      var allowed = new Set(['interpreter','tenant_manager','tenant_admin','supertranslator','superadmin_staff','superadmin']);
      try {
        var res = await fetch('/auth/me', { headers: { Authorization: `Bearer ${token}` } });
        var me = await res.json();
        if (!res.ok || !me) return;
        var role = String(me.role || '').toLowerCase();
        if (!allowed.has(role)) {
          var navInterpreter = document.getElementById('navInterpreterToplanti');
          var linkInterpreterPanel = document.getElementById('linkInterpreterPanel');
          if (navInterpreter) navInterpreter.style.display = 'none';
          if (linkInterpreterPanel) linkInterpreterPanel.style.display = 'none';
        }
        var pName = me.active_project_name || '-';
        var pCode = me.active_project_code || (me.active_project_id ? ('ID-' + me.active_project_id) : '-');
        badge.textContent = `AKTİF PROJE: ${pName} (${pCode})`;
      } catch (_) {}
    })();

    (function(){
      var msg = document.getElementById("msg");
      var rowsBody = document.getElementById("rowsBody");
      var btnCalc = document.getElementById("btnCalc");
      var btnSave = document.getElementById("btnSave");
      var btnRefresh = document.getElementById("btnRefresh");
      var token = localStorage.getItem("access_token") || "";
      var activeProjectId = null;
      var kayitRows = [];

      function authHeaders(){ return token ? { Authorization: "Bearer " + token } : {}; }
      function n(v){ var x = Number(v); return Number.isFinite(x) ? x : 0; }
      function fmt(v){ return n(v).toFixed(2); }
      function val(id){ var el = document.getElementById(id); return el ? String(el.value || "").trim() : ""; }
      function setVal(id, v){ var el = document.getElementById(id); if (el) el.value = v == null ? "" : String(v); }
      function setMsg(text){ if (msg) msg.textContent = text || ""; }
      function esc(v){ return String(v || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
      function up(v){ return String(v || "").toLocaleUpperCase("tr-TR"); }

      function selectedPerson(pid){
        var idNum = parseInt(String(pid || "0"), 10);
        if (!idNum) return null;
        for (var i = 0; i < kayitRows.length; i += 1) if (Number(kayitRows[i].id) === idNum) return kayitRows[i];
        return null;
      }

      function calcAmounts(){
        var room = val("f_room_type");
        var plan = val("f_plan");
        var sng = n(val("f_price_sng"));
        var dbl = n(val("f_price_dbl"));
        var trp = n(val("f_price_trp"));
        var p1 = 0, p2 = 0, p3 = 0, total = 0;

        if (room === "SNG") total = sng;
        else if (room === "DBL") total = dbl;
        else total = trp;

        if (plan === "tek_kisi_tam") {
          p1 = total;
        } else if (plan === "dbl_yarim") {
          if (room !== "DBL") { setMsg("DBL İki Kişi Eşit planı için oda tipi DBL olmalıdır."); return null; }
          p1 = dbl / 2; p2 = dbl / 2;
        } else if (plan === "dbl_sng_plus_fark") {
          if (room !== "DBL") { setMsg("Bu plan için oda tipi DBL olmalıdır."); return null; }
          p1 = sng;
          p2 = Math.max(0, dbl - sng);
        } else if (plan === "trp_ucuncu_fark") {
          if (room !== "TRP") { setMsg("Bu plan için oda tipi TRP olmalıdır."); return null; }
          p1 = dbl / 2;
          p2 = dbl / 2;
          p3 = Math.max(0, trp - dbl);
        } else if (plan === "manuel_tutar") {
          p1 = n(val("f_amt1"));
          p2 = n(val("f_amt2"));
          p3 = n(val("f_amt3"));
        }

        setVal("f_amt1", fmt(p1));
        setVal("f_amt2", fmt(p2));
        setVal("f_amt3", fmt(p3));
        setVal("f_total", fmt(p1 + p2 + p3));
        setMsg("");
        return { p1: p1, p2: p2, p3: p3, total: (p1 + p2 + p3) };
      }

      function bindPersonPicker(prefix){
        var q = document.getElementById(prefix + "_query");
        var hid = document.getElementById(prefix + "_id");
        var sug = document.getElementById(prefix + "_suggest");
        var hint = document.getElementById(prefix + "_hint");
        if (!q || !hid || !sug) return;

        function closeSug(){ sug.style.display = "none"; sug.innerHTML = ""; }
        function selectRow(row){
          hid.value = String(row.id || "");
          q.value = [row.f_id || ("KAYIT-" + row.id), row.full_name].join(" - ");
          if (hint) hint.textContent = "Seçildi: " + row.full_name;
          closeSug();
        }
        q.addEventListener("input", function(){
          var text = String(q.value || "").trim();
          hid.value = "";
          if (hint) hint.textContent = "";
          if (text.length < 5) { closeSug(); return; }
          var needle = up(text);
          var list = [];
          for (var i = 0; i < kayitRows.length; i += 1) {
            var r = kayitRows[i];
            var hay = up((r.f_id || ("KAYIT-" + r.id)) + " " + (r.full_name || ""));
            if (hay.indexOf(needle) >= 0) list.push(r);
            if (list.length >= 12) break;
          }
          if (!list.length) { closeSug(); return; }
          var html = "";
          for (var j = 0; j < list.length; j += 1) {
            var it = list[j];
            html += '<div data-id="' + esc(it.id) + '" style="padding:7px 8px; cursor:pointer; border-bottom:1px solid #edf2fa;">'
              + esc((it.f_id || ("KAYIT-" + it.id)) + " - " + it.full_name) + '</div>';
          }
          sug.innerHTML = html;
          sug.style.display = "block";
          Array.prototype.slice.call(sug.querySelectorAll("div[data-id]")).forEach(function(el){
            el.addEventListener("click", function(){
              var rid = parseInt(String(el.getAttribute("data-id") || "0"), 10);
              for (var k = 0; k < list.length; k += 1) if (Number(list[k].id) === rid) { selectRow(list[k]); break; }
            });
          });
        });
        document.addEventListener("click", function(e){
          if (!sug.contains(e.target) && e.target !== q) closeSug();
        });
      }

      function mapKayitRow(r){
        var d = (r && r.data) || {};
        var fId = d.f_id || ("KAYIT-" + String(r.id || ""));
        var isim = d.isim || d.f_isim || "";
        var soyisim = d.soyisim || d.f_soyisim || "";
        return {
          id: r.id,
          f_id: fId,
          full_name: String((isim + " " + soyisim)).trim()
        };
      }

      async function loadContext(){
        if (!token) { setMsg("Oturum bulunamadı."); return false; }
        var meRes = await fetch("/auth/me", { headers: authHeaders() });
        var me = await meRes.json().catch(function(){ return {}; });
        if (!meRes.ok || !me) { setMsg("Oturum doğrulanamadı."); return false; }
        if (!me.active_project_id) { setMsg("Aktif proje seçimi gerekli."); return false; }
        activeProjectId = Number(me.active_project_id);
        var kUrl = "/module-data?module_name=kayit&project_id=" + encodeURIComponent(String(activeProjectId)) + "&limit=5000";
        var kRes = await fetch(kUrl, { headers: authHeaders() });
        var kData = await kRes.json().catch(function(){ return []; });
        if (!kRes.ok || !Array.isArray(kData)) { setMsg("Kayıt kartları alınamadı."); return false; }
        kayitRows = kData.map(mapKayitRow).filter(function(x){ return !!x && !!x.id; });
        return true;
      }

      async function loadRows(){
        if (!activeProjectId) return;
        var url = "/module-data?module_name=konaklama&project_id=" + encodeURIComponent(String(activeProjectId)) + "&limit=1000";
        var res = await fetch(url, { headers: authHeaders() });
        var data = await res.json().catch(function(){ return []; });
        if (!res.ok || !Array.isArray(data)) { setMsg("Konaklama kayıtları alınamadı."); return; }
        var html = "";
        for (var i = 0; i < data.length; i += 1) {
          var r = data[i] || {};
          var d = r.data || {};
          html += "<tr>"
            + "<td>" + esc(r.id) + "</td>"
            + "<td>" + esc(d.hotel) + "</td>"
            + "<td>" + esc((d.package_code || "") + " " + (d.package_name ? ("- " + d.package_name) : "")) + "</td>"
            + "<td>" + esc(d.room_type) + "</td>"
            + "<td>" + esc(d.payment_plan) + "</td>"
            + "<td>" + esc(d.person1_name) + "</td>"
            + "<td>" + esc(d.amount1) + "</td>"
            + "<td>" + esc(d.person2_name) + "</td>"
            + "<td>" + esc(d.amount2) + "</td>"
            + "<td>" + esc(d.person3_name) + "</td>"
            + "<td>" + esc(d.amount3) + "</td>"
            + "<td>" + esc(d.total_amount) + "</td>"
            + "<td>" + esc(d.note) + "</td>"
            + "<td>" + esc(r.created_at) + "</td>"
            + "</tr>";
        }
        rowsBody.innerHTML = html;
      }

      async function saveRow(){
        var calc = calcAmounts();
        if (!calc) return;
        var p1id = parseInt(val("p1_id") || "0", 10);
        var p2id = parseInt(val("p2_id") || "0", 10);
        var p3id = parseInt(val("p3_id") || "0", 10);
        if (!p1id) { setMsg("1. kişi seçimi zorunludur."); return; }
        if (calc.p2 > 0 && !p2id) { setMsg("2. kişi payı var, 2. kişi seçilmelidir."); return; }
        if (calc.p3 > 0 && !p3id) { setMsg("3. kişi payı var, 3. kişi seçilmelidir."); return; }

        var p1 = selectedPerson(p1id);
        var p2 = selectedPerson(p2id);
        var p3 = selectedPerson(p3id);
        var payload = {
          module_name: "konaklama",
          project_id: activeProjectId,
          kayit_id: p1id,
          entity_type: "oda_plani",
          data: {
            hotel: val("f_hotel"),
            package_code: val("f_paket_kod"),
            package_name: val("f_paket_ad"),
            room_type: val("f_room_type"),
            payment_plan: val("f_plan"),
            price_sng: fmt(val("f_price_sng")),
            price_dbl: fmt(val("f_price_dbl")),
            price_trp: fmt(val("f_price_trp")),
            person1_id: p1id || null,
            person1_name: p1 ? p1.full_name : "",
            person2_id: p2id || null,
            person2_name: p2 ? p2.full_name : "",
            person3_id: p3id || null,
            person3_name: p3 ? p3.full_name : "",
            amount1: fmt(calc.p1),
            amount2: fmt(calc.p2),
            amount3: fmt(calc.p3),
            total_amount: fmt(calc.total),
            note: val("f_note")
          }
        };
        var res = await fetch("/module-data", {
          method: "POST",
          headers: Object.assign({ "Content-Type": "application/json" }, authHeaders()),
          body: JSON.stringify(payload)
        });
        var data = await res.json().catch(function(){ return {}; });
        if (!res.ok) { setMsg(data.detail || "Kaydetme hatası."); return; }
        setMsg("Konaklama kaydı oluşturuldu.");
        await loadRows();
      }

      bindPersonPicker("p1");
      bindPersonPicker("p2");
      bindPersonPicker("p3");
      btnCalc.addEventListener("click", calcAmounts);
      btnSave.addEventListener("click", function(){ saveRow().catch(function(){ setMsg("Kaydetme sırasında hata oluştu."); }); });
      btnRefresh.addEventListener("click", function(){ loadRows().catch(function(){ setMsg("Liste yüklenemedi."); }); });

      loadContext().then(function(ok){
        if (!ok) return;
        loadRows();
      }).catch(function(){
        setMsg("Modül başlatılamadı.");
      });
    })();
  </script>
  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""


@app.get("/toplanti-ui", response_class=HTMLResponse)
def toplanti_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Toplantı Modülü</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .head {
      display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;
      background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; position:relative;
    }
    .head-right { display:flex; flex-direction:row; align-items:center; gap:8px; margin-right:68px; }
    .right-panel {
      border:1px solid rgba(159,216,255,0.45);
      border-radius:8px;
      padding:4px 7px;
      background:rgba(8,23,56,0.20);
    }
    .links a { margin-right: 6px; color: #9FD8FF; text-decoration: none; font-size: 11px; font-weight: 600; }
    .admin-menu { position:relative; }
    .admin-btn { display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF; border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600; text-decoration:none; cursor:pointer; white-space:nowrap; }
    .admin-menu .links { display:none; position:absolute; top:100%; margin-top:2px; right:0; min-width:150px; background:#0A1024; border:1px solid rgba(159,216,255,0.35); border-radius:8px; padding:6px; z-index:50; }
    .admin-menu .links a { display:block; margin:0; padding:5px 6px; color:#9FD8FF; border-radius:6px; }
    .admin-menu .links a:hover { background:rgba(159,216,255,0.12); }
    .admin-menu:hover .links, .admin-menu:focus-within .links, .admin-menu.open .links { display:block; }
    .project-badge {
      display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF;
      border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600;
      letter-spacing:0.15px; white-space:nowrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08);
    }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn {
      background: rgba(255,255,255,0.18); color:#fff; text-decoration:none;
      border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px;
    }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .lang-mini { position:absolute; top:4px; right:8px; font-size:11px; padding:2px 4px; border-radius:6px; border:0; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .tabs { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px; }
    .tab { border:0; border-radius:8px; background:#2b7fff; color:#fff; padding:8px 12px; cursor:pointer; }
    .tab.alt { background:#5c6b82; }
    .panel { border:1px solid #dde4ef; border-radius:10px; padding:12px; background:#fbfdff; }
    .muted { color:#5c6b82; font-size:13px; }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="head-left module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn" href="/kayit-ui" accesskey="2" title="Kısayol: Alt+2">Kayıt Modülü</a>
        <a class="m-btn" href="/konaklama-ui" accesskey="3" title="Kısayol: Alt+3">Konaklama Modülü</a>
        <a class="m-btn active" href="/toplanti-ui" accesskey="4" title="Kısayol: Alt+4">Toplantı Modülü</a>
        <a id="navInterpreterToplanti" class="m-btn" href="/tercuman-ui">Tercüman Modülü</a>
        <a class="m-btn" href="/transfer-ui" accesskey="1" title="Kısayol: Alt+1">Ulaşım Modülü</a>
        <a class="m-btn" href="/muhasebe-finans-ui" accesskey="5" title="Kısayol: Alt+5">Muhasebe - Finans Modülü</a>
        <a class="m-btn" href="/duyurular-ui" accesskey="6" title="Kısayol: Alt+6">Duyurular</a>
      </div>
      <div class="head-right">
        <div class="admin-menu">
          <a class="admin-btn" href="/yonetici-ui">Yönetici Modülü</a>
          <div class="links">
            <a href="/reports-ui">Raporlar</a>
            <a href="/duyurular-ui">Duyurular</a>
            <a href="/projects-ui">Projeler</a>
            <a href="/users-ui">Kullanıcılar</a>
          </div>
        </div>
        <div class="right-panel">
          <span id="activeProjectBadge" class="project-badge">AKTİF PROJE: -</span>
        </div>
      </div>
      <select id="langSelect" class="lang-mini">
        <option value="tr">TR</option><option value="en">EN</option><option value="es">ES</option>
        <option value="ar">??</option><option value="it">IT</option><option value="ru">??</option>
      </select>
    </div>
    <div class="box">
      <h3 id="pageTitle">Toplantı Modülü</h3>
      <div id="pageDesc" class="muted">Bu modül altında bilimsel program, kurslar ve sertifikalar yönetilir.</div>
      <div class="tabs">
        <button id="tabProgram" class="tab">Bilimsel Program</button>
        <button id="tabOfficials" class="tab alt">Bilimsel Görevliler</button>
        <button id="tabQA" class="tab alt">Soru Cevap</button>
        <button id="tabSurvey" class="tab alt">Anket</button>
        <button id="tabCourses" class="tab alt">Kurslar</button>
        <button id="tabCerts" class="tab alt">Sertifikalar</button>
        <button id="tabOnlineMeeting" class="tab alt">Online Toplantı</button>
        <button id="tabTranslationSessions" class="tab alt">Çeviri Oturumları</button>
      </div>
      <div id="panelProgram" class="panel">
        <strong id="panelProgramTitle">Bilimsel Program</strong>
        <div id="panelProgramDesc" class="muted" style="margin-top:6px;">Oturum, konuşmacı, salon ve saat planlaması bu alt modülde yönetilir.</div>
      </div>
      <div id="panelOfficials" class="panel" style="display:none;">
        <strong id="panelOfficialsTitle">Bilimsel Görevliler</strong>
        <div id="panelOfficialsDesc" class="muted" style="margin-top:6px;">Bilimsel görevli listeleri, roller ve görevlendirme süreçleri bu alt modülde yönetilir.</div>
      </div>
      <div id="panelQA" class="panel" style="display:none;">
        <strong id="panelQATitle">Soru Cevap</strong>
        <div id="panelQADesc" class="muted" style="margin-top:6px;">Soru toplama, moderasyon ve canlı soru-cevap akışları bu alt modülde yönetilir.</div>
      </div>
      <div id="panelSurvey" class="panel" style="display:none;">
        <strong id="panelSurveyTitle">Anket</strong>
        <div id="panelSurveyDesc" class="muted" style="margin-top:6px;">Anket oluşturma, yanıt toplama ve sonuç değerlendirme süreçleri bu alt modülde yönetilir.</div>
      </div>
      <div id="panelCourses" class="panel" style="display:none;">
        <strong id="panelCoursesTitle">Kurslar</strong>
        <div id="panelCoursesDesc" class="muted" style="margin-top:6px;">Kurs tanımları, kontenjan, eğitmen ve katılımcı akışları bu alt modülde yönetilir.</div>
      </div>
      <div id="panelCerts" class="panel" style="display:none;">
        <strong id="panelCertsTitle">Sertifikalar</strong>
        <div id="panelCertsDesc" class="muted" style="margin-top:6px;">Sertifika şablonları, üretim ve teslim süreçleri bu alt modülde yönetilir.</div>
      </div>
      <div id="panelOnlineMeeting" class="panel" style="display:none;">
        <strong id="panelOnlineMeetingTitle">Online Toplantı</strong>
        <div id="panelOnlineMeetingDesc" class="muted" style="margin-top:6px;">Online toplantı odaları, bağlantı bilgileri ve canlı katılım akışı burada yönetilir.</div>
      </div>
      <div id="panelTranslationSessions" class="panel" style="display:none;">
        <strong id="panelTranslationSessionsTitle">Çeviri Oturumları</strong>
        <div id="panelTranslationSessionsDesc" class="muted" style="margin-top:6px;">Çeviri oturumları tercüman modülü ile entegre çalışır. Atanan tercümanlar canlı online çeviri sağlar, katılımcılar telefon uygulamasından dinler.</div>
        <div style="margin-top:8px;">
          <a href="/ceviri-oturumlari-ui" class="tab" style="text-decoration:none;">Çeviri Oturumlarına Git</a>
          <a id="linkInterpreterPanel" href="/tercuman-ui" class="tab alt" style="text-decoration:none;">Tercüman Modülüne Git</a>
        </div>
      </div>
    </div>
  </div>
  <script>
    (function(){
      var ls = document.getElementById("langSelect");
      var saved = localStorage.getItem("ui_lang") || "tr";
      var i18n = {
        tr: {
          pageTitle: "Toplantı Modülü",
          pageDesc: "Bu modül altında bilimsel program, kurslar ve sertifikalar yönetilir.",
          tabProgram: "Bilimsel Program", tabOfficials: "Bilimsel Görevliler", tabQA: "Soru Cevap", tabSurvey: "Anket", tabCourses: "Kurslar", tabCerts: "Sertifikalar",
          tabOnlineMeeting: "Online Toplantı", tabTranslationSessions: "Çeviri Oturumları",
          panelProgramTitle: "Bilimsel Program", panelProgramDesc: "Oturum, konuşmacı, salon ve saat planlaması bu alt modülde yönetilir.",
          panelOfficialsTitle: "Bilimsel Görevliler", panelOfficialsDesc: "Bilimsel görevli listeleri, roller ve görevlendirme süreçleri bu alt modülde yönetilir.",
          panelQATitle: "Soru Cevap", panelQADesc: "Soru toplama, moderasyon ve canlı soru-cevap akışları bu alt modülde yönetilir.",
          panelSurveyTitle: "Anket", panelSurveyDesc: "Anket oluşturma, yanıt toplama ve sonuç değerlendirme süreçleri bu alt modülde yönetilir.",
          panelCoursesTitle: "Kurslar", panelCoursesDesc: "Kurs tanımları, kontenjan, eğitmen ve katılımcı akışları bu alt modülde yönetilir.",
          panelCertsTitle: "Sertifikalar", panelCertsDesc: "Sertifika şablonları, üretim ve teslim süreçleri bu alt modülde yönetilir."
          ,panelOnlineMeetingTitle: "Online Toplantı", panelOnlineMeetingDesc: "Online toplantı odaları, bağlantı bilgileri ve canlı katılım akışı burada yönetilir."
          ,panelTranslationSessionsTitle: "Çeviri Oturumları", panelTranslationSessionsDesc: "Çeviri oturumları tercüman modülü ile entegre çalışır. Atanan tercümanlar canlı online çeviri sağlar, katılımcılar telefon uygulamasından dinler."
        },
        en: {
          pageTitle: "Meeting Module",
          pageDesc: "Scientific program, courses and certificates are managed under this module.",
          tabProgram: "Scientific Program", tabOfficials: "Scientific Staff", tabQA: "Q&A", tabSurvey: "Survey", tabCourses: "Courses", tabCerts: "Certificates",
          tabOnlineMeeting: "Online Meeting", tabTranslationSessions: "Translation Sessions",
          panelProgramTitle: "Scientific Program", panelProgramDesc: "Sessions, speakers, halls and schedule planning are managed in this submodule.",
          panelOfficialsTitle: "Scientific Staff", panelOfficialsDesc: "Scientific staff lists, roles and assignment workflows are managed in this submodule.",
          panelQATitle: "Q&A", panelQADesc: "Question collection, moderation and live Q&A workflows are managed in this submodule.",
          panelSurveyTitle: "Survey", panelSurveyDesc: "Survey creation, response collection and result evaluation are managed in this submodule.",
          panelCoursesTitle: "Courses", panelCoursesDesc: "Course definitions, quotas, instructors and participant flows are managed in this submodule.",
          panelCertsTitle: "Certificates", panelCertsDesc: "Certificate templates, generation and delivery processes are managed in this submodule."
          ,panelOnlineMeetingTitle: "Online Meeting", panelOnlineMeetingDesc: "Online meeting rooms, access links and live participation flow are managed in this submodule."
          ,panelTranslationSessionsTitle: "Translation Sessions", panelTranslationSessionsDesc: "Translation sessions are integrated with the interpreter module. Assigned interpreters provide live online translation and attendees listen via mobile app."
        },
        es: {
          pageTitle: "Módulo de Reunión",
          pageDesc: "En este módulo se gestionan el programa científico, los cursos y los certificados.",
          tabProgram: "Programa Científico", tabOfficials: "Personal Científico", tabQA: "Preguntas y Respuestas", tabSurvey: "Encuesta", tabCourses: "Cursos", tabCerts: "Certificados",
          panelProgramTitle: "Programa Científico", panelProgramDesc: "En este submódulo se gestionan sesiones, ponentes, salas y planificación horaria.",
          panelOfficialsTitle: "Personal Científico", panelOfficialsDesc: "En este submódulo se gestionan listas de personal científico, roles y asignaciones.",
          panelQATitle: "Preguntas y Respuestas", panelQADesc: "En este submódulo se gestionan la recolección de preguntas, moderación y flujos de preguntas en vivo.",
          panelSurveyTitle: "Encuesta", panelSurveyDesc: "En este submódulo se gestionan la creación de encuestas, recolección de respuestas y evaluación de resultados.",
          panelCoursesTitle: "Cursos", panelCoursesDesc: "En este submódulo se gestionan definiciones de cursos, cupos, instructores y flujo de participantes.",
          panelCertsTitle: "Certificados", panelCertsDesc: "En este submódulo se gestionan plantillas, generación y entrega de certificados."
        },
        ar: {
          pageTitle: "???? ??????????",
          pageDesc: "??? ??? ??? ?????? ????? ???????? ?????? ???????? ?????????.",
          tabProgram: "???????? ??????", tabOfficials: "??????? ???????", tabQA: "??????? ????????", tabSurvey: "?????????", tabCourses: "???????", tabCerts: "????????",
          panelProgramTitle: "???????? ??????", panelProgramDesc: "??? ????? ??????? ?????????? ???????? ?????? ????? ?? ??? ?????? ???????.",
          panelOfficialsTitle: "??????? ???????", panelOfficialsDesc: "??? ????? ????? ??????? ??????? ???????? ??????? ??????? ?? ??? ?????? ???????.",
          panelQATitle: "??????? ????????", panelQADesc: "??? ????? ??? ??????? ???????? ????? ??????? ???????? ?? ??? ?????? ???????.",
          panelSurveyTitle: "?????????", panelSurveyDesc: "??? ????? ????? ??????????? ???? ?????? ?????? ??????? ?? ??? ?????? ???????.",
          panelCoursesTitle: "???????", panelCoursesDesc: "??? ????? ??????? ??????? ?????? ????????? ????? ????????? ?? ??? ?????? ???????.",
          panelCertsTitle: "????????", panelCertsDesc: "??? ????? ????? ???????? ???????? ???????? ?? ??? ?????? ???????."
        },
        it: {
          pageTitle: "Modulo Riunione",
          pageDesc: "In questo modulo vengono gestiti programma scientifico, corsi e certificati.",
          tabProgram: "Programma Scientifico", tabOfficials: "Staff Scientifico", tabQA: "Domande e Risposte", tabSurvey: "Sondaggio", tabCourses: "Corsi", tabCerts: "Certificati",
          panelProgramTitle: "Programma Scientifico", panelProgramDesc: "In questo sottomodulo si gestiscono sessioni, relatori, sale e pianificazione oraria.",
          panelOfficialsTitle: "Staff Scientifico", panelOfficialsDesc: "In questo sottomodulo si gestiscono liste staff scientifico, ruoli e assegnazioni.",
          panelQATitle: "Domande e Risposte", panelQADesc: "In questo sottomodulo si gestiscono raccolta domande, moderazione e flussi Q&A dal vivo.",
          panelSurveyTitle: "Sondaggio", panelSurveyDesc: "In questo sottomodulo si gestiscono creazione sondaggi, raccolta risposte e valutazione risultati.",
          panelCoursesTitle: "Corsi", panelCoursesDesc: "In questo sottomodulo si gestiscono definizioni dei corsi, capienza, istruttori e flussi partecipanti.",
          panelCertsTitle: "Certificati", panelCertsDesc: "In questo sottomodulo si gestiscono modelli, produzione e consegna dei certificati."
        },
        ru: {
          pageTitle: "?????? ??????",
          pageDesc: "? ???? ?????? ??????????? ??????? ?????????, ????? ? ???????????.",
          tabProgram: "??????? ?????????", tabOfficials: "??????? ????????", tabQA: "??????? ? ??????", tabSurvey: "?????", tabCourses: "?????", tabCerts: "???????????",
          panelProgramTitle: "??????? ?????????", panelProgramDesc: "? ???? ????????? ??????????? ??????, ??????????, ???? ? ??????????.",
          panelOfficialsTitle: "??????? ????????", panelOfficialsDesc: "? ???? ????????? ??????????? ?????? ???????? ?????????, ???? ? ??????????.",
          panelQATitle: "??????? ? ??????", panelQADesc: "? ???? ????????? ??????????? ???? ????????, ????????? ? ?????? ????? ?????? Q&A.",
          panelSurveyTitle: "?????", panelSurveyDesc: "? ???? ????????? ??????????? ???????? ???????, ???? ??????? ? ?????? ???????????.",
          panelCoursesTitle: "?????", panelCoursesDesc: "? ???? ????????? ??????????? ????????? ??????, ?????, ??????????? ? ?????? ??????????.",
          panelCertsTitle: "???????????", panelCertsDesc: "? ???? ????????? ??????????? ???????, ?????? ? ?????? ????????????."
        }
      };
      function applyLang(lang){
        var pack = i18n[lang] || i18n.tr;
        var keys = Object.keys(pack);
        for (var i = 0; i < keys.length; i++) {
          var k = keys[i];
          var el = document.getElementById(k);
          if (el) el.textContent = pack[k];
        }
        document.documentElement.lang = lang;
        document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
        localStorage.setItem("ui_lang", lang);
        if (ls) ls.value = lang;
      }
      applyLang(saved);
      if (ls) ls.addEventListener("change", function(){
        applyLang(ls.value || "tr");
      });
    })();
    (async function(){
      var token = localStorage.getItem('access_token') || '';
      var badge = document.getElementById('activeProjectBadge');
      if (!token || !badge) return;
      try {
        var res = await fetch('/auth/me', { headers: { Authorization: `Bearer ${token}` } });
        var me = await res.json();
        if (!res.ok || !me) return;
        var pName = me.active_project_name || '-';
        var pCode = me.active_project_code || (me.active_project_id ? ('ID-' + me.active_project_id) : '-');
        badge.textContent = `AKTİF PROJE: ${pName} (${pCode})`;
      } catch (_) {}
    })();
    const tabs = {
      tabProgram: "panelProgram",
      tabOfficials: "panelOfficials",
      tabQA: "panelQA",
      tabSurvey: "panelSurvey",
      tabCourses: "panelCourses",
      tabCerts: "panelCerts",
      tabOnlineMeeting: "panelOnlineMeeting",
      tabTranslationSessions: "panelTranslationSessions"
    };
    const show = (tabId) => {
      Object.keys(tabs).forEach((id) => {
        const tab = document.getElementById(id);
        const panel = document.getElementById(tabs[id]);
        if (id === tabId) {
          tab.classList.remove("alt");
          panel.style.display = "";
        } else {
          tab.classList.add("alt");
          panel.style.display = "none";
        }
      });
    };
    Object.keys(tabs).forEach((id) => {
      document.getElementById(id).addEventListener("click", () => show(id));
    });
  </script>
  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""


@app.get("/tercuman-ui", response_class=HTMLResponse)
def tercuman_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Tercüman Modülü</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .head { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; position:relative; }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn { background: rgba(255,255,255,0.18); color:#fff; text-decoration:none; border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px; }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .btn { border:0; border-radius:8px; background:#2b7fff; color:#fff; padding:8px 12px; cursor:pointer; text-decoration:none; display:inline-block; }
    .btn.alt { background:#5c6b82; }
    .row { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
    table { width:100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }
    th, td { border:1px solid #dde4ef; padding:8px; text-align:left; }
    th { background:#f0f5ff; }
    .muted { color:#5c6b82; font-size:13px; }
    .switch-wrap { display:inline-flex; align-items:center; gap:8px; }
    .switch { position: relative; display: inline-block; width: 46px; height: 24px; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; cursor: pointer; inset: 0; background: #c62828; transition: .2s; border-radius: 999px; }
    .slider:before {
      position: absolute; content: ""; height: 18px; width: 18px; left: 3px; top: 3px;
      background: #fff; transition: .2s; border-radius: 50%;
    }
    .switch input:checked + .slider { background: #0a7a2f; }
    .switch input:checked + .slider:before { transform: translateX(22px); }
    .status-chip {
      border-radius: 999px; padding: 2px 8px; font-size: 11px; font-weight: 700;
      border: 1px solid transparent;
      display: inline-flex; align-items: center; gap: 6px;
    }
    .status-chip.active { color: #0a7a2f; background:#e8f7ee; border-color:#98d9b1; }
    .status-chip.passive { color: #b91c1c; background:#fdecec; border-color:#f4b6b6; }
    .neon-dot {
      width: 8px; height: 8px; border-radius: 50%; display: inline-block;
      box-shadow: 0 0 6px currentColor, 0 0 12px currentColor;
    }
    .neon-dot.green { color: #00e676; background: #00e676; }
    .neon-dot.red { color: #ff1744; background: #ff1744; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn" href="/toplanti-ui">Toplantı Modülü</a>
        <a class="m-btn" href="/ceviri-oturumlari-ui">Çeviri Oturumları</a>
        <a class="m-btn active" href="/tercuman-ui">Tercüman Modülü</a>
      </div>
    </div>
    <div class="box">
      <h3 style="margin:0 0 8px 0;">Tercüman Ana Modülü</h3>
      <div class="row">
        <a class="btn" href="/ceviri-oturumlari-ui">Çeviri Oturumları Yönetimi</a>
      </div>
      <div id="msg" class="muted"></div>
      <table>
        <thead><tr><th>OTURUM</th><th>DİL</th><th>SAAT</th><th>DURUM</th><th>CANLI AÇ/KAPA</th><th>KATILIM LINK</th></tr></thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
  </div>
  <script>
    (function(){
      const token = localStorage.getItem('access_token')
        || sessionStorage.getItem('access_token')
        || localStorage.getItem('token')
        || sessionStorage.getItem('token')
        || '';
      const rows = document.getElementById('rows');
      const msg = document.getElementById('msg');
      const headers = () => token ? ({ Authorization: `Bearer ${token}` }) : ({});
      const esc = (v) => String(v || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      const roleAllowed = (role) => {
        let r = String(role || '').toLowerCase();
        if (r === 'admin') r = 'tenant_admin';
        if (r === 'manager') r = 'tenant_manager';
        if (r === 'operator') r = 'tenant_operator';
        if (r.includes('superadmin')) return true;
        return ['interpreter','tenant_manager','tenant_admin','supertranslator','superadmin_staff','superadmin'].includes(r);
      };
      const moduleAllowed = (me) => {
        const mods = Array.isArray(me && me.visible_modules) ? me.visible_modules.map((x) => String(x || '').toLowerCase()) : [];
        return mods.includes('tercuman') || mods.includes('yonetim');
      };

      const ensureModuleAccess = async () => {
        if (!token) {
          msg.textContent = 'Oturum bulunamadı. Lütfen tekrar giriş yapın.';
          throw new Error('missing_token');
        }
        const meRes = await fetch('/auth/me', { headers: headers() });
        const me = await meRes.json().catch(() => ({}));
        if (!meRes.ok) {
          msg.textContent = me.detail || 'Oturum doğrulanamadı.';
          throw new Error('auth_failed');
        }
        if (!(roleAllowed(me.role) || moduleAllowed(me))) {
          msg.textContent = 'Bu modüle erişim yetkiniz yok.';
          throw new Error('forbidden');
        }
      };

      const load = async () => {
        if (!token) { msg.textContent = 'Oturum bulunamadı. Lütfen tekrar giriş yapın.'; return; }
        const res = await fetch('/translation/my-sessions', { headers: headers() });
        const data = await res.json().catch(() => []);
        if (!res.ok) { msg.textContent = data.detail || 'Oturumlar alınamadı'; return; }
        const allItems = Array.isArray(data) ? data : [];
        const isActive = (x) => {
          const st = String(x.status || '').toLowerCase();
          return !!x.is_live || st === 'live' || st === 'active' || st === 'canli';
        };
        const list = allItems.slice().sort((a, b) => {
          const av = isActive(a) ? 1 : 0;
          const bv = isActive(b) ? 1 : 0;
          return bv - av;
        });
        rows.innerHTML = list.map((x) => {
          const starts = x.starts_at || '-';
          const isLive = !!x.is_live;
          const statusText = isLive ? 'Canlı' : 'Beklemede';
          const statusClass = isLive ? 'active' : 'passive';
          const dotClass = isLive ? 'green' : 'red';
          const listen = '/canli-ceviri?code=' + encodeURIComponent(x.access_code || '');
          return '<tr>'
            + '<td>' + esc(x.title) + '</td>'
            + '<td>' + esc(x.language) + '</td>'
            + '<td>' + esc(starts) + '</td>'
            + '<td>'
              + '<span class="status-chip ' + statusClass + '"><span class="neon-dot ' + dotClass + '"></span>' + statusText + '</span>'
            + '</td>'
            + '<td>'
              + '<span class="switch-wrap">'
                + '<label class="switch">'
                  + '<input class="live-switch" type="checkbox" data-sid="' + x.session_id + '" data-lang="' + esc(x.language) + '" ' + (isLive ? 'checked' : '') + ' />'
                  + '<span class="slider"></span>'
                + '</label>'
                + '<span>' + (isLive ? 'Canlı' : 'Beklemede') + '</span>'
              + '</span>'
            + '</td>'
            + '<td><a href="' + listen + '" target="_blank">' + esc(x.access_code || '-') + '</a></td>'
            + '</tr>';
        }).join('');
        msg.textContent = list.length + ' erişilebilir tercüman oturumu listelendi.';
      };

      rows.addEventListener('change', async (e) => {
        const sw = e.target.closest('input.live-switch');
        if (!sw) return;
        const sid = parseInt(sw.getAttribute('data-sid') || '0', 10);
        const lang = sw.getAttribute('data-lang') || '';
        if (!sid) return;
        const url = sw.checked ? ('/translation/sessions/' + sid + '/go-live') : ('/translation/sessions/' + sid + '/end-live');
        sw.disabled = true;
        const res = await fetch(url, { method:'POST', headers:{...headers(), 'Content-Type':'application/json'}, body: JSON.stringify({ language: lang }) });
        const out = await res.json().catch(() => ({}));
        if (!res.ok) { msg.textContent = out.detail || 'İşlem başarısız'; sw.disabled = false; await load(); return; }
        await load();
      });

      (async () => {
        await ensureModuleAccess();
        await load();
        setInterval(() => { load().catch(() => {}); }, 15000);
      })().catch(() => { if (!msg.textContent) msg.textContent = 'Liste yüklenemedi'; });
    })();
  </script>
</body>
</html>
"""


@app.get("/ceviri-oturumlari-ui", response_class=HTMLResponse)
def ceviri_oturumlari_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Çeviri Oturumları</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); color:#1c2635; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .head { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn { background: rgba(255,255,255,0.18); color:#fff; text-decoration:none; border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px; }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .row { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
    input, select { border:1px solid #cfd9e8; border-radius:7px; padding:7px 8px; font-size:12px; }
    .btn { border:0; border-radius:8px; padding:8px 12px; cursor:pointer; color:#fff; background:#2b7fff; }
    .btn.alt { background:#5c6b82; }
    table { width:100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }
    th, td { border:1px solid #dde4ef; padding:8px; text-align:left; vertical-align: top; }
    th { background:#f0f5ff; }
    .muted { color:#5c6b82; font-size:13px; margin-top:8px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn" href="/toplanti-ui">Toplantı Modülü</a>
        <a class="m-btn active" href="/ceviri-oturumlari-ui">Çeviri Oturumları</a>
        <a id="navInterpreterCeviri" class="m-btn" href="/tercuman-ui">Tercüman Modülü</a>
      </div>
    </div>
    <div class="box">
      <h3 style="margin:0 0 8px 0;">Çeviri Oturumları</h3>
      <div class="row">
        <input id="title" placeholder="Oturum Başlığı" style="min-width:260px;" />
        <input id="startsAt" placeholder="Başlangıç (YYYY-MM-DD HH:MM)" style="min-width:180px;" />
        <input id="endsAt" placeholder="Bitiş (YYYY-MM-DD HH:MM)" style="min-width:180px;" />
        <input id="meetingKey" placeholder="Toplantı Anahtarı (ops.)" style="min-width:160px;" />
        <button id="createBtn" class="btn" type="button">Oturum Oluştur</button>
      </div>
      <div class="row">
        <select id="sessionSel" style="min-width:260px;"><option value="">Oturum Seçiniz</option></select>
        <select id="interpreterSel" style="min-width:220px;"><option value="">Tercüman Seçiniz</option></select>
        <select id="langSel" style="min-width:120px;">
          <option value="tr">TR</option><option value="en">EN</option><option value="ar">AR</option>
          <option value="ru">RU</option><option value="es">ES</option><option value="fr">FR</option>
        </select>
        <button id="assignBtn" class="btn alt" type="button">Tercüman Ata</button>
      </div>
      <div id="msg" class="muted"></div>
      <table>
        <thead><tr><th>ID</th><th>OTURUM</th><th>ZAMAN</th><th>DURUM</th><th>KOD</th><th>ATAMALAR</th><th>DİNLEME</th></tr></thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
  </div>
  <script>
    (function(){
      const token = localStorage.getItem('access_token')
        || sessionStorage.getItem('access_token')
        || localStorage.getItem('token')
        || sessionStorage.getItem('token')
        || '';
      const headers = () => token ? ({ Authorization: `Bearer ${token}` }) : ({});
      const rows = document.getElementById('rows');
      const msg = document.getElementById('msg');
      const sessionSel = document.getElementById('sessionSel');
      const interpreterSel = document.getElementById('interpreterSel');
      const title = document.getElementById('title');
      const startsAt = document.getElementById('startsAt');
      const endsAt = document.getElementById('endsAt');
      const meetingKey = document.getElementById('meetingKey');
      const createBtn = document.getElementById('createBtn');
      const assignBtn = document.getElementById('assignBtn');
      const langSel = document.getElementById('langSel');
      const esc = (v) => String(v || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      const roleAllowed = (role) => {
        let r = String(role || '').toLowerCase();
        if (r === 'admin') r = 'tenant_admin';
        if (r === 'manager') r = 'tenant_manager';
        if (r === 'operator') r = 'tenant_operator';
        if (r.includes('superadmin')) return true;
        return ['interpreter','tenant_manager','tenant_admin','supertranslator','superadmin_staff','superadmin'].includes(r);
      };
      const moduleAllowed = (me) => {
        const mods = Array.isArray(me && me.visible_modules) ? me.visible_modules.map((x) => String(x || '').toLowerCase()) : [];
        return mods.includes('tercuman') || mods.includes('yonetim');
      };
      const applyInterpreterNavVisibility = async () => {
        const meRes = await fetch('/auth/me', { headers: headers() });
        const me = await meRes.json().catch(() => ({}));
        if (!meRes.ok) return;
        if (!(roleAllowed(me.role) || moduleAllowed(me))) {
          const navInterpreter = document.getElementById('navInterpreterCeviri');
          if (navInterpreter) navInterpreter.style.display = 'none';
        }
      };

      const loadUsers = async () => {
        const [res, meRes] = await Promise.all([
          fetch('/users', { headers: headers() }),
          fetch('/auth/me', { headers: headers() }),
        ]);
        const data = await res.json().catch(() => []);
        const me = await meRes.json().catch(() => ({}));
        if (!res.ok) return;
        const users = Array.isArray(data) ? data.slice() : [];
        if (meRes.ok && me && me.id != null) {
          const exists = users.some((u) => String(u.id) === String(me.id));
          if (!exists) {
            users.unshift({
              id: me.id,
              username: me.username || 'Admin',
              role: me.role || 'admin',
            });
          }
        }
        interpreterSel.innerHTML = '<option value="">Tercüman Seçiniz</option>' + users.map((u) => `<option value="${u.id}">${esc(u.username)} (${esc(u.role || '-')})</option>`).join('');
      };

      const loadSessions = async () => {
        const res = await fetch('/translation/sessions', { headers: headers() });
        const data = await res.json().catch(() => []);
        if (!res.ok) { msg.textContent = data.detail || 'Oturumlar alınamadı'; return; }
        sessionSel.innerHTML = '<option value="">Oturum Seçiniz</option>' + (data || []).map((s) => `<option value="${s.id}">${esc(s.title)}</option>`).join('');
        rows.innerHTML = (data || []).map((s) => {
          const assigns = (s.assignments || []).map((a) => esc(a.interpreter_username) + ' / ' + esc(a.language) + (a.is_live ? ' (canlı)' : '')).join('<br/>');
          const link = '/canli-ceviri?code=' + encodeURIComponent(s.access_code || '');
          return '<tr>'
            + '<td>' + s.id + '</td>'
            + '<td>' + esc(s.title) + '</td>'
            + '<td>' + esc((s.starts_at || '-') + ' - ' + (s.ends_at || '-')) + '</td>'
            + '<td>' + esc(s.status || '-') + '</td>'
            + '<td>' + esc(s.access_code || '-') + '</td>'
            + '<td>' + (assigns || '-') + '</td>'
            + '<td><a href="' + link + '" target="_blank">Dinleme Linki</a></td>'
            + '</tr>';
        }).join('');
        msg.textContent = (data || []).length + ' oturum listelendi.';
      };

      createBtn.addEventListener('click', async () => {
        const payload = { title: title.value || '', starts_at: startsAt.value || '', ends_at: endsAt.value || '', meeting_key: meetingKey.value || '' };
        const res = await fetch('/translation/sessions', { method:'POST', headers:{...headers(), 'Content-Type':'application/json'}, body: JSON.stringify(payload) });
        const out = await res.json().catch(() => ({}));
        if (!res.ok) { msg.textContent = out.detail || 'Oturum oluşturulamadı'; return; }
        msg.textContent = 'Oturum oluşturuldu: ' + (out.access_code || '');
        await loadSessions();
      });

      assignBtn.addEventListener('click', async () => {
        const sid = parseInt(sessionSel.value || '0', 10);
        const uid = parseInt(interpreterSel.value || '0', 10);
        const lang = langSel.value || 'tr';
        if (!sid || !uid) { msg.textContent = 'Oturum ve tercüman seçiniz.'; return; }
        const res = await fetch('/translation/sessions/' + sid + '/assign', { method:'POST', headers:{...headers(), 'Content-Type':'application/json'}, body: JSON.stringify({ interpreter_user_id: uid, language: lang }) });
        const out = await res.json().catch(() => ({}));
        if (!res.ok) { msg.textContent = out.detail || 'Atama yapılamadı'; return; }
        msg.textContent = 'Tercüman atandı.';
        await loadSessions();
      });

      (async () => {
        if (!token) { msg.textContent = 'Oturum bulunamadı. Lütfen tekrar giriş yapın.'; return; }
        await applyInterpreterNavVisibility();
        await loadUsers();
        await loadSessions();
      })().catch(() => { msg.textContent = 'Ekran yüklenemedi.'; });
    })();
  </script>
</body>
</html>
"""


@app.get("/canli-ceviri", response_class=HTMLResponse)
def canli_ceviri_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Canlı Çeviri Dinleme</title>
  <style>
    body { font-family: Arial, sans-serif; margin:0; background:#f4f7ff; color:#1c2635; }
    .wrap { max-width: 760px; margin: 0 auto; padding: 20px; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .row { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
    .btn { border:0; border-radius:8px; background:#2b7fff; color:#fff; padding:8px 12px; cursor:pointer; }
    .btn.alt { background:#5c6b82; }
    .muted { color:#5c6b82; font-size:13px; margin-top:8px; }
    select, input { border:1px solid #cfd9e8; border-radius:7px; padding:7px 8px; font-size:12px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="box">
      <h3 style="margin:0 0 8px 0;">Canlı Çeviri Dinleme</h3>
      <div class="row">
        <input id="code" placeholder="Oturum Kodu" />
        <button id="loadBtn" class="btn alt" type="button">Oturumu Yükle</button>
      </div>
      <div class="row">
        <select id="lang"></select>
        <button id="joinBtn" class="btn" type="button">Dinlemeye Başla</button>
        <button id="leaveBtn" class="btn alt" type="button">Ayrıl</button>
      </div>
      <div id="msg" class="muted"></div>
    </div>
  </div>
  <script>
    (function(){
      const q = new URLSearchParams(window.location.search);
      const codeEl = document.getElementById('code');
      const langEl = document.getElementById('lang');
      const msg = document.getElementById('msg');
      const loadBtn = document.getElementById('loadBtn');
      const joinBtn = document.getElementById('joinBtn');
      const leaveBtn = document.getElementById('leaveBtn');
      const deviceId = localStorage.getItem('listener_device_id') || ('D-' + Math.random().toString(36).slice(2, 10).toUpperCase());
      localStorage.setItem('listener_device_id', deviceId);
      codeEl.value = q.get('code') || '';

      const loadSession = async () => {
        const code = (codeEl.value || '').trim().toUpperCase();
        if (!code) { msg.textContent = 'Kod giriniz.'; return; }
        const res = await fetch('/translation/sessions/by-code/' + encodeURIComponent(code));
        const out = await res.json().catch(() => ({}));
        if (!res.ok) { msg.textContent = out.detail || 'Oturum bulunamadı'; return; }
        langEl.innerHTML = (out.languages || []).map((l) => '<option value="' + (l.language || '') + '">' + (l.language || '').toUpperCase() + (l.is_live ? ' (canlı)' : '') + '</option>').join('');
        msg.textContent = 'Oturum: ' + (out.title || '-') + ' / Durum: ' + (out.status || '-');
      };

      const sendEvent = async (action) => {
        const code = (codeEl.value || '').trim().toUpperCase();
        const lang = (langEl.value || '').trim().toLowerCase();
        if (!code) return;
        const res = await fetch('/translation/listener-event', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ code: code, language: lang, device_id: deviceId, action: action }) });
        const out = await res.json().catch(() => ({}));
        if (!res.ok) { msg.textContent = out.detail || 'İşlem başarısız'; return; }
        msg.textContent = 'Aktif dinleyici (tahmini): ' + (out.active_listeners_estimate != null ? out.active_listeners_estimate : '-');
      };

      loadBtn.addEventListener('click', () => loadSession().catch(() => { msg.textContent = 'Yüklenemedi'; }));
      joinBtn.addEventListener('click', () => sendEvent('join').catch(() => { msg.textContent = 'Başlatılamadı'; }));
      leaveBtn.addEventListener('click', () => sendEvent('leave').catch(() => { msg.textContent = 'Sonlandırılamadı'; }));
      if (codeEl.value) loadSession().catch(() => {});
    })();
  </script>
</body>
</html>
"""


@app.get("/translation/sessions")
def list_translation_sessions(
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    scoped_project_id, _ = _resolve_project_scope_for_user(db, current_user, project_id)
    if scoped_project_id is None:
        raise HTTPException(status_code=400, detail="Active project required")
    project = db.query(Project).filter(Project.id == scoped_project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tenant_id = int(project.tenant_id or 0)
    if not is_superadmin(current_user) and tenant_id != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="Forbidden")

    sessions = (
        db.query(TranslationSession)
        .filter(TranslationSession.project_id == int(scoped_project_id), TranslationSession.tenant_id == tenant_id)
        .order_by(TranslationSession.created_at.desc())
        .all()
    )
    out = []
    for s in sessions:
        assigns = (
            db.query(TranslationAssignment, User)
            .join(User, User.id == TranslationAssignment.interpreter_user_id)
            .filter(TranslationAssignment.session_id == s.id)
            .all()
        )
        out.append(
            {
                "id": s.id,
                "title": s.title,
                "meeting_key": s.meeting_key,
                "starts_at": s.starts_at,
                "ends_at": s.ends_at,
                "status": s.status,
                "access_code": s.access_code,
                "assignments": [
                    {
                        "id": a.id,
                        "interpreter_user_id": a.interpreter_user_id,
                        "interpreter_username": u.username,
                        "language": a.language,
                        "is_live": a.is_live,
                    }
                    for a, u in assigns
                ],
            }
        )
    return out


@app.post("/translation/sessions")
def create_translation_session(
    payload: dict,
    req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    scoped_project_id, _ = _resolve_project_scope_for_user(db, current_user, payload.get("project_id"))
    if scoped_project_id is None:
        raise HTTPException(status_code=400, detail="Active project required")
    project = db.query(Project).filter(Project.id == scoped_project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tenant_id = int(project.tenant_id or 0)
    if not is_superadmin(current_user) and tenant_id != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="Forbidden")

    title = str(payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    starts_at = str(payload.get("starts_at") or "").strip() or None
    ends_at = str(payload.get("ends_at") or "").strip() or None
    meeting_key = str(payload.get("meeting_key") or "").strip() or None

    access_code = ""
    for _ in range(20):
        cand = _safe_translation_code()
        exists = db.query(TranslationSession).filter(TranslationSession.access_code == cand).first()
        if not exists:
            access_code = cand
            break
    if not access_code:
        raise HTTPException(status_code=500, detail="access_code generation failed")

    row = TranslationSession(
        tenant_id=tenant_id,
        project_id=int(scoped_project_id),
        title=title,
        meeting_key=meeting_key,
        starts_at=starts_at,
        ends_at=ends_at,
        access_code=access_code,
        status="planned",
        created_by_user_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "access_code": row.access_code,
        "listener_url": _public_listener_url(req, row.access_code),
    }


@app.post("/translation/sessions/{session_id}/assign")
def assign_translation_session(
    session_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    session_row = db.query(TranslationSession).filter(TranslationSession.id == session_id).first()
    if not session_row:
        raise HTTPException(status_code=404, detail="Session not found")
    if not is_superadmin(current_user) and int(session_row.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="Forbidden")

    interpreter_user_id = int(payload.get("interpreter_user_id") or 0)
    language = str(payload.get("language") or "").strip().lower()
    if not interpreter_user_id or not language:
        raise HTTPException(status_code=400, detail="interpreter_user_id and language are required")
    user = db.query(User).filter(User.id == interpreter_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Interpreter user not found")
    if not is_superadmin(current_user) and int(user.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="Interpreter is outside tenant")

    row = (
        db.query(TranslationAssignment)
        .filter(
            TranslationAssignment.session_id == session_row.id,
            TranslationAssignment.interpreter_user_id == interpreter_user_id,
            TranslationAssignment.language == language,
        )
        .first()
    )
    if not row:
        row = TranslationAssignment(
            tenant_id=int(session_row.tenant_id),
            project_id=int(session_row.project_id),
            session_id=int(session_row.id),
            interpreter_user_id=interpreter_user_id,
            language=language,
            is_live=False,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "session_id": row.session_id,
        "interpreter_user_id": row.interpreter_user_id,
        "language": row.language,
        "is_live": row.is_live,
    }


@app.get("/translation/my-sessions")
def list_my_translation_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if not can_access_interpreter_module(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    # Interpreters see only their own assignments.
    if role_level(current_user.role) < role_level("tenant_manager"):
        query = db.query(TranslationAssignment, TranslationSession).join(
            TranslationSession, TranslationSession.id == TranslationAssignment.session_id
        )
        if not (is_superadmin(current_user) or is_supertranslator(current_user)):
            query = query.filter(TranslationAssignment.tenant_id == current_user.tenant_id)
        query = query.filter(TranslationAssignment.interpreter_user_id == current_user.id)
        rows = query.order_by(TranslationSession.starts_at.asc(), TranslationSession.created_at.desc()).all()
        return [
            {
                "assignment_id": a.id,
                "session_id": s.id,
                "title": s.title,
                "starts_at": s.starts_at,
                "ends_at": s.ends_at,
                "status": s.status,
                "access_code": s.access_code,
                "language": a.language,
                "is_live": a.is_live,
            }
            for a, s in rows
        ]

    # Managers/admins/superadmins see all sessions they can access (tenant/project scoped).
    active_project, management_scope = _active_project_and_management_scope(db, current_user)
    s_query = db.query(TranslationSession)
    if not (is_superadmin(current_user) or is_supertranslator(current_user)):
        s_query = s_query.filter(TranslationSession.tenant_id == current_user.tenant_id)
    if not management_scope:
        if active_project is None:
            raise HTTPException(status_code=400, detail="Active project required")
        s_query = s_query.filter(TranslationSession.project_id == int(active_project.id))
    elif active_project is not None and not _is_management_project(active_project):
        s_query = s_query.filter(TranslationSession.project_id == int(active_project.id))

    sessions = s_query.order_by(TranslationSession.starts_at.asc(), TranslationSession.created_at.desc()).all()
    out: list[dict] = []
    for s in sessions:
        assigns = (
            db.query(TranslationAssignment)
            .filter(TranslationAssignment.session_id == s.id)
            .order_by(TranslationAssignment.language.asc())
            .all()
        )
        if not assigns:
            out.append(
                {
                    "assignment_id": None,
                    "session_id": s.id,
                    "title": s.title,
                    "starts_at": s.starts_at,
                    "ends_at": s.ends_at,
                    "status": s.status,
                    "access_code": s.access_code,
                    "language": "-",
                    "is_live": False,
                }
            )
            continue
        for a in assigns:
            out.append(
                {
                    "assignment_id": a.id,
                    "session_id": s.id,
                    "title": s.title,
                    "starts_at": s.starts_at,
                    "ends_at": s.ends_at,
                    "status": s.status,
                    "access_code": s.access_code,
                    "language": a.language,
                    "is_live": a.is_live,
                }
            )
    return out


@app.post("/translation/sessions/{session_id}/go-live")
def translation_go_live(
    session_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    payload = payload or {}
    if not can_access_interpreter_module(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    language = str(payload.get("language") or "").strip().lower()
    q = db.query(TranslationAssignment).filter(TranslationAssignment.session_id == session_id)
    if language:
        q = q.filter(TranslationAssignment.language == language)
    if not (is_superadmin(current_user) or is_supertranslator(current_user)):
        if role_level(current_user.role) < role_level("tenant_manager"):
            q = q.filter(TranslationAssignment.interpreter_user_id == current_user.id)
        q = q.filter(TranslationAssignment.tenant_id == current_user.tenant_id)
    row = q.first()
    if not row:
        raise HTTPException(status_code=404, detail="Assignment not found")
    row.is_live = True
    s = db.query(TranslationSession).filter(TranslationSession.id == session_id).first()
    if s:
        s.status = "live"
    db.commit()
    return {"ok": True}


@app.post("/translation/sessions/{session_id}/end-live")
def translation_end_live(
    session_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    payload = payload or {}
    if not can_access_interpreter_module(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    language = str(payload.get("language") or "").strip().lower()
    q = db.query(TranslationAssignment).filter(TranslationAssignment.session_id == session_id)
    if language:
        q = q.filter(TranslationAssignment.language == language)
    if not (is_superadmin(current_user) or is_supertranslator(current_user)):
        if role_level(current_user.role) < role_level("tenant_manager"):
            q = q.filter(TranslationAssignment.interpreter_user_id == current_user.id)
        q = q.filter(TranslationAssignment.tenant_id == current_user.tenant_id)
    row = q.first()
    if not row:
        raise HTTPException(status_code=404, detail="Assignment not found")
    row.is_live = False
    s = db.query(TranslationSession).filter(TranslationSession.id == session_id).first()
    if s:
        live_count = (
            db.query(TranslationAssignment)
            .filter(TranslationAssignment.session_id == session_id, TranslationAssignment.is_live == True)  # noqa: E712
            .count()
        )
        s.status = "live" if live_count > 0 else "planned"
    db.commit()
    return {"ok": True}


@app.get("/translation/sessions/by-code/{access_code}")
def get_translation_session_by_code(access_code: str, db: Session = Depends(get_db)):
    code = str(access_code or "").strip().upper()
    row = db.query(TranslationSession).filter(TranslationSession.access_code == code).first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    assigns = (
        db.query(TranslationAssignment)
        .filter(TranslationAssignment.session_id == row.id)
        .order_by(TranslationAssignment.language.asc())
        .all()
    )
    langs = []
    seen = set()
    for a in assigns:
        lg = str(a.language or "").strip().lower()
        if not lg or lg in seen:
            continue
        seen.add(lg)
        langs.append({"language": lg, "is_live": bool(a.is_live)})
    return {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "starts_at": row.starts_at,
        "ends_at": row.ends_at,
        "access_code": row.access_code,
        "languages": langs,
    }


@app.post("/translation/listener-event")
def translation_listener_event(payload: dict, db: Session = Depends(get_db)):
    code = str(payload.get("code") or "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="code is required")
    action = str(payload.get("action") or "").strip().lower()
    if action not in {"join", "leave", "heartbeat"}:
        raise HTTPException(status_code=400, detail="action must be join|leave|heartbeat")
    language = str(payload.get("language") or "").strip().lower() or None
    device_id = str(payload.get("device_id") or "").strip() or None

    s = db.query(TranslationSession).filter(TranslationSession.access_code == code).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    ev = TranslationListenerEvent(
        tenant_id=int(s.tenant_id),
        project_id=int(s.project_id),
        session_id=int(s.id),
        language=language,
        device_id=device_id,
        action=action,
    )
    db.add(ev)
    db.commit()
    joins = (
        db.query(TranslationListenerEvent)
        .filter(TranslationListenerEvent.session_id == s.id, TranslationListenerEvent.action == "join")
        .count()
    )
    leaves = (
        db.query(TranslationListenerEvent)
        .filter(TranslationListenerEvent.session_id == s.id, TranslationListenerEvent.action == "leave")
        .count()
    )
    return {"ok": True, "session_id": s.id, "active_listeners_estimate": max(joins - leaves, 0)}


@app.get("/translation/sessions/{session_id}/stats")
def translation_session_stats(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    s = db.query(TranslationSession).filter(TranslationSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if not is_superadmin(current_user) and int(s.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="Forbidden")

    total_join = (
        db.query(TranslationListenerEvent)
        .filter(TranslationListenerEvent.session_id == s.id, TranslationListenerEvent.action == "join")
        .count()
    )
    total_leave = (
        db.query(TranslationListenerEvent)
        .filter(TranslationListenerEvent.session_id == s.id, TranslationListenerEvent.action == "leave")
        .count()
    )
    by_lang: dict[str, dict[str, int]] = {}
    events = db.query(TranslationListenerEvent).filter(TranslationListenerEvent.session_id == s.id).all()
    for ev in events:
        lg = str(ev.language or "unknown")
        if lg not in by_lang:
            by_lang[lg] = {"join": 0, "leave": 0, "heartbeat": 0}
        by_lang[lg][str(ev.action)] = by_lang[lg].get(str(ev.action), 0) + 1
    return {
        "session_id": s.id,
        "title": s.title,
        "status": s.status,
        "active_listeners_estimate": max(total_join - total_leave, 0),
        "by_language": by_lang,
    }


@app.get("/tenants")
def list_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin required")
    rows = db.query(Tenant).order_by(Tenant.created_at.desc()).all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "token_balance": row.token_balance,
            "is_active": row.is_active,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@app.post("/tenants")
def create_tenant(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin required")
    name = str(payload.get("name") or "").strip()
    token_balance = int(payload.get("token_balance") or 0)
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if db.query(Tenant).filter(Tenant.name == name).first():
        raise HTTPException(status_code=409, detail="tenant already exists")
    tenant = Tenant(name=name, token_balance=max(0, token_balance), is_active=True)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    _ensure_management_project_for_tenant(db, int(tenant.id))
    db.commit()
    return {
        "id": tenant.id,
        "name": tenant.name,
        "token_balance": tenant.token_balance,
        "is_active": tenant.is_active,
    }


@app.put("/tenants/{tenant_id}")
def update_tenant(
    tenant_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin required")
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        conflict = db.query(Tenant).filter(Tenant.name == name, Tenant.id != tenant.id).first()
        if conflict:
            raise HTTPException(status_code=409, detail="tenant name already exists")
        tenant.name = name
    if "token_balance" in payload:
        tenant.token_balance = max(0, int(payload.get("token_balance") or 0))
    if "is_active" in payload:
        tenant.is_active = bool(payload.get("is_active"))
    db.commit()
    db.refresh(tenant)
    return {
        "id": tenant.id,
        "name": tenant.name,
        "token_balance": tenant.token_balance,
        "is_active": tenant.is_active,
    }


@app.get("/projects")
def list_projects(
    tenant_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    query = db.query(Project)
    if is_superadmin(current_user):
        if tenant_id is not None:
            query = query.filter(Project.tenant_id == tenant_id)
    else:
        if not current_user.tenant_id:
            return []
        query = query.filter(Project.tenant_id == current_user.tenant_id)
    rows = query.order_by(Project.created_at.desc()).all()
    if not is_superadmin(current_user):
        rows = [p for p in rows if _can_user_access_project(db, current_user, p)]
    if not rows:
        return []
    tenant_ids = sorted({int(p.tenant_id) for p in rows if p.tenant_id is not None})
    tenant_map = {}
    if tenant_ids:
        for item in db.query(Tenant).filter(Tenant.id.in_(tenant_ids)).all():
            tenant_map[item.id] = item.name
    supplier_ids = sorted({int(p.default_supplier_company_id) for p in rows if p.default_supplier_company_id is not None})
    supplier_map: dict[int, str] = {}
    if supplier_ids:
        for s in db.query(SupplierCompany).filter(SupplierCompany.id.in_(supplier_ids)).all():
            supplier_map[int(s.id)] = s.name
    project_ids = [int(p.id) for p in rows]
    project_admins_map: dict[int, set[str]] = {pid: set() for pid in project_ids}
    project_managers_map: dict[int, set[str]] = {pid: set() for pid in project_ids}
    project_others_map: dict[int, set[str]] = {pid: set() for pid in project_ids}
    project_user_ids: dict[int, set[int]] = {pid: set() for pid in project_ids}
    if project_ids:
        access_rows = (
            db.query(UserProjectAccess)
            .filter(
                UserProjectAccess.project_id.in_(project_ids),
                UserProjectAccess.is_denied.is_(False),
            )
            .all()
        )
        user_ids = set()
        for a in access_rows:
            pid = int(a.project_id)
            uid = int(a.user_id)
            if pid in project_user_ids:
                project_user_ids[pid].add(uid)
                user_ids.add(uid)
        if user_ids:
            users = db.query(User).filter(User.id.in_(list(user_ids))).all()
        else:
            users = []
        for u in db.query(User).filter(User.active_project_id.in_(project_ids), User.is_active.is_(True)).all():
            user_ids.add(int(u.id))
        user_map = {int(u.id): u for u in users}
        for u in db.query(User).filter(User.id.in_(list(user_ids)) if user_ids else text("1=0")).all():
            user_map[int(u.id)] = u
        for u in user_map.values():
            if u and u.active_project_id is not None:
                apid = int(u.active_project_id)
                if apid in project_user_ids:
                    project_user_ids[apid].add(int(u.id))
        for pid in project_ids:
            for uid in project_user_ids.get(pid, set()):
                u = user_map.get(uid)
                if not u or not u.is_active:
                    continue
                role = normalize_role(u.role)
                uname = str(u.username or "").strip()
                if not uname:
                    continue
                if role in {"superadmin", "superadmin_staff", "tenant_admin", "admin"}:
                    project_admins_map[pid].add(uname)
                elif role in {"tenant_manager", "manager"}:
                    project_managers_map[pid].add(uname)
                else:
                    project_others_map[pid].add(uname)
    def _format_project_team(pid: int) -> str:
        managers = sorted(project_managers_map.get(pid, set()))
        others = sorted(project_others_map.get(pid, set()))
        parts = []
        if managers:
            parts.append(f"Manager: {', '.join(managers)}")
        if others:
            parts.append(f"Diğer: {', '.join(others)}")
        return " | ".join(parts)
    return [
        {
            "id": p.id,
            "tenant_id": p.tenant_id,
            "tenant_name": tenant_map.get(p.tenant_id),
            "name": p.name,
            "city": p.city,
            "operation_code": p.operation_code,
            "token_limit": p.token_limit,
            "token_used": p.token_used,
            "is_active": p.is_active,
            "project_admins": ", ".join(sorted(project_admins_map.get(int(p.id), set()))),
            "project_team": _format_project_team(int(p.id)),
            "default_supplier_company_id": p.default_supplier_company_id,
            "default_supplier_company_name": supplier_map.get(int(p.default_supplier_company_id)) if p.default_supplier_company_id is not None else None,
            "created_at": p.created_at,
        }
        for p in rows
    ]


@app.post("/projects")
def create_project(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    tenant_id = current_user.tenant_id
    if is_superadmin(current_user):
        tenant_id = _resolve_superadmin_tenant_id(db, payload)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Current user has no tenant")
    name = str(payload.get("name") or "").strip()
    city = _normalize_project_city(payload.get("city"))
    operation_code = str(payload.get("operation_code") or "").strip().upper()
    supplier_company_id = payload.get("default_supplier_company_id")
    token_limit = payload.get("token_limit")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if city not in ALLOWED_PROJECT_CITIES:
        raise HTTPException(status_code=400, detail="city is invalid")
    if not operation_code or len(operation_code) > 9:
        raise HTTPException(status_code=400, detail="operation_code is required and max 9 chars")
    existing = (
        db.query(Project)
        .filter(
            Project.tenant_id == tenant_id,
            Project.operation_code == operation_code,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="operation_code already exists")
    default_supplier_company_id = None
    if supplier_company_id is not None and str(supplier_company_id).strip() != "":
        supplier_id = int(supplier_company_id)
        supplier = db.query(SupplierCompany).filter(SupplierCompany.id == supplier_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier company not found")
        if int(supplier.tenant_id or 0) != int(tenant_id or 0):
            raise HTTPException(status_code=403, detail="Supplier company tenant mismatch")
        default_supplier_company_id = supplier.id
    project = Project(
        tenant_id=tenant_id,
        name=name,
        city=city,
        operation_code=operation_code,
        default_supplier_company_id=default_supplier_company_id,
        token_limit=int(token_limit) if token_limit is not None else None,
        token_used=0,
        is_active=True,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    _ensure_project_modules_defaults(db, int(project.id))
    db.commit()
    return {
        "id": project.id,
        "name": project.name,
        "city": project.city,
        "operation_code": project.operation_code,
        "default_supplier_company_id": project.default_supplier_company_id,
        "token_limit": project.token_limit,
        "token_used": project.token_used,
        "is_active": project.is_active,
    }


@app.put("/projects/{project_id}")
def update_project(
    project_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    q = db.query(Project).filter(Project.id == project_id)
    if not is_superadmin(current_user):
        q = q.filter(Project.tenant_id == current_user.tenant_id)
    project = q.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        project.name = name
    if "city" in payload:
        city = _normalize_project_city(payload.get("city"))
        if city not in ALLOWED_PROJECT_CITIES:
            raise HTTPException(status_code=400, detail="city is invalid")
        project.city = city
    if "operation_code" in payload:
        operation_code = str(payload.get("operation_code") or "").strip().upper()
        if not operation_code or len(operation_code) > 9:
            raise HTTPException(status_code=400, detail="operation_code max 9 chars")
        conflict = (
            db.query(Project)
            .filter(
                Project.tenant_id == current_user.tenant_id,
                Project.operation_code == operation_code,
                Project.id != project.id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(status_code=409, detail="operation_code already exists")
        project.operation_code = operation_code
    if "token_limit" in payload:
        value = payload.get("token_limit")
        project.token_limit = int(value) if value is not None else None
    if "default_supplier_company_id" in payload:
        raw = payload.get("default_supplier_company_id")
        if raw is None or str(raw).strip() == "":
            project.default_supplier_company_id = None
        else:
            supplier_id = int(raw)
            supplier = db.query(SupplierCompany).filter(SupplierCompany.id == supplier_id).first()
            if not supplier:
                raise HTTPException(status_code=404, detail="Supplier company not found")
            if int(supplier.tenant_id or 0) != int(project.tenant_id or 0):
                raise HTTPException(status_code=403, detail="Supplier company tenant mismatch")
            project.default_supplier_company_id = supplier.id
    if "is_active" in payload:
        project.is_active = bool(payload.get("is_active"))
    db.commit()
    db.refresh(project)
    return {
        "id": project.id,
        "name": project.name,
        "city": project.city,
        "operation_code": project.operation_code,
        "default_supplier_company_id": project.default_supplier_company_id,
        "token_limit": project.token_limit,
        "token_used": project.token_used,
        "is_active": project.is_active,
    }


@app.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin required")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if str(project.operation_code or "").strip().upper() == MANAGEMENT_PROJECT_CODE:
        raise HTTPException(status_code=400, detail="Management project cannot be deleted")
    db.query(ProjectModule).filter(ProjectModule.project_id == project_id).delete(synchronize_session=False)
    db.query(ProjectServiceProduct).filter(ProjectServiceProduct.project_id == project_id).delete(synchronize_session=False)
    db.query(UserProjectAccess).filter(UserProjectAccess.project_id == project_id).delete(synchronize_session=False)
    db.query(User).filter(User.active_project_id == project_id).update({"active_project_id": None}, synchronize_session=False)
    db.query(Upload).filter(Upload.project_id == project_id).update({"project_id": None}, synchronize_session=False)
    db.query(Transfer).filter(Transfer.project_id == project_id).update({"project_id": None}, synchronize_session=False)
    db.delete(project)
    db.commit()
    return {"ok": True, "deleted_project_id": project_id}


@app.get("/users")
def list_users(
    tenant_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    query = db.query(User)
    if is_superadmin(current_user):
        if tenant_id is not None:
            query = query.filter(User.tenant_id == tenant_id)
    else:
        query = query.filter(
            User.tenant_id == current_user.tenant_id,
            User.id != current_user.id,
        )
    rows = query.order_by(User.created_at.desc()).all()
    if not is_superadmin(current_user):
        rows = [r for r in rows if role_level(r.role) < role_level(current_user.role)]
    tenant_ids = sorted({int(r.tenant_id) for r in rows if r.tenant_id is not None})
    tenant_map = {}
    if tenant_ids:
        for t in db.query(Tenant).filter(Tenant.id.in_(tenant_ids)).all():
            tenant_map[t.id] = t.name
    return [
        {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "tenant_name": tenant_map.get(row.tenant_id),
            "username": row.username,
            "role": row.role,
            "token_limit": row.token_limit,
            "token_used": row.token_used,
            "is_active": row.is_active,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@app.post("/users")
def create_user(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    role = normalize_role(str(payload.get("role") or "tenant_operator"))
    token_limit = payload.get("token_limit")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password are required")
    if role not in ALLOWED_USER_ROLES:
        raise HTTPException(status_code=400, detail="invalid role")
    if not can_assign_role(current_user, role):
        raise HTTPException(status_code=403, detail="insufficient role delegation authority")
    tenant_id = current_user.tenant_id
    if is_superadmin(current_user):
        tenant_id = _resolve_superadmin_tenant_id(db, payload)
    if role != "superadmin" and not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required for non-superadmin user")
    if not is_superadmin(current_user) and tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="cannot create user in another tenant")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="username already exists")
    user = User(
        tenant_id=tenant_id,
        username=username,
        password_hash=_hash_password(password),
        role=role,
        token_limit=int(token_limit) if token_limit is not None else None,
        token_used=0,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first() if user.tenant_id else None
    return {
        "id": user.id,
        "tenant_id": user.tenant_id,
        "tenant_name": tenant.name if tenant else None,
        "username": user.username,
        "role": user.role,
        "token_limit": user.token_limit,
        "token_used": user.token_used,
        "is_active": user.is_active,
    }


@app.put("/users/{user_id}")
def update_user(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    query = db.query(User).filter(User.id == user_id)
    if not is_superadmin(current_user):
        query = query.filter(User.tenant_id == current_user.tenant_id)
    user = query.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not can_manage_user(current_user, user):
        raise HTTPException(status_code=403, detail="cannot manage this user")
    if "password" in payload:
        password = str(payload.get("password") or "")
        if not password:
            raise HTTPException(status_code=400, detail="password cannot be empty")
        user.password_hash = _hash_password(password)
    if "role" in payload:
        role = normalize_role(str(payload.get("role") or ""))
        if role not in ALLOWED_USER_ROLES:
            raise HTTPException(status_code=400, detail="invalid role")
        if not can_assign_role(current_user, role):
            raise HTTPException(status_code=403, detail="insufficient role delegation authority")
        user.role = role
    if is_superadmin(current_user) and "tenant_id" in payload:
        val = payload.get("tenant_id")
        user.tenant_id = int(val) if val is not None else None
    if "token_limit" in payload:
        value = payload.get("token_limit")
        user.token_limit = int(value) if value is not None else None
    if "is_active" in payload:
        user.is_active = bool(payload.get("is_active"))
    db.commit()
    db.refresh(user)
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first() if user.tenant_id else None
    return {
        "id": user.id,
        "tenant_id": user.tenant_id,
        "tenant_name": tenant.name if tenant else None,
        "username": user.username,
        "role": user.role,
        "token_limit": user.token_limit,
        "token_used": user.token_used,
        "is_active": user.is_active,
    }


@app.get("/admin/project-modules")
def list_project_modules(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not is_superadmin(current_user) and int(project.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="Forbidden")
    _ensure_project_modules_defaults(db, int(project.id))
    db.commit()
    rows = (
        db.query(ProjectModule)
        .filter(ProjectModule.project_id == project.id)
        .order_by(ProjectModule.module_key.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "module_key": r.module_key,
            "enabled": r.enabled,
        }
        for r in rows
    ]


@app.put("/admin/project-modules/{project_id}")
def set_project_module(
    project_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Superadmin required")
    module_key = str(payload.get("module_key") or "").strip().lower()
    enabled = bool(payload.get("enabled"))
    if not module_key:
        raise HTTPException(status_code=400, detail="module_key is required")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    row = (
        db.query(ProjectModule)
        .filter(ProjectModule.project_id == project_id, ProjectModule.module_key == module_key)
        .first()
    )
    if not row:
        row = ProjectModule(project_id=project_id, module_key=module_key, enabled=enabled)
        db.add(row)
    else:
        row.enabled = enabled
    db.commit()
    db.refresh(row)
    return {
        "ok": True,
        "id": row.id,
        "project_id": row.project_id,
        "module_key": row.module_key,
        "enabled": row.enabled,
    }


@app.get("/admin/user-project-access/{user_id}")
def list_user_project_access(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if not is_superadmin(current_user) and int(target.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="Forbidden")
    rows = (
        db.query(UserProjectAccess)
        .filter(UserProjectAccess.user_id == user_id)
        .order_by(UserProjectAccess.project_id.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "project_id": r.project_id,
            "can_view": r.can_view,
            "can_edit": r.can_edit,
            "is_denied": r.is_denied,
        }
        for r in rows
    ]


@app.put("/admin/user-project-access")
def set_user_project_access(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    user_id = int(payload.get("user_id") or 0)
    project_id = int(payload.get("project_id") or 0)
    if not user_id or not project_id:
        raise HTTPException(status_code=400, detail="user_id and project_id are required")
    target = db.query(User).filter(User.id == user_id).first()
    project = db.query(Project).filter(Project.id == project_id).first()
    if not target or not project:
        raise HTTPException(status_code=404, detail="User or project not found")
    if not is_superadmin(current_user):
        if int(target.tenant_id or 0) != int(current_user.tenant_id or 0):
            raise HTTPException(status_code=403, detail="Forbidden")
        if int(project.tenant_id or 0) != int(current_user.tenant_id or 0):
            raise HTTPException(status_code=403, detail="Forbidden")
    row = (
        db.query(UserProjectAccess)
        .filter(UserProjectAccess.user_id == user_id, UserProjectAccess.project_id == project_id)
        .first()
    )
    if not row:
        row = UserProjectAccess(user_id=user_id, project_id=project_id)
        db.add(row)
    if "can_view" in payload:
        row.can_view = bool(payload.get("can_view"))
    if "can_edit" in payload:
        row.can_edit = bool(payload.get("can_edit"))
    if "is_denied" in payload:
        row.is_denied = bool(payload.get("is_denied"))
    db.commit()
    db.refresh(row)
    return {
        "ok": True,
        "id": row.id,
        "user_id": row.user_id,
        "project_id": row.project_id,
        "can_view": row.can_view,
        "can_edit": row.can_edit,
        "is_denied": row.is_denied,
    }


@app.get("/admin/service-products")
def list_service_products(
    tenant_id: int | None = Query(default=None),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    query = db.query(ServiceProduct)
    if is_superadmin(current_user):
        if tenant_id is not None:
            query = query.filter(ServiceProduct.tenant_id == tenant_id)
    else:
        query = query.filter(ServiceProduct.tenant_id == current_user.tenant_id)
    if category:
        query = query.filter(ServiceProduct.category == str(category).strip().lower())
    rows = query.order_by(ServiceProduct.created_at.desc()).all()
    out = []
    for r in rows:
        clean_desc, meta = _unpack_product_description(r.description)
        out.append(
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "name": r.name,
                "category": r.category,
                "code": r.code,
                "description": clean_desc,
                "meta": meta,
                "price": r.price,
                "currency": r.currency,
                "vat_rate": r.vat_rate,
                "quota": r.quota,
                "is_active": r.is_active,
                "created_at": r.created_at,
            }
        )
    return out


@app.post("/admin/service-products")
def create_service_product(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    tenant_id = current_user.tenant_id
    if is_superadmin(current_user):
        tenant_id = _resolve_superadmin_tenant_id(db, payload)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    name = str(payload.get("name") or "").strip()
    category = str(payload.get("category") or "").strip().lower()
    code = str(payload.get("code") or "").strip().upper()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if category not in SERVICE_PRODUCT_CATEGORIES:
        raise HTTPException(status_code=400, detail="invalid category")
    if not code:
        raise HTTPException(status_code=400, detail="code is required")
    exists = (
        db.query(ServiceProduct)
        .filter(ServiceProduct.tenant_id == tenant_id, ServiceProduct.code == code)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="product code already exists")
    meta_obj = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    for mk in [
        "main_category",
        "level_1",
        "level_2",
        "level_3",
        "hotel",
        "package_code",
        "package_name",
        "room_type",
        "sng_price",
        "dbl_price",
        "trp_price",
    ]:
        if mk in payload and mk not in meta_obj:
            meta_obj[mk] = payload.get(mk)
    packed_description = _pack_product_description(
        str(payload.get("description") or "").strip() or None,
        meta_obj,
    )
    row = ServiceProduct(
        tenant_id=tenant_id,
        name=name,
        category=category,
        code=code,
        description=packed_description,
        price=float(payload.get("price")) if payload.get("price") is not None else None,
        currency=str(payload.get("currency") or "TRY").strip().upper() or "TRY",
        vat_rate=float(payload.get("vat_rate")) if payload.get("vat_rate") is not None else None,
        quota=int(payload.get("quota")) if payload.get("quota") is not None else None,
        is_active=bool(payload.get("is_active", True)),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    clean_desc, meta = _unpack_product_description(row.description)
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "name": row.name,
        "category": row.category,
        "code": row.code,
        "description": clean_desc,
        "meta": meta,
        "price": row.price,
        "currency": row.currency,
        "vat_rate": row.vat_rate,
        "quota": row.quota,
        "is_active": row.is_active,
    }


@app.put("/admin/service-products/{product_id}")
def update_service_product(
    product_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    query = db.query(ServiceProduct).filter(ServiceProduct.id == product_id)
    if not is_superadmin(current_user):
        query = query.filter(ServiceProduct.tenant_id == current_user.tenant_id)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    if "name" in payload:
        row.name = str(payload.get("name") or "").strip() or row.name
    if "category" in payload:
        category = str(payload.get("category") or "").strip().lower()
        if category not in SERVICE_PRODUCT_CATEGORIES:
            raise HTTPException(status_code=400, detail="invalid category")
        row.category = category
    if "code" in payload:
        code = str(payload.get("code") or "").strip().upper()
        if not code:
            raise HTTPException(status_code=400, detail="code cannot be empty")
        conflict = (
            db.query(ServiceProduct)
            .filter(
                ServiceProduct.tenant_id == row.tenant_id,
                ServiceProduct.code == code,
                ServiceProduct.id != row.id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(status_code=409, detail="product code already exists")
        row.code = code
    if "description" in payload:
        # açıklama, meta ile birlikte saklanır; aşağıda birlikte set edilir.
        pass
    if "price" in payload:
        row.price = float(payload.get("price")) if payload.get("price") is not None else None
    if "currency" in payload:
        row.currency = str(payload.get("currency") or "TRY").strip().upper() or "TRY"
    if "vat_rate" in payload:
        row.vat_rate = float(payload.get("vat_rate")) if payload.get("vat_rate") is not None else None
    if "quota" in payload:
        row.quota = int(payload.get("quota")) if payload.get("quota") is not None else None
    if "is_active" in payload:
        row.is_active = bool(payload.get("is_active"))
    current_desc, current_meta = _unpack_product_description(row.description)
    next_desc = (
        str(payload.get("description") or "").strip()
        if "description" in payload
        else (current_desc or "")
    )
    next_meta = dict(current_meta or {})
    if isinstance(payload.get("meta"), dict):
        for k, v in payload.get("meta").items():
            next_meta[str(k)] = v
    for mk in [
        "main_category",
        "level_1",
        "level_2",
        "level_3",
        "hotel",
        "package_code",
        "package_name",
        "room_type",
        "sng_price",
        "dbl_price",
        "trp_price",
    ]:
        if mk in payload:
            next_meta[mk] = payload.get(mk)
    row.description = _pack_product_description(next_desc or None, next_meta)
    db.commit()
    db.refresh(row)
    clean_desc, meta = _unpack_product_description(row.description)
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "name": row.name,
        "category": row.category,
        "code": row.code,
        "description": clean_desc,
        "meta": meta,
        "price": row.price,
        "currency": row.currency,
        "vat_rate": row.vat_rate,
        "quota": row.quota,
        "is_active": row.is_active,
    }


@app.get("/admin/project-service-products")
def list_project_service_products(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    scoped_project_id, management_scope = _resolve_project_scope_for_user(db, current_user, project_id)
    if management_scope and not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Only superadmin can use management scope")
    if scoped_project_id is None:
        raise HTTPException(status_code=400, detail="project_id is required in management scope")
    project = db.query(Project).filter(Project.id == scoped_project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not is_superadmin(current_user) and int(project.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="Forbidden")
    rows = (
        db.query(ProjectServiceProduct, ServiceProduct)
        .join(ServiceProduct, ServiceProduct.id == ProjectServiceProduct.product_id)
        .filter(ProjectServiceProduct.project_id == scoped_project_id)
        .order_by(ProjectServiceProduct.created_at.desc())
        .all()
    )
    return [
        {
            "id": ps.id,
            "project_id": ps.project_id,
            "product_id": ps.product_id,
            "product_name": p.name,
            "category": p.category,
            "code": p.code,
            "base_price": p.price,
            "base_currency": p.currency,
            "price_override": ps.price_override,
            "currency_override": ps.currency_override,
            "quota_override": ps.quota_override,
            "sale_start_date": ps.sale_start_date,
            "sale_end_date": ps.sale_end_date,
            "is_active": ps.is_active,
        }
        for ps, p in rows
    ]


@app.put("/admin/project-service-products")
def upsert_project_service_product(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    raw_project_id = payload.get("project_id")
    scoped_project_id, management_scope = _resolve_project_scope_for_user(db, current_user, raw_project_id)
    if management_scope and not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Only superadmin can use management scope")
    if scoped_project_id is None:
        raise HTTPException(status_code=400, detail="project_id is required in management scope")
    project_id = int(scoped_project_id)
    product_id = int(payload.get("product_id") or 0)
    if not project_id or not product_id:
        raise HTTPException(status_code=400, detail="project_id and product_id are required")
    project = db.query(Project).filter(Project.id == project_id).first()
    product = db.query(ServiceProduct).filter(ServiceProduct.id == product_id).first()
    if not project or not product:
        raise HTTPException(status_code=404, detail="Project or product not found")
    if not is_superadmin(current_user):
        if int(project.tenant_id or 0) != int(current_user.tenant_id or 0):
            raise HTTPException(status_code=403, detail="Forbidden")
        if int(product.tenant_id or 0) != int(current_user.tenant_id or 0):
            raise HTTPException(status_code=403, detail="Forbidden")
    row = (
        db.query(ProjectServiceProduct)
        .filter(ProjectServiceProduct.project_id == project_id, ProjectServiceProduct.product_id == product_id)
        .first()
    )
    if not row:
        row = ProjectServiceProduct(project_id=project_id, product_id=product_id)
        db.add(row)
    if "price_override" in payload:
        row.price_override = float(payload.get("price_override")) if payload.get("price_override") is not None else None
    if "currency_override" in payload:
        row.currency_override = str(payload.get("currency_override") or "").strip().upper() or None
    if "quota_override" in payload:
        row.quota_override = int(payload.get("quota_override")) if payload.get("quota_override") is not None else None
    if "sale_start_date" in payload:
        row.sale_start_date = str(payload.get("sale_start_date") or "").strip() or None
    if "sale_end_date" in payload:
        row.sale_end_date = str(payload.get("sale_end_date") or "").strip() or None
    if "is_active" in payload:
        row.is_active = bool(payload.get("is_active"))
    db.commit()
    db.refresh(row)
    return {
        "ok": True,
        "id": row.id,
        "project_id": row.project_id,
        "product_id": row.product_id,
        "price_override": row.price_override,
        "currency_override": row.currency_override,
        "quota_override": row.quota_override,
        "sale_start_date": row.sale_start_date,
        "sale_end_date": row.sale_end_date,
        "is_active": row.is_active,
    }


@app.get("/supplier-companies")
def list_supplier_companies(
    tenant_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    query = db.query(SupplierCompany)
    if is_superadmin(current_user):
        if tenant_id is not None:
            query = query.filter(SupplierCompany.tenant_id == tenant_id)
    else:
        query = query.filter(SupplierCompany.tenant_id == current_user.tenant_id)
    rows = query.order_by(SupplierCompany.created_at.desc()).all()
    return [
        {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "name": row.name,
            "is_active": row.is_active,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@app.post("/supplier-companies")
def create_supplier_company(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    tenant_id = current_user.tenant_id
    if is_superadmin(current_user):
        tenant_id = _resolve_superadmin_tenant_id(db, payload)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    exists = (
        db.query(SupplierCompany)
        .filter(SupplierCompany.tenant_id == tenant_id, SupplierCompany.name == name)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="supplier company already exists")
    row = SupplierCompany(tenant_id=tenant_id, name=name, is_active=True)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "name": row.name,
        "is_active": row.is_active,
    }


@app.get("/supplier-staff")
def list_supplier_staff(
    supplier_company_id: int | None = Query(default=None),
    role: str | None = Query(default=None),
    tenant_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    query = db.query(SupplierStaff)
    if is_superadmin(current_user):
        if tenant_id is not None:
            query = query.filter(SupplierStaff.tenant_id == tenant_id)
    else:
        query = query.filter(SupplierStaff.tenant_id == current_user.tenant_id)
    if supplier_company_id is not None:
        query = query.filter(SupplierStaff.supplier_company_id == supplier_company_id)
    if role:
        query = query.filter(SupplierStaff.role == role.lower())
    rows = query.order_by(SupplierStaff.created_at.desc()).all()
    return [
        {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "supplier_company_id": row.supplier_company_id,
            "full_name": row.full_name,
            "role": row.role,
            "phone": row.phone,
            "vehicle_plate": row.vehicle_plate,
            "is_active": row.is_active,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@app.post("/supplier-staff")
def create_supplier_staff(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    supplier_company_id = int(payload.get("supplier_company_id") or 0)
    full_name = str(payload.get("full_name") or "").strip()
    role = str(payload.get("role") or "").strip().lower()
    phone = str(payload.get("phone") or "").strip() or None
    vehicle_plate = str(payload.get("vehicle_plate") or "").strip().upper() or None
    if not supplier_company_id:
        raise HTTPException(status_code=400, detail="supplier_company_id is required")
    if role not in {"greeter", "driver"}:
        raise HTTPException(status_code=400, detail="role must be greeter or driver")
    if not full_name:
        raise HTTPException(status_code=400, detail="full_name is required")
    company = db.query(SupplierCompany).filter(SupplierCompany.id == supplier_company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="supplier company not found")
    if not is_superadmin(current_user) and company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="forbidden")
    row = SupplierStaff(
        tenant_id=company.tenant_id,
        supplier_company_id=company.id,
        full_name=full_name,
        role=role,
        phone=phone,
        vehicle_plate=vehicle_plate,
        is_active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "supplier_company_id": row.supplier_company_id,
        "full_name": row.full_name,
        "role": row.role,
        "phone": row.phone,
        "vehicle_plate": row.vehicle_plate,
        "is_active": row.is_active,
    }


def _supplier_client_out(row: SupplierClient) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "supplier_company_id": row.supplier_company_id,
        "project_id": row.project_id,
        "full_name": row.full_name,
        "phone": row.phone,
        "email": row.email,
        "source_type": row.source_type,
        "status": row.status,
        "notes": row.notes,
        "created_at": row.created_at,
    }


@app.get("/supplier-clients")
def list_supplier_clients(
    supplier_company_id: int | None = Query(default=None),
    source_type: str | None = Query(default=None),
    project_id: int | None = Query(default=None),
    tenant_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    query = db.query(SupplierClient)
    if is_superadmin(current_user):
        if tenant_id is not None:
            query = query.filter(SupplierClient.tenant_id == tenant_id)
    else:
        query = query.filter(SupplierClient.tenant_id == current_user.tenant_id)
    if supplier_company_id is not None:
        query = query.filter(SupplierClient.supplier_company_id == supplier_company_id)
    if source_type:
        st = str(source_type).strip().lower()
        if st not in {"project", "external"}:
            raise HTTPException(status_code=400, detail="source_type must be project or external")
        query = query.filter(SupplierClient.source_type == st)
    if project_id is not None:
        query = query.filter(SupplierClient.project_id == project_id)
    rows = query.order_by(SupplierClient.created_at.desc()).all()
    return [_supplier_client_out(r) for r in rows]


@app.post("/supplier-clients")
def create_supplier_client(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    supplier_company_id = int(payload.get("supplier_company_id") or 0)
    full_name = str(payload.get("full_name") or "").strip()
    source_type = str(payload.get("source_type") or "external").strip().lower()
    if source_type not in {"project", "external"}:
        raise HTTPException(status_code=400, detail="source_type must be project or external")
    if not supplier_company_id:
        raise HTTPException(status_code=400, detail="supplier_company_id is required")
    if not full_name:
        raise HTTPException(status_code=400, detail="full_name is required")
    company = db.query(SupplierCompany).filter(SupplierCompany.id == supplier_company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="supplier company not found")
    if not is_superadmin(current_user) and int(company.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="forbidden")

    project_id = payload.get("project_id")
    if project_id is not None:
        project_id = int(project_id)
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="project not found")
        if int(project.tenant_id or 0) != int(company.tenant_id or 0):
            raise HTTPException(status_code=400, detail="project tenant mismatch")
    elif source_type == "project":
        raise HTTPException(status_code=400, detail="project_id is required when source_type=project")

    row = SupplierClient(
        tenant_id=company.tenant_id,
        supplier_company_id=company.id,
        project_id=project_id,
        full_name=full_name,
        phone=str(payload.get("phone") or "").strip() or None,
        email=str(payload.get("email") or "").strip() or None,
        source_type=source_type,
        status=str(payload.get("status") or "active").strip().lower() or "active",
        notes=str(payload.get("notes") or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _supplier_client_out(row)


@app.put("/supplier-clients/{client_id}")
def update_supplier_client(
    client_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    row = db.query(SupplierClient).filter(SupplierClient.id == client_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="supplier client not found")
    if not is_superadmin(current_user) and int(row.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="forbidden")

    if "full_name" in payload:
        full_name = str(payload.get("full_name") or "").strip()
        if not full_name:
            raise HTTPException(status_code=400, detail="full_name cannot be empty")
        row.full_name = full_name
    if "phone" in payload:
        row.phone = str(payload.get("phone") or "").strip() or None
    if "email" in payload:
        row.email = str(payload.get("email") or "").strip() or None
    if "notes" in payload:
        row.notes = str(payload.get("notes") or "").strip() or None
    if "status" in payload:
        row.status = str(payload.get("status") or "active").strip().lower() or "active"
    if "source_type" in payload:
        st = str(payload.get("source_type") or "").strip().lower()
        if st not in {"project", "external"}:
            raise HTTPException(status_code=400, detail="source_type must be project or external")
        row.source_type = st
        if st == "external":
            row.project_id = None
    if "project_id" in payload:
        proj_val = payload.get("project_id")
        if proj_val in {None, ""}:
            row.project_id = None
        else:
            project_id = int(proj_val)
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise HTTPException(status_code=404, detail="project not found")
            if int(project.tenant_id or 0) != int(row.tenant_id or 0):
                raise HTTPException(status_code=400, detail="project tenant mismatch")
            row.project_id = project_id
            row.source_type = "project"
    db.commit()
    db.refresh(row)
    return _supplier_client_out(row)


def _supplier_service_type_out(row: SupplierServiceType) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "supplier_company_id": row.supplier_company_id,
        "code": row.code,
        "name": row.name,
        "scope_type": row.scope_type,
        "project_id": row.project_id,
        "parent_id": row.parent_id,
        "unit_price": row.unit_price,
        "currency": row.currency,
        "is_active": row.is_active,
        "created_at": row.created_at,
    }


@app.get("/supplier-service-types")
def list_supplier_service_types(
    supplier_company_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    scope_type: str | None = Query(default=None),
    tenant_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    query = db.query(SupplierServiceType)
    if is_superadmin(current_user):
        if tenant_id is not None:
            query = query.filter(SupplierServiceType.tenant_id == tenant_id)
    else:
        query = query.filter(SupplierServiceType.tenant_id == current_user.tenant_id)
    if supplier_company_id is not None:
        query = query.filter(SupplierServiceType.supplier_company_id == supplier_company_id)
    if project_id is not None:
        query = query.filter(SupplierServiceType.project_id == project_id)
    if scope_type:
        st = str(scope_type).strip().lower()
        if st not in {"general", "company", "project"}:
            raise HTTPException(status_code=400, detail="scope_type must be general/company/project")
        query = query.filter(SupplierServiceType.scope_type == st)
    rows = query.order_by(SupplierServiceType.code.asc(), SupplierServiceType.created_at.desc()).all()
    return [_supplier_service_type_out(r) for r in rows]


@app.post("/supplier-service-types")
def create_supplier_service_type(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    scope_type = str(payload.get("scope_type") or "general").strip().lower()
    if scope_type not in {"general", "company", "project"}:
        raise HTTPException(status_code=400, detail="scope_type must be general/company/project")

    tenant_id = current_user.tenant_id
    if is_superadmin(current_user):
        tenant_id = _resolve_superadmin_tenant_id(db, payload)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")

    supplier_company_id = payload.get("supplier_company_id")
    if supplier_company_id is not None:
        supplier_company_id = int(supplier_company_id)
    project_id = payload.get("project_id")
    if project_id is not None:
        project_id = int(project_id)

    if scope_type == "company" and not supplier_company_id:
        raise HTTPException(status_code=400, detail="supplier_company_id is required for company scope")
    if scope_type == "project" and (not supplier_company_id or not project_id):
        raise HTTPException(status_code=400, detail="supplier_company_id and project_id are required for project scope")

    code = str(payload.get("code") or "").strip().upper()
    name = str(payload.get("name") or "").strip()
    if not code or not name:
        raise HTTPException(status_code=400, detail="code and name are required")

    exists = (
        db.query(SupplierServiceType)
        .filter(
            SupplierServiceType.tenant_id == tenant_id,
            SupplierServiceType.code == code,
            SupplierServiceType.scope_type == scope_type,
            SupplierServiceType.supplier_company_id.is_(None) if supplier_company_id is None else SupplierServiceType.supplier_company_id == supplier_company_id,
            SupplierServiceType.project_id.is_(None) if project_id is None else SupplierServiceType.project_id == project_id,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="service type already exists in this scope")

    row = SupplierServiceType(
        tenant_id=tenant_id,
        supplier_company_id=supplier_company_id,
        code=code,
        name=name,
        scope_type=scope_type,
        project_id=project_id,
        parent_id=int(payload.get("parent_id")) if payload.get("parent_id") is not None else None,
        unit_price=float(payload.get("unit_price")) if payload.get("unit_price") is not None else None,
        currency=str(payload.get("currency") or "TRY").strip().upper() or "TRY",
        is_active=bool(payload.get("is_active", True)),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _supplier_service_type_out(row)


def _resolve_service_price(
    db: Session,
    tenant_id: int,
    supplier_company_id: int,
    project_id: int | None,
    service_type_id: int | None,
    service_type_name: str | None,
) -> tuple[float | None, str]:
    currency = "TRY"
    if service_type_id:
        st = db.query(SupplierServiceType).filter(SupplierServiceType.id == int(service_type_id)).first()
        if st and st.unit_price is not None:
            return float(st.unit_price), str(st.currency or "TRY")
        if st:
            service_type_name = st.name
    name_norm = str(service_type_name or "").strip().lower()
    if not name_norm:
        return None, currency

    if project_id is not None:
        project_price = (
            db.query(SupplierServiceType)
            .filter(
                SupplierServiceType.tenant_id == tenant_id,
                SupplierServiceType.scope_type == "project",
                SupplierServiceType.supplier_company_id == supplier_company_id,
                SupplierServiceType.project_id == project_id,
                func.lower(SupplierServiceType.name) == name_norm,
                SupplierServiceType.is_active.is_(True),
            )
            .order_by(SupplierServiceType.created_at.desc())
            .first()
        )
        if project_price and project_price.unit_price is not None:
            return float(project_price.unit_price), str(project_price.currency or "TRY")

    company_price = (
        db.query(SupplierServiceType)
        .filter(
            SupplierServiceType.tenant_id == tenant_id,
            SupplierServiceType.scope_type == "company",
            SupplierServiceType.supplier_company_id == supplier_company_id,
            func.lower(SupplierServiceType.name) == name_norm,
            SupplierServiceType.is_active.is_(True),
        )
        .order_by(SupplierServiceType.created_at.desc())
        .first()
    )
    if company_price and company_price.unit_price is not None:
        return float(company_price.unit_price), str(company_price.currency or "TRY")

    general_price = (
        db.query(SupplierServiceType)
        .filter(
            SupplierServiceType.tenant_id == tenant_id,
            SupplierServiceType.scope_type == "general",
            SupplierServiceType.supplier_company_id.is_(None),
            func.lower(SupplierServiceType.name) == name_norm,
            SupplierServiceType.is_active.is_(True),
        )
        .order_by(SupplierServiceType.created_at.desc())
        .first()
    )
    if general_price and general_price.unit_price is not None:
        return float(general_price.unit_price), str(general_price.currency or "TRY")
    return None, currency


@app.get("/supplier-bookings")
def list_supplier_bookings(
    supplier_company_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    tenant_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    query = db.query(SupplierBooking)
    if is_superadmin(current_user):
        if tenant_id is not None:
            query = query.filter(SupplierBooking.tenant_id == tenant_id)
    else:
        query = query.filter(SupplierBooking.tenant_id == current_user.tenant_id)
    if supplier_company_id is not None:
        query = query.filter(SupplierBooking.supplier_company_id == supplier_company_id)
    if project_id is not None:
        query = query.filter(SupplierBooking.project_id == project_id)
    rows = query.order_by(SupplierBooking.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "supplier_company_id": r.supplier_company_id,
            "project_id": r.project_id,
            "project_reservation_no": r.project_reservation_no,
            "service_type_id": r.service_type_id,
            "service_type_name": r.service_type_name,
            "date": r.date,
            "time": r.time,
            "from_location": r.from_location,
            "to_location": r.to_location,
            "status": r.status,
            "base_amount": r.base_amount,
            "extra_parking": r.extra_parking,
            "extra_greeter": r.extra_greeter,
            "extra_hgs": r.extra_hgs,
            "extra_meal": r.extra_meal,
            "extra_other": r.extra_other,
            "total_amount": r.total_amount,
            "currency": r.currency,
            "notes": r.notes,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@app.post("/supplier-bookings")
def create_supplier_booking(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    supplier_company_id = int(payload.get("supplier_company_id") or 0)
    if not supplier_company_id:
        raise HTTPException(status_code=400, detail="supplier_company_id is required")
    company = db.query(SupplierCompany).filter(SupplierCompany.id == supplier_company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="supplier company not found")
    if not is_superadmin(current_user) and int(company.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="forbidden")

    project_id = payload.get("project_id")
    project_id_int = int(project_id) if project_id is not None else None
    if project_id_int is not None:
        project = db.query(Project).filter(Project.id == project_id_int).first()
        if not project:
            raise HTTPException(status_code=404, detail="project not found")
        if int(project.tenant_id or 0) != int(company.tenant_id or 0):
            raise HTTPException(status_code=400, detail="project tenant mismatch")

    project_reservation_no = str(payload.get("project_reservation_no") or "").strip().upper()
    if not project_reservation_no:
        raise HTTPException(status_code=400, detail="project_reservation_no is required")

    service_type_id = int(payload.get("service_type_id")) if payload.get("service_type_id") is not None else None
    service_type_name = str(payload.get("service_type_name") or "").strip() or None

    base_amount, price_currency = _resolve_service_price(
        db,
        int(company.tenant_id),
        int(company.id),
        project_id_int,
        service_type_id,
        service_type_name,
    )
    extra_parking = float(payload.get("extra_parking") or 0)
    extra_greeter = float(payload.get("extra_greeter") or 0)
    extra_hgs = float(payload.get("extra_hgs") or 0)
    extra_meal = float(payload.get("extra_meal") or 0)
    extra_other = float(payload.get("extra_other") or 0)
    total_amount = (float(base_amount or 0) + extra_parking + extra_greeter + extra_hgs + extra_meal + extra_other)

    booking = SupplierBooking(
        tenant_id=company.tenant_id,
        supplier_company_id=company.id,
        project_id=project_id_int,
        project_reservation_no=project_reservation_no,
        service_type_id=service_type_id,
        service_type_name=service_type_name,
        date=str(payload.get("date") or "").strip() or None,
        time=str(payload.get("time") or "").strip() or None,
        from_location=str(payload.get("from_location") or "").strip() or None,
        to_location=str(payload.get("to_location") or "").strip() or None,
        status=str(payload.get("status") or "planned").strip().lower() or "planned",
        base_amount=base_amount,
        extra_parking=extra_parking,
        extra_greeter=extra_greeter,
        extra_hgs=extra_hgs,
        extra_meal=extra_meal,
        extra_other=extra_other,
        total_amount=total_amount,
        currency=str(payload.get("currency") or price_currency or "TRY").strip().upper() or "TRY",
        notes=str(payload.get("notes") or "").strip() or None,
    )
    db.add(booking)
    db.flush()

    for c in (payload.get("contacts") or []):
        if not isinstance(c, dict):
            continue
        phone = str(c.get("phone") or "").strip()
        if not phone:
            continue
        db.add(
            SupplierBookingContact(
                booking_id=int(booking.id),
                contact_type=str(c.get("contact_type") or "passenger").strip().lower() or "passenger",
                full_name=str(c.get("full_name") or "").strip() or None,
                phone=phone,
                email=str(c.get("email") or "").strip() or None,
            )
        )
    db.commit()
    db.refresh(booking)
    return {
        "id": booking.id,
        "project_reservation_no": booking.project_reservation_no,
        "total_amount": booking.total_amount,
        "currency": booking.currency,
        "status": booking.status,
    }


def _sms_template_out(row: SupplierSmsTemplate) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "supplier_company_id": row.supplier_company_id,
        "event_key": row.event_key,
        "template_text": row.template_text,
        "is_active": row.is_active,
        "created_at": row.created_at,
    }


@app.get("/supplier-sms-templates")
def list_supplier_sms_templates(
    supplier_company_id: int = Query(...),
    tenant_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    company = db.query(SupplierCompany).filter(SupplierCompany.id == supplier_company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="supplier company not found")
    if not is_superadmin(current_user) and int(company.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="forbidden")
    query = db.query(SupplierSmsTemplate).filter(SupplierSmsTemplate.supplier_company_id == supplier_company_id)
    if is_superadmin(current_user):
        if tenant_id is not None:
            query = query.filter(SupplierSmsTemplate.tenant_id == tenant_id)
    else:
        query = query.filter(SupplierSmsTemplate.tenant_id == current_user.tenant_id)
    rows = query.order_by(SupplierSmsTemplate.event_key.asc()).all()
    return [_sms_template_out(r) for r in rows]


@app.put("/supplier-sms-templates")
def upsert_supplier_sms_template(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    supplier_company_id = int(payload.get("supplier_company_id") or 0)
    event_key = str(payload.get("event_key") or "").strip().lower()
    template_text = str(payload.get("template_text") or "").strip()
    if not supplier_company_id or not event_key or not template_text:
        raise HTTPException(status_code=400, detail="supplier_company_id, event_key and template_text are required")
    company = db.query(SupplierCompany).filter(SupplierCompany.id == supplier_company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="supplier company not found")
    if not is_superadmin(current_user) and int(company.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="forbidden")
    row = (
        db.query(SupplierSmsTemplate)
        .filter(
            SupplierSmsTemplate.tenant_id == company.tenant_id,
            SupplierSmsTemplate.supplier_company_id == supplier_company_id,
            SupplierSmsTemplate.event_key == event_key,
        )
        .first()
    )
    if not row:
        row = SupplierSmsTemplate(
            tenant_id=company.tenant_id,
            supplier_company_id=supplier_company_id,
            event_key=event_key,
            template_text=template_text,
            is_active=bool(payload.get("is_active", True)),
        )
        db.add(row)
    else:
        row.template_text = template_text
        if "is_active" in payload:
            row.is_active = bool(payload.get("is_active"))
    db.commit()
    db.refresh(row)
    return _sms_template_out(row)


def _render_supplier_sms_message(db: Session, booking: SupplierBooking, event_key: str) -> str:
    tpl = (
        db.query(SupplierSmsTemplate)
        .filter(
            SupplierSmsTemplate.tenant_id == booking.tenant_id,
            SupplierSmsTemplate.supplier_company_id == booking.supplier_company_id,
            SupplierSmsTemplate.event_key == event_key,
            SupplierSmsTemplate.is_active.is_(True),
        )
        .first()
    )
    base = (
        tpl.template_text
        if tpl and tpl.template_text
        else "Rezervasyon {reservation_no} durumu: {status}. {date} {time} {from_location} -> {to_location}"
    )
    company = db.query(SupplierCompany).filter(SupplierCompany.id == booking.supplier_company_id).first()
    mapping = {
        "firma_adi": (company.name if company else "-"),
        "reservation_no": (booking.project_reservation_no or "-"),
        "status": (booking.status or event_key or "-"),
        "date": (booking.date or ""),
        "time": (booking.time or ""),
        "from_location": (booking.from_location or ""),
        "to_location": (booking.to_location or ""),
        "service_type": (booking.service_type_name or ""),
    }
    msg = base
    for k, v in mapping.items():
        msg = msg.replace("{" + k + "}", str(v))
    msg = re.sub(r"\s+", " ", msg).strip()
    return f"[{SMS_SENDER_TITLE}] {msg}".strip()


@app.post("/supplier-bookings/{booking_id}/notify")
def queue_supplier_booking_sms(
    booking_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    booking = db.query(SupplierBooking).filter(SupplierBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="booking not found")
    if not is_superadmin(current_user) and int(booking.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="forbidden")
    status_txt = str(payload.get("status") or booking.status or "planned").strip().lower()
    booking.status = status_txt or booking.status
    contacts = db.query(SupplierBookingContact).filter(SupplierBookingContact.booking_id == booking.id).all()
    if not contacts:
        raise HTTPException(status_code=400, detail="no contacts to notify")
    message = _render_supplier_sms_message(db, booking, status_txt)
    queued = 0
    for c in contacts:
        if not c.phone:
            continue
        db.add(
            SupplierSmsQueue(
                tenant_id=booking.tenant_id,
                booking_id=booking.id,
                to_phone=c.phone,
                message=message,
                status="queued",
            )
        )
        queued += 1
    db.commit()
    return {"ok": True, "queued_sms": queued}


def _supplier_company_guard(
    db: Session,
    current_user: User,
    supplier_company_id: int,
) -> SupplierCompany:
    company = db.query(SupplierCompany).filter(SupplierCompany.id == int(supplier_company_id)).first()
    if not company:
        raise HTTPException(status_code=404, detail="supplier company not found")
    if not is_superadmin(current_user) and int(company.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="forbidden")
    return company


def _tracking_entity(company_id: int, key: str) -> str:
    return f"company:{int(company_id)}:{key}"


def _tracking_config_out(data: dict) -> dict:
    return {
        "provider": str(data.get("provider") or "arvento"),
        "enabled": bool(data.get("enabled", False)),
        "poll_interval_sec": int(data.get("poll_interval_sec") or 30),
        "base_url": str(data.get("base_url") or "").strip(),
        "vehicles_endpoint": str(data.get("vehicles_endpoint") or "").strip(),
        "auth_type": str(data.get("auth_type") or "bearer").strip().lower(),
        "username": str(data.get("username") or "").strip(),
        "has_token": bool(str(data.get("token") or "").strip()),
        "has_password": bool(str(data.get("password") or "").strip()),
        "timeout_sec": int(data.get("timeout_sec") or 20),
    }


@app.get("/supplier-tracking-config")
def get_supplier_tracking_config(
    supplier_company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    company = _supplier_company_guard(db, current_user, supplier_company_id)
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == company.tenant_id,
            ModuleData.module_name == "supplier_tracking",
            ModuleData.entity_type == _tracking_entity(company.id, "config"),
        )
        .order_by(ModuleData.id.desc())
        .first()
    )
    data = row.data if row and isinstance(row.data, dict) else {}
    return {"supplier_company_id": company.id, "config": _tracking_config_out(data)}


@app.put("/supplier-tracking-config")
def upsert_supplier_tracking_config(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    supplier_company_id = int(payload.get("supplier_company_id") or 0)
    if not supplier_company_id:
        raise HTTPException(status_code=400, detail="supplier_company_id is required")
    company = _supplier_company_guard(db, current_user, supplier_company_id)
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == company.tenant_id,
            ModuleData.module_name == "supplier_tracking",
            ModuleData.entity_type == _tracking_entity(company.id, "config"),
        )
        .order_by(ModuleData.id.desc())
        .first()
    )
    data = dict(row.data) if row and isinstance(row.data, dict) else {}
    for key in ("provider", "base_url", "vehicles_endpoint", "auth_type", "username", "token", "password"):
        if key in payload:
            data[key] = str(payload.get(key) or "").strip()
    for key in ("enabled",):
        if key in payload:
            data[key] = bool(payload.get(key))
    for key in ("poll_interval_sec", "timeout_sec"):
        if key in payload:
            try:
                data[key] = int(payload.get(key) or 0)
            except Exception:
                data[key] = 0
    if not row:
        row = ModuleData(
            tenant_id=company.tenant_id,
            project_id=None,
            module_name="supplier_tracking",
            entity_type=_tracking_entity(company.id, "config"),
            data=data,
            created_by_user_id=current_user.id,
            updated_by_user_id=current_user.id,
        )
        db.add(row)
    else:
        row.data = data
        row.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return {"ok": True, "supplier_company_id": company.id, "config": _tracking_config_out(data)}


@app.post("/supplier-tracking/poll")
def poll_supplier_tracking_now(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    supplier_company_id = int(payload.get("supplier_company_id") or 0)
    if not supplier_company_id:
        raise HTTPException(status_code=400, detail="supplier_company_id is required")
    company = _supplier_company_guard(db, current_user, supplier_company_id)
    cfg_row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == company.tenant_id,
            ModuleData.module_name == "supplier_tracking",
            ModuleData.entity_type == _tracking_entity(company.id, "config"),
        )
        .order_by(ModuleData.id.desc())
        .first()
    )
    config = dict(cfg_row.data) if cfg_row and isinstance(cfg_row.data, dict) else {}
    if not bool(config.get("enabled", False)):
        raise HTTPException(status_code=400, detail="tracking is disabled")
    provider = str(config.get("provider") or "arvento").strip().lower()
    if provider != "arvento":
        raise HTTPException(status_code=400, detail="unsupported provider")
    try:
        items = fetch_arvento_positions(config)
        error = None
    except Exception as exc:
        items = []
        error = str(exc)
    transfer_rows = (
        db.query(Transfer)
        .filter(
            Transfer.tenant_id == company.tenant_id,
            Transfer.supplier_company_id == company.id,
            Transfer.vehicle_code.isnot(None),
        )
        .all()
    )
    transfer_by_vehicle: dict[str, list[int]] = {}
    for t in transfer_rows:
        code = str(t.vehicle_code or "").strip().upper()
        if not code:
            continue
        transfer_by_vehicle.setdefault(code, []).append(int(t.id))
    for it in items:
        plate = str(it.get("plate") or "").strip().upper()
        it["transfer_ids"] = transfer_by_vehicle.get(plate, [])
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    pos_payload = {
        "provider": "arvento",
        "fetched_at": now,
        "count": len(items),
        "error": error,
        "items": items,
    }
    pos_row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == company.tenant_id,
            ModuleData.module_name == "supplier_tracking",
            ModuleData.entity_type == _tracking_entity(company.id, "positions"),
        )
        .order_by(ModuleData.id.desc())
        .first()
    )
    if not pos_row:
        pos_row = ModuleData(
            tenant_id=company.tenant_id,
            project_id=None,
            module_name="supplier_tracking",
            entity_type=_tracking_entity(company.id, "positions"),
            data=pos_payload,
            created_by_user_id=current_user.id,
            updated_by_user_id=current_user.id,
        )
        db.add(pos_row)
    else:
        pos_row.data = pos_payload
        pos_row.updated_by_user_id = current_user.id
    db.commit()
    return {"ok": True, "supplier_company_id": company.id, "fetched_at": now, "count": len(items), "error": error}


@app.get("/supplier-tracking/live")
def get_supplier_tracking_live(
    supplier_company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    company = _supplier_company_guard(db, current_user, supplier_company_id)
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == company.tenant_id,
            ModuleData.module_name == "supplier_tracking",
            ModuleData.entity_type == _tracking_entity(company.id, "positions"),
        )
        .order_by(ModuleData.id.desc())
        .first()
    )
    data = row.data if row and isinstance(row.data, dict) else {}
    return {
        "supplier_company_id": company.id,
        "provider": str(data.get("provider") or "arvento"),
        "fetched_at": data.get("fetched_at"),
        "count": int(data.get("count") or 0),
        "error": data.get("error"),
        "items": data.get("items") if isinstance(data.get("items"), list) else [],
    }


@app.post("/transfer-ops/assign")
def assign_transfer_operation(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_admin),
):
    scoped_project_id, management_scope = _resolve_project_scope_for_user(
        db, current_user, payload.get("project_id")
    )
    transfer_id = int(payload.get("transfer_id") or 0)
    if not transfer_id:
        raise HTTPException(status_code=400, detail="transfer_id is required")
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="transfer not found")
    if not is_superadmin(current_user) and transfer.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="forbidden")
    if not management_scope and transfer.project_id != scoped_project_id:
        raise HTTPException(status_code=403, detail="forbidden")
    if management_scope and scoped_project_id is not None and transfer.project_id != scoped_project_id:
        raise HTTPException(status_code=403, detail="transfer is outside selected project scope")

    vehicle_code = str(payload.get("vehicle_code") or "").strip().upper()
    if not vehicle_code:
        raise HTTPException(status_code=400, detail="vehicle_code is required")
    transfer_point = str(payload.get("transfer_point") or "").strip() or None
    pickup_time = str(payload.get("pickup_time") or "").strip() or None

    supplier_company_id = payload.get("supplier_company_id")
    greeter_staff_id = payload.get("greeter_staff_id")
    driver_staff_id = payload.get("driver_staff_id")
    if supplier_company_id is not None:
        supplier_company_id = int(supplier_company_id)
    if greeter_staff_id is not None:
        greeter_staff_id = int(greeter_staff_id)
    if driver_staff_id is not None:
        driver_staff_id = int(driver_staff_id)

    if supplier_company_id is not None:
        supplier = db.query(SupplierCompany).filter(SupplierCompany.id == supplier_company_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="supplier company not found")
        if supplier.tenant_id != transfer.tenant_id:
            raise HTTPException(status_code=400, detail="supplier company tenant mismatch")
        transfer.supplier_company_id = supplier.id
    if greeter_staff_id is not None:
        greeter = db.query(SupplierStaff).filter(SupplierStaff.id == greeter_staff_id).first()
        if not greeter or greeter.role != "greeter":
            raise HTTPException(status_code=400, detail="greeter staff not found")
        if greeter.tenant_id != transfer.tenant_id:
            raise HTTPException(status_code=400, detail="greeter tenant mismatch")
        transfer.greeter_staff_id = greeter.id
        if not transfer.greeter_action:
            transfer.greeter_action = PERSONNEL_ACTION_FLOW[0]
    if driver_staff_id is not None:
        driver = db.query(SupplierStaff).filter(SupplierStaff.id == driver_staff_id).first()
        if not driver or driver.role != "driver":
            raise HTTPException(status_code=400, detail="driver staff not found")
        if driver.tenant_id != transfer.tenant_id:
            raise HTTPException(status_code=400, detail="driver tenant mismatch")
        transfer.driver_staff_id = driver.id
        if not transfer.driver_action:
            transfer.driver_action = PERSONNEL_ACTION_FLOW[0]

    transfer.vehicle_code = vehicle_code
    transfer.transfer_point = transfer_point
    transfer.pickup_time = pickup_time

    existing_group = (
        db.query(Transfer)
        .filter(
            Transfer.id != transfer.id,
            Transfer.tenant_id == transfer.tenant_id,
            Transfer.project_id == transfer.project_id,
            Transfer.flight_date == transfer.flight_date,
            Transfer.vehicle_code == vehicle_code,
            Transfer.reservation_code.isnot(None),
        )
        .order_by(Transfer.id.desc())
        .first()
    )
    transfer.reservation_code = (
        existing_group.reservation_code
        if existing_group and existing_group.reservation_code
        else _build_reservation_code(vehicle_code, transfer.flight_date, transfer.project_id)
    )
    if not transfer.transfer_action:
        transfer.transfer_action = TRANSFER_ACTION_FLOW[0]

    db.commit()
    db.refresh(transfer)
    return {
        "id": transfer.id,
        "reservation_code": transfer.reservation_code,
        "vehicle_code": transfer.vehicle_code,
        "transfer_action": transfer.transfer_action,
        "pickup_time": transfer.pickup_time,
        "transfer_point": transfer.transfer_point,
    }


@app.post("/transfer-ops/advance")
def advance_transfer_operation(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    scoped_project_id, management_scope = _resolve_project_scope_for_user(
        db, current_user, payload.get("project_id")
    )
    transfer_id = int(payload.get("transfer_id") or 0)
    if not transfer_id:
        raise HTTPException(status_code=400, detail="transfer_id is required")
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="transfer not found")
    if not is_superadmin(current_user) and transfer.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="forbidden")
    if not management_scope and transfer.project_id != scoped_project_id:
        raise HTTPException(status_code=403, detail="forbidden")
    if management_scope and scoped_project_id is not None and transfer.project_id != scoped_project_id:
        raise HTTPException(status_code=403, detail="transfer is outside selected project scope")
    next_action = _next_transfer_action(transfer.transfer_action)
    if next_action is None:
        return {"id": transfer.id, "done": True, "transfer_action": transfer.transfer_action}
    transfer.transfer_action = next_action
    db.commit()
    db.refresh(transfer)
    return {"id": transfer.id, "done": False, "transfer_action": transfer.transfer_action}


@app.get("/supplier-transfers")
def supplier_transfers(
    supplier_company_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    scoped_project_id, management_scope = _resolve_project_scope_for_user(db, current_user, project_id)
    query = db.query(Transfer)
    if not is_superadmin(current_user):
        query = query.filter(Transfer.tenant_id == current_user.tenant_id)
    if not management_scope:
        query = query.filter(Transfer.project_id == scoped_project_id)
    elif scoped_project_id is not None:
        query = query.filter(Transfer.project_id == scoped_project_id)
    if supplier_company_id is not None:
        query = query.filter(Transfer.supplier_company_id == supplier_company_id)
    rows = query.order_by(Transfer.created_at.desc()).all()
    supplier_ids = sorted({int(r.supplier_company_id) for r in rows if r.supplier_company_id})
    staff_ids = sorted(
        {
            int(x)
            for r in rows
            for x in [r.greeter_staff_id, r.driver_staff_id]
            if x
        }
    )
    supplier_map = {x.id: x.name for x in db.query(SupplierCompany).filter(SupplierCompany.id.in_(supplier_ids)).all()} if supplier_ids else {}
    staff_map = {x.id: x.full_name for x in db.query(SupplierStaff).filter(SupplierStaff.id.in_(staff_ids)).all()} if staff_ids else {}
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "passenger_name": _normalized_person_name(r) or r.passenger_name,
            "pnr": r.pnr,
            "flight_no": r.flight_no,
            "date": r.flight_date,
            "from": r.pickup_location,
            "to": r.dropoff_location,
            "supplier_company_id": r.supplier_company_id,
            "supplier_company": supplier_map.get(r.supplier_company_id),
            "greeter_staff_id": r.greeter_staff_id,
            "greeter_name": staff_map.get(r.greeter_staff_id),
            "driver_staff_id": r.driver_staff_id,
            "driver_name": staff_map.get(r.driver_staff_id),
            "participant_phone": r.participant_phone,
            "participant_order_no": r.participant_order_no,
            "pickup_time": r.pickup_time,
            "transfer_point": r.transfer_point,
            "vehicle_code": r.vehicle_code,
            "reservation_code": r.reservation_code,
            "transfer_action": r.transfer_action,
            "driver_action": r.driver_action,
            "greeter_action": r.greeter_action,
            "next_action": _next_transfer_action(r.transfer_action),
        }
        for r in rows
    ]


@app.get("/supplier-transfers-ui", response_class=HTMLResponse)
def supplier_transfers_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Supplier Transfers</title>
  <style>
    body { font-family: Arial, sans-serif; margin:0; background: linear-gradient(135deg,#e6eefc 0%,#dbe7fb 48%,#edf3ff 100%); color:#1c2635; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:14px; }
    .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-top:8px; }
    .muted { color:#5c6b82; font-size:13px; }
    .btn { border:0; border-radius:8px; background:#2b7fff; color:#fff; padding:8px 12px; cursor:pointer; }
    .btn.alt { background:#5c6b82; }
    table { width:100%; border-collapse:collapse; margin-top:10px; font-size:12px; }
    th, td { border:1px solid #dde4ef; padding:8px; text-align:left; }
    th { background:#f0f5ff; }
    .chip { padding:2px 8px; border-radius:999px; background:#eef4ff; border:1px solid #d3e0fa; font-size:11px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="box">
      <h3 style="margin:0;">Araç Firması Transferleri</h3>
      <div class="muted">Sürücü atanmış satırlarda tek tıkla panel linki oluşturup SMS kuyruğuna gönderebilirsiniz.</div>
      <div class="row">
        <button id="refreshBtn" class="btn alt" type="button">Yenile</button>
        <span id="summary" class="muted"></span>
      </div>
      <table id="tbl" style="display:none;">
        <thead><tr><th>ID</th><th>Sıra</th><th>Yolcu</th><th>Telefon</th><th>Nereden</th><th>Nereye</th><th>Rezervasyon</th><th>Sürücü</th><th>Karşılamacı</th><th>Sürücü Durum</th><th>Karşılamacı Durum</th><th>İşlem</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
  <script>
    (function(){
      const token = localStorage.getItem('access_token') || '';
      const tbl = document.getElementById('tbl');
      const body = tbl.querySelector('tbody');
      const summary = document.getElementById('summary');
      const headers = () => ({ Authorization: `Bearer ${token}` });
      const esc = (v) => String(v == null ? '' : v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

      async function load(){
        if (!token) { window.location.href = '/'; return; }
        const res = await fetch('/supplier-transfers', { headers: headers() });
        const data = await res.json().catch(() => []);
        if (!res.ok) { summary.textContent = 'Hata: ' + (data.detail || 'Liste alınamadı'); return; }
        const rows = Array.isArray(data) ? data : [];
        body.innerHTML = rows.map((r) => {
          const canSendDriver = !!r.driver_staff_id;
          const canSendGreeter = !!r.greeter_staff_id;
          return `<tr>
            <td>${esc(r.id)}</td>
            <td>${esc(r.participant_order_no)}</td>
            <td>${esc(r.passenger_name)}</td>
            <td>${esc(r.participant_phone || '-')}</td>
            <td>${esc(r.from || '-')}</td>
            <td>${esc(r.to || '-')}</td>
            <td>${esc(r.reservation_code)}</td>
            <td>${esc(r.driver_name || '-')}</td>
            <td>${esc(r.greeter_name || '-')}</td>
            <td><span class="chip">${esc(r.driver_action || '-')}</span></td>
            <td><span class="chip">${esc(r.greeter_action || '-')}</span></td>
            <td>
              ${canSendDriver ? `<button class="btn sendLinkBtn" data-role="driver" data-id="${r.id}" type="button">Sürücü Link</button>` : '<span class="muted">Sürücü yok</span>'}
              ${canSendGreeter ? `<button class="btn alt sendLinkBtn" data-role="greeter" data-id="${r.id}" type="button">Karşılamacı Link</button>` : '<span class="muted"> Karşılamacı yok</span>'}
            </td>
          </tr>`;
        }).join('');
        tbl.style.display = rows.length ? '' : 'none';
        summary.textContent = `${rows.length} transfer listelendi.`;
      }

      async function sendLink(transferId, role){
        const res = await fetch('/driver-panel/link', {
          method: 'POST',
          headers: { ...headers(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ transfer_id: Number(transferId), panel_role: (role || 'driver'), ttl_minutes: 720 })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { summary.textContent = 'Hata: ' + (data.detail || 'Link üretilemedi'); return; }
        const smsInfo = data.sms_queued ? 'SMS kuyruğa eklendi.' : 'Telefon yok, SMS kuyruğa eklenmedi.';
        summary.textContent = `Link hazır (${data.panel_role || role || '-'} / ${data.staff_name || '-'}): ${smsInfo}`;
        try { await navigator.clipboard.writeText(data.panel_link || ''); } catch (_) {}
        const roleLabel = (data.panel_role || role || 'driver') === 'greeter' ? 'Karşılamacı' : 'Sürücü';
        alert(`${roleLabel} Linki Hazır\\n\\n${data.panel_link || '-'}\\n\\n${smsInfo}`);
      }

      document.getElementById('refreshBtn').addEventListener('click', load);
      body.addEventListener('click', (e) => {
        const btn = e.target && e.target.closest ? e.target.closest('.sendLinkBtn') : null;
        if (!btn) return;
        const id = Number(btn.getAttribute('data-id') || 0);
        const role = String(btn.getAttribute('data-role') || 'driver');
        if (!id) return;
        sendLink(id, role);
      });
      load();
    })();
  </script>
</body>
</html>
"""


@app.post("/driver-panel/link")
def create_driver_panel_link(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_transfer_operator),
):
    transfer_id = int(payload.get("transfer_id") or 0)
    panel_role = str(payload.get("panel_role") or "driver").strip().lower()
    ttl_minutes = int(payload.get("ttl_minutes") or 720)
    if not transfer_id:
        raise HTTPException(status_code=400, detail="transfer_id is required")
    if panel_role not in {"driver", "greeter"}:
        raise HTTPException(status_code=400, detail="panel_role must be driver or greeter")
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="transfer not found")
    if panel_role == "driver" and not transfer.driver_staff_id:
        raise HTTPException(status_code=400, detail="driver is not assigned for transfer")
    if panel_role == "greeter" and not transfer.greeter_staff_id:
        raise HTTPException(status_code=400, detail="greeter is not assigned for transfer")
    if not is_superadmin(current_user) and int(transfer.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="forbidden")

    target_staff_id = int(transfer.driver_staff_id) if panel_role == "driver" else int(transfer.greeter_staff_id)
    staff = db.query(SupplierStaff).filter(SupplierStaff.id == target_staff_id).first()
    if not staff or str(staff.role or "").lower() != panel_role:
        raise HTTPException(status_code=400, detail=f"{panel_role} staff not found")
    if int(staff.tenant_id or 0) != int(transfer.tenant_id or 0):
        raise HTTPException(status_code=400, detail=f"{panel_role} tenant mismatch")

    token_raw, token_row = _issue_driver_panel_token(
        db,
        tenant_id=int(transfer.tenant_id or 0),
        project_id=int(transfer.project_id) if transfer.project_id is not None else None,
        supplier_company_id=int(transfer.supplier_company_id) if transfer.supplier_company_id is not None else None,
        panel_role=panel_role,
        staff_id=int(staff.id),
        created_by_user_id=int(current_user.id),
        ttl_minutes=max(5, min(4320, ttl_minutes)),
    )
    base_url = str(os.getenv("PUBLIC_BASE_URL") or "http://localhost:8000").strip().rstrip("/")
    panel_path = "/driver-panel" if panel_role == "driver" else "/greeter-panel"
    panel_link = f"{base_url}{panel_path}?token={token_raw}"

    sms_phone = str(staff.phone or "").strip()
    sms_label = "Sürücü" if panel_role == "driver" else "Karşılamacı"
    sms_message = f"{sms_label} panel bağlantınız: {panel_link}"
    queued_sms = False
    if sms_phone:
        db.add(
            SupplierSmsQueue(
                tenant_id=int(transfer.tenant_id or 0),
                booking_id=None,
                to_phone=sms_phone,
                message=sms_message,
                status="queued",
                error_message=None,
            )
        )
        queued_sms = True

    db.commit()
    return {
        "ok": True,
        "token_id": token_row.id,
        "expires_at": token_row.expires_at,
        "panel_role": panel_role,
        "staff_id": staff.id,
        "staff_name": staff.full_name,
        "staff_phone": staff.phone,
        "panel_link": panel_link,
        "sms_queued": queued_sms,
    }


@app.post("/greeter-panel/link")
def create_greeter_panel_link(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_transfer_operator),
):
    body = dict(payload or {})
    body["panel_role"] = "greeter"
    return create_driver_panel_link(body, db, current_user)


@app.get("/driver-panel/session")
def driver_panel_session(
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    token_row = _get_driver_panel_token_row(db, token)
    if not token_row:
        raise HTTPException(status_code=401, detail="Invalid or expired driver panel token")
    panel_role = str(token_row.panel_role or "driver").strip().lower()
    staff_id = int(token_row.driver_staff_id or 0) if panel_role == "driver" else int(token_row.greeter_staff_id or token_row.driver_staff_id or 0)
    staff = db.query(SupplierStaff).filter(SupplierStaff.id == staff_id).first()
    if not staff or not bool(staff.is_active):
        raise HTTPException(status_code=401, detail=f"{panel_role} account is inactive")
    rows = (
        _driver_panel_transfers_query(db, token_row)
        .order_by(Transfer.created_at.desc())
        .limit(200)
        .all()
    )
    return {
        "staff": {
            "id": staff.id,
            "full_name": staff.full_name,
            "phone": staff.phone,
            "vehicle_plate": staff.vehicle_plate,
            "role": panel_role,
        },
        "token": {
            "id": token_row.id,
            "project_id": token_row.project_id,
            "supplier_company_id": token_row.supplier_company_id,
            "panel_role": panel_role,
            "expires_at": token_row.expires_at,
        },
        "transfers": [
            {
                "id": r.id,
                "project_id": r.project_id,
                "passenger_name": _normalized_person_name(r) or r.passenger_name,
                "pnr": r.pnr,
                "flight_no": r.flight_no,
                "date": r.flight_date,
                "pickup_time": r.pickup_time,
                "from": r.pickup_location,
                "to": r.dropoff_location,
                "vehicle_code": r.vehicle_code,
                "reservation_code": r.reservation_code,
                "driver_action": r.driver_action,
                "greeter_action": r.greeter_action,
                "action": (r.driver_action if panel_role == "driver" else r.greeter_action),
                "next_action": _next_personnel_action(r.driver_action if panel_role == "driver" else r.greeter_action),
            }
            for r in rows
        ],
    }


@app.post("/driver-panel/advance")
def driver_panel_advance(
    payload: dict,
    db: Session = Depends(get_db),
):
    token_row = _get_driver_panel_token_row(db, payload.get("token"))
    if not token_row:
        raise HTTPException(status_code=401, detail="Invalid or expired driver panel token")
    panel_role = str(token_row.panel_role or "driver").strip().lower()
    transfer_id = int(payload.get("transfer_id") or 0)
    if not transfer_id:
        raise HTTPException(status_code=400, detail="transfer_id is required")
    transfer = (
        _driver_panel_transfers_query(db, token_row)
        .filter(Transfer.id == transfer_id)
        .first()
    )
    if not transfer:
        raise HTTPException(status_code=404, detail="transfer not found in driver scope")
    current_action = transfer.driver_action if panel_role == "driver" else transfer.greeter_action
    next_action = _next_personnel_action(current_action)
    if next_action is None:
        queued_sms = _queue_driver_group_sms(db, transfer, current_action)
        db.commit()
        return {"id": transfer.id, "done": True, "panel_role": panel_role, "action": current_action, "queued_sms": queued_sms}
    if panel_role == "driver":
        transfer.driver_action = next_action
    else:
        transfer.greeter_action = next_action
    queued_sms = _queue_driver_group_sms(db, transfer, next_action)
    db.commit()
    db.refresh(transfer)
    return {"id": transfer.id, "done": False, "panel_role": panel_role, "action": next_action, "queued_sms": queued_sms}


@app.post("/driver-panel/command")
def driver_panel_command(
    payload: dict,
    db: Session = Depends(get_db),
):
    token_row = _get_driver_panel_token_row(db, payload.get("token"))
    if not token_row:
        raise HTTPException(status_code=401, detail="Invalid or expired driver panel token")
    panel_role = str(token_row.panel_role or "driver").strip().lower()
    command = str(payload.get("command") or "").strip()
    if not command:
        raise HTTPException(status_code=400, detail="command is required")

    parts = command.split()
    verb = parts[0].strip().upper()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if verb == "LIST":
        rows = (
            _driver_panel_transfers_query(db, token_row)
            .order_by(Transfer.created_at.desc())
            .limit(20)
            .all()
        )
        return {
            "ok": True,
            "command": "LIST",
            "items": [
                {
                    "id": r.id,
                    "reservation_code": r.reservation_code,
                    "passenger_name": _normalized_person_name(r) or r.passenger_name,
                    "action": (r.driver_action if panel_role == "driver" else r.greeter_action),
                    "next_action": _next_personnel_action(r.driver_action if panel_role == "driver" else r.greeter_action),
                }
                for r in rows
            ],
        }

    if verb in {"NEXT", "ADVANCE"}:
        q = _driver_panel_transfers_query(db, token_row)
        target = None
        if arg.isdigit():
            target = q.filter(Transfer.id == int(arg)).first()
        if target is None and arg:
            target = q.filter(Transfer.reservation_code == arg.upper()).order_by(Transfer.id.desc()).first()
        if not target:
            raise HTTPException(status_code=404, detail="transfer not found for command target")
        current_action = target.driver_action if panel_role == "driver" else target.greeter_action
        next_action = _next_personnel_action(current_action)
        if next_action is None:
            queued_sms = _queue_driver_group_sms(db, target, current_action)
            db.commit()
            return {"ok": True, "done": True, "panel_role": panel_role, "id": target.id, "action": current_action, "queued_sms": queued_sms}
        if panel_role == "driver":
            target.driver_action = next_action
        else:
            target.greeter_action = next_action
        queued_sms = _queue_driver_group_sms(db, target, next_action)
        db.commit()
        db.refresh(target)
        return {"ok": True, "done": False, "panel_role": panel_role, "id": target.id, "action": next_action, "queued_sms": queued_sms}

    raise HTTPException(status_code=400, detail="Supported commands: LIST, NEXT <transfer_id|reservation_code>")


@app.get("/driver-panel", response_class=HTMLResponse)
@app.get("/greeter-panel", response_class=HTMLResponse)
def driver_panel_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Personel Paneli</title>
  <style>
    body { font-family: Arial, sans-serif; margin:0; background:#eef3fb; color:#1c2635; }
    .wrap { max-width: 1100px; margin: 0 auto; padding: 16px; }
    .card { background:#fff; border:1px solid #dbe3f0; border-radius:12px; padding:14px; margin-bottom:12px; }
    .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
    .muted { color:#5c6b82; font-size:13px; }
    .btn { border:0; border-radius:8px; background:#2b7fff; color:#fff; padding:8px 12px; cursor:pointer; }
    .btn.alt { background:#5c6b82; }
    table { width:100%; border-collapse:collapse; margin-top:8px; font-size:12px; }
    th, td { border:1px solid #dde4ef; padding:8px; text-align:left; }
    th { background:#f0f5ff; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h3 id="panelTitle" style="margin:0 0 8px;">Personel Paneli</h3>
      <div id="driverInfo" class="muted">Yükleniyor...</div>
      <div class="row" style="margin-top:8px;">
        <input id="cmd" placeholder="Komut (LIST veya NEXT 123)" style="padding:8px;min-width:260px;border:1px solid #cfd9e8;border-radius:8px;" />
        <button id="cmdBtn" class="btn" type="button">Komut Çalıştır</button>
        <button id="refreshBtn" class="btn alt" type="button">Yenile</button>
      </div>
      <div id="msg" class="muted" style="margin-top:8px;"></div>
    </div>
    <div class="card">
      <table>
        <thead><tr><th>ID</th><th>Yolcu</th><th>Rezervasyon</th><th>Nereden</th><th>Nereye</th><th>Tarih</th><th>Saat</th><th>Kendi Durum</th><th>Diğer Durum</th><th>İşlem</th></tr></thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
  </div>
  <script>
    (function(){
      const qs = new URLSearchParams(window.location.search);
      const token = qs.get('token') || '';
      const tbody = document.getElementById('tbody');
      const msg = document.getElementById('msg');
      const driverInfo = document.getElementById('driverInfo');
      const panelTitle = document.getElementById('panelTitle');
      const esc = (v) => String(v || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      let rows = [];

      async function load(){
        if (!token) { driverInfo.textContent = 'Token bulunamadı.'; return; }
        const res = await fetch('/driver-panel/session?token=' + encodeURIComponent(token));
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { driverInfo.textContent = 'Hata: ' + (data.detail || 'Oturum açılamadı'); return; }
        const d = data.staff || {};
        const role = String((d.role || data?.token?.panel_role || '')).toLowerCase();
        const roleLabel = role === 'greeter' ? 'Karşılamacı' : 'Sürücü';
        if (panelTitle) panelTitle.textContent = roleLabel + ' Paneli';
        driverInfo.textContent = `${roleLabel}: ${d.full_name || '-'} | ${d.phone || '-'} | Araç: ${d.vehicle_plate || '-'}`;
        rows = Array.isArray(data.transfers) ? data.transfers : [];
        tbody.innerHTML = rows.map((r) => `<tr>
          <td>${esc(r.id)}</td>
          <td>${esc(r.passenger_name)}</td>
          <td>${esc(r.reservation_code)}</td>
          <td>${esc(r.from)}</td>
          <td>${esc(r.to)}</td>
          <td>${esc(r.date)}</td>
          <td>${esc(r.pickup_time)}</td>
          <td>${esc(r.action || '-')}</td>
          <td>${esc((String((d.role || data?.token?.panel_role || '')).toLowerCase() === 'greeter') ? (r.driver_action || '-') : (r.greeter_action || '-'))}</td>
          <td><button class="btn adv" data-id="${r.id}" type="button">İlerle</button></td>
        </tr>`).join('');
        msg.textContent = rows.length + ' transfer listelendi.';
      }

      async function advanceTransfer(transferId){
        const res = await fetch('/driver-panel/advance', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ token, transfer_id: transferId })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { msg.textContent = 'Hata: ' + (data.detail || 'Aksiyon ilerletilemedi'); return; }
        msg.textContent = `Transfer #${data.id} -> ${data.action} | SMS: ${Number(data.queued_sms || 0)}`;
        await load();
      }

      document.getElementById('refreshBtn').addEventListener('click', load);
      document.getElementById('cmdBtn').addEventListener('click', async () => {
        const command = (document.getElementById('cmd').value || '').trim();
        if (!command) return;
        const res = await fetch('/driver-panel/command', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ token, command })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { msg.textContent = 'Hata: ' + (data.detail || 'Komut başarısız'); return; }
        msg.textContent = `Komut işlendi: ${command} | SMS: ${Number(data.queued_sms || 0)}`;
        await load();
      });

      tbody.addEventListener('click', (e) => {
        const btn = e.target && e.target.closest ? e.target.closest('.adv') : null;
        if (!btn) return;
        const id = Number(btn.getAttribute('data-id') || 0);
        if (!id) return;
        advanceTransfer(id);
      });

      load();
    })();
  </script>
</body>
</html>
"""


@app.get("/upload-ui", response_class=HTMLResponse)
def upload_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Transfer</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .box { width: 100vw; max-width: 100vw; margin: 0; background: #fff; border: 1px solid #dde4ef; border-radius: 0; padding: 12px 14px; box-sizing: border-box; }
    .drop { border: 2px dashed #93a7c2; border-radius: 10px; padding: 14px; text-align: center; background: #fbfdff; margin-top: 6px; }
    .drop.dragover { border-color: #2b7fff; background: #eef5ff; }
    button { background: #2b7fff; color: #fff; border: 0; border-radius: 8px; padding: 10px 14px; cursor: pointer; }
    .btn-row { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
    .btn-muted { background: #5c6b82; }
    .btn-green { background: #0f9d58; }
    .table-wrap { width: 100%; overflow-x: auto; margin-top: 10px; }
    table { width: 100%; border-collapse: collapse; margin-top: 0; font-size: 12px; min-width: 1350px; }
    th, td { border: 1px solid #dde4ef; padding: 8px; text-align: left; }
    th { background: #f0f5ff; }
    #transferTable thead th { font-size: 10px; }
    .muted { color: #5c6b82; font-size: 13px; margin-top: 8px; }
    .section-title { margin-top: 12px; font-size: 15px; font-weight: 700; }
    .footer-brand { position: fixed; left: 0; right: 0; bottom: 0; height: 54px; background: #0A1024; display: flex; align-items: center; padding-left: 12px; z-index: 998; overflow: hidden; }
    .footer-brand img { height: 150%; width: auto; display: block; object-fit: cover; object-position: center; clip-path: inset(0 3% 0 0); }
    .logo-reg { color: #fff; font-size: 12px; line-height: 1; margin-left: 0; font-weight: 700; position: relative; left: -26px; transform: translateY(-45%); }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
    .overlay { position: fixed; inset: 0; background: rgba(10,16,36,0.45); display: none; align-items: center; justify-content: center; z-index: 1200; }
    .overlay .card { background: #fff; border: 1px solid #d8e0ee; border-radius: 12px; min-width: 320px; padding: 16px; text-align: center; box-shadow: 0 12px 30px rgba(10,16,36,0.22); }
    .spinner { width: 28px; height: 28px; border: 3px solid #d9e5fb; border-top-color: #2b7fff; border-radius: 50%; margin: 0 auto 10px auto; animation: spin 1s linear infinite; }
    .popup { position: fixed; inset: 0; background: rgba(10,16,36,0.45); display: none; align-items: center; justify-content: center; z-index: 1250; }
    .popup .card { background: #fff; border: 1px solid #d8e0ee; border-radius: 12px; min-width: 360px; max-width: 92vw; padding: 16px; box-shadow: 0 12px 30px rgba(10,16,36,0.22); }
    .popup .title { font-size: 15px; font-weight: 700; margin-bottom: 8px; }
    .popup .actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
    .btn-small { padding: 6px 10px; font-size: 12px; border-radius: 6px; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div class="box">
    <div id="projectInfo" class="muted" style="display:none;">Aktif proje: seçilmedi</div>
    <div style="display:none;">
      <select id="projectSelect"><option value="">Proje Seçiniz</option></select>
      <input id="projectQuick" list="projectOptions" placeholder="Proje kodu veya ad yazin" />
      <datalist id="projectOptions"></datalist>
      <button id="reloadProjectsBtn" type="button" class="btn-muted">Projeleri Yenile</button>
    </div>

    <div class="section-title">1) Dosya Yükleme</div>
    <div id="drop" class="drop">
      <div>Dosyalari surukleyip birakin (pdf, zip, jpg, jpeg, png)</div>
      <div class="muted">veya</div>
      <input id="picker" type="file" multiple accept=".pdf,.zip,.jpg,.jpeg,.png" />
      <div class="btn-row"><button id="uploadBtn" type="button">Yükle</button></div>
    </div>

    <div class="section-title">2) İşlemler</div>
    <div class="btn-row">
      <button id="listTransfersBtn" type="button" class="btn-muted">İçeri Aktar (Tümü)</button>
      <button id="transferSelectedBtn" type="button" class="btn-muted">Seçilenleri Aktar</button>
      <button id="exportZipBtn" type="button" class="btn-green">ZIP Dışarı Aktar</button>
    </div>
    <div id="summary" class="muted"></div>

    <div class="table-wrap">
    <table id="resultTable" style="display:none;">
      <thead>
        <tr>
          <th><input id="selectAllFiltered" type="checkbox" title="Filtrelenenleri seç" /></th>
          <th>Düzenle</th>
          <th data-sort="original_filename">Dosya</th>
          <th data-sort="upload_id">Yükleme ID</th>
          <th data-sort="status">Durum</th>
          <th data-sort="passenger_name">Yolcu</th>
          <th data-sort="pnr">PNR</th>
          <th data-sort="issue_date">Düzenlenme Tarihi</th>
          <th data-sort="ucus_sekli">Uçuş Şekli</th>
          <th data-sort="flight_no">Uçuş Kodu</th>
          <th data-sort="from_to">Rota</th>
          <th data-sort="kalkis_tarihi_saati">Kalkış Tarihi-Saati</th>
          <th data-sort="inis_tarihi_saati">İniş Tarihi-Saati</th>
          <th data-sort="pickup_time">Karşılama Saati</th>
          <th data-sort="transfer_point">Transfer Noktası</th>
          <th data-sort="vehicle_code">Araç Kodu</th>
          <th data-sort="note">Not</th>
        </tr>
        <tr>
          <th></th><th></th><th></th><th></th>
          <th><input data-filter="status" placeholder="filtre" style="width:90px;" /></th>
          <th><input data-filter="passenger_name" placeholder="filtre" style="width:120px;" /></th>
          <th><input data-filter="pnr" placeholder="filtre" style="width:80px;" /></th>
          <th><input data-filter="issue_date" placeholder="filtre" style="width:100px;" /></th>
          <th><input data-filter="ucus_sekli" placeholder="filtre" style="width:100px;" /></th>
          <th><input data-filter="flight_no" placeholder="filtre" style="width:90px;" /></th>
          <th><input data-filter="from_to" placeholder="filtre" style="width:90px;" /></th>
          <th><input data-filter="kalkis_tarihi_saati" placeholder="filtre" style="width:110px;" /></th>
          <th><input data-filter="inis_tarihi_saati" placeholder="filtre" style="width:110px;" /></th>
          <th><input data-filter="pickup_time" placeholder="filtre" style="width:95px;" /></th>
          <th><input data-filter="transfer_point" placeholder="filtre" style="width:95px;" /></th>
          <th><input data-filter="vehicle_code" placeholder="filtre" style="width:90px;" /></th>
          <th><input data-filter="note" placeholder="filtre" style="width:90px;" /></th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
    </div>

    <div class="section-title">3) Transfer Listesi</div>
    <div class="btn-row">
      <button id="refreshTransferListBtn" type="button" class="btn-muted">Transfer Listesini Yenile</button>
      <a href="/supplier-transfers-ui" class="btn" style="text-decoration:none;">Sürücü Link Gönder</a>
    </div>
    <div class="table-wrap">
    <table id="transferTable" style="display:none;">
      <thead>
        <tr>
          <th data-tsort="id">ID</th>
          <th data-tsort="passenger_name">YOLCU</th>
          <th data-tsort="cinsiyet">CİNSİYET</th>
          <th data-tsort="pnr">PNR</th>
          <th data-tsort="duzenlenme_tarihi">DÜZENLENME TARİHİ</th>
          <th data-tsort="ucus_sekli">UÇUŞ ŞEKLİ</th>
          <th data-tsort="flight_no">UÇUŞ KODU</th>
          <th data-tsort="from_to">ROTA</th>
          <th data-tsort="kalkis_tarihi_saati">KALKIŞ TARİHİ-SAATİ</th>
          <th data-tsort="inis_tarihi_saati">İNİŞ TARİHİ-SAATİ</th>
          <th data-tsort="pickup_time">KARŞILAMA SAATİ</th>
          <th data-tsort="transfer_noktasi">TRANSFER NOKTASI</th>
          <th data-tsort="arac_kod">ARAÇ KODU</th>
          <th data-tsort="status">DURUM</th>
        </tr>
        <tr>
          <th><input data-tfilter="id" placeholder="filtre" style="width:60px;" /></th>
          <th><input data-tfilter="passenger_name" placeholder="filtre" style="width:120px;" /></th>
          <th><input data-tfilter="cinsiyet" placeholder="filtre" style="width:80px;" /></th>
          <th><input data-tfilter="pnr" placeholder="filtre" style="width:80px;" /></th>
          <th><input data-tfilter="duzenlenme_tarihi" placeholder="filtre" style="width:100px;" /></th>
          <th><input data-tfilter="ucus_sekli" placeholder="filtre" style="width:100px;" /></th>
          <th><input data-tfilter="flight_no" placeholder="filtre" style="width:90px;" /></th>
          <th><input data-tfilter="from_to" placeholder="filtre" style="width:90px;" /></th>
          <th><input data-tfilter="kalkis_tarihi_saati" placeholder="filtre" style="width:110px;" /></th>
          <th><input data-tfilter="inis_tarihi_saati" placeholder="filtre" style="width:110px;" /></th>
          <th><input data-tfilter="pickup_time" placeholder="filtre" style="width:95px;" /></th>
          <th><input data-tfilter="transfer_noktasi" placeholder="filtre" style="width:95px;" /></th>
          <th><input data-tfilter="arac_kod" placeholder="filtre" style="width:90px;" /></th>
          <th><input data-tfilter="status" placeholder="filtre" style="width:80px;" /></th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
    </div>
  </div>
  <div id="loadingOverlay" class="overlay">
    <div class="card">
      <div class="spinner"></div>
      <div id="loadingText">Yükleniyor...</div>
    </div>
  </div>
  <div id="refreshPopup" class="popup">
    <div class="card">
      <div class="title">Yükleme Tamamlandı</div>
      <div id="refreshPopupText">Dosyalar yüklendi. Listeyi güncellemek için aşağıdan devam edin.</div>
      <div class="actions">
        <button id="refreshPopupClose" type="button" class="btn-muted btn-small">Kapat</button>
        <button id="refreshPopupAction" type="button" class="btn-green btn-small">Listeyi Yenile</button>
      </div>
    </div>
  </div>
  <script>
    const drop = document.getElementById('drop');
    const picker = document.getElementById('picker');
    const projectSelect = document.getElementById('projectSelect');
    const projectInfo = document.getElementById('projectInfo');
    const uploadBtn = document.getElementById('uploadBtn');
    const listTransfersBtn = document.getElementById('listTransfersBtn');
    const transferSelectedBtn = document.getElementById('transferSelectedBtn');
    const exportZipBtn = document.getElementById('exportZipBtn');
    const refreshTransferListBtn = document.getElementById('refreshTransferListBtn');
    const summary = document.getElementById('summary');
    const table = document.getElementById('resultTable');
    const tbody = table.querySelector('tbody');
    const tableHead = table.querySelector('thead');
    const selectAllFiltered = document.getElementById('selectAllFiltered');
    const transferTable = document.getElementById('transferTable');
    const transferBody = transferTable.querySelector('tbody');
    const transferHead = transferTable.querySelector('thead');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    const refreshPopup = document.getElementById('refreshPopup');
    const refreshPopupText = document.getElementById('refreshPopupText');
    const refreshPopupAction = document.getElementById('refreshPopupAction');
    const refreshPopupClose = document.getElementById('refreshPopupClose');
    let stagedUploads = [];
    let transferRowsCache = [];

    let selected = [];
    let token = localStorage.getItem('access_token') || '';
    let me = null;
    let processStartedAt = 0;
    let processTimeoutMs = 0;
    let sortStack = [];
    let filterState = {};
    let transferSortStack = [];
    let transferFilterState = {};

    if (!token) {
      window.location.href = '/';
    }

    const authHeaders = () => ({ 'Authorization': `Bearer ${token}` });
    const norm = (v) => String(v || '').trim().toLocaleUpperCase('tr-TR').replace(/\\s+/g, ' ');
    const showLoading = (text) => {
      if (loadingText) loadingText.textContent = text || 'Yükleniyor...';
      if (loadingOverlay) loadingOverlay.style.display = 'flex';
    };
    const hideLoading = () => {
      if (loadingOverlay) loadingOverlay.style.display = 'none';
    };
    const showRefreshPopup = (text) => {
      if (refreshPopupText) refreshPopupText.textContent = text || 'Dosyalar yüklendi.';
      if (refreshPopup) refreshPopup.style.display = 'flex';
    };
    const hideRefreshPopup = () => {
      if (refreshPopup) refreshPopup.style.display = 'none';
    };
    const routePair = (r) => {
      const raw = String(r?.from_to || '').trim();
      if (raw.includes('/')) {
        const parts = raw.split('/');
        return [norm(parts[0]), norm(parts[1])];
      }
      return [norm(r?.from || ''), norm(r?.to || '')];
    };
    const compareCellValues = (avRaw, bvRaw) => {
      const av = String(avRaw || '').toLocaleUpperCase('tr-TR');
      const bv = String(bvRaw || '').toLocaleUpperCase('tr-TR');
      if (av < bv) return -1;
      if (av > bv) return 1;
      return 0;
    };
    const pushSortRule = (stack, key) => {
      const idx = stack.findIndex(x => x.key === key);
      if (idx === 0) {
        stack[0].dir = -stack[0].dir;
        return;
      }
      if (idx > 0) {
        const existing = stack.splice(idx, 1)[0];
        existing.dir = 1;
        stack.unshift(existing);
      } else {
        stack.unshift({ key, dir: 1 });
      }
      if (stack.length > 8) stack.length = 8;
    };
    const getFilteredSortedRows = () => {
      const rows = stagedUploads.map((r, idx) => ({ r, idx }));
      const activeFilters = Object.entries(filterState).filter(([_, v]) => String(v || '').trim() !== '');
      const filtered = rows.filter(({ r }) => {
        for (const [k, v] of activeFilters) {
          const hay = String(r[k] || '').toLocaleUpperCase('tr-TR');
          const needle = String(v || '').toLocaleUpperCase('tr-TR').trim();
          if (!hay.includes(needle)) return false;
        }
        return true;
      });
      if (!sortStack.length) return filtered;
      filtered.sort((a, b) => {
        for (let i = 0; i < sortStack.length; i += 1) {
          const rule = sortStack[i];
          const cmp = compareCellValues(a.r?.[rule.key], b.r?.[rule.key]);
          if (cmp !== 0) return cmp * rule.dir;
        }
        return 0;
      });
      return filtered;
    };

    const stagedDupKey = (r) => {
      return [
        norm(r?.passenger_name || ''),
        norm(r?.ucus_sekli || ''),
        norm(r?.pnr || '')
      ].join('|');
    };
    const buildStagedDupMap = () => {
      const map = {};
      stagedUploads.forEach((r) => {
        const pname = norm(r?.passenger_name || '');
        const flightType = norm(r?.ucus_sekli || '');
        const pnr = norm(r?.pnr || '');
        // Kural: yolcu + bilet türü + pnr üçü de doluysa duplicate kontrolüne girsin.
        if (!pname || !flightType || !pnr) return;
        const key = `${pname}|${flightType}|${pnr}`;
        map[key] = (map[key] || 0) + 1;
      });
      return map;
    };
    const isStagedDuplicateIdx = (idx, dupMap = null) => {
      if (idx < 0 || idx >= stagedUploads.length) return false;
      const map = dupMap || buildStagedDupMap();
      const key = stagedDupKey(stagedUploads[idx]);
      return (map[key] || 0) > 1;
    };

    const renderStagedTable = () => {
      tbody.innerHTML = '';
      const dupMap = buildStagedDupMap();
      const rows = getFilteredSortedRows();
      rows.forEach(({ r, idx }) => {
        const isDup = isStagedDuplicateIdx(idx, dupMap);
        const tr = document.createElement('tr');
        tr.setAttribute('data-idx', String(idx));
        if (isDup) tr.classList.add('dup-alert');
        const noteText = isDup ? ((r.note ? `${r.note} | ` : '') + 'UYARI: Aynı Yolcu + Bilet Türü + PNR') : (r.note || '');
        tr.innerHTML = `<td><input type="checkbox" class="row-select" ${r._selected ? 'checked' : ''} /></td><td>Düzenlenebilir</td><td data-field="original_filename" contenteditable="true">${r.original_filename || ''}</td><td data-field="upload_id" contenteditable="true">${r.upload_id || ''}</td><td data-field="status" contenteditable="true">${r.status || ''}</td><td data-field="passenger_name" contenteditable="true">${r.passenger_name || ''}</td><td data-field="pnr" contenteditable="true">${r.pnr || ''}</td><td data-field="issue_date" contenteditable="true">${r.issue_date || ''}</td><td data-field="ucus_sekli" contenteditable="true">${r.ucus_sekli || ''}</td><td data-field="flight_no" contenteditable="true">${r.flight_no || ''}</td><td data-field="from_to" contenteditable="true">${r.from_to || ''}</td><td data-field="kalkis_tarihi_saati" contenteditable="true">${r.kalkis_tarihi_saati || ''}</td><td data-field="inis_tarihi_saati" contenteditable="true">${r.inis_tarihi_saati || ''}</td><td data-field="pickup_time" contenteditable="true">${r.pickup_time || ''}</td><td data-field="transfer_point" contenteditable="true">${r.transfer_point || ''}</td><td data-field="vehicle_code" contenteditable="true">${r.vehicle_code || ''}</td><td data-field="note" contenteditable="true">${noteText}</td>`;
        tbody.appendChild(tr);
      });
      table.style.display = stagedUploads.length ? '' : 'none';
      if (selectAllFiltered) {
        const visible = rows.length;
        const selectedVisible = rows.filter(x => x.r._selected).length;
        selectAllFiltered.checked = visible > 0 && selectedVisible === visible;
      }
    };
    const fetchProjectTransfers = async () => {
      const listRes = await fetch(`/transfers?project_id=${encodeURIComponent(String(me.active_project_id))}&limit=5000`, { headers: authHeaders() });
      const listData = await listRes.json();
      if (!listRes.ok) throw new Error(listData.detail || 'Transfer listesi alınamadı');
      transferRowsCache = Array.isArray(listData) ? listData : [];
      return transferRowsCache;
    };
    const getFilteredSortedTransferRows = () => {
      const rows = Array.isArray(transferRowsCache) ? [...transferRowsCache] : [];
      const active = Object.entries(transferFilterState).filter(([_, v]) => String(v || '').trim() !== '');
      const filtered = rows.filter(r => {
        for (const [k, v] of active) {
          const hay = String(r?.[k] || '').toLocaleUpperCase('tr-TR');
          const needle = String(v || '').toLocaleUpperCase('tr-TR').trim();
          if (!hay.includes(needle)) return false;
        }
        return true;
      });
      if (!transferSortStack.length) return filtered;
      filtered.sort((a, b) => {
        for (let i = 0; i < transferSortStack.length; i += 1) {
          const rule = transferSortStack[i];
          const cmp = compareCellValues(a?.[rule.key], b?.[rule.key]);
          if (cmp !== 0) return cmp * rule.dir;
        }
        return 0;
      });
      return filtered;
    };
    const renderTransferListTable = () => {
      transferBody.innerHTML = '';
      const rows = getFilteredSortedTransferRows();
      rows.forEach(t => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${t.id ?? ''}</td><td>${t.passenger_name ?? ''}</td><td>${t.cinsiyet ?? ''}</td><td>${t.pnr ?? ''}</td><td>${t.duzenlenme_tarihi ?? ''}</td><td>${t.ucus_sekli ?? ''}</td><td>${t.flight_no ?? ''}</td><td>${t.from_to ?? ''}</td><td>${t.kalkis_tarihi_saati ?? ''}</td><td>${t.inis_tarihi_saati ?? ''}</td><td>${t.pickup_time ?? ''}</td><td>${t.transfer_noktasi ?? ''}</td><td>${t.arac_kod ?? ''}</td><td>${t.status ?? ''}</td>`;
        transferBody.appendChild(tr);
      });
      transferTable.style.display = '';
    };
    const findDuplicateReason = (baseRow, passengerName, pnrValue) => {
      const passengerN = norm(passengerName);
      const pnrN = norm(pnrValue);
      const flightN = norm(baseRow.flight_no);
      const [fromN, toN] = routePair(baseRow);
      for (const item of transferRowsCache) {
        if (!item || !item.id || Number(item.id) === Number(baseRow.id)) continue;
        if (norm(item.passenger_name) !== passengerN) continue;
        const samePnrFlight = !!pnrN && !!flightN && norm(item.pnr) === pnrN && norm(item.flight_no) === flightN;
        const [ifrom, ito] = routePair(item);
        const sameRoute = !!fromN && !!toN && ifrom === fromN && ito === toN;
        if (samePnrFlight) return 'Aynı Passenger + PNR + Uçuş Kodu zaten var.';
        if (sameRoute) return 'Aynı Passenger + Rota zaten var.';
      }
      return '';
    };
    const saveStagedRow = async (idx) => {
      if (idx < 0 || idx >= stagedUploads.length) return { ok: false, message: 'Geçersiz satır.' };
      const s = stagedUploads[idx];
      if (!s.upload_id) return { ok: false, message: 'Upload ID bulunamadı.' };
      if (!transferRowsCache.length) await fetchProjectTransfers();
      const matched = transferRowsCache.filter(t => String(t.upload_id || '') === String(s.upload_id));
      const trf = matched.length ? matched[0] : null;
      if (!trf || !trf.id) return { ok: false, message: 'Bu dosya henüz işlenmemiş. Biraz sonra tekrar deneyin.' };
      const passenger = (s.passenger_name || trf.passenger_name || '').trim();
      const pnr = (s.pnr || trf.pnr || '').trim();
      if (isStagedDuplicateIdx(idx)) {
        return { ok: false, message: 'UYARI: Aynı Yolcu + Bilet Türü + PNR olan kayıt aktarılmaz.' };
      }
      const dupReason = findDuplicateReason(trf, passenger, pnr);
      if (dupReason) return { ok: false, message: dupReason };
      const payload = {
        project_id: me.active_project_id,
        passenger_name: passenger || null,
        pnr: pnr || null,
        issue_date: (s.issue_date || '').trim() || null,
        pickup_time: (s.pickup_time || '').trim() || null,
        transfer_point: (s.transfer_point || '').trim() || null,
        vehicle_code: (s.vehicle_code || '').trim() || null
      };
      const updRes = await fetch(`/transfers/${trf.id}`, {
        method: 'PUT',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const updData = await updRes.json().catch(() => ({}));
      if (!updRes.ok) return { ok: false, message: updData.detail || 'Kaydetme hatası.' };
      return { ok: true, message: `Satır kaydedildi: ${passenger || '-'}` };
    };

    const setFiles = (files) => {
      selected = Array.from(files || []);
      summary.textContent = selected.length ? `${selected.length} dosya secildi.` : 'Dosya secilmedi.';
    };
    picker.addEventListener('change', (e) => setFiles(e.target.files));
    ['dragenter','dragover'].forEach(ev => drop.addEventListener(ev, (e) => { e.preventDefault(); e.stopPropagation(); drop.classList.add('dragover'); }));
    ['dragleave','drop'].forEach(ev => drop.addEventListener(ev, (e) => { e.preventDefault(); e.stopPropagation(); drop.classList.remove('dragover'); }));
    drop.addEventListener('drop', (e) => setFiles(e.dataTransfer.files));

    const ensureActiveProject = async () => {
      if (!token) {
        window.location.href = '/';
        return false;
      }
      const res = await fetch('/auth/me', { headers: authHeaders() });
      const data = await res.json();
      if (!res.ok) {
        localStorage.removeItem('access_token');
        window.location.href = '/';
        return false;
      }
      me = data;
      if (!data.active_project_id) {
        window.location.href = '/project-select-ui';
        return false;
      }
      projectSelect.value = String(data.active_project_id);
      projectInfo.textContent = `Aktif proje: ${data.active_project_name || '-'} | Kod: ${data.active_project_code || '-'}`;
      return true;
    };

    const calculateTimeoutMs = (rows) => {
      const list = Array.isArray(rows) ? rows : [];
      const seconds = 30 + (list.length * 1.5);
      return Math.max(30000, Math.floor(seconds * 1000));
    };
    const timeoutSec = () => Math.ceil((processTimeoutMs || 0) / 1000);
    const elapsedSec = () => processStartedAt ? Math.max(0, Math.floor((Date.now() - processStartedAt) / 1000)) : 0;
    const remainingSec = () => Math.max(0, timeoutSec() - elapsedSec());
    const phaseText = (phase, detail) => {
      if (!processTimeoutMs) return `Aşama ${phase}: ${detail}`;
      return `Aşama ${phase}: ${detail} | Timeout: ${timeoutSec()} sn | Kalan: ~${remainingSec()} sn`;
    };
    const logUploadEdit = async (entry) => {
      try {
        await fetch('/uploads/edit-log', {
          method: 'POST',
          headers: { ...authHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify(entry)
        });
      } catch (_) {}
    };

    const getUploadStatuses = async (uploadIds) => {
      const res = await fetch('/uploads/statuses', {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ upload_ids: uploadIds })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload durumları alınamadı');
      return Array.isArray(data) ? data : [];
    };

    const retryUploads = async (uploadIds) => {
      const res = await fetch('/uploads/retry', {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ upload_ids: uploadIds })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Retry başlatılamadı');
      return data;
    };

    const downloadFailedZip = async (uploadIds) => {
      if (!uploadIds.length) return;
      const res = await fetch('/exports/zip', {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upload_ids: uploadIds,
          only_processed: false,
          project_id: me.active_project_id
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Başarısız dosyalar ZIP indirilemedi');
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'yuklenmeyenler.zip';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    };

    const waitForProcessing = async (uploadIds, timeoutMs, intervalMs = 2000) => {
      const startedAt = Date.now();
      while (Date.now() - startedAt < timeoutMs) {
        await fetchProjectTransfers();
        const statuses = await getUploadStatuses(uploadIds);
        const statusMap = {};
        statuses.forEach(s => { statusMap[String(s.id)] = s; });
        let done = 0;
        const byUpload = {};
        transferRowsCache.forEach(t => {
          if (t.upload_id != null && !byUpload[String(t.upload_id)]) byUpload[String(t.upload_id)] = t;
        });
        stagedUploads = stagedUploads.map(s => {
          const trf = byUpload[String(s.upload_id || '')];
          const st = statusMap[String(s.upload_id || '')];
          const uploadStatus = (st?.status || '').toLowerCase();
          if (uploadStatus === 'processed' || uploadStatus === 'failed') done += 1;
          if (!trf) {
            return {
              ...s,
              status: uploadStatus || s.status || 'pending',
              note: st?.error_message || s.note || ''
            };
          }
          return {
            ...s,
            status: 'hazır',
            passenger_name: s.passenger_name || (trf.passenger_name || ''),
            pnr: s.pnr || (trf.pnr || ''),
            issue_date: s.issue_date || (trf.duzenlenme_tarihi || ''),
            ucus_sekli: trf.ucus_sekli || '',
            flight_no: trf.flight_no || '',
            from_to: trf.from_to || '',
            kalkis_tarihi_saati: trf.kalkis_tarihi_saati || '',
            inis_tarihi_saati: trf.inis_tarihi_saati || '',
            pickup_time: s.pickup_time || (trf.pickup_time || ''),
            transfer_point: s.transfer_point || (trf.transfer_noktasi || ''),
            vehicle_code: s.vehicle_code || (trf.arac_kod || ''),
          };
        });
        showLoading(phaseText('2/3', `İşleniyor... ${done}/${stagedUploads.length}`));
        if (done >= stagedUploads.length) {
          return { allReady: true, unresolved: [] };
        }
        await new Promise(resolve => setTimeout(resolve, intervalMs));
      }
      const unresolved = stagedUploads
        .filter(s => {
          const st = String(s.status || '').toLowerCase();
          return st !== 'processed' && st !== 'failed' && st !== 'hazır';
        })
        .map(s => s.upload_id)
        .filter(Boolean);
      return { allReady: false, unresolved };
    };

    uploadBtn.addEventListener('click', async () => {
      if (!token) { summary.textContent = 'Oturum bulunamadi.'; window.location.href = '/'; return; }
      if (!selected.length) { summary.textContent = 'Once dosya secin.'; return; }
      if (!me || !me.active_project_id) { summary.textContent = 'Aktif proje secilmemis.'; window.location.href='/project-select-ui'; return; }
      tbody.innerHTML = '';
      table.style.display = 'none';
      stagedUploads = [];
      summary.textContent = 'Yükleniyor...';
      showLoading('Aşama 1/3: Dosyalar yükleniyor...');
      const form = new FormData();
      selected.forEach(f => form.append('files', f));
      form.append('project_id', String(me.active_project_id));
      try {
        const res = await fetch('/upload-many', { method:'POST', headers: authHeaders(), body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Yükleme hatasi');
        const rows = data.results || [];
        const uploadIds = rows.filter(r => !!r.id).map(r => r.id);
        stagedUploads = rows.filter(r => !!r.id).map(r => ({
          original_filename: r.original_filename || '',
          upload_id: r.id || null,
          status: r.status || '',
          note: r.note || '',
          _selected: false,
          passenger_name: '',
          pnr: '',
          issue_date: '',
          ucus_sekli: '',
          flight_no: '',
          from_to: '',
          kalkis_tarihi_saati: '',
          inis_tarihi_saati: '',
          pickup_time: '',
          transfer_point: '',
          vehicle_code: ''
        }));
        const timeoutMs = calculateTimeoutMs(rows);
        processStartedAt = Date.now();
        processTimeoutMs = timeoutMs;
        showLoading(phaseText('2/3', `İşlem kuyruğu bekleniyor... 0/${stagedUploads.length}`));
        let unresolved = [...uploadIds];
        let allReady = false;
        const retryCount = 2;
        for (let attempt = 0; attempt <= retryCount; attempt += 1) {
          const result = await waitForProcessing(unresolved, timeoutMs, 2000);
          allReady = !!result.allReady;
          unresolved = Array.isArray(result.unresolved) ? result.unresolved : [];
          if (allReady) break;
          if (!unresolved.length) break;
          if (attempt < retryCount) {
            showLoading(phaseText('3/3', `Yeniden deneniyor... (${attempt + 1}/${retryCount})`));
            await new Promise(resolve => setTimeout(resolve, 30000));
            await retryUploads(unresolved);
          }
        }
        if (allReady) {
          summary.textContent = `Tamamlandi: ${stagedUploads.length} dosya işlendi.`;
          showRefreshPopup(`Yükleme ve işleme tamamlandı. Timeout: ${timeoutSec()} sn. "Listeyi Yenile" butonuna basın.`);
        } else {
          try {
            await downloadFailedZip(unresolved);
            summary.textContent = `Kısmi tamamlandı. ${unresolved.length} dosya yüklenemedi, ZIP indirildi.`;
          } catch (zipErr) {
            summary.textContent = `Kısmi tamamlandı. Kalan dosyalar ZIP indirilemedi: ${zipErr.message}`;
          }
          showRefreshPopup(`Kısmi sonuç hazır. Timeout: ${timeoutSec()} sn. "Listeyi Yenile" ile gelen satırları görebilirsiniz.`);
        }
      } catch (err) { summary.textContent = `Hata: ${err.message}`; }
      finally { hideLoading(); processStartedAt = 0; processTimeoutMs = 0; }
    });

    tbody.addEventListener('input', (e) => {
      const td = e.target.closest('td[data-field]');
      const tr = e.target.closest('tr[data-idx]');
      if (!td || !tr) return;
      const idx = parseInt(tr.getAttribute('data-idx') || '-1', 10);
      if (idx < 0 || idx >= stagedUploads.length) return;
      const field = td.getAttribute('data-field');
      if (!field) return;
      stagedUploads[idx][field] = (td.textContent || '').trim();
      if (field === 'passenger_name' || field === 'ucus_sekli' || field === 'pnr') {
        renderStagedTable();
      }
    });

    tbody.addEventListener('focusin', (e) => {
      const td = e.target.closest('td[data-field]');
      if (!td) return;
      td.dataset.oldValue = (td.textContent || '').trim();
    });

    tbody.addEventListener('focusout', (e) => {
      const td = e.target.closest('td[data-field]');
      const tr = e.target.closest('tr[data-idx]');
      if (!td || !tr) return;
      const idx = parseInt(tr.getAttribute('data-idx') || '-1', 10);
      if (idx < 0 || idx >= stagedUploads.length) return;
      const field = td.getAttribute('data-field');
      if (!field) return;
      const oldValue = td.dataset.oldValue || '';
      const newValue = (td.textContent || '').trim();
      if (oldValue === newValue) return;
      logUploadEdit({
        upload_id: stagedUploads[idx].upload_id,
        original_filename: stagedUploads[idx].original_filename || '',
        field,
        old_value: oldValue,
        new_value: newValue
      });
    });

    tbody.addEventListener('change', (e) => {
      const cb = e.target.closest('.row-select');
      if (!cb) return;
      const tr = e.target.closest('tr[data-idx]');
      if (!tr) return;
      const idx = parseInt(tr.getAttribute('data-idx') || '-1', 10);
      if (idx < 0 || idx >= stagedUploads.length) return;
      stagedUploads[idx]._selected = !!cb.checked;
    });

    tableHead.addEventListener('click', (e) => {
      const th = e.target.closest('th[data-sort]');
      if (!th) return;
      const key = th.getAttribute('data-sort');
      if (!key) return;
      pushSortRule(sortStack, key);
      renderStagedTable();
    });

    tableHead.addEventListener('input', (e) => {
      const inp = e.target.closest('input[data-filter]');
      if (!inp) return;
      const key = inp.getAttribute('data-filter');
      if (!key) return;
      filterState[key] = inp.value || '';
      if (String(inp.value || '').trim() !== '') {
        const idx = sortStack.findIndex(x => x.key === key);
        if (idx > 0) {
          const existing = sortStack.splice(idx, 1)[0];
          sortStack.unshift(existing);
        } else if (idx < 0) {
          sortStack.unshift({ key, dir: 1 });
        }
      }
      renderStagedTable();
    });

    if (selectAllFiltered) {
      selectAllFiltered.addEventListener('change', () => {
        const rows = getFilteredSortedRows();
        rows.forEach(({ idx }) => {
          if (idx >= 0 && idx < stagedUploads.length) stagedUploads[idx]._selected = !!selectAllFiltered.checked;
        });
        renderStagedTable();
      });
    }

    // Tekli kaydetme kaldırıldı; satırlar toplu aktarım için düzenlenir.

    const resetUploadScreenState = () => {
      selected = [];
      if (picker) picker.value = '';
      tbody.innerHTML = '';
      transferBody.innerHTML = '';
      table.style.display = 'none';
      transferTable.style.display = 'none';
      stagedUploads = [];
      transferRowsCache = [];
      summary.textContent = 'Alan temizlendi.';
    };

    listTransfersBtn.addEventListener('click', async () => {
      if (!token) { summary.textContent = 'Oturum bulunamadi.'; window.location.href = '/'; return; }
      if (!stagedUploads.length) { summary.textContent = 'Önce dosya yükleyin.'; return; }
      try {
        showLoading('İçeri aktarım yapılıyor...');
        summary.textContent = 'İçeri aktarım yapılıyor...';
        if (!me || !me.active_project_id) {
          const ok = await ensureActiveProject();
          if (!ok) return;
        }
        await fetchProjectTransfers();
        let updated = 0;
        let skipped = 0;
        const queue = [...stagedUploads];
        for (let i = 0; i < queue.length; i += 1) {
          const current = queue[i];
          const idx = stagedUploads.findIndex(x => String(x.upload_id || '') === String(current.upload_id || ''));
          if (idx < 0) continue;
          const result = await saveStagedRow(idx);
          if (result.ok) {
            stagedUploads.splice(idx, 1);
            updated += 1;
          } else {
            skipped += 1;
          }
        }
        renderStagedTable();
        summary.textContent = `İçeri aktarıldı. Kaydedilen: ${updated}, Atlanan/Uyarı: ${skipped}.`;
        if (updated > 0) {
          if (!stagedUploads.length) resetUploadScreenState();
          await fetchProjectTransfers();
          renderTransferListTable();
        }
      } catch (err) {
        summary.textContent = `Hata: ${err.message}`;
      }
      finally { hideLoading(); }
    });

    transferSelectedBtn.addEventListener('click', async () => {
      if (!token) { summary.textContent = 'Oturum bulunamadi.'; window.location.href = '/'; return; }
      const selectedIdx = stagedUploads.map((r, i) => (r._selected ? i : -1)).filter(i => i >= 0);
      if (!selectedIdx.length) { summary.textContent = 'Önce satır seçin.'; return; }
      try {
        showLoading('Seçilenler aktarılıyor...');
        summary.textContent = 'Seçilenler aktarılıyor...';
        if (!me || !me.active_project_id) {
          const ok = await ensureActiveProject();
          if (!ok) return;
        }
        await fetchProjectTransfers();
        let updated = 0, skipped = 0;
        const desc = [...selectedIdx].sort((a, b) => b - a);
        for (const idx of desc) {
          if (idx < 0 || idx >= stagedUploads.length) continue;
          const result = await saveStagedRow(idx);
          if (result.ok) {
            stagedUploads.splice(idx, 1);
            updated += 1;
          } else {
            skipped += 1;
          }
        }
        renderStagedTable();
        summary.textContent = `Seçilenler aktarıldı. Kaydedilen: ${updated}, Atlanan/Uyarı: ${skipped}.`;
        if (updated > 0) {
          await fetchProjectTransfers();
          renderTransferListTable();
        }
      } catch (err) {
        summary.textContent = `Hata: ${err.message}`;
      } finally {
        hideLoading();
      }
    });

    refreshTransferListBtn.addEventListener('click', async () => {
      try {
        showLoading('Transfer listesi yenileniyor...');
        if (!me || !me.active_project_id) {
          const ok = await ensureActiveProject();
          if (!ok) return;
        }
        await fetchProjectTransfers();
        renderTransferListTable();
        summary.textContent = `${transferRowsCache.length} transfer listelendi.`;
      } catch (err) {
        summary.textContent = `Hata: ${err.message}`;
      } finally {
        hideLoading();
      }
    });

    transferHead.addEventListener('click', (e) => {
      const th = e.target.closest('th[data-tsort]');
      if (!th) return;
      const key = th.getAttribute('data-tsort');
      if (!key) return;
      pushSortRule(transferSortStack, key);
      renderTransferListTable();
    });

    transferHead.addEventListener('input', (e) => {
      const inp = e.target.closest('input[data-tfilter]');
      if (!inp) return;
      const key = inp.getAttribute('data-tfilter');
      if (!key) return;
      transferFilterState[key] = inp.value || '';
      if (String(inp.value || '').trim() !== '') {
        const idx = transferSortStack.findIndex(x => x.key === key);
        if (idx > 0) {
          const existing = transferSortStack.splice(idx, 1)[0];
          transferSortStack.unshift(existing);
        } else if (idx < 0) {
          transferSortStack.unshift({ key, dir: 1 });
        }
      }
      renderTransferListTable();
    });

    refreshPopupAction.addEventListener('click', async () => {
      hideRefreshPopup();
      try {
        showLoading('Liste güncelleniyor...');
        if (!me || !me.active_project_id) {
          const ok = await ensureActiveProject();
          if (!ok) return;
        }
        await fetchProjectTransfers();
        const byUpload = {};
        transferRowsCache.forEach(t => {
          if (t.upload_id != null && !byUpload[String(t.upload_id)]) byUpload[String(t.upload_id)] = t;
        });
        stagedUploads = stagedUploads.map(s => {
          const t = byUpload[String(s.upload_id || '')];
          return {
            ...s,
            _selected: !!s._selected,
            status: t ? 'hazır' : (s.status || ''),
            passenger_name: s.passenger_name || (t?.passenger_name || ''),
            pnr: s.pnr || (t?.pnr || ''),
            issue_date: s.issue_date || (t?.duzenlenme_tarihi || ''),
            ucus_sekli: t?.ucus_sekli || '',
            flight_no: t?.flight_no || '',
            from_to: t?.from_to || '',
            kalkis_tarihi_saati: t?.kalkis_tarihi_saati || '',
            inis_tarihi_saati: t?.inis_tarihi_saati || '',
            pickup_time: s.pickup_time || (t?.pickup_time || ''),
            transfer_point: s.transfer_point || (t?.transfer_noktasi || ''),
            vehicle_code: s.vehicle_code || (t?.arac_kod || ''),
          };
        });
        renderStagedTable();
        summary.textContent = "Liste yenilendi. Satır bazında Kaydet ile Transfer Listesi'ne gönderebilirsiniz.";
      } catch (err) {
        summary.textContent = `Hata: ${err.message}`;
      } finally {
        hideLoading();
      }
    });
    refreshPopupClose.addEventListener('click', hideRefreshPopup);

    exportZipBtn.addEventListener('click', async () => {
      if (!token) { summary.textContent = 'Oturum bulunamadi.'; window.location.href = '/'; return; }
      summary.textContent = 'ZIP hazirlaniyor...';
      try {
        const res = await fetch('/exports/zip', { method:'POST', headers:{...authHeaders(),'Content-Type':'application/json'}, body: JSON.stringify({ only_processed: true }) });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || 'ZIP export başarısız');
        }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'bilet_export.zip';
        document.body.appendChild(a); a.click(); a.remove();
        window.URL.revokeObjectURL(url);
        summary.textContent = 'ZIP indirildi.';
      } catch (err) { summary.textContent = `Hata: ${err.message}`; }
    });
    ensureActiveProject().then(async () => {
      try {
        await fetchProjectTransfers();
        renderTransferListTable();
      } catch (_) {}
    }).catch((err) => { summary.textContent = `Hata: ${err.message}`; });
  </script>
</body>
</html>
"""


@app.get("/yonetici-ui", response_class=HTMLResponse)
def yonetici_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Yönetici Modülü</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .head { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; position:relative; }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn { background: rgba(255,255,255,0.18); color:#fff; text-decoration:none; border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px; }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .head-right { display:flex; flex-direction:row; align-items:center; gap:8px; margin-right:68px; }
    .admin-menu { position:relative; }
    .admin-btn { display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF; border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600; text-decoration:none; cursor:pointer; white-space:nowrap; }
    .admin-menu .links { display:none; position:absolute; top:100%; margin-top:2px; right:0; min-width:150px; background:#0A1024; border:1px solid rgba(159,216,255,0.35); border-radius:8px; padding:6px; z-index:50; }
    .admin-menu .links a { display:block; margin:0; padding:5px 6px; color:#9FD8FF; border-radius:6px; text-decoration:none; }
    .admin-menu .links a:hover { background:rgba(159,216,255,0.12); }
    .admin-menu:hover .links, .admin-menu:focus-within .links, .admin-menu.open .links { display:block; }
    .right-panel { border:1px solid rgba(159,216,255,0.45); border-radius:8px; padding:4px 7px; background:rgba(8,23,56,0.20); }
    .project-badge { display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF; border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .grid { margin-top:10px; }
    .section-title { margin:16px 0 8px; font-weight:700; color:#0f2242; }
    .rules { border:1px solid #dde4ef; border-radius:10px; overflow:hidden; }
    .rule-row { display:grid; grid-template-columns: 1fr auto; gap:10px; align-items:center; padding:9px 10px; border-bottom:1px solid #edf2fa; }
    .rules .rule-row:nth-child(even) { background: rgba(159, 216, 255, 0.22); }
    .rule-row:last-child { border-bottom:0; }
    .rule-row label { font-size:13px; color:#22324d; }
    .rule-row select, .rule-row input { border:1px solid #cfd9e8; border-radius:7px; padding:6px 8px; font-size:12px; }
    .minute-select { min-width:96px; width:96px; justify-self:end; }
    .cap-input { width:96px; justify-self:end; }
    .time-wrap { display:flex; align-items:center; gap:4px; }
    .time-wrap select { width:31px; text-align:center; }
    .rule-row.daily-row .time-wrap { justify-self:end; }
    .actions { margin-top:10px; display:flex; gap:8px; }
    .btn { border:0; border-radius:8px; padding:8px 12px; cursor:pointer; color:#fff; background:#2b7fff; }
    .btn.alt { background:#5c6b82; }
    .note { margin-top:8px; color:#5c6b82; font-size:12px; }
    .fx-box { margin-top:14px; border:1px solid #dde4ef; border-radius:10px; padding:10px; }
    .fx-grid { display:grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap:8px; margin-top:8px; }
    .fx-grid input, .fx-grid select { border:1px solid #cfd9e8; border-radius:7px; padding:6px 8px; font-size:12px; width:100%; box-sizing:border-box; }
    .fx-row { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; align-items:center; }
    .fx-table { width:100%; border-collapse:collapse; margin-top:8px; font-size:12px; }
    .fx-table th, .fx-table td { border:1px solid #dde4ef; padding:6px; text-align:left; }
    .fx-table th { background:#f0f5ff; }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn" href="/kayit-ui" accesskey="2" title="Kısayol: Alt+2">Kayıt Modülü</a>
        <a class="m-btn" href="/konaklama-ui" accesskey="3" title="Kısayol: Alt+3">Konaklama Modülü</a>
        <a class="m-btn" href="/toplanti-ui" accesskey="4" title="Kısayol: Alt+4">Toplantı Modülü</a>
        <a class="m-btn" href="/transfer-ui" accesskey="1" title="Kısayol: Alt+1">Ulaşım Modülü</a>
        <a class="m-btn" href="/muhasebe-finans-ui" accesskey="5" title="Kısayol: Alt+5">Muhasebe - Finans Modülü</a>
        <a class="m-btn" href="/duyurular-ui" accesskey="6" title="Kısayol: Alt+6">Duyurular</a>
      </div>
      <div class="head-right">
        <div class="admin-menu">
          <a class="admin-btn active" href="/yonetici-ui">Yönetici Modülü</a>
          <div class="links">
            <a href="/reports-ui">Raporlar</a>
            <a href="/duyurular-ui">Duyurular</a>
            <a href="/projects-ui">Projeler</a>
            <a href="/users-ui">Kullanıcılar</a>
            <a href="/admin-db-ui">Veritabanı</a>
            <a href="/urunler-ui">Ürünler</a>
          </div>
        </div>
        <div class="right-panel"><span id="activeProjectBadge" class="project-badge">AKTİF PROJE: -</span></div>
      </div>
    </div>
    <div class="box">
      <h3 style="margin:0;">Yönetici Modülü</h3>
      <div class="tabs" id="adminTabs">
        <button class="tab" type="button" data-go="/reports-ui">Raporlar</button>
        <button class="tab alt" type="button" data-go="/duyurular-ui">Duyurular</button>
        <button class="tab alt" type="button" data-go="/projects-ui">Projeler</button>
        <button class="tab alt" type="button" data-go="/users-ui">Kullanıcılar</button>
        <button class="tab alt" type="button" data-go="/admin-db-ui">Veritabanı</button>
        <button class="tab alt" type="button" data-go="/urunler-ui">Ürünler</button>
      </div>
      <div class="section-title">Raporlama Uyarı Parametreleri</div>
      <div class="rules" id="rulesWrap">
        <div class="rule-row"><label>Havalimanı - Otel1 arası kaç dakika</label><select class="minute-select" data-key="airport_hotel1"></select></div>
        <div class="rule-row"><label>Havalimanı - Otel2 arası kaç dakika</label><select class="minute-select" data-key="airport_hotel2"></select></div>
        <div class="rule-row"><label>Havalimanı - Otel3 arası kaç dakika</label><select class="minute-select" data-key="airport_hotel3"></select></div>
        <div class="rule-row"><label>Havalimanı - Otel4 arası kaç dakika</label><select class="minute-select" data-key="airport_hotel4"></select></div>
        <div class="rule-row"><label>Havalimanı - Kongre Merkezi kaç dakika</label><select class="minute-select" data-key="airport_congress"></select></div>
        <div class="rule-row"><label>Otel1'den Havalimanına en az kaç dakika önce yola çıkmalı</label><select class="minute-select" data-key="hotel1_airport_min"></select></div>
        <div class="rule-row"><label>Otel2'den Havalimanına en az kaç dakika önce yola çıkmalı</label><select class="minute-select" data-key="hotel2_airport_min"></select></div>
        <div class="rule-row"><label>Otel3'den Havalimanına en az kaç dakika önce yola çıkmalı</label><select class="minute-select" data-key="hotel3_airport_min"></select></div>
        <div class="rule-row"><label>Otel4'den Havalimanına en az kaç dakika önce yola çıkmalı</label><select class="minute-select" data-key="hotel4_airport_min"></select></div>
        <div class="rule-row"><label>Kongre Merkezi'nden Havalimanına en az kaç dakika önce yola çıkmalı</label><select class="minute-select" data-key="congress_airport_min"></select></div>
        <div class="rule-row"><label>Otel1'den Havalimanına en fazla kaç dakika önce yola çıkmalı</label><select class="minute-select" data-key="hotel1_airport_max"></select></div>
        <div class="rule-row"><label>Otel2'den Havalimanına en fazla kaç dakika önce yola çıkmalı</label><select class="minute-select" data-key="hotel2_airport_max"></select></div>
        <div class="rule-row"><label>Otel3'den Havalimanına en fazla kaç dakika önce yola çıkmalı</label><select class="minute-select" data-key="hotel3_airport_max"></select></div>
        <div class="rule-row"><label>Otel4'den Havalimanına en fazla kaç dakika önce yola çıkmalı</label><select class="minute-select" data-key="hotel4_airport_max"></select></div>
        <div class="rule-row"><label>Kongre Merkezi'nden Havalimanına en fazla kaç dakika önce yola çıkmalı</label><select class="minute-select" data-key="congress_airport_max"></select></div>

        <div class="rule-row daily-row">
          <label>Daily House Başlangıç saati</label>
          <div class="time-wrap" data-time-key="daily_house_start">
            <select data-part="h1"></select><select data-part="h2"></select><span>:</span><select data-part="m1"></select><select data-part="m2"></select>
          </div>
        </div>
        <div class="rule-row daily-row">
          <label>Daily House Bitiş saati</label>
          <div class="time-wrap" data-time-key="daily_house_end">
            <select data-part="h1"></select><select data-part="h2"></select><span>:</span><select data-part="m1"></select><select data-part="m2"></select>
          </div>
        </div>

        <div class="rule-row"><label>Vito araç kaç kişi binebilir</label><input class="cap-input" type="number" min="1" max="99" step="1" data-key="cap_vito" value="6" /></div>
        <div class="rule-row"><label>Mini araç kaç kişi binebilir</label><input class="cap-input" type="number" min="1" max="99" step="1" data-key="cap_mini" value="4" /></div>
        <div class="rule-row"><label>Midi araç kaç kişi binebilir</label><input class="cap-input" type="number" min="1" max="99" step="1" data-key="cap_midi" value="16" /></div>
        <div class="rule-row"><label>Bus araç kaç kişi binebilir</label><input class="cap-input" type="number" min="1" max="99" step="1" data-key="cap_bus" value="46" /></div>
      </div>
      <div class="actions">
        <button id="saveRulesBtn" class="btn" type="button">Ayarları Kaydet</button>
        <button id="resetRulesBtn" class="btn alt" type="button">Sıfırla</button>
      </div>
      <div id="rulesNote" class="note"></div>

      <div class="section-title">Veritabanı - Kur Yönetimi</div>
      <div class="fx-box">
        <div class="fx-row">
          <label>Kur Modu</label>
          <select id="fxMode">
            <option value="fixed">Sabit Kur</option>
            <option value="daily">Merkez Bankası Günlük Kur</option>
            <option value="event_daily">Kongre Kur Gününe Göre</option>
          </select>
          <label>Kongre Kur Günü</label>
          <input id="fxEventDate" type="date" />
        </div>
        <div class="fx-grid">
          <div><label>TL</label><input id="fxTl" type="number" step="0.0001" value="1" /></div>
          <div><label>USD</label><input id="fxUsd" type="number" step="0.0001" placeholder="Örn: 36.25" /></div>
          <div><label>EUR</label><input id="fxEur" type="number" step="0.0001" placeholder="Örn: 39.40" /></div>
          <div><label>GBP</label><input id="fxGbp" type="number" step="0.0001" placeholder="Örn: 46.10" /></div>
        </div>
        <div class="fx-row">
          <strong>Günlük Kur Satırı Ekle</strong>
          <input id="fxDailyDate" type="date" />
          <input id="fxDailyUsd" type="number" step="0.0001" placeholder="USD" />
          <input id="fxDailyEur" type="number" step="0.0001" placeholder="EUR" />
          <input id="fxDailyGbp" type="number" step="0.0001" placeholder="GBP" />
          <button id="fxAddDailyBtn" class="btn alt" type="button">Gün Ekle/Güncelle</button>
          <button id="fxFetchTcmbBtn" class="btn alt" type="button">TCMB'den Güncelle</button>
        </div>
        <table class="fx-table">
          <thead><tr><th>TARİH</th><th>USD</th><th>EUR</th><th>GBP</th><th>İŞLEM</th></tr></thead>
          <tbody id="fxDailyRows"></tbody>
        </table>
        <div class="actions">
          <button id="fxSaveBtn" class="btn" type="button">Kur Ayarlarını Kaydet</button>
          <button id="fxResetBtn" class="btn alt" type="button">Kur Ayarlarını Sıfırla</button>
        </div>
        <div id="fxNote" class="note"></div>
      </div>
    </div>
  </div>
  <script>
    (function(){
      const token = localStorage.getItem('access_token') || '';
      const badge = document.getElementById('activeProjectBadge');
      const note = document.getElementById('rulesNote');
      const fxNote = document.getElementById('fxNote');
      const saveBtn = document.getElementById('saveRulesBtn');
      const resetBtn = document.getElementById('resetRulesBtn');
      const fxMode = document.getElementById('fxMode');
      const fxEventDate = document.getElementById('fxEventDate');
      const fxTl = document.getElementById('fxTl');
      const fxUsd = document.getElementById('fxUsd');
      const fxEur = document.getElementById('fxEur');
      const fxGbp = document.getElementById('fxGbp');
      const fxDailyDate = document.getElementById('fxDailyDate');
      const fxDailyUsd = document.getElementById('fxDailyUsd');
      const fxDailyEur = document.getElementById('fxDailyEur');
      const fxDailyGbp = document.getElementById('fxDailyGbp');
      const fxAddDailyBtn = document.getElementById('fxAddDailyBtn');
      const fxFetchTcmbBtn = document.getElementById('fxFetchTcmbBtn');
      const fxDailyRows = document.getElementById('fxDailyRows');
      const fxSaveBtn = document.getElementById('fxSaveBtn');
      const fxResetBtn = document.getElementById('fxResetBtn');
      let projectKey = 'global';

      const minutes = [];
      for (let i = 5; i <= 120; i += 5) minutes.push(i);
      document.querySelectorAll('.minute-select').forEach((s) => {
        s.innerHTML = `<option value=""></option>` + minutes.map((m) => `<option value="${m}">${m} dk</option>`).join('');
      });

      const digits = (from, to) => {
        const out = [];
        for (let i = from; i <= to; i++) out.push(String(i));
        return out;
      };
      const opts = (arr, includeBlank=false) => (includeBlank ? [''] : []).concat(arr).map((x) => {
        if (x === '') return `<option value=""></option>`;
        return `<option value="${x}">${x}</option>`;
      }).join('');
      document.querySelectorAll('.time-wrap').forEach((w) => {
        w.querySelector('[data-part="h1"]').innerHTML = opts(['0','1','2'], true);
        w.querySelector('[data-part="m1"]').innerHTML = opts(['0','1','2','3','4','5'], true);
        w.querySelector('[data-part="m2"]').innerHTML = opts(digits(0,9), true);
      });
      const syncHourOnes = (wrap) => {
        const h1 = wrap.querySelector('[data-part="h1"]');
        const h2 = wrap.querySelector('[data-part="h2"]');
        const max = h1.value === '2' ? 3 : 9;
        const current = h2.value;
        h2.innerHTML = opts(digits(0, max), true);
        if (current && parseInt(current, 10) <= max) h2.value = current;
      };
      document.querySelectorAll('.time-wrap').forEach((w) => {
        syncHourOnes(w);
        w.querySelector('[data-part="h1"]').addEventListener('change', () => syncHourOnes(w));
      });

      const timeGet = (wrap) => {
        const h1 = wrap.querySelector('[data-part="h1"]').value || '';
        const h2 = wrap.querySelector('[data-part="h2"]').value || '';
        const m1 = wrap.querySelector('[data-part="m1"]').value || '';
        const m2 = wrap.querySelector('[data-part="m2"]').value || '';
        if (!(h1 && h2 && m1 && m2)) return '';
        return `${h1}${h2}:${m1}${m2}`;
      };
      const timeSet = (wrap, value) => {
        const raw = String(value || '');
        if (!raw) {
          wrap.querySelector('[data-part="h1"]').value = '';
          syncHourOnes(wrap);
          wrap.querySelector('[data-part="h2"]').value = '';
          wrap.querySelector('[data-part="m1"]').value = '';
          wrap.querySelector('[data-part="m2"]').value = '';
          return;
        }
        const v = /^([0-2][0-9]):([0-5][0-9])$/.test(raw) ? raw : '';
        if (!v) {
          wrap.querySelector('[data-part="h1"]').value = '';
          syncHourOnes(wrap);
          wrap.querySelector('[data-part="h2"]').value = '';
          wrap.querySelector('[data-part="m1"]').value = '';
          wrap.querySelector('[data-part="m2"]').value = '';
          return;
        }
        wrap.querySelector('[data-part="h1"]').value = v[0];
        syncHourOnes(wrap);
        wrap.querySelector('[data-part="h2"]').value = v[1];
        wrap.querySelector('[data-part="m1"]').value = v[3];
        wrap.querySelector('[data-part="m2"]').value = v[4];
      };

      const storageKey = () => `reporting_rules_${projectKey}`;
      const fxStorageKey = () => `fx_settings_${projectKey}`;
      const collect = () => {
        const out = {};
        document.querySelectorAll('[data-key]').forEach((el) => { out[el.dataset.key] = el.value; });
        document.querySelectorAll('.time-wrap[data-time-key]').forEach((w) => { out[w.dataset.timeKey] = timeGet(w); });
        return out;
      };
      const apply = (obj) => {
        document.querySelectorAll('[data-key]').forEach((el) => {
          if (obj[el.dataset.key] != null) el.value = String(obj[el.dataset.key]);
        });
        document.querySelectorAll('.time-wrap[data-time-key]').forEach((w) => timeSet(w, obj[w.dataset.timeKey] || ''));
      };
      const load = () => {
        const raw = localStorage.getItem(storageKey());
        if (!raw) return;
        try { apply(JSON.parse(raw)); } catch (_) {}
      };
      const save = () => {
        localStorage.setItem(storageKey(), JSON.stringify(collect()));
        note.textContent = 'Ayarlar kaydedildi.';
      };
      const reset = () => {
        localStorage.removeItem(storageKey());
        location.reload();
      };

      const fxDefault = () => ({
        mode: 'fixed',
        event_date: '',
        fixed: { TL: '1', USD: '', EUR: '', GBP: '' },
        daily: {}
      });
      const fxNum = (v) => {
        const n = parseFloat(String(v || '').replace(',', '.'));
        return Number.isFinite(n) ? String(n) : '';
      };
      const fxRead = () => {
        const raw = localStorage.getItem(fxStorageKey());
        if (!raw) return fxDefault();
        try {
          const obj = JSON.parse(raw);
          if (!obj || typeof obj !== 'object') return fxDefault();
          return {
            mode: obj.mode || 'fixed',
            event_date: obj.event_date || '',
            fixed: {
              TL: (obj.fixed && obj.fixed.TL) || '1',
              USD: (obj.fixed && obj.fixed.USD) || '',
              EUR: (obj.fixed && obj.fixed.EUR) || '',
              GBP: (obj.fixed && obj.fixed.GBP) || ''
            },
            daily: (obj.daily && typeof obj.daily === 'object') ? obj.daily : {}
          };
        } catch (_) {
          return fxDefault();
        }
      };
      const fxWrite = (cfg) => {
        localStorage.setItem(fxStorageKey(), JSON.stringify(cfg));
      };
      const fxRenderDaily = (cfg) => {
        if (!fxDailyRows) return;
        const days = Object.keys(cfg.daily || {}).sort().reverse();
        if (!days.length) {
          fxDailyRows.innerHTML = '<tr><td colspan="5" class="muted">Günlük kur kaydı yok.</td></tr>';
          return;
        }
        fxDailyRows.innerHTML = days.map((d) => {
          const r = cfg.daily[d] || {};
          return '<tr>'
            + '<td>' + d + '</td>'
            + '<td>' + (r.USD || '') + '</td>'
            + '<td>' + (r.EUR || '') + '</td>'
            + '<td>' + (r.GBP || '') + '</td>'
            + '<td><button type="button" class="btn alt" data-fx-del="' + d + '">Sil</button></td>'
            + '</tr>';
        }).join('');
      };
      const fxApply = (cfg) => {
        if (fxMode) fxMode.value = cfg.mode || 'fixed';
        if (fxEventDate) fxEventDate.value = cfg.event_date || '';
        if (fxTl) fxTl.value = cfg.fixed.TL || '1';
        if (fxUsd) fxUsd.value = cfg.fixed.USD || '';
        if (fxEur) fxEur.value = cfg.fixed.EUR || '';
        if (fxGbp) fxGbp.value = cfg.fixed.GBP || '';
        fxRenderDaily(cfg);
      };
      const fxCollect = (base) => {
        const cfg = base || fxDefault();
        cfg.mode = fxMode ? fxMode.value : 'fixed';
        cfg.event_date = fxEventDate ? (fxEventDate.value || '') : '';
        cfg.fixed = {
          TL: fxNum(fxTl ? fxTl.value : '1') || '1',
          USD: fxNum(fxUsd ? fxUsd.value : ''),
          EUR: fxNum(fxEur ? fxEur.value : ''),
          GBP: fxNum(fxGbp ? fxGbp.value : '')
        };
        return cfg;
      };

      saveBtn.addEventListener('click', save);
      resetBtn.addEventListener('click', reset);
      if (fxAddDailyBtn) {
        fxAddDailyBtn.addEventListener('click', () => {
          const cfg = fxCollect(fxRead());
          const d = fxDailyDate ? (fxDailyDate.value || '') : '';
          if (!d) { if (fxNote) fxNote.textContent = 'Tarih seçiniz.'; return; }
          cfg.daily[d] = {
            USD: fxNum(fxDailyUsd ? fxDailyUsd.value : ''),
            EUR: fxNum(fxDailyEur ? fxDailyEur.value : ''),
            GBP: fxNum(fxDailyGbp ? fxDailyGbp.value : '')
          };
          fxWrite(cfg);
          fxApply(cfg);
          if (fxNote) fxNote.textContent = 'Günlük kur satırı kaydedildi.';
        });
      }
      if (fxFetchTcmbBtn) {
        fxFetchTcmbBtn.addEventListener('click', async () => {
          try {
            const d = (fxDailyDate && fxDailyDate.value) ? fxDailyDate.value : '';
            const url = d ? ('/fx/tcmb-rates?date=' + encodeURIComponent(d)) : '/fx/tcmb-rates';
            const res = await fetch(url, { headers: token ? ({ Authorization: `Bearer ${token}` }) : ({}) });
            const out = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(out.detail || 'TCMB kuru alınamadı');
            const rates = out.rates || {};
            const rateDate = out.date || d || '';
            if (!rateDate) throw new Error('TCMB tarih bilgisi alınamadı');
            if (fxDailyDate) fxDailyDate.value = rateDate;
            if (fxDailyUsd) fxDailyUsd.value = rates.USD != null ? String(rates.USD) : '';
            if (fxDailyEur) fxDailyEur.value = rates.EUR != null ? String(rates.EUR) : '';
            if (fxDailyGbp) fxDailyGbp.value = rates.GBP != null ? String(rates.GBP) : '';

            const cfg = fxCollect(fxRead());
            cfg.daily[rateDate] = {
              USD: rates.USD != null ? String(rates.USD) : '',
              EUR: rates.EUR != null ? String(rates.EUR) : '',
              GBP: rates.GBP != null ? String(rates.GBP) : ''
            };
            fxWrite(cfg);
            fxApply(cfg);
            if (fxNote) fxNote.textContent = 'TCMB kuru çekildi ve günlük kura işlendi.';
          } catch (err) {
            if (fxNote) fxNote.textContent = 'Hata: ' + (err && err.message ? err.message : 'TCMB kuru alınamadı');
          }
        });
      }
      if (fxDailyRows) {
        fxDailyRows.addEventListener('click', (e) => {
          const t = e.target;
          if (!t || t.dataset.fxDel == null) return;
          const d = t.dataset.fxDel;
          const cfg = fxRead();
          if (cfg.daily && cfg.daily[d]) delete cfg.daily[d];
          fxWrite(cfg);
          fxApply(cfg);
          if (fxNote) fxNote.textContent = 'Günlük kur satırı silindi.';
        });
      }
      if (fxSaveBtn) {
        fxSaveBtn.addEventListener('click', () => {
          const cfg = fxCollect(fxRead());
          fxWrite(cfg);
          fxApply(cfg);
          if (fxNote) fxNote.textContent = 'Kur ayarları kaydedildi.';
        });
      }
      if (fxResetBtn) {
        fxResetBtn.addEventListener('click', () => {
          const cfg = fxDefault();
          fxWrite(cfg);
          fxApply(cfg);
          if (fxNote) fxNote.textContent = 'Kur ayarları sıfırlandı.';
        });
      }

      (async function initProject(){
        if (!token) return;
        try {
          const res = await fetch('/auth/me', { headers: { Authorization: `Bearer ${token}` } });
          const me = await res.json();
          if (!res.ok || !me) return;
          if (badge) {
            const pName = me.active_project_name || '-';
            const pCode = me.active_project_code || (me.active_project_id ? ('ID-' + me.active_project_id) : '-');
            badge.textContent = `AKTİF PROJE: ${pName} (${pCode})`;
          }
          projectKey = String(me.active_project_id || 'global');
        } catch (_) {}
        load();
        fxApply(fxRead());
      })();

      const adminTabs = Array.from(document.querySelectorAll('#adminTabs .tab'));
      adminTabs.forEach((btn) => {
        btn.addEventListener('click', () => {
          adminTabs.forEach((x) => { x.classList.add('alt'); });
          btn.classList.remove('alt');
          const go = btn.getAttribute('data-go');
          if (go) window.location.href = go;
        });
      });
    })();
  </script>
  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""


@app.get("/admin-db-ui", response_class=HTMLResponse)
def admin_db_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Veritabanı Ekranı</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { max-width: 1280px; margin: 0 auto; padding: 16px; }
    .head { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn { background: rgba(255,255,255,0.18); color:#fff; text-decoration:none; border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px; }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .panel { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:14px; margin-bottom:12px; }
    .title { margin:0 0 8px 0; font-size:16px; font-weight:700; }
    .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:8px; }
    select, input { border:1px solid #cfd9e8; border-radius:8px; padding:7px 9px; font-size:12px; }
    button { background:#2b7fff; color:#fff; border:0; border-radius:8px; padding:8px 12px; cursor:pointer; }
    button.alt { background:#5c6b82; }
    .muted { color:#5c6b82; font-size:12px; }
    .tbl-wrap { overflow:auto; max-height:48vh; border:1px solid #dde4ef; border-radius:10px; }
    table { width:100%; border-collapse:collapse; font-size:12px; }
    th, td { border:1px solid #dde4ef; padding:7px; text-align:left; white-space:nowrap; }
    th { background:#f0f5ff; position:sticky; top:0; }
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn" href="/yonetici-ui">Yönetici Modülü</a>
        <a class="m-btn active" href="/admin-db-ui">Veritabanı</a>
      </div>
    </div>

    <div class="panel">
      <h3 class="title">Genel Veritabanı</h3>
      <div class="row">
        <select id="generalTable"></select>
        <button id="generalLoad" type="button">Yükle</button>
        <span id="generalInfo" class="muted"></span>
      </div>
      <div class="tbl-wrap"><table id="generalTbl"><thead></thead><tbody></tbody></table></div>
    </div>

    <div class="panel">
      <h3 class="title">Proje Veritabanı</h3>
      <div class="row">
        <select id="projectFilter"></select>
        <select id="projectTable"></select>
        <button id="projectLoad" type="button">Yükle</button>
        <span id="projectInfo" class="muted"></span>
      </div>
      <div class="tbl-wrap"><table id="projectTbl"><thead></thead><tbody></tbody></table></div>
    </div>
  </div>
  <script>
    (function(){
      const authBar = document.createElement('div');
      authBar.className = 'panel';
      authBar.style.marginTop = '0';
      authBar.innerHTML = '<div class="row"><input id="dbUser" placeholder="Superadmin kullanıcı adı" /><input id="dbPass" type="password" placeholder="Şifre" /><button id="dbLoginBtn" type="button">Giriş Yap</button><button id="dbLogoutBtn" class="alt" type="button">Çıkış</button><span id="dbAuthInfo" class="muted"></span></div>';
      document.querySelector('.wrap').insertBefore(authBar, document.querySelector('.panel'));

      const dbUser = document.getElementById('dbUser');
      const dbPass = document.getElementById('dbPass');
      const dbLoginBtn = document.getElementById('dbLoginBtn');
      const dbLogoutBtn = document.getElementById('dbLogoutBtn');
      const dbAuthInfo = document.getElementById('dbAuthInfo');
      const loginOnEnter = (e) => { if (e.key === 'Enter') { e.preventDefault(); dbLoginBtn.click(); } };
      dbUser.addEventListener('keydown', loginOnEnter);
      dbPass.addEventListener('keydown', loginOnEnter);
      const generalTable = document.getElementById('generalTable');
      const projectTable = document.getElementById('projectTable');
      const projectFilter = document.getElementById('projectFilter');
      const generalInfo = document.getElementById('generalInfo');
      const projectInfo = document.getElementById('projectInfo');
      const generalTbl = document.getElementById('generalTbl');
      const projectTbl = document.getElementById('projectTbl');
      const esc = (v) => String(v == null ? '' : v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

      const renderTable = (tableEl, payload) => {
        const cols = Array.isArray(payload.columns) ? payload.columns : [];
        const rows = Array.isArray(payload.rows) ? payload.rows : [];
        tableEl.querySelector('thead').innerHTML = `<tr>${cols.map(c => `<th>${esc(c)}</th>`).join('')}</tr>`;
        tableEl.querySelector('tbody').innerHTML = rows.map((r) => `<tr>${cols.map(c => `<td>${esc(r[c])}</td>`).join('')}</tr>`).join('');
      };

      const authFetch = async (url, opts) => fetch(url, Object.assign({ credentials: 'include' }, opts || {}));

      const ensureSuperadmin = async () => {
        const res = await authFetch('/admin-db/me');
        const me = await res.json().catch(() => ({}));
        if (!res.ok) return false;
        dbAuthInfo.textContent = `Giriş: ${me.username} (${me.role})`;
        return true;
      };

      const loadTableList = async () => {
        const [gRes, pRes] = await Promise.all([
          authFetch('/admin/db/tables?scope=general'),
          authFetch('/admin/db/tables?scope=project')
        ]);
        const gData = await gRes.json().catch(() => []);
        const pData = await pRes.json().catch(() => []);
        if (!gRes.ok || !pRes.ok) throw new Error('Tablo listeleri alınamadı');
        generalTable.innerHTML = (Array.isArray(gData) ? gData : []).map(t => `<option value="${esc(t.name)}">${esc(t.name)}</option>`).join('');
        projectTable.innerHTML = (Array.isArray(pData) ? pData : []).map(t => `<option value="${esc(t.name)}">${esc(t.name)}</option>`).join('');
      };

      const loadProjects = async () => {
        const res = await authFetch('/admin/db/projects-active');
        const data = await res.json().catch(() => []);
        if (!res.ok) throw new Error('Aktif projeler alınamadı');
        projectFilter.innerHTML = '<option value="">Aktif Proje Seçiniz</option>' + (Array.isArray(data) ? data : []).map(p => `<option value="${p.id}">${esc(p.operation_code)} | ${esc(p.name)} | ${esc(p.city)}</option>`).join('');
      };

      const loadGeneral = async () => {
        const t = generalTable.value;
        if (!t) return;
        const res = await authFetch(`/admin/db/table/${encodeURIComponent(t)}?limit=200`);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || 'Tablo okunamadı');
        renderTable(generalTbl, data);
        generalInfo.textContent = `${data.table}: ${data.count} kayıt`;
      };

      const loadProjectScoped = async () => {
        const t = projectTable.value;
        const pid = projectFilter.value;
        if (!t) return;
        const qs = new URLSearchParams({ limit: '200' });
        if (pid) qs.set('project_id', pid);
        const res = await authFetch(`/admin/db/table/${encodeURIComponent(t)}?` + qs.toString());
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || 'Tablo okunamadı');
        renderTable(projectTbl, data);
        projectInfo.textContent = `${data.table}: ${data.count} kayıt`;
      };

      document.getElementById('generalLoad').addEventListener('click', async () => { try { await loadGeneral(); } catch (e) { generalInfo.textContent = 'Hata: ' + e.message; } });
      document.getElementById('projectLoad').addEventListener('click', async () => { try { await loadProjectScoped(); } catch (e) { projectInfo.textContent = 'Hata: ' + e.message; } });

      dbLoginBtn.addEventListener('click', async () => {
        try {
          const res = await authFetch('/admin-db/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: dbUser.value || '', password: dbPass.value || '' })
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) throw new Error(data.detail || 'Giriş başarısız');
          dbPass.value = '';
          dbAuthInfo.textContent = `Giriş: ${data.username} (${data.role})`;
          await loadTableList();
          await loadProjects();
          await loadGeneral();
          await loadProjectScoped();
        } catch (e) {
          dbAuthInfo.textContent = 'Hata: ' + e.message;
        }
      });
      dbLogoutBtn.addEventListener('click', async () => {
        await authFetch('/admin-db/logout', { method: 'POST' });
        dbAuthInfo.textContent = 'Çıkış yapıldı.';
      });

      (async () => {
        if (!(await ensureSuperadmin())) { dbAuthInfo.textContent = 'Giriş yapınız.'; return; }
        try {
          await loadTableList();
          await loadProjects();
          await loadGeneral();
          await loadProjectScoped();
          setInterval(loadProjects, 15000);
        } catch (e) {
          generalInfo.textContent = 'Hata: ' + e.message;
          projectInfo.textContent = 'Hata: ' + e.message;
        }
      })();
    })();
  </script>
</body>
</html>
"""


@app.get("/projects-ui", response_class=HTMLResponse)
def projects_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Projeler</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .head {
      display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;
      background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; position:relative;
    }
    .head-left { display:flex; align-items:center; gap:12px; }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn {
      background: rgba(255,255,255,0.18); color:#fff; text-decoration:none;
      border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px;
    }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .head-right { display:flex; flex-direction:row; align-items:center; gap:8px; margin-right:68px; }
    .right-panel {
      border:1px solid rgba(159,216,255,0.45);
      border-radius:8px;
      padding:4px 7px;
      background:rgba(8,23,56,0.20);
    }
    .links a { margin-right: 6px; color: #9FD8FF; text-decoration: none; font-size: 11px; font-weight: 600; }
    .admin-menu { position:relative; }
    .admin-btn { display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF; border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600; text-decoration:none; cursor:pointer; white-space:nowrap; }
    .admin-menu .links { display:none; position:absolute; top:100%; margin-top:2px; right:0; min-width:150px; background:#0A1024; border:1px solid rgba(159,216,255,0.35); border-radius:8px; padding:6px; z-index:50; }
    .admin-menu .links a { display:block; margin:0; padding:5px 6px; color:#9FD8FF; border-radius:6px; }
    .admin-menu .links a:hover { background:rgba(159,216,255,0.12); }
    .admin-menu:hover .links, .admin-menu:focus-within .links, .admin-menu.open .links { display:block; }
    .project-badge {
      display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF;
      border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600;
      letter-spacing:0.15px; white-space:nowrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08);
    }
    .lang-mini { position:absolute; top:4px; right:8px; font-size:11px; padding:2px 4px; border-radius:6px; border:0; }
    .box { max-width: 1100px; margin: 0 auto; background: #fff; border: 1px solid #dde4ef; border-radius: 12px; padding: 20px; }
    .top-login { position: static; background: #fff; border: 1px solid #dde4ef; border-radius: 10px; padding: 8px; z-index: 1; }
    html.ui-booting .top-login { visibility: hidden; }
    html.has-token #username,
    html.has-token #password,
    html.has-token #rememberWrap,
    html.has-token #loginBtn { display: none !important; }
    .top-login input { width: 120px; }
    input, select { padding: 8px; }
    button { background: #2b7fff; color: #fff; border: 0; border-radius: 8px; padding: 10px 14px; cursor: pointer; }
    .btn-muted { background: #5c6b82; }
    .row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
    table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 12px; }
    th, td { border: 1px solid #dde4ef; padding: 8px; text-align: left; }
    th { background: #f0f5ff; }
    .switch-wrap { display:inline-flex; align-items:center; gap:8px; }
    .switch {
      position: relative; display: inline-block; width: 46px; height: 24px;
    }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute; cursor: pointer; inset: 0; background: #c62828;
      transition: .2s; border-radius: 999px;
    }
    .slider:before {
      position: absolute; content: ""; height: 18px; width: 18px; left: 3px; top: 3px;
      background: #fff; transition: .2s; border-radius: 50%;
    }
    .switch input:checked + .slider { background: #0a7a2f; }
    .switch input:checked + .slider:before { transform: translateX(22px); }
    .status-chip {
      border-radius: 999px; padding: 2px 8px; font-size: 11px; font-weight: 700;
      border: 1px solid transparent;
    }
    .status-chip.active { color: #0a7a2f; background:#e8f7ee; border-color:#98d9b1; }
    .status-chip.passive { color: #b91c1c; background:#fdecec; border-color:#f4b6b6; }
    .muted { color: #5c6b82; font-size: 13px; margin-top: 8px; }
    .footer-brand { position: fixed; left: 0; right: 0; bottom: 0; height: 54px; background: #0A1024; display: flex; align-items: center; padding-left: 12px; z-index: 998; overflow: hidden; }
    .footer-brand img { height: 150%; width: auto; display: block; object-fit: cover; object-position: center; clip-path: inset(0 3% 0 0); }
    .logo-reg { color: #fff; font-size: 12px; line-height: 1; margin-left: 0; font-weight: 700; position: relative; left: -26px; transform: translateY(-45%); }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
  <script>
    (function(){
      try {
        var root = document.documentElement;
        root.classList.add('ui-booting');
        if (localStorage.getItem('access_token')) root.classList.add('has-token');
      } catch (_) {}
    })();
  </script>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="head-left module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn" href="/kayit-ui" accesskey="2" title="Kısayol: Alt+2">Kayıt Modülü</a>
        <a class="m-btn" href="/konaklama-ui" accesskey="3" title="Kısayol: Alt+3">Konaklama Modülü</a>
        <a class="m-btn" href="/toplanti-ui" accesskey="4" title="Kısayol: Alt+4">Toplantı Modülü</a>
        <a class="m-btn" href="/transfer-ui" accesskey="1" title="Kısayol: Alt+1">Ulaşım Modülü</a>
        <a class="m-btn" href="/muhasebe-finans-ui" accesskey="5" title="Kısayol: Alt+5">Muhasebe - Finans Modülü</a>
        <a class="m-btn" href="/duyurular-ui" accesskey="6" title="Kısayol: Alt+6">Duyurular</a>
      </div>
      <div class="head-right">
        <div class="admin-menu">
          <a class="admin-btn" href="/yonetici-ui">Yönetici Modülü</a>
          <div class="links">
            <a href="/reports-ui">Raporlar</a>
            <a href="/duyurular-ui">Duyurular</a>
            <a href="/projects-ui">Projeler</a>
            <a href="/users-ui">Kullanıcılar</a>
          </div>
        </div>
        <div class="right-panel">
          <span id="activeProjectBadge" class="project-badge">AKTİF PROJE: -</span>
        </div>
      </div>
      <select id="langSelect" class="lang-mini">
        <option value="tr">TR</option><option value="en">EN</option><option value="es">ES</option>
        <option value="ar">??</option><option value="it">IT</option><option value="ru">??</option>
      </select>
    </div>
  <div class="box">
    <h2>Projeler Yönetimi</h2>
    <div class="row top-login">
      <input id="username" placeholder="Kullanıcı adi" />
      <input id="password" type="password" placeholder="Şifre" />
      <label id="rememberWrap" style="font-size:13px;"><input id="rememberMe" type="checkbox" /> Beni Hatirla</label>
      <button id="loginBtn" type="button">Giriş Yap</button>
      <div id="tokenInfo" class="muted" style="width:100%;"></div>
    </div>
    <div class="row">
      <input id="name" placeholder="Proje adi" />
      <input id="city" list="cityList" placeholder="Şehir Seçiniz (yazılabilir)" />
      <datalist id="cityList"></datalist>
      <input id="op" maxlength="9" placeholder="Operasyon (max 9)" />
      <input id="limit" placeholder="Token limiti (ops.)" />
      <button id="createBtn" type="button">Proje Ekle</button>
    </div>
    <div id="summaryWrap" class="muted" style="display:flex;align-items:center;gap:8px;">
      <span id="summary"></span>
      <button id="saveBtn" type="button" class="btn-muted" style="display:none;padding:6px 12px;">Kaydet</button>
    </div>
    <table id="tbl" style="display:none;">
      <thead><tr><th>Aç/Kapa</th><th>PROJE KODU</th><th>Proje Adı</th><th>Proje Şehri</th><th>Proje Adminleri</th><th>Projede Managerler vs.</th><th>Araç Firması Ataması</th><th>Limit</th><th>Kullanılan</th><th>İşlem</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
  </div>
  <script>
    const username = document.getElementById('username');
    const password = document.getElementById('password');
    const rememberMe = document.getElementById('rememberMe');
    const tokenInfo = document.getElementById('tokenInfo');
    const loginBtn = document.getElementById('loginBtn');
    const saveBtn = document.getElementById('saveBtn');
    const createBtn = document.getElementById('createBtn');
    const summary = document.getElementById('summary');
    const activeProjectBadge = document.getElementById('activeProjectBadge');
    const tbl = document.getElementById('tbl');
    const tbody = tbl.querySelector('tbody');
    const nameInput = document.getElementById('name');
    const cityInput = document.getElementById('city');
    const cityListEl = document.getElementById('cityList');
    const opInput = document.getElementById('op');
    const limitInput = document.getElementById('limit');
    let token = localStorage.getItem('access_token') || '';
    let currentRole = '';
    let supplierCompanies = [];
    let validCityCodes = new Set();
    const pendingProjectStatus = {};
    const refreshSaveButton = () => {
      if (!saveBtn) return;
      saveBtn.style.display = Object.keys(pendingProjectStatus).length ? '' : 'none';
    };
    const rememberedUsername = localStorage.getItem('remembered_username') || '';
    const rememberedEnabled = localStorage.getItem('remember_me') === '1';
    if (rememberedEnabled && rememberedUsername) {
      username.value = rememberedUsername;
      rememberMe.checked = true;
    }
    const loginOnEnter = (e) => { if (e.key === 'Enter') { e.preventDefault(); loginBtn.click(); } };
    username.addEventListener('keydown', loginOnEnter);
    password.addEventListener('keydown', loginOnEnter);
    const clearSessionCache = () => {
      const uiLang = localStorage.getItem('ui_lang') || '';
      localStorage.clear();
      sessionStorage.clear();
      if (uiLang) localStorage.setItem('ui_lang', uiLang);
    };
    const headers = () => ({ Authorization: `Bearer ${token}` });
    const normalizeCityInput = (val) => String(val || '')
      .trim()
      .toUpperCase()
      .replaceAll('İ', 'I')
      .replaceAll('İ', 'I')
      .replaceAll('Ş', 'S')
      .replaceAll('Ğ', 'G')
      .replaceAll('Ü', 'U')
      .replaceAll('Ö', 'O')
      .replaceAll('Ç', 'C')
      .replaceAll('Â', 'A')
      .replaceAll('Î', 'I')
      .replaceAll('Û', 'U')
      .replace(/\\s+/g, ' ');
    const loadCityCatalog = async () => {
      try {
        const res = await fetch('/cities');
        const data = await res.json().catch(() => []);
        if (!res.ok) return;
        const rows = Array.isArray(data) ? data : [];
        validCityCodes = new Set(rows.map((x) => String(x.code || '').trim()).filter(Boolean));
        if (cityListEl) {
          cityListEl.innerHTML = rows.map((x) => `<option value="${escHtml(x.name || x.code || '')}" data-code="${escHtml(x.code || '')}">${escHtml(x.iata_codes || '')}</option>`).join('');
        }
      } catch (_) {}
    };
    const escHtml = (v) => String(v || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    const supplierSelectHtml = (project) => {
      const current = project && project.default_supplier_company_id != null ? String(project.default_supplier_company_id) : '';
      const opts = ['<option value="">Atama Yok</option>']
        .concat((supplierCompanies || []).map((c) => `<option value="${c.id}" ${String(c.id) === current ? 'selected' : ''}>${escHtml(c.name)}</option>`));
      return `<select class="assign-supplier" data-id="${project.id}" style="padding:6px 8px;min-width:170px;border:1px solid #cfd9e8;border-radius:8px;">${opts.join('')}</select>`;
    };
    const loadSupplierCompanies = async () => {
      if (!token) return;
      try {
        const res = await fetch('/supplier-companies', { headers: headers() });
        const data = await res.json().catch(() => []);
        if (!res.ok) return;
        supplierCompanies = Array.isArray(data) ? data : [];
      } catch (_) {}
    };
    const renderProjectBadge = (user) => {
      if (!activeProjectBadge) return;
      const pName = user && user.active_project_name ? user.active_project_name : '-';
      const pCode = user && (user.active_project_code || (user.active_project_id ? `ID-${user.active_project_id}` : '-'));
      activeProjectBadge.textContent = `AKTİF PROJE: ${pName} (${pCode || '-'})`;
    };
    const renderTokenInfo = (user, tenantBalance) => {
      const personal = user && user.token_remaining != null ? user.token_remaining : 'SINIRSIZ';
      const firma = tenantBalance != null ? tenantBalance : '-';
      tokenInfo.textContent = `Kisisel Token: ${personal} | Firma Token: ${firma}`;
    };
    let profileBtn = null;
    let profileMenu = null;
    const closeProfileMenu = () => { if (profileMenu) profileMenu.style.display = 'none'; };
    const ensureProfileUi = () => {
      if (profileBtn) return;
      profileBtn = document.createElement('button');
      profileBtn.type = 'button';
      profileBtn.className = 'btn-muted';
      profileBtn.style.marginLeft = '6px';
      profileBtn.style.display = 'inline-flex';
      profileBtn.style.alignItems = 'center';
      profileBtn.style.gap = '6px';
      profileBtn.innerHTML = '<span style="width:18px;height:18px;border-radius:50%;background:#2b7fff;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;">U</span><span>PROFILE</span>';
      loginBtn.parentElement.appendChild(profileBtn);
      profileMenu = document.createElement('div');
      profileMenu.style.position = 'absolute';
      profileMenu.style.top = '46px';
      profileMenu.style.right = '8px';
      profileMenu.style.background = '#fff';
      profileMenu.style.border = '1px solid #dde4ef';
      profileMenu.style.borderRadius = '8px';
      profileMenu.style.padding = '10px';
      profileMenu.style.minWidth = '220px';
      profileMenu.style.display = 'none';
      profileMenu.style.boxShadow = '0 8px 20px rgba(0,0,0,0.08)';
      profileMenu.innerHTML = '<div id="pmUser" style="font-weight:700;"></div><div id="pmRole" class="muted" style="margin:4px 0 8px;"></div><button id="pmProfile" type="button">Profil Bilgileri</button> <button id="pmSettings" type="button" class="btn-muted">Ayarlar</button> <button id="pmLogout" type="button" style="background:#c62828;color:#fff;border:0;border-radius:8px;padding:8px 10px;margin-left:4px;">Çıkış</button>';
      loginBtn.parentElement.style.position = 'relative';
      loginBtn.parentElement.appendChild(profileMenu);
      profileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        profileMenu.style.display = profileMenu.style.display === 'none' ? 'block' : 'none';
      });
      document.addEventListener('click', (e) => {
        if (!profileMenu || profileMenu.style.display === 'none') return;
        if (!profileMenu.contains(e.target) && e.target !== profileBtn) closeProfileMenu();
      });
      const showPersonalQr = async () => {
        try {
          const res = await fetch('/auth/personal-qr', { headers: headers() });
          if (!res.ok) { alert('Karekod yüklenemedi.'); return; }
          const payload = res.headers.get('X-QR-Payload') || '-';
          const blob = await res.blob();
          const imgUrl = URL.createObjectURL(blob);
          const overlay = document.createElement('div');
          overlay.style.position = 'fixed';
          overlay.style.inset = '0';
          overlay.style.background = 'rgba(10,16,36,0.55)';
          overlay.style.display = 'flex';
          overlay.style.alignItems = 'center';
          overlay.style.justifyContent = 'center';
          overlay.style.zIndex = '1400';
          const card = document.createElement('div');
          card.style.background = '#fff';
          card.style.border = '1px solid #dde4ef';
          card.style.borderRadius = '12px';
          card.style.padding = '14px';
          card.style.minWidth = '320px';
          card.style.textAlign = 'center';
          card.innerHTML = `<div style="font-weight:700;margin-bottom:8px;">Kişisel Karekod</div><img src="${imgUrl}" alt="Kişisel Karekod" style="width:220px;height:220px;border:1px solid #e2e8f0;border-radius:8px;background:#fff;" /><div class="muted" style="margin-top:8px;word-break:break-all;">${payload}</div><div style="margin-top:10px;"><button id="closeQrBtn" type="button" class="btn-muted">Kapat</button></div>`;
          overlay.appendChild(card);
          document.body.appendChild(overlay);
          const close = () => { URL.revokeObjectURL(imgUrl); overlay.remove(); };
          overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
          card.querySelector('#closeQrBtn').addEventListener('click', close);
        } catch (_) {
          alert('Karekod yüklenemedi.');
        }
      };
      profileMenu.querySelector('#pmProfile').addEventListener('click', showPersonalQr);
      profileMenu.querySelector('#pmSettings').addEventListener('click', () => alert('Ayarlar paneli yakında eklenecek.'));
      profileMenu.querySelector('#pmLogout').addEventListener('click', () => {
        clearSessionCache();
        token = '';
        closeProfileMenu();
        applyAuthUi(null, null);
        summary.textContent = 'Çıkış yapildi.';
      });
    };
    const applyAuthUi = (user, tenantBalance) => {
      const root = document.documentElement;
      const loggedIn = !!(user && user.username);
      if (loggedIn) root.classList.add('has-token');
      else root.classList.remove('has-token');
      username.style.display = loggedIn ? 'none' : '';
      password.style.display = loggedIn ? 'none' : '';
      if (rememberMe && rememberMe.parentElement) rememberMe.parentElement.style.display = loggedIn ? 'none' : '';
      loginBtn.style.display = loggedIn ? 'none' : '';
      ensureProfileUi();
      profileBtn.style.display = loggedIn ? '' : 'none';
      if (loggedIn) {
        const initial = ((user.username || 'U').charAt(0) || 'U').toUpperCase();
        profileBtn.innerHTML = `<span style="width:18px;height:18px;border-radius:50%;background:#2b7fff;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;">${initial}</span><span>${user.username}</span>`;
        const pmUser = profileMenu.querySelector('#pmUser');
        const pmRole = profileMenu.querySelector('#pmRole');
        if (pmUser) pmUser.textContent = user.username;
        if (pmRole) pmRole.textContent = `Rol: ${user.role || '-'} | Firma: ${user.tenant_name || '-'}`;
        currentRole = String(user.role || '').toLowerCase();
        renderTokenInfo(user, tenantBalance);
        renderProjectBadge(user);
      } else {
        closeProfileMenu();
        tokenInfo.textContent = '';
        renderProjectBadge(null);
        Object.keys(pendingProjectStatus).forEach((k) => delete pendingProjectStatus[k]);
        refreshSaveButton();
      }
      root.classList.remove('ui-booting');
    };
    const loadSessionInfo = async () => {
      if (!token) return;
      try {
        const res = await fetch('/auth/me', { headers: headers() });
        const data = await res.json();
        if (!res.ok) {
          clearSessionCache();
          token = '';
          summary.textContent = 'Oturum suresi dolmus, tekrar giris yapin.';
          applyAuthUi(null, null);
          return;
        }
        applyAuthUi(data, data.tenant_token_balance);
        renderProjectBadge(data);
        summary.textContent = `Oturum aktif: ${data.username}`;
        await load();
      } catch (_) {
        applyAuthUi(null, null);
      }
    };
    if (token) loadSessionInfo();
    else applyAuthUi(null, null);
    loadCityCatalog();

    const load = async () => {
      if (!token) { summary.textContent = 'Once giris yapin.'; return; }
      if (!supplierCompanies.length) await loadSupplierCompanies();
      const res = await fetch('/projects', { headers: headers() });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Projeler alınamadı');
      Object.keys(pendingProjectStatus).forEach((k) => delete pendingProjectStatus[k]);
      refreshSaveButton();
      tbody.innerHTML = '';
      (data || []).forEach(p => {
        const tr = document.createElement('tr');
        const toggleBtn = `<span class="switch-wrap"><label class="switch"><input type="checkbox" class="toggle-project" data-id="${p.id}" data-active="${p.is_active ? '1':'0'}" ${p.is_active ? 'checked' : ''}><span class="slider"></span></label><span class="status-chip ${p.is_active ? 'active' : 'passive'}">${p.is_active ? 'Aktif' : 'Pasif'}</span></span>`;
        const action = currentRole === 'superadmin'
          ? `<button type="button" class="btn-muted del-project" data-id="${p.id}" data-code="${p.operation_code || ''}" style="padding:6px 10px;">Sil</button>`
          : '';
        const supplierCell = supplierSelectHtml(p);
        tr.innerHTML = `<td>${toggleBtn}</td><td>${p.operation_code || ''}</td><td>${p.name}</td><td>${p.city}</td><td>${p.project_admins || '-'}</td><td>${p.project_team || '-'}</td><td>${supplierCell}</td><td>${p.token_limit ?? ''}</td><td>${p.token_used ?? 0}</td><td>${action}</td>`;
        tbody.appendChild(tr);
      });
      tbl.style.display = '';
      summary.textContent = `${(data || []).length} proje listelendi.`;
    };

    loginBtn.addEventListener('click', async () => {
      try {
        const res = await fetch('/auth/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ username: username.value, password: password.value }) });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Giriş başarısız');
        clearSessionCache();
        token = data.access_token || '';
        localStorage.setItem('access_token', token);
        applyAuthUi(data.user || {}, data.tenant_token_balance);
        if (rememberMe.checked) {
          localStorage.setItem('remember_me', '1');
          localStorage.setItem('remembered_username', username.value || '');
        } else {
          localStorage.removeItem('remember_me');
          localStorage.removeItem('remembered_username');
        }
        await loadSessionInfo();
        await load();
      } catch (err) { summary.textContent = `Hata: ${err.message}`; }
    });

    createBtn.addEventListener('click', async () => {
      if (!token) { summary.textContent = 'Once giris yapin.'; return; }
      try {
        const cityNorm = normalizeCityInput(cityInput.value || '');
        if (!cityNorm || !validCityCodes.has(cityNorm)) {
          summary.textContent = 'Geçerli bir şehir seçiniz.';
          return;
        }
        const payload = { name: nameInput.value || '', city: cityNorm, operation_code: opInput.value || '' };
        if ((limitInput.value || '').trim()) payload.token_limit = parseInt(limitInput.value, 10);
        const res = await fetch('/projects', { method:'POST', headers:{...headers(),'Content-Type':'application/json'}, body: JSON.stringify(payload) });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Proje oluşturulamadı');
        await load();
      } catch (err) { summary.textContent = `Hata: ${err.message}`; }
    });

    saveBtn.addEventListener('click', async () => {
      if (!token) { summary.textContent = 'Önce giriş yapın.'; return; }
      const entries = Object.entries(pendingProjectStatus);
      if (!entries.length) { summary.textContent = 'Kaydedilecek durum değişikliği yok.'; return; }
      saveBtn.disabled = true;
      try {
        for (const [projectId, nextState] of entries) {
          const res = await fetch(`/projects/${projectId}`, {
            method:'PUT',
            headers:{...headers(),'Content-Type':'application/json'},
            body: JSON.stringify({ is_active: !!nextState })
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) throw new Error(data.detail || `Proje durumu güncellenemedi (ID: ${projectId})`);
        }
        summary.textContent = 'Durum değişiklikleri kaydedildi. Sayfa yenileniyor...';
        Object.keys(pendingProjectStatus).forEach((k) => delete pendingProjectStatus[k]);
        refreshSaveButton();
        setTimeout(() => { window.location.reload(); }, 400);
      } catch (err) {
        summary.textContent = `Hata: ${err.message}`;
      } finally {
        saveBtn.disabled = false;
      }
    });
    tbody.addEventListener('click', async (e) => {
      const toggleBtn = e.target.closest('.toggle-project');
      if (toggleBtn) {
        if (!token) { summary.textContent = 'Önce giriş yapın.'; return; }
        const id = parseInt(toggleBtn.getAttribute('data-id') || '0', 10);
        const isActive = toggleBtn.getAttribute('data-active') === '1';
        if (!id) return;
        const nextState = !!toggleBtn.checked;
        if (nextState === isActive) delete pendingProjectStatus[id];
        else pendingProjectStatus[id] = nextState;
        refreshSaveButton();
        const wrap = toggleBtn.closest('.switch-wrap');
        const chip = wrap ? wrap.querySelector('.status-chip') : null;
        if (chip) {
          chip.textContent = nextState ? 'Aktif' : 'Pasif';
          chip.classList.remove(nextState ? 'passive' : 'active');
          chip.classList.add(nextState ? 'active' : 'passive');
        }
        summary.textContent = Object.keys(pendingProjectStatus).length
          ? 'Durum değişikliği hazır. Kaydet ile kalıcı yapabilirsiniz.'
          : 'Bekleyen durum değişikliği kalmadı.';
        return;
      }
      const btn = e.target.closest('.del-project');
      if (!btn) return;
      if (currentRole !== 'superadmin') return;
      const id = parseInt(btn.getAttribute('data-id') || '0', 10);
      const code = btn.getAttribute('data-code') || '-';
      if (!id) return;
      if (!confirm(`Projeyi silmek istediğinize emin misiniz? (${code})`)) return;
      try {
        const res = await fetch(`/projects/${id}`, { method:'DELETE', headers: headers() });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || 'Proje silinemedi');
        summary.textContent = `Proje silindi: ${code}`;
        await load();
      } catch (err) {
        summary.textContent = `Hata: ${err.message}`;
      }
    });
    tbody.addEventListener('change', async (e) => {
      const sel = e.target.closest('.assign-supplier');
      if (!sel) return;
      if (!token) { summary.textContent = 'Önce giriş yapın.'; return; }
      const projectId = parseInt(sel.getAttribute('data-id') || '0', 10);
      if (!projectId) return;
      const raw = String(sel.value || '').trim();
      const payload = { default_supplier_company_id: raw ? parseInt(raw, 10) : null };
      sel.disabled = true;
      try {
        const res = await fetch(`/projects/${projectId}`, {
          method:'PUT',
          headers:{...headers(),'Content-Type':'application/json'},
          body: JSON.stringify(payload)
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || 'Araç firması ataması güncellenemedi');
        summary.textContent = raw ? 'Araç firması atandı.' : 'Araç firması ataması kaldırıldı.';
      } catch (err) {
        summary.textContent = `Hata: ${err.message}`;
        await load();
      } finally {
        sel.disabled = false;
      }
    });
  </script>  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""


def _desk_fold(value: str | None) -> str:
    s = str(value or "").lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return (
        s.replace("ı", "i")
        .replace("ş", "s")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ö", "o")
        .replace("ç", "c")
    )


def _desk_compact(value: str | None) -> str:
    return re.sub(r"[^a-z0-9*]", "", _desk_fold(value))


def _desk_wildcard(token: str) -> re.Pattern[str] | None:
    raw = str(token or "").strip()
    if not raw:
        return None
    parts = [re.escape(p) for p in raw.split("*")]
    pattern = ".*".join(parts)
    try:
        return re.compile(pattern, flags=re.IGNORECASE)
    except re.error:
        return None


def _desk_match_text(hay: str, needle: str) -> bool:
    n = _desk_fold(needle).strip()
    if not n:
        return True
    h = _desk_fold(hay)
    h_compact = _desk_compact(h)
    tokens = [t.strip() for t in n.split(" ") if t.strip()]

    phrase_compact = _desk_compact(n)
    if "*" in n:
        rx = _desk_wildcard(n)
        rx2 = _desk_wildcard(phrase_compact)
        phrase_ok = bool((rx and rx.search(h)) or (rx2 and rx2.search(h_compact)))
    else:
        phrase_ok = (n in h) or (phrase_compact and phrase_compact in h_compact)

    token_ok = True
    for tok in tokens:
        tok_compact = _desk_compact(tok)
        if "*" in tok:
            rx = _desk_wildcard(tok)
            rx2 = _desk_wildcard(tok_compact)
            ok = bool((rx and rx.search(h)) or (rx2 and rx2.search(h_compact)))
        else:
            ok = (tok in h) or (tok_compact and tok_compact in h_compact)
        if not ok:
            token_ok = False
            break
    return bool(phrase_ok or token_ok)


@app.get("/desk/search")
def desk_search(
    q: str = Query(...),
    project_id: int | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    _require_module_access(db, current_user, "kayit")
    scoped_project_id, management_scope = _resolve_project_scope_for_user(db, current_user, project_id)
    query = db.query(ModuleData).filter(ModuleData.module_name == "kayit")
    if not is_superadmin(current_user):
        query = query.filter(ModuleData.tenant_id == current_user.tenant_id)
    if not management_scope:
        query = query.filter(ModuleData.project_id == scoped_project_id)
    elif scoped_project_id is not None:
        query = query.filter(ModuleData.project_id == scoped_project_id)

    out = []
    rows = query.order_by(ModuleData.created_at.desc()).limit(10000).all()
    for r in rows:
        d = r.data if isinstance(r.data, dict) else {}
        hay = json.dumps(d or {}, ensure_ascii=False)
        if _desk_match_text(hay, q):
            out.append(
                {
                    "id": r.id,
                    "tenant_id": r.tenant_id,
                    "project_id": r.project_id,
                    "module_name": r.module_name,
                    "entity_type": r.entity_type,
                    "data": r.data,
                    "created_by_user_id": r.created_by_user_id,
                    "updated_by_user_id": r.updated_by_user_id,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                }
            )
            if len(out) >= limit:
                break
    return out


@app.get("/desk-ui", response_class=HTMLResponse)
def desk_ui():
    html = """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Desk Yetkileri ve Katılımcı Hizmetleri</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .head { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; position:relative; }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn { background: rgba(255,255,255,0.18); color:#fff; text-decoration:none; border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px; }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .muted { color:#5c6b82; font-size:13px; }
    .row { display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }
    .input { border:1px solid #cfd9e8; border-radius:8px; padding:8px 10px; font-size:12px; min-width:210px; }
    .btn { border:0; border-radius:8px; background:#2b7fff; color:#fff; padding:8px 12px; cursor:pointer; }
    .btn.alt { background:#5c6b82; }
    .grid { display:grid; grid-template-columns: repeat(2, minmax(280px, 1fr)); gap:12px; margin-top:12px; }
    .card { border:1px solid #dde4ef; border-radius:10px; padding:12px; background:#f8fbff; }
    .k { color:#5c6b82; font-size:11px; }
    .v { color:#1c2635; font-size:13px; font-weight:700; margin-bottom:6px; }
    .service { border:1px solid #d9e4f5; border-radius:8px; padding:8px; margin-top:8px; background:#fff; }
    .service h4 { margin:0 0 6px; font-size:12px; color:#0f2242; }
    .list { margin-top:12px; border:1px solid #dde4ef; border-radius:10px; overflow:auto; max-height:48vh; }
    table { width:100%; border-collapse:collapse; font-size:12px; }
    th, td { border:1px solid #dde4ef; padding:7px; text-align:left; }
    th { background:#f0f5ff; position: sticky; top: 0; }
    tr.active td { background:#eaf3ff; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn" href="/kayit-ui">Kayıt Modülü</a>
        <a class="m-btn active" href="/desk-ui">Desk</a>
      </div>
    </div>
    <div class="box">
      <h3 style="margin:0;">Desk Yetkileri ve Katılımcı Hizmetleri</h3>
      <div class="muted">Katılımcı girişinde kişisel bilgileri ve aldığı hizmetleri tek ekranda görüntülemek için hazırlık motoru.</div>
      <div class="row">
        <input id="q" class="input" placeholder="Ad Soyad, Kimlik, Telefon, E-posta ile ara" />
        <button id="btnSearch" class="btn" type="button">Ara</button>
        <button id="btnRefresh" class="btn alt" type="button">Yenile</button>
      </div>
      <div id="info" class="muted" style="margin-top:8px;">Yükleniyor...</div>
      <div class="list">
        <table>
          <thead><tr><th>ID</th><th>Ad Soyad</th><th>Kimlik</th><th>Telefon</th><th>E-posta</th><th>Kurum</th></tr></thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
      <div class="grid">
        <div class="card">
          <h4 style="margin:0 0 8px;">Kişisel Bilgiler</h4>
          <div class="k">Ad Soyad</div><div id="p_name" class="v">-</div>
          <div class="k">Kimlik No</div><div id="p_idno" class="v">-</div>
          <div class="k">Doğum Tarihi</div><div id="p_birth" class="v">-</div>
          <div class="k">Cinsiyet</div><div id="p_gender" class="v">-</div>
          <div class="k">Telefon</div><div id="p_phone" class="v">-</div>
          <div class="k">E-posta</div><div id="p_mail" class="v">-</div>
          <div class="k">Kurum</div><div id="p_org" class="v">-</div>
        </div>
        <div class="card">
          <h4 style="margin:0 0 8px;">Alınan Hizmetler</h4>
          <div class="service">
            <h4>Transfer</h4>
            <div id="s_transfer" class="muted">-</div>
          </div>
          <div class="service">
            <h4>Konaklama</h4>
            <div id="s_hotel" class="muted">-</div>
          </div>
          <div class="service">
            <h4>Diğer Notlar</h4>
            <div id="s_note" class="muted">-</div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <script>
    (function(){
      const info = document.getElementById("info");
      const tbody = document.getElementById("tbody");
      const q = document.getElementById("q");
      const token = localStorage.getItem("access_token")
        || sessionStorage.getItem("access_token")
        || localStorage.getItem("token")
        || sessionStorage.getItem("token")
        || "";
      const headers = () => token ? ({ Authorization: "Bearer " + token }) : ({});
      const esc = (v) => String(v || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      let rows = [];
      let filtered = [];
      let activeProjectId = null;

      function normalizeRow(r){
        const d = (r && r.data) || {};
        const fullName = d.ad_soyad || d.full_name || d.passenger_name || d.adsoyad || "";
        const fullParts = String(fullName || "").trim().split(" ").map((p) => String(p || "").trim()).filter(Boolean);
        const firstFromFull = fullParts.length ? fullParts[0] : "";
        const lastFromFull = fullParts.length > 1 ? fullParts.slice(1).join(" ") : "";
        const searchBlob = JSON.stringify(d || {});
        return {
          row: r,
          id: r && r.id,
          ad: d.isim || d.f_isim || d.ad || d.first_name || firstFromFull || "",
          soyad: d.soyisim || d.f_soyisim || d.soyad || d.last_name || lastFromFull || "",
          kimlik: d.kimlik_no || d.f_kimlik || "",
          dogum: d.dogum_tarihi || d.f_dogum || "",
          cinsiyet: d.cinsiyet || d.f_cinsiyet || "",
          telefon: d.telefon || d.f_telefon || "",
          mail: d.mail || d.f_mail || "",
          kurum: d.kurum || d.f_kurum || "",
          transfer: d.transfer_detay || d.f_transfer || "",
          konaklama: d.konaklama_detay || d.f_konaklama || "",
          note: d.not || d.note || "",
          search_blob: searchBlob
        };
      }

      function renderDetail(item){
        if (!item) {
          ["p_name","p_idno","p_birth","p_gender","p_phone","p_mail","p_org"].forEach((id) => document.getElementById(id).textContent = "-");
          ["s_transfer","s_hotel","s_note"].forEach((id) => document.getElementById(id).textContent = "-");
          return;
        }
        document.getElementById("p_name").textContent = ((item.ad || "") + " " + (item.soyad || "")).trim() || "-";
        document.getElementById("p_idno").textContent = item.kimlik || "-";
        document.getElementById("p_birth").textContent = item.dogum || "-";
        document.getElementById("p_gender").textContent = item.cinsiyet || "-";
        document.getElementById("p_phone").textContent = item.telefon || "-";
        document.getElementById("p_mail").textContent = item.mail || "-";
        document.getElementById("p_org").textContent = item.kurum || "-";
        document.getElementById("s_transfer").textContent = item.transfer || "Transfer kaydı bulunmuyor.";
        document.getElementById("s_hotel").textContent = item.konaklama || "Konaklama kaydı bulunmuyor.";
        document.getElementById("s_note").textContent = item.note || "-";
      }

      function renderTable(list){
        tbody.innerHTML = list.map((x, idx) => `
          <tr data-idx="${idx}">
            <td>${esc(x.id)}</td>
            <td>${esc(((x.ad || "") + " " + (x.soyad || "")).trim())}</td>
            <td>${esc(x.kimlik)}</td>
            <td>${esc(x.telefon)}</td>
            <td>${esc(x.mail)}</td>
            <td>${esc(x.kurum)}</td>
          </tr>
        `).join("");
        info.textContent = `Toplam ${list.length} katılımcı listelendi.`;
        renderDetail(list[0] || null);
        const first = tbody.querySelector("tr");
        if (first) first.classList.add("active");
      }

      function escRegex(text){
        const specials = "^$.*+?()[]{}|" + String.fromCharCode(92);
        let out = "";
        for (const ch of String(text || "")) {
          out += (specials.indexOf(ch) >= 0) ? (String.fromCharCode(92) + ch) : ch;
        }
        return out;
      }

      function foldTr(text){
        const decomposed = String(text || "")
          .toLocaleLowerCase("tr-TR")
          .normalize("NFD");
        let s = "";
        for (const ch of decomposed) {
          const code = ch.charCodeAt(0);
          if (code >= 0x0300 && code <= 0x036f) continue;
          s += ch;
        }
        return s
          .replaceAll("ı", "i")
          .replaceAll("ş", "s")
          .replaceAll("ğ", "g")
          .replaceAll("ü", "u")
          .replaceAll("ö", "o")
          .replaceAll("ç", "c");
      }

      function compactForSearch(text){
        return foldTr(text || "").replace(/[^a-z0-9*]/g, "");
      }

      function wildcardTokenToRegex(token){
        const raw = String(token || "").trim();
        if (!raw) return null;
        const pattern = raw.split("*").map((part) => escRegex(part)).join(".*");
        try { return new RegExp(pattern, "i"); } catch (_) { return null; }
      }

      async function applyFilter(){
        const needle = foldTr(q.value || "").trim();
        if (!needle) {
          filtered = rows.slice();
          renderTable(filtered);
          return;
        }
        const tokens = needle.split(" ").map((t) => String(t || "").trim()).filter(Boolean);
        const regexTokens = tokens.map((t) => wildcardTokenToRegex(t));
        const compactTokens = tokens.map((t) => compactForSearch(t));
        const compactRegexTokens = compactTokens.map((t) => wildcardTokenToRegex(t));
        const needleCompact = compactForSearch(needle);
        const needleRegex = wildcardTokenToRegex(needle);
        const needleCompactRegex = wildcardTokenToRegex(needleCompact);
        filtered = rows.filter((x) => {
          const hay = [x.ad, x.soyad, x.kimlik, x.telefon, x.mail, x.kurum, x.transfer, x.konaklama, x.note, x.search_blob, JSON.stringify(x.row || {})].join(" ");
          const hayLower = foldTr(hay);
          const hayCompact = compactForSearch(hay);
          const phraseMatch = needle.indexOf("*") >= 0
            ? ((!!needleRegex && needleRegex.test(hayLower)) || (!!needleCompactRegex && needleCompactRegex.test(hayCompact)))
            : (hayLower.indexOf(needle) >= 0 || (needleCompact && hayCompact.indexOf(needleCompact) >= 0));
          const tokenMatch = tokens.every((tok, idx) => {
            const rx = regexTokens[idx];
            const tokCompact = compactTokens[idx];
            const rxCompact = compactRegexTokens[idx];
            if (rx && tok.indexOf("*") >= 0) {
              return rx.test(hayLower) || (!!rxCompact && rxCompact.test(hayCompact));
            }
            return hayLower.indexOf(tok) >= 0 || (tokCompact && hayCompact.indexOf(tokCompact) >= 0);
          });
          return phraseMatch || tokenMatch;
        });
        if (filtered.length > 0) {
          renderTable(filtered);
          return;
        }
        try {
          const qs = new URLSearchParams();
          qs.set("q", String(q.value || ""));
          qs.set("limit", "2000");
          if (activeProjectId) qs.set("project_id", String(activeProjectId));
          const res = await fetch("/desk/search?" + qs.toString(), { headers: headers() });
          const data = await res.json().catch(() => []);
          if (!res.ok) throw new Error((data && data.detail) || "Arama yapılamadı");
          const remoteRows = (Array.isArray(data) ? data : []).map(normalizeRow);
          filtered = remoteRows;
          renderTable(filtered);
        } catch (_) {
          renderTable(filtered);
        }
      }

      async function load(){
        if (!token) { info.textContent = "Oturum yok. Önce giriş yapınız."; return; }
        try {
          const meRes = await fetch("/auth/me", { headers: headers() });
          const me = await meRes.json().catch(() => ({}));
          if (!meRes.ok) throw new Error(me.detail || "Oturum doğrulanamadı");
          activeProjectId = me.active_project_id || null;
          if (!activeProjectId) {
            rows = [];
            filtered = [];
            renderTable(filtered);
            info.textContent = "Aktif proje seçiniz. Desk yalnızca aktif projedeki katılımcıları listeler.";
            return;
          }
          const url = "/module-data?module_name=kayit&limit=5000&project_id=" + encodeURIComponent(String(activeProjectId));
          const res = await fetch(url, { headers: headers() });
          const data = await res.json().catch(() => []);
          if (!res.ok) throw new Error((data && data.detail) || "Kayıtlar alınamadı");
          rows = (Array.isArray(data) ? data : []).map(normalizeRow);
          filtered = rows.slice();
          renderTable(filtered);
        } catch (err) {
          info.textContent = "Hata: " + err.message;
        }
      }

      document.getElementById("btnSearch").addEventListener("click", () => { applyFilter(); });
      document.getElementById("btnRefresh").addEventListener("click", load);
      q.addEventListener("keydown", (e) => { if (e.key === "Enter") applyFilter(); });
      q.addEventListener("input", () => { applyFilter(); });
      tbody.addEventListener("click", (e) => {
        const tr = e.target && e.target.closest ? e.target.closest("tr[data-idx]") : null;
        if (!tr) return;
        const idx = Number(tr.getAttribute("data-idx"));
        Array.prototype.forEach.call(tbody.querySelectorAll("tr"), (x) => x.classList.remove("active"));
        tr.classList.add("active");
        renderDetail(filtered[idx] || null);
      });
      load();
    })();
  </script>
</body>
</html>
"""
    return HTMLResponse(_inject_standard_header_style(html))


@app.get("/duyurular-ui", response_class=HTMLResponse)
def announcements_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Duyurular</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .head { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; position:relative; }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn { background: rgba(255,255,255,0.18); color:#fff; text-decoration:none; border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px; }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .head-right { display:flex; flex-direction:row; align-items:center; gap:8px; margin-right:68px; }
    .right-panel { border:1px solid rgba(159,216,255,0.45); border-radius:8px; padding:4px 7px; background:rgba(8,23,56,0.20); }
    .admin-menu { position:relative; }
    .admin-btn { display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF; border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600; text-decoration:none; cursor:pointer; white-space:nowrap; }
    .admin-menu .links { display:none; position:absolute; top:100%; margin-top:2px; right:0; min-width:150px; background:#0A1024; border:1px solid rgba(159,216,255,0.35); border-radius:8px; padding:6px; z-index:50; }
    .admin-menu .links a { display:block; margin:0; padding:5px 6px; color:#9FD8FF; border-radius:6px; text-decoration:none; }
    .admin-menu .links a:hover { background:rgba(159,216,255,0.12); }
    .admin-menu:hover .links, .admin-menu:focus-within .links, .admin-menu.open .links { display:block; }
    .project-badge {
      display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF;
      border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600;
      letter-spacing:0.15px; white-space:nowrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08);
    }
    .panel { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .muted { color:#5c6b82; font-size:13px; }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn" href="/kayit-ui" accesskey="2" title="Kısayol: Alt+2">Kayıt Modülü</a>
        <a class="m-btn" href="/konaklama-ui" accesskey="3" title="Kısayol: Alt+3">Konaklama Modülü</a>
        <a class="m-btn" href="/toplanti-ui" accesskey="4" title="Kısayol: Alt+4">Toplantı Modülü</a>
        <a class="m-btn" href="/transfer-ui" accesskey="1" title="Kısayol: Alt+1">Ulaşım Modülü</a>
        <a class="m-btn" href="/muhasebe-finans-ui" accesskey="5" title="Kısayol: Alt+5">Muhasebe - Finans Modülü</a>
        <a class="m-btn active" href="/duyurular-ui" accesskey="6" title="Kısayol: Alt+6">Duyurular</a>
      </div>
    </div>
    <div class="panel">
      <h3 style="margin:0 0 8px 0;">Duyurular</h3>
      <div class="tabs" id="annTabs">
        <button class="tab" type="button" data-panel="panelAnnouncements">Duyurular</button>
        <button class="tab alt" type="button" data-panel="panelNotifications">Bildirimler</button>
      </div>
      <div id="panelAnnouncements" style="margin-top:10px;">
        <div class="muted">Sistem ve operasyon duyuruları bu bölümde yayınlanır.</div>
      </div>
      <div id="panelNotifications" style="margin-top:10px; display:none;">
        <div class="muted">Kullanıcıya özel bildirimler bu bölümde listelenir.</div>
      </div>
    </div>
  </div>
  <script>
    (function(){
      const tabs = Array.from(document.querySelectorAll('#annTabs .tab'));
      tabs.forEach((btn) => {
        btn.addEventListener('click', () => {
          tabs.forEach((x) => x.classList.add('alt'));
          btn.classList.remove('alt');
          const pid = btn.getAttribute('data-panel');
          ['panelAnnouncements','panelNotifications'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.style.display = (id === pid ? '' : 'none');
          });
        });
      });
    })();
  </script>
  <script>
    (async function(){
      const token = localStorage.getItem('access_token') || '';
      const badge = document.getElementById('activeProjectBadge');
      if (!token || !badge) return;
      try {
        const res = await fetch('/auth/me', { headers: { Authorization: `Bearer ${token}` } });
        const me = await res.json();
        if (!res.ok || !me) return;
        const pName = me.active_project_name || '-';
        const pCode = me.active_project_code || (me.active_project_id ? ('ID-' + me.active_project_id) : '-');
        badge.textContent = `AKTİF PROJE: ${pName} (${pCode})`;
      } catch (_) {}
    })();
  </script>
  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""


@app.get("/muhasebe-finans-ui", response_class=HTMLResponse)
def finance_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Muhasebe - Finans</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .head { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; position:relative; }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn { background: rgba(255,255,255,0.18); color:#fff; text-decoration:none; border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px; }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .head-right { display:flex; flex-direction:row; align-items:center; gap:8px; margin-right:68px; }
    .right-panel { border:1px solid rgba(159,216,255,0.45); border-radius:8px; padding:4px 7px; background:rgba(8,23,56,0.20); }
    .admin-menu { position:relative; }
    .admin-btn { display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF; border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600; text-decoration:none; cursor:pointer; white-space:nowrap; }
    .admin-menu .links { display:none; position:absolute; top:100%; margin-top:2px; right:0; min-width:150px; background:#0A1024; border:1px solid rgba(159,216,255,0.35); border-radius:8px; padding:6px; z-index:50; }
    .admin-menu .links a { display:block; margin:0; padding:5px 6px; color:#9FD8FF; border-radius:6px; text-decoration:none; }
    .admin-menu .links a:hover { background:rgba(159,216,255,0.12); }
    .admin-menu:hover .links, .admin-menu:focus-within .links, .admin-menu.open .links { display:block; }
    .project-badge {
      display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF;
      border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600;
      letter-spacing:0.15px; white-space:nowrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08);
    }
    .panel { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .muted { color:#5c6b82; font-size:13px; }
    table { width:100%; border-collapse:collapse; margin-top:10px; font-size:12px; }
    th, td { border:1px solid #dde4ef; padding:8px; text-align:left; }
    th { background:#f0f5ff; }
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn" href="/kayit-ui" accesskey="2" title="Kısayol: Alt+2">Kayıt Modülü</a>
        <a class="m-btn" href="/konaklama-ui" accesskey="3" title="Kısayol: Alt+3">Konaklama Modülü</a>
        <a class="m-btn" href="/toplanti-ui" accesskey="4" title="Kısayol: Alt+4">Toplantı Modülü</a>
        <a class="m-btn" href="/transfer-ui" accesskey="1" title="Kısayol: Alt+1">Ulaşım Modülü</a>
        <a class="m-btn active" href="/muhasebe-finans-ui" accesskey="5" title="Kısayol: Alt+5">Muhasebe - Finans Modülü</a>
        <a class="m-btn" href="/duyurular-ui" accesskey="6" title="Kısayol: Alt+6">Duyurular</a>
      </div>
      <div class="head-right">
        <div class="admin-menu">
          <a class="admin-btn" href="/yonetici-ui">Yönetici Modülü</a>
          <div class="links">
            <a href="/reports-ui">Raporlar</a>
            <a href="/duyurular-ui">Duyurular</a>
            <a href="/projects-ui">Projeler</a>
            <a href="/users-ui">Kullanıcılar</a>
          </div>
        </div>
        <div class="right-panel">
          <span id="activeProjectBadge" class="project-badge">AKTİF PROJE: -</span>
        </div>
      </div>
    </div>
    <div class="panel">
      <h3 style="margin:0 0 8px 0;">Muhasebe - Finans</h3>
      <div class="tabs" id="financeTabs">
        <button id="tabAll" class="tab" type="button" data-kind="all">Hepsi</button>
        <button class="tab alt" type="button" data-kind="konaklama">Konaklama</button>
        <button class="tab alt" type="button" data-kind="transfer">Transfer</button>
        <button class="tab alt" type="button" data-kind="ucak_bileti">Uçak Bileti</button>
        <button class="tab alt" type="button" data-kind="kayit">Kayıt</button>
        <button class="tab alt" type="button" data-kind="diger">Diğer</button>
      </div>
      <div class="muted" style="margin-top:8px;">Satırlar otomatik üretilir (Kayıt, Konaklama, Transfer, Uçak Bileti).</div>
      <div class="row" style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
        <button id="refreshFinanceBtn" class="tab alt" type="button">Yenile</button>
      </div>
      <div id="financeMsg" class="muted"></div>
      <table>
        <thead>
          <tr>
            <th>HİZMET TÜRÜ</th>
            <th>HİZMET ADI</th>
            <th>HİZMETİ KİM ALDI</th>
            <th>KİM ÖDEDİ</th>
            <th>MATRAH</th>
            <th>KDV</th>
            <th>TOPLAM</th>
            <th>PARA BİRİMİ</th>
            <th>DETAY</th>
            <th>TARİH</th>
          </tr>
        </thead>
        <tbody id="financeRows"></tbody>
      </table>
    </div>
  </div>
  <script>
    (function(){
      const token = localStorage.getItem('access_token') || '';
      const headers = () => ({ Authorization: `Bearer ${token}` });
      const rows = document.getElementById('financeRows');
      const tabs = Array.from(document.querySelectorAll('#financeTabs .tab'));
      const refreshBtn = document.getElementById('refreshFinanceBtn');
      const financeMsg = document.getElementById('financeMsg');
      const fmt = (n) => Number(n || 0).toFixed(2);
      let currentKind = 'all';
      let financeRows = [];

      const esc = (v) => String(v || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      const setMsg = (t) => { if (financeMsg) financeMsg.textContent = t || ''; };

      const render = (kind) => {
        const list = financeRows.filter(x => kind === 'all' ? true : x.kind === kind);
        rows.innerHTML = list.map(x => `<tr><td>${esc(String(x.kind || '').toUpperCase())}</td><td>${esc(x.service_name || '')}</td><td>${esc(x.alan || '')}</td><td>${esc(x.odeyen || '')}</td><td>${fmt(x.matrah)}</td><td>${fmt(x.kdv)}</td><td>${fmt(x.toplam)}</td><td>${esc(x.currency || '')}</td><td>${esc(x.detail || '')}</td><td>${esc(x.date || '')}</td></tr>`).join('');
      };

      const loadFinanceRows = async () => {
        const res = await fetch('/finance/auto-lines', { headers: headers() });
        const out = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(out.detail || 'Finans satırları alınamadı');
        financeRows = Array.isArray(out.rows) ? out.rows : [];
        setMsg(`Toplam satır: ${financeRows.length}`);
        render(currentKind);
      };

      tabs.forEach(btn => {
        btn.addEventListener('click', () => {
          tabs.forEach(t => t.classList.add('alt'));
          btn.classList.remove('alt');
          currentKind = btn.getAttribute('data-kind') || 'all';
          render(currentKind);
        });
      });

      if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
          loadFinanceRows().catch((err) => setMsg(`Hata: ${err.message}`));
        });
      }

      (async () => {
        try {
          await loadFinanceRows();
        } catch (err) {
          setMsg(`Hata: ${err.message}`);
        }
      })();
    })();
    (async function(){
      const token = localStorage.getItem('access_token') || '';
      const badge = document.getElementById('activeProjectBadge');
      if (!token || !badge) return;
      try {
        const res = await fetch('/auth/me', { headers: { Authorization: `Bearer ${token}` } });
        const me = await res.json();
        if (!res.ok || !me) return;
        const pName = me.active_project_name || '-';
        const pCode = me.active_project_code || (me.active_project_id ? ('ID-' + me.active_project_id) : '-');
        badge.textContent = `AKTİF PROJE: ${pName} (${pCode})`;
      } catch (_) {}
    })();
  </script>
  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""


@app.get("/finance/auto-lines")
def finance_auto_lines(
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    scoped_project_id, management_scope = _resolve_project_scope_for_user(db, current_user, project_id)
    if not management_scope and scoped_project_id is None:
        raise HTTPException(status_code=400, detail="Active project required")
    if scoped_project_id is None:
        raise HTTPException(status_code=400, detail="project_id is required in management scope")

    project = db.query(Project).filter(Project.id == scoped_project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not is_superadmin(current_user) and int(project.tenant_id or 0) != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="Forbidden")
    tenant_scope = int(project.tenant_id or 0)

    def _name_from_kayit_data(d: dict | None) -> str:
        d = d or {}
        first = str(d.get("isim") or d.get("f_isim") or "").strip()
        last = str(d.get("soyisim") or d.get("f_soyisim") or "").strip()
        full = f"{first} {last}".strip()
        if full:
            return full
        fallback = str(d.get("f_id") or d.get("id") or "").strip()
        return fallback or "Bilinmiyor"

    def _to_iso_date(v) -> str:
        if not v:
            return ""
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d")
        raw = str(v).strip()
        if not raw:
            return ""
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            return raw
        m = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
        if m:
            return m.group(1)
        m2 = re.search(r"(\d{2})[./-](\d{2})[./-](\d{4})", raw)
        if m2:
            return f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}"
        return raw[:10]

    def _mk_line(
        kind: str,
        service_name: str,
        alan: str,
        odeyen: str,
        matrah: float,
        kdv: float,
        toplam: float,
        currency: str = "TRY",
        source_id: int | None = None,
        detail: str = "",
        date_str: str = "",
    ) -> dict:
        return {
            "kind": kind,
            "service_name": service_name,
            "alan": alan or "Bilinmiyor",
            "odeyen": odeyen or "Bilinmiyor",
            "matrah": round(_to_float(matrah), 2),
            "kdv": round(_to_float(kdv), 2),
            "toplam": round(_to_float(toplam), 2),
            "currency": (currency or "TRY").upper(),
            "source_id": source_id,
            "detail": detail or "",
            "date": date_str or "",
        }

    category_defaults: dict[str, dict] = {}
    product_rows = (
        db.query(ProjectServiceProduct, ServiceProduct)
        .join(ServiceProduct, ServiceProduct.id == ProjectServiceProduct.product_id)
        .filter(
            ProjectServiceProduct.project_id == int(scoped_project_id),
            ProjectServiceProduct.is_active == True,  # noqa: E712
            ServiceProduct.is_active == True,  # noqa: E712
        )
        .order_by(ProjectServiceProduct.created_at.desc())
        .all()
    )
    for ps, sp in product_rows:
        cat = str(sp.category or "").strip().lower()
        if not cat or cat in category_defaults:
            continue
        price = ps.price_override if ps.price_override is not None else sp.price
        currency = ps.currency_override if ps.currency_override else sp.currency
        category_defaults[cat] = {
            "price": _to_float(price),
            "vat_rate": _to_float(sp.vat_rate),
            "currency": (currency or "TRY").upper(),
            "name": str(sp.name or cat).strip(),
        }

    kayit_rows = (
        db.query(ModuleData)
        .filter(
            ModuleData.module_name == "kayit",
            ModuleData.project_id == int(scoped_project_id),
            ModuleData.tenant_id == tenant_scope,
        )
        .order_by(ModuleData.created_at.desc())
        .all()
    )
    kayit_name_map: dict[int, str] = {}
    for row in kayit_rows:
        kayit_name_map[int(row.id)] = _name_from_kayit_data(row.data if isinstance(row.data, dict) else {})

    lines: list[dict] = []

    kayit_cfg = category_defaults.get("kayit", {})
    kayit_price = _to_float(kayit_cfg.get("price"))
    kayit_vat_rate = _to_float(kayit_cfg.get("vat_rate"))
    kayit_currency = str(kayit_cfg.get("currency") or "TRY").upper()
    kayit_service = str(kayit_cfg.get("name") or "Kayıt Hizmeti")
    for row in kayit_rows:
        d = row.data if isinstance(row.data, dict) else {}
        person_name = _name_from_kayit_data(d)
        matrah = _to_float(d.get("matrah")) or _to_float(d.get("ucret")) or kayit_price
        kdv = _to_float(d.get("kdv"))
        if kdv <= 0 and kayit_vat_rate > 0:
            kdv = round(matrah * kayit_vat_rate / 100.0, 2)
        toplam = _to_float(d.get("toplam")) or round(matrah + kdv, 2)
        lines.append(
            _mk_line(
                "kayit",
                kayit_service,
                person_name,
                person_name,
                matrah,
                kdv,
                toplam,
                kayit_currency,
                source_id=int(row.id),
                detail=str(d.get("kurum") or d.get("f_kurum") or ""),
                date_str=_to_iso_date(row.created_at),
            )
        )

    kon_cfg = category_defaults.get("konaklama", {})
    kon_currency = str(kon_cfg.get("currency") or "TRY").upper()
    kon_service = str(kon_cfg.get("name") or "Konaklama")
    kon_rows = (
        db.query(ModuleData)
        .filter(
            ModuleData.module_name == "konaklama",
            ModuleData.project_id == int(scoped_project_id),
            ModuleData.tenant_id == tenant_scope,
        )
        .order_by(ModuleData.created_at.desc())
        .all()
    )
    for row in kon_rows:
        d = row.data if isinstance(row.data, dict) else {}
        detail_parts = [
            str(d.get("hotel") or "").strip(),
            str(d.get("package_code") or "").strip(),
            str(d.get("room_type") or "").strip(),
        ]
        detail = " / ".join([p for p in detail_parts if p])
        person_amounts = [
            (str(d.get("person1_name") or "").strip(), _to_float(d.get("amount1"))),
            (str(d.get("person2_name") or "").strip(), _to_float(d.get("amount2"))),
            (str(d.get("person3_name") or "").strip(), _to_float(d.get("amount3"))),
        ]
        for person_name, amount in person_amounts:
            if not person_name or amount <= 0:
                continue
            lines.append(
                _mk_line(
                    "konaklama",
                    kon_service,
                    person_name,
                    person_name,
                    amount,
                    0.0,
                    amount,
                    kon_currency,
                    source_id=int(row.id),
                    detail=detail,
                    date_str=_to_iso_date(row.created_at),
                )
            )

    transfer_cfg = category_defaults.get("transfer", {})
    transfer_price = _to_float(transfer_cfg.get("price"))
    transfer_vat_rate = _to_float(transfer_cfg.get("vat_rate"))
    transfer_currency_default = str(transfer_cfg.get("currency") or "TRY").upper()
    transfer_service = str(transfer_cfg.get("name") or "Transfer")
    transfer_rows = (
        db.query(Transfer)
        .filter(Transfer.project_id == int(scoped_project_id), Transfer.tenant_id == tenant_scope)
        .order_by(Transfer.created_at.desc())
        .all()
    )
    for t in transfer_rows:
        person_name = (_normalized_person_name(t) or t.passenger_name or "Bilinmiyor").strip() or "Bilinmiyor"
        trip_label = _flight_shape_label(t)
        transfer_matrah = transfer_price
        transfer_kdv = round(transfer_matrah * transfer_vat_rate / 100.0, 2) if transfer_vat_rate > 0 else 0.0
        transfer_toplam = round(transfer_matrah + transfer_kdv, 2)
        lines.append(
            _mk_line(
                "transfer",
                transfer_service,
                person_name,
                person_name,
                transfer_matrah,
                transfer_kdv,
                transfer_toplam,
                transfer_currency_default,
                source_id=int(t.id),
                detail=trip_label,
                date_str=_to_iso_date(t.flight_date or t.created_at),
            )
        )

        fare = _to_float(t.base_fare)
        tax = _to_float(t.tax_total)
        total = _to_float(t.total_amount)
        if fare > 0 or tax > 0 or total > 0:
            if total <= 0:
                total = round(fare + tax, 2)
            lines.append(
                _mk_line(
                    "ucak_bileti",
                    "Uçak Bileti",
                    person_name,
                    person_name,
                    fare,
                    tax,
                    total,
                    str((t.currency or transfer_currency_default) or "TRY").upper(),
                    source_id=int(t.id),
                    detail=f"{(t.flight_no or '').strip()} / {(t.pnr or '').strip()}".strip(" /"),
                    date_str=_to_iso_date(t.flight_date or t.created_at),
                )
            )

    lines.sort(key=lambda x: ((x.get("date") or ""), int(x.get("source_id") or 0)), reverse=True)
    return {
        "project_id": int(scoped_project_id),
        "count": len(lines),
        "rows": lines,
    }


@app.get("/fx/tcmb-rates")
def fx_tcmb_rates(
    date: str | None = Query(default=None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    target = (date or "").strip()
    if target:
        try:
            dt = datetime.strptime(target, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    else:
        dt = datetime.now()
        target = dt.strftime("%Y-%m-%d")

    ddmmyyyy = dt.strftime("%d%m%Y")
    yyyymm = dt.strftime("%Y%m")
    url = f"https://www.tcmb.gov.tr/kurlar/{yyyymm}/{ddmmyyyy}.xml"
    if dt.date() == datetime.now().date():
        url = "https://www.tcmb.gov.tr/kurlar/today.xml"

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            xml_bytes = resp.read()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TCMB kur verisi alınamadı: {exc}")

    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        raise HTTPException(status_code=502, detail="TCMB XML parse edilemedi")

    def _rate_for(code: str) -> float | None:
        node = root.find(f".//Currency[@Kod='{code}']")
        if node is None:
            return None
        tags = ["ForexSelling", "BanknoteSelling", "ForexBuying", "BanknoteBuying"]
        for tag in tags:
            val_node = node.find(tag)
            raw = (val_node.text if val_node is not None else "") or ""
            raw = raw.strip().replace(",", ".")
            try:
                if raw:
                    return float(raw)
            except Exception:
                continue
        return None

    usd = _rate_for("USD")
    eur = _rate_for("EUR")
    gbp = _rate_for("GBP")
    if usd is None and eur is None and gbp is None:
        raise HTTPException(status_code=502, detail="TCMB verisinde kur bulunamadı")

    return {
        "date": target,
        "source": "tcmb",
        "rates": {
            "TL": 1.0,
            "USD": usd,
            "EUR": eur,
            "GBP": gbp,
        },
    }


@app.get("/urunler-ui", response_class=HTMLResponse)
def urunler_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Ürünler</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { max-width: 1100px; margin: 0 auto; padding: 16px; }
    .head { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn { background: rgba(255,255,255,0.18); color:#fff; text-decoration:none; border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px; }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:20px; }
    .title { font-size:22px; font-weight:700; margin:0 0 8px; }
    .muted { color:#5c6b82; font-size:14px; }
    .notice { margin-top:12px; border:1px dashed #9db2d4; border-radius:10px; padding:16px; background:#f8fbff; }
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn" href="/yonetici-ui">Yönetici Modülü</a>
        <a class="m-btn active" href="/urunler-ui">Ürünler</a>
      </div>
    </div>
    <div class="box">
      <div class="title">Ürünler</div>
      <div class="notice">
        <div class="muted">Tüm ürün verileri temizlendi. Bu sayfa yeni ürün yapısına göre baştan geliştirilecek.</div>
      </div>
    </div>
  </div>
</body>
</html>
"""

@app.get("/users-ui", response_class=HTMLResponse)
def users_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kullanıcılar</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
    .head {
      display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;
      background:#0A1024; color:#fff; padding:10px 12px; border-radius:10px; position:relative;
    }
    .head-left { display:flex; align-items:center; gap:12px; }
    .module-nav { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .m-btn {
      background: rgba(255,255,255,0.18); color:#fff; text-decoration:none;
      border:1px solid rgba(255,255,255,0.35); border-radius:8px; padding:5px 9px; font-size:12px;
    }
    .m-btn.active { background:#fff; color:#0A1024; font-weight:700; }
    .head-right { display:flex; flex-direction:row; align-items:center; gap:8px; margin-right:68px; }
    .right-panel {
      border:1px solid rgba(159,216,255,0.45);
      border-radius:8px;
      padding:4px 7px;
      background:rgba(8,23,56,0.20);
    }
    .links a { margin-right: 6px; color: #9FD8FF; text-decoration: none; font-size: 11px; font-weight: 600; }
    .admin-menu { position:relative; }
    .admin-btn { display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF; border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600; text-decoration:none; cursor:pointer; white-space:nowrap; }
    .admin-menu .links { display:none; position:absolute; top:100%; margin-top:2px; right:0; min-width:150px; background:#0A1024; border:1px solid rgba(159,216,255,0.35); border-radius:8px; padding:6px; z-index:50; }
    .admin-menu .links a { display:block; margin:0; padding:5px 6px; color:#9FD8FF; border-radius:6px; }
    .admin-menu .links a:hover { background:rgba(159,216,255,0.12); }
    .admin-menu:hover .links, .admin-menu:focus-within .links, .admin-menu.open .links { display:block; }
    .project-badge {
      display:inline-flex; align-items:center; background:rgba(7,19,46,0.28); color:#9FD8FF;
      border:1px solid rgba(159,216,255,0.78); border-radius:8px; padding:4px 8px; font-size:11px; font-weight:600;
      letter-spacing:0.15px; white-space:nowrap; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08);
    }
    .lang-mini { position:absolute; top:4px; right:8px; font-size:11px; padding:2px 4px; border-radius:6px; border:0; }
    .box { max-width: 1100px; margin: 0 auto; background: #fff; border: 1px solid #dde4ef; border-radius: 12px; padding: 20px; }
    .top-login { position: static; background: #fff; border: 1px solid #dde4ef; border-radius: 10px; padding: 8px; z-index: 1; }
    .top-login input { width: 120px; }
    input, select { padding: 8px; }
    button { background: #2b7fff; color: #fff; border: 0; border-radius: 8px; padding: 10px 14px; cursor: pointer; }
    .btn-muted { background: #5c6b82; }
    .row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
    table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 12px; }
    th, td { border: 1px solid #dde4ef; padding: 8px; text-align: left; }
    th { background: #f0f5ff; }
    .muted { color: #5c6b82; font-size: 13px; margin-top: 8px; }
    .footer-brand { position: fixed; left: 0; right: 0; bottom: 0; height: 54px; background: #0A1024; display: flex; align-items: center; padding-left: 12px; z-index: 998; overflow: hidden; }
    .footer-brand img { height: 150%; width: auto; display: block; object-fit: cover; object-position: center; clip-path: inset(0 3% 0 0); }
    .logo-reg { color: #fff; font-size: 12px; line-height: 1; margin-left: 0; font-weight: 700; position: relative; left: -26px; transform: translateY(-45%); }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="head-left module-nav">
        <a class="m-btn" href="/modules-ui">Ana Sayfa</a>
        <a class="m-btn" href="/kayit-ui" accesskey="2" title="Kısayol: Alt+2">Kayıt Modülü</a>
        <a class="m-btn" href="/konaklama-ui" accesskey="3" title="Kısayol: Alt+3">Konaklama Modülü</a>
        <a class="m-btn" href="/toplanti-ui" accesskey="4" title="Kısayol: Alt+4">Toplantı Modülü</a>
        <a class="m-btn" href="/transfer-ui" accesskey="1" title="Kısayol: Alt+1">Ulaşım Modülü</a>
        <a class="m-btn" href="/muhasebe-finans-ui" accesskey="5" title="Kısayol: Alt+5">Muhasebe - Finans Modülü</a>
        <a class="m-btn" href="/duyurular-ui" accesskey="6" title="Kısayol: Alt+6">Duyurular</a>
      </div>
      <div class="head-right">
        <div class="admin-menu">
          <a class="admin-btn" href="/yonetici-ui">Yönetici Modülü</a>
          <div class="links">
            <a href="/reports-ui">Raporlar</a>
            <a href="/duyurular-ui">Duyurular</a>
            <a href="/projects-ui">Projeler</a>
            <a href="/users-ui">Kullanıcılar</a>
          </div>
        </div>
        <div class="right-panel">
          <span id="activeProjectBadge" class="project-badge">AKTİF PROJE: -</span>
        </div>
      </div>
      <select id="langSelect" class="lang-mini">
        <option value="tr">TR</option><option value="en">EN</option><option value="es">ES</option>
        <option value="ar">??</option><option value="it">IT</option><option value="ru">??</option>
      </select>
    </div>
  <div class="box">
    <h2>Kullanıcılar Yönetimi</h2>
    <div class="row top-login">
      <input id="username" placeholder="Kullanıcı adi" />
      <input id="password" type="password" placeholder="Şifre" />
      <label style="font-size:13px;"><input id="rememberMe" type="checkbox" /> Beni Hatirla</label>
      <button id="loginBtn" type="button">Giriş Yap</button>
      <button id="reloadBtn" type="button" class="btn-muted">Yenile</button>
      <div id="tokenInfo" class="muted" style="width:100%;"></div>
    </div>
    <div class="row">
      <input id="newUsername" placeholder="Kullanıcı adi" />
      <input id="newPassword" placeholder="Şifre" />
      <select id="newRole">
        <option value="tenant_operator">tenant_operator</option>
        <option value="interpreter">interpreter</option>
        <option value="participant">participant</option>
        <option value="greeter">greeter</option>
        <option value="driver">driver</option>
        <option value="supplier_admin">supplier_admin</option>
        <option value="tenant_manager">tenant_manager</option>
        <option value="tenant_admin">tenant_admin</option>
        <option value="supertranslator">supertranslator</option>
        <option value="superadmin_staff">superadmin_staff</option>
        <option value="superadmin">superadmin</option>
      </select>
      <input id="newTenantId" placeholder="Firma ID (ops.)" />
      <input id="newLimit" placeholder="Token limiti (ops.)" />
      <button id="createBtn" type="button">Kullanıcı Ekle</button>
    </div>
    <div id="summary" class="muted"></div>
    <table id="tbl" style="display:none;">
      <thead><tr><th>ID</th><th>Firma</th><th>Kullanıcı</th><th>Rol</th><th>Limit</th><th>Kullanilan</th><th>Aktif</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
  </div>
  <script>
    const username = document.getElementById('username');
    const password = document.getElementById('password');
    const rememberMe = document.getElementById('rememberMe');
    const tokenInfo = document.getElementById('tokenInfo');
    const loginBtn = document.getElementById('loginBtn');
    const reloadBtn = document.getElementById('reloadBtn');
    const createBtn = document.getElementById('createBtn');
    const summary = document.getElementById('summary');
    const activeProjectBadge = document.getElementById('activeProjectBadge');
    const tbl = document.getElementById('tbl');
    const tbody = tbl.querySelector('tbody');
    const newUsername = document.getElementById('newUsername');
    const newPassword = document.getElementById('newPassword');
    const newRole = document.getElementById('newRole');
    const newTenantId = document.getElementById('newTenantId');
    const newLimit = document.getElementById('newLimit');
    let token = localStorage.getItem('access_token') || '';
    const rememberedUsername = localStorage.getItem('remembered_username') || '';
    const rememberedEnabled = localStorage.getItem('remember_me') === '1';
    if (rememberedEnabled && rememberedUsername) {
      username.value = rememberedUsername;
      rememberMe.checked = true;
    }
    const loginOnEnter = (e) => { if (e.key === 'Enter') { e.preventDefault(); loginBtn.click(); } };
    username.addEventListener('keydown', loginOnEnter);
    password.addEventListener('keydown', loginOnEnter);
    const clearSessionCache = () => {
      const uiLang = localStorage.getItem('ui_lang') || '';
      localStorage.clear();
      sessionStorage.clear();
      if (uiLang) localStorage.setItem('ui_lang', uiLang);
    };
    const headers = () => ({ Authorization: `Bearer ${token}` });
    const renderProjectBadge = (user) => {
      if (!activeProjectBadge) return;
      const pName = user && user.active_project_name ? user.active_project_name : '-';
      const pCode = user && (user.active_project_code || (user.active_project_id ? `ID-${user.active_project_id}` : '-'));
      activeProjectBadge.textContent = `AKTİF PROJE: ${pName} (${pCode || '-'})`;
    };
    const renderTokenInfo = (user, tenantBalance) => {
      const personal = user && user.token_remaining != null ? user.token_remaining : 'SINIRSIZ';
      const firma = tenantBalance != null ? tenantBalance : '-';
      tokenInfo.textContent = `Kisisel Token: ${personal} | Firma Token: ${firma}`;
    };
    let profileBtn = null;
    let profileMenu = null;
    const closeProfileMenu = () => { if (profileMenu) profileMenu.style.display = 'none'; };
    const ensureProfileUi = () => {
      if (profileBtn) return;
      profileBtn = document.createElement('button');
      profileBtn.type = 'button';
      profileBtn.className = 'btn-muted';
      profileBtn.style.marginLeft = '6px';
      profileBtn.style.display = 'inline-flex';
      profileBtn.style.alignItems = 'center';
      profileBtn.style.gap = '6px';
      profileBtn.innerHTML = '<span style="width:18px;height:18px;border-radius:50%;background:#2b7fff;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;">U</span><span>PROFILE</span>';
      loginBtn.parentElement.appendChild(profileBtn);
      profileMenu = document.createElement('div');
      profileMenu.style.position = 'absolute';
      profileMenu.style.top = '46px';
      profileMenu.style.right = '8px';
      profileMenu.style.background = '#fff';
      profileMenu.style.border = '1px solid #dde4ef';
      profileMenu.style.borderRadius = '8px';
      profileMenu.style.padding = '10px';
      profileMenu.style.minWidth = '220px';
      profileMenu.style.display = 'none';
      profileMenu.style.boxShadow = '0 8px 20px rgba(0,0,0,0.08)';
      profileMenu.innerHTML = '<div id="pmUser" style="font-weight:700;"></div><div id="pmRole" class="muted" style="margin:4px 0 8px;"></div><button id="pmProfile" type="button">Profil Bilgileri</button> <button id="pmSettings" type="button" class="btn-muted">Ayarlar</button> <button id="pmLogout" type="button" style="background:#c62828;color:#fff;border:0;border-radius:8px;padding:8px 10px;margin-left:4px;">Çıkış</button>';
      loginBtn.parentElement.style.position = 'relative';
      loginBtn.parentElement.appendChild(profileMenu);
      profileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        profileMenu.style.display = profileMenu.style.display === 'none' ? 'block' : 'none';
      });
      document.addEventListener('click', (e) => {
        if (!profileMenu || profileMenu.style.display === 'none') return;
        if (!profileMenu.contains(e.target) && e.target !== profileBtn) closeProfileMenu();
      });
      const showPersonalQr = async () => {
        try {
          const res = await fetch('/auth/personal-qr', { headers: headers() });
          if (!res.ok) { alert('Karekod yüklenemedi.'); return; }
          const payload = res.headers.get('X-QR-Payload') || '-';
          const blob = await res.blob();
          const imgUrl = URL.createObjectURL(blob);
          const overlay = document.createElement('div');
          overlay.style.position = 'fixed';
          overlay.style.inset = '0';
          overlay.style.background = 'rgba(10,16,36,0.55)';
          overlay.style.display = 'flex';
          overlay.style.alignItems = 'center';
          overlay.style.justifyContent = 'center';
          overlay.style.zIndex = '1400';
          const card = document.createElement('div');
          card.style.background = '#fff';
          card.style.border = '1px solid #dde4ef';
          card.style.borderRadius = '12px';
          card.style.padding = '14px';
          card.style.minWidth = '320px';
          card.style.textAlign = 'center';
          card.innerHTML = `<div style="font-weight:700;margin-bottom:8px;">Kişisel Karekod</div><img src="${imgUrl}" alt="Kişisel Karekod" style="width:220px;height:220px;border:1px solid #e2e8f0;border-radius:8px;background:#fff;" /><div class="muted" style="margin-top:8px;word-break:break-all;">${payload}</div><div style="margin-top:10px;"><button id="closeQrBtn" type="button" class="btn-muted">Kapat</button></div>`;
          overlay.appendChild(card);
          document.body.appendChild(overlay);
          const close = () => { URL.revokeObjectURL(imgUrl); overlay.remove(); };
          overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
          card.querySelector('#closeQrBtn').addEventListener('click', close);
        } catch (_) {
          alert('Karekod yüklenemedi.');
        }
      };
      profileMenu.querySelector('#pmProfile').addEventListener('click', showPersonalQr);
      profileMenu.querySelector('#pmSettings').addEventListener('click', () => alert('Ayarlar paneli yakında eklenecek.'));
      profileMenu.querySelector('#pmLogout').addEventListener('click', () => {
        clearSessionCache();
        token = '';
        closeProfileMenu();
        applyAuthUi(null, null);
        summary.textContent = 'Çıkış yapildi.';
      });
    };
    const applyAuthUi = (user, tenantBalance) => {
      const loggedIn = !!(user && user.username);
      username.style.display = loggedIn ? 'none' : '';
      password.style.display = loggedIn ? 'none' : '';
      if (rememberMe && rememberMe.parentElement) rememberMe.parentElement.style.display = loggedIn ? 'none' : '';
      loginBtn.style.display = loggedIn ? 'none' : '';
      ensureProfileUi();
      profileBtn.style.display = loggedIn ? '' : 'none';
      if (loggedIn) {
        const initial = ((user.username || 'U').charAt(0) || 'U').toUpperCase();
        profileBtn.innerHTML = `<span style="width:18px;height:18px;border-radius:50%;background:#2b7fff;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;">${initial}</span><span>${user.username}</span>`;
        const pmUser = profileMenu.querySelector('#pmUser');
        const pmRole = profileMenu.querySelector('#pmRole');
        if (pmUser) pmUser.textContent = user.username;
        if (pmRole) pmRole.textContent = `Rol: ${user.role || '-'} | Firma: ${user.tenant_name || '-'}`;
        renderTokenInfo(user, tenantBalance);
        renderProjectBadge(user);
      } else {
        closeProfileMenu();
        tokenInfo.textContent = '';
        renderProjectBadge(null);
      }
    };
    const loadSessionInfo = async () => {
      if (!token) return;
      try {
        const res = await fetch('/auth/me', { headers: headers() });
        const data = await res.json();
        if (!res.ok) {
          clearSessionCache();
          token = '';
          summary.textContent = 'Oturum suresi dolmus, tekrar giris yapin.';
          return;
        }
        applyAuthUi(data, data.tenant_token_balance);
        renderProjectBadge(data);
        summary.textContent = `Oturum aktif: ${data.username}`;
      } catch (_) {}
    };
    applyAuthUi(null, null);
    loadSessionInfo();

    const load = async () => {
      if (!token) { summary.textContent = 'Once giris yapin.'; return; }
      const res = await fetch('/users', { headers: headers() });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Kullanıcılar alınamadı');
      tbody.innerHTML = '';
      (data || []).forEach(u => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${u.id}</td><td>${u.tenant_name || u.tenant_id || '-'}</td><td>${u.username}</td><td>${u.role}</td><td>${u.token_limit ?? ''}</td><td>${u.token_used ?? 0}</td><td>${u.is_active ? 'Evet':'Hayir'}</td>`;
        tbody.appendChild(tr);
      });
      tbl.style.display = '';
      summary.textContent = `${(data || []).length} kullanıcı listelendi.`;
    };

    loginBtn.addEventListener('click', async () => {
      try {
        const res = await fetch('/auth/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ username: username.value, password: password.value }) });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Giriş başarısız');
        clearSessionCache();
        token = data.access_token || '';
        localStorage.setItem('access_token', token);
        applyAuthUi(data.user || {}, data.tenant_token_balance);
        if (rememberMe.checked) {
          localStorage.setItem('remember_me', '1');
          localStorage.setItem('remembered_username', username.value || '');
        } else {
          localStorage.removeItem('remember_me');
          localStorage.removeItem('remembered_username');
        }
        await loadSessionInfo();
        await load();
      } catch (err) { summary.textContent = `Hata: ${err.message}`; }
    });

    createBtn.addEventListener('click', async () => {
      if (!token) { summary.textContent = 'Once giris yapin.'; return; }
      try {
        const payload = {
          username: newUsername.value || '',
          password: newPassword.value || '',
          role: newRole.value || 'tenant_operator'
        };
        if ((newTenantId.value || '').trim()) payload.tenant_id = parseInt(newTenantId.value, 10);
        if ((newLimit.value || '').trim()) payload.token_limit = parseInt(newLimit.value, 10);
        const res = await fetch('/users', { method:'POST', headers:{...headers(),'Content-Type':'application/json'}, body: JSON.stringify(payload) });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Kullanıcı oluşturulamadı');
        await load();
      } catch (err) { summary.textContent = `Hata: ${err.message}`; }
    });

    reloadBtn.addEventListener('click', async () => {
      try { await load(); } catch (err) { summary.textContent = `Hata: ${err.message}`; }
    });
  </script>  <div class="footer-brand" style="position:fixed;left:0;right:0;bottom:0;height:54px;background:#0A1024;display:flex;align-items:center;padding-left:12px;z-index:998;overflow:hidden;"><img src="/assets/kontrast-logo.png" alt="Creatro Logo" style="height:150%;width:auto;display:block;object-fit:cover;object-position:center;clip-path:inset(0 3% 0 0);" /><span class="logo-reg" style="color:#fff;font-size:12px;line-height:1;margin-left:0;font-weight:700;position:relative;left:-26px;transform:translateY(-45%);">&reg;</span></div>
</body>
</html>
"""


@app.get("/supplier-ui", response_class=HTMLResponse)
def supplier_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Araç Takip</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 16px; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); color: #1c2635; }
    .box { max-width: 1200px; margin: 0 auto; background: #fff; border: 1px solid #dde4ef; border-radius: 12px; padding: 16px; }
    .title { font-size: 22px; font-weight: 700; margin: 0 0 6px; }
    .muted { color: #5c6b82; font-size: 14px; }
    .row { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
    .input, .sel { border:1px solid #cfd9e8; border-radius:8px; padding:8px 10px; font-size:12px; min-width:180px; }
    .btn { border:0; border-radius:8px; background:#2b7fff; color:#fff; padding:8px 12px; cursor:pointer; }
    .btn.alt { background:#5c6b82; }
    table { width:100%; border-collapse: collapse; margin-top:10px; font-size:12px; }
    th, td { border:1px solid #dde4ef; padding:8px; text-align:left; }
    th { background:#f0f5ff; }
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
</head>
<body>
  <div class="box">
    <div class="title">Araç Takip</div>
    <div class="muted">Araç firmaları için proje kaynaklı ve harici müşteriler burada takip edilir.</div>
    <div class="row">
      <select id="companySel" class="sel"></select>
      <select id="sourceSel" class="sel"><option value="external">Harici</option><option value="project">Proje</option></select>
      <input id="projectId" class="input" placeholder="Proje ID (project için)" />
      <input id="fullName" class="input" placeholder="Müşteri Ad Soyad" />
      <input id="phone" class="input" placeholder="Telefon" />
      <input id="email" class="input" placeholder="E-posta" />
      <input id="notes" class="input" placeholder="Not" style="min-width:260px;" />
      <button id="addBtn" class="btn" type="button">Müşteri Ekle</button>
    </div>
    <div class="row"><select id="filterSource" class="sel"><option value="">Tümü</option><option value="external">Harici</option><option value="project">Proje</option></select><button id="refreshBtn" class="btn alt" type="button">Listeyi Yenile</button><a href="/supplier-transfers-ui" class="btn" style="text-decoration:none;display:inline-block;">Araç Takip Operasyon</a></div>
    <hr style="margin:14px 0; border:0; border-top:1px solid #e2e8f0;" />
    <div class="muted"><b>Arvento Polling Ayarları</b> (doküman gelince endpoint ve auth netleştirilecek)</div>
    <div class="row">
      <input id="trkBaseUrl" class="input" placeholder="Base URL (örn: https://...)" style="min-width:260px;" />
      <input id="trkEndpoint" class="input" placeholder="Araç endpoint (örn: /api/vehicles)" style="min-width:240px;" />
      <select id="trkAuthType" class="sel"><option value="bearer">Bearer</option><option value="basic">Basic</option></select>
      <input id="trkToken" class="input" placeholder="Token (bearer)" style="min-width:220px;" />
      <input id="trkUser" class="input" placeholder="Kullanıcı (basic)" />
      <input id="trkPass" class="input" placeholder="Şifre (basic)" type="password" />
      <input id="trkPollSec" class="input" placeholder="Poll sn (vars. 30)" style="min-width:140px;" />
      <label class="muted" style="display:flex;align-items:center;gap:6px;"><input id="trkEnabled" type="checkbox" /> Aktif</label>
      <button id="trkSaveBtn" class="btn" type="button">Ayarı Kaydet</button>
      <button id="trkPollBtn" class="btn alt" type="button">Şimdi Poll Et</button>
      <button id="trkRefreshBtn" class="btn alt" type="button">Canlıyı Yenile</button>
    </div>
    <table id="trkTbl" style="display:none;">
      <thead><tr><th>PLAKA</th><th>LAT</th><th>LON</th><th>HIZ</th><th>ZAMAN</th><th>TRANSFER ID</th></tr></thead>
      <tbody></tbody>
    </table>
    <div id="summary" class="muted"></div>
    <table id="tbl" style="display:none;"><thead><tr><th>ID</th><th>Firma</th><th>KAYNAK</th><th>Proje</th><th>Müşteri</th><th>Telefon</th><th>E-posta</th><th>Durum</th><th>Not</th></tr></thead><tbody></tbody></table>
  </div>
  <script>
    const token = localStorage.getItem('access_token') || '';
    const headers = () => ({ Authorization: `Bearer ${token}` });
    const companySel = document.getElementById('companySel');
    const sourceSel = document.getElementById('sourceSel');
    const projectId = document.getElementById('projectId');
    const fullName = document.getElementById('fullName');
    const phone = document.getElementById('phone');
    const email = document.getElementById('email');
    const notes = document.getElementById('notes');
    const addBtn = document.getElementById('addBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    const filterSource = document.getElementById('filterSource');
    const summary = document.getElementById('summary');
    const tbl = document.getElementById('tbl');
    const tbody = tbl.querySelector('tbody');
    const trkBaseUrl = document.getElementById('trkBaseUrl');
    const trkEndpoint = document.getElementById('trkEndpoint');
    const trkAuthType = document.getElementById('trkAuthType');
    const trkToken = document.getElementById('trkToken');
    const trkUser = document.getElementById('trkUser');
    const trkPass = document.getElementById('trkPass');
    const trkPollSec = document.getElementById('trkPollSec');
    const trkEnabled = document.getElementById('trkEnabled');
    const trkSaveBtn = document.getElementById('trkSaveBtn');
    const trkPollBtn = document.getElementById('trkPollBtn');
    const trkRefreshBtn = document.getElementById('trkRefreshBtn');
    const trkTbl = document.getElementById('trkTbl');
    const trkBody = trkTbl.querySelector('tbody');
    let companies = [];
    const loadCompanies = async () => { const res = await fetch('/supplier-companies', { headers: headers() }); const data = await res.json(); if (!res.ok) throw new Error(data.detail || 'Firmalar alınamadı'); companies = Array.isArray(data) ? data : []; companySel.innerHTML = companies.map(c => `<option value="${c.id}">${c.name}</option>`).join(''); };
    const companyName = (id) => { const f = companies.find(c => String(c.id) === String(id)); return f ? f.name : String(id || '-'); };
    const loadClients = async () => { const qs = new URLSearchParams(); if (companySel.value) qs.set('supplier_company_id', companySel.value); if (filterSource.value) qs.set('source_type', filterSource.value); const res = await fetch('/supplier-clients?' + qs.toString(), { headers: headers() }); const data = await res.json(); if (!res.ok) throw new Error(data.detail || 'Müşteriler alınamadı'); const rows = Array.isArray(data) ? data : []; tbody.innerHTML = rows.map(r => `<tr><td>${r.id}</td><td>${companyName(r.supplier_company_id)}</td><td>${r.source_type}</td><td>${r.project_id || '-'}</td><td>${r.full_name || ''}</td><td>${r.phone || ''}</td><td>${r.email || ''}</td><td>${r.status || ''}</td><td>${r.notes || ''}</td></tr>`).join(''); tbl.style.display = rows.length ? '' : 'none'; summary.textContent = `${rows.length} müşteri listelendi.`; };
    const loadTrackingConfig = async () => {
      if (!companySel.value) return;
      const res = await fetch(`/supplier-tracking-config?supplier_company_id=${encodeURIComponent(companySel.value)}`, { headers: headers() });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Takip ayarı alınamadı');
      const c = data.config || {};
      trkBaseUrl.value = c.base_url || '';
      trkEndpoint.value = c.vehicles_endpoint || '';
      trkAuthType.value = c.auth_type || 'bearer';
      trkToken.value = '';
      trkPass.value = '';
      trkUser.value = c.username || '';
      trkPollSec.value = String(c.poll_interval_sec || 30);
      trkEnabled.checked = !!c.enabled;
    };
    const loadTrackingLive = async () => {
      if (!companySel.value) return;
      const res = await fetch(`/supplier-tracking/live?supplier_company_id=${encodeURIComponent(companySel.value)}`, { headers: headers() });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Canlı takip alınamadı');
      const rows = Array.isArray(data.items) ? data.items : [];
      trkBody.innerHTML = rows.map(r => `<tr><td>${r.plate || ''}</td><td>${r.lat ?? ''}</td><td>${r.lon ?? ''}</td><td>${r.speed ?? ''}</td><td>${r.timestamp || ''}</td><td>${Array.isArray(r.transfer_ids) ? r.transfer_ids.join(', ') : ''}</td></tr>`).join('');
      trkTbl.style.display = rows.length ? '' : 'none';
      if (data.fetched_at) summary.textContent = `Araç takip güncellendi: ${data.fetched_at} (${rows.length} araç).`;
    };
    addBtn.addEventListener('click', async () => { try { const payload = { supplier_company_id: Number(companySel.value || 0), source_type: sourceSel.value || 'external', full_name: fullName.value || '', phone: phone.value || '', email: email.value || '', notes: notes.value || '', status: 'active' }; if (payload.source_type === 'project' && (projectId.value || '').trim()) payload.project_id = Number(projectId.value); const res = await fetch('/supplier-clients', { method:'POST', headers: { ...headers(), 'Content-Type':'application/json' }, body: JSON.stringify(payload) }); const data = await res.json(); if (!res.ok) throw new Error(data.detail || 'Kayıt eklenemedi'); fullName.value=''; phone.value=''; email.value=''; notes.value=''; projectId.value=''; await loadClients(); } catch (err) { summary.textContent = `Hata: ${err.message}`; } });
    trkSaveBtn.addEventListener('click', async () => {
      try {
        const payload = {
          supplier_company_id: Number(companySel.value || 0),
          provider: 'arvento',
          enabled: !!trkEnabled.checked,
          base_url: trkBaseUrl.value || '',
          vehicles_endpoint: trkEndpoint.value || '',
          auth_type: trkAuthType.value || 'bearer',
          username: trkUser.value || '',
          token: trkToken.value || '',
          password: trkPass.value || '',
          poll_interval_sec: Number(trkPollSec.value || 30)
        };
        const res = await fetch('/supplier-tracking-config', { method:'PUT', headers: { ...headers(), 'Content-Type':'application/json' }, body: JSON.stringify(payload) });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Takip ayarı kaydedilemedi');
        summary.textContent = 'Araç takip ayarı kaydedildi.';
      } catch (err) { summary.textContent = `Hata: ${err.message}`; }
    });
    trkPollBtn.addEventListener('click', async () => {
      try {
        const payload = { supplier_company_id: Number(companySel.value || 0) };
        const res = await fetch('/supplier-tracking/poll', { method:'POST', headers: { ...headers(), 'Content-Type':'application/json' }, body: JSON.stringify(payload) });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Poll işlemi başarısız');
        await loadTrackingLive();
      } catch (err) { summary.textContent = `Hata: ${err.message}`; }
    });
    trkRefreshBtn.addEventListener('click', () => loadTrackingLive().catch(err => { summary.textContent = `Hata: ${err.message}`; }));
    refreshBtn.addEventListener('click', () => loadClients().catch(err => { summary.textContent = `Hata: ${err.message}`; }));
    filterSource.addEventListener('change', () => loadClients().catch(err => { summary.textContent = `Hata: ${err.message}`; }));
    companySel.addEventListener('change', async () => {
      try {
        await loadClients();
        await loadTrackingConfig();
        await loadTrackingLive();
      } catch (err) { summary.textContent = `Hata: ${err.message}`; }
    });
    (async () => { if (!token) { window.location.href = '/'; return; } try { await loadCompanies(); await loadClients(); await loadTrackingConfig(); await loadTrackingLive(); } catch (err) { summary.textContent = `Hata: ${err.message}`; } })();
  </script>
</body>
</html>
"""
@app.get("/transfer-list-ui", response_class=HTMLResponse)
def transfer_list_ui():
    return """
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Transfer Listesi</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 18px; background: linear-gradient(135deg, #e6eefc 0%, #dbe7fb 48%, #edf3ff 100%); background-attachment: fixed; color: #1c2635; }
    .box { background:#fff; border:1px solid #dde4ef; border-radius:12px; padding:16px; }
    .row { display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }
    .btn { background:#2b7fff; color:#fff; border:0; border-radius:8px; padding:8px 12px; cursor:pointer; text-decoration:none; }
    .sel { border:1px solid #cfd9e8; border-radius:8px; padding:8px 10px; font-size:12px; }
    .muted { color:#5c6b82; font-size:13px; margin-top:8px; }
    table { width:100%; border-collapse: collapse; margin-top: 12px; font-size:12px; }
    th, td { border:1px solid #dde4ef; padding:7px; text-align:left; vertical-align: top; }
    th { background:#f0f5ff; }
    @media print {
      body { margin: 0; background: #fff !important; }
      .box { border: 0; border-radius: 0; padding: 0; }
      .row, #summary, h3, #printBtn, .footer-brand { display: none !important; }
      #transferTable { display: table !important; margin-top: 0; }
      table, th, td { color: #000; }
    }
  
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style>
</head>
<body>
  <div class="box">
    <h3 style="margin:0;">Transfer Listesi</h3>
    <div class="row">
      <button id="refreshBtn" class="btn" type="button">Listeyi Yenile</button>
      <button id="printBtn" class="btn" type="button">Print</button>
      <a class="btn" href="/upload-ui" target="_top">İçeri Aktar</a>
      <select id="exportFormat" class="sel">
        <option value="pdf">PDF</option>
        <option value="xlsx">XLSX</option>
        <option value="csv">CSV</option>
      </select>
      <button id="exportBtn" class="btn" type="button">Dışarı Aktar</button>
    </div>
    <div id="summary" class="muted"></div>
    <table id="transferTable" style="display:none;">
      <thead><tr><th>ID</th><th>YOLCU</th><th>CİNSİYET</th><th>PNR</th><th>DÜZENLENME TARİHİ</th><th>UÇUŞ ŞEKLİ</th><th>UÇUŞ KODU</th><th>ROTA</th><th>KALKIŞ TARİHİ-SAATİ</th><th>İNİŞ TARİHİ-SAATİ</th><th>KARŞILAMA SAATİ</th><th>TRANSFER NOKTASI</th><th>ARAÇ KODU</th><th>DÜZENLE</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
  <script>
    const refreshBtn = document.getElementById('refreshBtn');
    const printBtn = document.getElementById('printBtn');
    const exportBtn = document.getElementById('exportBtn');
    const exportFormat = document.getElementById('exportFormat');
    const summary = document.getElementById('summary');
    const transferTable = document.getElementById('transferTable');
    const transferBody = transferTable.querySelector('tbody');
    const token = localStorage.getItem('access_token') || '';
    const authHeaders = () => ({ 'Authorization': `Bearer ${token}` });
    const norm = (v) => String(v || '').trim().toLocaleUpperCase('tr-TR').replace(/\\s+/g, ' ');
    const showLoading = (text) => {
      if (loadingText) loadingText.textContent = text || 'Yükleniyor...';
      if (loadingOverlay) loadingOverlay.style.display = 'flex';
    };
    const hideLoading = () => {
      if (loadingOverlay) loadingOverlay.style.display = 'none';
    };
    const showRefreshPopup = (text) => {
      if (refreshPopupText) refreshPopupText.textContent = text || 'Dosyalar yüklendi.';
      if (refreshPopup) refreshPopup.style.display = 'flex';
    };
    const hideRefreshPopup = () => {
      if (refreshPopup) refreshPopup.style.display = 'none';
    };
    const routePair = (r) => {
      const raw = String(r?.from_to || '').trim();
      if (raw.includes('/')) {
        const parts = raw.split('/');
        return [norm(parts[0]), norm(parts[1])];
      }
      return [norm(r?.from || ''), norm(r?.to || '')];
    };
    const renderStagedTable = () => {
      tbody.innerHTML = '';
      stagedUploads.forEach((r, idx) => {
        const tr = document.createElement('tr');
        tr.setAttribute('data-idx', String(idx));
        tr.innerHTML = `<td><button type="button" class="btn-small btn-green row-save">Kaydet</button></td><td>${r.original_filename || ''}</td><td>${r.upload_id || ''}</td><td>${r.status || ''}</td><td data-field="passenger_name" contenteditable="true">${r.passenger_name || ''}</td><td data-field="pnr" contenteditable="true">${r.pnr || ''}</td><td>${r.flight_no || ''}</td><td>${r.from_to || ''}</td><td data-field="pickup_time" contenteditable="true">${r.pickup_time || ''}</td><td data-field="transfer_point" contenteditable="true">${r.transfer_point || ''}</td><td data-field="vehicle_code" contenteditable="true">${r.vehicle_code || ''}</td><td>${r.note || ''}</td>`;
        tbody.appendChild(tr);
      });
      table.style.display = stagedUploads.length ? '' : 'none';
    };
    const fetchProjectTransfers = async () => {
      const listRes = await fetch(`/transfers?project_id=${encodeURIComponent(String(me.active_project_id))}&limit=5000`, { headers: authHeaders() });
      const listData = await listRes.json();
      if (!listRes.ok) throw new Error(listData.detail || 'Transfer listesi alınamadı');
      transferRowsCache = Array.isArray(listData) ? listData : [];
      return transferRowsCache;
    };
    const findDuplicateReason = (baseRow, passengerName, pnrValue) => {
      const passengerN = norm(passengerName);
      const pnrN = norm(pnrValue);
      const flightN = norm(baseRow.flight_no);
      const [fromN, toN] = routePair(baseRow);
      for (const item of transferRowsCache) {
        if (!item || !item.id || Number(item.id) === Number(baseRow.id)) continue;
        if (norm(item.passenger_name) !== passengerN) continue;
        const samePnrFlight = !!pnrN && !!flightN && norm(item.pnr) === pnrN && norm(item.flight_no) === flightN;
        const [ifrom, ito] = routePair(item);
        const sameRoute = !!fromN && !!toN && ifrom === fromN && ito === toN;
        if (samePnrFlight) return 'Aynı Passenger + PNR + Uçuş Kodu zaten var.';
        if (sameRoute) return 'Aynı Passenger + Rota zaten var.';
      }
      return '';
    };
    const saveStagedRow = async (idx, navigateAfter = true) => {
      if (idx < 0 || idx >= stagedUploads.length) return { ok: false, message: 'Geçersiz satır.' };
      const s = stagedUploads[idx];
      if (!s.upload_id) return { ok: false, message: 'Upload ID bulunamadı.' };
      if (!transferRowsCache.length) await fetchProjectTransfers();
      const matched = transferRowsCache.filter(t => String(t.upload_id || '') === String(s.upload_id));
      const trf = matched.length ? matched[0] : null;
      if (!trf || !trf.id) return { ok: false, message: 'Bu dosya henüz işlenmemiş. Biraz sonra tekrar deneyin.' };
      const passenger = (s.passenger_name || trf.passenger_name || '').trim();
      const pnr = (s.pnr || trf.pnr || '').trim();
      const dupReason = findDuplicateReason(trf, passenger, pnr);
      if (dupReason) return { ok: false, message: dupReason };
      const payload = {
        project_id: me.active_project_id,
        passenger_name: passenger || null,
        pnr: pnr || null,
        pickup_time: (s.pickup_time || '').trim() || null,
        transfer_point: (s.transfer_point || '').trim() || null,
        vehicle_code: (s.vehicle_code || '').trim() || null
      };
      const updRes = await fetch(`/transfers/${trf.id}`, {
        method: 'PUT',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const updData = await updRes.json().catch(() => ({}));
      if (!updRes.ok) return { ok: false, message: updData.detail || 'Kaydetme hatası.' };
      stagedUploads.splice(idx, 1);
      renderStagedTable();
      summary.textContent = `Satır kaydedildi: ${passenger || '-'}`;
      if (navigateAfter) window.location.href = '/transfer-list-ui';
      return { ok: true };
    };
    const norm = (v) => String(v || '').trim().toLocaleUpperCase('tr-TR').replace(/\\s+/g, ' ');
    const showLoading = (text) => {
      if (loadingText) loadingText.textContent = text || 'Yükleniyor...';
      if (loadingOverlay) loadingOverlay.style.display = 'flex';
    };
    const hideLoading = () => {
      if (loadingOverlay) loadingOverlay.style.display = 'none';
    };
    const showRefreshPopup = (text) => {
      if (refreshPopupText) refreshPopupText.textContent = text || 'Dosyalar yüklendi.';
      if (refreshPopup) refreshPopup.style.display = 'flex';
    };
    const hideRefreshPopup = () => {
      if (refreshPopup) refreshPopup.style.display = 'none';
    };
    const routePair = (r) => {
      const raw = String(r?.from_to || '').trim();
      if (raw.includes('/')) {
        const parts = raw.split('/');
        return [norm(parts[0]), norm(parts[1])];
      }
      return [norm(r?.from || ''), norm(r?.to || '')];
    };
    const renderStagedTable = () => {
      tbody.innerHTML = '';
      stagedUploads.forEach((r, idx) => {
        const tr = document.createElement('tr');
        tr.setAttribute('data-idx', String(idx));
        tr.innerHTML = `<td><button type="button" class="btn-small btn-green row-save">Kaydet</button></td><td>${r.original_filename || ''}</td><td>${r.upload_id || ''}</td><td>${r.status || ''}</td><td data-field="passenger_name" contenteditable="true">${r.passenger_name || ''}</td><td data-field="pnr" contenteditable="true">${r.pnr || ''}</td><td>${r.flight_no || ''}</td><td>${r.from_to || ''}</td><td data-field="pickup_time" contenteditable="true">${r.pickup_time || ''}</td><td data-field="transfer_point" contenteditable="true">${r.transfer_point || ''}</td><td data-field="vehicle_code" contenteditable="true">${r.vehicle_code || ''}</td><td>${r.note || ''}</td>`;
        tbody.appendChild(tr);
      });
      table.style.display = stagedUploads.length ? '' : 'none';
    };
    const fetchProjectTransfers = async () => {
      const listRes = await fetch(`/transfers?project_id=${encodeURIComponent(String(me.active_project_id))}&limit=5000`, { headers: authHeaders() });
      const listData = await listRes.json();
      if (!listRes.ok) throw new Error(listData.detail || 'Transfer listesi alınamadı');
      transferRowsCache = Array.isArray(listData) ? listData : [];
      return transferRowsCache;
    };
    const findDuplicateReason = (baseRow, passengerName, pnrValue) => {
      const passengerN = norm(passengerName);
      const pnrN = norm(pnrValue);
      const flightN = norm(baseRow.flight_no);
      const [fromN, toN] = routePair(baseRow);
      for (const item of transferRowsCache) {
        if (!item || !item.id || Number(item.id) === Number(baseRow.id)) continue;
        if (norm(item.passenger_name) !== passengerN) continue;
        const samePnrFlight = !!pnrN && !!flightN && norm(item.pnr) === pnrN && norm(item.flight_no) === flightN;
        const [ifrom, ito] = routePair(item);
        const sameRoute = !!fromN && !!toN && ifrom === fromN && ito === toN;
        if (samePnrFlight) return 'Aynı Passenger + PNR + Uçuş Kodu zaten var.';
        if (sameRoute) return 'Aynı Passenger + Rota zaten var.';
      }
      return '';
    };
    const saveStagedRow = async (idx, navigateAfter = true) => {
      if (idx < 0 || idx >= stagedUploads.length) return { ok: false, message: 'Geçersiz satır.' };
      const s = stagedUploads[idx];
      if (!s.upload_id) return { ok: false, message: 'Upload ID bulunamadı.' };
      if (!transferRowsCache.length) await fetchProjectTransfers();
      const matched = transferRowsCache.filter(t => String(t.upload_id || '') === String(s.upload_id));
      const trf = matched.length ? matched[0] : null;
      if (!trf || !trf.id) return { ok: false, message: 'Bu dosya henüz işlenmemiş. Biraz sonra tekrar deneyin.' };
      const passenger = (s.passenger_name || trf.passenger_name || '').trim();
      const pnr = (s.pnr || trf.pnr || '').trim();
      const dupReason = findDuplicateReason(trf, passenger, pnr);
      if (dupReason) return { ok: false, message: dupReason };
      const payload = {
        project_id: me.active_project_id,
        passenger_name: passenger || null,
        pnr: pnr || null,
        pickup_time: (s.pickup_time || '').trim() || null,
        transfer_point: (s.transfer_point || '').trim() || null,
        vehicle_code: (s.vehicle_code || '').trim() || null
      };
      const updRes = await fetch(`/transfers/${trf.id}`, {
        method: 'PUT',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const updData = await updRes.json().catch(() => ({}));
      if (!updRes.ok) return { ok: false, message: updData.detail || 'Kaydetme hatası.' };
      stagedUploads.splice(idx, 1);
      renderStagedTable();
      summary.textContent = `Satır kaydedildi: ${passenger || '-'}`;
      if (navigateAfter) window.location.href = '/transfer-list-ui';
      return { ok: true };
    };
    const norm = (v) => String(v || '').trim().toLocaleUpperCase('tr-TR').replace(/\\s+/g, ' ');
    const showLoading = (text) => {
      if (loadingText) loadingText.textContent = text || 'Yükleniyor...';
      if (loadingOverlay) loadingOverlay.style.display = 'flex';
    };
    const hideLoading = () => {
      if (loadingOverlay) loadingOverlay.style.display = 'none';
    };
    const showRefreshPopup = (text) => {
      if (refreshPopupText) refreshPopupText.textContent = text || 'Dosyalar yüklendi.';
      if (refreshPopup) refreshPopup.style.display = 'flex';
    };
    const hideRefreshPopup = () => {
      if (refreshPopup) refreshPopup.style.display = 'none';
    };
    const routePair = (r) => {
      const raw = String(r?.from_to || '').trim();
      if (raw.includes('/')) {
        const parts = raw.split('/');
        return [norm(parts[0]), norm(parts[1])];
      }
      return [norm(r?.from || ''), norm(r?.to || '')];
    };
    const renderStagedTable = () => {
      tbody.innerHTML = '';
      stagedUploads.forEach((r, idx) => {
        const tr = document.createElement('tr');
        tr.setAttribute('data-idx', String(idx));
        tr.innerHTML = `<td><button type="button" class="btn-small btn-green row-save">Kaydet</button></td><td>${r.original_filename || ''}</td><td>${r.upload_id || ''}</td><td>${r.status || ''}</td><td data-field="passenger_name" contenteditable="true">${r.passenger_name || ''}</td><td data-field="pnr" contenteditable="true">${r.pnr || ''}</td><td>${r.flight_no || ''}</td><td>${r.from_to || ''}</td><td data-field="pickup_time" contenteditable="true">${r.pickup_time || ''}</td><td data-field="transfer_point" contenteditable="true">${r.transfer_point || ''}</td><td data-field="vehicle_code" contenteditable="true">${r.vehicle_code || ''}</td><td>${r.note || ''}</td>`;
        tbody.appendChild(tr);
      });
      table.style.display = stagedUploads.length ? '' : 'none';
    };
    const fetchProjectTransfers = async () => {
      const listRes = await fetch(`/transfers?project_id=${encodeURIComponent(String(me.active_project_id))}&limit=5000`, { headers: authHeaders() });
      const listData = await listRes.json();
      if (!listRes.ok) throw new Error(listData.detail || 'Transfer listesi alınamadı');
      transferRowsCache = Array.isArray(listData) ? listData : [];
      return transferRowsCache;
    };
    const findDuplicateReason = (baseRow, passengerName, pnrValue) => {
      const passengerN = norm(passengerName);
      const pnrN = norm(pnrValue);
      const flightN = norm(baseRow.flight_no);
      const [fromN, toN] = routePair(baseRow);
      for (const item of transferRowsCache) {
        if (!item || !item.id || Number(item.id) === Number(baseRow.id)) continue;
        if (norm(item.passenger_name) !== passengerN) continue;
        const samePnrFlight = !!pnrN && !!flightN && norm(item.pnr) === pnrN && norm(item.flight_no) === flightN;
        const [ifrom, ito] = routePair(item);
        const sameRoute = !!fromN && !!toN && ifrom === fromN && ito === toN;
        if (samePnrFlight) return 'Aynı Passenger + PNR + Uçuş Kodu zaten var.';
        if (sameRoute) return 'Aynı Passenger + Rota zaten var.';
      }
      return '';
    };
    const saveStagedRow = async (idx, navigateAfter = true) => {
      if (idx < 0 || idx >= stagedUploads.length) return { ok: false, message: 'Geçersiz satır.' };
      const s = stagedUploads[idx];
      if (!s.upload_id) return { ok: false, message: 'Upload ID bulunamadı.' };
      if (!transferRowsCache.length) await fetchProjectTransfers();
      const matched = transferRowsCache.filter(t => String(t.upload_id || '') === String(s.upload_id));
      const trf = matched.length ? matched[0] : null;
      if (!trf || !trf.id) return { ok: false, message: 'Bu dosya henüz işlenmemiş. Biraz sonra tekrar deneyin.' };
      const passenger = (s.passenger_name || trf.passenger_name || '').trim();
      const pnr = (s.pnr || trf.pnr || '').trim();
      const dupReason = findDuplicateReason(trf, passenger, pnr);
      if (dupReason) return { ok: false, message: dupReason };
      const payload = {
        project_id: me.active_project_id,
        passenger_name: passenger || null,
        pnr: pnr || null,
        pickup_time: (s.pickup_time || '').trim() || null,
        transfer_point: (s.transfer_point || '').trim() || null,
        vehicle_code: (s.vehicle_code || '').trim() || null
      };
      const updRes = await fetch(`/transfers/${trf.id}`, {
        method: 'PUT',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const updData = await updRes.json().catch(() => ({}));
      if (!updRes.ok) return { ok: false, message: updData.detail || 'Kaydetme hatası.' };
      stagedUploads.splice(idx, 1);
      renderStagedTable();
      summary.textContent = `Satır kaydedildi: ${passenger || '-'}`;
      if (navigateAfter) window.location.href = '/transfer-list-ui';
      return { ok: true };
    };
    const norm = (v) => String(v || '').trim().toLocaleUpperCase('tr-TR').replace(/\\s+/g, ' ');
    const showLoading = (text) => {
      if (loadingText) loadingText.textContent = text || 'Yükleniyor...';
      if (loadingOverlay) loadingOverlay.style.display = 'flex';
    };
    const hideLoading = () => {
      if (loadingOverlay) loadingOverlay.style.display = 'none';
    };
    const showRefreshPopup = (text) => {
      if (refreshPopupText) refreshPopupText.textContent = text || 'Dosyalar yüklendi.';
      if (refreshPopup) refreshPopup.style.display = 'flex';
    };
    const hideRefreshPopup = () => {
      if (refreshPopup) refreshPopup.style.display = 'none';
    };
    const routePair = (r) => {
      const raw = String(r?.from_to || '').trim();
      if (raw.includes('/')) {
        const parts = raw.split('/');
        return [norm(parts[0]), norm(parts[1])];
      }
      return [norm(r?.from || ''), norm(r?.to || '')];
    };
    const renderStagedTable = () => {
      tbody.innerHTML = '';
      stagedUploads.forEach((r, idx) => {
        const tr = document.createElement('tr');
        tr.setAttribute('data-idx', String(idx));
        tr.innerHTML = `<td><button type="button" class="btn-small btn-green row-save">Kaydet</button></td><td>${r.original_filename || ''}</td><td>${r.upload_id || ''}</td><td>${r.status || ''}</td><td data-field="passenger_name" contenteditable="true">${r.passenger_name || ''}</td><td data-field="pnr" contenteditable="true">${r.pnr || ''}</td><td>${r.flight_no || ''}</td><td>${r.from_to || ''}</td><td data-field="pickup_time" contenteditable="true">${r.pickup_time || ''}</td><td data-field="transfer_point" contenteditable="true">${r.transfer_point || ''}</td><td data-field="vehicle_code" contenteditable="true">${r.vehicle_code || ''}</td><td>${r.note || ''}</td>`;
        tbody.appendChild(tr);
      });
      table.style.display = stagedUploads.length ? '' : 'none';
    };
    const fetchProjectTransfers = async () => {
      const listRes = await fetch(`/transfers?project_id=${encodeURIComponent(String(me.active_project_id))}&limit=5000`, { headers: authHeaders() });
      const listData = await listRes.json();
      if (!listRes.ok) throw new Error(listData.detail || 'Transfer listesi alınamadı');
      transferRowsCache = Array.isArray(listData) ? listData : [];
      return transferRowsCache;
    };
    const findDuplicateReason = (baseRow, passengerName, pnrValue) => {
      const passengerN = norm(passengerName);
      const pnrN = norm(pnrValue);
      const flightN = norm(baseRow.flight_no);
      const [fromN, toN] = routePair(baseRow);
      for (const item of transferRowsCache) {
        if (!item || !item.id || Number(item.id) === Number(baseRow.id)) continue;
        if (norm(item.passenger_name) !== passengerN) continue;
        const samePnrFlight = !!pnrN && !!flightN && norm(item.pnr) === pnrN && norm(item.flight_no) === flightN;
        const [ifrom, ito] = routePair(item);
        const sameRoute = !!fromN && !!toN && ifrom === fromN && ito === toN;
        if (samePnrFlight) return 'Aynı Passenger + PNR + Uçuş Kodu zaten var.';
        if (sameRoute) return 'Aynı Passenger + Rota zaten var.';
      }
      return '';
    };
    const saveStagedRow = async (idx, navigateAfter = true) => {
      if (idx < 0 || idx >= stagedUploads.length) return { ok: false, message: 'Geçersiz satır.' };
      const s = stagedUploads[idx];
      if (!s.upload_id) return { ok: false, message: 'Upload ID bulunamadı.' };
      if (!transferRowsCache.length) await fetchProjectTransfers();
      const matched = transferRowsCache.filter(t => String(t.upload_id || '') === String(s.upload_id));
      const trf = matched.length ? matched[0] : null;
      if (!trf || !trf.id) return { ok: false, message: 'Bu dosya henüz işlenmemiş. Biraz sonra tekrar deneyin.' };
      const passenger = (s.passenger_name || trf.passenger_name || '').trim();
      const pnr = (s.pnr || trf.pnr || '').trim();
      const dupReason = findDuplicateReason(trf, passenger, pnr);
      if (dupReason) return { ok: false, message: dupReason };
      const payload = {
        project_id: me.active_project_id,
        passenger_name: passenger || null,
        pnr: pnr || null,
        pickup_time: (s.pickup_time || '').trim() || null,
        transfer_point: (s.transfer_point || '').trim() || null,
        vehicle_code: (s.vehicle_code || '').trim() || null
      };
      const updRes = await fetch(`/transfers/${trf.id}`, {
        method: 'PUT',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const updData = await updRes.json().catch(() => ({}));
      if (!updRes.ok) return { ok: false, message: updData.detail || 'Kaydetme hatası.' };
      stagedUploads.splice(idx, 1);
      renderStagedTable();
      summary.textContent = `Satır kaydedildi: ${passenger || '-'}`;
      if (navigateAfter) window.location.href = '/transfer-list-ui';
      return { ok: true };
    };
    let me = null;
    let loadedTransfers = [];

    const ensureActiveProject = async () => {
      if (!token) { window.location.href = '/'; return false; }
      const res = await fetch('/auth/me', { headers: authHeaders() });
      const data = await res.json();
      if (!res.ok) { localStorage.removeItem('access_token'); window.location.href = '/'; return false; }
      me = data;
      if (!data.active_project_id) { window.location.href = '/project-select-ui'; return false; }
      return true;
    };

    const loadTransfers = async () => {
      if (!(await ensureActiveProject())) return;
      summary.textContent = 'Transfer listesi aliniyor...';
      transferBody.innerHTML = '';
      try {
        const url = `/transfers?project_id=${encodeURIComponent(String(me.active_project_id))}`;
        const res = await fetch(url, { headers: authHeaders() });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Liste alınamadı');
        loadedTransfers = Array.isArray(data) ? data : [];
        (loadedTransfers || []).forEach(t => {
          const tr = document.createElement('tr');
          tr.setAttribute('data-id', String(t.id ?? ''));
          tr.innerHTML = `<td>${t.id ?? ''}</td><td data-field="passenger_name" contenteditable="true">${t.passenger_name ?? ''}</td><td>${t.cinsiyet ?? ''}</td><td data-field="pnr" contenteditable="true">${t.pnr ?? ''}</td><td data-field="issue_date" contenteditable="true">${t.duzenlenme_tarihi ?? ''}</td><td>${t.ucus_sekli ?? ''}</td><td>${t.flight_no ?? ''}</td><td>${t.from_to ?? ''}</td><td>${t.kalkis_tarihi_saati ?? ''}</td><td>${t.inis_tarihi_saati ?? ''}</td><td data-field="pickup_time" contenteditable="true">${t.pickup_time ?? ''}</td><td data-field="transfer_point" contenteditable="true">${t.transfer_noktasi ?? ''}</td><td data-field="vehicle_code" contenteditable="true">${t.arac_kod ?? ''}</td><td><button type="button" class="btn save-row" style="padding:6px 9px;">Kaydet</button></td>`;
          transferBody.appendChild(tr);
        });
        transferTable.style.display = '';
        summary.textContent = `${(loadedTransfers || []).length} transfer listelendi.`;
      } catch (err) {
        summary.textContent = `Hata: ${err.message}`;
      }
    };

    refreshBtn.addEventListener('click', loadTransfers);
    transferBody.addEventListener('click', async (e) => {
      const btn = e.target.closest('.save-row');
      if (!btn) return;
      const tr = btn.closest('tr');
      if (!tr) return;
      const id = parseInt(tr.getAttribute('data-id') || '0', 10);
      if (!id) return;
      const getCell = (field) => {
        const el = tr.querySelector(`[data-field="${field}"]`);
        return (el ? el.textContent : '')?.trim() || null;
      };
      const payload = {
        project_id: me && me.active_project_id ? me.active_project_id : null,
        passenger_name: getCell('passenger_name'),
        pnr: getCell('pnr'),
        issue_date: getCell('issue_date'),
        pickup_time: getCell('pickup_time'),
        transfer_point: getCell('transfer_point'),
        vehicle_code: getCell('vehicle_code'),
      };
      try {
        const res = await fetch(`/transfers/${id}`, {
          method: 'PUT',
          headers: { ...authHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || 'Kayıt güncellenemedi');
        summary.textContent = `Transfer güncellendi: #${id}`;
      } catch (err) {
        summary.textContent = `Hata: ${err.message}`;
      }
    });
    printBtn.addEventListener('click', () => window.print());
    const normalize = (v) => (v == null ? '' : String(v));
    const tableHeaders = [
      'ID','PASSENGER','GENDER','PNR','ISSUE DATE','FLIGHT TYPE','FLIGHT','ROUTE',
      'DEPARTURE DATETIME','ARRIVAL DATETIME','PICK-UP TIME','TRANSFER POINT','VEHICLE CODE'
    ];
    const rowFromTransfer = (t) => ([
      normalize(t.id), normalize(t.passenger_name), normalize(t.cinsiyet), normalize(t.pnr),
      normalize(t.duzenlenme_tarihi), normalize(t.ucus_sekli), normalize(t.flight_no), normalize(t.from_to),
      normalize(t.kalkis_tarihi_saati), normalize(t.inis_tarihi_saati), normalize(t.pickup_time),
      normalize(t.transfer_noktasi), normalize(t.arac_kod)
    ]);
    const fetchTransferRows = async () => {
      if (!(await ensureActiveProject())) return [];
      const url = `/transfers?project_id=${encodeURIComponent(String(me.active_project_id))}`;
      const res = await fetch(url, { headers: authHeaders() });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Liste alınamadı');
      return (data || []).map(rowFromTransfer);
    };
    const downloadBlob = (blob, filename) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    };
    const exportCsv = (rows) => {
      const esc = (v) => `"${normalize(v).replace(/"/g, '""')}"`;
      const lines = [tableHeaders.map(esc).join(','), ...rows.map(r => r.map(esc).join(','))];
      downloadBlob(new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' }), 'transfer_listesi.csv');
    };
    const exportXlsx = (rows) => {
      // Excel HTML fallback: modern Excel .xlsx uzantısı ile açabilir.
      const thead = `<tr>${tableHeaders.map(h => `<th>${h}</th>`).join('')}</tr>`;
      const tbody = rows.map(r => `<tr>${r.map(c => `<td>${normalize(c)}</td>`).join('')}</tr>`).join('');
      const html = `<!doctype html><html><head><meta charset="utf-8"></head><body><table border="1"><thead>${thead}</thead><tbody>${tbody}</tbody></table></body></html>`;
      downloadBlob(new Blob([html], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }), 'transfer_listesi.xlsx');
    };
    const exportPdf = (rows) => {
      const w = window.open('', '_blank');
      if (!w) throw new Error('Popup engellendi');
      const thead = `<tr>${tableHeaders.map(h => `<th>${h}</th>`).join('')}</tr>`;
      const tbody = rows.map(r => `<tr>${r.map(c => `<td>${normalize(c)}</td>`).join('')}</tr>`).join('');
      w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Transfer Listesi</title><style>body{font-family:Arial,sans-serif;margin:18px}table{width:100%;border-collapse:collapse;font-size:12px}th,td{border:1px solid #ddd;padding:6px;text-align:left;vertical-align:top}th{background:#f5f5f5}
    html, body { margin:0 !important; padding:0 !important; }
    .wrap { padding-top:0 !important; }
    .head { width:100vw; max-width:100vw; margin:0 calc(50% - 50vw) 10px calc(50% - 50vw); border-radius:0 !important; box-sizing:border-box; }
  
    table tbody tr:nth-child(even) td { background: rgba(159, 216, 255, 0.22); }
  </style></head><body><table><thead>${thead}</thead><tbody>${tbody}</tbody></table></body></html>`);
      w.document.close();
      w.focus();
      w.print();
    };
    exportBtn.addEventListener('click', async () => {
      try {
        summary.textContent = 'Dışarı Aktar hazırlanıyor...';
        const rows = await fetchTransferRows();
        if (!rows.length) { summary.textContent = 'Dışarı Aktar için kayıt bulunamadı.'; return; }
        const format = (exportFormat.value || 'pdf').toLowerCase();
        if (format === 'csv') exportCsv(rows);
        else if (format === 'xlsx') exportXlsx(rows);
        else exportPdf(rows);
        summary.textContent = `Dışarı Aktar tamamlandı (${format.toUpperCase()}).`;
      } catch (err) {
        summary.textContent = `Hata: ${err.message}`;
      }
    });
    loadTransfers();
  </script>
</body>
</html>
"""


@app.post("/upload-many")
def upload_many(
    files: list[UploadFile] = File(...),
    project_id: int | None = Form(default=None),
    operation_city: str = Form(default=""),
    target_airports: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if not is_superadmin(current_user):
        if current_user.active_project_id is None:
            raise HTTPException(status_code=400, detail="Active project is required")
        if project_id is not None and int(project_id) != int(current_user.active_project_id):
            raise HTTPException(status_code=403, detail="Only active project is allowed")
        project_id = current_user.active_project_id
    elif project_id is None:
        project_id = current_user.active_project_id
    selected_project = None
    if project_id is not None:
        query = db.query(Project).filter(Project.id == project_id, Project.is_active.is_(True))
        if not is_superadmin(current_user):
            query = query.filter(Project.tenant_id == current_user.tenant_id)
        selected_project = query.first()
        if not selected_project:
            raise HTTPException(status_code=404, detail="Project not found")
        if not _can_user_access_project(db, current_user, selected_project):
            raise HTTPException(status_code=403, detail="Project access denied")
        if not _is_module_enabled_for_project(db, int(selected_project.id), "transfer"):
            raise HTTPException(status_code=403, detail="Transfer module is disabled for this project")
    if not selected_project:
        raise HTTPException(status_code=400, detail="Active project is required")
    effective_tenant_id = selected_project.tenant_id if selected_project else current_user.tenant_id
    if not effective_tenant_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    effective_city = (selected_project.city if selected_project else operation_city) or ""
    resolved_targets = _resolve_target_airports(target_airports, effective_city)
    if selected_project:
        resolved_targets = _resolve_target_airports("", selected_project.city)
    results: list[dict] = []
    for file in files:
        extension = Path(file.filename or "").suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            results.append(
                {
                    "original_filename": file.filename or "",
                    "status": "skipped",
                    "note": "Unsupported file type",
                }
            )
            continue

        content = file.file.read()

        def _create_upload_record(raw_bytes: bytes, original_name: str, content_type: str | None):
            item_ext = Path(original_name).suffix.lower()
            stored_name = f"{uuid.uuid4().hex}{item_ext}"
            destination = UPLOAD_DIR / stored_name
            with open(destination, "wb") as output:
                output.write(raw_bytes)
            upload = Upload(
                tenant_id=effective_tenant_id,
                user_id=current_user.id,
                project_id=selected_project.id if selected_project else None,
                operation_city=effective_city or None,
                operation_code=(selected_project.operation_code if selected_project else None),
                original_filename=original_name or stored_name,
                stored_filename=stored_name,
                content_type=content_type or "application/octet-stream",
                file_size=len(raw_bytes),
                file_path=str(destination),
                status="pending",
            )
            db.add(upload)
            db.flush()
            upload_queue.enqueue("app.tasks.process_upload", upload.id, resolved_targets)
            return upload

        if extension == ".zip":
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        original_name = Path(info.filename).name
                        item_ext = Path(original_name).suffix.lower()
                        if item_ext not in {".pdf", ".jpg", ".jpeg", ".png"}:
                            results.append(
                                {
                                    "original_filename": info.filename,
                                    "status": "skipped",
                                    "note": "Unsupported file in ZIP",
                                }
                            )
                            continue
                        raw = zf.read(info.filename)
                        upload = _create_upload_record(raw, original_name, None)
                        results.append(
                            {
                                "id": upload.id,
                                "original_filename": upload.original_filename,
                                "status": upload.status,
                                "note": "queued (zip)",
                            }
                        )
            except zipfile.BadZipFile:
                results.append(
                    {
                        "original_filename": file.filename or "",
                        "status": "failed",
                        "note": "Invalid ZIP archive",
                    }
                )
            continue

        upload = _create_upload_record(content, file.filename or f"{uuid.uuid4().hex}{extension}", file.content_type)
        results.append(
            {
                "id": upload.id,
                "original_filename": upload.original_filename,
                "status": upload.status,
                "note": "queued",
            }
        )

    db.commit()
    return {
        "total": len(results),
        "results": results,
        "project_id": selected_project.id if selected_project else None,
        "operation_city": effective_city or None,
        "operation_code": selected_project.operation_code if selected_project else None,
        "target_airports": resolved_targets,
    }


@app.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    project_id: int | None = Form(default=None),
    operation_city: str = Form(default=""),
    target_airports: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if not is_superadmin(current_user):
        if current_user.active_project_id is None:
            raise HTTPException(status_code=400, detail="Active project is required")
        if project_id is not None and int(project_id) != int(current_user.active_project_id):
            raise HTTPException(status_code=403, detail="Only active project is allowed")
        project_id = current_user.active_project_id
    elif project_id is None:
        project_id = current_user.active_project_id
    selected_project = None
    if project_id is not None:
        query = db.query(Project).filter(Project.id == project_id, Project.is_active.is_(True))
        if not is_superadmin(current_user):
            query = query.filter(Project.tenant_id == current_user.tenant_id)
        selected_project = query.first()
        if not selected_project:
            raise HTTPException(status_code=404, detail="Project not found")
        if not _can_user_access_project(db, current_user, selected_project):
            raise HTTPException(status_code=403, detail="Project access denied")
        if not _is_module_enabled_for_project(db, int(selected_project.id), "transfer"):
            raise HTTPException(status_code=403, detail="Transfer module is disabled for this project")
    if not selected_project:
        raise HTTPException(status_code=400, detail="Active project is required")
    effective_tenant_id = selected_project.tenant_id if selected_project else current_user.tenant_id
    if not effective_tenant_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    effective_city = (selected_project.city if selected_project else operation_city) or ""
    resolved_targets = _resolve_target_airports(target_airports, effective_city)
    if selected_project:
        resolved_targets = _resolve_target_airports("", selected_project.city)
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed: PDF, JPG, PNG, ZIP",
        )

    content = file.file.read()

    def _create_upload_record(raw_bytes: bytes, original_name: str, content_type: str | None):
        item_ext = Path(original_name).suffix.lower()
        stored_name = f"{uuid.uuid4().hex}{item_ext}"
        destination = UPLOAD_DIR / stored_name
        with open(destination, "wb") as output:
            output.write(raw_bytes)
        upload = Upload(
            tenant_id=effective_tenant_id,
            user_id=current_user.id,
            project_id=selected_project.id if selected_project else None,
            operation_city=effective_city or None,
            operation_code=(selected_project.operation_code if selected_project else None),
            original_filename=original_name or stored_name,
            stored_filename=stored_name,
            content_type=content_type or "application/octet-stream",
            file_size=len(raw_bytes),
            file_path=str(destination),
            status="pending",
        )
        db.add(upload)
        db.flush()
        upload_queue.enqueue("app.tasks.process_upload", upload.id, resolved_targets)
        return upload

    if extension == ".zip":
        created_uploads: list[dict] = []
        skipped_entries: list[str] = []
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    original_name = Path(info.filename).name
                    item_ext = Path(original_name).suffix.lower()
                    if item_ext not in {".pdf", ".jpg", ".jpeg", ".png"}:
                        skipped_entries.append(info.filename)
                        continue
                    raw = zf.read(info.filename)
                    upload = _create_upload_record(raw, original_name, None)
                    created_uploads.append(
                        {
                            "id": upload.id,
                            "original_filename": upload.original_filename,
                            "stored_filename": upload.stored_filename,
                            "file_size": upload.file_size,
                            "content_type": upload.content_type,
                            "file_path": upload.file_path,
                            "status": upload.status,
                            "created_at": upload.created_at,
                        }
                    )
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP archive.")

        db.commit()
        return {
            "mode": "zip_batch",
            "zip_filename": file.filename or "archive.zip",
            "created_count": len(created_uploads),
            "skipped_count": len(skipped_entries),
            "skipped_entries": skipped_entries,
            "uploads": created_uploads,
            "project_id": selected_project.id if selected_project else None,
            "operation_city": effective_city or None,
            "operation_code": selected_project.operation_code if selected_project else None,
            "target_airports": resolved_targets,
        }

    upload = _create_upload_record(content, file.filename or f"{uuid.uuid4().hex}{extension}", file.content_type)
    db.commit()
    db.refresh(upload)
    return {
        "id": upload.id,
        "original_filename": upload.original_filename,
        "stored_filename": upload.stored_filename,
        "file_size": upload.file_size,
        "content_type": upload.content_type,
        "file_path": upload.file_path,
        "status": upload.status,
        "parse_result": upload.parse_result,
        "error_message": upload.error_message,
        "created_at": upload.created_at,
        "project_id": selected_project.id if selected_project else None,
        "operation_city": effective_city or None,
        "operation_code": selected_project.operation_code if selected_project else None,
        "target_airports": resolved_targets,
    }


@app.get("/uploads/{upload_id}")
def get_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    active_project, management_scope = _active_project_and_management_scope(db, current_user)
    if not management_scope and active_project is None:
        raise HTTPException(status_code=400, detail="Active project required")
    query = db.query(Upload).filter(Upload.id == upload_id)
    if not is_superadmin(current_user):
        query = query.filter(Upload.tenant_id == current_user.tenant_id)
    if not management_scope:
        query = query.filter(Upload.project_id == int(active_project.id))
    upload = query.first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    return {
        "id": upload.id,
        "original_filename": upload.original_filename,
        "stored_filename": upload.stored_filename,
        "file_size": upload.file_size,
        "content_type": upload.content_type,
        "file_path": upload.file_path,
        "status": upload.status,
        "parse_result": upload.parse_result,
        "error_message": upload.error_message,
        "created_at": upload.created_at,
    }


@app.post("/uploads/statuses")
def get_upload_statuses(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    upload_ids = payload.get("upload_ids") or []
    if not isinstance(upload_ids, list) or not upload_ids:
        raise HTTPException(status_code=400, detail="upload_ids is required")
    try:
        normalized_ids = [int(x) for x in upload_ids]
    except Exception:
        raise HTTPException(status_code=400, detail="upload_ids must be integer list")

    active_project, management_scope = _active_project_and_management_scope(db, current_user)
    if not management_scope and active_project is None:
        raise HTTPException(status_code=400, detail="Active project required")

    query = db.query(Upload).filter(Upload.id.in_(normalized_ids))
    if not is_superadmin(current_user):
        query = query.filter(Upload.tenant_id == current_user.tenant_id)
    if not management_scope:
        query = query.filter(Upload.project_id == int(active_project.id))

    rows = query.all()
    return [
        {
            "id": row.id,
            "status": row.status,
            "error_message": row.error_message,
            "project_id": row.project_id,
        }
        for row in rows
    ]


@app.post("/uploads/retry")
def retry_uploads(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    upload_ids = payload.get("upload_ids") or []
    if not isinstance(upload_ids, list) or not upload_ids:
        raise HTTPException(status_code=400, detail="upload_ids is required")
    try:
        normalized_ids = [int(x) for x in upload_ids]
    except Exception:
        raise HTTPException(status_code=400, detail="upload_ids must be integer list")

    active_project, management_scope = _active_project_and_management_scope(db, current_user)
    if not management_scope and active_project is None:
        raise HTTPException(status_code=400, detail="Active project required")

    query = db.query(Upload).filter(Upload.id.in_(normalized_ids))
    if not is_superadmin(current_user):
        query = query.filter(Upload.tenant_id == current_user.tenant_id)
    if not management_scope:
        query = query.filter(Upload.project_id == int(active_project.id))

    queued: list[int] = []
    skipped: list[int] = []
    rows = query.all()
    for row in rows:
        if row.status == "processed":
            skipped.append(row.id)
            continue
        row.status = "pending"
        row.error_message = None
        db.flush()
        retry_targets = None
        if row.project_id:
            project = db.query(Project).filter(Project.id == row.project_id).first()
            if project and project.city:
                retry_targets = _resolve_target_airports("", project.city)
        upload_queue.enqueue("app.tasks.process_upload", row.id, retry_targets)
        queued.append(row.id)

    db.commit()
    return {"queued": queued, "skipped": skipped, "count": len(queued)}


@app.post("/uploads/edit-log")
def log_upload_edit(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    upload_id_raw = payload.get("upload_id")
    field = str(payload.get("field") or "").strip()
    old_value = payload.get("old_value")
    new_value = payload.get("new_value")
    original_filename = payload.get("original_filename")

    if not field:
        raise HTTPException(status_code=400, detail="field is required")
    try:
        upload_id = int(upload_id_raw) if upload_id_raw is not None and str(upload_id_raw).strip() != "" else None
    except Exception:
        raise HTTPException(status_code=400, detail="upload_id must be integer")

    related_transfer_id = None
    if upload_id is not None:
        trf = db.query(Transfer).filter(Transfer.upload_id == upload_id).order_by(Transfer.id.desc()).first()
        if trf:
            related_transfer_id = trf.id

    db.add(
        OpsEvent(
            tenant_id=str(current_user.tenant_id) if current_user.tenant_id is not None else None,
            project_id=current_user.active_project_id,
            actor_user_id=current_user.id,
            actor_username=current_user.username,
            event_id=f"upload-edit-{current_user.id}",
            event_type="transfer_updated",
            action="update",
            request_method="POST",
            request_path="/uploads/log-edit",
            status_code=200,
            related_transfer_id=related_transfer_id,
            payload={
                "source": "upload_ui_edit",
                "user_id": current_user.id,
                "upload_id": upload_id,
                "original_filename": original_filename,
                "field": field,
                "old_value": old_value,
                "new_value": new_value,
            },
        )
    )
    db.commit()
    return {"ok": True}


@app.post("/exports/zip")
def export_processed_zip(
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    payload = payload or {}
    upload_ids = payload.get("upload_ids") or []
    only_processed = bool(payload.get("only_processed", True))
    active_project, management_scope = _active_project_and_management_scope(db, current_user)
    raw_project_id = payload.get("project_id")
    requested_project_id: int | None = None
    if raw_project_id is not None:
        try:
            requested_project_id = int(raw_project_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="project_id must be integer")
    elif active_project is not None:
        requested_project_id = int(active_project.id)
    if (
        management_scope
        and active_project is not None
        and _is_management_project(active_project)
        and requested_project_id == int(active_project.id)
    ):
        requested_project_id = None
    if not management_scope and requested_project_id is None:
        raise HTTPException(status_code=400, detail="Active project required")

    query = db.query(Upload)
    if not is_superadmin(current_user):
        query = query.filter(Upload.tenant_id == current_user.tenant_id)
    if not management_scope:
        if active_project is None:
            raise HTTPException(status_code=400, detail="Active project required")
        if requested_project_id is not None and int(requested_project_id) != int(active_project.id):
            raise HTTPException(status_code=403, detail="Only active project is allowed")
        query = query.filter(Upload.project_id == int(active_project.id))
    elif requested_project_id is not None:
        query = query.filter(Upload.project_id == int(requested_project_id))
    if upload_ids:
        query = query.filter(Upload.id.in_([int(x) for x in upload_ids if str(x).isdigit()]))
    if only_processed:
        query = query.filter(Upload.status == "processed")
    uploads = query.order_by(Upload.id.asc()).all()
    if not uploads:
        raise HTTPException(status_code=404, detail="No matching uploads found")

    upload_map = {u.id: u for u in uploads}
    transfer_rows = (
        db.query(Transfer)
        .filter(Transfer.upload_id.in_(list(upload_map.keys())))
        .all()
    )
    transfer_by_upload = {t.upload_id: t for t in transfer_rows if t.upload_id is not None}

    zip_buffer = io.BytesIO()
    used_names: dict[str, int] = {}
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for upload in uploads:
            path = Path(upload.file_path or "")
            if not path.exists() or not path.is_file():
                continue

            transfer = transfer_by_upload.get(upload.id)
            ext = path.suffix.lower() or Path(upload.original_filename or "").suffix.lower() or ".pdf"
            normalized_name = _normalized_person_name(transfer) if transfer else (upload.original_filename or "")
            name_part = _safe_name_part(normalized_name)
            pnr_part = _safe_name_part(transfer.pnr if transfer else "")
            base = "_".join([p for p in [name_part, pnr_part] if p]) or "BILET"
            base_filename = f"{base}{ext}"
            filename = base_filename

            counter = used_names.get(base_filename, 0)
            if counter > 0:
                stem = Path(filename).stem
                filename = f"{stem}_{counter + 1}{ext}"
            used_names[base_filename] = counter + 1

            zf.write(path, arcname=filename)

    zip_buffer.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"bilet_export_{timestamp}.zip"
    headers = {"Content-Disposition": f'attachment; filename="{out_name}"'}
    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)


@app.get("/transfers")
def list_transfers(
    status: str | None = Query(default=None),
    airline: str | None = Query(default=None),
    needs_review: bool | None = Query(default=None),
    project_id: int | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    active_project, management_scope = _active_project_and_management_scope(db, current_user)
    requested_project_id: int | None = project_id
    if requested_project_id is None and active_project is not None:
        requested_project_id = int(active_project.id)
    if requested_project_id is not None:
        try:
            requested_project_id = int(requested_project_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="project_id must be integer")
    if (
        management_scope
        and active_project is not None
        and _is_management_project(active_project)
        and requested_project_id == int(active_project.id)
    ):
        requested_project_id = None

    query = db.query(Transfer)
    if not is_superadmin(current_user):
        query = query.filter(Transfer.tenant_id == current_user.tenant_id)
    if not management_scope:
        if active_project is None:
            raise HTTPException(status_code=400, detail="Active project required")
        if requested_project_id is not None and int(requested_project_id) != int(active_project.id):
            raise HTTPException(status_code=403, detail="Only active project is allowed")
        query = query.filter(Transfer.project_id == int(active_project.id))
    elif requested_project_id is not None:
        query = query.filter(Transfer.project_id == int(requested_project_id))
    if status:
        query = query.filter(Transfer.status == status)
    if airline:
        query = query.filter(Transfer.airline == airline.lower())
    if needs_review is not None:
        query = query.filter(Transfer.needs_review == needs_review)

    items = query.order_by(Transfer.created_at.desc()).offset(offset).limit(limit).all()

    color_map = {
        "unassigned": "red",
        "planned": "yellow",
        "completed": "green",
    }

    rows = []
    for transfer in items:
        segment_rows = _segment_rows_for_transfer(transfer)
        for seg in segment_rows:
            rows.append(
                {
                    "id": transfer.id,
                    "upload_id": transfer.upload_id,
                    "project_id": transfer.project_id,
                    "airline": transfer.airline,
                    "passenger_name": _normalized_person_name(transfer) or transfer.passenger_name,
                    "participant_phone": transfer.participant_phone,
                    "participant_order_no": transfer.participant_order_no,
                    "first_name": _split_person_name(transfer)[0],
                    "last_name": _split_person_name(transfer)[1],
                    "passenger_gender": transfer.passenger_gender,
                    "cinsiyet": _gender_label_tr(transfer.passenger_gender),
                    "pnr": transfer.pnr,
                    "flight_no": seg.get("flight_no") or transfer.flight_no,
                    "date": transfer.flight_date,
                    "time": transfer.flight_time,
                    "trip_type": transfer.trip_type,
                    "outbound_date": transfer.outbound_date,
                    "return_date": transfer.return_date,
                    "segment_count": transfer.segment_count,
                    "outbound_departure_date": transfer.outbound_departure_date,
                    "outbound_departure_time": transfer.outbound_departure_time,
                    "outbound_arrival_date": transfer.outbound_arrival_date,
                    "outbound_arrival_time": transfer.outbound_arrival_time,
                    "return_departure_date": transfer.return_departure_date,
                    "return_departure_time": transfer.return_departure_time,
                    "return_arrival_date": transfer.return_arrival_date,
                    "return_arrival_time": transfer.return_arrival_time,
                    "from": transfer.pickup_location,
                    "to": transfer.dropoff_location,
                    "from_to": seg.get("from_to"),
                    "kalkis_tarihi_saati": seg.get("kalkis_tarihi_saati"),
                    "inis_tarihi_saati": seg.get("inis_tarihi_saati"),
                    "ucus_sekli": seg.get("ucus_sekli") or _flight_shape_label(transfer),
                    "status": transfer.status,
                    "status_color": color_map.get(transfer.status, "red"),
                    "pickup_time": transfer.pickup_time,
                    "transfer_noktasi": transfer.transfer_point,
                    "arac_kod": transfer.vehicle_code,
                    "rezervasyon_kodu": transfer.reservation_code,
                    "transfer_aksiyon": transfer.transfer_action,
                    "confidence": transfer.confidence,
                    "needs_review": transfer.needs_review,
                    "created_at": transfer.created_at,
                    "payment_type": transfer.payment_type,
                    "currency": transfer.currency,
                    "total_amount": transfer.total_amount,
                    "issue_date": transfer.issue_date,
                    "duzenlenme_tarihi": transfer.issue_date,
                    "base_fare": "hidden" if transfer.pricing_visibility == "masked" else transfer.base_fare,
                    "taxes": "hidden" if transfer.pricing_visibility == "masked" else transfer.tax_breakdown,
                }
            )
    return rows


@app.put("/transfers/{transfer_id}")
def update_transfer(
    transfer_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    scoped_project_id, management_scope = _resolve_project_scope_for_user(
        db, current_user, payload.get("project_id")
    )
    row = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if not is_superadmin(current_user) and row.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="forbidden")
    if not management_scope and row.project_id != scoped_project_id:
        raise HTTPException(status_code=403, detail="forbidden")
    if management_scope and scoped_project_id is not None and row.project_id != scoped_project_id:
        raise HTTPException(status_code=403, detail="transfer is outside selected project scope")

    allowed = {
        "passenger_name",
        "participant_phone",
        "participant_order_no",
        "pnr",
        "issue_date",
        "pickup_time",
        "transfer_point",
        "vehicle_code",
        "status",
    }
    updated = 0
    for k, v in (payload or {}).items():
        if k not in allowed:
            continue
        txt = str(v).strip() if v is not None else ""
        if k == "participant_order_no":
            try:
                setattr(row, k, int(txt) if txt else None)
            except ValueError:
                raise HTTPException(status_code=400, detail="participant_order_no must be integer")
            updated += 1
            continue
        if k == "vehicle_code":
            txt = txt.upper()
        setattr(row, k, txt or None)
        updated += 1
    if updated == 0:
        raise HTTPException(status_code=400, detail="No editable field provided")

    # Araç kodu varsa rezervasyon kodunu boş bırakmayalım
    if row.vehicle_code and not row.reservation_code:
        row.reservation_code = _build_reservation_code(row.vehicle_code, row.flight_date, row.project_id)

    db.commit()
    db.refresh(row)
    return {
        "ok": True,
        "id": row.id,
        "passenger_name": row.passenger_name,
        "participant_phone": row.participant_phone,
        "participant_order_no": row.participant_order_no,
        "pnr": row.pnr,
        "issue_date": row.issue_date,
        "pickup_time": row.pickup_time,
        "transfer_point": row.transfer_point,
        "vehicle_code": row.vehicle_code,
        "status": row.status,
    }


@app.get("/module-data")
def list_module_data(
    module_name: str = Query(...),
    entity_type: str | None = Query(default=None),
    project_id: int | None = Query(default=None),
    tenant_id: int | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    mod = _normalize_module_name(module_name)
    _require_module_access(db, current_user, mod)
    scoped_project_id, management_scope = _resolve_project_scope_for_user(db, current_user, project_id)

    query = db.query(ModuleData).filter(ModuleData.module_name == mod)
    if not is_superadmin(current_user):
        query = query.filter(ModuleData.tenant_id == current_user.tenant_id)
    elif tenant_id is not None:
        query = query.filter(ModuleData.tenant_id == int(tenant_id))

    if not management_scope:
        query = query.filter(ModuleData.project_id == scoped_project_id)
    elif scoped_project_id is not None:
        query = query.filter(ModuleData.project_id == scoped_project_id)

    if entity_type:
        query = query.filter(ModuleData.entity_type == str(entity_type).strip().lower())

    rows = (
        query.order_by(ModuleData.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "project_id": r.project_id,
            "module_name": r.module_name,
            "entity_type": r.entity_type,
            "data": r.data,
            "created_by_user_id": r.created_by_user_id,
            "updated_by_user_id": r.updated_by_user_id,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in rows
    ]


@app.post("/module-data")
def create_module_data(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    mod = _normalize_module_name(payload.get("module_name"))
    _require_module_access(db, current_user, mod)
    scoped_project_id, management_scope = _resolve_project_scope_for_user(
        db, current_user, payload.get("project_id")
    )
    raw_tenant = payload.get("tenant_id")
    payload_tenant_id: int | None = None
    if raw_tenant is not None and str(raw_tenant).strip() != "":
        try:
            payload_tenant_id = int(raw_tenant)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="tenant_id must be integer")
    tenant_scope = _resolve_tenant_for_module_data(
        db,
        current_user,
        scoped_project_id,
        payload_tenant_id,
    )

    if not management_scope and scoped_project_id is None:
        raise HTTPException(status_code=400, detail="Active project required")

    entity_type = str(payload.get("entity_type") or "").strip().lower() or None
    data_obj = payload.get("data")
    if not isinstance(data_obj, dict):
        raise HTTPException(status_code=400, detail="data must be an object")
    if mod in MODULES_REQUIRING_KAYIT:
        kayit_id = _extract_kayit_id_from_payload(payload)
        kayit_id = _ensure_kayit_exists_for_scope(db, tenant_scope, scoped_project_id, kayit_id)
        data_obj["kayit_id"] = kayit_id

    row = ModuleData(
        tenant_id=tenant_scope,
        project_id=scoped_project_id,
        module_name=mod,
        entity_type=entity_type,
        data=data_obj,
        created_by_user_id=current_user.id,
        updated_by_user_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "module_name": row.module_name,
        "entity_type": row.entity_type,
        "data": row.data,
        "created_by_user_id": row.created_by_user_id,
        "updated_by_user_id": row.updated_by_user_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@app.put("/module-data/{row_id}")
def update_module_data(
    row_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    row = db.query(ModuleData).filter(ModuleData.id == row_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    _require_module_access(db, current_user, str(row.module_name or ""))

    scoped_project_id, management_scope = _resolve_project_scope_for_user(
        db, current_user, payload.get("project_id")
    )
    if not is_superadmin(current_user) and row.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="forbidden")
    if not management_scope:
        if row.project_id != scoped_project_id:
            raise HTTPException(status_code=403, detail="forbidden")
    elif scoped_project_id is not None and row.project_id != scoped_project_id:
        raise HTTPException(status_code=403, detail="forbidden")

    if "module_name" in payload:
        new_module_name = _normalize_module_name(payload.get("module_name"))
        _require_module_access(db, current_user, new_module_name)
        row.module_name = new_module_name
    if "entity_type" in payload:
        row.entity_type = str(payload.get("entity_type") or "").strip().lower() or None
    if "data" in payload:
        data_obj = payload.get("data")
        if not isinstance(data_obj, dict):
            raise HTTPException(status_code=400, detail="data must be an object")
        if row.module_name in MODULES_REQUIRING_KAYIT:
            kayit_id = _extract_kayit_id_from_payload({"data": data_obj, "kayit_id": payload.get("kayit_id")})
            kayit_id = _ensure_kayit_exists_for_scope(db, int(row.tenant_id or 0), row.project_id, kayit_id)
            data_obj["kayit_id"] = kayit_id
        row.data = data_obj
    elif row.module_name in MODULES_REQUIRING_KAYIT and "kayit_id" in payload:
        data_obj = dict(row.data or {})
        kayit_id = _extract_kayit_id_from_payload(payload)
        kayit_id = _ensure_kayit_exists_for_scope(db, int(row.tenant_id or 0), row.project_id, kayit_id)
        data_obj["kayit_id"] = kayit_id
        row.data = data_obj
    row.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "module_name": row.module_name,
        "entity_type": row.entity_type,
        "data": row.data,
        "created_by_user_id": row.created_by_user_id,
        "updated_by_user_id": row.updated_by_user_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@app.delete("/module-data/{row_id}")
def delete_module_data(
    row_id: int,
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    row = db.query(ModuleData).filter(ModuleData.id == row_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    _require_module_access(db, current_user, str(row.module_name or ""))
    scoped_project_id, management_scope = _resolve_project_scope_for_user(db, current_user, project_id)
    if not is_superadmin(current_user) and row.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="forbidden")
    if not management_scope:
        if row.project_id != scoped_project_id:
            raise HTTPException(status_code=403, detail="forbidden")
    elif scoped_project_id is not None and row.project_id != scoped_project_id:
        raise HTTPException(status_code=403, detail="forbidden")
    db.delete(row)
    db.commit()
    return {"ok": True, "deleted_id": row_id}


@app.get("/ops-events")
def list_ops_events(
    tenant_id: str | None = Query(default=None),
    event_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    actor_user_id: int | None = Query(default=None),
    actor_username: str | None = Query(default=None),
    request_method: str | None = Query(default=None),
    request_path: str | None = Query(default=None),
    status_code: int | None = Query(default=None),
    related_transfer_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    scoped_project_id, management_scope = _resolve_project_scope_for_user(db, current_user, project_id)
    query = db.query(OpsEvent)
    scoped_tenant = None if is_superadmin(current_user) else (str(current_user.tenant_id) if current_user.tenant_id else None)
    if tenant_id and scoped_tenant and tenant_id != scoped_tenant:
        raise HTTPException(status_code=403, detail="Tenant scope mismatch")
    if tenant_id:
        query = query.filter(OpsEvent.tenant_id == tenant_id)
    elif scoped_tenant:
        query = query.filter(OpsEvent.tenant_id == scoped_tenant)
    if event_id:
        query = query.filter(OpsEvent.event_id == event_id)
    if event_type:
        if event_type not in ALLOWED_OPS_EVENT_TYPES:
            raise HTTPException(status_code=400, detail="Invalid event_type")
        query = query.filter(OpsEvent.event_type == event_type)
    if action:
        query = query.filter(OpsEvent.action == str(action).strip().lower())
    if actor_user_id is not None:
        query = query.filter(OpsEvent.actor_user_id == actor_user_id)
    if actor_username:
        query = query.filter(OpsEvent.actor_username == str(actor_username).strip())
    if request_method:
        query = query.filter(OpsEvent.request_method == str(request_method).strip().upper())
    if request_path:
        query = query.filter(OpsEvent.request_path.ilike(f"%{str(request_path).strip()}%"))
    if status_code is not None:
        query = query.filter(OpsEvent.status_code == status_code)
    if related_transfer_id is not None:
        query = query.filter(OpsEvent.related_transfer_id == related_transfer_id)
    if not management_scope:
        query = query.outerjoin(Transfer, Transfer.id == OpsEvent.related_transfer_id).filter(
            (OpsEvent.project_id == scoped_project_id)
            | ((OpsEvent.project_id.is_(None)) & (Transfer.project_id == scoped_project_id))
        )
    elif scoped_project_id is not None:
        query = query.outerjoin(Transfer, Transfer.id == OpsEvent.related_transfer_id).filter(
            (OpsEvent.project_id == scoped_project_id)
            | ((OpsEvent.project_id.is_(None)) & (Transfer.project_id == scoped_project_id))
        )

    rows = (
        query.order_by(OpsEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "project_id": row.project_id,
            "actor_user_id": row.actor_user_id,
            "actor_username": row.actor_username,
            "event_id": row.event_id,
            "event_type": row.event_type,
            "action": row.action,
            "request_method": row.request_method,
            "request_path": row.request_path,
            "status_code": row.status_code,
            "ip_address": row.ip_address,
            "user_agent": row.user_agent,
            "related_transfer_id": row.related_transfer_id,
            "payload": row.payload,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@app.get("/audit-ui", response_class=HTMLResponse)
def audit_ui():
    html = """
    <!doctype html>
    <html lang="tr">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width,initial-scale=1" />
      <title>Audit Log</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 16px; background: #f7f9fc; color: #111827; }
        .box { background: #fff; border: 1px solid #dbe2ea; border-radius: 10px; padding: 12px; }
        .row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
        input, select, button { border: 1px solid #c8d0da; border-radius: 8px; padding: 8px 10px; font-size: 13px; }
        button { background: #0a1024; color: #fff; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th, td { border: 1px solid #e5e7eb; padding: 6px; vertical-align: top; text-align: left; }
        th { background: #f3f4f6; }
        .mono { font-family: Consolas, monospace; white-space: pre-wrap; word-break: break-word; }
      </style>
    </head>
    <body>
      <div class="box">
        <h2>Audit Log (Superadmin)</h2>
        <div class="row">
          <input id="f_action" placeholder="action (create/update/delete/read)" />
          <input id="f_actor" placeholder="actor_username" />
          <input id="f_project" placeholder="project_id" />
          <input id="f_tenant" placeholder="tenant_id" />
          <input id="f_path" placeholder="request_path içerir" />
          <select id="f_method">
            <option value="">method (all)</option>
            <option>GET</option><option>POST</option><option>PUT</option><option>PATCH</option><option>DELETE</option>
          </select>
          <input id="f_limit" value="200" placeholder="limit" />
          <button id="btnLoad">Yenile</button>
        </div>
        <div style="overflow:auto;max-height:70vh">
          <table id="tbl">
            <thead>
              <tr>
                <th>Zaman</th><th>User</th><th>Tenant</th><th>Project</th><th>Action</th>
                <th>Method</th><th>Path</th><th>Status</th><th>Change</th><th>Data</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
      <script>
        function esc(v){ return String(v ?? '').replace(/[&<>]/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[s])); }
        async function loadLogs(){
          const t = localStorage.getItem('access_token') || '';
          if(!t){ alert('Token bulunamadı, önce giriş yapın.'); return; }
          const p = new URLSearchParams();
          const pairs = [
            ['action','f_action'], ['actor_username','f_actor'], ['project_id','f_project'],
            ['tenant_id','f_tenant'], ['request_path','f_path'], ['request_method','f_method'], ['limit','f_limit']
          ];
          for (const [k,id] of pairs){
            const v = (document.getElementById(id).value || '').trim();
            if(v) p.set(k,v);
          }
          const meRes = await fetch('/auth/me', { headers: { Authorization: 'Bearer ' + t }});
          const me = await meRes.json().catch(() => ({}));
          if(!meRes.ok || String(me.role || '').toLowerCase() !== 'superadmin'){
            alert('Bu ekran yalnızca superadmin içindir.');
            return;
          }
          const r = await fetch('/ops-events?' + p.toString(), { headers: { Authorization: 'Bearer ' + t }});
          const rows = await r.json().catch(() => []);
          if(!r.ok){ alert('Loglar alınamadı'); return; }
          const tb = document.querySelector('#tbl tbody');
          tb.innerHTML = '';
          (Array.isArray(rows) ? rows : []).forEach(x => {
            const tr = document.createElement('tr');
            const change = x?.payload?.change_kind || '';
            tr.innerHTML =
              '<td>' + esc(x.created_at) + '</td>' +
              '<td>' + esc(x.actor_username || x.actor_user_id) + '</td>' +
              '<td>' + esc(x.tenant_id) + '</td>' +
              '<td>' + esc(x.project_id) + '</td>' +
              '<td>' + esc(x.action) + '</td>' +
              '<td>' + esc(x.request_method) + '</td>' +
              '<td>' + esc(x.request_path) + '</td>' +
              '<td>' + esc(x.status_code) + '</td>' +
              '<td>' + esc(change) + '</td>' +
              '<td class=\"mono\">' + esc(JSON.stringify(x.payload?.request_body ?? x.payload ?? {}, null, 2)) + '</td>';
            tb.appendChild(tr);
          });
        }
        document.getElementById('btnLoad').addEventListener('click', loadLogs);
        loadLogs();
      </script>
    </body>
    </html>
    """
    return HTMLResponse(_inject_standard_header_style(html))











































