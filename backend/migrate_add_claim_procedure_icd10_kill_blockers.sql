-- Find and kill connections blocking ALTER TABLE claim_procedures
-- Run this in a NEW MySQL session (not the one running ALTER).

-- Step 1: Find the processlist Id(s) that hold metadata lock on claim_procedures
-- (These are the OWNER_THREAD_IDs with LOCK_STATUS = 'GRANTED' in metadata_locks)
SELECT
  t.PROCESSLIST_ID AS 'Kill_This_Id',
  t.PROCESSLIST_USER,
  t.PROCESSLIST_HOST,
  t.PROCESSLIST_COMMAND,
  t.PROCESSLIST_TIME AS 'Time_sec',
  LEFT(t.PROCESSLIST_INFO, 80) AS 'Query_preview'
FROM performance_schema.threads t
JOIN performance_schema.metadata_locks m
  ON m.OWNER_THREAD_ID = t.THREAD_ID
WHERE m.OBJECT_SCHEMA = 'hms'
  AND m.OBJECT_NAME = 'claim_procedures'
  AND m.LOCK_STATUS = 'GRANTED'
  AND m.LOCK_TYPE IN ('SHARED_READ', 'SHARED_WRITE', 'SHARED_UPGRADABLE')
  AND t.PROCESSLIST_ID IS NOT NULL
ORDER BY t.PROCESSLIST_TIME DESC;

-- Step 2: For each Kill_This_Id from the list above, run (replace 52 with actual Id):
--   KILL 52;
--
-- Step 3: Also kill any long-running "Sleep" connections using the hms database,
--         and old SELECT/UPDATE on claims so the ALTER can get the lock:
--   SHOW FULL PROCESSLIST;
--   Then: KILL <Id>;  for Sleep or long-running queries on hms (except your own session).
