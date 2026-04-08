import hashlib
import io
import json
import os
import re
import secrets
import urllib.error
import urllib.request
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, Form, UploadFile
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from .db import Base, SessionLocal, engine
from .models import ModuleData, Project, ProjectModule, SupplierCompany, Tenant, Upload, User, UserProjectAccess, UserSession


PROJECT_CITY_PRIORITY = ["ISTANBUL", "ANKARA", "ANTALYA", "IZMIR"]
SHARED_PARSER_BASE_URL = str(os.getenv("SHARED_PARSER_BASE_URL") or "http://backend:8000").strip().rstrip("/")
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
    "admin",
    "manager",
    "operator",
}
DEFAULT_MODULE_KEYS = [
    "transfer",
    "operasyon",
    "kayit",
    "konaklama",
    "toplanti",
    "tercuman",
    "muhasebe_finans",
    "duyurular",
    "yonetim",
]
MANAGEMENT_PROJECT_CODE = "YONETIM"
SESSION_IDLE_MINUTES = 1440
USER_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
APP_DIR = Path(__file__).resolve().parent
THEME_FAMILIES_FILE = APP_DIR / "data" / "theme_families.json"
VEHICLE_LICENSE_RULES_FILE = APP_DIR / "data" / "vehicle_license_rules.json"


def _load_theme_families() -> dict[str, dict[str, object]]:
    fallback = {
        "zumrut_operasyon": {
            "label": "Zümrüt Operasyon",
            "description": "Araç firması operasyon ekranları için dengeli yeşil ve altın tonları.",
            "colors": ["#0d3934", "#24b389", "#e4c067"],
        }
    }
    try:
        raw = json.loads(THEME_FAMILIES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(raw, dict) or not raw:
        return fallback
    normalized: dict[str, dict[str, object]] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        colors = value.get("colors") if isinstance(value.get("colors"), list) else []
        normalized[str(key)] = {
            "label": str(value.get("label") or key),
            "description": str(value.get("description") or ""),
            "colors": [str(color) for color in colors[:3]],
        }
    return normalized or fallback


def _load_vehicle_license_rules() -> dict[str, object]:
    fallback: dict[str, object] = {"version": 1, "rules": [], "model_hints": []}
    try:
        raw = json.loads(VEHICLE_LICENSE_RULES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(raw, dict):
        return fallback
    rules = raw.get("rules") if isinstance(raw.get("rules"), list) else []
    model_hints = raw.get("model_hints") if isinstance(raw.get("model_hints"), list) else []
    return {
        "version": int(raw.get("version") or 1),
        "rules": rules,
        "model_hints": model_hints,
    }


THEME_FAMILIES = _load_theme_families()
VEHICLE_LICENSE_RULES = _load_vehicle_license_rules()
ALLOWED_PROJECT_CITIES = {
    "ADANA", "ADIYAMAN", "AFYONKARAHISAR", "AGRI", "AMASYA", "ANKARA", "ANTALYA", "ARTVIN", "AYDIN",
    "BALIKESIR", "BILECIK", "BINGOL", "BITLIS", "BOLU", "BURDUR", "BURSA", "CANAKKALE", "CANKIRI",
    "CORUM", "DENIZLI", "DIYARBAKIR", "EDIRNE", "ELAZIG", "ERZINCAN", "ERZURUM", "ESKISEHIR", "GAZIANTEP",
    "GIRESUN", "GUMUSHANE", "HAKKARI", "HATAY", "ISPARTA", "MERSIN", "ISTANBUL", "IZMIR", "KARS",
    "KASTAMONU", "KAYSERI", "KIRKLARELI", "KIRSEHIR", "KOCAELI", "KONYA", "KUTAHYA", "MALATYA", "MANISA",
    "KAHRAMANMARAS", "MARDIN", "MUGLA", "MUS", "NEVSEHIR", "NIGDE", "ORDU", "RIZE", "SAKARYA", "SAMSUN",
    "SIIRT", "SINOP", "SIRNAK", "SIVAS", "TEKIRDAG", "TOKAT", "TRABZON", "TUNCELI", "USAK", "VAN",
    "YALOVA", "YOZGAT", "ZONGULDAK", "AKSARAY", "BAYBURT", "KARAMAN", "KIRIKKALE", "BATMAN",
    "SANLIURFA", "BARTIN", "ARDAHAN", "IGDIR", "YALOVA", "KARABUK", "KILIS", "OSMANIYE", "DUZCE", "SISTEM",
}


app = FastAPI(title="Creatro Platform Çekirdeği")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Base.metadata.create_all(bind=engine)


def _ensure_platform_core_schema() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE supplier_companies "
                "ADD COLUMN IF NOT EXISTS ui_theme_family VARCHAR(32) NOT NULL DEFAULT 'zumrut_operasyon'"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_supplier_companies_ui_theme_family "
                "ON supplier_companies (ui_theme_family)"
            )
        )


_ensure_platform_core_schema()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def normalize_role(role: str | None) -> str:
    raw = str(role or "").strip().lower()
    if not raw:
        return "tenant_operator"
    return ROLE_ALIASES.get(raw, raw)


def role_level(role: str | None) -> int:
    return ROLE_LEVEL.get(normalize_role(role), 0)


def is_superadmin(user: User) -> bool:
    return normalize_role(user.role) == "superadmin"


def can_manage_supplier_themes(user: User) -> bool:
    return normalize_role(user.role) in {"superadmin", "superadmin_staff"}


def is_unlimited_token_user(user: User | None) -> bool:
    if not user:
        return False
    return str(getattr(user, "username", "") or "").strip().lower() == "creatro"


def require_company_admin(current_user: User):
    if role_level(current_user.role) < role_level("tenant_manager"):
        raise HTTPException(status_code=403, detail="Admin or manager role required")
    return current_user


def require_theme_admin(current_user: User):
    if not can_manage_supplier_themes(current_user):
        raise HTTPException(status_code=403, detail="Theme admin role required")
    return current_user


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


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


def _normalize_login_email(value: str | None) -> str | None:
    txt = str(value or "").strip().lower()
    return txt or None


def _is_valid_contact_email(value: str | None) -> bool:
    email = _normalize_login_email(value)
    if not email:
        return True
    if "@" not in email:
        return False
    local_part, domain_part = email.rsplit("@", 1)
    if not local_part or not domain_part:
        return False
    return "." in domain_part


def _normalize_tc_kimlik_no(value: str | None) -> str | None:
    digits = re.sub(r"\D+", "", str(value or ""))
    if not digits:
        return None
    if digits == "11111111111":
        return digits
    if len(digits) != 11 or not digits.isdigit():
        return None
    if digits[0] == "0":
        return None
    first_nine = [int(ch) for ch in digits[:9]]
    tenth = int(digits[9])
    eleventh = int(digits[10])
    odd_sum = sum(first_nine[0::2])
    even_sum = sum(first_nine[1::2])
    if ((odd_sum * 7) - even_sum) % 10 != tenth:
        return None
    if (sum(int(ch) for ch in digits[:10]) % 10) != eleventh:
        return None
    if eleventh % 2 != 0:
        return None
    return digits


def _normalize_phone(value: str | None) -> str | None:
    digits = re.sub(r"\D+", "", str(value or ""))
    if not digits:
        return None
    if digits.startswith("0") and len(digits) == 11:
        digits = "90" + digits[1:]
    if digits.startswith("5") and len(digits) == 10:
        digits = "90" + digits
    return digits


def _format_phone_display(value: str | None) -> str:
    normalized = _normalize_phone(value)
    if normalized and normalized.startswith("90") and len(normalized) == 12:
        return f"+90 {normalized[2:5]} {normalized[5:8]} {normalized[8:10]} {normalized[10:12]}"
    return str(value or "").strip()


def _normalize_passport_no(value: str | None) -> str | None:
    raw = str(value or "").upper()
    cleaned = re.sub(r"[^A-Z0-9]", "", raw)
    return cleaned or None


COMMON_TEXT_REPAIRS = {
    "T?rk?e": "Türkçe",
    "?ngilizce": "İngilizce",
    "?stanbul": "İstanbul",
    "kay?t": "kayıt",
    "OK?AK": "OKŞAK",
}


def _repair_text_value(value):
    if isinstance(value, str):
        txt = value
        try:
            if any(token in txt for token in ("Ã", "Å", "Ä", "Â")):
                txt = txt.encode("latin-1").decode("utf-8")
        except Exception:
            pass
        for src, target in COMMON_TEXT_REPAIRS.items():
            txt = txt.replace(src, target)
        return txt.strip()
    if isinstance(value, list):
        return [_repair_text_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _repair_text_value(val) for key, val in value.items()}
    return value


def _normalize_birth_date(value: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _calculate_age(value: str | None) -> int | None:
    birth_date = _normalize_birth_date(value)
    if not birth_date:
        return None
    born = datetime.strptime(birth_date, "%Y-%m-%d").date()
    today = date.today()
    years = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return max(0, years)


def _normalize_dynamic_fields(value) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(value, list):
        return out
    for item in value:
        if not isinstance(item, dict):
            continue
        label = str(_repair_text_value(item.get("label")) or "").strip()
        field_value = str(_repair_text_value(item.get("value")) or "").strip()
        if not label and not field_value:
            continue
        out.append({"label": label, "value": field_value})
    return out


def _normalize_vehicle_card_item(item: dict) -> dict:
    cleaned = _repair_text_value(item if isinstance(item, dict) else {})
    return {
        "vehicle_code": str(cleaned.get("vehicle_code") or "").strip(),
        "plate_no": str(cleaned.get("plate_no") or "").strip(),
        "vehicle_category": str(cleaned.get("vehicle_category") or "").strip() or "VAN",
        "vehicle_type": str(cleaned.get("vehicle_type") or "").strip(),
        "model": str(cleaned.get("model") or "").strip(),
        "model_year": str(cleaned.get("model_year") or "").strip(),
        "seat_capacity": str(cleaned.get("seat_capacity") or "").strip(),
        "luggage_capacity": str(cleaned.get("luggage_capacity") or "").strip(),
        "seat_type": str(cleaned.get("seat_type") or "").strip(),
        "vehicle_features": str(cleaned.get("vehicle_features") or "").strip(),
        "vehicle_note": str(cleaned.get("vehicle_note") or "").strip(),
        "extra_fields": _normalize_dynamic_fields(cleaned.get("extra_fields")),
    }


def _sanitize_company_card_draft(data: dict | None) -> dict:
    cleaned = _repair_text_value(data if isinstance(data, dict) else {})
    cleaned.pop("system_code", None)
    for key in ("email", "authority_email"):
        if key in cleaned:
            cleaned[key] = _normalize_login_email(cleaned.get(key)) or ""
    for key in ("phone", "authority_phone"):
        if key in cleaned:
            cleaned[key] = _format_phone_display(cleaned.get(key))
    if isinstance(cleaned.get("responsible_people"), list):
        people = []
        for item in cleaned.get("responsible_people") or []:
            if not isinstance(item, dict):
                continue
            entry = _repair_text_value(item)
            if "email" in entry:
                entry["email"] = _normalize_login_email(entry.get("email")) or ""
            if "phone" in entry:
                entry["phone"] = _format_phone_display(entry.get("phone"))
            people.append(entry)
        cleaned["responsible_people"] = people
    return cleaned


def _normalize_tax_number_for_matching(value: str | None) -> str:
    raw = re.sub(r"[^0-9]", "", str(value or "").strip())
    if raw in {"2222222222", "11111111111"}:
        return raw
    if len(raw) == 11:
        return _normalize_tc_kimlik_no(raw) or ""
    if len(raw) == 10 and _is_valid_tax_number(raw):
        return raw
    return ""


def _is_valid_tax_number(value: str | None) -> bool:
    digits = re.sub(r"\D+", "", str(value or ""))
    if digits == "2222222222":
        return True
    if len(digits) != 10 or not digits.isdigit():
        return False
    total = 0
    for index in range(9):
        digit = int(digits[index])
        step = (digit + 10 - (index + 1)) % 10
        if step == 9:
            transformed = 9
        else:
            transformed = (step * (2 ** (10 - (index + 1)))) % 9
        total += transformed
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(digits[9])


def _is_placeholder_tax_number(value: str | None) -> bool:
    return _normalize_tax_number_for_matching(value) in {"2222222222", "11111111111"}


def _resolve_company_portal_status(
    db: Session,
    tenant_id: int | None,
    company_type: str | None,
    tax_number: str | None,
    current_draft_id: int | None = None,
) -> dict[str, object]:
    normalized_type = _normalize_company_type_for_code(company_type)
    raw_tax = re.sub(r"[^0-9]", "", str(tax_number or "").strip())
    normalized_tax = _normalize_tax_number_for_matching(tax_number)

    if raw_tax and not normalized_tax:
        return {
            "portal_mode": "pasif",
            "matched": False,
            "reason": "Vergi No / T.C. bilgisi doğrulama kurallarına uymuyor. Bilinmiyorsa firma için 2222222222, kişi için 11111111111 kullanılabilir.",
        }
    if not normalized_tax:
        return {
            "portal_mode": "pasif",
            "matched": False,
            "reason": "Vergi numarası veya T.C. bilgisi girilmediği için kayıt pasif açılır.",
        }
    if _is_placeholder_tax_number(normalized_tax):
        return {
            "portal_mode": "pasif",
            "matched": False,
            "reason": "Geçici vergi numarası kullanıldığı için kayıt pasif açılır.",
        }

    rows = (
        db.query(ModuleData)
        .filter(
            ModuleData.module_name == "fleet_company_card",
            ModuleData.entity_type == "draft",
            ModuleData.tenant_id == tenant_id if tenant_id else ModuleData.tenant_id.is_(None),
        )
        .order_by(ModuleData.id.desc())
        .all()
    )

    for row in rows:
        if current_draft_id and int(row.id) == int(current_draft_id):
            continue
        data = _sanitize_company_card_draft(row.data if isinstance(row.data, dict) else {})
        row_tax = _normalize_tax_number_for_matching(data.get("tax_number"))
        if row_tax != normalized_tax:
            continue
        row_type = _normalize_company_type_for_code(data.get("company_type"))
        return {
            "portal_mode": "aktif",
            "matched": True,
            "reason": f"Bu { 'acente' if row_type == 'agency' else 'firma' } sistemde kayıtlı göründüğü için portal modu aktif eşleştirildi.",
        }

    return {
        "portal_mode": "pasif",
        "matched": False,
        "reason": "Eşleşen kayıt bulunamadı. Firma pasif kayıt olarak açılır, sonradan otomatik veya manuel eşleştirilebilir.",
    }


def _normalize_company_type_for_code(company_type: str | None) -> str:
    raw = str(company_type or "").strip().lower()
    if raw in {"vehicle_company", "vehicle", "arac_firmasi", "araç_firması"}:
        return "vehicle_company"
    if raw in {"company", "firm", "firma", "normal_firma", "normal_company"}:
        return "company"
    return "agency"


def _company_code_prefix(company_type: str | None) -> str:
    normalized = _normalize_company_type_for_code(company_type)
    if normalized == "vehicle_company":
        return "TRN"
    if normalized == "company":
        return "FRM"
    return "ACN"


def _next_company_code(db: Session, tenant_id: int | None, company_type: str | None) -> str:
    normalized = _normalize_company_type_for_code(company_type)
    prefix = _company_code_prefix(normalized)
    max_no = 0

    rows = (
        db.query(ModuleData)
        .filter(
            ModuleData.module_name == "fleet_company_card",
            ModuleData.entity_type == "draft",
            ModuleData.tenant_id == tenant_id if tenant_id else ModuleData.tenant_id.is_(None),
        )
        .all()
    )
    pattern = re.compile(rf"^{prefix}-(\d{{3}})$", re.IGNORECASE)
    for row in rows:
        data = _sanitize_company_card_draft(row.data if isinstance(row.data, dict) else {})
        row_type = _normalize_company_type_for_code(data.get("company_type"))
        if row_type != normalized:
            continue
        match = pattern.match(str(data.get("company_code") or "").strip())
        if match:
            max_no = max(max_no, int(match.group(1)))

    supplier_type = None
    if normalized == "vehicle_company":
        supplier_type = "vehicle"
    elif normalized == "agency":
        supplier_type = "agency"

    supplier_count = 0
    if supplier_type:
        supplier_count = (
            db.query(func.count(SupplierCompany.id))
            .filter(
                SupplierCompany.tenant_id == tenant_id if tenant_id else SupplierCompany.tenant_id.is_(None),
                SupplierCompany.company_type == supplier_type,
            )
            .scalar()
            or 0
        )
    next_no = max(max_no + 1, int(supplier_count) + 1, 1)
    return f"{prefix}-{next_no:03d}"


def _normalize_driver_card_item(item: dict) -> dict:
    cleaned = _repair_text_value(item if isinstance(item, dict) else {})
    birth_date = _normalize_birth_date(cleaned.get("birth_date"))
    age = _calculate_age(birth_date)
    legacy_age = str(cleaned.get("age") or "").strip()
    return {
        "driver_code": str(cleaned.get("driver_code") or "").strip(),
        "full_name": str(cleaned.get("full_name") or "").strip(),
        "phone": _format_phone_display(cleaned.get("phone")),
        "tc_kimlik_no": _normalize_tc_kimlik_no(cleaned.get("tc_kimlik_no")),
        "birth_date": birth_date,
        "age": str(age) if age is not None else legacy_age,
        "address": str(cleaned.get("address") or "").strip(),
        "languages": str(cleaned.get("languages") or "").strip(),
        "license_class": str(cleaned.get("license_class") or "").strip(),
        "employment_type": str(cleaned.get("employment_type") or "").strip() or "internal",
        "access_type": str(cleaned.get("access_type") or "").strip() or "portal",
        "driver_note": str(cleaned.get("driver_note") or "").strip(),
        "extra_fields": _normalize_dynamic_fields(cleaned.get("extra_fields")),
    }


def _normalize_greeter_card_item(item: dict) -> dict:
    cleaned = _repair_text_value(item if isinstance(item, dict) else {})
    birth_date = _normalize_birth_date(cleaned.get("birth_date"))
    age = _calculate_age(birth_date)
    legacy_age = str(cleaned.get("age") or "").strip()
    return {
        "greeter_code": str(cleaned.get("greeter_code") or "").strip(),
        "full_name": str(cleaned.get("full_name") or "").strip(),
        "phone": _format_phone_display(cleaned.get("phone")),
        "tc_kimlik_no": _normalize_tc_kimlik_no(cleaned.get("tc_kimlik_no")),
        "birth_date": birth_date,
        "age": str(age) if age is not None else legacy_age,
        "languages": str(cleaned.get("languages") or "").strip(),
        "employment_type": str(cleaned.get("employment_type") or "").strip() or "internal",
        "access_type": str(cleaned.get("access_type") or "").strip() or "portal",
        "greeter_note": str(cleaned.get("greeter_note") or "").strip(),
        "extra_fields": _normalize_dynamic_fields(cleaned.get("extra_fields")),
    }


def _canonical_identity_seed(tc_kimlik_no: str | None, passport_no: str | None = None) -> str:
    tc = _normalize_tc_kimlik_no(tc_kimlik_no)
    passport = _normalize_passport_no(passport_no)
    if tc:
        return f"TC:{tc}"
    if passport:
        return f"PP:{passport}"
    return ""


def _to_base32_token(value: int, length: int = 6) -> str:
    chars = []
    n = int(value)
    base = len(USER_CODE_ALPHABET)
    while len(chars) < length:
        chars.append(USER_CODE_ALPHABET[n % base])
        n //= base
    return "".join(reversed(chars))


def _candidate_user_code(seed: str) -> str:
    if seed:
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        n = int.from_bytes(digest[:8], "big")
    else:
        n = secrets.randbits(48)
    return _to_base32_token(n, length=6)


def _generate_unique_user_code(
    db: Session,
    tc_kimlik_no: str | None = None,
    passport_no: str | None = None,
    existing_user_id: int | None = None,
) -> str:
    seed = _canonical_identity_seed(tc_kimlik_no, passport_no)
    tried: set[str] = set()
    for i in range(128):
        base_seed = seed if i == 0 else f"{seed}|{i}|{secrets.token_hex(2)}"
        code = _candidate_user_code(base_seed)
        if code in tried:
            continue
        tried.add(code)
        q = db.query(User).filter(User.user_code == code)
        if existing_user_id is not None:
            q = q.filter(User.id != int(existing_user_id))
        if not q.first():
            return code
    raise HTTPException(status_code=500, detail="User code could not be generated")


def _find_user_by_login_identifier(db: Session, identifier: str) -> User | None:
    raw = str(identifier or "").strip()
    if not raw:
        return None
    login_email = _normalize_login_email(raw)
    login_tc = _normalize_tc_kimlik_no(raw)
    login_passport = _normalize_passport_no(raw)
    filters = [User.username == raw, User.user_code == raw.upper()]
    if login_email:
        filters.append(func.lower(func.coalesce(User.email, "")) == login_email)
    if login_tc:
        filters.append(func.coalesce(User.tc_kimlik_no, "") == login_tc)
    if login_passport:
        filters.append(func.upper(func.coalesce(User.passport_no, "")) == login_passport)
    return db.query(User).filter(or_(*filters)).order_by(User.id.asc()).first()


def _find_user_by_token(db: Session, token: str | None, touch_session: bool) -> User | None:
    if not token:
        return None
    now = datetime.now(timezone.utc)
    session = db.query(UserSession).filter(UserSession.token == token, UserSession.expires_at > now).first()
    if not session:
        return None
    if touch_session:
        session.expires_at = now + timedelta(minutes=max(1, SESSION_IDLE_MINUTES))
        db.commit()
    return db.query(User).filter(User.id == session.user_id, User.is_active.is_(True)).first()


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


def _json_request(url: str, method: str = "GET", payload: dict | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=request_headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw) if raw else {}
        except Exception:
            data = {"detail": raw or str(exc)}
        return int(exc.code), data


def _encode_multipart_form(fields: dict[str, str], files: list[tuple[str, str, bytes, str]]) -> tuple[bytes, str]:
    boundary = f"----CreatroBoundary{uuid.uuid4().hex}"
    out = io.BytesIO()
    for name, value in fields.items():
        out.write(f"--{boundary}\r\n".encode("utf-8"))
        out.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        out.write(str(value or "").encode("utf-8"))
        out.write(b"\r\n")
    for field_name, filename, content, content_type in files:
        out.write(f"--{boundary}\r\n".encode("utf-8"))
        out.write(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename or "dosya"}"\r\n'.encode("utf-8")
        )
        out.write(f"Content-Type: {content_type or 'application/octet-stream'}\r\n\r\n".encode("utf-8"))
        out.write(content)
        out.write(b"\r\n")
    out.write(f"--{boundary}--\r\n".encode("utf-8"))
    return out.getvalue(), boundary


def _shared_parser_login(username: str, password: str) -> str:
    status, data = _json_request(
        f"{SHARED_PARSER_BASE_URL}/auth/login",
        method="POST",
        payload={"username": username, "password": password},
        headers={"Host": "localhost:3000"},
    )
    token = str((data or {}).get("access_token") or "").strip()
    if status >= 400 or not token:
        raise HTTPException(status_code=400, detail=str((data or {}).get("detail") or "Ortak parser oturumu açılamadı."))
    return token


def _shared_parser_authorization(username: str, password: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_shared_parser_login(username, password)}", "Host": "localhost:3000"}


def _normalize_project_city(value: str | None) -> str:
    txt = str(value or "").strip().upper()
    if not txt:
        return ""
    repl = {"İ": "I", "Ş": "S", "Ğ": "G", "Ü": "U", "Ö": "O", "Ç": "C", "Â": "A", "Î": "I", "Û": "U"}
    for src, target in repl.items():
        txt = txt.replace(src, target)
    return re.sub(r"\s+", " ", txt)


def _normalize_project_system_code(value: str | None) -> str | None:
    raw = str(value or "").strip().upper()
    if not raw:
        return None
    raw = re.sub(r"[^A-Z0-9]", "", raw)
    if not re.fullmatch(r"[A-Z0-9]{4}", raw):
        raise HTTPException(status_code=400, detail="system_code must be 4 chars [A-Z0-9]")
    return raw


def _normalize_iso_date_or_none(value: str | None, field_name: str) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} must be YYYY-MM-DD") from exc


def _generate_project_system_code(db: Session, tenant_id: int) -> str:
    for _ in range(128):
        candidate = "".join(secrets.choice(USER_CODE_ALPHABET) for _ in range(4))
        exists = db.query(Project).filter(Project.tenant_id == tenant_id, Project.system_code == candidate).first()
        if not exists:
            return candidate
    raise HTTPException(status_code=500, detail="Project system code could not be generated")


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
    project = db.query(Project).filter(Project.tenant_id == tenant_id, Project.operation_code == MANAGEMENT_PROJECT_CODE).first()
    if not project:
        project = Project(
            tenant_id=tenant_id,
            name="Yönetim Projesi",
            city="SISTEM",
            operation_code=MANAGEMENT_PROJECT_CODE,
            system_code=_generate_project_system_code(db, tenant_id),
            token_limit=None,
            token_used=0,
            is_active=True,
        )
        db.add(project)
        db.flush()
    _ensure_project_modules_defaults(db, int(project.id))
    return project


def _can_user_access_project(db: Session, user: User, project: Project) -> bool:
    if is_superadmin(user):
        return True
    if not project or not user.tenant_id or int(project.tenant_id or 0) != int(user.tenant_id or 0):
        return False
    deny = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == user.id,
        UserProjectAccess.project_id == project.id,
        UserProjectAccess.is_denied.is_(True),
    ).first()
    if deny:
        return False
    return True


def _supplier_payload_map(db: Session, supplier_ids: list[int]) -> dict[int, dict[str, str | int | None]]:
    out: dict[int, dict[str, str | int | None]] = {}
    if not supplier_ids:
        return out
    for row in db.query(SupplierCompany).filter(SupplierCompany.id.in_(supplier_ids)).all():
        out[int(row.id)] = {"name": row.name, "company_type": row.company_type}
    return out


def _company_type_label(raw: str | None) -> str:
    company_type = str(raw or "").strip().lower()
    if company_type == "vehicle":
        return "Araç firması"
    if company_type == "agency":
        return "Acente"
    return "Tanımsız"


def _theme_family_payload() -> dict[str, dict[str, str | list[str]]]:
    return {
        key: {
            "label": value["label"],
            "description": value["description"],
            "colors": list(value["colors"]),
        }
        for key, value in THEME_FAMILIES.items()
    }


def _theme_payload_for_company(row: SupplierCompany | None) -> dict[str, object]:
    family_code = getattr(row, "ui_theme_family", None) or "zumrut_operasyon"
    family = THEME_FAMILIES.get(family_code) or next(iter(THEME_FAMILIES.values()))
    return {
        "company_id": getattr(row, "id", None),
        "company_name": getattr(row, "name", None),
        "company_type": getattr(row, "company_type", None),
        "company_type_label": _company_type_label(getattr(row, "company_type", None)),
        "ui_theme_family": family_code,
        "theme": {
            "label": family.get("label"),
            "description": family.get("description"),
            "colors": list(family.get("colors", [])),
        },
        "brand_frame": {
            "name": "Creatro",
            "mode": "fixed",
            "description": "Creatro marka alanı sabittir ve tema değişiminden etkilenmez.",
        },
    }


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, int | str]:
    return {
        "status": "ok",
        "domain": "platform-core",
        "port": "8001",
        "tenant_count": db.query(Tenant).count(),
        "user_count": db.query(User).count(),
        "project_count": db.query(Project).count(),
    }


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
    <!doctype html>
    <html lang="tr">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Creatro Platform Çekirdeği</title>
        <style>
          :root {
            --bg: #f4efe8;
            --panel: #fffaf3;
            --ink: #1d2a33;
            --muted: #59656d;
            --line: #d9c9b7;
            --accent: #b25c2f;
          }
          * { box-sizing: border-box; }
          body {
            margin: 0;
            font-family: "Segoe UI", sans-serif;
            background:
              radial-gradient(circle at top left, rgba(178, 92, 47, 0.18), transparent 32%),
              linear-gradient(135deg, #f8f2ea, var(--bg));
            color: var(--ink);
          }
          main { max-width: 1080px; margin: 48px auto; padding: 24px; }
          .panel {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 24px;
            padding: 28px;
            box-shadow: 0 18px 50px rgba(29, 42, 51, 0.08);
          }
          h1 { margin: 0 0 12px; font-size: 38px; }
          p { color: var(--muted); line-height: 1.6; }
          .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-top: 24px;
          }
          .card {
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 18px;
            background: #fff;
          }
          .card strong {
            display: block;
            margin-bottom: 8px;
            color: var(--accent);
          }
          code {
            background: #f3e5d8;
            padding: 2px 6px;
            border-radius: 8px;
          }
          a { color: var(--accent); text-decoration: none; font-weight: 700; }
        </style>
      </head>
      <body>
        <main>
          <section class="panel">
            <h1>Platform Çekirdeği</h1>
            <p>
              Ortak altyapı servisi. Kimlik doğrulama, tenant, kullanıcı, proje ve entegrasyon omurgası burada toplanır.
            </p>
            <div class="grid">
              <article class="card">
                <strong>Hazır Uç Noktalar</strong>
                <code>/health</code>, <code>/auth/login</code>, <code>/auth/me</code>, <code>/tenants</code>,
                <code>/projects</code>, <code>/users</code>
              </article>
              <article class="card">
                <strong>Kullanım</strong>
                Bearer token ile çalışır. Ayrıntılı sözlük için <a href="/docs">Swagger</a>.
              </article>
              <article class="card">
                <strong>Bağlantı</strong>
                Araç firması domaini <a href="http://localhost:3002/">3002</a>,
                Acente domaini <a href="http://localhost:3003/">3003</a>.
              </article>
              <article class="card">
                <strong>Merkez Tema Yönetimi</strong>
                Creatro supplier admin için <a href="/supplier-theme-admin">tema aileleri yönetim ekranı</a>.
              </article>
              <article class="card">
                <strong>Sonraki Faz</strong>
                Tenant ayarları, servis kayıtları, entegrasyon kimlik bilgisi kasası ve denetim kayıtları.
              </article>
            </div>
          </section>
        </main>
      </body>
    </html>
    """


@app.get("/supplier-theme-admin", response_class=HTMLResponse)
def supplier_theme_admin_page() -> str:
    return """
    <!doctype html>
    <html lang="tr">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Supplier Tema Yönetimi</title>
      <style>
        :root {
          --bg-1: #091a2f;
          --bg-2: #102b47;
          --bg-3: #0f2338;
          --panel: rgba(10, 22, 38, 0.84);
          --panel-line: rgba(137, 190, 255, 0.18);
          --card: rgba(248, 251, 255, 0.96);
          --card-line: rgba(34, 71, 112, 0.10);
          --text: #10243c;
          --muted: #4d6179;
          --accent: #4f8fda;
          --accent-2: #d8a15f;
          --white: #f7fbff;
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          min-height: 100vh;
          font-family: "Segoe UI", Arial, sans-serif;
          color: var(--white);
          background:
            radial-gradient(circle at top right, rgba(79,143,218,0.24), transparent 28%),
            linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 52%, var(--bg-3) 100%);
        }
        .wrap { width: min(1240px, calc(100% - 32px)); margin: 24px auto 40px; }
        .head, .panel {
          background: var(--panel);
          border: 1px solid var(--panel-line);
          border-radius: 22px;
          backdrop-filter: blur(12px);
          box-shadow: 0 18px 36px rgba(3, 10, 20, 0.30);
        }
        .head {
          padding: 18px 20px;
          display: flex;
          justify-content: space-between;
          gap: 16px;
          align-items: center;
          margin-bottom: 16px;
        }
        .head strong { display:block; font-size:24px; }
        .head span { display:block; color:#b8cae3; margin-top:6px; font-size:13px; }
        .head a {
          color:#e7f1ff;
          text-decoration:none;
          min-height:42px;
          display:inline-flex;
          align-items:center;
          justify-content:center;
          padding:0 16px;
          border-radius:14px;
          border:1px solid rgba(137, 190, 255, 0.18);
          background:rgba(255,255,255,0.06);
          font-weight:700;
        }
        .panel { padding: 20px; }
        .toolbar {
          display:flex;
          flex-wrap:wrap;
          gap:12px;
          align-items:center;
          margin-bottom:16px;
        }
        .toolbar input, .toolbar select {
          min-height:42px;
          border-radius:14px;
          border:1px solid rgba(137, 190, 255, 0.18);
          background:rgba(255,255,255,0.08);
          color:#f7fbff;
          padding:0 14px;
          outline:none;
        }
        .toolbar input { min-width:260px; }
        .summary {
          color:#b8cae3;
          font-size:13px;
          margin-left:auto;
        }
        .grid {
          display:grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap:16px;
        }
        .card {
          background: var(--card);
          border: 1px solid var(--card-line);
          border-radius: 18px;
          padding: 18px;
          color: var(--text);
        }
        .card-top {
          display:flex;
          justify-content:space-between;
          gap:12px;
          align-items:flex-start;
          margin-bottom:14px;
        }
        .card-top strong {
          display:block;
          font-size:18px;
        }
        .card-top span {
          display:block;
          color: var(--muted);
          margin-top:5px;
          font-size:12px;
        }
        .badge {
          min-height:28px;
          display:inline-flex;
          align-items:center;
          justify-content:center;
          border-radius:999px;
          padding:0 10px;
          font-size:11px;
          font-weight:800;
          background:rgba(79,143,218,0.12);
          color:#1c4f86;
          border:1px solid rgba(79,143,218,0.20);
          white-space:nowrap;
        }
        .swatches {
          display:flex;
          gap:8px;
          margin:10px 0 14px;
        }
        .swatches i {
          width:20px;
          height:20px;
          border-radius:999px;
          display:inline-block;
          border:1px solid rgba(0,0,0,0.08);
        }
        .list {
          display:grid;
          gap:10px;
          margin-bottom:14px;
        }
        .row {
          display:grid;
          grid-template-columns: 128px 1fr;
          gap:10px;
          font-size:13px;
        }
        .row strong { color:#204978; }
        .row span { color:var(--muted); line-height:1.5; }
        .family-list {
          display:grid;
          gap:10px;
          margin-bottom:14px;
        }
        .preview {
          border-radius:16px;
          overflow:hidden;
          border:1px solid rgba(16,36,60,0.08);
          background:#eef4fb;
          margin-bottom:14px;
        }
        .preview-top {
          min-height:54px;
          padding:12px 14px;
          color:#f7fbff;
          display:flex;
          align-items:center;
          justify-content:space-between;
          gap:12px;
        }
        .preview-top strong {
          display:block;
          font-size:13px;
          margin-bottom:4px;
        }
        .preview-top span {
          display:block;
          font-size:11px;
          opacity:0.9;
        }
        .preview-page {
          display:grid;
          grid-template-columns: 88px 1fr;
          min-height:138px;
          background:linear-gradient(180deg, rgba(255,255,255,0.94) 0%, rgba(236,243,249,0.92) 100%);
        }
        .preview-brand {
          background:linear-gradient(180deg, #081f33 0%, #103454 100%);
          color:#f4f8ff;
          padding:12px 10px;
          display:flex;
          flex-direction:column;
          justify-content:space-between;
          gap:10px;
        }
        .preview-brand-mark {
          width:40px;
          height:40px;
          border-radius:14px;
          background:linear-gradient(180deg, #f3b562 0%, #e28743 100%);
          color:#10243c;
          font-weight:900;
          display:grid;
          place-items:center;
          font-size:11px;
        }
        .preview-brand small {
          display:block;
          font-size:10px;
          line-height:1.45;
          color:#d4e3f8;
        }
        .preview-main {
          display:flex;
          flex-direction:column;
        }
        .preview-header {
          min-height:48px;
          padding:10px 14px;
          color:#f7fbff;
          display:flex;
          align-items:center;
          justify-content:space-between;
          gap:12px;
        }
        .preview-header strong {
          display:block;
          font-size:12px;
          margin-bottom:3px;
        }
        .preview-header span {
          display:block;
          font-size:10px;
          opacity:0.92;
        }
        .preview-surface {
          flex:1;
          padding:12px 14px;
          display:grid;
          gap:10px;
          background:
            radial-gradient(circle at top right, rgba(255,255,255,0.55), transparent 30%),
            linear-gradient(180deg, rgba(255,255,255,0.92) 0%, rgba(234,242,248,0.92) 100%);
        }
        .preview-strip {
          height:10px;
          border-radius:999px;
          opacity:0.92;
        }
        .preview-cards {
          display:grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap:8px;
        }
        .preview-mini-card {
          min-height:44px;
          border-radius:12px;
          background:rgba(255,255,255,0.82);
          border:1px solid rgba(16,36,60,0.08);
          box-shadow:0 8px 18px rgba(16,36,60,0.08);
        }
        .family-option {
          display:flex;
          justify-content:space-between;
          gap:12px;
          border:1px solid rgba(16,36,60,0.08);
          border-radius:14px;
          padding:12px;
          background:rgba(255,255,255,0.75);
        }
        .family-option.active {
          border-color:rgba(79,143,218,0.44);
          box-shadow:0 0 0 3px rgba(79,143,218,0.10);
        }
        .family-option strong {
          display:block;
          margin-bottom:4px;
          font-size:13px;
        }
        .family-option span {
          display:block;
          font-size:12px;
          color:var(--muted);
          line-height:1.5;
        }
        .family-option button {
          min-width:110px;
          min-height:38px;
          border-radius:12px;
          border:0;
          background:linear-gradient(180deg, #6aa8ed 0%, #4f8fda 100%);
          color:#fff;
          font-weight:800;
          cursor:pointer;
        }
        .family-option button[disabled] {
          cursor:default;
          background:rgba(79,143,218,0.18);
          color:#2a4e79;
        }
        .note {
          border-radius:16px;
          padding:14px 16px;
          background:rgba(216, 161, 95, 0.12);
          border:1px solid rgba(216, 161, 95, 0.18);
          color:#f3d7b4;
          font-size:12px;
          line-height:1.6;
          margin-top:16px;
        }
        @media (max-width: 900px) {
          .grid { grid-template-columns: 1fr; }
          .summary { width:100%; margin-left:0; }
          .row { grid-template-columns: 1fr; }
          .preview-page { grid-template-columns: 1fr; }
          .preview-brand { flex-direction:row; align-items:center; }
        }
      </style>
    </head>
    <body>
      <div class="wrap">
        <section class="head">
          <div>
            <strong>Supplier Tema Yönetimi</strong>
            <span>Firma renk aileleri yalnızca Creatro çekirdeğinden yönetilir. Araç firması ve acente ekranlarında bu ayar görünmez.</span>
          </div>
          <a href="/">Çekirdeğe Dön</a>
        </section>

        <section class="panel">
          <div class="toolbar">
            <input id="searchInput" type="search" placeholder="Firma adına göre filtrele" />
            <select id="typeFilter">
              <option value="">Tüm firma tipleri</option>
              <option value="vehicle">Araç firması</option>
              <option value="agency">Acente</option>
            </select>
            <div id="summary" class="summary">Liste yükleniyor...</div>
          </div>

          <div id="grid" class="grid"></div>

          <div class="note">
            Tema renk ailesi üyelik sırasında bir kez seçilir. Sonradan yalnızca Creatro merkez yönetimi bu alanı değiştirebilir. Sabit `Creatro` marka alanı tema dışında kalır; değişebilir alan yalnızca proje/acente header ve uygulama yüzeyidir.
          </div>
        </section>
      </div>

      <script>
        (function () {
          var API_BASE = '';
          var TOKEN_KEY = 'platform_core_token';
          var searchInput = document.getElementById('searchInput');
          var typeFilter = document.getElementById('typeFilter');
          var summary = document.getElementById('summary');
          var grid = document.getElementById('grid');

          function token() {
            return localStorage.getItem(TOKEN_KEY) || '';
          }

          function headers() {
            return { Authorization: 'Bearer ' + token() };
          }

          function esc(value) {
            return String(value || '')
              .replaceAll('&', '&amp;')
              .replaceAll('<', '&lt;')
              .replaceAll('>', '&gt;')
              .replaceAll('"', '&quot;');
          }

          async function ensureAccess() {
            var t = token();
            if (!t) {
              window.location.href = '/';
              return false;
            }
            var res = await fetch(API_BASE + '/auth/me', { headers: headers() });
            if (!res.ok) {
              localStorage.removeItem(TOKEN_KEY);
              window.location.href = '/';
              return false;
            }
            var me = await res.json();
            if (!['superadmin', 'superadmin_staff'].includes(String(me.role || '').toLowerCase())) {
              summary.textContent = 'Bu ekran yalnızca Creatro merkez yönetimi tarafından kullanılabilir.';
              grid.innerHTML = '';
              return false;
            }
            return true;
          }

          function swatches(colors) {
            return (colors || []).map(function (c) { return '<i style="background:' + esc(c) + ';"></i>'; }).join('');
          }

          function previewTheme(row, family) {
            var colors = (family && family.colors) || ['#0d3934', '#24b389', '#e4c067'];
            return ''
              + '<div class="preview">'
              +   '<div class="preview-top" style="background:linear-gradient(135deg,' + esc(colors[0]) + ' 0%,' + esc(colors[1]) + ' 100%);">'
              +     '<div><strong>Değişebilir Proje Header</strong><span>' + esc(row.name || 'Firma') + ' görünümü</span></div>'
              +     '<div class="badge" style="background:rgba(255,255,255,0.14);border-color:rgba(255,255,255,0.22);color:#fff;">' + esc(family.label || '') + '</div>'
              +   '</div>'
              +   '<div class="preview-page">'
              +     '<aside class="preview-brand">'
              +       '<div class="preview-brand-mark">CRT</div>'
              +       '<small>Creatro marka alanı sabittir. Bu bölüm temadan etkilenmez.</small>'
              +     '</aside>'
              +     '<div class="preview-main">'
              +       '<div class="preview-header" style="background:linear-gradient(135deg,' + esc(colors[0]) + ' 0%,' + esc(colors[1]) + ' 100%);">'
              +         '<div><strong>Acente / Proje Header</strong><span>Renk ailesi burada hissedilir</span></div>'
              +         '<div style="font-size:11px;font-weight:800;">' + esc(row.company_type_label || '-') + '</div>'
              +       '</div>'
              +       '<div class="preview-surface">'
              +         '<div class="preview-strip" style="background:linear-gradient(90deg,' + esc(colors[1]) + ' 0%,' + esc(colors[2]) + ' 100%);"></div>'
              +         '<div class="preview-cards">'
              +           '<div class="preview-mini-card"></div>'
              +           '<div class="preview-mini-card"></div>'
              +         '</div>'
              +       '</div>'
              +     '</div>'
              +   '</div>'
              + '</div>';
          }

          function render(rows) {
            var q = String(searchInput.value || '').trim().toLowerCase();
            var type = String(typeFilter.value || '').trim().toLowerCase();
            var filtered = (rows || []).filter(function (row) {
              var byName = !q || String(row.name || '').toLowerCase().includes(q) || String(row.code || '').toLowerCase().includes(q);
              var byType = !type || String(row.company_type || '').toLowerCase() === type;
              return byName && byType;
            });
            summary.textContent = filtered.length + ' firma listelendi.';
            if (!filtered.length) {
              grid.innerHTML = '';
              return;
            }
            grid.innerHTML = filtered.map(function (row) {
              var families = Object.entries(row.theme_families || {}).map(function (entry) {
                var key = entry[0];
                var family = entry[1] || {};
                var active = key === row.ui_theme_family;
                return ''
                  + '<div class="family-option' + (active ? ' active' : '') + '">'
                  +   '<div>'
                  +     '<strong>' + esc(family.label || key) + '</strong>'
                  +     '<span>' + esc(family.description || '') + '</span>'
                  +     '<div class="swatches">' + swatches(family.colors || []) + '</div>'
                  +   '</div>'
                  +   '<button data-company-id="' + esc(row.id) + '" data-family="' + esc(key) + '"' + (active ? ' disabled' : '') + '>'
                  +     (active ? 'Aktif Aile' : 'Aileyi Uygula')
                  +   '</button>'
                  + '</div>';
              }).join('');
              return ''
                + '<article class="card">'
                +   '<div class="card-top">'
                +     '<div>'
                +       '<strong>' + esc(row.name) + '</strong>'
                +       '<span>' + esc(row.code || '-') + ' | ' + esc(row.company_type_label || row.company_type || '-') + '</span>'
                +     '</div>'
                +     '<span class="badge">' + esc(row.current_theme_label || row.ui_theme_family || '-') + '</span>'
                +   '</div>'
                +   '<div class="list">'
                +     '<div class="row"><strong>Sistem Kimliği</strong><span>' + esc(row.id) + '</span></div>'
                +     '<div class="row"><strong>Tema Kodu</strong><span>' + esc(row.ui_theme_family || '-') + '</span></div>'
                +     '<div class="row"><strong>Yetki</strong><span>Bu alan yalnızca Creatro supplier admin panelinden değiştirilebilir.</span></div>'
                +     '<div class="row"><strong>Marka Kuralı</strong><span>Creatro logo alanı sabittir. Yalnızca header ve uygulama yüzeyi tema ailesinden etkilenir.</span></div>'
                +   '</div>'
                +   previewTheme(row, row.theme_families[row.ui_theme_family] || {})
                +   '<div class="family-list">' + families + '</div>'
                + '</article>';
            }).join('');
          }

          async function loadRows() {
            summary.textContent = 'Firma listesi yükleniyor...';
            var res = await fetch(API_BASE + '/supplier-theme-settings', { headers: headers() });
            var data = await res.json();
            if (!res.ok) {
              summary.textContent = data.detail || 'Firma listesi alınamadı.';
              grid.innerHTML = '';
              return;
            }
            render(Array.isArray(data) ? data : []);
            window.__themeRows = Array.isArray(data) ? data : [];
          }

          async function updateTheme(companyId, family) {
            var res = await fetch(API_BASE + '/supplier-theme-settings/' + encodeURIComponent(companyId), {
              method: 'PUT',
              headers: Object.assign({ 'Content-Type': 'application/json' }, headers()),
              body: JSON.stringify({ ui_theme_family: family })
            });
            var data = await res.json();
            if (!res.ok) {
              alert(data.detail || 'Tema güncellenemedi.');
              return;
            }
            await loadRows();
          }

          grid.addEventListener('click', function (event) {
            var btn = event.target.closest('button[data-company-id][data-family]');
            if (!btn || btn.disabled) return;
            updateTheme(btn.getAttribute('data-company-id'), btn.getAttribute('data-family'));
          });

          searchInput.addEventListener('input', function () {
            render(window.__themeRows || []);
          });
          typeFilter.addEventListener('change', function () {
            render(window.__themeRows || []);
          });

          ensureAccess().then(function (ok) {
            if (ok) loadRows();
          });
        })();
      </script>
    </body>
    </html>
    """


@app.post("/auth/login")
def auth_login(payload: dict, db: Session = Depends(get_db)):
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")
    user = _find_user_by_login_identifier(db, username)
    if not user or not user.is_active or not _verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=max(1, SESSION_IDLE_MINUTES))
    db.add(UserSession(user_id=user.id, token=token, expires_at=expires_at))
    db.commit()
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first() if user.tenant_id else None
    active_project = db.query(Project).filter(Project.id == user.active_project_id).first() if user.active_project_id else None
    token_limit = None if is_unlimited_token_user(user) else user.token_limit
    token_used = 0 if is_unlimited_token_user(user) else user.token_used
    token_remaining = None if token_limit is None else max(0, int(token_limit or 0) - int(token_used or 0))
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
        "user": {
            "id": user.id,
            "user_code": user.user_code,
            "username": user.username,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "tenant_name": tenant.name if tenant else None,
            "active_project_id": user.active_project_id,
            "active_project_name": active_project.name if active_project else None,
            "token_limit": token_limit,
            "token_used": token_used,
            "token_remaining": token_remaining,
            },
    }


@app.post("/auth/logout")
def auth_logout(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    db.query(UserSession).filter(UserSession.token == token).delete()
    db.commit()
    return {"ok": True}


@app.get("/auth/me")
def auth_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first() if current_user.tenant_id else None
    active_project = db.query(Project).filter(Project.id == current_user.active_project_id).first() if current_user.active_project_id else None
    token_limit = None if is_unlimited_token_user(current_user) else current_user.token_limit
    token_used = 0 if is_unlimited_token_user(current_user) else current_user.token_used
    token_remaining = None if token_limit is None else max(0, int(token_limit or 0) - int(token_used or 0))
    return {
        "id": current_user.id,
        "user_code": current_user.user_code,
        "username": current_user.username,
        "role": current_user.role,
        "tenant_id": current_user.tenant_id,
        "tenant_name": tenant.name if tenant else None,
        "active_project_id": current_user.active_project_id,
        "active_project_name": active_project.name if active_project else None,
        "is_active": current_user.is_active,
        "token_limit": token_limit,
        "token_used": token_used,
        "token_remaining": token_remaining,
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
    session = db.query(UserSession).filter(UserSession.token == token, UserSession.expires_at > now).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return {
        "expires_at": session.expires_at.isoformat(),
        "remaining_seconds": max(0, int((session.expires_at - now).total_seconds())),
        "idle_timeout_minutes": max(1, SESSION_IDLE_MINUTES),
    }


@app.get("/supplier-theme-settings")
def list_supplier_theme_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    current_user = require_theme_admin(current_user)
    rows = db.query(SupplierCompany).order_by(SupplierCompany.name.asc()).all()
    families = _theme_family_payload()
    return [
        {
            "id": row.id,
            "name": row.name,
            "code": f"SUP-{int(row.id):05d}",
            "company_type": row.company_type,
            "company_type_label": _company_type_label(row.company_type),
            "ui_theme_family": getattr(row, "ui_theme_family", None) or "zumrut_operasyon",
            "current_theme_label": families.get(getattr(row, "ui_theme_family", None) or "zumrut_operasyon", {}).get("label"),
            "theme_families": families,
        }
        for row in rows
    ]


@app.get("/supplier-theme-settings/current")
def current_supplier_theme_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    supplier_company_id = int(getattr(current_user, "supplier_company_id", 0) or 0)
    if supplier_company_id <= 0:
        return _theme_payload_for_company(None)
    row = db.query(SupplierCompany).filter(SupplierCompany.id == supplier_company_id).first()
    if not row:
        return _theme_payload_for_company(None)
    return _theme_payload_for_company(row)


@app.put("/supplier-theme-settings/{supplier_company_id}")
def update_supplier_theme_settings(
    supplier_company_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    current_user = require_theme_admin(current_user)
    row = db.query(SupplierCompany).filter(SupplierCompany.id == supplier_company_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="supplier company not found")
    family = str(payload.get("ui_theme_family") or "").strip()
    if family not in THEME_FAMILIES:
        raise HTTPException(status_code=400, detail="invalid theme family")
    row.ui_theme_family = family
    db.commit()
    return {
        "id": row.id,
        "name": row.name,
        "ui_theme_family": row.ui_theme_family,
        "current_theme_label": THEME_FAMILIES[row.ui_theme_family]["label"],
    }


@app.get("/company-card-draft")
def get_company_card_draft(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0)
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == tenant_id if tenant_id > 0 else ModuleData.tenant_id.is_(None),
            ModuleData.project_id == project_id if project_id is not None else ModuleData.project_id.is_(None),
            ModuleData.module_name == "fleet_company_card",
            ModuleData.entity_type == "draft",
        )
        .order_by(ModuleData.updated_at.desc(), ModuleData.id.desc())
        .first()
    )
    portal_status = _resolve_company_portal_status(
        db,
        tenant_id or None,
        (row.data or {}).get("company_type") if row and isinstance(row.data, dict) else None,
        (row.data or {}).get("tax_number") if row and isinstance(row.data, dict) else None,
        row.id if row else None,
    )
    return {
        "id": row.id if row else None,
        "tenant_id": tenant_id or None,
        "project_id": project_id,
        "data": _sanitize_company_card_draft(row.data if row else {}),
        "portal_status": portal_status,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


@app.put("/company-card-draft")
def save_company_card_draft(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0)
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    data = payload.get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="data must be an object")
    data = _sanitize_company_card_draft(data)
    if not _is_valid_contact_email(data.get("email")):
        raise HTTPException(status_code=400, detail="Firma e-postası geçersiz. @ işaretinden sonra en az bir nokta olmalıdır.")
    if not _is_valid_contact_email(data.get("authority_email")):
        raise HTTPException(status_code=400, detail="Yetkili e-postası geçersiz. @ işaretinden sonra en az bir nokta olmalıdır.")
    for person in data.get("responsible_people") or []:
        if isinstance(person, dict) and not _is_valid_contact_email(person.get("email")):
            raise HTTPException(status_code=400, detail="Yetkili ve sorumlular bölümündeki e-posta geçersiz. @ işaretinden sonra en az bir nokta olmalıdır.")
    raw_tax = re.sub(r"[^0-9]", "", str(data.get("tax_number") or "").strip())
    if raw_tax and not _normalize_tax_number_for_matching(raw_tax):
        raise HTTPException(status_code=400, detail="Vergi No / T.C. bilgisi geçersiz. Bilinmiyorsa firma için 2222222222, kişi için 11111111111 kullanın.")
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == tenant_id if tenant_id > 0 else ModuleData.tenant_id.is_(None),
            ModuleData.project_id == project_id if project_id is not None else ModuleData.project_id.is_(None),
            ModuleData.module_name == "fleet_company_card",
            ModuleData.entity_type == "draft",
        )
        .order_by(ModuleData.updated_at.desc(), ModuleData.id.desc())
        .first()
    )
    portal_status = _resolve_company_portal_status(
        db,
        tenant_id or None,
        data.get("company_type"),
        data.get("tax_number"),
        row.id if row else None,
    )
    data["portal_mode"] = str(portal_status["portal_mode"])

    if not row:
        row = ModuleData(
            tenant_id=tenant_id or None,
            project_id=project_id,
            module_name="fleet_company_card",
            entity_type="draft",
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
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "data": _sanitize_company_card_draft(row.data if isinstance(row.data, dict) else {}),
        "portal_status": portal_status,
    }


@app.get("/company-portal-status")
def get_company_portal_status(
    company_type: str = Query("agency"),
    tax_number: str = Query(""),
    draft_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0) or None
    return _resolve_company_portal_status(db, tenant_id, company_type, tax_number, draft_id)


@app.get("/company-code-suggestion")
def get_company_code_suggestion(
    company_type: str = Query("agency"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0) or None
    normalized = _normalize_company_type_for_code(company_type)
    return {
        "company_type": normalized,
        "prefix": _company_code_prefix(normalized),
        "suggested_code": _next_company_code(db, tenant_id, normalized),
    }


@app.get("/vehicle-license-rules")
def get_vehicle_license_rules(
    current_user: User = Depends(require_auth),
):
    return VEHICLE_LICENSE_RULES


def _get_module_list_row(
    db: Session,
    tenant_id: int | None,
    project_id: int | None,
    module_name: str,
):
    return (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == tenant_id if tenant_id else ModuleData.tenant_id.is_(None),
            ModuleData.project_id == project_id if project_id is not None else ModuleData.project_id.is_(None),
            ModuleData.module_name == module_name,
            ModuleData.entity_type == "list",
        )
        .order_by(ModuleData.updated_at.desc(), ModuleData.id.desc())
        .first()
    )


def _list_module_items(
    module_name: str,
    db: Session,
    current_user: User,
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0) or None
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    row = _get_module_list_row(db, tenant_id, project_id, module_name)
    return {
        "tenant_id": tenant_id,
        "project_id": project_id,
        "items": row.data if row and isinstance(row.data, list) else [],
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


def _save_module_items(
    module_name: str,
    payload: dict,
    db: Session,
    current_user: User,
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0) or None
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    items = payload.get("items")
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items must be a list")
    items = [item for item in items if isinstance(item, dict)]
    row = _get_module_list_row(db, tenant_id, project_id, module_name)
    if not row:
        row = ModuleData(
            tenant_id=tenant_id,
            project_id=project_id,
            module_name=module_name,
            entity_type="list",
            data=items,
            created_by_user_id=current_user.id,
            updated_by_user_id=current_user.id,
        )
        db.add(row)
    else:
        row.data = items
        row.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "items": row.data if isinstance(row.data, list) else [],
    }


def _determine_transfer_direction(route_text: str, project_city: str, operation_city: str) -> str:
    normalized_route = str(route_text or "").upper()
    base_city = str(project_city or operation_city or "").strip().upper()
    if not base_city:
        return "Geliş"
    if normalized_route.endswith(base_city) or (">" in normalized_route and normalized_route.split(">")[-1].strip() == base_city):
        return "Geliş"
    if normalized_route.startswith(base_city) or (">" in normalized_route and normalized_route.split(">")[0].strip() == base_city):
        return "Gidiş"
    return "Geliş"


def _build_transfer_item_from_ticket(ticket: dict, project_city: str, operation_city: str, index: int) -> dict:
    file_name = str(ticket.get("original_filename") or "").strip()
    passenger_name = str(ticket.get("passenger_name") or "").strip()
    flight_no = str(ticket.get("flight_no") or "").strip()
    route_text = str(ticket.get("route_text") or "").strip()
    estimated_time = str(ticket.get("estimated_time") or "").strip()
    flight_date = str(ticket.get("flight_date") or "").strip()
    parse_note = str(ticket.get("parse_note") or "").strip()
    upload_id = str(ticket.get("upload_id") or "").strip()
    service_type = "Geliş Transfer"
    direction_type = _determine_transfer_direction(route_text, project_city, operation_city)
    if direction_type == "Gidiş":
        service_type = "Gidiş Transfer"
    transfer_code = str(ticket.get("transfer_code") or "").strip()
    if not transfer_code:
        suffix = flight_no or passenger_name[:6].upper() or file_name[:6].upper() or f"KAYIT{index + 1}"
        suffix = re.sub(r"[^A-Z0-9]+", "", suffix.upper())[:10] or f"KAYIT{index + 1}"
        transfer_code = f"TRF-{suffix}"
    return {
        "transfer_code": transfer_code,
        "service_type": service_type,
        "guest_name": passenger_name or "-",
        "project_city": project_city,
        "person_count": str(ticket.get("person_count") or "1"),
        "pickup_text": route_text.split(">")[0].strip() if ">" in route_text else route_text,
        "dropoff_text": route_text.split(">")[-1].strip() if ">" in route_text else route_text,
        "direction_type": direction_type,
        "flight_no": flight_no,
        "transfer_date": flight_date,
        "transfer_time": estimated_time,
        "source_file": file_name,
        "source_upload_id": upload_id,
        "plan_note": parse_note,
    }


def _determine_transfer_direction_clean(route_text: str, project_city: str, operation_city: str) -> str:
    normalized_route = str(route_text or "").upper()
    base_city = str(project_city or operation_city or "").strip().upper()
    if not base_city:
        return "Geliş"
    if normalized_route.endswith(base_city) or (">" in normalized_route and normalized_route.split(">")[-1].strip() == base_city):
        return "Geliş"
    if normalized_route.startswith(base_city) or (">" in normalized_route and normalized_route.split(">")[0].strip() == base_city):
        return "Gidiş"
    return "Geliş"


def _build_transfer_item_from_ticket_clean(ticket: dict, project_city: str, operation_city: str, index: int) -> dict:
    file_name = str(ticket.get("original_filename") or "").strip()
    passenger_name = str(ticket.get("passenger_name") or "").strip()
    flight_no = str(ticket.get("flight_no") or "").strip()
    route_text = str(ticket.get("route_text") or "").strip()
    estimated_time = str(ticket.get("estimated_time") or "").strip()
    flight_date = str(ticket.get("flight_date") or "").strip()
    parse_note = str(ticket.get("parse_note") or "").strip()
    upload_id = str(ticket.get("upload_id") or "").strip()
    service_type = "Geliş Transfer"
    direction_type = _determine_transfer_direction_clean(route_text, project_city, operation_city)
    if direction_type == "Gidiş":
        service_type = "Gidiş Transfer"
    transfer_code = str(ticket.get("transfer_code") or "").strip()
    if not transfer_code:
        suffix = flight_no or passenger_name[:6].upper() or file_name[:6].upper() or f"KAYIT{index + 1}"
        suffix = re.sub(r"[^A-Z0-9]+", "", suffix.upper())[:10] or f"KAYIT{index + 1}"
        transfer_code = f"TRF-{suffix}"
    return {
        "transfer_code": transfer_code,
        "service_type": service_type,
        "guest_name": passenger_name or "-",
        "project_city": project_city,
        "person_count": str(ticket.get("person_count") or "1"),
        "pickup_text": route_text.split(">")[0].strip() if ">" in route_text else route_text,
        "dropoff_text": route_text.split(">")[-1].strip() if ">" in route_text else route_text,
        "direction_type": direction_type,
        "flight_no": flight_no,
        "transfer_date": flight_date,
        "transfer_time": estimated_time,
        "source_file": file_name,
        "source_upload_id": upload_id,
        "plan_note": parse_note,
        "imported_at": datetime.utcnow().isoformat(),
    }


@app.get("/vehicle-cards")
def list_vehicle_cards(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0)
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == tenant_id if tenant_id > 0 else ModuleData.tenant_id.is_(None),
            ModuleData.project_id == project_id if project_id is not None else ModuleData.project_id.is_(None),
            ModuleData.module_name == "fleet_vehicle_cards",
            ModuleData.entity_type == "list",
        )
        .order_by(ModuleData.updated_at.desc(), ModuleData.id.desc())
        .first()
    )
    data = row.data if row and isinstance(row.data, list) else []
    return {
        "tenant_id": tenant_id or None,
        "project_id": project_id,
        "items": data,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


@app.put("/vehicle-cards")
def save_vehicle_cards(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0)
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    items = payload.get("items")
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items must be a list")
    items = [item for item in items if isinstance(item, dict)]
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == tenant_id if tenant_id > 0 else ModuleData.tenant_id.is_(None),
            ModuleData.project_id == project_id if project_id is not None else ModuleData.project_id.is_(None),
            ModuleData.module_name == "fleet_vehicle_cards",
            ModuleData.entity_type == "list",
        )
        .order_by(ModuleData.updated_at.desc(), ModuleData.id.desc())
        .first()
    )
    if not row:
        row = ModuleData(
            tenant_id=tenant_id or None,
            project_id=project_id,
            module_name="fleet_vehicle_cards",
            entity_type="list",
            data=items,
            created_by_user_id=current_user.id,
            updated_by_user_id=current_user.id,
        )
        db.add(row)
    else:
        row.data = items
        row.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "items": row.data if isinstance(row.data, list) else [],
    }


@app.get("/driver-cards")
def list_driver_cards(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0)
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == tenant_id if tenant_id > 0 else ModuleData.tenant_id.is_(None),
            ModuleData.project_id == project_id if project_id is not None else ModuleData.project_id.is_(None),
            ModuleData.module_name == "fleet_driver_cards",
            ModuleData.entity_type == "list",
        )
        .order_by(ModuleData.updated_at.desc(), ModuleData.id.desc())
        .first()
    )
    data = [_normalize_driver_card_item(item) for item in (row.data if row and isinstance(row.data, list) else [])]
    return {
        "tenant_id": tenant_id or None,
        "project_id": project_id,
        "items": data,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


@app.put("/driver-cards")
def save_driver_cards(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0)
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    items = payload.get("items")
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items must be a list")
    items = [_normalize_driver_card_item(item) for item in items if isinstance(item, dict)]
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == tenant_id if tenant_id > 0 else ModuleData.tenant_id.is_(None),
            ModuleData.project_id == project_id if project_id is not None else ModuleData.project_id.is_(None),
            ModuleData.module_name == "fleet_driver_cards",
            ModuleData.entity_type == "list",
        )
        .order_by(ModuleData.updated_at.desc(), ModuleData.id.desc())
        .first()
    )
    if not row:
        row = ModuleData(
            tenant_id=tenant_id or None,
            project_id=project_id,
            module_name="fleet_driver_cards",
            entity_type="list",
            data=items,
            created_by_user_id=current_user.id,
            updated_by_user_id=current_user.id,
        )
        db.add(row)
    else:
        row.data = items
        row.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "items": row.data if isinstance(row.data, list) else [],
    }


@app.get("/greeter-cards")
def list_greeter_cards(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0)
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == tenant_id if tenant_id > 0 else ModuleData.tenant_id.is_(None),
            ModuleData.project_id == project_id if project_id is not None else ModuleData.project_id.is_(None),
            ModuleData.module_name == "fleet_greeter_cards",
            ModuleData.entity_type == "list",
        )
        .order_by(ModuleData.updated_at.desc(), ModuleData.id.desc())
        .first()
    )
    data = [_normalize_greeter_card_item(item) for item in (row.data if row and isinstance(row.data, list) else [])]
    return {
        "tenant_id": tenant_id or None,
        "project_id": project_id,
        "items": data,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


@app.put("/greeter-cards")
def save_greeter_cards(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0)
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    items = payload.get("items")
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items must be a list")
    items = [_normalize_greeter_card_item(item) for item in items if isinstance(item, dict)]
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == tenant_id if tenant_id > 0 else ModuleData.tenant_id.is_(None),
            ModuleData.project_id == project_id if project_id is not None else ModuleData.project_id.is_(None),
            ModuleData.module_name == "fleet_greeter_cards",
            ModuleData.entity_type == "list",
        )
        .order_by(ModuleData.updated_at.desc(), ModuleData.id.desc())
        .first()
    )
    if not row:
        row = ModuleData(
            tenant_id=tenant_id or None,
            project_id=project_id,
            module_name="fleet_greeter_cards",
            entity_type="list",
            data=items,
            created_by_user_id=current_user.id,
            updated_by_user_id=current_user.id,
        )
        db.add(row)
    else:
        row.data = items
        row.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "items": row.data if isinstance(row.data, list) else [],
    }


@app.get("/planning-ticket-batches")
def list_planning_ticket_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    return _list_module_items("planning_ticket_batches", db, current_user)


@app.put("/planning-ticket-batches")
def save_planning_ticket_batches(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    return _save_module_items("planning_ticket_batches", payload, db, current_user)


@app.get("/planning-transfer-lists")
def list_planning_transfer_lists(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    return _list_module_items("planning_transfer_lists", db, current_user)


@app.put("/planning-transfer-lists")
def save_planning_transfer_lists(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    return _save_module_items("planning_transfer_lists", payload, db, current_user)


@app.post("/planning-transfer-lists/import-from-tickets")
def import_planning_transfer_lists_from_tickets(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0) or None
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    requested_project_city = str(payload.get("project_city") or "").strip().upper()
    requested_operation_city = str(payload.get("operation_city") or "").strip().upper()
    ticket_row = _get_module_list_row(db, tenant_id, project_id, "planning_ticket_batches")
    transfer_row = _get_module_list_row(db, tenant_id, project_id, "planning_transfer_lists")
    ticket_items = ticket_row.data if ticket_row and isinstance(ticket_row.data, list) else []
    existing_items = transfer_row.data if transfer_row and isinstance(transfer_row.data, list) else []
    project_city = requested_project_city
    if not project_city and isinstance(existing_items, list):
        for item in existing_items:
            if isinstance(item, dict) and str(item.get("project_city") or "").strip():
                project_city = str(item.get("project_city") or "").strip().upper()
                break
    operation_city = requested_operation_city
    imported_items: list[dict] = []
    seen_sources = {
        (
            str(item.get("source_upload_id") or "").strip(),
            str(item.get("flight_no") or "").strip().upper(),
            str(item.get("guest_name") or "").strip().upper(),
        )
        for item in existing_items
        if isinstance(item, dict)
    }
    for index, ticket in enumerate(ticket_items):
        if not isinstance(ticket, dict):
            continue
        upload_status = str(ticket.get("upload_status") or "").strip().lower()
        if upload_status not in {"processed", "completed", "done"}:
            continue
        source_key = (
            str(ticket.get("upload_id") or "").strip(),
            str(ticket.get("flight_no") or "").strip().upper(),
            str(ticket.get("passenger_name") or "").strip().upper(),
        )
        if source_key in seen_sources:
            continue
        imported_items.append(_build_transfer_item_from_ticket_clean(ticket, project_city, operation_city, len(imported_items)))
        seen_sources.add(source_key)
    merged_items = imported_items + [item for item in existing_items if isinstance(item, dict)]
    saved = _save_module_items("planning_transfer_lists", {"items": merged_items}, db, current_user)
    saved["imported_count"] = len(imported_items)
    saved["project_city"] = project_city or None
    saved["operation_city"] = operation_city or None
    return saved


@app.post("/planning-transfer-lists/import-selected-tickets")
def import_planning_transfer_lists_from_selected_tickets(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0) or None
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    requested_project_city = str(payload.get("project_city") or "").strip().upper()
    requested_operation_city = str(payload.get("operation_city") or "").strip().upper()
    selected_tickets = payload.get("tickets")
    if not isinstance(selected_tickets, list) or not selected_tickets:
        raise HTTPException(status_code=400, detail="tickets must be a non-empty list")

    transfer_row = _get_module_list_row(db, tenant_id, project_id, "planning_transfer_lists")
    existing_items = transfer_row.data if transfer_row and isinstance(transfer_row.data, list) else []
    project_city = requested_project_city
    if not project_city and isinstance(existing_items, list):
        for item in existing_items:
            if isinstance(item, dict) and str(item.get("project_city") or "").strip():
                project_city = str(item.get("project_city") or "").strip().upper()
                break
    operation_city = requested_operation_city

    imported_items: list[dict] = []
    imported_upload_ids: list[int] = []
    seen_sources = {
        (
            str(item.get("source_upload_id") or "").strip(),
            str(item.get("flight_no") or "").strip().upper(),
            str(item.get("guest_name") or "").strip().upper(),
        )
        for item in existing_items
        if isinstance(item, dict)
    }

    for index, ticket in enumerate(selected_tickets):
        if not isinstance(ticket, dict):
            continue
        source_key = (
            str(ticket.get("upload_id") or "").strip(),
            str(ticket.get("flight_no") or "").strip().upper(),
            str(ticket.get("passenger_name") or "").strip().upper(),
        )
        if source_key in seen_sources:
            continue
        imported_items.append(_build_transfer_item_from_ticket_clean(ticket, project_city, operation_city, len(imported_items)))
        seen_sources.add(source_key)
        try:
            upload_id = int(ticket.get("upload_id") or 0)
            if upload_id > 0:
                imported_upload_ids.append(upload_id)
        except (TypeError, ValueError):
            pass

    merged_items = imported_items + [item for item in existing_items if isinstance(item, dict)]
    saved = _save_module_items("planning_transfer_lists", {"items": merged_items}, db, current_user)
    saved["imported_count"] = len(imported_items)
    saved["imported_upload_ids"] = imported_upload_ids
    saved["project_city"] = project_city or None
    saved["operation_city"] = operation_city or None
    return saved


@app.get("/planning-operation-slots")
def list_planning_operation_slots(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    return _list_module_items("planning_operation_slots", db, current_user)


@app.put("/planning-operation-slots")
def save_planning_operation_slots(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    return _save_module_items("planning_operation_slots", payload, db, current_user)


@app.post("/shared-ticket-upload")
async def shared_ticket_upload(
    files: list[UploadFile] = File(...),
    username: str = Form(...),
    password: str = Form(...),
    operation_city: str = Form(default=""),
    target_airports: str = Form(default=""),
    current_user: User = Depends(require_auth),
):
    auth_headers = _shared_parser_authorization(str(username or "").strip(), str(password or ""))
    token = auth_headers["Authorization"].replace("Bearer ", "", 1)
    multipart_files: list[tuple[str, str, bytes, str]] = []
    for file in files:
        content = await file.read()
        multipart_files.append(("files", file.filename or "dosya", content, file.content_type or "application/octet-stream"))
    body, boundary = _encode_multipart_form(
        {
            "operation_city": operation_city or "",
            "target_airports": target_airports or "",
        },
        multipart_files,
    )
    req = urllib.request.Request(
        f"{SHARED_PARSER_BASE_URL}/upload-many",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            "Host": "localhost:3000",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {"detail": raw or str(exc)}
        raise HTTPException(status_code=int(exc.code), detail=str(payload.get("detail") or "Ortak parser yükleme hatası."))
    return {
        "ok": True,
        "engine": "shared_parser",
        "source": "8000_reference",
        "result": payload,
        "file_count": len(multipart_files),
        "requested_by_user_id": current_user.id,
    }


@app.post("/shared-ticket-statuses")
def shared_ticket_statuses(
    payload: dict,
    current_user: User = Depends(require_auth),
):
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    upload_ids = payload.get("upload_ids") or []
    if not username or not password:
        raise HTTPException(status_code=400, detail="Kullanıcı bilgisi zorunludur.")
    if not isinstance(upload_ids, list) or not upload_ids:
        raise HTTPException(status_code=400, detail="upload_ids listesi zorunludur.")
    status_code, data = _json_request(
        f"{SHARED_PARSER_BASE_URL}/uploads/statuses",
        method="POST",
        payload={"upload_ids": upload_ids},
        headers=_shared_parser_authorization(username, password),
    )
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=str((data or {}).get("detail") or "Durum bilgisi alınamadı."))
    return {"ok": True, "items": data if isinstance(data, list) else []}


@app.get("/shared-ticket-upload/{upload_id}")
def shared_ticket_upload_detail(
    upload_id: int,
    username: str = Query(...),
    password: str = Query(...),
    current_user: User = Depends(require_auth),
):
    status_code, data = _json_request(
        f"{SHARED_PARSER_BASE_URL}/uploads/{int(upload_id)}",
        method="GET",
        headers=_shared_parser_authorization(username, password),
    )
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=str((data or {}).get("detail") or "Upload detayı alınamadı."))
    return {"ok": True, "item": data}


@app.get("/shared-ticket-detail/{upload_id}")
def shared_ticket_detail_direct(
    upload_id: int,
    username: str = Query(...),
    password: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    if not str(username or "").strip() or not str(password or ""):
        raise HTTPException(status_code=400, detail="Kullanıcı bilgisi zorunludur.")
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0) or None
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    query = db.query(Upload).filter(Upload.id == int(upload_id))
    if tenant_id is not None:
        query = query.filter(Upload.tenant_id == tenant_id)
    if project_id is not None:
        query = query.filter(Upload.project_id == project_id)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Upload bulunamadı.")
    return {
        "ok": True,
        "item": {
            "id": row.id,
            "original_filename": row.original_filename,
            "status": row.status,
            "error_message": row.error_message,
            "project_id": row.project_id,
            "operation_city": row.operation_city,
            "operation_code": row.operation_code,
            "parse_result": row.parse_result if isinstance(row.parse_result, dict) else {},
            "created_at": row.created_at.isoformat() if row.created_at else None,
        },
    }


@app.get("/management-responsibility-rules")
def list_management_responsibility_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    return _list_module_items("management_responsibility_rules", db, current_user)


@app.put("/management-responsibility-rules")
def save_management_responsibility_rules(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    return _save_module_items("management_responsibility_rules", payload, db, current_user)


@app.get("/management-integrations")
def list_management_integrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    return _list_module_items("management_integrations", db, current_user)


@app.put("/management-integrations")
def save_management_integrations(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    return _save_module_items("management_integrations", payload, db, current_user)


@app.get("/notification-preferences/current")
def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0)
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    module_name = f"notification_preferences_user_{current_user.id}"
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == tenant_id if tenant_id > 0 else ModuleData.tenant_id.is_(None),
            ModuleData.project_id == project_id if project_id is not None else ModuleData.project_id.is_(None),
            ModuleData.module_name == module_name,
            ModuleData.entity_type == "preferences",
        )
        .order_by(ModuleData.updated_at.desc(), ModuleData.id.desc())
        .first()
    )
    default_items = [
        {"event_code": "flight_critical_changed", "label": "Kritik uçuş değişikliği", "system": True, "email": False, "sms": True, "whatsapp": False},
        {"event_code": "greeter_waiting", "label": "Karşılamacı bekliyor", "system": True, "email": False, "sms": True, "whatsapp": True},
        {"event_code": "vehicle_departed", "label": "Araç yola çıktı", "system": True, "email": False, "sms": True, "whatsapp": False},
        {"event_code": "driver_picked_up", "label": "Yolcu alındı", "system": True, "email": False, "sms": True, "whatsapp": False},
        {"event_code": "driver_dropped_off", "label": "Yolcu bırakıldı", "system": True, "email": False, "sms": True, "whatsapp": False},
        {"event_code": "transfer_completed", "label": "Transfer tamamlandı", "system": True, "email": True, "sms": False, "whatsapp": False},
    ]
    data = row.data if row and isinstance(row.data, list) else default_items
    return {
        "user_id": current_user.id,
        "role": current_user.role,
        "items": data,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


@app.put("/notification-preferences/current")
def save_notification_preferences(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    items = payload.get("items")
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items must be a list")
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0)
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    module_name = f"notification_preferences_user_{current_user.id}"
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == tenant_id if tenant_id > 0 else ModuleData.tenant_id.is_(None),
            ModuleData.project_id == project_id if project_id is not None else ModuleData.project_id.is_(None),
            ModuleData.module_name == module_name,
            ModuleData.entity_type == "preferences",
        )
        .order_by(ModuleData.updated_at.desc(), ModuleData.id.desc())
        .first()
    )
    if not row:
        row = ModuleData(
            tenant_id=tenant_id or None,
            project_id=project_id,
            module_name=module_name,
            entity_type="preferences",
            data=items,
            created_by_user_id=current_user.id,
            updated_by_user_id=current_user.id,
        )
        db.add(row)
    else:
        row.data = items
        row.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return {"user_id": current_user.id, "updated_at": row.updated_at.isoformat() if row.updated_at else None, "items": row.data}


@app.get("/notification-history/current")
def get_notification_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0)
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    module_name = f"notification_history_user_{current_user.id}"
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == tenant_id if tenant_id > 0 else ModuleData.tenant_id.is_(None),
            ModuleData.project_id == project_id if project_id is not None else ModuleData.project_id.is_(None),
            ModuleData.module_name == module_name,
            ModuleData.entity_type == "history",
        )
        .order_by(ModuleData.updated_at.desc(), ModuleData.id.desc())
        .first()
    )
    default_items = [
        {"event_code": "greeter_waiting", "title": "Karşılama bilgisi gönderildi", "channel": "sms", "summary": "Yolcuya bekleme alanı bilgisi iletildi.", "created_at": datetime.now(timezone.utc).isoformat(), "status": "delivered"},
        {"event_code": "vehicle_departed", "title": "Araç yola çıktı bildirimi", "channel": "system", "summary": "Araç hareket bilgisi kayıt altına alındı.", "created_at": datetime.now(timezone.utc).isoformat(), "status": "delivered"},
    ]
    data = row.data if row and isinstance(row.data, list) else default_items
    return {
        "user_id": current_user.id,
        "role": current_user.role,
        "items": data,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


@app.put("/notification-history/current")
def save_notification_history(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    items = payload.get("items")
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items must be a list")
    tenant_id = int(getattr(current_user, "tenant_id", 0) or 0)
    project_id = int(getattr(current_user, "active_project_id", 0) or 0) or None
    module_name = f"notification_history_user_{current_user.id}"
    row = (
        db.query(ModuleData)
        .filter(
            ModuleData.tenant_id == tenant_id if tenant_id > 0 else ModuleData.tenant_id.is_(None),
            ModuleData.project_id == project_id if project_id is not None else ModuleData.project_id.is_(None),
            ModuleData.module_name == module_name,
            ModuleData.entity_type == "history",
        )
        .order_by(ModuleData.updated_at.desc(), ModuleData.id.desc())
        .first()
    )
    if not row:
        row = ModuleData(
            tenant_id=tenant_id or None,
            project_id=project_id,
            module_name=module_name,
            entity_type="history",
            data=items,
            created_by_user_id=current_user.id,
            updated_by_user_id=current_user.id,
        )
        db.add(row)
    else:
        row.data = items
        row.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return {"user_id": current_user.id, "updated_at": row.updated_at.isoformat() if row.updated_at else None, "items": row.data}


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
            "created_at": row.created_at.isoformat() if row.created_at else None,
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
    token_balance = max(0, int(payload.get("token_balance") or 0))
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if db.query(Tenant).filter(func.lower(Tenant.name) == name.lower()).first():
        raise HTTPException(status_code=409, detail="tenant already exists")
    tenant = Tenant(name=name, token_balance=token_balance, is_active=True)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    _ensure_management_project_for_tenant(db, int(tenant.id))
    db.commit()
    return {"id": tenant.id, "name": tenant.name, "token_balance": tenant.token_balance, "is_active": tenant.is_active}


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
        rows = [row for row in rows if _can_user_access_project(db, current_user, row)]
    tenant_map = {row.id: row.name for row in db.query(Tenant).filter(Tenant.id.in_({int(r.tenant_id) for r in rows if r.tenant_id is not None})).all()} if rows else {}
    return [
        {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "tenant_name": tenant_map.get(row.tenant_id),
            "name": row.name,
            "city": row.city,
            "operation_code": row.operation_code,
            "system_code": row.system_code,
            "token_limit": row.token_limit,
            "token_used": row.token_used,
            "is_active": row.is_active,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@app.post("/projects")
def create_project(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    current_user = require_company_admin(current_user)
    tenant_id = int(payload.get("tenant_id") or current_user.tenant_id or 0)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    if not is_superadmin(current_user) and tenant_id != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="cannot create project in another tenant")
    name = str(payload.get("name") or "").strip()
    city = _normalize_project_city(payload.get("city"))
    operation_code = str(payload.get("operation_code") or "").strip().upper()
    system_code = _normalize_project_system_code(payload.get("system_code")) or _generate_project_system_code(db, tenant_id)
    start_date = _normalize_iso_date_or_none(payload.get("start_date"), "start_date")
    end_date = _normalize_iso_date_or_none(payload.get("end_date"), "end_date")
    token_limit = payload.get("token_limit")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if city not in ALLOWED_PROJECT_CITIES:
        raise HTTPException(status_code=400, detail="city is invalid")
    if not operation_code or len(operation_code) > 9:
        raise HTTPException(status_code=400, detail="operation_code is required and max 9 chars")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="end_date must be >= start_date")
    if db.query(Project).filter(Project.tenant_id == tenant_id, Project.operation_code == operation_code).first():
        raise HTTPException(status_code=409, detail="operation_code already exists")
    if db.query(Project).filter(Project.tenant_id == tenant_id, Project.system_code == system_code).first():
        raise HTTPException(status_code=409, detail="system_code already exists")
    project = Project(
        tenant_id=tenant_id,
        name=name,
        city=city,
        operation_code=operation_code,
        system_code=system_code,
        start_date=start_date,
        end_date=end_date,
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
        "tenant_id": project.tenant_id,
        "name": project.name,
        "city": project.city,
        "operation_code": project.operation_code,
        "system_code": project.system_code,
    }


@app.get("/users")
def list_users(
    tenant_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    current_user = require_company_admin(current_user)
    query = db.query(User)
    if is_superadmin(current_user):
        if tenant_id is not None:
            query = query.filter(User.tenant_id == tenant_id)
    else:
        query = query.filter(User.tenant_id == current_user.tenant_id, User.id != current_user.id)
    rows = query.order_by(User.created_at.desc()).all()
    if not is_superadmin(current_user):
        rows = [row for row in rows if role_level(row.role) < role_level(current_user.role)]
    tenant_map = {row.id: row.name for row in db.query(Tenant).filter(Tenant.id.in_({int(r.tenant_id) for r in rows if r.tenant_id is not None})).all()} if rows else {}
    supplier_map = _supplier_payload_map(db, [int(r.supplier_company_id) for r in rows if r.supplier_company_id is not None])
    return [
        {
            "id": row.id,
            "user_code": row.user_code,
            "tenant_id": row.tenant_id,
            "tenant_name": tenant_map.get(row.tenant_id),
            "username": row.username,
            "email": row.email,
            "phone": row.phone,
            "role": row.role,
            "supplier_company_id": row.supplier_company_id,
            "supplier_company_name": supplier_map.get(int(row.supplier_company_id or 0), {}).get("name"),
            "supplier_company_type": supplier_map.get(int(row.supplier_company_id or 0), {}).get("company_type"),
            "active_project_id": row.active_project_id,
            "is_active": row.is_active,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@app.post("/users")
def create_user(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    current_user = require_company_admin(current_user)
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    role = normalize_role(str(payload.get("role") or "tenant_operator"))
    email = _normalize_login_email(payload.get("email"))
    tc_kimlik_no = _normalize_tc_kimlik_no(payload.get("tc_kimlik_no"))
    passport_no = _normalize_passport_no(payload.get("passport_no"))
    phone = _normalize_phone(payload.get("phone"))
    company_name = str(payload.get("company_name") or "").strip()
    company_type = _normalize_company_type_for_code(payload.get("company_type"))
    raw_supplier_company_id = payload.get("supplier_company_id")
    raw_active_project_id = payload.get("active_project_id")
    tenant_id = int(payload.get("tenant_id") or current_user.tenant_id or 0)
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password are required")
    if role not in ALLOWED_USER_ROLES:
        raise HTTPException(status_code=400, detail="invalid role")
    if role_level(role) > role_level(current_user.role) and not is_superadmin(current_user):
        raise HTTPException(status_code=403, detail="insufficient role delegation authority")
    company_required = role in {"tenant_operator", "tenant_manager", "tenant_admin", "supplier_admin"} and is_superadmin(current_user)
    target_supplier_type = "vehicle" if role == "supplier_admin" else ("agency" if role in {"tenant_operator", "tenant_manager", "tenant_admin"} else None)
    if company_required and not tenant_id and not company_name:
        raise HTTPException(status_code=400, detail="company_name is required for agency and vehicle company memberships")
    if not tenant_id and role != "superadmin" and company_name:
        existing_tenant = db.query(Tenant).filter(func.lower(Tenant.name) == company_name.lower()).first()
        if existing_tenant:
            tenant_id = int(existing_tenant.id)
        else:
            tenant = Tenant(name=company_name, token_balance=0, is_active=True)
            db.add(tenant)
            db.flush()
            tenant_id = int(tenant.id)
            _ensure_management_project_for_tenant(db, tenant_id)
    if not tenant_id and role != "superadmin":
        raise HTTPException(status_code=400, detail="tenant_id is required")
    if not is_superadmin(current_user) and tenant_id != int(current_user.tenant_id or 0):
        raise HTTPException(status_code=403, detail="cannot create user in another tenant")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="username already exists")
    if email and db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(status_code=409, detail="email already exists")
    supplier_company_id = None
    if raw_supplier_company_id not in (None, ""):
        supplier_company_id = int(raw_supplier_company_id)
        supplier = db.query(SupplierCompany).filter(SupplierCompany.id == supplier_company_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="supplier company not found")
        if int(supplier.tenant_id or 0) != tenant_id:
            raise HTTPException(status_code=403, detail="supplier company tenant mismatch")
        if target_supplier_type and str(getattr(supplier, "company_type", "") or "").strip().lower() != target_supplier_type:
            raise HTTPException(status_code=400, detail="supplier company type mismatch")
    elif target_supplier_type and tenant_id > 0 and company_name:
        existing_supplier = (
            db.query(SupplierCompany)
            .filter(
                SupplierCompany.tenant_id == tenant_id,
                SupplierCompany.company_type == target_supplier_type,
                func.lower(SupplierCompany.name) == company_name.lower(),
            )
            .first()
        )
        if existing_supplier:
            supplier_company_id = int(existing_supplier.id)
        else:
            supplier = SupplierCompany(
                tenant_id=tenant_id,
                name=company_name,
                company_type=target_supplier_type,
                is_active=True,
            )
            db.add(supplier)
            db.flush()
            supplier_company_id = int(supplier.id)
    active_project_id = None
    if raw_active_project_id not in (None, ""):
        active_project_id = int(raw_active_project_id)
        project = db.query(Project).filter(Project.id == active_project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="project not found")
        if int(project.tenant_id or 0) != tenant_id:
            raise HTTPException(status_code=403, detail="project tenant mismatch")
    user = User(
        tenant_id=tenant_id if role != "superadmin" else None,
        username=username,
        user_code=_generate_unique_user_code(db, tc_kimlik_no=tc_kimlik_no, passport_no=passport_no),
        email=email,
        tc_kimlik_no=tc_kimlik_no,
        passport_no=passport_no,
        phone=phone,
        password_hash=_hash_password(password),
        role=role,
        supplier_company_id=supplier_company_id,
        active_project_id=active_project_id,
        is_active=True,
        token_used=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "user_code": user.user_code,
        "tenant_id": user.tenant_id,
        "username": user.username,
        "role": user.role,
        "active_project_id": user.active_project_id,
        "is_active": user.is_active,
    }
