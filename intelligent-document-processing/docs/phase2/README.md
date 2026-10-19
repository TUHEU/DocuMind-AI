# Phase 2 - System Design and Architecture (version 1.1)
- DocuMind_AI_Phase2_System_Design_Specification.pdf : the specification (50 pages). Chapter 9 is the tender module.
- db/documind_phase2_database.sql : the ONE file to load in MySQL (deletes the old idp_db, creates 16 tables)
- db/schema.sql : the same tables without the DROP/CREATE DATABASE lines (listed in Appendix A)
- db/documind_phase2_test.sql : checks (the last line must fail: audit table is append-only)
- api/openapi.yaml : REST contract (34 operations, validated; only the health endpoints exist in code)
- latex_src/ : LaTeX sources
Verified on MariaDB 10.11 only. NOT yet run on MySQL 8.0 since the tender tables were added.
Open decisions: Chapter 8 (P2-D1..D6) and Chapter 9 (P2-D7..D10).
