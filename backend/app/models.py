from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func

from .db import Base


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True, index=True)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    parse_result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    pnr = Column(String(16), nullable=False, index=True)
    passenger_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="new")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FlightSegment(Base):
    __tablename__ = "flight_segments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    segment_order = Column(Integer, nullable=False, default=1)
    flight_number = Column(String(32), nullable=False)
    departure_airport = Column(String(8), nullable=False)
    arrival_airport = Column(String(8), nullable=False)
    departure_time = Column(DateTime(timezone=True), nullable=False)
    arrival_time = Column(DateTime(timezone=True), nullable=False)


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True, index=True, unique=True)
    airline = Column(String(32), nullable=False, default="unknown")
    passenger_name = Column(String(255), nullable=True)
    passenger_gender = Column(String(16), nullable=True, index=True)
    pnr = Column(String(16), nullable=True, index=True)
    flight_no = Column(String(16), nullable=True, index=True)
    flight_date = Column(String(10), nullable=True)
    flight_time = Column(String(5), nullable=True)
    pickup_location = Column(String(255), nullable=True)
    dropoff_location = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="unassigned")
    confidence = Column(Float, nullable=True)
    needs_review = Column(Boolean, nullable=False, default=True)
    payment_type = Column(String(32), nullable=True)
    currency = Column(String(8), nullable=True)
    total_amount = Column(Float, nullable=True)
    base_fare = Column(Float, nullable=True)
    tax_total = Column(Float, nullable=True)
    tax_breakdown = Column(JSON, nullable=True)
    pricing_visibility = Column(String(16), nullable=False, default="masked")
    raw_parse = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OpsEvent(Base):
    __tablename__ = "ops_events"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    event_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    related_transfer_id = Column(Integer, ForeignKey("transfers.id"), nullable=True, index=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
