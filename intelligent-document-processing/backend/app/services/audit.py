from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditEvent


def client_ip(request: Request | None) -> str | None:
    return request.client.host if request is not None and request.client else None


def record_audit(
    db: Session,
    action: str,
    *,
    actor_id: str | None = None,
    document_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    request: Request | None = None,
) -> AuditEvent:
    """Add one audit row to the CURRENT transaction (the caller commits).
    Never put passwords, tokens or keys in before/after."""
    event = AuditEvent(
        action=action, actor_id=actor_id, document_id=document_id, entity_type=entity_type,
        entity_id=entity_id, before_json=before, after_json=after, ip_address=client_ip(request),
    )
    db.add(event)
    return event
