-- Verify admin/staff insertion + password hashes
-- Run using: sqlite3 inventory_app/database/inventory.db < verification_sqlite_admins.sql

SELECT id, username, substr(password, 1, 20) AS hash_prefix, role
FROM admins
ORDER BY id;

SELECT username
FROM admins
WHERE username IN ('admin','staff1');

