SELECT
    sessionId,
    ts
FROM dev.raw_data.session_timestamp
WHERE sessionId IS NOT NULL