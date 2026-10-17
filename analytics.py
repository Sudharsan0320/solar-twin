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


def weekly_cleaning_summary(parquet_files):
    with duckdb.connect(":memory:") as connection:
        return connection.execute(WEEKLY_CLEANING_QUERY, [parquet_files]).fetchdf()
