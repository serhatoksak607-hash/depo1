import io
from pathlib import Path

import fitz
import pytesseract
from PIL import Image
from pypdf import PdfReader

from .db import SessionLocal
from .models import Upload
from .parser import parse_ticket_text


MIN_TEXT_LENGTH = 30
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


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
            upload.status = "processed"
            upload.error_message = None
            db.commit()
        except Exception as exc:
            upload.status = "failed"
            upload.error_message = str(exc)
            db.commit()
    finally:
        db.close()
