-- Run AFTER the database file. Each query ends with a result; the last two must show an error.
USE idp_db;
SELECT COUNT(*) AS tables_count FROM information_schema.tables WHERE table_schema='idp_db';
SELECT COUNT(*) AS triggers_count FROM information_schema.triggers WHERE trigger_schema='idp_db';
INSERT INTO users (user_id,email,full_name,password_hash,role) VALUES ('u1','t@t.com','Test','x','ADMIN');
INSERT INTO audit_events (actor_id,action) VALUES ('u1','TEST');
-- EXPECTED TO FAIL (append-only):
UPDATE audit_events SET action='x' WHERE event_id=1;
