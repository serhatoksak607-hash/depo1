import os
import uuid
from pathlib import Path

import redis
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from rq import Queue
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import Base, SessionLocal, engine
from .models import Upload


ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".zip"}
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "storage/uploads"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
RQ_QUEUE = os.getenv("RQ_QUEUE", "upload_processing")

app = FastAPI(title="Transfer Module MVP")
redis_client = redis.Redis.from_url(REDIS_URL)
upload_queue = Queue(RQ_QUEUE, connection=redis_client)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
            text("ALTER TABLE uploads ADD COLUMN IF NOT EXISTS error_message TEXT")
        )


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


@app.post("/upload")
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed: PDF, JPG, PNG, ZIP",
        )

    stored_name = f"{uuid.uuid4().hex}{extension}"
    destination = UPLOAD_DIR / stored_name

    content = file.file.read()
    with open(destination, "wb") as output:
        output.write(content)

    upload = Upload(
        original_filename=file.filename or stored_name,
        stored_filename=stored_name,
        content_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        file_path=str(destination),
        status="pending",
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    upload_queue.enqueue("app.tasks.process_upload", upload.id)

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


@app.get("/uploads/{upload_id}")
def get_upload(upload_id: int, db: Session = Depends(get_db)):
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
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
