# -*- coding: utf-8 -*-
"""session_summary.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1A_7eyehGQCRMEMxdFXmA0tOEIsNQPwOV
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from airflow.sensors.external_task import ExternalTaskSensor

# Define default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create the DAG
dag = DAG(
    'snowflake_session_summary',
    default_args=default_args,
    description='Create session summary analytics table',
    schedule_interval='@daily',
    catchup=False
)

# Wait for the first DAG to complete
wait_for_import = ExternalTaskSensor(
    task_id='wait_for_import',
    external_dag_id='snowflake_table_import',
    external_task_id='copy_session_timestamp',
    timeout=600,
    dag=dag
)

# SQL commands
create_analytics_schema = """
CREATE SCHEMA IF NOT EXISTS DEV.ANALYTICS;
"""

create_session_summary = """
-- Create the session_summary table with deduplication logic
CREATE OR REPLACE TABLE DEV.ANALYTICS.session_summary AS
WITH deduplicated_sessions AS (
    -- Remove duplicates from user_session_channel
    SELECT
        userId,
        sessionId,
        channel,
        ROW_NUMBER() OVER (PARTITION BY sessionId ORDER BY sessionId) as rn_usc
    FROM DEV.RAW_DATA.user_session_channel
),
deduplicated_timestamps AS (
    -- Remove duplicates from session_timestamp
    SELECT
        sessionId,
        ts,
        ROW_NUMBER() OVER (PARTITION BY sessionId ORDER BY ts DESC) as rn_st
    FROM DEV.RAW_DATA.session_timestamp
)
SELECT
    usc.userId,
    usc.sessionId,
    usc.channel,
    st.ts as session_timestamp
FROM deduplicated_sessions usc
JOIN deduplicated_timestamps st
    ON usc.sessionId = st.sessionId
WHERE usc.rn_usc = 1  -- Keep only the first occurrence from user_session_channel
    AND st.rn_st = 1; -- Keep only the most recent timestamp

-- Add primary key and indexes
ALTER TABLE DEV.ANALYTICS.session_summary
    ADD PRIMARY KEY (sessionId);

-- Create a view for duplicate detection
CREATE OR REPLACE VIEW DEV.ANALYTICS.session_duplicates AS
SELECT
    sessionId,
    COUNT(*) as occurrence_count
FROM (
    SELECT sessionId FROM DEV.RAW_DATA.user_session_channel
    UNION ALL
    SELECT sessionId FROM DEV.RAW_DATA.session_timestamp
)
GROUP BY sessionId
HAVING COUNT(*) > 1;
"""

# Create tasks using SnowflakeOperator
create_schema = SnowflakeOperator(
    task_id='create_schema',
    sql=create_analytics_schema,
    snowflake_conn_id='snowflake_conn',
    dag=dag
)

create_summary = SnowflakeOperator(
    task_id='create_summary',
    sql=create_session_summary,
    snowflake_conn_id='snowflake_conn',
    dag=dag
)

# Define task dependencies
wait_for_import >> create_schema >> create_summary