-- DocuMind AI Phase 2: ONE file. It DELETES any old idp_db, then recreates it with all 16 tables.
DROP DATABASE IF EXISTS idp_db;
CREATE DATABASE idp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE idp_db;

-- =====================================================================
-- DocuMind AI - Phase 2 database design (MySQL 8.0, InnoDB, utf8mb4)
-- Design reference for the SQLAlchemy models and Alembic migrations of
-- the next phase. Times are stored in UTC. Identifiers are UUID strings.
--
-- Create the database once (outside this file):
--   CREATE DATABASE idp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- Then load this file into it:
--   mysql -u <user> -p idp_db < schema.sql
-- =====================================================================

SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- 1. organizations : companies that publish or answer listings (tender module)
-- ---------------------------------------------------------------------
CREATE TABLE organizations (
  org_id          CHAR(36)     NOT NULL,
  name            VARCHAR(200) NOT NULL,
  registration_no VARCHAR(60)  NULL,                  -- trade register or tax number, as given
  country         VARCHAR(60)  NULL,
  contact_email   VARCHAR(255) NULL,
  is_active       TINYINT      NOT NULL DEFAULT 1,
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (org_id),
  UNIQUE KEY uq_organizations_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 2. users : identity and role (RBAC)
-- ---------------------------------------------------------------------
CREATE TABLE users (
  user_id            CHAR(36)     NOT NULL,
  email              VARCHAR(255) NOT NULL,
  full_name          VARCHAR(150) NOT NULL,
  password_hash      VARCHAR(255) NOT NULL,           -- Argon2id or bcrypt hash, never plaintext
  role               VARCHAR(20)  NOT NULL,           -- OPERATOR | REVIEWER | ADMIN | COMPANY | APPLICANT
  org_id             CHAR(36)     NULL,               -- set for COMPANY users
  is_active          TINYINT      NOT NULL DEFAULT 1,
  failed_login_count INT          NOT NULL DEFAULT 0,
  locked_until       DATETIME     NULL,
  last_login_at      DATETIME     NULL,
  created_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  UNIQUE KEY uq_users_email (email),
  KEY idx_users_org (org_id),
  CONSTRAINT fk_users_org FOREIGN KEY (org_id) REFERENCES organizations (org_id),
  CONSTRAINT ck_users_role CHECK (role IN ('OPERATOR','REVIEWER','ADMIN','COMPANY','APPLICANT'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 3. documents : one uploaded source file and its workflow state
-- ---------------------------------------------------------------------
CREATE TABLE documents (
  document_id       CHAR(36)     NOT NULL,
  uploaded_by       CHAR(36)     NOT NULL,
  original_filename VARCHAR(255) NOT NULL,            -- display only, never used as a path
  storage_key       VARCHAR(255) NOT NULL,            -- opaque key inside protected storage
  sha256            CHAR(64)     NOT NULL,
  mime_type         VARCHAR(100) NOT NULL,
  size_bytes        BIGINT       NOT NULL,
  page_count        INT          NULL,
  document_type     VARCHAR(20)  NOT NULL DEFAULT 'INVOICE',
  language          VARCHAR(10)  NULL,                -- fr | en | mixed | unknown
  status            VARCHAR(20)  NOT NULL DEFAULT 'UPLOADED',
  retry_count       INT          NOT NULL DEFAULT 0,
  created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at        DATETIME     NULL,                -- retention / soft delete
  PRIMARY KEY (document_id),
  UNIQUE KEY uq_documents_storage_key (storage_key),
  KEY idx_documents_status_created (status, created_at),
  KEY idx_documents_sha256 (sha256),
  KEY idx_documents_uploaded_by (uploaded_by, created_at),
  CONSTRAINT fk_documents_user FOREIGN KEY (uploaded_by) REFERENCES users (user_id),
  CONSTRAINT ck_documents_size CHECK (size_bytes > 0),
  CONSTRAINT ck_documents_type CHECK (document_type IN ('INVOICE','RECEIPT','FORM','OFFER','CV','UNKNOWN')),
  CONSTRAINT ck_documents_status CHECK (status IN
    ('UPLOADED','QUEUED','PROCESSING','NEEDS_REVIEW','APPROVED','REJECTED','ERP_SENT','ERP_FAILED','FAILED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 4. processing_runs : each attempt to process a document (history kept)
-- ---------------------------------------------------------------------
CREATE TABLE processing_runs (
  run_id           CHAR(36)    NOT NULL,
  document_id      CHAR(36)    NOT NULL,
  run_number       INT         NOT NULL,               -- 1, 2, 3 ... per document
  status           VARCHAR(20) NOT NULL DEFAULT 'RUNNING',   -- RUNNING | SUCCEEDED | FAILED
  ocr_engine       VARCHAR(20) NOT NULL,               -- TESSERACT | CRNN
  model_version    VARCHAR(60) NULL,
  preproc_config   JSON        NULL,
  error_category   VARCHAR(40) NULL,                    -- e.g. UNREADABLE, OCR_ERROR, TIMEOUT
  error_message    VARCHAR(500) NULL,                  -- sanitised, no paths or stack traces
  started_at       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at         DATETIME    NULL,
  PRIMARY KEY (run_id),
  UNIQUE KEY uq_runs_document_number (document_id, run_number),
  CONSTRAINT fk_runs_document FOREIGN KEY (document_id) REFERENCES documents (document_id),
  CONSTRAINT ck_runs_status CHECK (status IN ('RUNNING','SUCCEEDED','FAILED')),
  CONSTRAINT ck_runs_engine CHECK (ocr_engine IN ('TESSERACT','CRNN'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 5. extracted_fields : candidate header fields of one run
--    field_name values: supplier_name, supplier_tax_id, invoice_number,
--    invoice_date, due_date, po_reference, subtotal, tax_amount,
--    total_amount, currency  (line items live in extracted_line_items)
-- ---------------------------------------------------------------------
CREATE TABLE extracted_fields (
  field_id          CHAR(36)      NOT NULL,
  run_id            CHAR(36)      NOT NULL,
  field_name        VARCHAR(40)   NOT NULL,
  raw_value         VARCHAR(1000) NULL,                -- exactly what OCR read
  normalized_value  VARCHAR(500)  NULL,                -- parsed date / decimal / code
  reviewed_value    VARCHAR(500)  NULL,                -- final value after human review
  confidence        DECIMAL(4,3)  NULL,                -- 0.000 - 1.000
  page_no           INT           NULL,
  bbox              JSON          NULL,                -- {"x":..,"y":..,"w":..,"h":..} relative to the page image
  validation_status VARCHAR(10)   NOT NULL DEFAULT 'REVIEW',
  validation_message VARCHAR(300) NULL,
  PRIMARY KEY (field_id),
  UNIQUE KEY uq_fields_run_name (run_id, field_name),
  CONSTRAINT fk_fields_run FOREIGN KEY (run_id) REFERENCES processing_runs (run_id),
  CONSTRAINT ck_fields_conf CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  CONSTRAINT ck_fields_validation CHECK (validation_status IN ('PASS','REVIEW','FAIL'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 6. extracted_line_items : invoice table rows of one run (optional field 7)
-- ---------------------------------------------------------------------
CREATE TABLE extracted_line_items (
  item_id      CHAR(36)       NOT NULL,
  run_id       CHAR(36)       NOT NULL,
  line_no      INT            NOT NULL,
  description  VARCHAR(500)   NULL,
  quantity     DECIMAL(18,4)  NULL,
  unit_price   DECIMAL(18,4)  NULL,
  amount       DECIMAL(18,2)  NULL,
  confidence   DECIMAL(4,3)   NULL,
  page_no      INT            NULL,
  bbox         JSON           NULL,
  PRIMARY KEY (item_id),
  UNIQUE KEY uq_items_run_line (run_id, line_no),
  CONSTRAINT fk_items_run FOREIGN KEY (run_id) REFERENCES processing_runs (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 7. validation_findings : document-level rule results (BR rules)
-- ---------------------------------------------------------------------
CREATE TABLE validation_findings (
  finding_id  CHAR(36)     NOT NULL,
  run_id      CHAR(36)     NOT NULL,
  rule_code   VARCHAR(40)  NOT NULL,                  -- REQUIRED_FIELD, ARITHMETIC, DUPLICATE, DATE, CURRENCY, ERP_SCHEMA
  severity    VARCHAR(10)  NOT NULL,                  -- INFO | WARNING | BLOCKING
  field_names VARCHAR(200) NULL,                      -- comma-separated field names concerned
  message     VARCHAR(500) NOT NULL,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (finding_id),
  KEY idx_findings_run (run_id),
  CONSTRAINT fk_findings_run FOREIGN KEY (run_id) REFERENCES processing_runs (run_id),
  CONSTRAINT ck_findings_severity CHECK (severity IN ('INFO','WARNING','BLOCKING'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 8. reviews : human decisions on a document
-- ---------------------------------------------------------------------
CREATE TABLE reviews (
  review_id    CHAR(36)     NOT NULL,
  document_id  CHAR(36)     NOT NULL,
  run_id       CHAR(36)     NOT NULL,
  reviewer_id  CHAR(36)     NOT NULL,
  decision     VARCHAR(10)  NOT NULL,                 -- APPROVED | REJECTED
  reason       VARCHAR(500) NULL,                     -- required when REJECTED (enforced in the API)
  decided_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (review_id),
  KEY idx_reviews_document (document_id, decided_at),
  CONSTRAINT fk_reviews_document FOREIGN KEY (document_id) REFERENCES documents (document_id),
  CONSTRAINT fk_reviews_run      FOREIGN KEY (run_id)      REFERENCES processing_runs (run_id),
  CONSTRAINT fk_reviews_reviewer FOREIGN KEY (reviewer_id) REFERENCES users (user_id),
  CONSTRAINT ck_reviews_decision CHECK (decision IN ('APPROVED','REJECTED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 9. field_corrections : every manual change, original value preserved (BR-5)
-- ---------------------------------------------------------------------
CREATE TABLE field_corrections (
  correction_id CHAR(36)     NOT NULL,
  field_id      CHAR(36)     NOT NULL,
  old_value     VARCHAR(500) NULL,
  new_value     VARCHAR(500) NULL,
  reason        VARCHAR(300) NOT NULL,
  corrected_by  CHAR(36)     NOT NULL,
  corrected_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (correction_id),
  KEY idx_corrections_field (field_id, corrected_at),
  CONSTRAINT fk_corrections_field FOREIGN KEY (field_id)     REFERENCES extracted_fields (field_id),
  CONSTRAINT fk_corrections_user  FOREIGN KEY (corrected_by) REFERENCES users (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 10. erp_attempts : every outbound submission (BR-4, BR-6)
-- ---------------------------------------------------------------------
CREATE TABLE erp_attempts (
  attempt_id       CHAR(36)     NOT NULL,
  document_id      CHAR(36)     NOT NULL,
  attempt_no       INT          NOT NULL,
  idempotency_key  VARCHAR(80)  NOT NULL,             -- same key for every retry of one document
  destination      VARCHAR(20)  NOT NULL,             -- MOCK | ODOO
  status           VARCHAR(10)  NOT NULL DEFAULT 'PENDING',   -- PENDING | SENT | FAILED
  http_status      INT          NULL,
  external_ref     VARCHAR(100) NULL,                 -- id returned by the ERP
  error_category   VARCHAR(40)  NULL,                 -- AUTH, VALIDATION, TIMEOUT, SERVER, DUPLICATE
  error_message    VARCHAR(500) NULL,                 -- sanitised
  created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at      DATETIME     NULL,
  PRIMARY KEY (attempt_id),
  UNIQUE KEY uq_erp_document_attempt (document_id, attempt_no),
  KEY idx_erp_idempotency (idempotency_key),
  KEY idx_erp_status (status),
  CONSTRAINT fk_erp_document FOREIGN KEY (document_id) REFERENCES documents (document_id),
  CONSTRAINT ck_erp_destination CHECK (destination IN ('MOCK','ODOO')),
  CONSTRAINT ck_erp_status CHECK (status IN ('PENDING','SENT','FAILED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- A document may have at most one successful ERP submission.
-- Enforced in the service layer inside a transaction (row lock on documents)
-- and checked by the retry tests required by objective O9.

-- ---------------------------------------------------------------------
-- 11. audit_events : append-only trail (FR-13)
-- ---------------------------------------------------------------------
CREATE TABLE audit_events (
  event_id     BIGINT       NOT NULL AUTO_INCREMENT,
  actor_id     CHAR(36)     NULL,                     -- NULL for system actions
  document_id  CHAR(36)     NULL,
  action       VARCHAR(50)  NOT NULL,                 -- LOGIN, UPLOAD, STATUS_CHANGE, CORRECT_FIELD, APPROVE, REJECT, ERP_SUBMIT, SETTING_CHANGE
  entity_type  VARCHAR(30)  NULL,
  entity_id    VARCHAR(36)  NULL,
  before_json  JSON         NULL,
  after_json   JSON         NULL,
  ip_address   VARCHAR(45)  NULL,
  created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (event_id),
  KEY idx_audit_document (document_id, created_at),
  KEY idx_audit_actor (actor_id, created_at),
  KEY idx_audit_action (action, created_at),
  CONSTRAINT fk_audit_actor    FOREIGN KEY (actor_id)    REFERENCES users (user_id),
  CONSTRAINT fk_audit_document FOREIGN KEY (document_id) REFERENCES documents (document_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Append-only guarantee at database level (in addition to the application rule).
CREATE TRIGGER trg_audit_no_update BEFORE UPDATE ON audit_events
  FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_events is append-only';
CREATE TRIGGER trg_audit_no_delete BEFORE DELETE ON audit_events
  FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_events is append-only';

-- ---------------------------------------------------------------------
-- 12. system_settings : administrator-editable rules and thresholds (FR-17)
-- ---------------------------------------------------------------------
CREATE TABLE system_settings (
  setting_key  VARCHAR(60)  NOT NULL,
  setting_value VARCHAR(255) NOT NULL,
  description  VARCHAR(255) NULL,
  updated_by   CHAR(36)     NULL,
  updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (setting_key),
  CONSTRAINT fk_settings_user FOREIGN KEY (updated_by) REFERENCES users (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Provisional defaults. Confidence thresholds MUST be re-tuned on validation data (see the provisional targets in the Phase 1 specification).
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
 ('confidence_accept',     '0.90',  'At or above this value a field is shown as accepted (provisional)'),
 ('confidence_review',     '0.70',  'Below this value a field requires review (provisional)'),
 ('arithmetic_tolerance',  '0.01',  'Allowed difference for subtotal + tax = total, in currency units'),
 ('max_upload_bytes',      '10485760', 'Maximum upload size (10 MB)'),
 ('max_pdf_pages',         '10',    'Maximum pages accepted per PDF'),
 ('allowed_mime_types',    'application/pdf,image/png,image/jpeg', 'Accepted upload types');

-- ---------------------------------------------------------------------
-- 13. listings : a tender, a job or an internship (tender module; jobs are a stretch goal)
-- ---------------------------------------------------------------------
CREATE TABLE listings (
  listing_id      CHAR(36)      NOT NULL,
  org_id          CHAR(36)      NOT NULL,             -- the publishing company
  created_by      CHAR(36)      NOT NULL,
  listing_type    VARCHAR(20)   NOT NULL,             -- TENDER | JOB | INTERNSHIP
  title           VARCHAR(200)  NOT NULL,
  description     TEXT          NOT NULL,
  requirements    TEXT          NULL,
  location        VARCHAR(120)  NULL,
  budget_amount   DECIMAL(15,2) NULL,                 -- tenders only
  currency        CHAR(3)       NULL,
  deadline        DATETIME      NOT NULL,             -- UTC
  status          VARCHAR(20)   NOT NULL DEFAULT 'DRAFT',
  awarded_application_id CHAR(36) NULL,               -- winner of a tender (set on award)
  created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (listing_id),
  KEY idx_listings_status_deadline (status, deadline),
  KEY idx_listings_type (listing_type, status),
  KEY idx_listings_org (org_id, created_at),
  CONSTRAINT fk_listings_org  FOREIGN KEY (org_id)     REFERENCES organizations (org_id),
  CONSTRAINT fk_listings_user FOREIGN KEY (created_by) REFERENCES users (user_id),
  CONSTRAINT ck_listings_type   CHECK (listing_type IN ('TENDER','JOB','INTERNSHIP')),
  CONSTRAINT ck_listings_status CHECK (status IN ('DRAFT','OPEN','CLOSED','AWARDED','CANCELLED')),
  CONSTRAINT ck_listings_budget CHECK (budget_amount IS NULL OR budget_amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 14. listing_documents : files that belong to a listing (call for tender, job description)
-- ---------------------------------------------------------------------
CREATE TABLE listing_documents (
  listing_id   CHAR(36)    NOT NULL,
  document_id  CHAR(36)    NOT NULL,
  doc_role     VARCHAR(20) NOT NULL DEFAULT 'ATTACHMENT',   -- CALL_DOCUMENT | ATTACHMENT
  created_at   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (listing_id, document_id),
  CONSTRAINT fk_ld_listing  FOREIGN KEY (listing_id)  REFERENCES listings (listing_id),
  CONSTRAINT fk_ld_document FOREIGN KEY (document_id) REFERENCES documents (document_id),
  CONSTRAINT ck_ld_role CHECK (doc_role IN ('CALL_DOCUMENT','ATTACHMENT'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- 15. applications : one company offer or one candidate application for a listing
-- ---------------------------------------------------------------------
CREATE TABLE applications (
  application_id CHAR(36)     NOT NULL,
  listing_id     CHAR(36)     NOT NULL,
  applicant_id   CHAR(36)     NOT NULL,                -- the user who applies
  applicant_org_id CHAR(36)   NULL,                    -- the answering company (tenders)
  cover_note     TEXT         NULL,
  status         VARCHAR(20)  NOT NULL DEFAULT 'SUBMITTED',
  submitted_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (application_id),
  UNIQUE KEY uq_applications_once (listing_id, applicant_id),   -- one application per person per listing
  KEY idx_applications_listing (listing_id, status),
  KEY idx_applications_applicant (applicant_id, submitted_at),
  CONSTRAINT fk_app_listing   FOREIGN KEY (listing_id)       REFERENCES listings (listing_id),
  CONSTRAINT fk_app_applicant FOREIGN KEY (applicant_id)     REFERENCES users (user_id),
  CONSTRAINT fk_app_org       FOREIGN KEY (applicant_org_id) REFERENCES organizations (org_id),
  CONSTRAINT ck_app_status CHECK (status IN ('SUBMITTED','UNDER_REVIEW','SHORTLISTED','ACCEPTED','REJECTED','WITHDRAWN'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE listings
  ADD CONSTRAINT fk_listings_awarded FOREIGN KEY (awarded_application_id) REFERENCES applications (application_id);

-- ---------------------------------------------------------------------
-- 16. application_documents : the files an application carries (offer PDF, CV, cover letter)
--     Each file is an ordinary row of documents, so it goes through OCR, extraction and review.
-- ---------------------------------------------------------------------
CREATE TABLE application_documents (
  application_id CHAR(36)    NOT NULL,
  document_id    CHAR(36)    NOT NULL,
  doc_role       VARCHAR(20) NOT NULL,                  -- OFFER | CV | COVER_LETTER | ATTACHMENT
  created_at     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (application_id, document_id),
  CONSTRAINT fk_ad_application FOREIGN KEY (application_id) REFERENCES applications (application_id),
  CONSTRAINT fk_ad_document    FOREIGN KEY (document_id)    REFERENCES documents (document_id),
  CONSTRAINT ck_ad_role CHECK (doc_role IN ('OFFER','CV','COVER_LETTER','ATTACHMENT'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
