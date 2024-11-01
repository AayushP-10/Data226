WITH u AS (
    SELECT * FROM DEV.ANALYTICS.user_session_channel
), st AS (
    SELECT * FROM DEV.ANALYTICS.session_timestamp
)
SELECT u.userId, u.sessionId, u.channel, st.ts
FROM u
JOIN st ON u.sessionId = st.sessionId