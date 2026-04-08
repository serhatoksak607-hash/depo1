import io
import io
import os
import shutil
import json
import re
import unicodedata
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

import fitz
import pytesseract
from PIL import Image
from pypdf import PdfReader

from .db import SessionLocal
from .iata_tr import IATA_EQUIVALENT_GROUPS
from .models import ModuleData, OpsEvent, Project, Tenant, Transfer, Upload, User
from .ops_events import (
    EVENT_TRANSFER_UPDATED,
    detect_ops_events_from_text,
    normalize_event_types,
)

_TR_ASCII_MAP = str.maketrans(
    {
        ord("\u00e7"): "c",
        ord("\u00c7"): "C",
        ord("\u011f"): "g",
        ord("\u011e"): "G",
        ord("\u0131"): "i",
        ord("\u0130"): "I",
        ord("\u00f6"): "o",
        ord("\u00d6"): "O",
        ord("\u015f"): "s",
        ord("\u015e"): "S",
        ord("\u00fc"): "u",
        ord("\u00dc"): "U",
    }
)
from .parser import parse_ticket_text


MIN_TEXT_LENGTH = 30
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
DEFAULT_TENANT_ID = os.getenv("DEFAULT_TENANT_ID")
DEFAULT_EVENT_ID = os.getenv("DEFAULT_EVENT_ID")
LICENSE_CONSUME_URL = os.getenv("LICENSE_CONSUME_URL", "").strip()
LICENSE_BEARER = os.getenv("LICENSE_BEARER", "").strip()
TOKEN_COST_PER_TICKET = int(os.getenv("TOKEN_COST_PER_TICKET", "1"))
TOKEN_COST_PER_FLIGHT = int(os.getenv("TOKEN_COST_PER_FLIGHT", "1"))
LICENSE_TIMEOUT_SEC = float(os.getenv("LICENSE_TIMEOUT_SEC", "8"))

_TR_ASCII_MAP = str.maketrans(
    {
        "ç": "c", "Ç": "C",
        "ğ": "g", "Ğ": "G",
        "ı": "i", "İ": "I",
        "ö": "o", "Ö": "O",
        "ş": "s", "Ş": "S",
        "ü": "u", "Ü": "U",
    }
)


def _configure_tesseract() -> None:
    if shutil.which("tesseract"):
        return
    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            return


_configure_tesseract()


def _extract_pdf_text(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    texts = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts).strip()


def _build_lines_from_words(words: list[tuple], y_tolerance: float = 3.0) -> list[tuple[float, str]]:
    ordered = sorted(words or [], key=lambda item: (round(float(item[1]), 1), float(item[0])))
    lines: list[dict] = []
    for word in ordered:
        x0, y0, x1, y1, text, *_rest = word
        token = str(text or "").strip()
        if not token:
            continue
        target = None
        for line in lines:
            if abs(float(line["y"]) - float(y0)) <= y_tolerance:
                target = line
                break
        if target is None:
            target = {"y": float(y0), "parts": []}
            lines.append(target)
        target["parts"].append((float(x0), token))
    out: list[tuple[float, str]] = []
    for line in lines:
        text = " ".join(part for _x, part in sorted(line["parts"], key=lambda item: item[0])).strip()
        if text:
            out.append((float(line["y"]), text))
    return out


def _extract_pdf_structured_finance_text(file_path: Path) -> str:
    finance_keywords = ("TKM", "TBU", "KDV", "TOPLAM", "TOTAL", "BASE", "FARE", "ESAS", "VERGI", "TAX", "PAYMENT", "ODEME", "RESTR", "ENDORSMEN", "KISITLAMA", "YR", "VQ", "TRY")
    doc = fitz.open(file_path)
    snippets: list[str] = []
    try:
        for page_index, page in enumerate(doc):
            lines = _build_lines_from_words(page.get_text("words"))
            if not lines:
                continue
            anchor_ys = [
                y for y, text in lines
                if any(label in text.upper() for label in ("KISITLAMA", "ENDORSMEN", "RESTR", "ODEME", "PAYMENT", "ESAS", "BASE FARE", "TOPLAM", "TOTAL"))
            ]
            y_min = min(anchor_ys) - 4 if anchor_ys else None
            y_max = max(anchor_ys) + 20 if anchor_ys else None
            picked: list[str] = []
            for y, text in lines:
                upper = text.upper()
                in_band = y_min is not None and y_max is not None and y_min <= y <= y_max
                if in_band or any(keyword in upper for keyword in finance_keywords):
                    picked.append(text)
            if picked:
                snippets.append(f"[STRUCTURED_PAGE_{page_index + 1}]\n" + "\n".join(picked))
    finally:
        doc.close()
    return "\n".join(snippets).strip()


def _ocr_image(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    return (pytesseract.image_to_string(image, lang="eng") or "").strip()


def _ocr_pdf(file_path: Path) -> str:
    doc = fitz.open(file_path)
    texts = []
    try:
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            texts.append(_ocr_image(pix.tobytes("png")))
    finally:
        doc.close()
    return "\n".join(filter(None, texts)).strip()


def _extract_text(file_path: Path, pricing_scan_enabled: bool = False) -> tuple[str, str]:
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        raw_text = _extract_pdf_text(file_path)
        if pricing_scan_enabled:
            structured_text = _extract_pdf_structured_finance_text(file_path)
            if structured_text:
                merged_parts = [part.strip() for part in [raw_text, structured_text] if str(part or "").strip()]
                raw_text = "\n".join(merged_parts).strip()
        method = "pdf_text"

        if len(raw_text.strip()) < MIN_TEXT_LENGTH:
            raw_text = _ocr_pdf(file_path)
            method = "ocr"
        return raw_text.strip(), method

    if suffix in IMAGE_EXTENSIONS:
        raw_text = _ocr_image(file_path.read_bytes())
        return raw_text.strip(), "ocr"

    raise ValueError(f"Unsupported extension for extraction: {suffix}")


def _create_or_update_transfer(
    upload_id: int,
    parsed_payload: dict,
    confidence: float,
    needs_review: bool,
    db,
) -> tuple[Transfer, bool, dict]:
    parsed = parsed_payload or {}
    transfer = db.query(Transfer).filter(Transfer.upload_id == upload_id).first()
    existed = transfer is not None
    changed_fields: dict[str, dict[str, str | None]] = {}
    if not transfer:
        transfer = Transfer(upload_id=upload_id)
        db.add(transfer)
    else:
        transfer.upload_id = upload_id

    field_map = {
        "airline": (parsed.get("airline") or "unknown").lower(),
        "passenger_name": parsed.get("passenger_name"),
        "passenger_gender": parsed.get("gender"),
        "pnr": parsed.get("pnr"),
        "flight_no": parsed.get("flight_no"),
        "flight_date": parsed.get("date"),
        "flight_time": parsed.get("time"),
        "trip_type": parsed.get("trip_type"),
        "outbound_date": parsed.get("outbound_date"),
        "return_date": parsed.get("return_date"),
        "segment_count": parsed.get("segment_count"),
        "outbound_departure_date": parsed.get("outbound_departure_date"),
        "outbound_departure_time": parsed.get("outbound_departure_time"),
        "outbound_arrival_date": parsed.get("outbound_arrival_date"),
        "outbound_arrival_time": parsed.get("outbound_arrival_time"),
        "return_departure_date": parsed.get("return_departure_date"),
        "return_departure_time": parsed.get("return_departure_time"),
        "return_arrival_date": parsed.get("return_arrival_date"),
        "return_arrival_time": parsed.get("return_arrival_time"),
        "pickup_location": parsed.get("from"),
        "dropoff_location": parsed.get("to"),
        "payment_type": parsed.get("payment_type"),
        "issue_date": parsed.get("issue_date"),
        "currency": parsed.get("currency"),
        "total_amount": parsed.get("total_amount"),
        "base_fare": parsed.get("base_fare"),
        "tax_total": parsed.get("tax_total"),
        "tax_breakdown": parsed.get("tax_breakdown"),
        "matrah": parsed.get("matrah"),
        "kdv": parsed.get("kdv"),
        "toplam_tutar": parsed.get("toplam_tutar"),
    }
    for attr, new_value in field_map.items():
        old_value = getattr(transfer, attr, None)
        if existed and old_value != new_value:
            changed_fields[attr] = {"old": old_value, "new": new_value}
        setattr(transfer, attr, new_value)

    transfer.status = transfer.status or "unassigned"
    transfer.confidence = confidence
    transfer.needs_review = needs_review
    transfer.pricing_visibility = transfer.pricing_visibility or "masked"
    transfer.raw_parse = parsed_payload
    return transfer, bool(changed_fields), changed_fields


def _create_ops_events(
    db,
    transfer: Transfer,
    upload_id: int,
    tenant_id: int | None,
    event_types: list[str],
    parsed_payload: dict,
    changed_fields: dict,
) -> None:
    for event_type in normalize_event_types(event_types):
        db.add(
            OpsEvent(
                tenant_id=str(tenant_id) if tenant_id is not None else DEFAULT_TENANT_ID,
                event_id=DEFAULT_EVENT_ID,
                event_type=event_type,
                related_transfer_id=transfer.id,
                payload={
                    "upload_id": upload_id,
                    "parsed": parsed_payload,
                    "changed_fields": changed_fields or None,
                },
            )
        )


def _normalize_person_name_for_match(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    txt = raw.translate(_TR_ASCII_MAP)
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = txt.encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^A-Za-z0-9\\s]", " ", txt).upper()
    txt = re.sub(r"\\s+", " ", txt).strip()
    return txt


def _compact_person_name(value: str | None) -> str:
    return _normalize_person_name_for_match(value).replace(" ", "")


def _kayit_name_candidates(data_obj: dict | None) -> list[str]:
    d = data_obj if isinstance(data_obj, dict) else {}
    out: list[str] = []
    pairs = [
        (d.get("isim"), d.get("soyisim")),
        (d.get("f_isim"), d.get("f_soyisim")),
        (d.get("ad"), d.get("soyad")),
    ]
    for a, b in pairs:
        name = (str(a or "").strip() + " " + str(b or "").strip()).strip()
        if name and name not in out:
            out.append(name)
    for key in ("full_name", "ad_soyad", "adsoyad", "f_adsoyad", "passenger_name"):
        v = str(d.get(key) or "").strip()
        if v and v not in out:
            out.append(v)
    return out


def _find_kayit_row_by_passenger_name(db, tenant_id: int, project_id: int | None, passenger_name: str | None):
    key = _compact_person_name(passenger_name)
    if not key:
        return None
    q = db.query(ModuleData).filter(
        ModuleData.module_name == "kayit",
        ModuleData.tenant_id == int(tenant_id),
    )
    if project_id is not None:
        q = q.filter(ModuleData.project_id == int(project_id))
    rows = q.order_by(ModuleData.created_at.desc(), ModuleData.id.desc()).all()
    best = None
    best_score = -1
    for row in rows:
        data_obj = row.data if isinstance(row.data, dict) else {}
        for cand in _kayit_name_candidates(data_obj):
            cand_key = _compact_person_name(cand)
            if not cand_key:
                continue
            if cand_key == key:
                return row
            score = 0
            if key and cand_key and (key in cand_key or cand_key in key):
                diff = abs(len(cand_key) - len(key))
                if diff <= 2:
                    score = 60 - diff
            if score > best_score:
                best_score = score
                best = row
    return best if best_score >= 60 else None


def _build_transfer_card_summary(transfer: Transfer) -> str:
    route = " / ".join(
        [x for x in [str(transfer.pickup_location or "").strip(), str(transfer.dropoff_location or "").strip()] if x]
    ) or "-"
    flight_part = " ".join([x for x in [str(transfer.flight_no or "").strip(), str(transfer.flight_date or "").strip(), str(transfer.flight_time or "").strip()] if x]).strip() or "-"
    pnr = str(transfer.pnr or "").strip() or "-"
    return f"Uçuş: {flight_part} | PNR: {pnr} | Rota: {route}"


def _sync_transfer_to_kayit_card(db, transfer: Transfer) -> None:
    if not transfer:
        return
    tenant_id = int(transfer.tenant_id or 0)
    if tenant_id <= 0:
        return
    project_id = int(transfer.project_id) if transfer.project_id is not None else None
    target_row = None
    if getattr(transfer, "participant_kayit_id", None):
        target_row = db.query(ModuleData).filter(
            ModuleData.id == int(transfer.participant_kayit_id),
            ModuleData.module_name == "kayit",
            ModuleData.tenant_id == tenant_id,
        ).first()
    if not target_row:
        target_row = _find_kayit_row_by_passenger_name(db, tenant_id, project_id, transfer.passenger_name)
    if not target_row:
        return
    transfer.participant_kayit_id = int(target_row.id)
    data_obj = target_row.data if isinstance(target_row.data, dict) else {}
    canonical_name = next((x for x in _kayit_name_candidates(data_obj) if str(x or "").strip()), "")
    if canonical_name:
        transfer.passenger_name = canonical_name
    phone = str(data_obj.get("telefon") or data_obj.get("f_telefon") or "").strip()
    if phone and not str(transfer.participant_phone or "").strip():
        transfer.participant_phone = phone
    data_obj["transfer"] = _build_transfer_card_summary(transfer)
    data_obj["f_transfer"] = data_obj["transfer"]
    data_obj["transfer_flight_no"] = transfer.flight_no or ""
    data_obj["transfer_flight_date"] = transfer.flight_date or ""
    data_obj["transfer_flight_time"] = transfer.flight_time or ""
    data_obj["transfer_pnr"] = transfer.pnr or ""
    data_obj["transfer_pickup_time"] = transfer.pickup_time or ""
    data_obj["transfer_transfer_point"] = transfer.transfer_point or ""
    data_obj["transfer_vehicle_code"] = transfer.vehicle_code or ""
    data_obj["transfer_linked_transfer_id"] = int(transfer.id or 0) or None
    target_row.data = data_obj


def _consume_remote_license_token(cost: int = 1) -> dict:
    if not LICENSE_CONSUME_URL or not LICENSE_BEARER:
        return {"enabled": False, "ok": None, "detail": "license consume not configured"}

    body = f"cost={max(1, int(cost))}".encode("utf-8")
    req = urlrequest.Request(
        LICENSE_CONSUME_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {LICENSE_BEARER}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urlrequest.urlopen(req, timeout=LICENSE_TIMEOUT_SEC) as resp:
            status = int(resp.getcode())
            payload_raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(payload_raw) if payload_raw else {}
            return {"enabled": True, "ok": 200 <= status < 300, "status": status, "response": payload}
    except urlerror.HTTPError as exc:
        payload_raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        try:
            payload = json.loads(payload_raw) if payload_raw else {}
        except Exception:
            payload = {"raw": payload_raw}
        return {"enabled": True, "ok": False, "status": int(exc.code), "response": payload}
    except Exception as exc:
        return {"enabled": True, "ok": False, "status": None, "error": str(exc)}


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _calculate_token_cost(parsed_payload: dict | None) -> dict:
    parsed = parsed_payload or {}
    ticket_cost = max(0, TOKEN_COST_PER_TICKET)
    segment_cost_unit = max(0, TOKEN_COST_PER_FLIGHT)

    segments = parsed.get("segments") or []
    if isinstance(segments, list) and segments:
        flight_count = len(segments)
    else:
        flight_count = _safe_int(parsed.get("segment_count"), 0)
        if flight_count <= 0 and parsed.get("flight_no"):
            flight_count = 1

    total = ticket_cost + max(0, flight_count) * segment_cost_unit
    return {
        "ticket_cost": ticket_cost,
        "flight_count": max(0, flight_count),
        "flight_unit_cost": segment_cost_unit,
        "total_cost": total,
    }


def _consume_internal_credits(db, upload: Upload, cost: int) -> dict:
    amount = max(0, int(cost))
    if amount <= 0:
        return {"enabled": True, "ok": True, "cost": 0}

    tenant_id = upload.tenant_id
    user_id = upload.user_id
    project_id = upload.project_id
    if not tenant_id:
        return {"enabled": False, "ok": None, "detail": "tenant not set on upload"}

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.is_active.is_(True)).first()
    if not tenant:
        return {"enabled": True, "ok": False, "detail": "tenant not found or inactive"}

    user = None
    unlimited_admin = False
    if user_id:
        user = (
            db.query(User)
            .filter(User.id == user_id, User.is_active.is_(True))
            .first()
        )
        if not user:
            return {"enabled": True, "ok": False, "detail": "user not found or inactive"}
        role_key = str(getattr(user, "role", "") or "").strip().lower()
        username_key = str(getattr(user, "username", "") or "").strip().lower()
        unlimited_admin = role_key == "superadmin" or username_key == "creatro"
        if (not unlimited_admin) and user.tenant_id != tenant_id:
            return {"enabled": True, "ok": False, "detail": "user tenant mismatch"}
        if (not unlimited_admin) and user.token_limit is not None and user.token_used + amount > user.token_limit:
            return {
                "enabled": True,
                "ok": False,
                "detail": "user_token_limit_exceeded",
                "user_limit": user.token_limit,
                "user_used": user.token_used,
                "cost": amount,
            }

    if (not unlimited_admin) and tenant.token_balance < amount:
        return {
            "enabled": True,
            "ok": False,
            "detail": "insufficient_tenant_tokens",
            "tenant_balance": tenant.token_balance,
            "cost": amount,
        }

    project = None
    if project_id:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.tenant_id == tenant_id, Project.is_active.is_(True))
            .first()
        )
        if not project:
            return {"enabled": True, "ok": False, "detail": "project not found or inactive"}
        if (not unlimited_admin) and project.token_limit is not None and project.token_used + amount > project.token_limit:
            return {
                "enabled": True,
                "ok": False,
                "detail": "project_token_limit_exceeded",
                "project_limit": project.token_limit,
                "project_used": project.token_used,
                "cost": amount,
            }

    if not unlimited_admin:
        tenant.token_balance -= amount
    if user is not None and not unlimited_admin:
        user.token_used = int(user.token_used or 0) + amount
    if project is not None and not unlimited_admin:
        project.token_used = int(project.token_used or 0) + amount

    return {
        "enabled": True,
        "ok": True,
        "cost": amount,
        "tenant_balance": tenant.token_balance,
        "user_used": int(user.token_used or 0) if user is not None else None,
        "project_used": int(project.token_used or 0) if project is not None else None,
        "unlimited_admin": unlimited_admin,
    }


def _auto_center_from_parsed(parsed: dict | None) -> list[str] | None:
    payload = parsed or {}
    segments = payload.get("segments") or []
    dep_counts: dict[str, int] = {}
    arr_counts: dict[str, int] = {}

    def _inc(counter: dict[str, int], code: str | None):
        if not code:
            return
        c = str(code).strip().upper()
        if len(c) != 3 or not c.isalpha():
            return
        counter[c] = counter.get(c, 0) + 1

    if isinstance(segments, list) and segments:
        for s in segments:
            if not isinstance(s, dict):
                continue
            _inc(dep_counts, s.get("from"))
            _inc(arr_counts, s.get("to"))
    else:
        _inc(dep_counts, payload.get("from"))
        _inc(arr_counts, payload.get("to"))

    candidates = set(dep_counts) | set(arr_counts)
    if not candidates:
        return None

    both = [c for c in candidates if dep_counts.get(c, 0) > 0 and arr_counts.get(c, 0) > 0]
    pool = both or list(candidates)
    best = max(
        pool,
        key=lambda c: (
            min(dep_counts.get(c, 0), arr_counts.get(c, 0)),
            dep_counts.get(c, 0) + arr_counts.get(c, 0),
            arr_counts.get(c, 0),
            dep_counts.get(c, 0),
        ),
    )
    if best in IATA_EQUIVALENT_GROUPS:
        return sorted(IATA_EQUIVALENT_GROUPS[best])
    return [best]


def process_upload(upload_id: int, target_airports: str | None = None, pricing_scan_enabled: bool = False) -> None:
    db = SessionLocal()
    try:
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        if not upload:
            return

        file_path = Path(upload.file_path)
        if not file_path.exists():
            upload.status = "failed"
            upload.error_message = "Uploaded file not found on disk."
            db.commit()
            return

        try:
            pricing_scan_enabled = bool(pricing_scan_enabled or getattr(upload, "pricing_scan_enabled", False))
            raw_text, method = _extract_text(file_path, pricing_scan_enabled=pricing_scan_enabled)
            if not raw_text:
                raise ValueError("No text extracted from file.")

            if target_airports:
                parsed_result = parse_ticket_text(
                    raw_text,
                    target_airports=target_airports,
                    pricing_scan_enabled=pricing_scan_enabled,
                )
                auto_target_used = None
            else:
                base_result = parse_ticket_text(raw_text, pricing_scan_enabled=pricing_scan_enabled)
                auto_target = _auto_center_from_parsed(base_result.get("parsed") or {})
                if auto_target:
                    parsed_result = parse_ticket_text(
                        raw_text,
                        target_airports=auto_target,
                        pricing_scan_enabled=pricing_scan_enabled,
                    )
                    auto_target_used = auto_target
                else:
                    parsed_result = base_result
                    auto_target_used = None
            upload.parse_result = {
                "method": method,
                "raw_text": raw_text,
                "parsed": parsed_result["parsed"],
                "confidence": parsed_result["confidence"],
                "needs_review": parsed_result["needs_review"],
                "target_airports_input": target_airports,
                "target_airports_auto": auto_target_used,
                "pricing_scan_enabled": pricing_scan_enabled,
            }
            transfer, has_changes, changed_fields = _create_or_update_transfer(
                upload_id=upload.id,
                parsed_payload=parsed_result["parsed"],
                confidence=parsed_result["confidence"],
                needs_review=parsed_result["needs_review"],
                db=db,
            )
            transfer.tenant_id = upload.tenant_id
            transfer.project_id = upload.project_id
            db.flush()
            _sync_transfer_to_kayit_card(db, transfer)
            detected_events = list(detect_ops_events_from_text(raw_text))
            if has_changes:
                detected_events.append(EVENT_TRANSFER_UPDATED)
            _create_ops_events(
                db=db,
                transfer=transfer,
                upload_id=upload.id,
                tenant_id=upload.tenant_id,
                event_types=detected_events,
                parsed_payload=parsed_result["parsed"],
                changed_fields=changed_fields,
            )
            cost_info = _calculate_token_cost(parsed_result.get("parsed") or {})
            internal_consume = _consume_internal_credits(db=db, upload=upload, cost=cost_info["total_cost"])
            if not internal_consume.get("ok"):
                raise ValueError(f"Internal token consume failed: {internal_consume.get('detail')}")
            consume_result = _consume_remote_license_token(cost=cost_info["total_cost"])
            consume_result["cost_breakdown"] = cost_info
            consume_result["internal"] = internal_consume
            if isinstance(upload.parse_result, dict):
                upload.parse_result["license_consume"] = consume_result
            upload.status = "processed"
            upload.error_message = None
            db.commit()
        except Exception as exc:
            db.rollback()
            upload = db.query(Upload).filter(Upload.id == upload_id).first()
            if not upload:
                return
            upload.status = "failed"
            upload.error_message = str(exc)
            db.commit()
    finally:
        db.close()
