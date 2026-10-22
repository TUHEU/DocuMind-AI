import pytest

from app.core.errors import ApiError
from app.models import AuditEvent, Document
from app.services.status import (ALLOWED_TRANSITIONS, APPLICATION_TRANSITIONS, DOCUMENT_STATUSES, LISTING_TRANSITIONS,
                                 can_transition, change_document_status)
from tests.conftest import make_user


def test_every_status_has_a_rule_and_targets_exist():
    assert set(ALLOWED_TRANSITIONS) == set(DOCUMENT_STATUSES)
    for targets in ALLOWED_TRANSITIONS.values():
        assert targets <= set(DOCUMENT_STATUSES)


def test_main_path_is_allowed():
    path = ["UPLOADED", "QUEUED", "PROCESSING", "NEEDS_REVIEW", "APPROVED", "ERP_SENT"]
    for a, b in zip(path, path[1:]):
        assert can_transition(a, b)


@pytest.mark.parametrize("a,b", [("UPLOADED", "APPROVED"), ("PROCESSING", "APPROVED"), ("ERP_SENT", "QUEUED"), ("REJECTED", "APPROVED")])
def test_forbidden_moves(a, b):
    assert not can_transition(a, b)


def test_listing_and_application_rules():
    assert can_transition("DRAFT", "OPEN", LISTING_TRANSITIONS)
    assert not can_transition("OPEN", "AWARDED", LISTING_TRANSITIONS)       # must be CLOSED first
    assert can_transition("SUBMITTED", "WITHDRAWN", APPLICATION_TRANSITIONS)
    assert not can_transition("REJECTED", "ACCEPTED", APPLICATION_TRANSITIONS)


def _doc(db, user, status="UPLOADED"):
    d = Document(uploaded_by=user.user_id, original_filename="a.pdf", storage_key="k1", sha256="0" * 64,
                 mime_type="application/pdf", size_bytes=10, status=status)
    db.add(d)
    db.commit()
    return d


def test_change_status_writes_audit(db_session):
    u = make_user(db_session, "op@example.com", "OPERATOR")
    d = _doc(db_session, u)
    change_document_status(db_session, d, "QUEUED", actor_id=u.user_id)
    db_session.commit()
    assert d.status == "QUEUED"
    ev = db_session.query(AuditEvent).filter_by(action="STATUS_CHANGE").one()
    assert ev.before_json == {"status": "UPLOADED"} and ev.after_json == {"status": "QUEUED"}


def test_invalid_change_raises_409_and_changes_nothing(db_session):
    u = make_user(db_session, "op@example.com", "OPERATOR")
    d = _doc(db_session, u)
    with pytest.raises(ApiError) as e:
        change_document_status(db_session, d, "APPROVED", actor_id=u.user_id)
    assert e.value.status_code == 409 and e.value.code == "INVALID_STATE"
    assert d.status == "UPLOADED"
    assert db_session.query(AuditEvent).count() == 0
