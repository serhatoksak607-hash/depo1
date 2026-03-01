import os
import uuid
from pathlib import Path

import redis
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import Base, SessionLocal, engine
from .models import Upload


ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".zip"}
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "storage/uploads"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

app = FastAPI(title="Transfer Module MVP")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


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
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    return {
        "id": upload.id,
        "original_filename": upload.original_filename,
        "stored_filename": upload.stored_filename,
        "file_size": upload.file_size,
        "content_type": upload.content_type,
        "file_path": upload.file_path,
        "created_at": upload.created_at,
    }

