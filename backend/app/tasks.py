import io
import os
from pathlib import Path

import fitz
import pytesseract
from PIL import Image
from pypdf import PdfReader

from .db import SessionLocal
from .models import OpsEvent, Transfer, Upload
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
    existed = transfer is not None
    changed_fields: dict[str, dict[str, str | None]] = {}
    if not transfer:
        transfer = Transfer(upload_id=upload_id)
        db.add(transfer)

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
        "pickup_location": parsed.get("from"),
        "dropoff_location": parsed.get("to"),
        "payment_type": parsed.get("payment_type"),
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
    event_types: list[str],
    parsed_payload: dict,
    changed_fields: dict,
) -> None:
    for event_type in normalize_event_types(event_types):
        db.add(
            OpsEvent(
                tenant_id=DEFAULT_TENANT_ID,
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


def process_upload(upload_id: int) -> None:
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

            parsed_result = parse_ticket_text(raw_text)
            upload.parse_result = {
                "method": method,
                "raw_text": raw_text,
                "parsed": parsed_result["parsed"],
                "confidence": parsed_result["confidence"],
                "needs_review": parsed_result["needs_review"],
            }
            transfer, has_changes, changed_fields = _create_or_update_transfer(
                upload_id=upload.id,
                parsed_payload=parsed_result["parsed"],
                confidence=parsed_result["confidence"],
                needs_review=parsed_result["needs_review"],
                db=db,
            )
            db.flush()
            detected_events = list(detect_ops_events_from_text(raw_text))
            if has_changes:
                detected_events.append(EVENT_TRANSFER_UPDATED)
            _create_ops_events(
                db=db,
                transfer=transfer,
                upload_id=upload.id,
                event_types=detected_events,
                parsed_payload=parsed_result["parsed"],
                changed_fields=changed_fields,
            )
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
