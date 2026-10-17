import duckdb


WEEKLY_CLEANING_QUERY = """
WITH readings AS (
    SELECT
        robot_id,
        ts,
        state,
        panel_id,
        battery_pct,
        lag(battery_pct) OVER (
            PARTITION BY robot_id ORDER BY ts
        ) AS previous_battery_pct
    FROM read_parquet(?, hive_partitioning = true)
),
week_start AS (
    SELECT date_trunc('week', max(ts)) AS start_ts
    FROM readings
),
per_robot AS (
    SELECT
        r.robot_id,
        count(DISTINCT r.panel_id) FILTER (
            WHERE r.state = 'CLEANING'
        ) AS panels_cleaned,
        sum(
            CASE
                WHEN r.state = 'CLEANING' AND r.previous_battery_pct IS NOT NULL
                THEN greatest(r.previous_battery_pct - r.battery_pct, 0)
                ELSE 0
            END
        ) / nullif(
            count(DISTINCT r.panel_id) FILTER (
                WHERE r.state = 'CLEANING'
            ),
            0
        ) AS average_battery_cost_per_panel
    FROM readings r
    CROSS JOIN week_start w
    WHERE r.ts >= w.start_ts
    GROUP BY r.robot_id
)
SELECT robot_id, panels_cleaned, average_battery_cost_per_panel
FROM per_robot
WHERE panels_cleaned > 0
ORDER BY panels_cleaned DESC, robot_id
"""

SOILING_RATE_QUERY = """
SELECT
    CAST(ts AS DATE) AS day,
    panel_id,
    min(panel_dust) AS min_dust,
    max(panel_dust) AS max_dust,
    max(panel_dust) - min(panel_dust) AS dust_swing
FROM read_parquet(?, hive_partitioning = true)
WHERE state != 'CLEANING'
GROUP BY day, panel_id
ORDER BY day, panel_id
"""

CLEANING_EFFECTIVENESS_QUERY = """
WITH readings_with_previous_state AS (
    SELECT
        robot_id,
        ts,
        state,
        panel_id,
        panel_dust,
        brush_health_pct,
        lag(state) OVER (
            PARTITION BY robot_id ORDER BY ts
        ) AS previous_state
    FROM read_parquet(?, hive_partitioning = true)
),
session_starts AS (
    SELECT
        *,
        CASE
            WHEN state = 'CLEANING'
                 AND previous_state IS DISTINCT FROM 'CLEANING'
            THEN 1
            ELSE 0
        END AS is_session_start
    FROM readings_with_previous_state
),
numbered_readings AS (
    SELECT
        *,
        sum(is_session_start) OVER (
            PARTITION BY robot_id
            ORDER BY ts
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS session_number
    FROM session_starts
),
cleaning_readings AS (
    SELECT *
    FROM numbered_readings
    WHERE state = 'CLEANING'
)
SELECT
    robot_id,
    session_number,
    panel_id,
    min(ts) AS session_start,
    max(ts) AS session_end,
    count(*) AS tick_count,
    arg_min(panel_dust, ts) AS dust_at_start,
    arg_max(panel_dust, ts) AS dust_at_end,
    arg_min(panel_dust, ts) - arg_max(panel_dust, ts) AS dust_removed,
    avg(brush_health_pct) AS average_brush_health_pct
FROM cleaning_readings
GROUP BY robot_id, session_number, panel_id
ORDER BY session_start, robot_id
"""


def weekly_cleaning_summary(parquet_files):
    with duckdb.connect(":memory:") as connection:
        return connection.execute(WEEKLY_CLEANING_QUERY, [parquet_files]).fetchdf()


def soiling_rate_per_day(parquet_files):
    with duckdb.connect(":memory:") as connection:
        return connection.execute(SOILING_RATE_QUERY, [parquet_files]).fetchdf()


def cleaning_effectiveness_per_session(parquet_files):
    with duckdb.connect(":memory:") as connection:
        return connection.execute(
            CLEANING_EFFECTIVENESS_QUERY, [parquet_files]
        ).fetchdf()
