import io
import os
import shutil
import json
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

import fitz
import pytesseract
from PIL import Image
from pypdf import PdfReader

from .db import SessionLocal
from .iata_tr import IATA_EQUIVALENT_GROUPS
from .models import OpsEvent, Project, Tenant, Transfer, Upload, User
from .ops_events import (
    EVENT_TRANSFER_UPDATED,
    detect_ops_events_from_text,
    normalize_event_types,
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


def _extract_text(file_path: Path) -> tuple[str, str]:
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        raw_text = _extract_pdf_text(file_path)
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
    if not transfer:
        pnr = (parsed.get("pnr") or "").strip()
        flight_no = (parsed.get("flight_no") or "").strip()
        flight_date = (parsed.get("date") or "").strip()
        passenger_name = (parsed.get("passenger_name") or "").strip()

        if pnr and flight_no and flight_date:
            transfer = (
                db.query(Transfer)
                .filter(
                    Transfer.pnr == pnr,
                    Transfer.flight_no == flight_no,
                    Transfer.flight_date == flight_date,
                )
                .order_by(Transfer.id.desc())
                .first()
            )
        elif pnr and flight_date:
            transfer = (
                db.query(Transfer)
                .filter(
                    Transfer.pnr == pnr,
                    Transfer.flight_date == flight_date,
                )
                .order_by(Transfer.id.desc())
                .first()
            )
        elif passenger_name and flight_no and flight_date:
            transfer = (
                db.query(Transfer)
                .filter(
                    Transfer.passenger_name == passenger_name,
                    Transfer.flight_no == flight_no,
                    Transfer.flight_date == flight_date,
                )
                .order_by(Transfer.id.desc())
                .first()
            )
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
    if tenant.token_balance < amount:
        return {
            "enabled": True,
            "ok": False,
            "detail": "insufficient_tenant_tokens",
            "tenant_balance": tenant.token_balance,
            "cost": amount,
        }

    user = None
    if user_id:
        user = (
            db.query(User)
            .filter(User.id == user_id, User.tenant_id == tenant_id, User.is_active.is_(True))
            .first()
        )
        if not user:
            return {"enabled": True, "ok": False, "detail": "user not found or inactive"}
        if user.token_limit is not None and user.token_used + amount > user.token_limit:
            return {
                "enabled": True,
                "ok": False,
                "detail": "user_token_limit_exceeded",
                "user_limit": user.token_limit,
                "user_used": user.token_used,
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
        if project.token_limit is not None and project.token_used + amount > project.token_limit:
            return {
                "enabled": True,
                "ok": False,
                "detail": "project_token_limit_exceeded",
                "project_limit": project.token_limit,
                "project_used": project.token_used,
                "cost": amount,
            }

    tenant.token_balance -= amount
    if user is not None:
        user.token_used = int(user.token_used or 0) + amount
    if project is not None:
        project.token_used = int(project.token_used or 0) + amount

    return {
        "enabled": True,
        "ok": True,
        "cost": amount,
        "tenant_balance": tenant.token_balance,
        "user_used": int(user.token_used or 0) if user is not None else None,
        "project_used": int(project.token_used or 0) if project is not None else None,
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


def process_upload(upload_id: int, target_airports: str | None = None) -> None:
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
            raw_text, method = _extract_text(file_path)
            if not raw_text:
                raise ValueError("No text extracted from file.")

            if target_airports:
                parsed_result = parse_ticket_text(raw_text, target_airports=target_airports)
                auto_target_used = None
            else:
                base_result = parse_ticket_text(raw_text)
                auto_target = _auto_center_from_parsed(base_result.get("parsed") or {})
                if auto_target:
                    parsed_result = parse_ticket_text(raw_text, target_airports=auto_target)
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
