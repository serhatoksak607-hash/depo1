from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func

from .db import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True, index=True)
    token_balance = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False, index=True)
    city = Column(String(64), nullable=False)
    operation_code = Column(String(9), nullable=False, index=True)
    default_supplier_company_id = Column(Integer, ForeignKey("supplier_companies.id"), nullable=True, index=True)
    token_limit = Column(Integer, nullable=True)
    token_used = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ProjectModule(Base):
    __tablename__ = "project_modules"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    module_key = Column(String(64), nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ServiceProduct(Base):
    __tablename__ = "service_products"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    name = Column(String(128), nullable=False, index=True)
    category = Column(String(32), nullable=False, index=True)  # kayit | konaklama | transfer | dis_katilim | diger
    code = Column(String(64), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    currency = Column(String(8), nullable=False, default="TRY")
    vat_rate = Column(Float, nullable=True)
    quota = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ProjectServiceProduct(Base):
    __tablename__ = "project_service_products"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("service_products.id"), nullable=False, index=True)
    price_override = Column(Float, nullable=True)
    currency_override = Column(String(8), nullable=True)
    quota_override = Column(Integer, nullable=True)
    sale_start_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    sale_end_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserProjectAccess(Base):
    __tablename__ = "user_project_access"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    can_view = Column(Boolean, nullable=False, default=True)
    can_edit = Column(Boolean, nullable=False, default=False)
    is_denied = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserModuleAccess(Base):
    __tablename__ = "user_module_access"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    module_key = Column(String(64), nullable=False, index=True)
    allowed = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    operation_city = Column(String(64), nullable=True)
    operation_code = Column(String(9), nullable=True, index=True)
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
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True, index=True, unique=True)
    airline = Column(String(32), nullable=False, default="unknown")
    passenger_name = Column(String(255), nullable=True)
    participant_phone = Column(String(32), nullable=True, index=True)
    participant_order_no = Column(Integer, nullable=True, index=True)
    passenger_gender = Column(String(16), nullable=True, index=True)
    pnr = Column(String(16), nullable=True, index=True)
    flight_no = Column(String(16), nullable=True, index=True)
    flight_date = Column(String(10), nullable=True)
    flight_time = Column(String(5), nullable=True)
    trip_type = Column(String(24), nullable=True, index=True)
    outbound_date = Column(String(10), nullable=True)
    return_date = Column(String(10), nullable=True)
    segment_count = Column(Integer, nullable=True)
    outbound_departure_date = Column(String(10), nullable=True)
    outbound_departure_time = Column(String(5), nullable=True)
    outbound_arrival_date = Column(String(10), nullable=True)
    outbound_arrival_time = Column(String(5), nullable=True)
    return_departure_date = Column(String(10), nullable=True)
    return_departure_time = Column(String(5), nullable=True)
    return_arrival_date = Column(String(10), nullable=True)
    return_arrival_time = Column(String(5), nullable=True)
    pickup_location = Column(String(255), nullable=True)
    dropoff_location = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="unassigned")
    confidence = Column(Float, nullable=True)
    needs_review = Column(Boolean, nullable=False, default=True)
    payment_type = Column(String(32), nullable=True)
    issue_date = Column(String(10), nullable=True)
    pickup_time = Column(String(16), nullable=True)
    transfer_point = Column(String(255), nullable=True)
    vehicle_code = Column(String(64), nullable=True, index=True)
    reservation_code = Column(String(64), nullable=True, index=True)
    supplier_company_id = Column(Integer, ForeignKey("supplier_companies.id"), nullable=True, index=True)
    greeter_staff_id = Column(Integer, ForeignKey("supplier_staff.id"), nullable=True, index=True)
    driver_staff_id = Column(Integer, ForeignKey("supplier_staff.id"), nullable=True, index=True)
    transfer_action = Column(String(32), nullable=True, index=True)
    driver_action = Column(String(24), nullable=True, index=True)
    greeter_action = Column(String(24), nullable=True, index=True)
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
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    actor_username = Column(String(64), nullable=True, index=True)
    event_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    action = Column(String(64), nullable=True, index=True)
    request_method = Column(String(10), nullable=True, index=True)
    request_path = Column(String(255), nullable=True, index=True)
    status_code = Column(Integer, nullable=True, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    related_transfer_id = Column(Integer, ForeignKey("transfers.id"), nullable=True, index=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    username = Column(String(64), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="operator")
    active_project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    token_limit = Column(Integer, nullable=True)
    token_used = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(128), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DriverPanelToken(Base):
    __tablename__ = "driver_panel_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(128), nullable=False, unique=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    supplier_company_id = Column(Integer, ForeignKey("supplier_companies.id"), nullable=True, index=True)
    driver_staff_id = Column(Integer, ForeignKey("supplier_staff.id"), nullable=False, index=True)
    greeter_staff_id = Column(Integer, ForeignKey("supplier_staff.id"), nullable=True, index=True)
    panel_role = Column(String(16), nullable=False, default="driver", index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class SupplierCompany(Base):
    __tablename__ = "supplier_companies"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SupplierStaff(Base):
    __tablename__ = "supplier_staff"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    supplier_company_id = Column(Integer, ForeignKey("supplier_companies.id"), nullable=False, index=True)
    full_name = Column(String(128), nullable=False)
    role = Column(String(16), nullable=False, index=True)  # greeter | driver
    phone = Column(String(32), nullable=True)
    vehicle_plate = Column(String(32), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SupplierClient(Base):
    __tablename__ = "supplier_clients"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    supplier_company_id = Column(Integer, ForeignKey("supplier_companies.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    full_name = Column(String(128), nullable=False, index=True)
    phone = Column(String(32), nullable=True)
    email = Column(String(128), nullable=True)
    source_type = Column(String(16), nullable=False, default="external", index=True)  # project | external
    status = Column(String(24), nullable=False, default="active", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SupplierServiceType(Base):
    __tablename__ = "supplier_service_types"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    supplier_company_id = Column(Integer, ForeignKey("supplier_companies.id"), nullable=True, index=True)
    code = Column(String(32), nullable=False, index=True)  # GNL_001, ABC_001, ABC_PRJ01
    name = Column(String(128), nullable=False, index=True)
    scope_type = Column(String(16), nullable=False, default="general", index=True)  # general | company | project
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    parent_id = Column(Integer, ForeignKey("supplier_service_types.id"), nullable=True, index=True)
    unit_price = Column(Float, nullable=True)
    currency = Column(String(8), nullable=False, default="TRY")
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SupplierBooking(Base):
    __tablename__ = "supplier_bookings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    supplier_company_id = Column(Integer, ForeignKey("supplier_companies.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    project_reservation_no = Column(String(64), nullable=False, index=True)  # PROJEKODU_REZNO
    service_type_id = Column(Integer, ForeignKey("supplier_service_types.id"), nullable=True, index=True)
    service_type_name = Column(String(128), nullable=True)
    date = Column(String(10), nullable=True)  # YYYY-MM-DD
    time = Column(String(5), nullable=True)  # HH:MM
    from_location = Column(String(255), nullable=True)
    to_location = Column(String(255), nullable=True)
    status = Column(String(24), nullable=False, default="planned", index=True)
    base_amount = Column(Float, nullable=True)
    extra_parking = Column(Float, nullable=True)
    extra_greeter = Column(Float, nullable=True)
    extra_hgs = Column(Float, nullable=True)
    extra_meal = Column(Float, nullable=True)
    extra_other = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=True)
    currency = Column(String(8), nullable=False, default="TRY")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SupplierBookingContact(Base):
    __tablename__ = "supplier_booking_contacts"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("supplier_bookings.id"), nullable=False, index=True)
    contact_type = Column(String(24), nullable=False, index=True)  # authority | passenger
    full_name = Column(String(128), nullable=True)
    phone = Column(String(32), nullable=True, index=True)
    email = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SupplierSmsQueue(Base):
    __tablename__ = "supplier_sms_queue"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("supplier_bookings.id"), nullable=True, index=True)
    to_phone = Column(String(32), nullable=False, index=True)
    message = Column(Text, nullable=False)
    status = Column(String(16), nullable=False, default="queued", index=True)  # queued | sent | failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SupplierSmsTemplate(Base):
    __tablename__ = "supplier_sms_templates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    supplier_company_id = Column(Integer, ForeignKey("supplier_companies.id"), nullable=False, index=True)
    event_key = Column(String(64), nullable=False, index=True)  # planned | on_the_way | picked_up | delivered ...
    template_text = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ModuleReport(Base):
    __tablename__ = "module_reports"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    module_name = Column(String(64), nullable=False, index=True)
    report_type = Column(String(16), nullable=False, default="info", index=True)  # info | warning | error
    title = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    source = Column(String(128), nullable=True)
    payload = Column(JSON, nullable=True)
    resolved = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ModuleData(Base):
    __tablename__ = "module_data"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    module_name = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=True, index=True)
    data = Column(JSON, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    updated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class TranslationSession(Base):
    __tablename__ = "translation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    meeting_key = Column(String(128), nullable=True, index=True)
    starts_at = Column(String(19), nullable=True)  # YYYY-MM-DD HH:MM
    ends_at = Column(String(19), nullable=True)  # YYYY-MM-DD HH:MM
    access_code = Column(String(32), nullable=False, index=True, unique=True)
    status = Column(String(16), nullable=False, default="planned", index=True)  # planned|live|ended
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class TranslationAssignment(Base):
    __tablename__ = "translation_assignments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("translation_sessions.id"), nullable=False, index=True)
    interpreter_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    language = Column(String(32), nullable=False, index=True)  # tr|en|...
    is_live = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class TranslationListenerEvent(Base):
    __tablename__ = "translation_listener_events"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("translation_sessions.id"), nullable=False, index=True)
    language = Column(String(32), nullable=True, index=True)
    device_id = Column(String(128), nullable=True, index=True)
    action = Column(String(16), nullable=False, index=True)  # join|leave|heartbeat
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
