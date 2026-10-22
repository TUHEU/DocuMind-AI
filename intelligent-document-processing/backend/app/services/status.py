"""The ONE place where a document status changes (Phase 2, Chapter 4).
Allowed moves are listed below; every move writes an audit event in the same transaction."""
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import Document
from app.services.audit import record_audit

DOCUMENT_STATUSES = (
    "UPLOADED", "QUEUED", "PROCESSING", "NEEDS_REVIEW", "APPROVED", "REJECTED", "ERP_SENT", "ERP_FAILED", "FAILED",
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "UPLOADED": {"QUEUED"},
    "QUEUED": {"PROCESSING"},
    "PROCESSING": {"NEEDS_REVIEW", "FAILED"},
    "NEEDS_REVIEW": {"APPROVED", "REJECTED", "QUEUED"},   # QUEUED = reprocess
    "APPROVED": {"ERP_SENT", "ERP_FAILED"},
    "REJECTED": {"QUEUED"},                               # reprocess
    "ERP_FAILED": {"ERP_SENT", "ERP_FAILED"},             # safe retry
    "FAILED": {"QUEUED"},                                 # reprocess
    "ERP_SENT": set(),                                    # final
}

LISTING_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"OPEN", "CANCELLED"},
    "OPEN": {"CLOSED", "CANCELLED"},
    "CLOSED": {"AWARDED"},
    "AWARDED": set(),
    "CANCELLED": set(),
}

APPLICATION_TRANSITIONS: dict[str, set[str]] = {
    "SUBMITTED": {"UNDER_REVIEW", "SHORTLISTED", "ACCEPTED", "REJECTED", "WITHDRAWN"},
    "UNDER_REVIEW": {"SHORTLISTED", "ACCEPTED", "REJECTED", "WITHDRAWN"},
    "SHORTLISTED": {"ACCEPTED", "REJECTED", "WITHDRAWN"},
    "ACCEPTED": set(),
    "REJECTED": set(),
    "WITHDRAWN": set(),
}


def can_transition(current: str, new: str, table: dict[str, set[str]] = ALLOWED_TRANSITIONS) -> bool:
    return new in table.get(current, set())


def change_document_status(db: Session, document: Document, new_status: str, *, actor_id: str | None, reason: str | None = None) -> Document:
    old = document.status
    if not can_transition(old, new_status):
        raise ApiError(409, "INVALID_STATE", f"A document in status {old} cannot move to {new_status}")
    document.status = new_status
    record_audit(
        db, "STATUS_CHANGE", actor_id=actor_id, document_id=document.document_id, entity_type="document",
        entity_id=document.document_id, before={"status": old}, after={"status": new_status, **({"reason": reason} if reason else {})},
    )
    return document
