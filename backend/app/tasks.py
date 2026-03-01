from pathlib import Path

from pypdf import PdfReader

from .db import SessionLocal
from .models import Upload


def _extract_pdf_text(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    texts = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts).strip()


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
            raw_text = ""
            method = "ocr_placeholder"

            if file_path.suffix.lower() == ".pdf":
                raw_text = _extract_pdf_text(file_path)
                method = "pdf_text"

            if not raw_text:
                raw_text = "OCR_NOT_IMPLEMENTED"
                method = "ocr_placeholder"

            upload.parse_result = {"raw_text": raw_text, "method": method}
            upload.status = "processed"
            upload.error_message = None
            db.commit()
        except Exception as exc:
            upload.status = "failed"
            upload.error_message = str(exc)
            db.commit()
    finally:
        db.close()
