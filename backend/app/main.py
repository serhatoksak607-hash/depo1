import os
import uuid
from pathlib import Path

import redis
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi import Query
from rq import Queue
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import Base, SessionLocal, engine
from .models import OpsEvent, Transfer, Upload
from .ops_events import ALLOWED_OPS_EVENT_TYPES


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
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS upload_id INTEGER")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS airline VARCHAR(32) NOT NULL DEFAULT 'unknown'")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS passenger_name VARCHAR(255)")
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
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS needs_review BOOLEAN NOT NULL DEFAULT TRUE")
        )
        conn.execute(
            text("ALTER TABLE transfers ADD COLUMN IF NOT EXISTS payment_type VARCHAR(32)")
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
            text(
                "CREATE INDEX IF NOT EXISTS ix_ops_events_scope_created "
                "ON ops_events (tenant_id, event_id, created_at DESC)"
            )
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


@app.get("/transfers")
def list_transfers(
    status: str | None = Query(default=None),
    airline: str | None = Query(default=None),
    needs_review: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Transfer)
    if status:
        query = query.filter(Transfer.status == status)
    if airline:
        query = query.filter(Transfer.airline == airline.lower())
    if needs_review is not None:
        query = query.filter(Transfer.needs_review == needs_review)

    items = query.order_by(Transfer.created_at.desc()).all()

    color_map = {
        "unassigned": "red",
        "planned": "yellow",
        "completed": "green",
    }

    return [
        {
            "id": transfer.id,
            "upload_id": transfer.upload_id,
            "airline": transfer.airline,
            "passenger_name": transfer.passenger_name,
            "passenger_gender": transfer.passenger_gender,
            "pnr": transfer.pnr,
            "flight_no": transfer.flight_no,
            "date": transfer.flight_date,
            "time": transfer.flight_time,
            "from": transfer.pickup_location,
            "to": transfer.dropoff_location,
            "status": transfer.status,
            "status_color": color_map.get(transfer.status, "red"),
            "confidence": transfer.confidence,
            "needs_review": transfer.needs_review,
            "created_at": transfer.created_at,
            "payment_type": transfer.payment_type,
            "currency": transfer.currency,
            "total_amount": transfer.total_amount,
            "base_fare": "hidden" if transfer.pricing_visibility == "masked" else transfer.base_fare,
            "taxes": "hidden" if transfer.pricing_visibility == "masked" else transfer.tax_breakdown,
        }
        for transfer in items
    ]


@app.get("/ops-events")
def list_ops_events(
    tenant_id: str | None = Query(default=None),
    event_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    related_transfer_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(OpsEvent)
    if tenant_id:
        query = query.filter(OpsEvent.tenant_id == tenant_id)
    if event_id:
        query = query.filter(OpsEvent.event_id == event_id)
    if event_type:
        if event_type not in ALLOWED_OPS_EVENT_TYPES:
            raise HTTPException(status_code=400, detail="Invalid event_type")
        query = query.filter(OpsEvent.event_type == event_type)
    if related_transfer_id is not None:
        query = query.filter(OpsEvent.related_transfer_id == related_transfer_id)

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
            "event_id": row.event_id,
            "event_type": row.event_type,
            "related_transfer_id": row.related_transfer_id,
            "payload": row.payload,
            "created_at": row.created_at,
        }
        for row in rows
    ]
