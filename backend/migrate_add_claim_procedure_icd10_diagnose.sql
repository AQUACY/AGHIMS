-- Run these in MySQL to see why ALTER TABLE is stuck and what to do
-- Run in a *different* session (new mysql window) while ALTER is stuck.

-- 1) See all current connections and what they're doing
SHOW FULL PROCESSLIST;

-- 2) See who has metadata locks (MySQL 5.7+; shows what is blocking ALTER)
-- Run this and look for rows where claim_procedures appears:
SELECT * FROM performance_schema.metadata_locks
WHERE OBJECT_SCHEMA = 'hms' AND OBJECT_NAME = 'claim_procedures';

-- 3) See InnoDB lock waits (who is waiting, who holds the lock)
SELECT * FROM performance_schema.data_lock_waits;

-- 4) To KILL a blocking session (use the Id from SHOW PROCESSLIST):
--    KILL <Id>;
-- Example: if processlist shows Id=7 with a long-running SELECT on claim_procedures:
--    KILL 7;
-- Then retry the ALTER in your original session.
