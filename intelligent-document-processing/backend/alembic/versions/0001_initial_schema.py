"""Initial schema: the 16 tables of the Phase 2 design, with CHECK constraints,
the two append-only triggers on audit_events and the 6 default system settings.

The statements come from alembic/sql/0001_initial.sql, the file that was tested on MySQL 8.0 / MariaDB
in Phase 2. Later changes (new columns, new tables) are normal Alembic revisions on top of this one.

Revision ID: 0001
Revises:
"""
import re
from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "0001_initial.sql"

# children first, so foreign keys never block a drop
DROP_ORDER = [
    "application_documents", "listing_documents", "applications", "listings", "system_settings",
    "audit_events", "erp_attempts", "field_corrections", "reviews", "validation_findings",
    "extracted_line_items", "extracted_fields", "processing_runs", "documents", "users", "organizations",
]


def _statements(text: str) -> list[str]:
    lines = [re.sub(r"--.*$", "", ln) for ln in text.splitlines()]   # remove comments (no '--' inside strings in this file)
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def upgrade() -> None:
    for stmt in _statements(SQL_FILE.read_text(encoding="utf-8")):
        op.execute(stmt)


def downgrade() -> None:
    op.execute("ALTER TABLE listings DROP FOREIGN KEY fk_listings_awarded")
    for table in DROP_ORDER:
        op.execute(f"DROP TABLE IF EXISTS {table}")
