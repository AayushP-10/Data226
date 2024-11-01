
  create or replace   view DEV.ANALYTICS.session_timestamp
  
   as (
    SELECT
    sessionId,
    ts
FROM dev.raw_data.session_timestamp
WHERE sessionId IS NOT NULL
  );

