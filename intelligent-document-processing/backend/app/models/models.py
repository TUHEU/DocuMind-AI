"""SQLAlchemy models for the 16 tables of the Phase 2 design (see alembic/sql/0001_initial.sql).

The database itself enforces the CHECK constraints and the append-only triggers on audit_events;
the models map the columns so the application can read and write them.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, new_id, utcnow

BigIntPK = BigInteger().with_variant(Integer, "sqlite")   # lets SQLite auto-number in unit tests

ROLES = ("OPERATOR", "REVIEWER", "ADMIN", "COMPANY", "APPLICANT")
INTERNAL_ROLES = ("OPERATOR", "REVIEWER", "ADMIN")
SELF_SERVICE_ROLES = ("COMPANY", "APPLICANT")


def _id() -> Mapped[str]:
    return mapped_column(String(36), primary_key=True, default=new_id)


class Organization(Base):
    __tablename__ = "organizations"
    org_id: Mapped[str] = _id()
    name: Mapped[str] = mapped_column(String(200), unique=True)
    registration_no: Mapped[str | None] = mapped_column(String(60))
    country: Mapped[str | None] = mapped_column(String(60))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = _id()
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    org_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.org_id"), index=True)
    is_active: Mapped[int] = mapped_column(default=1)
    failed_login_count: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    organization: Mapped[Organization | None] = relationship()


class Document(Base):
    __tablename__ = "documents"
    document_id: Mapped[str] = _id()
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    page_count: Mapped[int | None]
    document_type: Mapped[str] = mapped_column(String(20), default="INVOICE")
    language: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="UPLOADED")
    retry_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)


class ProcessingRun(Base):
    __tablename__ = "processing_runs"
    __table_args__ = (UniqueConstraint("document_id", "run_number", name="uq_runs_document_number"),)
    run_id: Mapped[str] = _id()
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.document_id"))
    run_number: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")
    ocr_engine: Mapped[str] = mapped_column(String(20))
    model_version: Mapped[str | None] = mapped_column(String(60))
    preproc_config: Mapped[dict | None] = mapped_column(JSON)
    error_category: Mapped[str | None] = mapped_column(String(40))
    error_message: Mapped[str | None] = mapped_column(String(500))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)


class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    __table_args__ = (UniqueConstraint("run_id", "field_name", name="uq_fields_run_name"),)
    field_id: Mapped[str] = _id()
    run_id: Mapped[str] = mapped_column(ForeignKey("processing_runs.run_id"))
    field_name: Mapped[str] = mapped_column(String(40))
    raw_value: Mapped[str | None] = mapped_column(String(1000))
    normalized_value: Mapped[str | None] = mapped_column(String(500))
    reviewed_value: Mapped[str | None] = mapped_column(String(500))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    page_no: Mapped[int | None]
    bbox: Mapped[dict | None] = mapped_column(JSON)
    validation_status: Mapped[str] = mapped_column(String(10), default="REVIEW")
    validation_message: Mapped[str | None] = mapped_column(String(300))


class ExtractedLineItem(Base):
    __tablename__ = "extracted_line_items"
    __table_args__ = (UniqueConstraint("run_id", "line_no", name="uq_items_run_line"),)
    item_id: Mapped[str] = _id()
    run_id: Mapped[str] = mapped_column(ForeignKey("processing_runs.run_id"))
    line_no: Mapped[int]
    description: Mapped[str | None] = mapped_column(String(500))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    page_no: Mapped[int | None]
    bbox: Mapped[dict | None] = mapped_column(JSON)


class ValidationFinding(Base):
    __tablename__ = "validation_findings"
    finding_id: Mapped[str] = _id()
    run_id: Mapped[str] = mapped_column(ForeignKey("processing_runs.run_id"), index=True)
    rule_code: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(10))
    field_names: Mapped[str | None] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Review(Base):
    __tablename__ = "reviews"
    review_id: Mapped[str] = _id()
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.document_id"))
    run_id: Mapped[str] = mapped_column(ForeignKey("processing_runs.run_id"))
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    decision: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str | None] = mapped_column(String(500))
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FieldCorrection(Base):
    __tablename__ = "field_corrections"
    correction_id: Mapped[str] = _id()
    field_id: Mapped[str] = mapped_column(ForeignKey("extracted_fields.field_id"))
    old_value: Mapped[str | None] = mapped_column(String(500))
    new_value: Mapped[str | None] = mapped_column(String(500))
    reason: Mapped[str] = mapped_column(String(300))
    corrected_by: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    corrected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ErpAttempt(Base):
    __tablename__ = "erp_attempts"
    __table_args__ = (UniqueConstraint("document_id", "attempt_no", name="uq_erp_document_attempt"),)
    attempt_id: Mapped[str] = _id()
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.document_id"))
    attempt_no: Mapped[int]
    idempotency_key: Mapped[str] = mapped_column(String(80), index=True)
    destination: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(10), default="PENDING", index=True)
    http_status: Mapped[int | None]
    external_ref: Mapped[str | None] = mapped_column(String(100))
    error_category: Mapped[str | None] = mapped_column(String(40))
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class AuditEvent(Base):
    """Append-only: MySQL triggers refuse UPDATE and DELETE on this table."""
    __tablename__ = "audit_events"
    event_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"))
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.document_id"))
    action: Mapped[str] = mapped_column(String(50))
    entity_type: Mapped[str | None] = mapped_column(String(30))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SystemSetting(Base):
    __tablename__ = "system_settings"
    setting_key: Mapped[str] = mapped_column(String(60), primary_key=True)
    setting_value: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(255))
    updated_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Listing(Base):
    __tablename__ = "listings"
    listing_id: Mapped[str] = _id()
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.org_id"), index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    listing_type: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(120))
    budget_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    deadline: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    awarded_application_id: Mapped[str | None] = mapped_column(
        ForeignKey("applications.application_id", use_alter=True, name="fk_listings_awarded"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ListingDocument(Base):
    __tablename__ = "listing_documents"
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.listing_id"), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.document_id"), primary_key=True)
    doc_role: Mapped[str] = mapped_column(String(20), default="ATTACHMENT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("listing_id", "applicant_id", name="uq_applications_once"),)
    application_id: Mapped[str] = _id()
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.listing_id"))
    applicant_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    applicant_org_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.org_id"))
    cover_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="SUBMITTED")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ApplicationDocument(Base):
    __tablename__ = "application_documents"
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.application_id"), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.document_id"), primary_key=True)
    doc_role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
